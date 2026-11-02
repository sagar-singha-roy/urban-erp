"""Run from backend/libs/urban_common: python -m unittest discover -s tests"""
import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["ENVIRONMENT"] = "test"

from fastapi.testclient import TestClient

from urban_common import events
from urban_common.cache import scoped_key

SERVICES = Path(__file__).resolve().parents[3] / "services"
MODULES = {"PTX", "WTR", "GRV", "FIN", "TRL", "UCH", "SWM", "HRM", "DMS", "ENG", "BPM", "SLM", "TPL", "PRK", "MPM", "LGL", "INV", "FNC", "GSC"}


class ServiceTests(unittest.TestCase):
    def test_every_module_has_its_own_service_that_starts(self):
        found = set()
        for main in sorted(SERVICES.glob("*_service/app/main.py")):
            code = main.parents[1].name.split("_")[0].upper()
            if code in ("CORE", "PTX"):
                found.add(code)
                continue
            spec = importlib.util.spec_from_file_location(f"{code}_main", main)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with TestClient(module.app) as client:
                self.assertEqual(client.get("/health").json()["module"], code)
            found.add(code)
        self.assertEqual(found - {"CORE"}, MODULES)
        self.assertIn("CORE", found)


class CacheKeyTests(unittest.TestCase):
    def test_keys_are_scoped_to_tenant_and_city(self):
        self.assertEqual(scoped_key("TG", "GWMC", "properties"), "stats:tenant:TG:sub:GWMC:properties")
        self.assertEqual(scoped_key("GWMC", None, "properties"), "stats:tenant:GWMC:sub:ALL:properties")


class EventTests(unittest.IsolatedAsyncioTestCase):
    def test_topic_names_follow_the_architecture_convention(self):
        self.assertEqual(events.topic_name("ptx", "property", "registered"), "urban.ptx.property.registered.v1")

    async def test_outbox_row_uses_the_callers_transaction(self):
        db = AsyncMock()
        event_id = await events.add_to_outbox(db, "ptx-service", "t", "k", "GWMC", {"a": 1})
        params = db.execute.call_args.args[1]
        self.assertEqual(json.loads(params["payload"])["eventId"], event_id)
        db.commit.assert_not_called()

    async def test_handler_is_skipped_for_a_redelivered_event(self):
        db = AsyncMock()
        db.execute.return_value = MagicMock(first=MagicMock(return_value=None))
        handler = AsyncMock()
        session = MagicMock()
        session.return_value.__aenter__ = AsyncMock(return_value=db)
        session.return_value.__aexit__ = AsyncMock(return_value=False)
        with patch.object(events, "SessionLocal", session):
            handled = await events.handle_once("x-service", {"eventId": "1"}, handler)
        self.assertFalse(handled)
        handler.assert_not_called()


if __name__ == "__main__":
    unittest.main()
