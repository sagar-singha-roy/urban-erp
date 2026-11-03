"""ADM-R04 option lists and pure rules for support impersonation."""
import datetime
import re
from typing import Any, Iterable, Optional

REQUEST_TYPES = ["Troubleshooting", "Data Verification", "Technical Support"]
DURATIONS = [5, 10, 15, 30]
MODE_READ_ONLY, MODE_RESTRICTED = "Read Only", "Restricted Actions"
ACCESS_MODES = [MODE_READ_ONLY, MODE_RESTRICTED]
TENANT_LEVELS = ["Platform", "State", "ULB"]

REQ_PENDING, REQ_SECOND, REQ_APPROVED, REQ_REJECTED, REQ_USED, REQ_EXPIRED, REQ_CANCELLED = (
    "Pending", "Awaiting Second Approval", "Approved", "Rejected", "Used", "Expired", "Cancelled",
)
REQUEST_STATUSES = [REQ_PENDING, REQ_SECOND, REQ_APPROVED, REQ_REJECTED, REQ_USED, REQ_EXPIRED, REQ_CANCELLED]
APPROVAL_STATUSES = ["Pending", "Approved", "Rejected"]
SESSION_ACTIVE, SESSION_TERMINATED, SESSION_EXPIRED = "Active", "Terminated", "Expired"
SESSION_STATUSES = [SESSION_ACTIVE, SESSION_TERMINATED, SESSION_EXPIRED]

# An approval must be used within this long, so a forgotten approval cannot be used weeks later.
MAX_APPROVAL_VALIDITY = datetime.timedelta(hours=24)
DEFAULT_APPROVAL_VALIDITY = datetime.timedelta(hours=2)

TOKEN_TYPE = "impersonation"
READ_METHODS = ("GET", "HEAD", "OPTIONS")
READ_ACTIONS = {"VIEW"}

# Field names are compared without case or separators. A name containing any of these is masked.
SENSITIVE_FIELD_PARTS = ("email", "mobile", "phone", "aadhaar", "pannumber", "address", "dateofbirth", "dob", "bankaccount", "accountnumber", "ifsc")
# Content types that are file downloads. Images stay, because pages need logos and map tiles.
DOWNLOAD_TYPES = ("text/csv", "application/pdf", "application/zip", "application/octet-stream", "application/vnd.", "application/x-")


def request_number(sequence: int) -> str:
    return f"IMP-{sequence:06d}"


def session_number(sequence: int) -> str:
    return f"IMS-{sequence:06d}"


def policy_code(sequence: int) -> str:
    return f"IMP-POL-{sequence:03d}"


# Token roles mapped to codes in the roles table. Policies and the permission matrix both use these.
TOKEN_ROLE_CODES = {"super_admin": "PLATFORM_SUPER_ADMIN", "state_director": "STATE_DIRECTOR", "revenue_officer": "TAX_INSPECTOR",
                    "town_planner": "TOWN_PLANNER", "citizen": "CITIZEN_READONLY"}


def role_code(role: str) -> str:
    return TOKEN_ROLE_CODES.get(role, role.upper())


def action_permitted(mode: str, write_actions: Iterable[str], download_disabled: bool, component_code: str, action: str) -> bool:
    """Read Only allows viewing. Restricted Actions also allows the component actions the policy lists."""
    action = action.upper()
    if action in READ_ACTIONS:
        return True
    if action == "EXPORT":
        return not download_disabled
    return mode == MODE_RESTRICTED and f"{component_code}:{action}" in set(write_actions)


def _normal(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def is_sensitive(key: str) -> bool:
    normal = _normal(key)
    return any(part in normal for part in SENSITIVE_FIELD_PARTS)


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


def mask_payload(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: mask_value(v) if is_sensitive(k) and not isinstance(v, (dict, list)) else mask_payload(v) for k, v in data.items()}
    if isinstance(data, list):
        return [mask_payload(item) for item in data]
    return data


def is_download(content_type: Optional[str], disposition: Optional[str]) -> bool:
    if disposition and "attachment" in disposition.lower():
        return True
    kind = (content_type or "").lower()
    return any(kind.startswith(prefix) for prefix in DOWNLOAD_TYPES)
