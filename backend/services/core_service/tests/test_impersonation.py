"""Run from backend/services/core_service: python -m unittest discover -s tests"""
import datetime
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key"
os.environ["AUDIT_SIGNING_KEY"] = "test-only-audit-key"

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core import auth, impersonation, impersonation_rules as rules
from app.core.security import create_access_token, decode_access_token
from app.schemas.impersonation import DecisionPayload, PolicyPayload, RequestPayload

API = "/api/v1"


def session_row(**values):
    base = dict(id="s1", session_sequence=4, target_user_id="target", support_user_id="agent", support_email="agent@x.in", status=rules.SESSION_ACTIVE,
                expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=10), access_mode=rules.MODE_READ_ONLY, tenant_id="GWMC")
    return SimpleNamespace(**{**base, **values})


def request_row():
    return SimpleNamespace(policy_snapshot={"writeActionsAllowed": ["PTX-P10:UPDATE"], "maskSensitiveData": True, "downloadDisabled": True, "sessionRecording": True})


def context(**values):
    return {**impersonation.session_context(session_row(), request_row()), **values}


class RuleTests(unittest.TestCase):
    def test_read_only_allows_viewing_only(self):
        self.assertTrue(rules.action_permitted(rules.MODE_READ_ONLY, ["PTX-P10:UPDATE"], True, "PTX-P10", "VIEW"))
        self.assertFalse(rules.action_permitted(rules.MODE_READ_ONLY, ["PTX-P10:UPDATE"], True, "PTX-P10", "UPDATE"))

    def test_restricted_allows_listed_actions_only(self):
        self.assertTrue(rules.action_permitted(rules.MODE_RESTRICTED, ["PTX-P10:UPDATE"], True, "PTX-P10", "UPDATE"))
        self.assertFalse(rules.action_permitted(rules.MODE_RESTRICTED, ["PTX-P10:UPDATE"], True, "PTX-P10", "DELETE"))
        self.assertFalse(rules.action_permitted(rules.MODE_RESTRICTED, ["PTX-P10:UPDATE"], True, "PTX-P01", "UPDATE"))

    def test_export_follows_the_download_setting(self):
        self.assertFalse(rules.action_permitted(rules.MODE_READ_ONLY, [], True, "PTX-P01", "EXPORT"))
        self.assertTrue(rules.action_permitted(rules.MODE_READ_ONLY, [], False, "PTX-P01", "EXPORT"))

    def test_masking(self):
        masked = rules.mask_payload({"ownerName": "Ravi", "email": "ravi@gmail.com", "mobileNumber": "9876543210", "items": [{"aadhaar_number": "123412341234"}],
                                     "officeAddress": "Plot 12, Hanamkonda", "contact": {"phone": None}})
        self.assertEqual(masked["ownerName"], "Ravi")
        self.assertEqual(masked["email"], "r***@gmail.com")
        self.assertEqual(masked["mobileNumber"], "******3210")
        self.assertEqual(masked["items"][0]["aadhaar_number"], "********1234")
        self.assertTrue(masked["officeAddress"].startswith("Pl*"))
        self.assertIsNone(masked["contact"]["phone"])

    def test_downloads(self):
        self.assertTrue(rules.is_download("text/csv; charset=utf-8", None))
        self.assertTrue(rules.is_download("application/json", 'attachment; filename="x.json"'))
        self.assertFalse(rules.is_download("image/png", None))
        self.assertFalse(rules.is_download("application/json", None))

    def test_role_codes_match_the_permission_matrix(self):
        self.assertEqual(rules.role_code("super_admin"), "PLATFORM_SUPER_ADMIN")
        self.assertEqual(auth.ROLE_CODES["revenue_officer"], rules.role_code("revenue_officer"))


class TokenTests(unittest.IsolatedAsyncioTestCase):
    def db_returning(self, row):
        db = AsyncMock()
        result = MagicMock()
        result.first.return_value = row
        db.execute.return_value = result
        return db

    def token(self, session=None):
        return impersonation.issue_token(session or session_row())

    def test_token_names_the_agent_and_never_holds_credentials(self):
        payload = decode_access_token(self.token())
        self.assertEqual(payload["typ"], rules.TOKEN_TYPE)
        self.assertEqual(payload["act"]["sub"], "agent")
        self.assertEqual(payload["sub"], "target")
        self.assertFalse({"password", "password_hash", "realm_access"} & set(payload))

    async def test_session_token_cannot_be_used_as_a_sign_in(self):
        with self.assertRaises(HTTPException) as caught:
            await auth._apply_current_account_state(decode_access_token(self.token()))
        self.assertEqual(caught.exception.status_code, 401)

    async def test_live_session_loads(self):
        session, _ = await impersonation.load_session(self.db_returning((session_row(), request_row())), self.token(), "agent")
        self.assertEqual(session.id, "s1")

    async def test_token_only_works_for_its_own_agent(self):
        with self.assertRaises(HTTPException):
            await impersonation.load_session(self.db_returning((session_row(), request_row())), self.token(), "someone-else")

    async def test_ended_or_expired_sessions_are_refused(self):
        for row in (session_row(status=rules.SESSION_TERMINATED), session_row(expires_at=datetime.datetime.utcnow() - datetime.timedelta(seconds=1))):
            with self.assertRaises(HTTPException):
                await impersonation.load_session(self.db_returning((row, request_row())), self.token(), "agent")

    async def test_ordinary_token_is_not_a_session_token(self):
        with self.assertRaises(HTTPException):
            await impersonation.load_session(self.db_returning((session_row(), request_row())), create_access_token({"sub": "target"}), "agent")


def fake_request(method="GET", path=f"{API}/properties"):
    return SimpleNamespace(method=method, url=SimpleNamespace(path=path), state=SimpleNamespace())


class EnforcementTests(unittest.TestCase):
    def test_reads_pass(self):
        request = fake_request()
        impersonation.enforce_path(request, context())
        self.assertEqual(request.state.impersonation["sessionId"], "s1")

    def test_account_admin_and_hub_routes_are_closed(self):
        for path in (f"{API}/auth/signin", f"{API}/iam/users", f"{API}/impersonation/requests"):
            with self.assertRaises(HTTPException, msg=path):
                impersonation.enforce_path(fake_request(path=path), context())

    def test_profile_and_module_authorization_stay_open(self):
        impersonation.enforce_path(fake_request(path=f"{API}/auth/me"), context())
        impersonation.enforce_path(fake_request("POST", impersonation.AUTHORIZE_PATH), context())

    def test_core_writes_are_refused(self):
        with self.assertRaises(HTTPException):
            impersonation.enforce_path(fake_request("PUT", f"{API}/executive/gis/workspaces/x"), context())

    def test_action_check_records_what_was_asked(self):
        request = fake_request()
        with self.assertRaises(HTTPException):
            impersonation.check_action(request, context(), "PTX-P10", "UPDATE")
        self.assertEqual(request.state.impersonation_permission, "PTX-P10:UPDATE")
        impersonation.check_action(request, context(mode=rules.MODE_RESTRICTED), "PTX-P10", "UPDATE")


class GetCurrentUserTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_cookie_switches_identity(self):
        request = MagicMock()
        request.method, request.url.path = "GET", f"{API}/properties"
        request.cookies = {"urban_session": "agent-token", impersonation.IMPERSONATION_COOKIE: "support-token"}
        request.headers = {}
        target = {"sub": "target", "tenant_id": "GWMC", "realm_access": {"roles": ["revenue_officer"]}, "impersonation": context()}
        with patch.object(auth, "_authenticate_support_session", AsyncMock(return_value=target)) as support, \
                patch.object(auth, "enforce_api_quota", AsyncMock()):
            user = await auth.get_current_user(request, None)
        support.assert_awaited_once_with("agent-token", "support-token")
        self.assertEqual(user["sub"], "target")

    async def test_bearer_requests_ignore_the_session_cookie(self):
        request = MagicMock()
        request.method = "GET"
        request.cookies = {impersonation.IMPERSONATION_COOKIE: "support-token"}
        credentials = SimpleNamespace(credentials="bearer-token")
        agent = {"sub": "agent", "tenant_id": "GWMC", "realm_access": {"roles": ["revenue_officer"]}}
        with patch.object(auth, "_authenticate", AsyncMock(return_value=agent)), \
                patch.object(auth, "_authenticate_support_session", AsyncMock(side_effect=AssertionError)), \
                patch.object(auth, "enforce_api_quota", AsyncMock()):
            user = await auth.get_current_user(request, credentials)
        self.assertEqual(user["sub"], "agent")


def guarded_app(ctx):
    app = FastAPI()
    app.add_middleware(impersonation.ImpersonationGuardMiddleware)

    @app.get("/json")
    async def json_route(request: Request):
        request.state.impersonation = ctx
        return {"email": "ravi@gmail.com", "ward": "14"}

    @app.get("/csv")
    async def csv_route(request: Request):
        request.state.impersonation = ctx
        return Response("a,b", media_type="text/csv")

    return app


class GuardMiddlewareTests(unittest.TestCase):
    def test_masks_blocks_and_records(self):
        with patch.object(impersonation, "record_action", AsyncMock()) as record:
            client = TestClient(guarded_app(context()))
            self.assertEqual(client.get("/json").json(), {"email": "r***@gmail.com", "ward": "14"})
            self.assertEqual(client.get("/csv").status_code, 403)
        self.assertEqual(record.await_count, 2)

    def test_settings_off_pass_through(self):
        with patch.object(impersonation, "record_action", AsyncMock()) as record:
            client = TestClient(guarded_app(context(maskSensitive=False, downloadDisabled=False, recording=False)))
            self.assertEqual(client.get("/json").json()["email"], "ravi@gmail.com")
            self.assertEqual(client.get("/csv").status_code, 200)
        record.assert_not_awaited()


class PayloadTests(unittest.TestCase):
    POLICY = dict(policyName="ULB support", allowedSupportRoles=["AUDITOR"], allowedTenantLevels=["ULB"], maxSessionMinutes=30)

    def test_policy_rules(self):
        PolicyPayload(**self.POLICY, writeActionsAllowed=["PTX-P10:UPDATE"])
        for bad in (dict(writeActionsAllowed=["PTX-P10:MANAGE"]), dict(writeActionsAllowed=["anything"]), dict(allowedTenantLevels=["City"]),
                    dict(dualApproval=True, approvalRequired=False), dict(maxSessionMinutes=2), dict(maxSessionMinutes=600)):
            with self.assertRaises(ValidationError, msg=str(bad)):
                PolicyPayload(**{**self.POLICY, **bad})

    def test_request_rules(self):
        values = dict(targetUserId="t", targetTenantId="GWMC", requestType="Troubleshooting", businessJustification="Citizen cannot see the demand notice",
                      ticketReference="SUP-1", requestedMinutes=15, accessMode="Read Only")
        RequestPayload(**values)
        for bad in (dict(requestedMinutes=45), dict(accessMode="Admin"), dict(businessJustification="too short")):
            with self.assertRaises(ValidationError, msg=str(bad)):
                RequestPayload(**{**values, **bad})

    def test_rejection_needs_a_reason(self):
        with self.assertRaises(ValidationError):
            DecisionPayload(decision="Rejected")
        DecisionPayload(decision="Approved")


if __name__ == "__main__":
    unittest.main()
