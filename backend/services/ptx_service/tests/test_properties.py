"""Run from backend/services/ptx_service: python -m unittest discover -s tests"""
import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ["ENVIRONMENT"] = "test"

import httpx
from fastapi.testclient import TestClient

from urban_common import authz
from app.main import app


def core_answer(status_code, body):
    return AsyncMock(return_value=httpx.Response(status_code, json=body, request=httpx.Request("POST", "http://core")))


class PropertyAccessTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_refusal_from_core_is_passed_on(self):
        with patch.object(authz._client, "post", core_answer(403, {"detail": "Operation requires PTX-P01:VIEW"})):
            response = self.client.get("/api/v1/properties", headers={"Authorization": "Bearer t"})
        self.assertEqual(response.status_code, 403)

    def test_requests_are_refused_when_core_cannot_answer(self):
        with patch.object(authz._client, "post", AsyncMock(side_effect=httpx.ConnectError("down"))):
            response = self.client.get("/api/v1/properties", headers={"Authorization": "Bearer t"})
        self.assertEqual(response.status_code, 503)

    def test_cookie_writes_need_the_csrf_header(self):
        with patch.object(authz._client, "post", core_answer(200, {"tenantId": "GWMC"})) as post:
            response = self.client.post("/api/v1/properties", json={}, cookies={"urban_session": "t"})
        self.assertEqual(response.status_code, 403)
        post.assert_not_called()

    def test_token_and_tenant_headers_reach_core(self):
        with patch.object(authz._client, "post", core_answer(401, {"detail": "no"})) as post:
            self.client.get("/api/v1/properties", headers={"Authorization": "Bearer t", "X-Tenant-ID": "GWMC"})
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["params"], {"component": "PTX-P01", "action": "VIEW"})
        self.assertEqual(kwargs["headers"]["authorization"], "Bearer t")
        self.assertEqual(kwargs["headers"]["x-tenant-id"], "GWMC")

    def test_the_resolved_tenant_scopes_row_level_security(self):
        from urban_common.tenant_context import rls_params

        seen = {}

        async def endpoint_probe():
            seen.update(rls_params())

        checker = authz.require_access("PTX-P01", "VIEW")
        request = AsyncMock()
        request.headers = {"authorization": "Bearer t"}
        request.method = "GET"

        async def run():
            await checker(request)
            await endpoint_probe()

        import asyncio

        with patch.object(authz._client, "post", core_answer(200, {"tenantId": "gwmc"})):
            asyncio.run(run())
        self.assertEqual(seen["tenant_ids"], "GWMC")


if __name__ == "__main__":
    unittest.main()
