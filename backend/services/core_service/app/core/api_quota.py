"""Per-tenant API limits and metering, shared across instances through Valkey.

If Valkey is unavailable limits stop applying and that is logged: a cache outage must not stop municipal services.
"""
import asyncio
import datetime
import logging
import time
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, Request, status
from sqlalchemy import select

from app.core.quota_rules import is_effective
from app.core.tenant_context import set_rls_context
from app.core.valkey import valkey_client
from app.db.models import ApiQuotaPolicy, StateTenant, Tenant

logger = logging.getLogger(__name__)

POLICY_CACHE_SECONDS = 30
AUTHORIZE_PATH = "/auth/authorize"
_policies: Dict[str, Tuple[float, Optional[dict]]] = {}


def counter_key(tenant_id: str, resource: str) -> str:
    return f"stats:tenant:{tenant_id}:sub:ALL:{resource}"


def window_keys(tenant_id: str, now: Optional[float] = None) -> Dict[str, Tuple[str, int]]:
    now = time.time() if now is None else now
    return {
        "second": (counter_key(tenant_id, f"apirate:s:{int(now)}"), 5),
        "minute": (counter_key(tenant_id, f"apirate:m:{int(now // 60)}"), 120),
        "hour": (counter_key(tenant_id, f"apirate:h:{int(now // 3600)}"), 7200),
        "day": (counter_key(tenant_id, f"apirate:d:{int(now // 86400)}"), 172800),
    }


def concurrent_key(tenant_id: str) -> str:
    return counter_key(tenant_id, "apiconcurrent")


def service_of(request: Request) -> str:
    """The module for a service's authorization call, otherwise the first path segment after the version."""
    if request.url.path.endswith(AUTHORIZE_PATH):
        return (request.query_params.get("component") or "module").split("-")[0].lower()
    parts = [p for p in request.url.path.split("/") if p]
    return parts[2] if len(parts) > 2 else "core"


def token_tenant(user: Dict) -> str:
    """From the signed token, never a request header, so a client cannot choose whose limit applies."""
    return str(user.get("tenant_id") or "").split(",")[0].strip()


async def _load_policy(tenant_id: str) -> Optional[dict]:
    from app.db.session import AsyncReadSessionLocal

    # Runs in its own task, so this bypass cannot reach the caller's request context.
    set_rls_context([], bypass=True)
    async with AsyncReadSessionLocal() as db:
        tenant_ids = [tenant_id]
        ulb = await db.scalar(select(Tenant).where(Tenant.tenant_id == tenant_id))
        if ulb:
            state_id = ulb.parent_state_tenant_id or await db.scalar(select(StateTenant.tenant_id).where(StateTenant.state_code == ulb.state_code))
            if state_id:
                tenant_ids.append(state_id)
        now = datetime.datetime.utcnow()
        for candidate in tenant_ids:
            rows = (await db.scalars(
                select(ApiQuotaPolicy).where(ApiQuotaPolicy.tenant_id == candidate, ApiQuotaPolicy.policy_status == "Active")
                .order_by(ApiQuotaPolicy.effective_from.desc())
            )).all()
            policy = next((r for r in rows if is_effective(r.effective_from, r.effective_until, now)), None)
            if policy:
                return {
                    "services": policy.api_services or [], "minute": policy.rate_limit_per_minute, "hour": policy.rate_limit_per_hour,
                    "day": policy.rate_limit_per_day, "second": policy.burst_limit, "concurrent": policy.concurrent_limit,
                }
    return None


async def policy_for(tenant_id: str) -> Optional[dict]:
    cached = _policies.get(tenant_id)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    policy = await asyncio.create_task(_load_policy(tenant_id))
    _policies[tenant_id] = (time.monotonic() + POLICY_CACHE_SECONDS, policy)
    return policy


def clear_policy_cache() -> None:
    _policies.clear()


WINDOW_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def exceeded_window(counts: Dict[str, int], policy: dict) -> Optional[str]:
    for window in ("second", "minute", "hour", "day"):
        limit = policy.get(window)
        if limit and counts.get(window, 0) > limit:
            return window
    return None


async def enforce(request: Request, user: Dict) -> None:
    """Called once per authenticated request. Platform administrators are exempt so they can fix a limited tenant."""
    client = valkey_client.client
    tenant_id = token_tenant(user)
    if not client or not tenant_id or "super_admin" in user.get("realm_access", {}).get("roles", []):
        return
    request.state.quota_tenant = tenant_id
    request.state.quota_service = service_of(request)
    try:
        policy = await policy_for(tenant_id)
        if not policy or (policy["services"] and request.state.quota_service not in policy["services"]):
            return
        keys = window_keys(tenant_id)
        pipe = client.pipeline()
        for key, ttl in keys.values():
            pipe.incr(key)
            pipe.expire(key, ttl)
        results = await pipe.execute()
        counts = {window: int(results[i * 2]) for i, window in enumerate(keys)}
    except Exception as exc:
        logger.error("API quota check skipped for %s: %s", tenant_id, type(exc).__name__)
        return
    window = exceeded_window(counts, policy)
    if window:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"This organisation has reached its API limit ({window}).",
            headers={"Retry-After": str(WINDOW_SECONDS[window])},
        )
    limit = policy.get("concurrent")
    # A module service holds the concurrency slot itself, because it knows when its work finishes.
    if limit and request.url.path.endswith(AUTHORIZE_PATH):
        request.state.quota_concurrent_limit = limit
    elif limit:
        key = concurrent_key(tenant_id)
        try:
            current = await client.incr(key)
            await client.expire(key, 300)
        except Exception:
            return
        if current > limit:
            await client.decr(key)
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="This organisation has too many requests in progress.", headers={"Retry-After": "1"})
        request.state.quota_concurrent_key = key


def usage_hash_key(tenant_id: str, minute: int) -> str:
    return counter_key(tenant_id, f"apiusage:{minute}")


def metric_fields(service: str, status_code: int, elapsed_ms: int) -> List[Tuple[str, int]]:
    outcome = "throttled" if status_code == 429 else "failed" if status_code >= 400 else "success"
    return [(f"{service}|total", 1), (f"{service}|{outcome}", 1), (f"{service}|latency", elapsed_ms)]


class ApiMeteringMiddleware:
    """Records each tenant request's outcome, and releases its concurrency slot however it ended."""

    def __init__(self, inner):
        self.inner = inner

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
        try:
            if state.get("quota_concurrent_key"):
                await client.decr(state["quota_concurrent_key"])
            # The module service records its own outcome. Its authorization call only counts when it refused the request.
            if scope["path"].endswith(AUTHORIZE_PATH) and status_code != 429:
                return
            key = usage_hash_key(tenant_id, int(time.time() // 60))
            pipe = client.pipeline()
            for field, amount in metric_fields(state.get("quota_service") or "core", status_code, elapsed_ms):
                pipe.hincrby(key, field, amount)
            pipe.expire(key, 86400)
            await pipe.execute()
        except Exception as exc:
            logger.warning("API metering skipped: %s", type(exc).__name__)
