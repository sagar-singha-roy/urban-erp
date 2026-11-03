"""Background work for ADM-S04: saves API metering and evaluates usage alerts against real figures."""
import asyncio
import datetime
import logging
import smtplib
import time
import uuid
from email.message import EmailMessage
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.core import quota_rules as rules
from app.core.api_quota import concurrent_key, policy_for, window_keys
from app.core.config import settings
from app.core.quota_service import used_bytes
from app.core.tenant_context import set_rls_context
from app.core.valkey import valkey_client
from app.db.models import (
    ApiUsageMinute, SmsCreditAllocation, StorageAllocation, UsageAlertEvent, UsageAlertRule, UsageThresholdLevel, User,
)
from app.db.session import AsyncWriteSessionLocal

logger = logging.getLogger(__name__)

TICK_SECONDS = 60


async def ensure_default_levels(db) -> None:
    if not await db.scalar(select(func.count(UsageThresholdLevel.id))):
        db.add_all([UsageThresholdLevel(level_name=name, percentage=value) for name, value in rules.DEFAULT_LEVELS])
        await db.commit()


def parse_usage_hash(values: dict) -> dict:
    services: dict = {}
    for field, amount in values.items():
        service, metric = field.split("|", 1)
        services.setdefault(service, {})[metric] = int(amount)
    return services


async def flush_api_usage(db) -> None:
    client = valkey_client.client
    if not client:
        return
    current = int(time.time() // 60)
    async for key in client.scan_iter(match="stats:tenant:*:sub:ALL:apiusage:*", count=200):
        minute = int(key.rsplit(":", 1)[1])
        # The current minute is still being written.
        if minute >= current:
            continue
        tenant_id = key.split(":")[2]
        bucket = datetime.datetime.utcfromtimestamp(minute * 60)
        for service, metrics in parse_usage_hash(await client.hgetall(key)).items():
            values = dict(
                total_requests=metrics.get("total", 0), successful_requests=metrics.get("success", 0),
                failed_requests=metrics.get("failed", 0), throttled_requests=metrics.get("throttled", 0),
                latency_ms_total=metrics.get("latency", 0),
            )
            statement = insert(ApiUsageMinute).values(id=str(uuid.uuid4()), tenant_id=tenant_id, service=service, bucket=bucket, **values)
            await db.execute(statement.on_conflict_do_update(
                constraint="uq_api_usage_minute",
                set_={name: getattr(ApiUsageMinute, name) + getattr(statement.excluded, name) for name in values},
            ))
        await db.commit()
        await client.delete(key)


async def current_usage(db, rule: UsageAlertRule) -> Optional[Tuple[float, float]]:
    """(value, percentage) from real sources, or None when nothing can be measured."""
    now = datetime.datetime.utcnow()
    if rule.resource_type == rules.RESOURCE_STORAGE:
        rows = (await db.scalars(select(StorageAllocation).where(StorageAllocation.tenant_id == rule.tenant_id, StorageAllocation.allocation_status == "Active"))).all()
        measured = [a for a in rows if a.storage_provider in rules.MEASURED_PROVIDERS and rules.is_effective(a.effective_from, a.effective_until, now)]
        if not measured:
            return None
        used = sum([await used_bytes(db, a) for a in measured])
        return float(used), rules.percentage(used, sum(a.allocation_bytes for a in measured))
    if rule.resource_type == rules.RESOURCE_SMS:
        rows = (await db.scalars(select(SmsCreditAllocation).where(SmsCreditAllocation.tenant_id == rule.tenant_id, SmsCreditAllocation.allocation_status == "Active"))).all()
        rows = [a for a in rows if rules.is_effective(a.valid_from, a.valid_until, now)]
        if not rows:
            return None
        used = sum(a.credits_consumed for a in rows)
        return float(used), rules.percentage(used, sum(a.credit_allocation for a in rows))
    client = valkey_client.client
    policy = await policy_for(rule.tenant_id)
    if not client or not policy:
        return None
    if rule.resource_type == rules.RESOURCE_CONCURRENT:
        used = int(await client.get(concurrent_key(rule.tenant_id)) or 0)
        return float(used), rules.percentage(used, policy.get("concurrent") or 0)
    used = int(await client.get(window_keys(rule.tenant_id)["minute"][0]) or 0)
    return float(used), rules.percentage(used, policy["minute"])


def rule_matches(rule: UsageAlertRule, value: float, percent: float) -> bool:
    if rule.alert_condition == rules.CONDITION_PERCENT:
        return rule.threshold_percentage is not None and rules.compare(percent, rule.comparison_operator, rule.threshold_percentage)
    return rule.threshold_value is not None and rules.compare(value, rule.comparison_operator, rule.threshold_value)


def should_notify(rule: UsageAlertRule, now: datetime.datetime) -> bool:
    if not rule.is_firing:
        return True
    if not rule.repeat_interval_minutes or not rule.last_notified_at:
        return False
    return now - rule.last_notified_at >= datetime.timedelta(minutes=rule.repeat_interval_minutes)


def _send_email(recipients: List[str], subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"], message["From"], message["To"] = subject, settings.SMTP_FROM, ", ".join(recipients)
    message.set_content(body)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        server.send_message(message)


async def deliver(db, tenant_id: str, severity: str, text: str, channels: List[str], recipient_ids: List[str], rule_id: Optional[str] = None) -> None:
    results = []
    if rules.CHANNEL_IN_APP in channels:
        results.append("In-App delivered")
    if rules.CHANNEL_EMAIL in channels:
        emails = (await db.scalars(select(User.email).where(User.id.in_(recipient_ids)))).all() if recipient_ids else []
        if not settings.SMTP_HOST or not emails:
            results.append("Email not sent")
        else:
            try:
                await asyncio.to_thread(_send_email, list(emails), f"[{severity}] Usage alert", text)
                results.append("Email sent")
            except Exception as exc:
                logger.error("Alert email failed: %s", type(exc).__name__)
                results.append("Email failed")
    if rules.CHANNEL_SMS in channels:
        results.append("SMS not sent")
    db.add(UsageAlertEvent(tenant_id=tenant_id, rule_id=rule_id, severity=severity, message=text[:500], delivery_summary=", ".join(results)[:255]))


async def evaluate_alerts(db) -> None:
    now = datetime.datetime.utcnow()
    for rule in (await db.scalars(select(UsageAlertRule).where(UsageAlertRule.is_active.is_(True)))).all():
        usage = await current_usage(db, rule)
        if usage is None:
            continue
        value, percent = usage
        rule.last_value = percent if rule.alert_condition == rules.CONDITION_PERCENT else value
        if not rule_matches(rule, value, percent):
            rule.is_firing = False
            continue
        if should_notify(rule, now):
            text = f"{rule.alert_name}: {rule.resource_type} for {rule.tenant_id} is at {percent:g}% ({value:g})."
            await deliver(db, rule.tenant_id, rule.alert_severity, text, rule.notification_channels, rule.notification_recipients, rule.id)
            rule.last_notified_at = now
        rule.is_firing = True
    for allocation in (await db.scalars(select(SmsCreditAllocation).where(SmsCreditAllocation.allocation_status == "Active", SmsCreditAllocation.low_credit_threshold.is_not(None)))).all():
        remaining = allocation.credit_allocation - allocation.credits_consumed
        if remaining > allocation.low_credit_threshold:
            allocation.low_credit_notified = False
        elif not allocation.low_credit_notified:
            channels = [rules.CHANNEL_IN_APP, rules.CHANNEL_EMAIL] if settings.SMTP_HOST else [rules.CHANNEL_IN_APP]
            await deliver(db, allocation.tenant_id, "High", f"{allocation.allocation_name}: {remaining} SMS credits remain.", channels, allocation.notification_recipients)
            allocation.low_credit_notified = True


async def run_once() -> None:
    set_rls_context([], bypass=True)
    async with AsyncWriteSessionLocal() as db:
        await ensure_default_levels(db)
        await flush_api_usage(db)
        await evaluate_alerts(db)
        await db.commit()


async def quota_loop() -> None:
    while True:
        await asyncio.sleep(TICK_SECONDS)
        try:
            await run_once()
        except Exception:
            logger.exception("Quota upkeep failed")
