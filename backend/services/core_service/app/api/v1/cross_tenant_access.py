"""ADM-R02 Tabs 1 and 2: cross-tenant grants, their approval, and their scope."""
import datetime
from typing import List, Optional, Set

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.white_label import tenant_exists
from app.core import cross_tenant_rules as rules
from app.core.auth import _tenant_identifiers, require_roles
from app.core.cross_tenant_history import client_ip, record_change
from app.db.models import (
    AccessReviewItem, ComponentModel, CrossTenantAccessGrant, CrossTenantAccessScope, CrossTenantGrantTarget, GlobalUserProfile,
    ModuleModel, StateTenant, Tenant, TenantDepartment, User, Ward, Zone,
)
from app.db.session import get_read_db, get_write_db
from app.schemas.cross_tenant import (
    AreaOption, ComponentOption, CrossTenantOptions, DepartmentOut, DepartmentPayload, GrantDecision, GrantOut, GrantPayload, ModuleOption,
    ScopeOut, ScopePayload, UserOption,
)
from app.schemas.tenant import ApiResponse
from app.schemas.white_label import PagedResponse

SUPER_ADMIN = Depends(require_roles(["super_admin"]))
router = APIRouter(prefix="/iam/cross-tenant", tags=["ADM-R02 Cross-Tenant Access Management"], dependencies=[SUPER_ADMIN])

LOOKUP_LIMIT = 50


def actor_of(user: dict) -> str:
    """Approvals compare people, so this is the signed-in user's email rather than a display name."""
    return str(user.get("email") or user.get("preferred_username") or "").strip().lower()[:150]


def full_name(profile: GlobalUserProfile) -> str:
    return " ".join(p for p in (profile.first_name, profile.middle_name, profile.last_name) if p)


def grant_out(grant: CrossTenantAccessGrant) -> GrantOut:
    values = {column.name: getattr(grant, column.name) for column in CrossTenantAccessGrant.__table__.columns}
    return GrantOut(**values, record_number=rules.record_number(grant.record_sequence),
                    target_tenant_ids=[t.target_tenant_id for t in grant.targets], has_scope=grant.scope is not None)


async def get_grant(db: AsyncSession, grant_id: str) -> CrossTenantAccessGrant:
    grant = await db.scalar(select(CrossTenantAccessGrant).where(CrossTenantAccessGrant.id == grant_id))
    if not grant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access record not found")
    return grant


async def revoke_grant(db: AsyncSession, grant: CrossTenantAccessGrant, actor: str, ip: Optional[str], reason: str, action: str = "REVOKED") -> None:
    if grant.status in rules.CLOSED_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"This access is already {grant.status.lower()}.")
    grant.status, grant.revoked_by, grant.revoked_at, grant.revoke_reason = rules.STATUS_REVOKED, actor, datetime.datetime.utcnow(), reason
    await record_change(db, grant, action, actor, ip, reason=reason, previous_level=grant.access_level)


async def _is_state(db: AsyncSession, tenant_id: str) -> bool:
    upper = tenant_id.upper()
    return bool(await db.scalar(select(StateTenant.id).where(or_(func.upper(StateTenant.tenant_id) == upper, func.upper(StateTenant.state_code) == upper))))


async def _platform_admin_emails(db: AsyncSession) -> Set[str]:
    rows = await db.scalars(select(User.email).where(User.role == "super_admin", User.is_active.is_(True)))
    return {email.lower() for email in rows.all()}


# ---------- options and lookups ----------

@router.get("/options", response_model=ApiResponse[CrossTenantOptions])
async def get_options(db: AsyncSession = Depends(get_read_db)):
    modules = (await db.execute(select(ModuleModel.code, ModuleModel.name).order_by(ModuleModel.code))).all()
    return ApiResponse(data=CrossTenantOptions(
        user_types=rules.USER_TYPES, access_levels=rules.ACCESS_LEVELS, access_statuses=rules.ACCESS_STATUSES, scope_levels=rules.SCOPE_LEVELS,
        scope_modes=rules.SCOPE_MODES, actions=rules.ACTIONS, data_scopes=rules.DATA_SCOPES, access_decisions=rules.ACCESS_DECISIONS,
        review_statuses=rules.REVIEW_STATUSES, review_decisions=rules.REVIEW_DECISIONS,
        modules=[ModuleOption(code=code, name=name) for code, name in modules],
    ))


def _user_option(profile: GlobalUserProfile) -> UserOption:
    return UserOption(id=profile.id, full_name=full_name(profile), email=profile.email, user_type=rules.PROFILE_USER_TYPES.get(profile.user_type),
                      home_tenant_id=profile.ulb_tenant_id or profile.state_tenant_id)


def _profile_search(search: Optional[str]):
    statement = select(GlobalUserProfile).where(GlobalUserProfile.account_status == "Active").order_by(GlobalUserProfile.first_name).limit(LOOKUP_LIMIT)
    if search and search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(or_(GlobalUserProfile.first_name.ilike(term), GlobalUserProfile.last_name.ilike(term), GlobalUserProfile.email.ilike(term)))
    return statement


@router.get("/lookups/users", response_model=ApiResponse[List[UserOption]])
async def lookup_users(search: Optional[str] = Query(None), db: AsyncSession = Depends(get_read_db)):
    admins = await _platform_admin_emails(db)
    rows = (await db.scalars(_profile_search(search))).all()
    return ApiResponse(data=[_user_option(p) for p in rows if p.email.lower() not in admins])


@router.get("/lookups/authorities", response_model=ApiResponse[List[UserOption]])
async def lookup_authorities(search: Optional[str] = Query(None), db: AsyncSession = Depends(get_read_db)):
    """Only platform super admins can open this page, so only they can approve."""
    admins = await _platform_admin_emails(db)
    rows = (await db.scalars(_profile_search(search).where(func.lower(GlobalUserProfile.email).in_(admins)))).all()
    return ApiResponse(data=[_user_option(p) for p in rows])


@router.get("/lookups/components", response_model=ApiResponse[List[ComponentOption]])
async def lookup_components(module: List[str] = Query([]), db: AsyncSession = Depends(get_read_db)):
    statement = select(ComponentModel).order_by(ComponentModel.parent_module_code, ComponentModel.display_order)
    if module:
        statement = statement.where(ComponentModel.parent_module_code.in_(module))
    rows = (await db.scalars(statement)).all()
    return ApiResponse(data=[ComponentOption(code=c.code, name=c.name, module_code=c.parent_module_code) for c in rows])


@router.get("/lookups/zones", response_model=ApiResponse[List[AreaOption]])
async def lookup_zones(tenant_id: List[str] = Query([]), db: AsyncSession = Depends(get_read_db)):
    if not tenant_id:
        return ApiResponse(data=[])
    rows = (await db.scalars(select(Zone).where(Zone.tenant_id.in_(tenant_id)).order_by(Zone.tenant_id, Zone.name))).all()
    return ApiResponse(data=[AreaOption(id=z.id, name=f"{z.name} ({z.code})", tenant_id=z.tenant_id) for z in rows])


@router.get("/lookups/wards", response_model=ApiResponse[List[AreaOption]])
async def lookup_wards(tenant_id: List[str] = Query([]), zone_id: List[str] = Query([]), db: AsyncSession = Depends(get_read_db)):
    if not tenant_id:
        return ApiResponse(data=[])
    statement = select(Ward).where(Ward.tenant_id.in_(tenant_id)).order_by(Ward.tenant_id, Ward.ward_number)
    if zone_id:
        statement = statement.where(Ward.zone_id.in_(zone_id))
    rows = (await db.scalars(statement)).all()
    return ApiResponse(data=[AreaOption(id=w.id, name=f"Ward {w.ward_number} - {w.ward_name}", tenant_id=w.tenant_id, zone_id=w.zone_id) for w in rows])


@router.get("/departments", response_model=ApiResponse[List[DepartmentOut]])
async def list_departments(tenant_id: List[str] = Query([]), db: AsyncSession = Depends(get_read_db)):
    if not tenant_id:
        return ApiResponse(data=[])
    rows = (await db.scalars(select(TenantDepartment).where(TenantDepartment.tenant_id.in_(tenant_id), TenantDepartment.is_active.is_(True)).order_by(TenantDepartment.name))).all()
    return ApiResponse(data=[DepartmentOut.model_validate(d) for d in rows])


@router.post("/departments", response_model=ApiResponse[DepartmentOut], status_code=status.HTTP_201_CREATED)
async def create_department(payload: DepartmentPayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    if not await tenant_exists(db, payload.tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    row = TenantDepartment(tenant_id=payload.tenant_id, code=payload.code.strip().upper(), name=payload.name.strip(), created_by=actor_of(user))
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This tenant already has a department with that code.")
    return ApiResponse(data=DepartmentOut.model_validate(row))


# ---------- Tab 1: access directory ----------

def _record_sequence(search: str) -> Optional[int]:
    digits = search.upper().removeprefix("XTA-")
    return int(digits) if digits.isdigit() else None


@router.get("/grants", response_model=PagedResponse[GrantOut])
async def list_grants(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    access_level: Optional[str] = Query(None),
    user_type: Optional[str] = Query(None),
    user_profile_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    for column, value in ((CrossTenantAccessGrant.status, status_filter), (CrossTenantAccessGrant.access_level, access_level),
                          (CrossTenantAccessGrant.user_type, user_type), (CrossTenantAccessGrant.user_profile_id, user_profile_id)):
        if value:
            conditions.append(column == value)
    if search and search.strip():
        term = f"%{search.strip()}%"
        matches = [CrossTenantAccessGrant.user_name.ilike(term), CrossTenantAccessGrant.user_email.ilike(term), CrossTenantAccessGrant.home_tenant_id.ilike(term),
                   CrossTenantAccessGrant.id.in_(select(CrossTenantGrantTarget.grant_id).where(CrossTenantGrantTarget.target_tenant_id.ilike(term)))]
        sequence = _record_sequence(search.strip())
        if sequence is not None:
            matches.append(CrossTenantAccessGrant.record_sequence == sequence)
        conditions.append(or_(*matches))
    total = await db.scalar(select(func.count(CrossTenantAccessGrant.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(CrossTenantAccessGrant).where(*conditions).order_by(CrossTenantAccessGrant.created_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[grant_out(g) for g in rows], total=total)


@router.get("/grants/{grant_id}", response_model=ApiResponse[GrantOut])
async def get_grant_detail(grant_id: str, db: AsyncSession = Depends(get_read_db)):
    return ApiResponse(data=grant_out(await get_grant(db, grant_id)))


async def _check_grant(db: AsyncSession, payload: GrantPayload, actor: str) -> tuple:
    profile = await db.scalar(select(GlobalUserProfile).where(GlobalUserProfile.id == payload.user_profile_id))
    if not profile or profile.account_status != "Active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Select an active user.")
    admins = await _platform_admin_emails(db)
    if profile.email.lower() in admins:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Platform super admins already reach every tenant.")
    authority = await db.scalar(select(GlobalUserProfile).where(GlobalUserProfile.id == payload.approval_authority_id))
    if not authority or authority.account_status != "Active" or authority.email.lower() not in admins:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The approval authority must be an active platform super admin.")
    if authority.email.lower() in (actor, profile.email.lower()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The approval authority must be someone other than the requester and the user.")
    for tenant_id in [payload.home_tenant_id, *payload.target_tenant_ids]:
        if not await tenant_exists(db, tenant_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tenant {tenant_id} not found")
    # A target inside the home state adds nothing the user does not already have.
    home = payload.home_tenant_id.upper()
    home_keys = await _tenant_identifiers(home, db) if await _is_state(db, home) else {home}
    for tenant_id in payload.target_tenant_ids:
        if home_keys & await _tenant_identifiers(tenant_id.upper(), db):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{tenant_id} is already within the user's home tenant.")
    return profile, authority


def _apply_grant(grant: CrossTenantAccessGrant, payload: GrantPayload, profile: GlobalUserProfile, authority: GlobalUserProfile) -> None:
    grant.user_profile_id, grant.user_email, grant.user_name = profile.id, profile.email.lower(), full_name(profile)
    grant.user_type, grant.home_tenant_id, grant.access_level = payload.user_type, payload.home_tenant_id, payload.access_level
    grant.effective_from, grant.effective_until = payload.effective_from, payload.effective_until
    grant.business_justification, grant.approval_reference = payload.business_justification, payload.approval_reference
    grant.approval_authority_id, grant.approval_authority_email = authority.id, authority.email.lower()
    current = {t.target_tenant_id for t in grant.targets}
    wanted = set(payload.target_tenant_ids)
    grant.targets = [t for t in grant.targets if t.target_tenant_id in wanted] + [CrossTenantGrantTarget(target_tenant_id=t) for t in payload.target_tenant_ids if t not in current]


@router.post("/grants", response_model=ApiResponse[GrantOut], status_code=status.HTTP_201_CREATED)
async def create_grant(payload: GrantPayload, request: Request, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    actor = actor_of(user)
    profile, authority = await _check_grant(db, payload, actor)
    # Set both relationships so nothing tries to lazy-load them in async code.
    grant = CrossTenantAccessGrant(status=rules.STATUS_PENDING, requested_by=actor, targets=[], scope=None)
    _apply_grant(grant, payload, profile, authority)
    db.add(grant)
    await db.flush()
    await db.refresh(grant, ["record_sequence"])
    await record_change(db, grant, "REQUESTED", actor, client_ip(request), reason=payload.business_justification)
    await db.commit()
    return ApiResponse(data=grant_out(grant))


@router.put("/grants/{grant_id}", response_model=ApiResponse[GrantOut])
async def update_grant(grant_id: str, payload: GrantPayload, request: Request, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    grant = await get_grant(db, grant_id)
    if grant.status not in (rules.STATUS_PENDING, rules.STATUS_ACTIVE):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{grant.status} access cannot be changed. Request new access instead.")
    if payload.user_profile_id != grant.user_profile_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An access record cannot move to another user.")
    actor = actor_of(user)
    profile, authority = await _check_grant(db, payload, actor)
    previous_level = grant.access_level
    _apply_grant(grant, payload, profile, authority)
    # Any change to approved access goes back for approval, so nothing widens unseen.
    grant.status, grant.requested_by, grant.approved_by, grant.approved_at = rules.STATUS_PENDING, actor, None, None
    for item in (await db.scalars(select(AccessReviewItem).where(AccessReviewItem.grant_id == grant.id, AccessReviewItem.status == rules.ITEM_AWAITING_CHANGE))).all():
        item.status = rules.ITEM_DECIDED
    await record_change(db, grant, "UPDATED", actor, client_ip(request), reason=payload.business_justification, previous_level=previous_level)
    await db.commit()
    return ApiResponse(data=grant_out(grant))


@router.post("/grants/{grant_id}/approve", response_model=ApiResponse[GrantOut])
async def approve_grant(grant_id: str, request: Request, note: Optional[str] = Body(None, embed=True, max_length=2000),
                        db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    grant = await get_grant(db, grant_id)
    actor = actor_of(user)
    if grant.status != rules.STATUS_PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending access can be approved.")
    if actor != grant.approval_authority_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the named approval authority can approve this access.")
    if actor == grant.requested_by:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The person who requested this access cannot approve it.")
    now = datetime.datetime.utcnow()
    if grant.effective_until and grant.effective_until < now:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This access has already passed its end date.")
    grant.status, grant.approved_by, grant.approved_at, grant.decision_note = rules.STATUS_ACTIVE, actor, now, note
    await record_change(db, grant, "APPROVED", actor, client_ip(request), reason=note)
    await db.commit()
    return ApiResponse(data=grant_out(grant))


@router.post("/grants/{grant_id}/reject", response_model=ApiResponse[GrantOut])
async def reject_grant(grant_id: str, payload: GrantDecision, request: Request, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    grant = await get_grant(db, grant_id)
    actor = actor_of(user)
    if grant.status != rules.STATUS_PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending access can be rejected.")
    if actor != grant.approval_authority_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the named approval authority can reject this access.")
    grant.status, grant.decision_note = rules.STATUS_REJECTED, payload.reason
    await record_change(db, grant, "REJECTED", actor, client_ip(request), reason=payload.reason)
    await db.commit()
    return ApiResponse(data=grant_out(grant))


@router.post("/grants/{grant_id}/revoke", response_model=ApiResponse[GrantOut])
async def revoke(grant_id: str, payload: GrantDecision, request: Request, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    grant = await get_grant(db, grant_id)
    await revoke_grant(db, grant, actor_of(user), client_ip(request), payload.reason)
    await db.commit()
    return ApiResponse(data=grant_out(grant))


# ---------- Tab 2: tenant scope ----------

def scope_out(scope: CrossTenantAccessScope, grant: CrossTenantAccessGrant) -> ScopeOut:
    values = {column.name: getattr(scope, column.name) for column in CrossTenantAccessScope.__table__.columns if column.name != "created_at"}
    return ScopeOut(**values, record_number=rules.record_number(grant.record_sequence), user_email=grant.user_email, user_name=grant.user_name)


@router.get("/scopes", response_model=PagedResponse[ScopeOut])
async def list_scopes(
    search: Optional[str] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(CrossTenantAccessGrant.user_name.ilike(term), CrossTenantAccessGrant.user_email.ilike(term),
                              CrossTenantAccessScope.state_tenant_id.ilike(term), CrossTenantAccessScope.access_scope.ilike(term)))
    joined = select(CrossTenantAccessScope, CrossTenantAccessGrant).join(CrossTenantAccessGrant, CrossTenantAccessScope.grant_id == CrossTenantAccessGrant.id).where(*conditions)
    total = await db.scalar(select(func.count()).select_from(joined.subquery())) or 0
    rows = (await db.execute(joined.order_by(CrossTenantAccessScope.updated_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[scope_out(s, g) for s, g in rows], total=total)


async def _ulbs_under(db: AsyncSession, state: StateTenant) -> Set[str]:
    rows = await db.scalars(select(Tenant.tenant_id).where(or_(Tenant.parent_state_tenant_id == state.tenant_id, Tenant.state_code == state.state_code)))
    return set(rows.all())


async def _check_scope(db: AsyncSession, payload: ScopePayload, grant: CrossTenantAccessGrant) -> None:
    def invalid(detail: str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    state = await db.scalar(select(StateTenant).where(StateTenant.tenant_id == payload.state_tenant_id))
    if not state:
        invalid("Select a state.")
    targets = {t.target_tenant_id for t in grant.targets}
    in_state = await _ulbs_under(db, state)
    whole_state = state.tenant_id in targets
    if not whole_state and not targets & in_state:
        invalid("This access has no target tenant in that state.")
    # A scope can only narrow the approved targets, never add to them.
    reachable = in_state if whole_state else targets & in_state
    if not payload.include_child_tenants and not whole_state:
        invalid("Child tenants can only be left out when the whole state is a target.")
    if set(payload.ulb_tenant_ids) - reachable:
        invalid("Each ULB must be one this access already reaches.")
    areas = set(payload.ulb_tenant_ids) or reachable
    if payload.department_ids:
        found = await db.scalar(select(func.count(TenantDepartment.id)).where(TenantDepartment.id.in_(payload.department_ids), TenantDepartment.tenant_id.in_(areas | {state.tenant_id})))
        if found != len(payload.department_ids):
            invalid("Each department must belong to the selected state or ULBs.")
    for model, ids, label in ((Zone, payload.zone_ids, "zone"), (Ward, payload.ward_ids, "ward")):
        if ids:
            found = await db.scalar(select(func.count(model.id)).where(model.id.in_(ids), model.tenant_id.in_(areas)))
            if found != len(ids):
                invalid(f"Each {label} must belong to the selected ULBs.")
    if payload.restricted_components:
        modules = set((await db.scalars(select(ModuleModel.code).where(ModuleModel.code.in_(payload.restricted_components)))).all())
        components = set((await db.scalars(select(ComponentModel.code).where(ComponentModel.code.in_(payload.restricted_components)))).all())
        if set(payload.restricted_components) - modules - components:
            invalid("Restrictions must name modules or components in the catalogue.")


@router.put("/scopes", response_model=ApiResponse[ScopeOut])
async def save_scope(payload: ScopePayload, request: Request, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    grant = await get_grant(db, payload.grant_id)
    if grant.status in rules.CLOSED_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{grant.status} access cannot be scoped.")
    await _check_scope(db, payload, grant)
    previous = rules.describe_scope(grant.scope)
    scope = grant.scope or CrossTenantAccessScope(grant_id=grant.id)
    for field, value in payload.model_dump().items():
        setattr(scope, field, value)
    scope.updated_by = actor_of(user)
    grant.scope = scope
    await db.flush()
    await record_change(db, grant, "SCOPE_UPDATED", actor_of(user), client_ip(request), previous_level=grant.access_level, previous_scope=previous)
    await db.commit()
    return ApiResponse(data=scope_out(scope, grant))
