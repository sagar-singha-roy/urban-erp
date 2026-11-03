"""ADM-R02 upkeep: marks grants past their end date as Expired and records it.

Requests already stop honouring a grant at its end date. This only brings the stored status into line.
"""
import asyncio
import datetime
import logging

from sqlalchemy import select

from app.core import cross_tenant_rules as rules
from app.core.cross_tenant_history import record_change
from app.core.tenant_context import set_rls_context
from app.db.models import CrossTenantAccessGrant
from app.db.session import AsyncWriteSessionLocal

logger = logging.getLogger(__name__)

TICK_SECONDS = 60
SYSTEM_ACTOR = "system"


async def expire_grants(db, now: datetime.datetime) -> int:
    grants = (await db.scalars(select(CrossTenantAccessGrant).where(
        CrossTenantAccessGrant.status == rules.STATUS_ACTIVE,
        CrossTenantAccessGrant.effective_until.is_not(None),
        CrossTenantAccessGrant.effective_until < now,
    ))).all()
    for grant in grants:
        grant.status = rules.STATUS_EXPIRED
        await record_change(db, grant, "EXPIRED", SYSTEM_ACTOR, None, reason="The end date passed.", previous_level=grant.access_level)
    return len(grants)


async def run_once() -> None:
    set_rls_context([], bypass=True)
    async with AsyncWriteSessionLocal() as db:
        await expire_grants(db, datetime.datetime.utcnow())
        await db.commit()


async def cross_tenant_loop() -> None:
    while True:
        await asyncio.sleep(TICK_SECONDS)
        try:
            await run_once()
        except Exception:
            logger.exception("Cross-tenant access upkeep failed")
