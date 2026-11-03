"""ADM-R02: active cross-tenant grants, read from the database on every request so revocation takes effect at once."""
import datetime
from typing import Dict, Iterable, List, Optional, Set

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cross_tenant_rules as rules
from app.db.models import CrossTenantAccessGrant, CrossTenantPermissionRule, StateTenant

# Request fields that name a tenant, in addition to the X-Tenant-ID and X-Sub-Tenant-ID headers.
TENANT_PARAMS = ("tenant_id", "state_tenant_id", "ulb_tenant_id")


def grant_tenants(grant: CrossTenantAccessGrant, state_codes: Dict[str, str], now: datetime.datetime) -> Set[str]:
    """Tenants a grant reaches. A state stays whole unless its scope leaves out child tenants."""
    scope = grant.scope
    if scope is not None and not rules.is_in_window(scope.effective_date, scope.expiry_date, now):
        return set()
    reached: Set[str] = set()
    for target in grant.targets:
        tenant = target.target_tenant_id.upper()
        if tenant in state_codes and scope is not None and not scope.include_child_tenants:
            reached.update(ulb.upper() for ulb in scope.ulb_tenant_ids)
            continue
        reached.add(tenant)
        if tenant in state_codes:
            # Rows and the policy name states by code as well as by identifier.
            reached.add(state_codes[tenant])
    return reached


def grant_entry(grant: CrossTenantAccessGrant, deny_rules: List[CrossTenantPermissionRule]) -> dict:
    scope = grant.scope
    return {
        "grant_id": grant.id,
        "access_level": grant.access_level,
        "restricted": list(scope.restricted_components) if scope else [],
        "departments": list(scope.department_ids) if scope else [],
        "zones": list(scope.zone_ids) if scope else [],
        "wards": list(scope.ward_ids) if scope else [],
        "deny": [{"tenant": r.target_tenant_id.upper(), "modules": r.module_codes, "components": r.component_codes, "actions": r.action_permissions} for r in deny_rules],
    }


async def load_active_grants(db: AsyncSession, email: Optional[str], now: Optional[datetime.datetime] = None) -> Dict[str, List[dict]]:
    """Tenant identifier mapped to the grants that reach it. Empty for nearly every user, at the cost of one indexed query."""
    if not email:
        return {}
    now = now or datetime.datetime.utcnow()
    grants = (await db.scalars(select(CrossTenantAccessGrant).where(
        CrossTenantAccessGrant.user_email == email.lower(),
        CrossTenantAccessGrant.status == rules.STATUS_ACTIVE,
        CrossTenantAccessGrant.effective_from <= now,
        or_(CrossTenantAccessGrant.effective_until.is_(None), CrossTenantAccessGrant.effective_until >= now),
    ))).all()
    if not grants:
        return {}
    targets = {t.target_tenant_id for g in grants for t in g.targets}
    states = (await db.execute(select(StateTenant.tenant_id, StateTenant.state_code).where(StateTenant.tenant_id.in_(targets)))).all()
    state_codes = {tenant_id.upper(): code.upper() for tenant_id, code in states}
    deny_rules = (await db.scalars(select(CrossTenantPermissionRule).where(
        CrossTenantPermissionRule.grant_id.in_([g.id for g in grants]),
        CrossTenantPermissionRule.review_status == rules.REVIEW_APPROVED,
        CrossTenantPermissionRule.access_decision == rules.DECISION_DENY,
    ))).all()
    reached: Dict[str, List[dict]] = {}
    for grant in grants:
        entry = grant_entry(grant, [r for r in deny_rules if r.grant_id == grant.id])
        for tenant in grant_tenants(grant, state_codes, now):
            reached.setdefault(tenant, []).append(entry)
    return reached


def split_scope(raw: Optional[str]) -> Set[str]:
    return {part.strip().upper() for part in str(raw or "").split(",") if part.strip()}


def with_grants(payload: dict, grants: Dict[str, List[dict]]) -> dict:
    """Add granted tenants to the scope, keeping the home scope so checks can tell the two apart."""
    if not grants:
        return payload
    home = split_scope(payload.get("tenant_scope") or payload.get("tenant_id"))
    return {**payload, "home_tenant_scope": ",".join(sorted(home)), "tenant_scope": ",".join(sorted(home | set(grants))), "cross_tenant": grants}


def entries_for(user: dict, identifiers: Iterable[str]) -> List[dict]:
    """Grants that reach a tenant, or none when the user's home scope already covers it."""
    grants = user.get("cross_tenant") or {}
    identifiers = set(identifiers)
    if not grants or split_scope(user.get("home_tenant_scope")) & identifiers:
        return []
    return [entry for key in identifiers if key in grants for entry in grants[key]]


def method_permitted(entries: List[dict], method: str) -> bool:
    return not entries or any(rules.method_allowed(e["access_level"], method) for e in entries)


def action_permitted(entries: List[dict], identifiers: Iterable[str], component_code: str, action: str) -> bool:
    """Some grant must allow the action at its level, with no restriction or approved Deny rule against it."""
    if not entries:
        return True
    identifiers = set(identifiers)
    for entry in entries:
        if not rules.action_allowed(entry["access_level"], action) or rules.is_restricted(entry["restricted"], component_code):
            continue
        denied = any(rule["tenant"] in identifiers and rules.rule_covers(rule["modules"], rule["components"], rule["actions"], component_code, action) for rule in entry["deny"])
        if not denied:
            return True
    return False


def request_tenants(request) -> List[str]:
    values = [request.headers.get("X-Sub-Tenant-ID"), request.headers.get("X-Tenant-ID")]
    for name in TENANT_PARAMS:
        values += [request.path_params.get(name), request.query_params.get(name)]
    seen: List[str] = []
    for value in values:
        cleaned = (value or "").strip().upper()
        if cleaned and cleaned != "ALL" and cleaned not in seen:
            seen.append(cleaned)
    return seen
