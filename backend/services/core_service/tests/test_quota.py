"""Run from backend/services/core_service: python -m unittest discover -s tests"""
import datetime
import hashlib
import hmac
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key"
os.environ["AUDIT_SIGNING_KEY"] = "test-only-audit-key"

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1.quotas import signature_is_valid
from app.core import api_quota, quota_rules as rules, quota_service
from app.core.auth import get_current_user
from app.core.quota_worker import parse_usage_hash, rule_matches, should_notify
from app.db.models import UsageAlertRule
from app.db.rls import RLS_TABLES
from app.main import app
from app.schemas.quota import AlertRulePayload, ApiPolicyPayload, SmsAllocationPayload, StorageAllocationPayload

NOW = "2026-11-01T00:00:00"


def storage(**overrides):
    values = dict(tenantLevel="State", stateTenantId="T", allocationName="A", storageType="Image Storage", storageProvider="AWS S3", storageBucket="b",
                  allocationAmount=1, storageUnit="GB", maxFileSizeMb=10, allowedFileTypes=["png"], effectiveFrom=NOW)
    return StorageAllocationPayload(**{**values, **overrides})


class RuleTests(unittest.TestCase):
    def test_units_and_percentage(self):
        self.assertEqual(rules.to_bytes(2, "GB"), 2 * 1024 ** 3)
        self.assertEqual(rules.percentage(50, 200), 25.0)
        self.assertEqual(rules.percentage(1, 0), 0.0)

    def test_usage_status_reads_configured_levels(self):
        levels = [("Warning", 50.0), ("Critical", 60.0)]
        self.assertEqual(rules.usage_status(10, levels), "Normal")
        self.assertEqual(rules.usage_status(55, levels), "Warning")
        self.assertEqual(rules.usage_status(60, levels), "Critical")
        self.assertEqual(rules.usage_status(None, levels), "Not Connected")

    def test_effective_dates(self):
        now = datetime.datetime(2026, 6, 1)
        self.assertTrue(rules.is_effective(None, None, now))
        self.assertFalse(rules.is_effective(datetime.datetime(2026, 7, 1), None, now))
        self.assertFalse(rules.is_effective(None, datetime.datetime(2026, 5, 1), now))

    def test_module_allocations_must_fit(self):
        with self.assertRaises(ValidationError):
            storage(moduleAllocations=[{"moduleCode": "PTX", "allocationBytes": 2 * 1024 ** 3}])
        with self.assertRaises(ValidationError):
            storage(moduleAllocations=[{"moduleCode": "PTX", "allocationBytes": 1}, {"moduleCode": "PTX", "allocationBytes": 1}])

    def test_storage_payload_rejects_bad_values(self):
        for bad in (dict(allocationAmount=0), dict(allowedFileTypes=[]), dict(allowedFileTypes=["exe"]), dict(storageUnit="PB"), dict(effectiveUntil="2020-01-01T00:00:00"), dict(tenantLevel="ULB")):
            with self.assertRaises(ValidationError, msg=str(bad)):
                storage(**bad)

    def test_active_sms_allocation_needs_dlt_details(self):
        values = dict(allocationName="A", stateTenantId="T", smsProvider="MSG91", creditAllocation=1, validFrom=NOW, validUntil="2027-01-01T00:00:00", allocationStatus="Active")
        with self.assertRaises(ValidationError):
            SmsAllocationPayload(**values)
        self.assertEqual(SmsAllocationPayload(**values, dltEntityId="1", senderId="S", dltTemplateId="2").allocation_status, "Active")

    def test_quota_period_needs_its_limit(self):
        values = dict(tenantLevel="State", stateTenantId="T", apiGateway=rules.API_GATEWAYS[0], rateLimitPerMinute=1, effectiveFrom=NOW)
        with self.assertRaises(ValidationError):
            ApiPolicyPayload(**values, quotaPeriod=rules.PERIOD_DAY)
        ApiPolicyPayload(**values, quotaPeriod=rules.PERIOD_MINUTE)

    def test_alert_needs_the_threshold_its_condition_uses(self):
        values = dict(tenantLevel="State", stateTenantId="T", alertName="A", alertCode="A1", resourceType=rules.RESOURCE_STORAGE, comparisonOperator=">=",
                      alertSeverity="High", notificationChannels=["In-App"], notificationRecipients=["u"])
        with self.assertRaises(ValidationError):
            AlertRulePayload(**values, alertCondition=rules.CONDITION_PERCENT)
        with self.assertRaises(ValidationError):
            AlertRulePayload(**values, alertCondition=rules.CONDITION_VALUE, thresholdPercentage=5)

    def test_levels_are_seed_values_only(self):
        source = (rules.__file__)
        from pathlib import Path
        worker = Path(source).with_name("quota_worker.py").read_text()
        self.assertNotIn("70", worker)
        self.assertNotIn("95", worker)

    def test_new_tables_have_row_level_security(self):
        for table in ("storage_allocations", "storage_objects", "sms_credit_allocations", "sms_messages", "api_quota_policies", "api_usage_minutes", "usage_alert_rules", "usage_alert_events"):
            self.assertIn(table, RLS_TABLES)


def fake_request(path="/api/v1/properties"):
    request = MagicMock()
    request.url.path = path
    request.query_params = {}
    request.state = MagicMock(spec=[])
    return request


class FakePipe:
    def __init__(self, counts):
        self.counts = counts

    def incr(self, key):
        pass

    def expire(self, key, ttl):
        pass

    async def execute(self):
        return [value for count in self.counts for value in (count, True)]


class ApiEnforcementTests(unittest.IsolatedAsyncioTestCase):
    POLICY = {"services": [], "second": 2, "minute": 10, "hour": None, "day": None, "concurrent": None}
    USER = {"tenant_id": "GWMC", "realm_access": {"roles": ["revenue_officer"]}}

    def client_with(self, counts):
        client = MagicMock()
        client.pipeline.return_value = FakePipe(counts)
        return client

    async def run_enforce(self, counts, policy=None, user=None, path="/api/v1/properties"):
        with patch.object(api_quota.valkey_client, "client", self.client_with(counts)), patch.object(api_quota, "policy_for", AsyncMock(return_value=policy or self.POLICY)):
            await api_quota.enforce(fake_request(path), user or self.USER)

    async def test_within_limits_passes(self):
        await self.run_enforce([1, 1, 1, 1])

    async def test_minute_limit_blocks_with_retry_after(self):
        with self.assertRaises(HTTPException) as caught:
            await self.run_enforce([1, 11, 11, 11])
        self.assertEqual(caught.exception.status_code, 429)
        self.assertEqual(caught.exception.headers["Retry-After"], "60")

    async def test_burst_limit_blocks(self):
        with self.assertRaises(HTTPException) as caught:
            await self.run_enforce([3, 3, 3, 3])
        self.assertEqual(caught.exception.headers["Retry-After"], "1")

    async def test_super_admin_is_exempt(self):
        await self.run_enforce([99, 99, 99, 99], user={"tenant_id": "GWMC", "realm_access": {"roles": ["super_admin"]}})

    async def test_policy_for_other_services_does_not_apply(self):
        await self.run_enforce([99, 99, 99, 99], policy={**self.POLICY, "services": ["wtr"]})

    async def test_valkey_outage_allows_the_request(self):
        client = MagicMock()
        pipe = MagicMock()
        pipe.execute = AsyncMock(side_effect=ConnectionError())
        client.pipeline.return_value = pipe
        with patch.object(api_quota.valkey_client, "client", client), patch.object(api_quota, "policy_for", AsyncMock(return_value=self.POLICY)):
            await api_quota.enforce(fake_request(), self.USER)

    async def test_no_valkey_never_touches_the_database(self):
        with patch.object(api_quota.valkey_client, "client", None), patch.object(api_quota, "policy_for", AsyncMock(side_effect=AssertionError)):
            await api_quota.enforce(fake_request(), self.USER)

    def test_limit_tenant_comes_from_the_token(self):
        self.assertEqual(api_quota.token_tenant({"tenant_id": "TG,GWMC"}), "TG")

    def test_service_names(self):
        self.assertEqual(api_quota.service_of(fake_request("/api/v1/tenants/x")), "tenants")
        request = fake_request("/api/v1/auth/authorize")
        request.query_params = {"component": "PTX-P10"}
        self.assertEqual(api_quota.service_of(request), "ptx")

    def test_metering_outcomes(self):
        self.assertIn(("core|success", 1), api_quota.metric_fields("core", 200, 5))
        self.assertIn(("core|failed", 1), api_quota.metric_fields("core", 500, 5))
        self.assertIn(("core|throttled", 1), api_quota.metric_fields("core", 429, 5))
        self.assertEqual(parse_usage_hash({"ptx|total": "2", "ptx|latency": "9"}), {"ptx": {"total": 2, "latency": 9}})


class AlertLogicTests(unittest.TestCase):
    def rule(self, **values):
        return UsageAlertRule(**{**dict(alert_condition=rules.CONDITION_PERCENT, comparison_operator=">=", threshold_percentage=80.0, is_firing=False), **values})

    def test_rule_compares_the_chosen_measure(self):
        self.assertTrue(rule_matches(self.rule(), 1, 80))
        self.assertFalse(rule_matches(self.rule(), 1000, 79))
        self.assertTrue(rule_matches(self.rule(alert_condition=rules.CONDITION_VALUE, threshold_value=5.0), 5, 0))

    def test_firing_rule_repeats_only_after_its_interval(self):
        now = datetime.datetime(2026, 1, 1, 12)
        self.assertTrue(should_notify(self.rule(), now))
        recent = now - datetime.timedelta(minutes=5)
        self.assertFalse(should_notify(self.rule(is_firing=True, last_notified_at=recent), now))
        self.assertFalse(should_notify(self.rule(is_firing=True, last_notified_at=recent, repeat_interval_minutes=10), now))
        self.assertTrue(should_notify(self.rule(is_firing=True, last_notified_at=recent, repeat_interval_minutes=5), now))


class SmsTests(unittest.IsolatedAsyncioTestCase):
    def test_signature(self):
        good = hmac.new(b"s", b"body", hashlib.sha256).hexdigest()
        self.assertTrue(signature_is_valid(b"body", good, "s"))
        self.assertFalse(signature_is_valid(b"other", good, "s"))
        self.assertFalse(signature_is_valid(b"body", None, "s"))

    async def test_no_provider_sends_nothing_and_takes_no_credits(self):
        db = AsyncMock()
        with self.assertRaises(quota_service.SmsNotConnected):
            await quota_service.send_sms(db, tenant_id="T", to="1", text="x")
        db.scalars.assert_not_called()


class ApiAccessTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(app.dependency_overrides.clear)

    def test_admin_routes_need_a_super_admin(self):
        paths = ["options", "recipients", "storage/allocations", "storage/usage", "sms/allocations", "api/policies", "alerts/rules", "alerts/events", "alerts/levels"]
        app.dependency_overrides[get_current_user] = lambda: {"realm_access": {"roles": ["revenue_officer"]}, "tenant_id": "GWMC"}
        for path in paths:
            self.assertEqual(self.client.get(f"/api/v1/modules/quotas/{path}").status_code, 403, path)

    def test_delivery_reports_need_configuration_and_a_signature(self):
        url = "/api/v1/public/quotas/sms/delivery-reports"
        with patch("app.api.v1.quotas.settings.SMS_WEBHOOK_SECRET", ""):
            self.assertEqual(self.client.post(url, content=b"{}").status_code, 503)
        with patch("app.api.v1.quotas.settings.SMS_WEBHOOK_SECRET", "secret"):
            self.assertEqual(self.client.post(url, content=b"{}", headers={"X-Urban-Signature": "forged"}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
