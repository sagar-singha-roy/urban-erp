"""Kafka events through a transactional outbox, with idempotent consumers.

A service writes its event in the same transaction as its data, and a relay publishes it
afterwards, so an event is never lost and never announces a change that was rolled back.
"""
import asyncio
import datetime
import json
import logging
import uuid
from typing import Any, Awaitable, Callable, Dict, Iterable

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from urban_common.db import SessionLocal
from urban_common.settings import settings

logger = logging.getLogger(__name__)
RELAY_INTERVAL_SECONDS = 2.0
RELAY_BATCH_SIZE = 100
RETRY_SECONDS = 10.0


def topic_name(module: str, entity: str, event: str, version: int = 1) -> str:
    return f"urban.{module}.{entity}.{event}.v{version}"


async def add_to_outbox(db: AsyncSession, service: str, topic: str, key: str, tenant_id: str, data: Dict[str, Any]) -> str:
    """Call before the caller's commit: the event then shares that transaction."""
    event_id = str(uuid.uuid4())
    payload = {
        "eventId": event_id,
        "topic": topic,
        "tenantId": tenant_id,
        "occurredAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "data": data,
    }
    await db.execute(
        text(
            "INSERT INTO event_outbox (id, source_service, topic, event_key, tenant_id, payload) "
            "VALUES (:id, :service, :topic, :key, :tenant_id, CAST(:payload AS json))"
        ),
        {"id": event_id, "service": service, "topic": topic, "key": key, "tenant_id": tenant_id, "payload": json.dumps(payload)},
    )
    return event_id


async def publish_pending(producer: Any, service: str) -> int:
    """Publishes one batch. SKIP LOCKED lets several replicas of a service run this safely."""
    async with SessionLocal() as db:
        rows = (
            await db.execute(
                text(
                    "SELECT id, topic, event_key, payload FROM event_outbox "
                    "WHERE source_service = :service AND published_at IS NULL "
                    "ORDER BY created_at LIMIT :limit FOR UPDATE SKIP LOCKED"
                ),
                {"service": service, "limit": RELAY_BATCH_SIZE},
            )
        ).all()
        for row in rows:
            await producer.send_and_wait(row.topic, json.dumps(row.payload).encode(), key=row.event_key.encode())
            await db.execute(text("UPDATE event_outbox SET published_at = now() WHERE id = :id"), {"id": row.id})
        await db.commit()
        return len(rows)


async def relay_loop(service: str) -> None:
    """Keeps retrying while Kafka is down: events wait safely in the outbox."""
    producer = None
    while True:
        try:
            if producer is None:
                candidate = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS, acks="all", enable_idempotence=True)
                await candidate.start()
                producer = candidate
                logger.info("Connected to Kafka for %s.", service)
            if not await publish_pending(producer, service):
                await asyncio.sleep(RELAY_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            if producer:
                await producer.stop()
            raise
        except (KafkaError, OSError) as exc:
            logger.warning("Kafka unavailable for %s: %s", service, exc)
            await asyncio.sleep(RETRY_SECONDS)
        except Exception:
            logger.exception("Event relay failed for %s.", service)
            await asyncio.sleep(RETRY_SECONDS)


async def handle_once(service: str, event: Dict[str, Any], handler: Callable[[Dict[str, Any], AsyncSession], Awaitable[None]]) -> bool:
    """Runs the handler and records the event in one transaction, so a redelivery is skipped."""
    async with SessionLocal() as db:
        inserted = await db.execute(
            text(
                "INSERT INTO event_inbox (consumer_service, event_id) VALUES (:service, :event_id) "
                "ON CONFLICT DO NOTHING RETURNING event_id"
            ),
            {"service": service, "event_id": event["eventId"]},
        )
        if inserted.first() is None:
            return False
        await handler(event, db)
        await db.commit()
        return True


async def consume_loop(service: str, topics: Iterable[str], handler: Callable[[Dict[str, Any], AsyncSession], Awaitable[None]]) -> None:
    """Commits the Kafka offset only after the handler's transaction, so failures are redelivered."""
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=service,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for message in consumer:
            await handle_once(service, json.loads(message.value), handler)
            await consumer.commit()
    finally:
        await consumer.stop()
