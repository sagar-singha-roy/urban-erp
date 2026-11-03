"""Run from backend/libs/urban_common: python -m unittest discover -s tests"""
import os
import unittest

os.environ["ENVIRONMENT"] = "test"

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient

from urban_common.impersonation import SupportSessionGuard, mask_payload

PARTS = ["email", "mobile", "aadhaar"]


def app_with(rules):
    app = FastAPI()
    app.add_middleware(SupportSessionGuard)

    @app.get("/owner")
    async def owner(request: Request):
        request.state.impersonation = rules
        return {"ownerName": "Ravi", "mobile": "9876543210", "aadhaar": "123412341234"}

    @app.get("/report")
    async def report(request: Request):
        request.state.impersonation = rules
        return Response("a,b", media_type="text/csv")

    return app


class SupportSessionGuardTests(unittest.TestCase):
    def test_fields_core_names_are_masked(self):
        data = mask_payload({"owners": [{"email": "ravi@gmail.com", "ward": "14"}]}, PARTS)
        self.assertEqual(data, {"owners": [{"email": "r***@gmail.com", "ward": "14"}]})

    def test_session_responses_are_masked_and_downloads_refused(self):
        client = TestClient(app_with({"maskSensitive": True, "downloadDisabled": True, "sensitiveFieldParts": PARTS}))
        self.assertEqual(client.get("/owner").json(), {"ownerName": "Ravi", "mobile": "******3210", "aadhaar": "********1234"})
        self.assertEqual(client.get("/report").status_code, 403)

    def test_ordinary_requests_are_untouched(self):
        client = TestClient(app_with(None))
        self.assertEqual(client.get("/owner").json()["mobile"], "9876543210")
        self.assertEqual(client.get("/report").status_code, 200)


if __name__ == "__main__":
    unittest.main()
