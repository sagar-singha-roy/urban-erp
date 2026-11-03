"""Per-request tenant scope that PostgreSQL row-level security policies read."""
from contextvars import ContextVar
from typing import Dict, Iterable

SET_RLS_CONTEXT_SQL = "SELECT set_config('app.tenant_ids', :tenant_ids, true), set_config('app.rls_bypass', :bypass, true)"

# Default is no access: a query outside an authenticated request sees no tenant rows.
_tenant_ids: ContextVar[str] = ContextVar("rls_tenant_ids", default="")
_bypass: ContextVar[bool] = ContextVar("rls_bypass", default=False)


def set_rls_context(tenant_ids: Iterable[str], bypass: bool = False) -> None:
    _tenant_ids.set(",".join(sorted({t.strip().upper() for t in tenant_ids if t and t.strip()})))
    _bypass.set(bypass)


def rls_params() -> Dict[str, str]:
    return {"tenant_ids": _tenant_ids.get(), "bypass": "on" if _bypass.get() else "off"}
