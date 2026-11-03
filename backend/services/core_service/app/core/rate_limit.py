"""Failed sign-in throttling, shared through Valkey when it is connected and per process otherwise."""
import logging
import time
from typing import Dict, List

from app.core.valkey import valkey_client

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


def _cache_key(key: str) -> str:
    return f"ratelimit:signin:{key}"


async def check(key: str) -> int:
    if valkey_client.client:
        try:
            count = int(await valkey_client.client.get(_cache_key(key)) or 0)
            if count < MAX_FAILURES:
                return 0
            return max(int(await valkey_client.client.ttl(_cache_key(key))), 1)
        except Exception as exc:
            logger.warning("Valkey rate limit check failed: %s", exc)
    return retry_after(key)


async def fail(key: str) -> None:
    if valkey_client.client:
        try:
            count = await valkey_client.client.incr(_cache_key(key))
            if count == 1:
                await valkey_client.client.expire(_cache_key(key), WINDOW_SECONDS)
            return
        except Exception as exc:
            logger.warning("Valkey rate limit update failed: %s", exc)
    record_failure(key)


async def reset(key: str) -> None:
    if valkey_client.client:
        try:
            await valkey_client.client.delete(_cache_key(key))
        except Exception as exc:
            logger.warning("Valkey rate limit reset failed: %s", exc)
    clear(key)
