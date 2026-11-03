"""Run from backend/services/core_service: python -m unittest discover -s tests"""
import os
import unittest

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key"
os.environ["AUDIT_SIGNING_KEY"] = "test-only-audit-key"

from pathlib import Path

from app.api.v1.executive import _share, _split
from app.api.v1.security import _describe_rls, _rls_is_enforced
from app.core import security
from app.schemas.executive import GlobalOverviewStats, GrievanceOverviewStats

APP_DIR = Path(__file__).resolve().parents[1] / "app"


class ExecutiveHonestyTests(unittest.TestCase):
    def test_unknown_metrics_default_to_null_not_zero(self):
        overview = GlobalOverviewStats()
        self.assertIsNone(overview.totalRevenueCollected)
        self.assertIsNone(overview.grievanceSlaCompliance)

    def test_unavailable_response_says_so(self):
        response = GrievanceOverviewStats(dataAvailable=False, unavailableReason="none")
        self.assertFalse(response.dataAvailable)
        self.assertIsNone(response.totalGrievances)

    def test_router_contains_no_invented_constants(self):
        source = (APP_DIR / "api/v1/executive.py").read_text()
        for invented in ("64200000", "45200000000", "except Exception", '"Telangana"', '"GWMC"'):
            self.assertNotIn(invented, source)

    def test_filter_values_are_normalized(self):
        self.assertEqual(_split(" tg,MH ", "tg", None, "ALL"), ["TG", "MH"])

    def test_share_of_zero_total_is_zero(self):
        self.assertEqual(_share(5, 0), 0.0)
        self.assertEqual(_share(1, 4), 25.0)


class RlsCheckTests(unittest.TestCase):
    def test_existing_table_without_rls_is_not_enforced(self):
        state = {"exists": True, "enabled": False, "forced": False, "policies": 0}
        self.assertFalse(_rls_is_enforced(state))
        self.assertIn("not enabled", _describe_rls("users", state))

    def test_enabled_without_policies_is_not_enforced(self):
        self.assertFalse(_rls_is_enforced({"exists": True, "enabled": True, "forced": False, "policies": 0}))

    def test_enabled_with_policy_is_enforced(self):
        self.assertTrue(_rls_is_enforced({"exists": True, "enabled": True, "forced": True, "policies": 1}))


class SimulationRemovalTests(unittest.TestCase):
    def test_backup_router_reports_no_fabricated_results(self):
        source = (APP_DIR / "api/v1/backup_dr.py").read_text()
        for fabricated in ("uuid.uuid4().hex + uuid.uuid4().hex", "_ensure_backup_dr_seeded", "Verified (Restorable)"):
            self.assertNotIn(fabricated, source)

    def test_isolation_run_is_not_hardcoded_to_pass(self):
        source = (APP_DIR / "api/v1/security.py").read_text()
        self.assertNotIn("100% pass rate", source)
        self.assertNotIn("_ensure_seeded_security_data", source)


class AuditSignatureTests(unittest.TestCase):
    def test_signature_verifies_for_same_hash(self):
        signature = security.sign_audit_hash("abc")
        self.assertTrue(security.audit_signature_is_valid("abc", signature))

    def test_changed_hash_fails(self):
        self.assertFalse(security.audit_signature_is_valid("abd", security.sign_audit_hash("abc")))

    def test_signature_depends_on_secret_key(self):
        original = security.AUDIT_SIGNING_KEY
        signature = security.sign_audit_hash("abc")
        security.AUDIT_SIGNING_KEY = b"another-key"
        self.addCleanup(setattr, security, "AUDIT_SIGNING_KEY", original)
        self.assertFalse(security.audit_signature_is_valid("abc", signature))

    def test_missing_signature_fails(self):
        self.assertFalse(security.audit_signature_is_valid("abc", None))


if __name__ == "__main__":
    unittest.main()
