"""Support sessions in module services. core_service decides the rules and sends them with each authorization answer."""
import json
import re
from typing import Any, Iterable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

# Content types that are file downloads. Images stay, because pages need logos and map tiles.
DOWNLOAD_TYPES = ("text/csv", "application/pdf", "application/zip", "application/octet-stream", "application/vnd.", "application/x-")


def is_sensitive(key: str, parts: Iterable[str]) -> bool:
    normal = re.sub(r"[^a-z0-9]", "", key.lower())
    return any(part in normal for part in parts)


def mask_value(value: Any) -> Any:
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        return "***"
    if "@" in value:
        local, _, domain = value.partition("@")
        return f"{local[:1]}***@{domain}"
    if len(value) <= 4:
        return "****"
    if value.replace(" ", "").replace("+", "").replace("-", "").isdigit():
        return "*" * (len(value) - 4) + value[-4:]
    return value[:2] + "*" * (len(value) - 2)


def mask_payload(data: Any, parts: Iterable[str]) -> Any:
    parts = tuple(parts)
    if isinstance(data, dict):
        return {k: mask_value(v) if is_sensitive(k, parts) and not isinstance(v, (dict, list)) else mask_payload(v, parts) for k, v in data.items()}
    if isinstance(data, list):
        return [mask_payload(item, parts) for item in data]
    return data


def is_download(content_type: str, disposition: str) -> bool:
    if disposition and "attachment" in disposition.lower():
        return True
    return any((content_type or "").lower().startswith(prefix) for prefix in DOWNLOAD_TYPES)


class SupportSessionGuard(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        rules = getattr(request.state, "impersonation", None)
        if not rules:
            return response
        if rules.get("downloadDisabled") and is_download(response.headers.get("content-type", ""), response.headers.get("content-disposition", "")):
            return JSONResponse({"detail": "Downloads are turned off during support sessions."}, status_code=403)
        if rules.get("maskSensitive") and (response.headers.get("content-type") or "").startswith("application/json"):
            body = b"".join([chunk async for chunk in response.body_iterator])
            try:
                body = json.dumps(mask_payload(json.loads(body), rules.get("sensitiveFieldParts") or [])).encode("utf-8")
            except ValueError:
                pass
            headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
            return Response(content=body, status_code=response.status_code, headers=headers, media_type="application/json")
        return response
