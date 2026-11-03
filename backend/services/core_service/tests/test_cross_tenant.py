"""Run from backend/services/core_service: python -m unittest discover -s tests"""
import datetime
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key"
os.environ["AUDIT_SIGNING_KEY"] = "test-only-audit-key"

from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.cross_tenant_reviews import safe_cell
from app.core import auth, cross_tenant_access as access, cross_tenant_rules as rules
from app.schemas.cross_tenant import GrantPayload, ReviewDecisionPayload, RulePayload, ScopePayload

NOW = datetime.datetime(2026, 11, 1, 12)
STATE = "STATE-UUID"


def grant(targets, scope=None, level=rules.LEVEL_READ_WRITE):
    return SimpleNamespace(id="g1", access_level=level, targets=[SimpleNamespace(target_tenant_id=t) for t in targets], scope=scope)


def scope(**values):
    base = dict(effective_date=NOW - datetime.timedelta(days=1), expiry_date=None, include_child_tenants=True, ulb_tenant_ids=[],
                restricted_components=[], department_ids=[], zone_ids=[], ward_ids=[], access_scope="State", scope_mode="Explicit")
    return SimpleNamespace(**{**base, **values})


def entry(level=rules.LEVEL_READ_WRITE, restricted=(), deny=()):
    return {"grant_id": "g", "access_level": level, "restricted": list(restricted), "deny": list(deny), "departments": [], "zones": [], "wards": []}


def granted_user(grants, home="GWMC"):
    return access.with_grants({"realm_access": {"roles": ["revenue_officer"]}, "tenant_id": home, "tenant_scope": home}, grants)


class RuleTests(unittest.TestCase):
    def test_record_number(self):
        self.assertEqual(rules.record_number(7), "XTA-000007")

    def test_levels(self):
        self.assertTrue(rules.method_allowed(rules.LEVEL_READ_ONLY, "GET"))
        self.assertFalse(rules.method_allowed(rules.LEVEL_READ_ONLY, "POST"))
        self.assertTrue(rules.method_allowed(rules.LEVEL_READ_WRITE, "DELETE"))
        self.assertFalse(rules.action_allowed(rules.LEVEL_READ_ONLY, "CREATE"))
        self.assertFalse(rules.action_allowed(rules.LEVEL_READ_WRITE, "APPROVE"))
        self.assertTrue(rules.action_allowed(rules.LEVEL_ADMIN, "MANAGE"))

    def test_rule_names_components_or_whole_modules(self):
        self.assertTrue(rules.rule_covers(["PTX"], [], ["Approve"], "PTX-P10", "APPROVE"))
        self.assertFalse(rules.rule_covers(["PTX"], ["PTX-P01"], ["Approve"], "PTX-P10", "APPROVE"))
        self.assertFalse(rules.rule_covers(["PTX"], [], ["View"], "PTX-P10", "APPROVE"))

    def test_restrictions(self):
        self.assertTrue(rules.is_restricted(["PTX"], "PTX-P10"))
        self.assertTrue(rules.is_restricted(["PTX-P10"], "PTX-P10"))
        self.assertFalse(rules.is_restricted(["WTR"], "PTX-P10"))


class GrantReachTests(unittest.TestCase):
    def test_whole_state_includes_its_code(self):
        self.assertEqual(access.grant_tenants(grant([STATE]), {STATE: "TG"}, NOW), {STATE, "TG"})

    def test_scope_without_children_keeps_only_listed_ulbs(self):
        reached = access.grant_tenants(grant([STATE], scope(include_child_tenants=False, ulb_tenant_ids=["gwmc"])), {STATE: "TG"}, NOW)
        self.assertEqual(reached, {"GWMC"})

    def test_expired_scope_reaches_nothing(self):
        self.assertEqual(access.grant_tenants(grant(["GHMC"], scope(expiry_date=NOW - datetime.timedelta(hours=1))), {}, NOW), set())

    def test_home_scope_is_kept_apart(self):
        user = granted_user({"GHMC": [entry()]})
        self.assertEqual(user["tenant_scope"], "GHMC,GWMC")
        self.assertEqual(user["home_tenant_scope"], "GWMC")
        self.assertEqual(access.entries_for(user, {"GWMC", "TG"}), [])
        self.assertEqual(len(access.entries_for(user, {"GHMC", "TG"})), 1)

    def test_no_grants_leaves_the_token_alone(self):
        payload = {"tenant_id": "GWMC"}
        self.assertIs(access.with_grants(payload, {}), payload)


class ActionTests(unittest.TestCase):
    def test_read_only_cannot_create(self):
        self.assertFalse(access.action_permitted([entry(rules.LEVEL_READ_ONLY)], {"GHMC"}, "PTX-P10", "CREATE"))
        self.assertTrue(access.action_permitted([entry(rules.LEVEL_READ_ONLY)], {"GHMC"}, "PTX-P10", "VIEW"))

    def test_restricted_component_is_blocked(self):
        self.assertFalse(access.action_permitted([entry(restricted=["PTX"])], {"GHMC"}, "PTX-P10", "VIEW"))

    def test_deny_rule_beats_the_access_level(self):
        deny = {"tenant": "GHMC", "modules": ["PTX"], "components": ["PTX-P10"], "actions": ["Update"]}
        self.assertFalse(access.action_permitted([entry(rules.LEVEL_ADMIN, deny=[deny])], {"GHMC"}, "PTX-P10", "UPDATE"))
        self.assertTrue(access.action_permitted([entry(rules.LEVEL_ADMIN, deny=[deny])], {"GHMC"}, "PTX-P01", "UPDATE"))

    def test_deny_rule_only_applies_in_its_tenant(self):
        deny = {"tenant": "GHMC", "modules": ["PTX"], "components": [], "actions": ["View"]}
        self.assertTrue(access.action_permitted([entry(deny=[deny])], {"KMC"}, "PTX-P10", "VIEW"))

    def test_another_grant_can_still_allow(self):
        self.assertTrue(access.action_permitted([entry(rules.LEVEL_READ_ONLY), entry(rules.LEVEL_READ_WRITE)], {"GHMC"}, "PTX-P10", "CREATE"))


def fake_request(method="POST", headers=None, path_params=None, query_params=None):
    return SimpleNamespace(method=method, headers=headers or {}, path_params=path_params or {}, query_params=query_params or {})


class FakeSession:
    async def __aenter__(self):
        return AsyncMock()

    async def __aexit__(self, *exc):
        return False


class EnforcementTests(unittest.IsolatedAsyncioTestCase):
    def identifiers(self, *values):
        return patch.object(auth, "_tenant_identifiers", AsyncMock(return_value=set(values)))

    async def test_read_only_grant_blocks_writes_to_that_tenant(self):
        user = granted_user({"GHMC": [entry(rules.LEVEL_READ_ONLY)]})
        with self.identifiers("GHMC", "TG"), patch.object(auth, "AsyncReadSessionLocal", FakeSession):
            with self.assertRaises(HTTPException) as caught:
                await auth._enforce_cross_tenant_method(fake_request(headers={"X-Tenant-ID": "ghmc"}), user)
            self.assertEqual(caught.exception.status_code, 403)
            await auth._enforce_cross_tenant_method(fake_request("GET", headers={"X-Tenant-ID": "ghmc"}), user)

    async def test_authorize_is_checked_by_action_not_method(self):
        user = granted_user({"GHMC": [entry(rules.LEVEL_READ_ONLY)]})
        request = fake_request(headers={"X-Tenant-ID": "GHMC"})
        request.url = SimpleNamespace(path=auth.AUTHORIZE_PATH)
        with self.identifiers("GHMC", "TG"), patch.object(auth, "AsyncReadSessionLocal", FakeSession):
            await auth._enforce_cross_tenant_method(request, user)

    async def test_home_tenant_writes_are_unaffected(self):
        user = granted_user({"GHMC": [entry(rules.LEVEL_READ_ONLY)]})
        with self.identifiers("GWMC", "TG"), patch.object(auth, "AsyncReadSessionLocal", FakeSession):
            await auth._enforce_cross_tenant_method(fake_request(headers={"X-Tenant-ID": "GWMC"}), user)

    async def test_permission_check_applies_the_grant(self):
        user = granted_user({"GHMC": [entry(rules.LEVEL_READ_WRITE)]})
        checker = auth.require_permission("PTX-P10", "APPROVE")
        with self.identifiers("GHMC", "TG"):
            with self.assertRaises(HTTPException) as caught:
                await checker(fake_request(headers={"X-Sub-Tenant-ID": "GHMC"}), user, AsyncMock())
        self.assertIn("PTX-P10:APPROVE", caught.exception.detail)

    async def test_grants_are_read_on_every_request(self):
        """Revoking or expiring a grant must take effect without the user signing in again."""
        db = AsyncMock()
        db.scalar.side_effect = [SimpleNamespace(is_active=True, email="a@x.in", role="revenue_officer"), None] * 2
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=db)
        session.__aexit__ = AsyncMock(return_value=False)
        loader = AsyncMock(side_effect=[{"GHMC": [entry()]}, {}])
        with patch.object(auth, "AsyncReadSessionLocal", MagicMock(return_value=session)), patch.object(auth, "load_active_grants", loader):
            first = await auth._apply_current_account_state({"sub": "u", "tenant_id": "GWMC"})
            second = await auth._apply_current_account_state({"sub": "u", "tenant_id": "GWMC"})
        self.assertIn("GHMC", first["tenant_scope"])
        self.assertNotIn("cross_tenant", second)

    def test_request_tenants_reads_headers_and_parameters(self):
        request = fake_request(headers={"X-Tenant-ID": "tg", "X-Sub-Tenant-ID": "ALL"}, path_params={"tenant_id": "ghmc"}, query_params={"state_tenant_id": "TG"})
        self.assertEqual(access.request_tenants(request), ["TG", "GHMC"])


class PayloadTests(unittest.TestCase):
    GRANT = dict(userProfileId="u", userType="Support", homeTenantId="GWMC", targetTenantIds=["GHMC"], accessLevel="Read Only",
                 effectiveFrom="2026-11-01T00:00:00", businessJustification="Audit support for the quarter", approvalAuthorityId="a")

    def test_grant_rules(self):
        GrantPayload(**self.GRANT)
        for bad in (dict(targetTenantIds=["GWMC"]), dict(effectiveUntil="2026-10-01T00:00:00"), dict(accessLevel="Owner"),
                    dict(userType="Citizen"), dict(targetTenantIds=["GHMC", "GHMC"]), dict(businessJustification="short")):
            with self.assertRaises(ValidationError, msg=str(bad)):
                GrantPayload(**{**self.GRANT, **bad})

    def test_scope_needs_the_areas_its_level_names(self):
        values = dict(grantId="g", accessScope="Ward", stateTenantId="S", scopeMode="Explicit", effectiveDate="2026-11-01T00:00:00")
        with self.assertRaises(ValidationError):
            ScopePayload(**values)
        with self.assertRaises(ValidationError):
            ScopePayload(**{**values, "accessScope": "State", "includeChildTenants": False})
        ScopePayload(**{**values, "wardIds": ["w1"]})

    def test_deny_rule_needs_a_reason(self):
        values = dict(grantId="g", targetTenantId="GHMC", moduleCodes=["PTX"], actionPermissions=["View"], dataAccessScope="ULB", accessDecision="Deny")
        with self.assertRaises(ValidationError):
            RulePayload(**values)
        RulePayload(**values, restrictionReason="Not needed for the audit")

    def test_revoke_decision_needs_a_comment(self):
        with self.assertRaises(ValidationError):
            ReviewDecisionPayload(reviewDecision="Revoke")
        ReviewDecisionPayload(reviewDecision="Retain")

    def test_export_cells_cannot_become_formulas(self):
        self.assertEqual(safe_cell("=HYPERLINK(1)"), "'=HYPERLINK(1)")
        self.assertEqual(safe_cell(None), "")
        self.assertEqual(safe_cell("REVOKED"), "REVOKED")


if __name__ == "__main__":
    unittest.main()
