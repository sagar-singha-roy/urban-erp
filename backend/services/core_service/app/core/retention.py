"""Enforces audit retention policies without breaking the hash chain."""
import datetime
import gzip
import json
import logging
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.db.models import AuditRetentionPolicyModel, ImmutableAuditEventModel
from app.db.session import AsyncWriteSessionLocal

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000
UNIT_DAYS = {"Days": 1, "Months": 30, "Years": 365}


def retention_days(period: int, unit: str) -> int:
    return period * UNIT_DAYS.get(unit, 365)


def expired_prefix(events, policies, now):
    """Oldest events that every matching policy has released, stopping at the first one that must stay.

    Only a contiguous oldest run is removed, so the remaining hash chain still verifies.
    An event no active policy covers is kept.
    """
    removable = []
    for event in events:
        matching = [
            p for p in policies
            if not p.event_categories or event.event_category in p.event_categories
        ]
        if not matching or event.is_legal_hold or any(p.legal_hold_enabled for p in matching):
            break
        keep_days = max(retention_days(p.retention_period, p.retention_unit) for p in matching)
        if event.created_at >= now - datetime.timedelta(days=keep_days):
            break
        removable.append(event)
    return removable


def _archive(events) -> str:
    directory = Path(settings.BACKUP_DIR).resolve() / "audit-archive"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / f"audit-{events[0].sequence_number}-{events[-1].sequence_number}.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for e in events:
            handle.write(json.dumps({
                "eventId": e.event_id,
                "sequence": e.sequence_number,
                "createdAt": e.created_at.isoformat(),
                "category": e.event_category,
                "action": e.action,
                "actorId": e.actor_id,
                "tenantId": e.tenant_id,
                "result": e.result,
                "details": e.details,
                "prevEventHash": e.prev_event_hash,
                "eventHash": e.event_hash,
                "signature": e.signature,
            }) + "\n")
    path.chmod(0o600)
    return str(path)


async def enforce_audit_retention() -> int:
    from app.api.v1.audit_vault import record_immutable_audit_event

    async with AsyncWriteSessionLocal() as db:
        policies = (await db.scalars(
            select(AuditRetentionPolicyModel).where(AuditRetentionPolicyModel.policy_status == "Active")
        )).all()
        if not policies:
            return 0
        events = (await db.scalars(
            select(ImmutableAuditEventModel).order_by(ImmutableAuditEventModel.sequence_number).limit(BATCH_SIZE)
        )).all()
        removable = expired_prefix(events, policies, datetime.datetime.utcnow())
        if not removable:
            return 0
        archive = _archive(removable) if any(p.archive_required for p in policies) else None
        first, last = removable[0].sequence_number, removable[-1].sequence_number
        for event in removable:
            await db.delete(event)
        await db.flush()
        await record_immutable_audit_event(
            db=db,
            event_category="Administrative Actions",
            action="AUDIT_RETENTION_ENFORCED",
            actor_id="system.retention",
            actor_role="System",
            details={"removed": len(removable), "firstSequence": first, "lastSequence": last, "archive": archive},
        )
        await db.commit()
        return len(removable)
