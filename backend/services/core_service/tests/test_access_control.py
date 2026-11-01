"""Run from backend/services/core_service: python -m unittest discover -s tests"""
import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key"

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core import auth
from app.core.auth import can_access_tenant, get_current_user, get_current_tenant
from app.core.security import create_access_token
from app.main import app
from app.schemas.auth import SignUpRequest

PUBLIC_ROUTES = {("POST", "/api/v1/auth/signin"), ("POST", "/api/v1/auth/signup"), ("POST", "/api/v1/auth/logout"), ("GET", "/health")}
STATE_SCOPED_PREFIXES = ("/api/v1/executive/gis", "/api/v1/modules/delegation", "/api/v1/modules/subscriptions")
SUPER_ADMIN_PREFIXES = (
    "/api/v1/iam",
    "/api/v1/security",
    "/api/v1/modules",
    "/api/v1/fleet",
    "/api/v1/executive",
    "/api/v1/compliance/audit",
    "/api/v1/admin",
)


def api_routes():
    """The OpenAPI schema lists every route, including those inside included routers."""
    routes = [
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    ]
    assert len(routes) > 100, "Route discovery found too few routes"
    return routes


def concrete(path):
    return path.replace("{", "").replace("}", "")


def user_with(role, tenant="GWMC"):
    return {"realm_access": {"roles": [role]}, "tenant_id": tenant}


class RouteProtectionTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(app.dependency_overrides.clear)

    def test_every_non_public_route_rejects_anonymous_requests(self):
        for method, path in api_routes():
            if (method, path) in PUBLIC_ROUTES:
                continue
            with self.subTest(method=method, path=path):
                self.assertEqual(self.client.request(method, concrete(path)).status_code, 401)

    def test_platform_routes_reject_non_super_admins(self):
        for role in ("citizen", "revenue_officer", "state_director"):
            app.dependency_overrides[get_current_user] = lambda role=role: user_with(role)
            for method, path in api_routes():
                if path.startswith(SUPER_ADMIN_PREFIXES) and not path.startswith(STATE_SCOPED_PREFIXES):
                    with self.subTest(role=role, method=method, path=path):
                        self.assertEqual(self.client.request(method, concrete(path)).status_code, 403)

    def test_citizens_cannot_read_property_records(self):
        token_user = user_with("citizen")
        app.dependency_overrides[get_current_user] = lambda: token_user
        fake_db = AsyncMock()
        fake_db.scalar.return_value = None
        app.dependency_overrides[auth.get_read_db] = lambda: fake_db
        self.assertEqual(self.client.get("/api/v1/properties").status_code, 403)

    def test_token_signed_with_another_key_is_rejected(self):
        from jose import jwt

        forged = jwt.encode({"realm_access": {"roles": ["super_admin"]}}, "guessed-key", algorithm="HS256")
        with patch.object(auth, "get_keycloak_jwks", AsyncMock(return_value={})):
            response = self.client.get("/api/v1/iam/roles", headers={"Authorization": f"Bearer {forged}"})
        self.assertEqual(response.status_code, 401)

    def test_validly_signed_citizen_token_is_forbidden(self):
        token = create_access_token(user_with("citizen"))
        with patch.object(auth, "_apply_current_account_state", AsyncMock(side_effect=lambda payload: payload)):
            response = self.client.get("/api/v1/iam/roles", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(response.status_code, 403)


class SignupTests(unittest.TestCase):
    def test_privileged_fields_are_not_accepted(self):
        request = SignUpRequest(
            username="x", email="x@example.com", password="long-enough", fullName="X", role="super_admin"
        )
        self.assertFalse(hasattr(request, "role"))

    def test_short_password_is_rejected(self):
        with self.assertRaises(ValidationError):
            SignUpRequest(username="x", email="x@example.com", password="short", fullName="X")


class TenantScopeTests(unittest.IsolatedAsyncioTestCase):
    def identifiers(self, *values):
        return patch.object(auth, "_tenant_identifiers", AsyncMock(return_value=set(values)))

    async def test_city_user_cannot_reach_another_city(self):
        with self.identifiers("GHMC", "TG"):
            self.assertFalse(await can_access_tenant("GHMC", user_with("revenue_officer"), None))

    async def test_city_user_cannot_use_parent_state_scope(self):
        with self.identifiers("TG"):
            self.assertFalse(await can_access_tenant("TG", user_with("revenue_officer"), None))

    async def test_state_user_can_reach_child_city(self):
        with self.identifiers("GWMC", "TG"):
            self.assertTrue(await can_access_tenant("GWMC", user_with("state_director", "TG"), None))

    async def test_state_user_cannot_reach_other_state_city(self):
        with self.identifiers("BMC", "MH"):
            self.assertFalse(await can_access_tenant("BMC", user_with("state_director", "TG"), None))

    async def test_super_admin_can_reach_any_tenant(self):
        self.assertTrue(await can_access_tenant("BMC", user_with("super_admin"), None))

    async def test_spoofed_tenant_header_is_rejected(self):
        with self.identifiers("GHMC", "TG"):
            with self.assertRaises(auth.HTTPException) as caught:
                await get_current_tenant("GHMC", None, user_with("revenue_officer"), None)
        self.assertEqual(caught.exception.status_code, 403)

    async def test_authorized_city_context_takes_priority_over_state(self):
        self.assertEqual(await get_current_tenant("TG", "GWMC", user_with("revenue_officer"), None), "GWMC")

    async def test_user_without_tenant_is_rejected(self):
        with self.assertRaises(auth.HTTPException):
            await get_current_tenant(None, None, {"realm_access": {"roles": ["citizen"]}}, None)


if __name__ == "__main__":
    unittest.main()
