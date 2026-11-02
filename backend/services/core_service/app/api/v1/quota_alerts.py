"""ADM-S04: usage alert rules, configurable threshold levels and alert history."""
import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.quotas import resolve_tenant
from app.api.v1.white_label import add_audit, operator_of
from app.core import quota_rules as rules
from app.core.auth import require_roles
from app.core.config import settings
from app.db.models import UsageAlertEvent, UsageAlertRule, UsageThresholdLevel
from app.db.session import get_read_db, get_write_db
from app.schemas.quota import AlertEventOut, AlertRuleOut, AlertRulePayload, ThresholdLevelOut, ThresholdLevelUpdate
from app.schemas.tenant import ApiResponse
from app.schemas.white_label import PagedResponse

SUPER_ADMIN = Depends(require_roles(["super_admin"]))
router = APIRouter(prefix="/modules/quotas/alerts", tags=["ADM-S04 Usage Alerts"], dependencies=[SUPER_ADMIN])


def _check_channels(channels: List[str]) -> None:
    """A channel with nothing behind it would look configured while sending nothing."""
    available = [rules.CHANNEL_IN_APP] + ([rules.CHANNEL_EMAIL] if settings.SMTP_HOST else [])
    unavailable = [c for c in channels if c not in available]
    if unavailable:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Not available on this platform yet: {', '.join(unavailable)}.")


@router.get("/levels", response_model=ApiResponse[List[ThresholdLevelOut]])
async def list_levels(db: AsyncSession = Depends(get_read_db)):
    rows = (await db.scalars(select(UsageThresholdLevel).order_by(UsageThresholdLevel.percentage))).all()
    return ApiResponse(data=[ThresholdLevelOut.model_validate(r) for r in rows])


@router.put("/levels/{level_id}", response_model=ApiResponse[ThresholdLevelOut])
async def update_level(level_id: str, payload: ThresholdLevelUpdate, db: AsyncSession = Depends(get_write_db)):
    row = await db.scalar(select(UsageThresholdLevel).where(UsageThresholdLevel.id == level_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")
    row.percentage = payload.percentage
    await db.commit()
    return ApiResponse(data=ThresholdLevelOut.model_validate(row))


@router.get("/rules", response_model=PagedResponse[AlertRuleOut])
async def list_rules(
    search: Optional[str] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(UsageAlertRule.alert_name.ilike(term), UsageAlertRule.alert_code.ilike(term), UsageAlertRule.tenant_id.ilike(term)))
    total = await db.scalar(select(func.count(UsageAlertRule.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(UsageAlertRule).where(*conditions).order_by(UsageAlertRule.alert_name).offset(skip).limit(limit))).all()
    return PagedResponse(data=[AlertRuleOut.model_validate(r) for r in rows], total=total)


async def _save(db: AsyncSession, row: UsageAlertRule, payload: AlertRulePayload, user: dict) -> ApiResponse[AlertRuleOut]:
    _check_channels(payload.notification_channels)
    tenant_id = await resolve_tenant(db, payload.state_tenant_id, payload.ulb_tenant_id if payload.tenant_level == "ULB" else None, user)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    row.tenant_id = tenant_id
    add_audit(db, tenant_id, "USAGE_ALERT_SAVED", user, f"Usage alert {payload.alert_code} saved.")
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This alert code is already in use.")
    return ApiResponse(data=AlertRuleOut.model_validate(row))


@router.post("/rules", response_model=ApiResponse[AlertRuleOut], status_code=status.HTTP_201_CREATED)
async def create_rule(payload: AlertRulePayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    row = UsageAlertRule(created_by=operator_of(user), is_firing=False)
    db.add(row)
    return await _save(db, row, payload, user)


@router.put("/rules/{rule_id}", response_model=ApiResponse[AlertRuleOut])
async def update_rule(rule_id: str, payload: AlertRulePayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    row = await db.scalar(select(UsageAlertRule).where(UsageAlertRule.id == rule_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert rule not found")
    return await _save(db, row, payload, user)


@router.get("/events", response_model=PagedResponse[AlertEventOut])
async def list_events(
    search: Optional[str] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(UsageAlertEvent.message.ilike(term), UsageAlertEvent.tenant_id.ilike(term)))
    total = await db.scalar(select(func.count(UsageAlertEvent.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(UsageAlertEvent).where(*conditions).order_by(UsageAlertEvent.created_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[AlertEventOut.model_validate(r) for r in rows], total=total)


@router.post("/events/{event_id}/acknowledge", response_model=ApiResponse[AlertEventOut])
async def acknowledge_event(event_id: str, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    row = await db.scalar(select(UsageAlertEvent).where(UsageAlertEvent.id == event_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if not row.acknowledged_at:
        row.acknowledged_by = operator_of(user)
        row.acknowledged_at = datetime.datetime.utcnow()
        await db.commit()
    return ApiResponse(data=AlertEventOut.model_validate(row))
