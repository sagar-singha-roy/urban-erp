"""Run from backend/services/core_service: python -m unittest discover -s tests"""
import os
import unittest

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key"
os.environ["AUDIT_SIGNING_KEY"] = "test-only-audit-key"

from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.tenant_context import rls_params, set_rls_context
from app.db.rls import RLS_TABLES, policy_expression

APP_DIR = Path(__file__).resolve().parents[1] / "app"


class RlsConfigurationTests(unittest.TestCase):
    def test_requests_do_not_use_the_admin_role(self):
        if "DATABASE_URL" not in os.environ:
            self.assertNotEqual(make_url(settings.write_db_url).username, make_url(settings.admin_db_url).username)

    def test_every_tenant_property_table_is_covered(self):
        for table in ("property_parcels", "buildings", "property_units", "owners", "wards", "zones", "localities"):
            self.assertIn(table, RLS_TABLES)

    def test_policy_reads_request_scope(self):
        expression = policy_expression("owners")
        self.assertIn("app.tenant_ids", expression)
        self.assertIn("owners.tenant_id", expression)

    def test_context_normalizes_and_defaults_to_no_bypass(self):
        set_rls_context([" gwmc ", "GHMC", ""])
        self.assertEqual(rls_params(), {"tenant_ids": "GHMC,GWMC", "bypass": "off"})
        set_rls_context([], bypass=True)
        self.assertEqual(rls_params(), {"tenant_ids": "", "bypass": "on"})
        set_rls_context([])


class SimulationRemovalTests(unittest.TestCase):
    def read(self, relative):
        return (APP_DIR / relative).read_text()

    def test_fleet_has_no_seeded_metrics(self):
        source = self.read("api/v1/fleet.py")
        for fabricated in ("_ensure_fleet_seeded", "99.99", "cpu_usage_pct=", "suvidha.internal"):
            self.assertNotIn(fabricated, source)

    def test_retention_policies_are_not_seeded(self):
        source = self.read("api/v1/audit_vault.py")
        self.assertNotIn("_ensure_vault_seeded", source)
        self.assertNotIn("WORM S3", source)

    def test_retest_does_not_always_pass(self):
        source = self.read("api/v1/security.py")
        self.assertNotIn("Synthetic boundary penetration", source)
        self.assertIn("VERIFIED can only be set by a passing retest", source)

    def test_restore_never_targets_an_existing_database(self):
        source = self.read("core/backup_runner.py")
        self.assertIn('target = f"restore_{uuid.uuid4().hex[:12]}"', source)
        self.assertNotIn("--clean", source)


if __name__ == "__main__":
    unittest.main()
