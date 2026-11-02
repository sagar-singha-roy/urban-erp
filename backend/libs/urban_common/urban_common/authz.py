"""Module services hold no identity data: core_service decides every request."""
import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from fastapi import HTTPException, Request, status

from urban_common.settings import settings
from urban_common.tenant_context import set_rls_context

logger = logging.getLogger(__name__)
CSRF_HEADER = "x-requested-with"
FORWARDED_HEADERS = ("authorization", "cookie", "x-tenant-id", "x-sub-tenant-id")
_client = httpx.AsyncClient(timeout=5.0)


@dataclass(frozen=True)
class AccessContext:
    tenant_id: str
    sub_tenant_id: Optional[str]
    user_id: Optional[str]


def require_access(component_code: str, action: str):
    """Enforces a component action such as PTX-P10:APPROVE and scopes the database to the resolved tenant."""

    async def checker(request: Request) -> AccessContext:
        # Browsers attach cookies by themselves, so state changes must also carry a header other sites cannot set.
        if (
            "authorization" not in request.headers
            and request.method not in ("GET", "HEAD", "OPTIONS")
            and CSRF_HEADER not in request.headers
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF header")
        headers = {name: request.headers[name] for name in FORWARDED_HEADERS if name in request.headers}
        headers[CSRF_HEADER] = "urban-common"
        try:
            response = await _client.post(
                f"{settings.CORE_SERVICE_URL}{settings.API_V1_STR}/auth/authorize",
                params={"component": component_code, "action": action},
                headers=headers,
            )
        except httpx.HTTPError as exc:
            # Fails closed: without an answer from core_service nobody gets in.
            logger.error("Authorization service unavailable: %s", exc)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authorization is unavailable")
        if response.status_code in (401, 403):
            detail = response.json().get("detail", "Not authorized")
            raise HTTPException(status_code=response.status_code, detail=detail)
        if response.status_code != 200:
            logger.error("Authorization service answered %s", response.status_code)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authorization is unavailable")
        body = response.json()
        set_rls_context([body["tenantId"]])
        return AccessContext(tenant_id=body["tenantId"], sub_tenant_id=body.get("subTenantId"), user_id=body.get("userId"))

    return checker
