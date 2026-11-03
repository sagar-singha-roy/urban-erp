"""Records a module service's real request outcomes under the tenant core_service named.

Key and field formats match app/core/api_quota.py in core_service, whose worker saves them.
"""
import logging
import time

from urban_common.cache import scoped_key, valkey_client

logger = logging.getLogger(__name__)


def usage_key(tenant_id: str, minute: int) -> str:
    return scoped_key(tenant_id, None, f"apiusage:{minute}")


def concurrent_key(tenant_id: str) -> str:
    return scoped_key(tenant_id, None, "apiconcurrent")


class ApiMeteringMiddleware:
    def __init__(self, inner, service: str):
        self.inner = inner
        self.service = service

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.inner(scope, receive, send)
            return
        started = time.monotonic()
        code = {"value": 500}

        async def capture(message):
            if message["type"] == "http.response.start":
                code["value"] = message["status"]
            await send(message)

        try:
            await self.inner(scope, receive, capture)
        finally:
            await self._record(scope, code["value"], int((time.monotonic() - started) * 1000))

    async def _record(self, scope, status_code: int, elapsed_ms: int) -> None:
        state = scope.get("state") or {}
        client = valkey_client.client
        tenant_id = state.get("quota_tenant")
        if not client or not tenant_id:
            return
        outcome = "throttled" if status_code == 429 else "failed" if status_code >= 400 else "success"
        try:
            if state.get("quota_concurrent_key"):
                await client.decr(state["quota_concurrent_key"])
            key = usage_key(tenant_id, int(time.time() // 60))
            pipe = client.pipeline()
            pipe.hincrby(key, f"{self.service}|total", 1)
            pipe.hincrby(key, f"{self.service}|{outcome}", 1)
            pipe.hincrby(key, f"{self.service}|latency", elapsed_ms)
            pipe.expire(key, 86400)
            await pipe.execute()
        except Exception as exc:
            logger.warning("API metering skipped: %s", type(exc).__name__)
