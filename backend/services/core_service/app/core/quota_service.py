"""Storage and SMS enforcement. Both lock their allocation rows, so simultaneous requests cannot overshoot."""
import datetime
from typing import List, Optional, Protocol

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.quota_rules import is_effective
from app.db.models import SmsCreditAllocation, SmsMessage, StateTenant, StorageAllocation, StorageObject, Tenant


class QuotaExceeded(Exception):
    """The message is safe to show to the user."""


class SmsNotConnected(Exception):
    pass


class SmsProvider(Protocol):
    async def send(self, *, to: str, text: str, sender_id: Optional[str], template_id: Optional[str], reference: str) -> None: ...


# No provider account exists yet. Registering one here is what connects SMS.
_sms_adapter: Optional[SmsProvider] = None


def register_sms_provider(adapter: Optional[SmsProvider]) -> None:
    global _sms_adapter
    _sms_adapter = adapter


def sms_connected() -> bool:
    return _sms_adapter is not None


async def state_of(db: AsyncSession, tenant_id: str) -> Optional[str]:
    ulb = await db.scalar(select(Tenant).where(Tenant.tenant_id == tenant_id))
    if not ulb:
        return None
    return ulb.parent_state_tenant_id or await db.scalar(select(StateTenant.tenant_id).where(StateTenant.state_code == ulb.state_code))


async def tenants_under(db: AsyncSession, allocation_tenant: str) -> List[str]:
    """A state's allocation counts its own files and those of all its ULBs."""
    state = await db.scalar(select(StateTenant).where(StateTenant.tenant_id == allocation_tenant))
    if not state:
        return [allocation_tenant]
    children = (await db.scalars(select(Tenant.tenant_id).where(
        or_(Tenant.parent_state_tenant_id == allocation_tenant, Tenant.state_code == state.state_code)
    ))).all()
    return [allocation_tenant, *children]


async def used_bytes(db: AsyncSession, allocation: StorageAllocation) -> int:
    tenants = await tenants_under(db, allocation.tenant_id)
    return int(await db.scalar(select(func.coalesce(func.sum(StorageObject.size_bytes), 0)).where(
        StorageObject.tenant_id.in_(tenants), StorageObject.storage_type == allocation.storage_type,
    )) or 0)


async def reserve_storage(
    db: AsyncSession, *, tenant_id: str, storage_type: str, module_code: str, object_name: str, size_bytes: int, file_type: str,
) -> StorageObject:
    """Call inside the transaction that stores the file. Until a tenant has an allocation its files are recorded but not limited."""
    state_id = await state_of(db, tenant_id)
    now = datetime.datetime.utcnow()
    rows = (await db.scalars(
        select(StorageAllocation).where(
            StorageAllocation.tenant_id.in_([t for t in (tenant_id, state_id) if t]),
            StorageAllocation.storage_type == storage_type,
            StorageAllocation.allocation_status == "Active",
        ).order_by(StorageAllocation.id).with_for_update()
    )).all()
    allocations = [a for a in rows if is_effective(a.effective_from, a.effective_until, now)]
    # The tenant's own allocation is first: its file rules apply, and every allocation's total must hold.
    allocations.sort(key=lambda a: a.tenant_id != tenant_id)
    if allocations:
        rule = allocations[0]
        if size_bytes > rule.max_file_size_mb * 1024 * 1024:
            raise QuotaExceeded(f"This file is larger than the {rule.max_file_size_mb:g} MB limit.")
        if file_type not in rule.allowed_file_types:
            raise QuotaExceeded(f"{file_type.upper()} files are not allowed by this storage allocation.")
    for allocation in allocations:
        if await used_bytes(db, allocation) + size_bytes > allocation.allocation_bytes:
            raise QuotaExceeded("This organisation has used its storage allocation.")
        module_limit = next((m for m in allocation.module_allocations or [] if m.get("moduleCode") == module_code), None)
        if module_limit:
            module_used = int(await db.scalar(select(func.coalesce(func.sum(StorageObject.size_bytes), 0)).where(
                StorageObject.tenant_id.in_(await tenants_under(db, allocation.tenant_id)),
                StorageObject.storage_type == storage_type, StorageObject.module_code == module_code,
            )) or 0)
            if module_used + size_bytes > module_limit["allocationBytes"]:
                raise QuotaExceeded(f"The {module_code} module has used its storage allocation.")
    record = StorageObject(tenant_id=tenant_id, storage_type=storage_type, module_code=module_code, object_name=object_name[:255], size_bytes=size_bytes)
    db.add(record)
    await db.flush()
    return record


async def consume_sms_credits(db: AsyncSession, *, tenant_id: str, category: Optional[str] = None, credits: int = 1) -> SmsMessage:
    """Takes the credits before anything is sent. No active, in-date allocation means no message."""
    now = datetime.datetime.utcnow()
    rows = (await db.scalars(
        select(SmsCreditAllocation).where(SmsCreditAllocation.tenant_id == tenant_id, SmsCreditAllocation.allocation_status == "Active")
        .order_by(SmsCreditAllocation.valid_until).with_for_update()
    )).all()
    for allocation in rows:
        if not is_effective(allocation.valid_from, allocation.valid_until, now):
            continue
        if category and allocation.sms_categories and category not in allocation.sms_categories:
            continue
        if allocation.credits_consumed + credits > allocation.credit_allocation:
            continue
        allocation.credits_consumed += credits
        message = SmsMessage(tenant_id=tenant_id, allocation_id=allocation.id, category=category, credits=credits)
        db.add(message)
        await db.flush()
        return message
    raise QuotaExceeded("This organisation has no SMS credits available.")


async def send_sms(db: AsyncSession, *, tenant_id: str, to: str, text: str, category: Optional[str] = None, credits: int = 1) -> SmsMessage:
    if not _sms_adapter:
        raise SmsNotConnected("No SMS provider is connected.")
    message = await consume_sms_credits(db, tenant_id=tenant_id, category=category, credits=credits)
    allocation = await db.scalar(select(SmsCreditAllocation).where(SmsCreditAllocation.id == message.allocation_id))
    await _sms_adapter.send(to=to, text=text, sender_id=allocation.sender_id, template_id=allocation.dlt_template_id, reference=message.id)
    message.delivery_status = "Sent"
    return message
