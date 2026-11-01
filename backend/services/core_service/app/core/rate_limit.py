"""Failed sign-in throttling, shared through Redis when it is connected and per process otherwise."""
import logging
import time
from typing import Dict, List

from app.core.redis import redis_client

logger = logging.getLogger(__name__)

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60

_failures: Dict[str, List[float]] = {}


def retry_after(key: str) -> int:
    """Seconds the caller must wait, or 0 when another attempt is allowed."""
    now = time.monotonic()
    recent = [at for at in _failures.get(key, []) if now - at < WINDOW_SECONDS]
    if recent:
        _failures[key] = recent
    else:
        _failures.pop(key, None)
    if len(recent) < MAX_FAILURES:
        return 0
    return int(WINDOW_SECONDS - (now - recent[0])) + 1


def record_failure(key: str) -> None:
    _failures.setdefault(key, []).append(time.monotonic())


def clear(key: str) -> None:
    _failures.pop(key, None)


def _redis_key(key: str) -> str:
    return f"ratelimit:signin:{key}"


async def check(key: str) -> int:
    if redis_client.redis:
        try:
            count = int(await redis_client.redis.get(_redis_key(key)) or 0)
            if count < MAX_FAILURES:
                return 0
            return max(int(await redis_client.redis.ttl(_redis_key(key))), 1)
        except Exception as exc:
            logger.warning("Redis rate limit check failed: %s", exc)
    return retry_after(key)


async def fail(key: str) -> None:
    if redis_client.redis:
        try:
            count = await redis_client.redis.incr(_redis_key(key))
            if count == 1:
                await redis_client.redis.expire(_redis_key(key), WINDOW_SECONDS)
            return
        except Exception as exc:
            logger.warning("Redis rate limit update failed: %s", exc)
    record_failure(key)


async def reset(key: str) -> None:
    if redis_client.redis:
        try:
            await redis_client.redis.delete(_redis_key(key))
        except Exception as exc:
            logger.warning("Redis rate limit reset failed: %s", exc)
    clear(key)
