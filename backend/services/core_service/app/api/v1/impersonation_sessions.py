"""ADM-R04 Tabs 3 and 5: starting, ending and auditing support sessions."""
import csv
import datetime
import io
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.cross_tenant_reviews import safe_cell
from app.api.v1.impersonation import HUB, SUPER_ADMIN, actor_email, get_request, hub_user, vault
from app.core import impersonation, impersonation_rules as rules
from app.core.auth import _authenticate, is_super_admin
from app.core.cross_tenant_history import client_ip
from app.core.security import CSRF_HEADER, SESSION_COOKIE
from app.db.models import ImpersonationAction, ImpersonationRequest, ImpersonationSession, User
from app.db.session import AsyncReadSessionLocal, AsyncWriteSessionLocal, get_read_db, get_write_db
from app.schemas.impersonation import ActionOut, AuditOut, CurrentSession, ReasonPayload, SessionOut
from app.schemas.tenant import ApiResponse
from app.schemas.white_label import PagedResponse

router = APIRouter(prefix="/impersonation", tags=["ADM-R04 Support Impersonation Hub"], dependencies=[Depends(hub_user)])
# The banner and its End button work from inside a session, where the hub itself is closed.
session_router = APIRouter(prefix="/impersonation/session", tags=["ADM-R04 Support Impersonation Hub"])

EXPORT_LIMIT = 5000
DEVICE_LENGTH = 255


def session_out(session: ImpersonationSession, request: ImpersonationRequest, now: Optional[datetime.datetime] = None) -> SessionOut:
    now = now or datetime.datetime.utcnow()
    # The worker records expiry within a minute. Requests stop honouring the session at once, so the list says so too.
    shown = rules.SESSION_EXPIRED if session.status == rules.SESSION_ACTIVE and session.expires_at <= now else session.status
    return SessionOut(
        id=session.id, session_number=rules.session_number(session.session_sequence), request_id=request.id, request_number=rules.request_number(request.request_sequence),
        support_email=session.support_email, target_email=session.target_email, target_name=request.target_name, tenant_id=session.tenant_id,
        access_mode=session.access_mode, status=shown, started_at=session.started_at, expires_at=session.expires_at, ended_at=session.ended_at,
        termination_reason=session.termination_reason, terminated_by=session.terminated_by,
    )


async def end_session(db: AsyncSession, session: ImpersonationSession, actor: str, reason: str, ip: Optional[str]) -> None:
    now = datetime.datetime.utcnow()
    session.status, session.ended_at, session.termination_reason, session.terminated_by = rules.SESSION_TERMINATED, now, reason, actor
    await vault(db, "SESSION_TERMINATED", actor, session.tenant_id, ip, {"sessionId": session.id, "agent": session.support_email,
                                                                       "target": session.target_email, "reason": reason})


@router.post("/requests/{request_id}/start", response_model=ApiResponse[SessionOut])
async def start_session(request_id: str, request: Request, response: Response, user: dict = HUB, db: AsyncSession = Depends(get_write_db)):
    row = await get_request(db, request_id)
    agent_id, now = str(user.get("sub") or ""), datetime.datetime.utcnow()
    if row.support_user_id != agent_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the support agent who asked can start this session.")
    if row.status != rules.REQ_APPROVED or (row.approval_valid_until and row.approval_valid_until < now):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only an approved request within its validity can be started.")
    if await db.scalar(select(ImpersonationSession.id).where(ImpersonationSession.support_user_id == agent_id,
                                                             ImpersonationSession.status == rules.SESSION_ACTIVE, ImpersonationSession.expires_at > now)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="End your current support session first.")
    agent = await db.scalar(select(User).where(User.id == agent_id))
    target = await db.scalar(select(User).where(User.id == row.target_user_id))
    if not agent or rules.role_code(agent.role) not in row.policy_snapshot.get("allowedSupportRoles", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role is no longer allowed by this request's policy.")
    if not target or not target.is_active or target.role == "super_admin":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This user can no longer be impersonated.")
    minutes = min(row.requested_minutes, int(row.policy_snapshot.get("maxSessionMinutes", row.requested_minutes)))
    session = ImpersonationSession(
        request_id=row.id, support_user_id=agent_id, support_email=row.support_email, target_user_id=row.target_user_id, target_email=row.target_email,
        tenant_id=row.target_tenant_id, access_mode=row.access_mode, status=rules.SESSION_ACTIVE, started_at=now,
        expires_at=now + datetime.timedelta(minutes=minutes), ip_address=client_ip(request), device=(request.headers.get("user-agent") or "")[:DEVICE_LENGTH] or None,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session, ["session_sequence"])
    row.status = rules.REQ_USED
    session.audit_event_id = await vault(db, "SESSION_STARTED", row.support_email, row.target_tenant_id, session.ip_address,
                                         {"sessionId": session.id, "request": rules.request_number(row.request_sequence), "target": row.target_email,
                                          "mode": row.access_mode, "expiresAt": session.expires_at.isoformat(), "device": session.device})
    await db.commit()
    impersonation.set_cookie(response, impersonation.issue_token(session), session.expires_at)
    return ApiResponse(data=session_out(session, row, now))


@router.get("/sessions", response_model=PagedResponse[SessionOut])
async def list_sessions(
    search: Optional[str] = Query(None), status_filter: Optional[str] = Query(None, alias="status"), skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100), user: dict = HUB, db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if not is_super_admin(user):
        conditions.append(ImpersonationSession.support_user_id == str(user.get("sub") or ""))
    now = datetime.datetime.utcnow()
    if status_filter == rules.SESSION_ACTIVE:
        conditions += [ImpersonationSession.status == rules.SESSION_ACTIVE, ImpersonationSession.expires_at > now]
    elif status_filter == rules.SESSION_EXPIRED:
        conditions.append(or_(ImpersonationSession.status == rules.SESSION_EXPIRED,
                              (ImpersonationSession.status == rules.SESSION_ACTIVE) & (ImpersonationSession.expires_at <= now)))
    elif status_filter:
        conditions.append(ImpersonationSession.status == status_filter)
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(ImpersonationSession.support_email.ilike(term), ImpersonationSession.target_email.ilike(term), ImpersonationSession.tenant_id.ilike(term)))
    joined = select(ImpersonationSession, ImpersonationRequest).join(ImpersonationRequest, ImpersonationSession.request_id == ImpersonationRequest.id).where(*conditions)
    total = await db.scalar(select(func.count()).select_from(joined.subquery())) or 0
    rows = (await db.execute(joined.order_by(ImpersonationSession.started_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[session_out(s, r, now) for s, r in rows], total=total)


@router.post("/sessions/{session_id}/terminate", response_model=ApiResponse[SessionOut])
async def terminate(session_id: str, payload: ReasonPayload, request: Request, response: Response, user: dict = HUB, db: AsyncSession = Depends(get_write_db)):
    row = (await db.execute(select(ImpersonationSession, ImpersonationRequest).join(ImpersonationRequest, ImpersonationSession.request_id == ImpersonationRequest.id)
                            .where(ImpersonationSession.id == session_id))).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session, req = row
    if not is_super_admin(user) and session.support_user_id != str(user.get("sub") or ""):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the agent or a super admin can end this session.")
    if session.status != rules.SESSION_ACTIVE or session.expires_at <= datetime.datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This session has already ended.")
    await end_session(db, session, actor_email(user), payload.reason.strip(), client_ip(request))
    await db.commit()
    return ApiResponse(data=session_out(session, req))


# ---------- the session banner ----------

async def _agent(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in first", headers={"WWW-Authenticate": "Bearer"})
    return await _authenticate(token)


@session_router.get("/current", response_model=ApiResponse[CurrentSession])
async def current_session(request: Request, response: Response):
    agent = await _agent(request)
    support_token = request.cookies.get(impersonation.IMPERSONATION_COOKIE)
    if not support_token:
        return ApiResponse(data=CurrentSession(active=False))
    async with AsyncReadSessionLocal() as db:
        try:
            session, req = await impersonation.load_session(db, support_token, str(agent.get("sub") or ""))
        except HTTPException:
            impersonation.clear_cookie(response)
            return ApiResponse(data=CurrentSession(active=False))
    return ApiResponse(data=CurrentSession(
        active=True, session_number=rules.session_number(session.session_sequence), target_name=req.target_name, target_email=session.target_email,
        tenant_id=session.tenant_id, access_mode=session.access_mode, expires_at=session.expires_at, agent_email=session.support_email,
    ))


@session_router.post("/current/end", response_model=ApiResponse[CurrentSession])
async def end_current_session(request: Request, response: Response):
    agent = await _agent(request)
    # Cookies arrive by themselves, so this change also needs a header other sites cannot set.
    if not request.headers.get(CSRF_HEADER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF header")
    impersonation.clear_cookie(response)
    support_token = request.cookies.get(impersonation.IMPERSONATION_COOKIE)
    if support_token:
        async with AsyncWriteSessionLocal() as db:
            try:
                session, _ = await impersonation.load_session(db, support_token, str(agent.get("sub") or ""))
            except HTTPException:
                return ApiResponse(data=CurrentSession(active=False))
            await end_session(db, session, session.support_email, "Ended by the support agent.", client_ip(request))
            await db.commit()
    return ApiResponse(data=CurrentSession(active=False))


# ---------- Tab 5: audit ----------

def approval_reference(req: ImpersonationRequest) -> str:
    number = rules.request_number(req.request_sequence)
    approvers = [a.approver_email for a in req.approvals if a.decision == "Approved"]
    if approvers:
        return f"{number} approved by {' and '.join(approvers)}"
    return f"{number} approved by policy {req.policy_snapshot.get('policyCode', '')}"


def _audit_conditions(search: Optional[str], date_from, date_to) -> list:
    conditions = []
    if date_from:
        conditions.append(ImpersonationSession.started_at >= date_from)
    if date_to:
        conditions.append(ImpersonationSession.started_at <= date_to)
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(ImpersonationSession.support_email.ilike(term), ImpersonationSession.target_email.ilike(term),
                              ImpersonationSession.tenant_id.ilike(term), ImpersonationSession.ip_address.ilike(term)))
    return conditions


async def _audit_rows(db: AsyncSession, conditions: list, skip: int, limit: int) -> List[AuditOut]:
    counts = select(ImpersonationAction.session_id, func.count(ImpersonationAction.id).label("n")).group_by(ImpersonationAction.session_id).subquery()
    statement = (select(ImpersonationSession, ImpersonationRequest, func.coalesce(counts.c.n, 0))
                 .join(ImpersonationRequest, ImpersonationSession.request_id == ImpersonationRequest.id)
                 .outerjoin(counts, counts.c.session_id == ImpersonationSession.id).where(*conditions)
                 .order_by(ImpersonationSession.started_at.desc()).offset(skip).limit(limit))
    now = datetime.datetime.utcnow()
    result = []
    for session, req, actions in (await db.execute(statement)).all():
        shown = session_out(session, req, now)
        result.append(AuditOut(
            session_id=session.id, session_number=shown.session_number, request_number=shown.request_number, support_email=session.support_email,
            target_email=session.target_email, tenant_id=session.tenant_id, status=shown.status, login_time=session.started_at,
            logout_time=session.ended_at or (session.expires_at if shown.status == rules.SESSION_EXPIRED else None), actions_performed=int(actions),
            ip_address=session.ip_address, device=session.device, approval_reference=approval_reference(req),
            termination_reason=session.termination_reason, audit_event_id=session.audit_event_id,
        ))
    return result


@router.get("/audit", response_model=PagedResponse[AuditOut])
async def list_audit(
    search: Optional[str] = Query(None), date_from: Optional[datetime.datetime] = Query(None), date_to: Optional[datetime.datetime] = Query(None),
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), user: dict = SUPER_ADMIN, db: AsyncSession = Depends(get_read_db),
):
    conditions = _audit_conditions(search, date_from, date_to)
    total = await db.scalar(select(func.count(ImpersonationSession.id)).where(*conditions)) or 0
    return PagedResponse(data=await _audit_rows(db, conditions, skip, limit), total=total)


@router.get("/audit/{session_id}/actions", response_model=PagedResponse[ActionOut])
async def list_actions(session_id: str, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), user: dict = SUPER_ADMIN, db: AsyncSession = Depends(get_read_db)):
    total = await db.scalar(select(func.count(ImpersonationAction.id)).where(ImpersonationAction.session_id == session_id)) or 0
    rows = (await db.scalars(select(ImpersonationAction).where(ImpersonationAction.session_id == session_id)
                             .order_by(ImpersonationAction.created_at).offset(skip).limit(limit))).all()
    return PagedResponse(data=[ActionOut.model_validate(r) for r in rows], total=total)


@router.get("/audit/export")
async def export_audit(
    search: Optional[str] = Query(None), date_from: Optional[datetime.datetime] = Query(None), date_to: Optional[datetime.datetime] = Query(None),
    user: dict = SUPER_ADMIN, db: AsyncSession = Depends(get_read_db),
):
    rows = await _audit_rows(db, _audit_conditions(search, date_from, date_to), 0, EXPORT_LIMIT)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Request ID", "Support Agent", "Target User", "Tenant", "Session ID", "Login Time (UTC)", "Logout Time (UTC)", "Actions Performed",
                     "IP Address", "Device Information", "Approval Reference", "Termination Reason", "Audit Event ID"])
    for r in rows:
        writer.writerow([safe_cell(v) for v in (r.request_number, r.support_email, r.target_email, r.tenant_id, r.session_number, r.login_time.isoformat(),
                                                 r.logout_time.isoformat() if r.logout_time else "", r.actions_performed, r.ip_address, r.device,
                                                 r.approval_reference, r.termination_reason, r.audit_event_id)])
    return Response(content=buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="impersonation-audit.csv"'})
