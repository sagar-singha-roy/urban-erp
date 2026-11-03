"""ADM-R04 Tabs 1, 2 and 4: impersonation policies, requests and their approval."""
import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.audit_vault import record_immutable_audit_event
from app.core import impersonation_rules as rules
from app.core.auth import get_current_user, is_super_admin
from app.core.config import PLATFORM_ULB_TYPE
from app.core.cross_tenant_history import client_ip
from app.db.models import (
    ComponentModel, GlobalUserProfile, ImpersonationApproval, ImpersonationPolicy, ImpersonationRequest, RoleModel, StateTenant, Tenant, User,
)
from app.db.session import get_read_db, get_write_db
from app.schemas.impersonation import (
    WRITE_ACTIONS, ApprovalOut, ApproverOption, DecisionPayload, HubProfile, ImpersonationOptions, PolicyOut, PolicyPayload, RequestOut,
    RequestPayload, RoleOption, TargetOption,
)
from app.schemas.tenant import ApiResponse
from app.schemas.white_label import PagedResponse

LOOKUP_LIMIT = 50
AUDIT_CATEGORY = "Authentication"


def roles_of(user: dict) -> List[str]:
    return user.get("realm_access", {}).get("roles", [])


async def active_policies(db: AsyncSession) -> List[ImpersonationPolicy]:
    return list((await db.scalars(select(ImpersonationPolicy).where(ImpersonationPolicy.is_active.is_(True)))).all())


def can_request(user: dict, policies: List[ImpersonationPolicy]) -> bool:
    codes = {rules.role_code(r) for r in roles_of(user)}
    return any(codes & set(p.allowed_support_roles) for p in policies)


async def hub_user(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_read_db)) -> dict:
    """Super admins, and support staff whose role an active policy allows."""
    if is_super_admin(user) or can_request(user, await active_policies(db)):
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot use support impersonation.")


def require_super_admin(user: dict = Depends(hub_user)) -> dict:
    if not is_super_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only platform super admins can do this.")
    return user


router = APIRouter(prefix="/impersonation", tags=["ADM-R04 Support Impersonation Hub"], dependencies=[Depends(hub_user)])
HUB = Depends(hub_user)
SUPER_ADMIN = Depends(require_super_admin)


def actor_email(user: dict) -> str:
    return str(user.get("email") or user.get("preferred_username") or "").strip().lower()


async def vault(db: AsyncSession, action: str, actor: str, tenant_id: Optional[str], ip: Optional[str], details: Dict, severity: str = "High") -> str:
    event = await record_immutable_audit_event(db, event_category=AUDIT_CATEGORY, action=f"IMPERSONATION_{action}", actor_id=actor or "unknown",
                                               actor_role="Support Impersonation", tenant_id=tenant_id, severity=severity,
                                               ip_address=ip or "unknown", details=details)
    return event.event_id


def request_out(row: ImpersonationRequest) -> RequestOut:
    skipped = ("policy_snapshot", "policy_id", "request_sequence", "second_approver_id")
    values = {c.name: getattr(row, c.name) for c in ImpersonationRequest.__table__.columns if c.name not in skipped}
    return RequestOut(**values, request_number=rules.request_number(row.request_sequence), policy_code=row.policy_snapshot.get("policyCode", ""),
                      approvals=[ApprovalOut.model_validate(a) for a in row.approvals])


async def get_request(db: AsyncSession, request_id: str) -> ImpersonationRequest:
    row = await db.scalar(select(ImpersonationRequest).where(ImpersonationRequest.id == request_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return row


# ---------- options and lookups ----------

@router.get("/options", response_model=ApiResponse[ImpersonationOptions])
async def get_options(db: AsyncSession = Depends(get_read_db)):
    roles = (await db.execute(select(RoleModel.code, RoleModel.name).where(RoleModel.status == "Active").order_by(RoleModel.name))).all()
    return ApiResponse(data=ImpersonationOptions(
        request_types=rules.REQUEST_TYPES, durations=rules.DURATIONS, access_modes=rules.ACCESS_MODES, tenant_levels=rules.TENANT_LEVELS,
        request_statuses=rules.REQUEST_STATUSES, session_statuses=rules.SESSION_STATUSES, roles=[RoleOption(code=c, name=n) for c, n in roles],
        write_action_types=WRITE_ACTIONS, sensitive_field_parts=list(rules.SENSITIVE_FIELD_PARTS),
        max_approval_hours=int(rules.MAX_APPROVAL_VALIDITY.total_seconds() // 3600),
    ))


@router.get("/me", response_model=ApiResponse[HubProfile])
async def get_me(user: dict = HUB, db: AsyncSession = Depends(get_read_db)):
    row = await db.scalar(select(User).where(User.id == str(user.get("sub") or "")))
    role = (roles_of(user) or [""])[0]
    return ApiResponse(data=HubProfile(user_id=str(user.get("sub") or ""), email=actor_email(user), full_name=row.full_name if row else actor_email(user),
                                       role_code=rules.role_code(role), is_super_admin=is_super_admin(user), can_request=can_request(user, await active_policies(db))))


def user_tenants(user: User, profile: Optional[GlobalUserProfile]) -> List[str]:
    values = [user.tenant_id]
    if profile:
        values += [v.strip() for v in f"{profile.state_tenant_id or ''},{profile.ulb_tenant_id or ''}".split(",")]
    return list(dict.fromkeys(v for v in values if v))


@router.get("/lookups/targets", response_model=ApiResponse[List[TargetOption]])
async def lookup_targets(search: Optional[str] = Query(None), user: dict = HUB, db: AsyncSession = Depends(get_read_db)):
    statement = (select(User).where(User.is_active.is_(True), User.role != "super_admin", User.id != str(user.get("sub") or ""))
                 .order_by(User.full_name).limit(LOOKUP_LIMIT))
    if search and search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(or_(User.full_name.ilike(term), User.email.ilike(term), User.username.ilike(term)))
    users = (await db.scalars(statement)).all()
    emails = [u.email.lower() for u in users]
    profiles = {p.email.lower(): p for p in (await db.scalars(select(GlobalUserProfile).where(func.lower(GlobalUserProfile.email).in_(emails)))).all()}
    return ApiResponse(data=[TargetOption(id=u.id, full_name=u.full_name, email=u.email, role=u.role, tenant_ids=user_tenants(u, profiles.get(u.email.lower())))
                             for u in users])


@router.get("/lookups/approvers", response_model=ApiResponse[List[ApproverOption]])
async def lookup_approvers(user: dict = SUPER_ADMIN, db: AsyncSession = Depends(get_read_db)):
    rows = await db.scalars(select(User).where(User.role == "super_admin", User.is_active.is_(True), User.id != str(user.get("sub") or "")).order_by(User.full_name))
    return ApiResponse(data=[ApproverOption(id=u.id, full_name=u.full_name, email=u.email) for u in rows.all()])


# ---------- Tab 4: policies ----------

def policy_out(row: ImpersonationPolicy) -> PolicyOut:
    values = {c.name: getattr(row, c.name) for c in ImpersonationPolicy.__table__.columns if c.name not in ("policy_sequence", "created_at")}
    return PolicyOut(**values, policy_code=rules.policy_code(row.policy_sequence))


@router.get("/policies", response_model=PagedResponse[PolicyOut])
async def list_policies(
    search: Optional[str] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    user: dict = SUPER_ADMIN, db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if search and search.strip():
        conditions.append(ImpersonationPolicy.policy_name.ilike(f"%{search.strip()}%"))
    total = await db.scalar(select(func.count(ImpersonationPolicy.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(ImpersonationPolicy).where(*conditions).order_by(ImpersonationPolicy.updated_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[policy_out(r) for r in rows], total=total)


async def _check_policy(db: AsyncSession, payload: PolicyPayload, keep_id: Optional[str]) -> None:
    known = set((await db.scalars(select(RoleModel.code).where(RoleModel.code.in_(payload.allowed_support_roles)))).all())
    if known != set(payload.allowed_support_roles):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose support roles from the roles list.")
    components = {a.split(":")[0] for a in payload.write_actions_allowed}
    if components:
        found = set((await db.scalars(select(ComponentModel.code).where(ComponentModel.code.in_(components)))).all())
        if found != components:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Write actions must name components in the catalogue.")
    if not payload.is_active:
        return
    # Requests pick their policy by tenant level, so two active policies cannot share one.
    for other in await active_policies(db):
        overlap = set(other.allowed_tenant_levels) & set(payload.allowed_tenant_levels)
        if other.id != keep_id and overlap:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"{rules.policy_code(other.policy_sequence)} already covers {', '.join(sorted(overlap))}. Turn it off or remove that level first.")


@router.post("/policies", response_model=ApiResponse[PolicyOut], status_code=status.HTTP_201_CREATED)
async def create_policy(payload: PolicyPayload, request: Request, user: dict = SUPER_ADMIN, db: AsyncSession = Depends(get_write_db)):
    await _check_policy(db, payload, None)
    row = ImpersonationPolicy(**payload.model_dump(), updated_by=actor_email(user))
    db.add(row)
    await db.flush()
    await db.refresh(row, ["policy_sequence"])
    await vault(db, "POLICY_SAVED", actor_email(user), None, client_ip(request), {"policy": rules.policy_code(row.policy_sequence), **payload.model_dump()}, "Medium")
    await db.commit()
    return ApiResponse(data=policy_out(row))


@router.put("/policies/{policy_id}", response_model=ApiResponse[PolicyOut])
async def update_policy(policy_id: str, payload: PolicyPayload, request: Request, user: dict = SUPER_ADMIN, db: AsyncSession = Depends(get_write_db)):
    row = await db.scalar(select(ImpersonationPolicy).where(ImpersonationPolicy.id == policy_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    await _check_policy(db, payload, row.id)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    row.updated_by = actor_email(user)
    await vault(db, "POLICY_SAVED", actor_email(user), None, client_ip(request), {"policy": rules.policy_code(row.policy_sequence), **payload.model_dump()}, "Medium")
    await db.commit()
    return ApiResponse(data=policy_out(row))


# ---------- Tab 1: requests ----------

@router.get("/requests", response_model=PagedResponse[RequestOut])
async def list_requests(
    search: Optional[str] = Query(None), status_filter: Optional[str] = Query(None, alias="status"), skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100), user: dict = HUB, db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    # Support staff see their own requests. Super admins see everyone's.
    if not is_super_admin(user):
        conditions.append(ImpersonationRequest.support_user_id == str(user.get("sub") or ""))
    if status_filter:
        conditions.append(ImpersonationRequest.status == status_filter)
    if search and search.strip():
        term = f"%{search.strip()}%"
        matches = [ImpersonationRequest.support_email.ilike(term), ImpersonationRequest.target_email.ilike(term), ImpersonationRequest.target_name.ilike(term),
                   ImpersonationRequest.ticket_reference.ilike(term), ImpersonationRequest.target_tenant_id.ilike(term)]
        digits = search.strip().upper().removeprefix("IMP-")
        if digits.isdigit():
            matches.append(ImpersonationRequest.request_sequence == int(digits))
        conditions.append(or_(*matches))
    total = await db.scalar(select(func.count(ImpersonationRequest.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(ImpersonationRequest).where(*conditions).order_by(ImpersonationRequest.requested_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[request_out(r) for r in rows], total=total)


async def tenant_level(db: AsyncSession, tenant_id: str) -> Optional[str]:
    tenant = await db.scalar(select(Tenant).where(Tenant.tenant_id == tenant_id))
    if tenant:
        return "Platform" if tenant.ulb_type == PLATFORM_ULB_TYPE else "ULB"
    state = await db.scalar(select(StateTenant.id).where(or_(StateTenant.tenant_id == tenant_id, StateTenant.state_code == tenant_id)))
    return "State" if state else None


def snapshot(policy: ImpersonationPolicy) -> Dict:
    return {
        "policyCode": rules.policy_code(policy.policy_sequence), "allowedSupportRoles": policy.allowed_support_roles, "maxSessionMinutes": policy.max_session_minutes,
        "approvalRequired": policy.approval_required, "dualApproval": policy.dual_approval, "maskSensitiveData": policy.mask_sensitive_data,
        "downloadDisabled": policy.download_disabled, "writeActionsAllowed": policy.write_actions_allowed, "sessionRecording": policy.session_recording,
    }


@router.post("/requests", response_model=ApiResponse[RequestOut], status_code=status.HTTP_201_CREATED)
async def create_request(payload: RequestPayload, request: Request, user: dict = HUB, db: AsyncSession = Depends(get_write_db)):
    agent = await db.scalar(select(User).where(User.id == str(user.get("sub") or "")))
    target = await db.scalar(select(User).where(User.id == payload.target_user_id))
    if not agent or not target or not target.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Select an active user.")
    if target.id == agent.id or target.role == "super_admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Super admins and your own account cannot be impersonated.")
    profile = await db.scalar(select(GlobalUserProfile).where(func.lower(GlobalUserProfile.email) == target.email.lower()))
    if payload.target_tenant_id not in user_tenants(target, profile):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose one of this user's own tenants.")
    level = await tenant_level(db, payload.target_tenant_id)
    policy = next((p for p in await active_policies(db) if level in p.allowed_tenant_levels), None)
    if not level or not policy:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No active impersonation policy covers this tenant level.")
    if rules.role_code(agent.role) not in policy.allowed_support_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{rules.policy_code(policy.policy_sequence)} does not allow your role to impersonate here.")
    if payload.requested_minutes > policy.max_session_minutes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"The policy allows at most {policy.max_session_minutes} minutes.")
    if payload.access_mode == rules.MODE_RESTRICTED and not policy.write_actions_allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The policy allows no write actions, so request Read Only.")
    now = datetime.datetime.utcnow()
    row = ImpersonationRequest(
        **payload.model_dump(), policy_id=policy.id, policy_snapshot=snapshot(policy), support_user_id=agent.id, support_email=agent.email.lower(),
        support_name=agent.full_name, target_email=target.email.lower(), target_name=target.full_name, target_tenant_level=level,
        status=rules.REQ_PENDING, dual_approval_required=policy.dual_approval, requested_at=now, approvals=[],
    )
    if not policy.approval_required:
        row.status, row.decided_at, row.approval_valid_until = rules.REQ_APPROVED, now, now + rules.DEFAULT_APPROVAL_VALIDITY
    db.add(row)
    await db.flush()
    await db.refresh(row, ["request_sequence"])
    await vault(db, "REQUESTED", agent.email, payload.target_tenant_id, client_ip(request),
                {"request": rules.request_number(row.request_sequence), "target": row.target_email, "type": row.request_type, "ticket": row.ticket_reference,
                 "minutes": row.requested_minutes, "mode": row.access_mode, "autoApproved": not policy.approval_required})
    await db.commit()
    return ApiResponse(data=request_out(row))


@router.post("/requests/{request_id}/cancel", response_model=ApiResponse[RequestOut])
async def cancel_request(request_id: str, request: Request, user: dict = HUB, db: AsyncSession = Depends(get_write_db)):
    row = await get_request(db, request_id)
    if row.support_user_id != str(user.get("sub") or "") and not is_super_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the requester can cancel this request.")
    if row.status not in (rules.REQ_PENDING, rules.REQ_SECOND, rules.REQ_APPROVED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A {row.status.lower()} request cannot be cancelled.")
    row.status = rules.REQ_CANCELLED
    await vault(db, "REQUEST_CANCELLED", actor_email(user), row.target_tenant_id, client_ip(request), {"request": rules.request_number(row.request_sequence)}, "Medium")
    await db.commit()
    return ApiResponse(data=request_out(row))


# ---------- Tab 2: approvals ----------

def approval_window(payload: DecisionPayload, now: datetime.datetime) -> datetime.datetime:
    until = payload.approval_valid_until or now + rules.DEFAULT_APPROVAL_VALIDITY
    if until <= now or until > now + rules.MAX_APPROVAL_VALIDITY:
        hours = int(rules.MAX_APPROVAL_VALIDITY.total_seconds() // 3600)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Approval Validity must be within the next {hours} hours.")
    return until


@router.post("/requests/{request_id}/decision", response_model=ApiResponse[RequestOut])
async def decide(request_id: str, payload: DecisionPayload, request: Request, user: dict = SUPER_ADMIN, db: AsyncSession = Depends(get_write_db)):
    row = await get_request(db, request_id)
    approver_id, approver = str(user.get("sub") or ""), actor_email(user)
    now = datetime.datetime.utcnow()
    if approver_id == row.support_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot approve your own request.")
    if row.status == rules.REQ_PENDING:
        stage = 1
    elif row.status == rules.REQ_SECOND:
        stage = 2
        if approver_id != row.second_approver_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the named second approver can decide now.")
    else:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A {row.status.lower()} request has no decision to make.")
    validity = approval_window(payload, now) if payload.decision == "Approved" else None
    if payload.decision == "Rejected":
        row.status, row.decided_at = rules.REQ_REJECTED, now
    elif stage == 1 and (row.dual_approval_required or payload.dual_approval_required):
        second = await db.scalar(select(User).where(User.id == (payload.second_approver_id or ""), User.role == "super_admin", User.is_active.is_(True)))
        if not second or second.id in (approver_id, row.support_user_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name a second approver: another active super admin who is not the requester.")
        row.dual_approval_required, row.second_approver_id, row.second_approver_email = True, second.id, second.email.lower()
        row.status, row.approval_valid_until = rules.REQ_SECOND, validity
    else:
        # The second approver can shorten the window, never extend it.
        row.approval_valid_until = min(v for v in (row.approval_valid_until, validity) if v)
        row.status, row.decided_at = rules.REQ_APPROVED, now
    row.approvals.append(ImpersonationApproval(stage=stage, approver_id=approver_id, approver_email=approver, decision=payload.decision,
                                               comments=(payload.comments or "").strip() or None, decided_at=now))
    await vault(db, f"STAGE_{stage}_{payload.decision.upper()}", approver, row.target_tenant_id, client_ip(request),
                {"request": rules.request_number(row.request_sequence), "status": row.status, "secondApprover": row.second_approver_email,
                 "validUntil": row.approval_valid_until.isoformat() if row.approval_valid_until else None, "comments": payload.comments})
    await db.commit()
    return ApiResponse(data=request_out(row))
