"""ADM-S04: storage allocations and usage, SMS credits and API policies."""
import datetime
import hashlib
import hmac
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.white_label import add_audit, operator_of, require_tenant
from app.core import quota_rules as rules
from app.core.api_quota import clear_policy_cache, window_keys
from app.core.auth import require_roles
from app.core.config import settings
from app.core.quota_service import sms_connected, tenants_under, used_bytes
from app.core.tenant_context import set_rls_context
from app.core.valkey import valkey_client
from app.db.models import (
    ApiQuotaPolicy, ApiUsageMinute, MicroserviceRegistryModel, ModuleModel, SmsCreditAllocation, SmsMessage, StateTenant,
    StorageAllocation, StorageObject, Tenant, UsageThresholdLevel, User,
)
from app.db.session import AsyncWriteSessionLocal, get_read_db, get_write_db
from app.schemas.quota import (
    ApiPolicyOut, ApiPolicyPayload, DeliveryReport, LargestFile, QuotaOptions, RecipientOption, SmsAllocationOut, SmsAllocationPayload,
    StorageAllocationOut, StorageAllocationPayload, StorageUsageRow,
)
from app.schemas.tenant import ApiResponse
from app.schemas.white_label import PagedResponse

SUPER_ADMIN = Depends(require_roles(["super_admin"]))
router = APIRouter(prefix="/modules/quotas", tags=["ADM-S04 Quota & Usage Management"], dependencies=[SUPER_ADMIN])
public_router = APIRouter(prefix="/public/quotas", tags=["ADM-S04 SMS Delivery Reports"])

LARGEST_FILES = 5


def naive(value: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    return value.astimezone(datetime.timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value


async def resolve_tenant(db: AsyncSession, state_id: str, ulb_id: Optional[str], user: dict) -> str:
    state = await require_tenant(db, state_id, user)
    if not ulb_id:
        return state
    ulb_id = await require_tenant(db, ulb_id, user)
    ulb = await db.scalar(select(Tenant).where(Tenant.tenant_id == ulb_id))
    state_row = await db.scalar(select(StateTenant).where(StateTenant.tenant_id == state))
    if not ulb or not state_row or (ulb.parent_state_tenant_id != state and ulb.state_code != state_row.state_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This ULB does not belong to the selected state")
    return ulb_id


@router.get("/options", response_model=ApiResponse[QuotaOptions])
async def get_options(db: AsyncSession = Depends(get_read_db)):
    modules = (await db.scalars(select(ModuleModel.code).order_by(ModuleModel.code))).all()
    registered = (await db.scalars(select(MicroserviceRegistryModel.service_code))).all()
    services = sorted({m.lower() for m in modules} | set(registered))
    channels = [rules.CHANNEL_IN_APP]
    if settings.SMTP_HOST:
        channels.append(rules.CHANNEL_EMAIL)
    return ApiResponse(data=QuotaOptions(
        tenant_levels=rules.TENANT_LEVELS, record_statuses=rules.RECORD_STATUSES, storage_types=rules.STORAGE_TYPES,
        storage_providers=rules.STORAGE_PROVIDERS, measured_providers=rules.MEASURED_PROVIDERS, storage_units=list(rules.STORAGE_UNITS),
        file_types=rules.FILE_TYPES, modules=list(modules), sms_providers=rules.SMS_PROVIDERS, sms_categories=rules.SMS_CATEGORIES,
        sms_connected=sms_connected(), api_gateways=rules.API_GATEWAYS, api_services=services, api_categories=rules.API_CATEGORIES,
        quota_periods=rules.QUOTA_PERIODS, resource_types=rules.RESOURCE_TYPES, alert_conditions=rules.ALERT_CONDITIONS,
        operators=rules.OPERATORS, severities=rules.SEVERITIES, notification_channels=channels,
    ))


@router.get("/recipients", response_model=ApiResponse[List[RecipientOption]])
async def list_recipients(search: Optional[str] = Query(None), limit: int = Query(100, ge=1, le=100), db: AsyncSession = Depends(get_read_db)):
    statement = select(User).where(User.is_active.is_(True)).order_by(User.full_name).limit(limit)
    if search and search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(or_(User.full_name.ilike(term), User.email.ilike(term)))
    rows = (await db.scalars(statement)).all()
    return ApiResponse(data=[RecipientOption(id=u.id, full_name=u.full_name, email=u.email, tenant_id=u.tenant_id) for u in rows])


async def _check_state_capacity(db: AsyncSession, payload: StorageAllocationPayload, tenant_id: str, keep_id: Optional[str]) -> None:
    """Active ULB allocations must fit inside their state's, so a state cannot promise more than it has."""
    if payload.allocation_status != "Active" or payload.tenant_level != "ULB":
        return
    state_allocation = await db.scalar(select(StorageAllocation).where(
        StorageAllocation.tenant_id == payload.state_tenant_id, StorageAllocation.storage_type == payload.storage_type,
        StorageAllocation.allocation_status == "Active",
    ))
    if not state_allocation:
        return
    conditions = [StorageAllocation.state_tenant_id == payload.state_tenant_id, StorageAllocation.tenant_level == "ULB",
                  StorageAllocation.storage_type == payload.storage_type, StorageAllocation.allocation_status == "Active"]
    if keep_id:
        conditions.append(StorageAllocation.id != keep_id)
    others = await db.scalar(select(func.coalesce(func.sum(StorageAllocation.allocation_bytes), 0)).where(*conditions)) or 0
    if int(others) + rules.to_bytes(payload.allocation_amount, payload.storage_unit) > state_allocation.allocation_bytes:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ULB allocations cannot exceed the state's allocation.")


@router.get("/storage/allocations", response_model=PagedResponse[StorageAllocationOut])
async def list_storage_allocations(
    search: Optional[str] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(StorageAllocation.allocation_name.ilike(term), StorageAllocation.tenant_id.ilike(term), StorageAllocation.storage_bucket.ilike(term)))
    total = await db.scalar(select(func.count(StorageAllocation.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(StorageAllocation).where(*conditions).order_by(StorageAllocation.updated_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[StorageAllocationOut.model_validate(r) for r in rows], total=total)


def _apply_storage(row: StorageAllocation, payload: StorageAllocationPayload, tenant_id: str) -> None:
    for field, value in payload.model_dump(by_alias=False).items():
        if field != "module_allocations":
            setattr(row, field, value)
    row.tenant_id = tenant_id
    row.allocation_bytes = rules.to_bytes(payload.allocation_amount, payload.storage_unit)
    row.module_allocations = [m.model_dump(by_alias=True) for m in payload.module_allocations]
    row.effective_from, row.effective_until = naive(payload.effective_from), naive(payload.effective_until)
    if payload.tenant_level == "State":
        row.ulb_tenant_id = None


@router.post("/storage/allocations", response_model=ApiResponse[StorageAllocationOut], status_code=status.HTTP_201_CREATED)
async def create_storage_allocation(payload: StorageAllocationPayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    tenant_id = await resolve_tenant(db, payload.state_tenant_id, payload.ulb_tenant_id if payload.tenant_level == "ULB" else None, user)
    await _check_state_capacity(db, payload, tenant_id, None)
    row = StorageAllocation(created_by=operator_of(user))
    _apply_storage(row, payload, tenant_id)
    db.add(row)
    add_audit(db, tenant_id, "STORAGE_ALLOCATION_SAVED", user, f"{payload.allocation_name}: {payload.allocation_amount:g} {payload.storage_unit} as {payload.allocation_status}.")
    await db.commit()
    return ApiResponse(data=StorageAllocationOut.model_validate(row))


@router.put("/storage/allocations/{allocation_id}", response_model=ApiResponse[StorageAllocationOut])
async def update_storage_allocation(allocation_id: str, payload: StorageAllocationPayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    row = await db.scalar(select(StorageAllocation).where(StorageAllocation.id == allocation_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found")
    tenant_id = await resolve_tenant(db, payload.state_tenant_id, payload.ulb_tenant_id if payload.tenant_level == "ULB" else None, user)
    await _check_state_capacity(db, payload, tenant_id, row.id)
    _apply_storage(row, payload, tenant_id)
    add_audit(db, tenant_id, "STORAGE_ALLOCATION_SAVED", user, f"{payload.allocation_name}: {payload.allocation_amount:g} {payload.storage_unit} as {payload.allocation_status}.")
    await db.commit()
    return ApiResponse(data=StorageAllocationOut.model_validate(row))


async def _levels(db: AsyncSession) -> List[tuple]:
    return [(r.level_name, r.percentage) for r in (await db.scalars(select(UsageThresholdLevel))).all()]


async def _usage_row(db: AsyncSession, allocation: StorageAllocation, levels: List[tuple], modules: List[str], start, end) -> StorageUsageRow:
    row = StorageUsageRow(
        allocation_id=allocation.id, allocation_name=allocation.allocation_name, tenant_id=allocation.tenant_id, tenant_level=allocation.tenant_level,
        storage_type=allocation.storage_type, storage_provider=allocation.storage_provider, allocated_bytes=allocation.allocation_bytes,
        telemetry_connected=allocation.storage_provider in rules.MEASURED_PROVIDERS, usage_status="Not Connected",
    )
    if not row.telemetry_connected:
        return row
    used = await used_bytes(db, allocation)
    row.used_bytes = used
    row.available_bytes = max(allocation.allocation_bytes - used, 0)
    row.utilisation_percentage = rules.percentage(used, allocation.allocation_bytes)
    row.usage_status = rules.usage_status(row.utilisation_percentage, levels)
    scope = [StorageObject.tenant_id.in_(await tenants_under(db, allocation.tenant_id)), StorageObject.storage_type == allocation.storage_type]
    if modules:
        scope.append(StorageObject.module_code.in_(modules))
    if start:
        scope.append(StorageObject.created_at >= naive(start))
    if end:
        scope.append(StorageObject.created_at <= naive(end))
    row.total_files = await db.scalar(select(func.count(StorageObject.id)).where(*scope)) or 0
    largest = (await db.scalars(select(StorageObject).where(*scope).order_by(StorageObject.size_bytes.desc()).limit(LARGEST_FILES))).all()
    row.largest_files = [LargestFile(object_name=o.object_name, size_bytes=o.size_bytes, module_code=o.module_code) for o in largest]
    grouped = await db.execute(select(StorageObject.module_code, func.sum(StorageObject.size_bytes)).where(*scope).group_by(StorageObject.module_code))
    row.module_usage = {code: int(size) for code, size in grouped.all()}
    return row


@router.get("/storage/usage", response_model=PagedResponse[StorageUsageRow])
async def storage_usage(
    search: Optional[str] = Query(None),
    tenant_level: Optional[str] = Query(None),
    state_tenant_id: Optional[str] = Query(None),
    ulb_tenant_id: Optional[str] = Query(None),
    storage_provider: Optional[str] = Query(None),
    storage_type: Optional[str] = Query(None),
    module: List[str] = Query([]),
    date_from: Optional[datetime.datetime] = Query(None),
    date_to: Optional[datetime.datetime] = Query(None),
    usage_state: Optional[str] = Query(None),
    min_percentage: Optional[float] = Query(None, ge=0),
    max_percentage: Optional[float] = Query(None, ge=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_read_db),
):
    conditions = [StorageAllocation.allocation_status == "Active"]
    for column, value in ((StorageAllocation.tenant_level, tenant_level), (StorageAllocation.state_tenant_id, state_tenant_id),
                          (StorageAllocation.ulb_tenant_id, ulb_tenant_id), (StorageAllocation.storage_provider, storage_provider),
                          (StorageAllocation.storage_type, storage_type)):
        if value:
            conditions.append(column == value)
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(StorageAllocation.allocation_name.ilike(term), StorageAllocation.tenant_id.ilike(term)))
    allocations = (await db.scalars(select(StorageAllocation).where(*conditions).order_by(StorageAllocation.allocation_name))).all()
    levels = await _levels(db)
    rows = [await _usage_row(db, a, levels, module, date_from, date_to) for a in allocations]
    # Percentage and status are calculated, so these filters run after the figures exist.
    if usage_state:
        rows = [r for r in rows if r.usage_status == usage_state]
    if min_percentage is not None:
        rows = [r for r in rows if r.utilisation_percentage is not None and r.utilisation_percentage >= min_percentage]
    if max_percentage is not None:
        rows = [r for r in rows if r.utilisation_percentage is not None and r.utilisation_percentage <= max_percentage]
    return PagedResponse(data=rows[skip:skip + limit], total=len(rows))


async def _sms_out(db: AsyncSession, row: SmsCreditAllocation) -> SmsAllocationOut:
    out = SmsAllocationOut.model_validate(row)
    out.remaining_credits = max(row.credit_allocation - row.credits_consumed, 0)
    counts = dict((await db.execute(select(SmsMessage.delivery_status, func.count(SmsMessage.id)).where(SmsMessage.allocation_id == row.id).group_by(SmsMessage.delivery_status))).all())
    out.delivered_messages, out.failed_messages = counts.get("Delivered", 0), counts.get("Failed", 0)
    finished = out.delivered_messages + out.failed_messages
    out.delivery_percentage = rules.percentage(out.delivered_messages, finished) if finished else None
    return out


@router.get("/sms/allocations", response_model=PagedResponse[SmsAllocationOut])
async def list_sms_allocations(
    search: Optional[str] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(SmsCreditAllocation.allocation_name.ilike(term), SmsCreditAllocation.tenant_id.ilike(term), SmsCreditAllocation.sms_provider.ilike(term)))
    total = await db.scalar(select(func.count(SmsCreditAllocation.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(SmsCreditAllocation).where(*conditions).order_by(SmsCreditAllocation.updated_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[await _sms_out(db, r) for r in rows], total=total)


def _apply_sms(row: SmsCreditAllocation, payload: SmsAllocationPayload, tenant_id: str) -> None:
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    row.tenant_id = tenant_id
    row.valid_from, row.valid_until = naive(payload.valid_from), naive(payload.valid_until)


@router.post("/sms/allocations", response_model=ApiResponse[SmsAllocationOut], status_code=status.HTTP_201_CREATED)
async def create_sms_allocation(payload: SmsAllocationPayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    tenant_id = await resolve_tenant(db, payload.state_tenant_id, payload.ulb_tenant_id, user)
    row = SmsCreditAllocation(created_by=operator_of(user), credits_consumed=0)
    _apply_sms(row, payload, tenant_id)
    db.add(row)
    add_audit(db, tenant_id, "SMS_ALLOCATION_SAVED", user, f"{payload.allocation_name}: {payload.credit_allocation} credits as {payload.allocation_status}.")
    await db.commit()
    return ApiResponse(data=await _sms_out(db, row))


@router.put("/sms/allocations/{allocation_id}", response_model=ApiResponse[SmsAllocationOut])
async def update_sms_allocation(allocation_id: str, payload: SmsAllocationPayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    row = await db.scalar(select(SmsCreditAllocation).where(SmsCreditAllocation.id == allocation_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Allocation not found")
    if payload.credit_allocation < row.credits_consumed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The allocation cannot be below the credits already used.")
    tenant_id = await resolve_tenant(db, payload.state_tenant_id, payload.ulb_tenant_id, user)
    _apply_sms(row, payload, tenant_id)
    add_audit(db, tenant_id, "SMS_ALLOCATION_SAVED", user, f"{payload.allocation_name}: {payload.credit_allocation} credits as {payload.allocation_status}.")
    await db.commit()
    return ApiResponse(data=await _sms_out(db, row))


def signature_is_valid(body: bytes, signature: Optional[str], secret: str) -> bool:
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)


@public_router.post("/sms/delivery-reports", status_code=status.HTTP_204_NO_CONTENT)
async def sms_delivery_report(request: Request, x_urban_signature: Optional[str] = Header(None)):
    """The provider signs each report, because this route has no signed-in user."""
    if not settings.SMS_WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SMS delivery reports are not configured.")
    body = await request.body()
    if not signature_is_valid(body, x_urban_signature, settings.SMS_WEBHOOK_SECRET):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
    report = DeliveryReport.model_validate_json(body)
    set_rls_context([], bypass=True)
    try:
        async with AsyncWriteSessionLocal() as db:
            message = await db.scalar(select(SmsMessage).where(SmsMessage.id == report.message_id))
            if not message:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
            # Delivered is final, so a late or repeated report cannot undo it.
            if message.delivery_status != "Delivered":
                message.delivery_status = report.status
                await db.commit()
    finally:
        set_rls_context([])


async def _policy_out(db: AsyncSession, row: ApiQuotaPolicy) -> ApiPolicyOut:
    out = ApiPolicyOut.model_validate(row)
    now = datetime.datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    totals = (await db.execute(select(
        func.coalesce(func.sum(ApiUsageMinute.total_requests), 0), func.coalesce(func.sum(ApiUsageMinute.successful_requests), 0),
        func.coalesce(func.sum(ApiUsageMinute.failed_requests), 0), func.coalesce(func.sum(ApiUsageMinute.throttled_requests), 0),
        func.coalesce(func.sum(ApiUsageMinute.latency_ms_total), 0),
    ).where(ApiUsageMinute.tenant_id == row.tenant_id, ApiUsageMinute.bucket >= start))).one()
    out.total_requests, out.successful_requests, out.failed_requests, out.throttled_requests = int(totals[0]), int(totals[1]), int(totals[2]), int(totals[3])
    out.average_response_ms = round(int(totals[4]) / out.total_requests, 1) if out.total_requests else None
    per_minute = select(func.sum(ApiUsageMinute.total_requests).label("n")).where(ApiUsageMinute.tenant_id == row.tenant_id, ApiUsageMinute.bucket >= start).group_by(ApiUsageMinute.bucket).subquery()
    out.peak_requests_per_minute = int(await db.scalar(select(func.max(per_minute.c.n))) or 0)
    window, limit = {rules.PERIOD_MINUTE: ("minute", row.rate_limit_per_minute), rules.PERIOD_HOUR: ("hour", row.rate_limit_per_hour), rules.PERIOD_DAY: ("day", row.rate_limit_per_day)}[row.quota_period]
    client = valkey_client.client
    if client and limit:
        try:
            used = int(await client.get(window_keys(row.tenant_id)[window][0]) or 0)
            out.remaining_quota = max(limit - used, 0)
        except Exception:
            out.remaining_quota = None
    return out


@router.get("/api/policies", response_model=PagedResponse[ApiPolicyOut])
async def list_api_policies(
    search: Optional[str] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if search and search.strip():
        conditions.append(ApiQuotaPolicy.tenant_id.ilike(f"%{search.strip()}%"))
    total = await db.scalar(select(func.count(ApiQuotaPolicy.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(ApiQuotaPolicy).where(*conditions).order_by(ApiQuotaPolicy.updated_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[await _policy_out(db, r) for r in rows], total=total)


def _apply_policy(row: ApiQuotaPolicy, payload: ApiPolicyPayload, tenant_id: str) -> None:
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    row.tenant_id = tenant_id
    row.effective_from, row.effective_until = naive(payload.effective_from), naive(payload.effective_until)
    if payload.tenant_level == "State":
        row.ulb_tenant_id = None


@router.post("/api/policies", response_model=ApiResponse[ApiPolicyOut], status_code=status.HTTP_201_CREATED)
async def create_api_policy(payload: ApiPolicyPayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    tenant_id = await resolve_tenant(db, payload.state_tenant_id, payload.ulb_tenant_id if payload.tenant_level == "ULB" else None, user)
    row = ApiQuotaPolicy(created_by=operator_of(user))
    _apply_policy(row, payload, tenant_id)
    db.add(row)
    add_audit(db, tenant_id, "API_POLICY_SAVED", user, f"API policy at {payload.rate_limit_per_minute}/min saved as {payload.policy_status}.")
    await db.commit()
    clear_policy_cache()
    return ApiResponse(data=await _policy_out(db, row))


@router.put("/api/policies/{policy_id}", response_model=ApiResponse[ApiPolicyOut])
async def update_api_policy(policy_id: str, payload: ApiPolicyPayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    row = await db.scalar(select(ApiQuotaPolicy).where(ApiQuotaPolicy.id == policy_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    tenant_id = await resolve_tenant(db, payload.state_tenant_id, payload.ulb_tenant_id if payload.tenant_level == "ULB" else None, user)
    _apply_policy(row, payload, tenant_id)
    add_audit(db, tenant_id, "API_POLICY_SAVED", user, f"API policy at {payload.rate_limit_per_minute}/min saved as {payload.policy_status}.")
    await db.commit()
    clear_policy_cache()
    return ApiResponse(data=await _policy_out(db, row))
