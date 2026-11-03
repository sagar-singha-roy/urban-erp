"""ADM-R04 support impersonation request and response models."""
import datetime
import re
from typing import List, Optional

from pydantic import Field, model_validator

from app.core import impersonation_rules as rules
from app.schemas.tenant import CamelModel

WRITE_ACTION_PATTERN = re.compile(r"^[A-Z0-9]+-[A-Z0-9]+:(CREATE|UPDATE|DELETE|APPROVE)$")
WRITE_ACTIONS = ["CREATE", "UPDATE", "DELETE", "APPROVE"]


def _naive(value: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    return value.astimezone(datetime.timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value


def _choices(values: List[str], allowed: List[str], label: str) -> List[str]:
    for value in values:
        if value not in allowed:
            raise ValueError(f"{label} must be one of: {', '.join(allowed)}.")
    if len(set(values)) != len(values):
        raise ValueError(f"Each {label} can be chosen once.")
    return values


class RoleOption(CamelModel):
    code: str
    name: str


class ImpersonationOptions(CamelModel):
    request_types: List[str]
    durations: List[int]
    access_modes: List[str]
    tenant_levels: List[str]
    request_statuses: List[str]
    session_statuses: List[str]
    roles: List[RoleOption]
    write_action_types: List[str]
    sensitive_field_parts: List[str]
    max_approval_hours: int


class HubProfile(CamelModel):
    user_id: str
    email: str
    full_name: str
    role_code: str
    is_super_admin: bool
    can_request: bool


class TargetOption(CamelModel):
    id: str
    full_name: str
    email: str
    role: str
    tenant_ids: List[str]


class ApproverOption(CamelModel):
    id: str
    full_name: str
    email: str


class PolicyPayload(CamelModel):
    policy_name: str = Field(min_length=3, max_length=150)
    allowed_support_roles: List[str] = Field(min_length=1)
    allowed_tenant_levels: List[str] = Field(min_length=1)
    max_session_minutes: int = Field(ge=5, le=60)
    approval_required: bool = True
    dual_approval: bool = False
    read_only_default: bool = True
    mask_sensitive_data: bool = True
    download_disabled: bool = True
    write_actions_allowed: List[str] = Field(default_factory=list, max_length=200)
    session_recording: bool = True
    is_active: bool = True

    @model_validator(mode="after")
    def check(self):
        self.policy_name = self.policy_name.strip()
        self.allowed_tenant_levels = _choices(self.allowed_tenant_levels, rules.TENANT_LEVELS, "tenant level")
        if len(set(self.allowed_support_roles)) != len(self.allowed_support_roles):
            raise ValueError("Each support role can be chosen once.")
        for action in self.write_actions_allowed:
            if not WRITE_ACTION_PATTERN.match(action):
                raise ValueError("Write actions look like PTX-P10:UPDATE.")
        if self.dual_approval and not self.approval_required:
            raise ValueError("Dual approval needs approval to be required.")
        return self


class PolicyOut(PolicyPayload):
    id: str
    policy_code: str
    updated_by: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None


class RequestPayload(CamelModel):
    target_user_id: str = Field(min_length=1, max_length=36)
    target_tenant_id: str = Field(min_length=1, max_length=50)
    request_type: str
    business_justification: str = Field(min_length=20, max_length=2000)
    ticket_reference: str = Field(min_length=2, max_length=100)
    requested_minutes: int
    access_mode: str

    @model_validator(mode="after")
    def check(self):
        if self.request_type not in rules.REQUEST_TYPES:
            raise ValueError("Choose a request type.")
        if self.requested_minutes not in rules.DURATIONS:
            raise ValueError(f"The duration must be one of {', '.join(map(str, rules.DURATIONS))} minutes.")
        if self.access_mode not in rules.ACCESS_MODES:
            raise ValueError("Choose an access mode.")
        self.business_justification, self.ticket_reference = self.business_justification.strip(), self.ticket_reference.strip()
        return self


class ApprovalOut(CamelModel):
    stage: int
    approver_email: str
    decision: str
    comments: Optional[str] = None
    decided_at: Optional[datetime.datetime] = None


class RequestOut(CamelModel):
    id: str
    request_number: str
    policy_code: str
    support_user_id: str
    support_email: str
    support_name: str
    target_user_id: str
    target_email: str
    target_name: str
    target_tenant_id: str
    target_tenant_level: str
    request_type: str
    business_justification: str
    ticket_reference: str
    requested_minutes: int
    access_mode: str
    status: str
    dual_approval_required: bool
    second_approver_email: Optional[str] = None
    approval_valid_until: Optional[datetime.datetime] = None
    requested_at: Optional[datetime.datetime] = None
    decided_at: Optional[datetime.datetime] = None
    approvals: List[ApprovalOut] = []


class DecisionPayload(CamelModel):
    decision: str
    comments: Optional[str] = Field(None, max_length=2000)
    approval_valid_until: Optional[datetime.datetime] = None
    dual_approval_required: bool = False
    second_approver_id: Optional[str] = Field(None, max_length=36)

    @model_validator(mode="after")
    def check(self):
        if self.decision not in ("Approved", "Rejected"):
            raise ValueError("The decision must be Approved or Rejected.")
        if self.decision == "Rejected" and not (self.comments or "").strip():
            raise ValueError("Say why the request is rejected.")
        self.approval_valid_until = _naive(self.approval_valid_until)
        return self


class ReasonPayload(CamelModel):
    reason: str = Field(min_length=3, max_length=2000)


class SessionOut(CamelModel):
    id: str
    session_number: str
    request_id: str
    request_number: str
    support_email: str
    target_email: str
    target_name: str
    tenant_id: str
    access_mode: str
    status: str
    started_at: datetime.datetime
    expires_at: datetime.datetime
    ended_at: Optional[datetime.datetime] = None
    termination_reason: Optional[str] = None
    terminated_by: Optional[str] = None


class CurrentSession(CamelModel):
    active: bool
    session_number: Optional[str] = None
    target_name: Optional[str] = None
    target_email: Optional[str] = None
    tenant_id: Optional[str] = None
    access_mode: Optional[str] = None
    expires_at: Optional[datetime.datetime] = None
    agent_email: Optional[str] = None


class AuditOut(CamelModel):
    session_id: str
    session_number: str
    request_number: str
    support_email: str
    target_email: str
    tenant_id: str
    status: str
    login_time: datetime.datetime
    logout_time: Optional[datetime.datetime] = None
    actions_performed: int
    ip_address: Optional[str] = None
    device: Optional[str] = None
    approval_reference: str
    termination_reason: Optional[str] = None
    audit_event_id: Optional[str] = None


class ActionOut(CamelModel):
    method: str
    path: str
    permission: Optional[str] = None
    status_code: int
    created_at: datetime.datetime
