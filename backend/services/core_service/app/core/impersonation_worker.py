"""ADM-R04 upkeep: marks timed-out sessions and unused approvals as Expired, and records it.

Requests already stop honouring a session at its expiry. This only brings the stored status into line.
"""
import asyncio
import datetime
import logging

from sqlalchemy import select

from app.api.v1.audit_vault import record_immutable_audit_event
from app.core import impersonation_rules as rules
from app.core.tenant_context import set_rls_context
from app.db.models import ImpersonationRequest, ImpersonationSession
from app.db.session import AsyncWriteSessionLocal

logger = logging.getLogger(__name__)

TICK_SECONDS = 30
SYSTEM_ACTOR = "system"


async def expire(db, now: datetime.datetime) -> tuple:
    sessions = (await db.scalars(select(ImpersonationSession).where(
        ImpersonationSession.status == rules.SESSION_ACTIVE, ImpersonationSession.expires_at <= now,
    ))).all()
    for session in sessions:
        session.status, session.ended_at, session.termination_reason = rules.SESSION_EXPIRED, session.expires_at, "The session reached its time limit."
        await record_immutable_audit_event(db, event_category="Authentication", action="IMPERSONATION_SESSION_EXPIRED", actor_id=SYSTEM_ACTOR,
                                           tenant_id=session.tenant_id, severity="Medium", ip_address="system",
                                           details={"sessionId": session.id, "agent": session.support_email, "target": session.target_email})
    requests = (await db.scalars(select(ImpersonationRequest).where(
        ImpersonationRequest.status == rules.REQ_APPROVED, ImpersonationRequest.approval_valid_until.is_not(None),
        ImpersonationRequest.approval_valid_until < now,
    ))).all()
    for request in requests:
        request.status = rules.REQ_EXPIRED
    return len(sessions), len(requests)


async def run_once() -> None:
    set_rls_context([], bypass=True)
    async with AsyncWriteSessionLocal() as db:
        await expire(db, datetime.datetime.utcnow())
        await db.commit()


async def impersonation_loop() -> None:
    while True:
        await asyncio.sleep(TICK_SECONDS)
        try:
            await run_once()
        except Exception:
            logger.exception("Support session upkeep failed")
