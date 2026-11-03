"""ADM-R02 Tabs 3 to 5: permission rules, access certification campaigns and the change history."""
import csv
import datetime
import io
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.cross_tenant_access import _platform_admin_emails, _ulbs_under, actor_of, get_grant, revoke_grant
from app.core import cross_tenant_rules as rules
from app.core.auth import require_roles
from app.core.cross_tenant_history import client_ip, record_change
from app.db.models import (
    AccessChangeHistory, AccessReviewCampaign, AccessReviewItem, ComponentModel, CrossTenantAccessGrant, CrossTenantGrantTarget,
    CrossTenantPermissionRule, GlobalUserProfile, ModuleModel, StateTenant,
)
from app.db.session import get_read_db, get_write_db
from app.schemas.cross_tenant import (
    CampaignOut, CampaignPayload, HistoryOut, ReviewDecisionPayload, ReviewItemOut, RuleOut, RulePayload, RuleReview,
)
from app.schemas.tenant import ApiResponse
from app.schemas.white_label import PagedResponse

SUPER_ADMIN = Depends(require_roles(["super_admin"]))
router = APIRouter(prefix="/iam/cross-tenant", tags=["ADM-R02 Cross-Tenant Access Management"], dependencies=[SUPER_ADMIN])

EXPORT_LIMIT = 5000
# Spreadsheet programs run cells that start with these, so exported text is prefixed to stay text.
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


# ---------- Tab 3: permission rules ----------

def rule_out(rule: CrossTenantPermissionRule, grant: CrossTenantAccessGrant) -> RuleOut:
    values = {column.name: getattr(rule, column.name) for column in CrossTenantPermissionRule.__table__.columns if column.name not in ("created_at", "updated_at")}
    return RuleOut(**values, record_number=rules.record_number(grant.record_sequence))


@router.get("/rules", response_model=PagedResponse[RuleOut])
async def list_rules(
    search: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if review_status:
        conditions.append(CrossTenantPermissionRule.review_status == review_status)
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(CrossTenantPermissionRule.user_email.ilike(term), CrossTenantPermissionRule.target_tenant_id.ilike(term),
                              CrossTenantPermissionRule.access_decision.ilike(term), CrossTenantAccessGrant.user_name.ilike(term)))
    joined = select(CrossTenantPermissionRule, CrossTenantAccessGrant).join(CrossTenantAccessGrant, CrossTenantPermissionRule.grant_id == CrossTenantAccessGrant.id).where(*conditions)
    total = await db.scalar(select(func.count()).select_from(joined.subquery())) or 0
    rows = (await db.execute(joined.order_by(CrossTenantPermissionRule.updated_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[rule_out(r, g) for r, g in rows], total=total)


async def _check_rule(db: AsyncSession, payload: RulePayload, grant: CrossTenantAccessGrant) -> None:
    if grant.status in rules.CLOSED_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{grant.status} access cannot take new rules.")
    targets = {t.target_tenant_id for t in grant.targets}
    if payload.target_tenant_id not in targets:
        # A ULB inside a whole-state target is also reachable.
        states = (await db.scalars(select(StateTenant).where(StateTenant.tenant_id.in_(targets)))).all()
        reachable = set()
        for state in states:
            reachable |= await _ulbs_under(db, state)
        if payload.target_tenant_id not in reachable:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The tenant must be one this access reaches.")
    modules = set((await db.scalars(select(ModuleModel.code).where(ModuleModel.code.in_(payload.module_codes)))).all())
    if modules != set(payload.module_codes):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select modules from the catalogue.")
    if payload.component_codes:
        found = await db.scalar(select(func.count(ComponentModel.component_id)).where(
            ComponentModel.code.in_(payload.component_codes), ComponentModel.parent_module_code.in_(payload.module_codes)))
        if found != len(payload.component_codes):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Each component must belong to a selected module.")


def _describe_rule(rule: CrossTenantPermissionRule) -> str:
    scope = ", ".join(rule.component_codes) or ", ".join(rule.module_codes)
    return f"{rule.access_decision} {', '.join(rule.action_permissions)} on {scope} in {rule.target_tenant_id}"


@router.post("/rules", response_model=ApiResponse[RuleOut], status_code=status.HTTP_201_CREATED)
async def create_rule(payload: RulePayload, request: Request, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    grant = await get_grant(db, payload.grant_id)
    await _check_rule(db, payload, grant)
    rule = CrossTenantPermissionRule(**payload.model_dump(), user_email=grant.user_email, review_status=rules.REVIEW_PENDING, created_by=actor_of(user))
    db.add(rule)
    await db.flush()
    await record_change(db, grant, "PERMISSION_RULE_SAVED", actor_of(user), client_ip(request), reason=_describe_rule(rule), previous_level=grant.access_level)
    await db.commit()
    return ApiResponse(data=rule_out(rule, grant))


@router.put("/rules/{rule_id}", response_model=ApiResponse[RuleOut])
async def update_rule(rule_id: str, payload: RulePayload, request: Request, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    rule = await db.scalar(select(CrossTenantPermissionRule).where(CrossTenantPermissionRule.id == rule_id))
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    if payload.grant_id != rule.grant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A rule cannot move to another access record.")
    grant = await get_grant(db, rule.grant_id)
    await _check_rule(db, payload, grant)
    for field, value in payload.model_dump().items():
        setattr(rule, field, value)
    # A changed rule needs a fresh review before it applies.
    rule.review_status, rule.reviewed_by, rule.reviewed_at, rule.created_by = rules.REVIEW_PENDING, None, None, actor_of(user)
    await record_change(db, grant, "PERMISSION_RULE_SAVED", actor_of(user), client_ip(request), reason=_describe_rule(rule), previous_level=grant.access_level)
    await db.commit()
    return ApiResponse(data=rule_out(rule, grant))


@router.post("/rules/{rule_id}/review", response_model=ApiResponse[RuleOut])
async def review_rule(rule_id: str, payload: RuleReview, request: Request, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    rule = await db.scalar(select(CrossTenantPermissionRule).where(CrossTenantPermissionRule.id == rule_id))
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    actor = actor_of(user)
    if rule.review_status != rules.REVIEW_PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending rules can be reviewed.")
    if actor == rule.created_by:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The person who wrote this rule cannot review it.")
    rule.review_status, rule.reviewed_by, rule.reviewed_at = payload.review_status, actor, datetime.datetime.utcnow()
    grant = await get_grant(db, rule.grant_id)
    await record_change(db, grant, f"PERMISSION_RULE_{payload.review_status.upper()}", actor, client_ip(request), reason=_describe_rule(rule), previous_level=grant.access_level)
    await db.commit()
    return ApiResponse(data=rule_out(rule, grant))


# ---------- Tab 4: access review and certification ----------

async def _campaign_out(db: AsyncSession, campaign: AccessReviewCampaign) -> CampaignOut:
    counts = dict((await db.execute(select(AccessReviewItem.status, func.count(AccessReviewItem.id)).where(AccessReviewItem.campaign_id == campaign.id).group_by(AccessReviewItem.status))).all())
    out = CampaignOut.model_validate(campaign)
    out.total_items = sum(counts.values())
    out.decided_items = out.total_items - counts.get(rules.ITEM_PENDING, 0)
    return out


@router.get("/campaigns", response_model=PagedResponse[CampaignOut])
async def list_campaigns(
    search: Optional[str] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(AccessReviewCampaign.campaign_name.ilike(term), AccessReviewCampaign.review_owner_email.ilike(term), AccessReviewCampaign.status.ilike(term)))
    total = await db.scalar(select(func.count(AccessReviewCampaign.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(AccessReviewCampaign).where(*conditions).order_by(AccessReviewCampaign.created_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[await _campaign_out(db, c) for c in rows], total=total)


def matching_grants(payload: CampaignPayload):
    statement = select(CrossTenantAccessGrant.id).where(CrossTenantAccessGrant.status.in_(payload.access_statuses), CrossTenantAccessGrant.user_type.in_(payload.user_types))
    if payload.tenant_scope:
        statement = statement.where(or_(
            CrossTenantAccessGrant.home_tenant_id.in_(payload.tenant_scope),
            CrossTenantAccessGrant.id.in_(select(CrossTenantGrantTarget.grant_id).where(CrossTenantGrantTarget.target_tenant_id.in_(payload.tenant_scope))),
        ))
    return statement


@router.post("/campaigns", response_model=ApiResponse[CampaignOut], status_code=status.HTTP_201_CREATED)
async def create_campaign(payload: CampaignPayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    owner = await db.scalar(select(GlobalUserProfile).where(GlobalUserProfile.id == payload.review_owner_id))
    if not owner or owner.account_status != "Active" or owner.email.lower() not in await _platform_admin_emails(db):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The review owner must be an active platform super admin.")
    grant_ids = (await db.scalars(matching_grants(payload))).all()
    if not grant_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No access records match these filters.")
    campaign = AccessReviewCampaign(
        **payload.model_dump(exclude={"review_owner_id", "review_deadline"}), review_owner_id=owner.id, review_owner_email=owner.email.lower(),
        review_deadline=datetime.datetime.combine(payload.review_deadline, datetime.time.max), status=rules.CAMPAIGN_OPEN, created_by=actor_of(user),
    )
    db.add(campaign)
    await db.flush()
    db.add_all([AccessReviewItem(campaign_id=campaign.id, grant_id=grant_id, status=rules.ITEM_PENDING) for grant_id in grant_ids])
    await db.commit()
    return ApiResponse(data=await _campaign_out(db, campaign))


def item_out(item: AccessReviewItem, grant: CrossTenantAccessGrant) -> ReviewItemOut:
    return ReviewItemOut(
        id=item.id, grant_id=grant.id, record_number=rules.record_number(grant.record_sequence), user_email=grant.user_email, user_name=grant.user_name,
        user_type=grant.user_type, home_tenant_id=grant.home_tenant_id, target_tenant_ids=[t.target_tenant_id for t in grant.targets],
        access_level=grant.access_level, grant_status=grant.status, status=item.status, review_decision=item.review_decision,
        reviewer_comments=item.reviewer_comments, decided_by=item.decided_by, decided_at=item.decided_at,
    )


@router.get("/campaigns/{campaign_id}/items", response_model=PagedResponse[ReviewItemOut])
async def list_campaign_items(
    campaign_id: str, search: Optional[str] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_read_db),
):
    conditions = [AccessReviewItem.campaign_id == campaign_id]
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(CrossTenantAccessGrant.user_name.ilike(term), CrossTenantAccessGrant.user_email.ilike(term), AccessReviewItem.status.ilike(term)))
    joined = select(AccessReviewItem, CrossTenantAccessGrant).join(CrossTenantAccessGrant, AccessReviewItem.grant_id == CrossTenantAccessGrant.id).where(*conditions)
    total = await db.scalar(select(func.count()).select_from(joined.subquery())) or 0
    rows = (await db.execute(joined.order_by(CrossTenantAccessGrant.user_name).offset(skip).limit(limit))).all()
    return PagedResponse(data=[item_out(i, g) for i, g in rows], total=total)


@router.post("/campaigns/{campaign_id}/items/{item_id}/decision", response_model=ApiResponse[ReviewItemOut])
async def decide_item(campaign_id: str, item_id: str, payload: ReviewDecisionPayload, request: Request,
                      db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    campaign = await db.scalar(select(AccessReviewCampaign).where(AccessReviewCampaign.id == campaign_id))
    item = await db.scalar(select(AccessReviewItem).where(AccessReviewItem.id == item_id, AccessReviewItem.campaign_id == campaign_id))
    if not campaign or not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found")
    actor = actor_of(user)
    if campaign.status != rules.CAMPAIGN_OPEN:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This campaign is closed.")
    if actor != campaign.review_owner_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the review owner can record decisions.")
    if item.status != rules.ITEM_PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This item already has a decision.")
    grant = await get_grant(db, item.grant_id)
    ip = client_ip(request)
    now = datetime.datetime.utcnow()
    item.review_decision, item.reviewer_comments, item.decided_by, item.decided_at = payload.review_decision, payload.reviewer_comments, actor, now
    if payload.review_decision == rules.REVOKE:
        if grant.status not in rules.CLOSED_STATUSES:
            await revoke_grant(db, grant, actor, ip, payload.reviewer_comments, action="REVIEW_REVOKED")
        item.status = rules.ITEM_DECIDED
    elif payload.review_decision == rules.MODIFY:
        await record_change(db, grant, "REVIEW_MODIFY_REQUESTED", actor, ip, reason=payload.reviewer_comments, previous_level=grant.access_level)
        item.status = rules.ITEM_AWAITING_CHANGE
    else:
        await record_change(db, grant, "REVIEW_RETAINED", actor, ip, reason=payload.reviewer_comments, previous_level=grant.access_level)
        item.status = rules.ITEM_DECIDED
    await db.flush()
    pending = await db.scalar(select(func.count(AccessReviewItem.id)).where(AccessReviewItem.campaign_id == campaign.id, AccessReviewItem.status == rules.ITEM_PENDING))
    if not pending:
        campaign.status, campaign.completed_at = rules.CAMPAIGN_COMPLETED, now
    await db.commit()
    return ApiResponse(data=item_out(item, grant))


# ---------- Tab 5: access history and audit ----------

def _history_conditions(search, action, date_from, date_to) -> list:
    conditions = []
    if action:
        conditions.append(AccessChangeHistory.action == action)
    if date_from:
        conditions.append(AccessChangeHistory.created_at >= date_from)
    if date_to:
        conditions.append(AccessChangeHistory.created_at <= date_to)
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(AccessChangeHistory.user_email.ilike(term), AccessChangeHistory.changed_by.ilike(term), AccessChangeHistory.action.ilike(term),
                              AccessChangeHistory.home_tenant_id.ilike(term), AccessChangeHistory.approval_reference.ilike(term)))
    return conditions


@router.get("/history", response_model=PagedResponse[HistoryOut])
async def list_history(
    search: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    date_from: Optional[datetime.datetime] = Query(None),
    date_to: Optional[datetime.datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_read_db),
):
    conditions = _history_conditions(search, action, date_from, date_to)
    total = await db.scalar(select(func.count(AccessChangeHistory.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(AccessChangeHistory).where(*conditions).order_by(AccessChangeHistory.created_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[HistoryOut.model_validate(r) for r in rows], total=total)


@router.get("/history/actions", response_model=ApiResponse[List[str]])
async def list_history_actions(db: AsyncSession = Depends(get_read_db)):
    rows = await db.scalars(select(AccessChangeHistory.action).distinct().order_by(AccessChangeHistory.action))
    return ApiResponse(data=list(rows.all()))


def safe_cell(value) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(FORMULA_PREFIXES) else text


@router.get("/history/export")
async def export_history(
    search: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    date_from: Optional[datetime.datetime] = Query(None),
    date_to: Optional[datetime.datetime] = Query(None),
    db: AsyncSession = Depends(get_read_db),
):
    conditions = _history_conditions(search, action, date_from, date_to)
    rows = (await db.scalars(select(AccessChangeHistory).where(*conditions).order_by(AccessChangeHistory.created_at.desc()).limit(EXPORT_LIMIT))).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Timestamp (UTC)", "User", "Home Tenant", "Target Tenants", "Previous Access Level", "New Access Level", "Previous Scope",
                     "New Scope", "Action", "Changed By", "IP Address", "Reason", "Approval Reference"])
    for r in rows:
        writer.writerow([safe_cell(v) for v in (r.created_at.isoformat(), r.user_email, r.home_tenant_id, "; ".join(r.target_tenant_ids or []), r.previous_access_level,
                                                 r.new_access_level, r.previous_scope, r.new_scope, r.action, r.changed_by, r.ip_address, r.reason, r.approval_reference)])
    return Response(content=buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="cross-tenant-access-history.csv"'})
