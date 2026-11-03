"""ADM-R02 option lists and pure rules for cross-tenant access."""
import datetime
from typing import Iterable, Optional

USER_TYPES = ["Internal Admin", "State Admin", "Support", "Auditor"]
# The profile's own user type suggests the grant's, so the form starts filled in.
PROFILE_USER_TYPES = {"Internal Staff": "Internal Admin", "Government Officer": "State Admin", "Support Staff": "Support", "Auditor": "Auditor"}

LEVEL_READ_ONLY, LEVEL_READ_WRITE, LEVEL_ADMIN = "Read Only", "Read/Write", "Admin"
ACCESS_LEVELS = [LEVEL_READ_ONLY, LEVEL_READ_WRITE, LEVEL_ADMIN]

STATUS_ACTIVE, STATUS_PENDING, STATUS_REVOKED, STATUS_EXPIRED, STATUS_REJECTED = "Active", "Pending", "Revoked", "Expired", "Rejected"
ACCESS_STATUSES = [STATUS_ACTIVE, STATUS_PENDING, STATUS_REVOKED, STATUS_EXPIRED]
CLOSED_STATUSES = (STATUS_REVOKED, STATUS_EXPIRED, STATUS_REJECTED)

SCOPE_LEVELS = ["State", "ULB", "Department", "Zone", "Ward"]
SCOPE_MODES = ["Explicit", "Inherited"]

ACTIONS = ["View", "Create", "Update", "Delete", "Approve", "Export"]
DATA_SCOPES = ["Own", "Department", "ULB", "State", "Global"]
DECISION_ALLOW, DECISION_DENY = "Allow", "Deny"
ACCESS_DECISIONS = [DECISION_ALLOW, DECISION_DENY]
REVIEW_PENDING, REVIEW_APPROVED, REVIEW_REJECTED = "Pending", "Approved", "Rejected"
REVIEW_STATUSES = [REVIEW_PENDING, REVIEW_APPROVED, REVIEW_REJECTED]

RETAIN, MODIFY, REVOKE = "Retain", "Modify", "Revoke"
REVIEW_DECISIONS = [RETAIN, MODIFY, REVOKE]
CAMPAIGN_OPEN, CAMPAIGN_COMPLETED = "Open", "Completed"
ITEM_PENDING, ITEM_DECIDED, ITEM_AWAITING_CHANGE = "Pending", "Decided", "Awaiting Change"

# Matrix actions each access level may use in a tenant reached through a grant.
LEVEL_ACTIONS = {
    LEVEL_READ_ONLY: {"VIEW", "EXPORT"},
    LEVEL_READ_WRITE: {"VIEW", "EXPORT", "CREATE", "UPDATE", "DELETE"},
    LEVEL_ADMIN: {"VIEW", "EXPORT", "CREATE", "UPDATE", "DELETE", "APPROVE", "MANAGE"},
}
READ_METHODS = ("GET", "HEAD", "OPTIONS")


def record_number(sequence: int) -> str:
    return f"XTA-{sequence:06d}"


def is_in_window(start: Optional[datetime.datetime], end: Optional[datetime.datetime], now: datetime.datetime) -> bool:
    return (start is None or start <= now) and (end is None or end >= now)


def method_allowed(access_level: str, method: str) -> bool:
    return access_level != LEVEL_READ_ONLY or method.upper() in READ_METHODS


def action_allowed(access_level: str, action: str) -> bool:
    return action.upper() in LEVEL_ACTIONS.get(access_level, set())


def rule_covers(rule_modules: Iterable[str], rule_components: Iterable[str], rule_actions: Iterable[str], component_code: str, action: str) -> bool:
    """A rule names components, or whole modules when it names none."""
    components = set(rule_components)
    if components:
        covered = component_code in components
    else:
        covered = component_code.split("-", 1)[0] in set(rule_modules)
    return covered and action.upper() in {a.upper() for a in rule_actions}


def is_restricted(restrictions: Iterable[str], component_code: str) -> bool:
    """Restrictions hold component codes, or module codes that cover every component in them."""
    module = component_code.split("-", 1)[0]
    return any(item == component_code or item == module for item in restrictions)


def describe_scope(scope) -> str:
    if scope is None:
        return "No scope"
    parts = [f"{scope.access_scope} ({scope.scope_mode})"]
    for label, values in (("ULBs", scope.ulb_tenant_ids), ("Departments", scope.department_ids), ("Zones", scope.zone_ids), ("Wards", scope.ward_ids)):
        if values:
            parts.append(f"{label}: {len(values)}")
    if not scope.include_child_tenants:
        parts.append("no child tenants")
    if scope.restricted_components:
        parts.append(f"restricted: {', '.join(scope.restricted_components)}")
    return "; ".join(parts)
