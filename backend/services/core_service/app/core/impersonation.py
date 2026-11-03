"""ADM-R04 support sessions: a separate short-lived token, checked against the database on every request.

The support agent never receives the target user's credentials. The session token names the agent as the
actor, and it only works next to the agent's own sign-in cookie.
"""
import datetime
import json
import logging
from typing import Optional, Tuple

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core import impersonation_rules as rules
from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.db.models import ImpersonationAction, ImpersonationRequest, ImpersonationSession
from app.db.session import AsyncWriteSessionLocal

logger = logging.getLogger(__name__)

IMPERSONATION_COOKIE = "urban_impersonation"
API = settings.API_V1_STR
AUTHORIZE_PATH = f"{API}/auth/authorize"
# A session can read its own profile and module list, and module services can ask for decisions. Nothing else under these.
ALLOWED_PATHS = {f"{API}/auth/me", f"{API}/auth/modules", AUTHORIZE_PATH}
BLOCKED_PREFIXES = (f"{API}/auth/", f"{API}/iam", f"{API}/impersonation")
ENDED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This support session has ended.", headers={"WWW-Authenticate": "Bearer"})


def issue_token(session: ImpersonationSession) -> str:
    lifetime = session.expires_at - datetime.datetime.utcnow()
    return create_access_token({
        "typ": rules.TOKEN_TYPE, "sub": session.target_user_id, "sid": session.id,
        "act": {"sub": session.support_user_id, "email": session.support_email},
    }, expires_delta=lifetime)


def set_cookie(response: Response, token: str, expires_at: datetime.datetime) -> None:
    seconds = max(int((expires_at - datetime.datetime.utcnow()).total_seconds()), 1)
    response.set_cookie(IMPERSONATION_COOKIE, token, max_age=seconds, httponly=True, secure=not settings.is_development, samesite="lax", path="/")


def clear_cookie(response: Response) -> None:
    response.delete_cookie(IMPERSONATION_COOKIE, path="/", secure=not settings.is_development, httponly=True, samesite="lax")


async def load_session(db: AsyncSession, token: Optional[str], agent_id: str, now: Optional[datetime.datetime] = None) -> Tuple[ImpersonationSession, ImpersonationRequest]:
    """The live session behind a token. The token must be a session token issued to this signed-in agent."""
    payload = decode_access_token(token or "") or {}
    actor = payload.get("act") or {}
    if payload.get("typ") != rules.TOKEN_TYPE or str(actor.get("sub")) != str(agent_id):
        raise ENDED
    row = (await db.execute(
        select(ImpersonationSession, ImpersonationRequest)
        .join(ImpersonationRequest, ImpersonationSession.request_id == ImpersonationRequest.id)
        .where(ImpersonationSession.id == str(payload.get("sid") or ""))
    )).first()
    now = now or datetime.datetime.utcnow()
    if not row:
        raise ENDED
    session, request = row
    if (session.status != rules.SESSION_ACTIVE or session.expires_at <= now or session.support_user_id != str(agent_id)
            or session.target_user_id != str(payload.get("sub"))):
        raise ENDED
    return session, request


def session_context(session: ImpersonationSession, request: ImpersonationRequest) -> dict:
    policy = request.policy_snapshot or {}
    return {
        "sessionId": session.id, "sessionNumber": rules.session_number(session.session_sequence), "agentEmail": session.support_email,
        "agentId": session.support_user_id, "mode": session.access_mode, "expiresAt": session.expires_at.isoformat(),
        "writeActions": list(policy.get("writeActionsAllowed") or []), "maskSensitive": bool(policy.get("maskSensitiveData", True)),
        "downloadDisabled": bool(policy.get("downloadDisabled", True)), "recording": bool(policy.get("sessionRecording", True)),
    }


def enforce_path(request: Request, context: dict) -> None:
    """Sessions read records and use module actions the policy allows. Account, admin and hub routes stay closed."""
    request.state.impersonation = context
    path = request.url.path
    if path not in ALLOWED_PATHS and path.startswith(BLOCKED_PREFIXES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This is not available during a support session.")
    if request.method not in rules.READ_METHODS and path != AUTHORIZE_PATH:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A support session cannot change records here.")


def check_action(request, context: dict, component_code: str, action: str) -> None:
    permission = f"{component_code}:{action.upper()}"
    if request is not None:
        request.state.impersonation_permission = permission
    if not rules.action_permitted(context["mode"], context["writeActions"], context["downloadDisabled"], component_code, action):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"This support session does not allow {permission}.")


async def record_action(session_id: str, method: str, path: str, permission: Optional[str], status_code: int) -> None:
    try:
        async with AsyncWriteSessionLocal() as db:
            db.add(ImpersonationAction(session_id=session_id, method=method[:10], path=path[:500], permission=permission, status_code=status_code))
            await db.commit()
    except Exception as exc:
        # Losing an activity row must not break the request, but it is reported.
        logger.error("Support session activity was not recorded: %s", type(exc).__name__)


class ImpersonationGuardMiddleware(BaseHTTPMiddleware):
    """Masks personal data, refuses downloads and records activity for requests made in a support session."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        context = getattr(request.state, "impersonation", None)
        if not context:
            return response
        if context["downloadDisabled"] and rules.is_download(response.headers.get("content-type"), response.headers.get("content-disposition")):
            response = JSONResponse({"detail": "Downloads are turned off during support sessions."}, status_code=status.HTTP_403_FORBIDDEN)
        elif context["maskSensitive"] and (response.headers.get("content-type") or "").startswith("application/json"):
            body = b"".join([chunk async for chunk in response.body_iterator])
            try:
                body = json.dumps(rules.mask_payload(json.loads(body))).encode("utf-8")
            except ValueError:
                pass
            headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
            response = Response(content=body, status_code=response.status_code, headers=headers, media_type="application/json")
        if context["recording"]:
            await record_action(context["sessionId"], request.method, request.url.path, getattr(request.state, "impersonation_permission", None), response.status_code)
        return response
