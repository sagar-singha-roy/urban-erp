"""Counters and process readings measured by this API instance since it started."""
from typing import Optional

import psutil

_process = psutil.Process()
_process.cpu_percent(interval=None)  # The first reading only sets the baseline.
_requests = 0
_server_errors = 0


def record_response(status_code: int) -> None:
    global _requests, _server_errors
    _requests += 1
    if status_code >= 500:
        _server_errors += 1


def error_rate_pct() -> Optional[float]:
    return round(_server_errors / _requests * 100, 2) if _requests else None


def cpu_pct() -> float:
    return round(_process.cpu_percent(interval=None), 1)


def memory_pct() -> float:
    return round(_process.memory_percent(), 1)
