"""Run from backend/services/core_service: python -m unittest discover -s tests"""
import os
import unittest
from unittest.mock import patch

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key"
os.environ["AUDIT_SIGNING_KEY"] = "test-only-audit-key"

from app.core import rate_limit
from app.core.auth import keycloak_token_is_for_this_client
from app.core.config import settings


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        rate_limit.clear("k")
        self.addCleanup(rate_limit.clear, "k")

    def test_blocks_after_limit(self):
        for _ in range(rate_limit.MAX_FAILURES - 1):
            rate_limit.record_failure("k")
        self.assertEqual(rate_limit.retry_after("k"), 0)
        rate_limit.record_failure("k")
        self.assertGreater(rate_limit.retry_after("k"), 0)

    def test_success_clears(self):
        for _ in range(rate_limit.MAX_FAILURES):
            rate_limit.record_failure("k")
        rate_limit.clear("k")
        self.assertEqual(rate_limit.retry_after("k"), 0)

    def test_failures_expire(self):
        with patch.object(rate_limit.time, "monotonic", return_value=1000.0):
            for _ in range(rate_limit.MAX_FAILURES):
                rate_limit.record_failure("k")
        with patch.object(rate_limit.time, "monotonic", return_value=1000.0 + rate_limit.WINDOW_SECONDS + 1):
            self.assertEqual(rate_limit.retry_after("k"), 0)


class KeycloakAudienceTests(unittest.TestCase):
    def test_accepts_this_client(self):
        self.assertTrue(keycloak_token_is_for_this_client({"aud": [settings.KEYCLOAK_CLIENT_ID]}))
        self.assertTrue(keycloak_token_is_for_this_client({"aud": "account", "azp": settings.KEYCLOAK_CLIENT_ID}))

    def test_rejects_another_client(self):
        self.assertFalse(keycloak_token_is_for_this_client({"aud": "account", "azp": "other-app"}))
        self.assertFalse(keycloak_token_is_for_this_client({}))


class ServerErrorTests(unittest.TestCase):
    def test_unexpected_errors_keep_cors_headers(self):
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.testclient import TestClient

        from app.main import ServerErrorResponder

        app = FastAPI()
        app.add_middleware(ServerErrorResponder)
        app.add_middleware(CORSMiddleware, allow_origins=["http://allowed.test"])

        @app.get("/boom")
        async def boom():
            raise RuntimeError("boom")

        response = TestClient(app).get("/boom", headers={"Origin": "http://allowed.test"})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://allowed.test")
        self.assertEqual(response.json(), {"detail": "The server could not complete this request."})


if __name__ == "__main__":
    unittest.main()
