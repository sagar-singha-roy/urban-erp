"""Failed sign-in throttling. Counts are per process, so run one limiter per worker's share of traffic."""
import time
from typing import Dict, List

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
