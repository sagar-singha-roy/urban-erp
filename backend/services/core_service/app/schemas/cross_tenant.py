"""ADM-R02 cross-tenant access request and response models."""
import datetime
from typing import List, Optional

from pydantic import Field, field_validator, model_validator

from app.core import cross_tenant_rules as rules
from app.schemas.tenant import CamelModel


def _unique(values: List[str]) -> List[str]:
    cleaned = [v.strip() for v in values if v and v.strip()]
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("Each value can be chosen once.")
    return cleaned


def _naive(value: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    return value.astimezone(datetime.timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value


def _choice(value: str, allowed: List[str], label: str) -> str:
    if value not in allowed:
        raise ValueError(f"{label} must be one of: {', '.join(allowed)}.")
    return value


def _choices(values: List[str], allowed: List[str], label: str) -> List[str]:
    for value in values:
        _choice(value, allowed, label)
    return _unique(values)


class ModuleOption(CamelModel):
    code: str
    name: str


class CrossTenantOptions(CamelModel):
    user_types: List[str]
    access_levels: List[str]
    access_statuses: List[str]
    scope_levels: List[str]
    scope_modes: List[str]
    actions: List[str]
    data_scopes: List[str]
    access_decisions: List[str]
    review_statuses: List[str]
    review_decisions: List[str]
    modules: List[ModuleOption]


class UserOption(CamelModel):
    id: str
    full_name: str
    email: str
    user_type: Optional[str] = None
    home_tenant_id: Optional[str] = None


class ComponentOption(CamelModel):
    code: str
    name: str
    module_code: str


class AreaOption(CamelModel):
    id: str
    name: str
    tenant_id: str
    zone_id: Optional[str] = None


class DepartmentPayload(CamelModel):
    tenant_id: str = Field(min_length=1, max_length=50)
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=150)


class DepartmentOut(CamelModel):
    id: str
    tenant_id: str
    code: str
    name: str
    is_active: bool


class GrantPayload(CamelModel):
    user_profile_id: str = Field(min_length=1, max_length=36)
    user_type: str
    home_tenant_id: str = Field(min_length=1, max_length=50)
    target_tenant_ids: List[str] = Field(min_length=1, max_length=50)
    access_level: str
    effective_from: datetime.datetime
    effective_until: Optional[datetime.datetime] = None
    business_justification: str = Field(min_length=10, max_length=2000)
    approval_authority_id: str = Field(min_length=1, max_length=36)
    approval_reference: Optional[str] = Field(None, max_length=100)

    @field_validator("target_tenant_ids")
    @classmethod
    def targets(cls, value: List[str]) -> List[str]:
        return _unique(value)

    @model_validator(mode="after")
    def check(self):
        _choice(self.user_type, rules.USER_TYPES, "User Type")
        _choice(self.access_level, rules.ACCESS_LEVELS, "Access Level")
        self.effective_from, self.effective_until = _naive(self.effective_from), _naive(self.effective_until)
        if self.effective_until and self.effective_until <= self.effective_from:
            raise ValueError("Effective Until must be after Effective From.")
        if self.home_tenant_id.strip().upper() in {t.upper() for t in self.target_tenant_ids}:
            raise ValueError("The home tenant cannot also be a target tenant.")
        self.business_justification = self.business_justification.strip()
        return self


class GrantDecision(CamelModel):
    reason: str = Field(min_length=3, max_length=2000)


class GrantOut(CamelModel):
    id: str
    record_number: str
    user_profile_id: str
    user_email: str
    user_name: str
    user_type: str
    home_tenant_id: str
    target_tenant_ids: List[str]
    access_level: str
    status: str
    effective_from: datetime.datetime
    effective_until: Optional[datetime.datetime] = None
    business_justification: str
    approval_authority_id: str
    approval_authority_email: str
    requested_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime.datetime] = None
    decision_note: Optional[str] = None
    revoked_by: Optional[str] = None
    revoked_at: Optional[datetime.datetime] = None
    revoke_reason: Optional[str] = None
    approval_reference: Optional[str] = None
    has_scope: bool = False
    created_at: Optional[datetime.datetime] = None


class ScopePayload(CamelModel):
    grant_id: str = Field(min_length=1, max_length=36)
    access_scope: str
    state_tenant_id: str = Field(min_length=1, max_length=50)
    ulb_tenant_ids: List[str] = Field(default_factory=list, max_length=200)
    department_ids: List[str] = Field(default_factory=list, max_length=200)
    zone_ids: List[str] = Field(default_factory=list, max_length=500)
    ward_ids: List[str] = Field(default_factory=list, max_length=1000)
    scope_mode: str
    include_child_tenants: bool = True
    restricted_components: List[str] = Field(default_factory=list, max_length=500)
    effective_date: datetime.datetime
    expiry_date: Optional[datetime.datetime] = None

    @field_validator("ulb_tenant_ids", "department_ids", "zone_ids", "ward_ids", "restricted_components")
    @classmethod
    def unique(cls, value: List[str]) -> List[str]:
        return _unique(value)

    @model_validator(mode="after")
    def check(self):
        _choice(self.access_scope, rules.SCOPE_LEVELS, "Access Scope")
        _choice(self.scope_mode, rules.SCOPE_MODES, "Scope Mode")
        self.effective_date, self.expiry_date = _naive(self.effective_date), _naive(self.expiry_date)
        if self.expiry_date and self.expiry_date <= self.effective_date:
            raise ValueError("Expiry Date must be after Effective Date.")
        needed = {"ULB": self.ulb_tenant_ids, "Department": self.department_ids, "Zone": self.zone_ids, "Ward": self.ward_ids}
        if self.access_scope in needed and not needed[self.access_scope]:
            raise ValueError(f"Select at least one {self.access_scope} for this access scope.")
        if not self.include_child_tenants and not self.ulb_tenant_ids:
            raise ValueError("Without child tenants, select the ULBs this access covers.")
        return self


class ScopeOut(CamelModel):
    id: str
    grant_id: str
    record_number: str
    user_email: str
    user_name: str
    access_scope: str
    state_tenant_id: str
    ulb_tenant_ids: List[str]
    department_ids: List[str]
    zone_ids: List[str]
    ward_ids: List[str]
    scope_mode: str
    include_child_tenants: bool
    restricted_components: List[str]
    effective_date: datetime.datetime
    expiry_date: Optional[datetime.datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime.datetime] = None


class RulePayload(CamelModel):
    grant_id: str = Field(min_length=1, max_length=36)
    target_tenant_id: str = Field(min_length=1, max_length=50)
    module_codes: List[str] = Field(min_length=1, max_length=30)
    component_codes: List[str] = Field(default_factory=list, max_length=500)
    action_permissions: List[str] = Field(min_length=1)
    data_access_scope: str
    access_decision: str
    restriction_reason: Optional[str] = Field(None, max_length=2000)

    @field_validator("module_codes", "component_codes")
    @classmethod
    def unique(cls, value: List[str]) -> List[str]:
        return _unique(value)

    @model_validator(mode="after")
    def check(self):
        self.action_permissions = _choices(self.action_permissions, rules.ACTIONS, "Action Permissions")
        _choice(self.data_access_scope, rules.DATA_SCOPES, "Data Access Scope")
        _choice(self.access_decision, rules.ACCESS_DECISIONS, "Access Decision")
        if self.access_decision == rules.DECISION_DENY and not (self.restriction_reason or "").strip():
            raise ValueError("Give the reason for this restriction.")
        return self


class RuleReview(CamelModel):
    review_status: str

    @field_validator("review_status")
    @classmethod
    def status(cls, value: str) -> str:
        return _choice(value, [rules.REVIEW_APPROVED, rules.REVIEW_REJECTED], "Review Status")


class RuleOut(CamelModel):
    id: str
    grant_id: str
    record_number: str
    user_email: str
    target_tenant_id: str
    module_codes: List[str]
    component_codes: List[str]
    action_permissions: List[str]
    data_access_scope: str
    access_decision: str
    restriction_reason: Optional[str] = None
    review_status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime.datetime] = None
    created_by: Optional[str] = None


class CampaignPayload(CamelModel):
    campaign_name: str = Field(min_length=3, max_length=150)
    period_start: datetime.datetime
    period_end: datetime.datetime
    tenant_scope: List[str] = Field(default_factory=list, max_length=200)
    user_types: List[str] = Field(min_length=1)
    access_statuses: List[str] = Field(min_length=1)
    review_owner_id: str = Field(min_length=1, max_length=36)
    review_deadline: datetime.date

    @model_validator(mode="after")
    def check(self):
        self.tenant_scope = _unique(self.tenant_scope)
        self.user_types = _choices(self.user_types, rules.USER_TYPES, "User Type")
        self.access_statuses = _choices(self.access_statuses, [rules.STATUS_ACTIVE, rules.STATUS_EXPIRED, rules.STATUS_PENDING], "Access Status")
        self.period_start, self.period_end = _naive(self.period_start), _naive(self.period_end)
        if self.period_end <= self.period_start:
            raise ValueError("The review period must end after it starts.")
        if self.review_deadline < self.period_start.date():
            raise ValueError("The review deadline cannot be before the review period starts.")
        return self


class CampaignOut(CamelModel):
    id: str
    campaign_name: str
    period_start: datetime.datetime
    period_end: datetime.datetime
    tenant_scope: List[str]
    user_types: List[str]
    access_statuses: List[str]
    review_owner_id: str
    review_owner_email: str
    review_deadline: datetime.datetime
    status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    total_items: int = 0
    decided_items: int = 0


class ReviewDecisionPayload(CamelModel):
    review_decision: str
    reviewer_comments: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def check(self):
        _choice(self.review_decision, rules.REVIEW_DECISIONS, "Review Decision")
        if self.review_decision != rules.RETAIN and not (self.reviewer_comments or "").strip():
            raise ValueError("Add a comment when modifying or revoking access.")
        return self


class ReviewItemOut(CamelModel):
    id: str
    grant_id: str
    record_number: str
    user_email: str
    user_name: str
    user_type: str
    home_tenant_id: str
    target_tenant_ids: List[str]
    access_level: str
    grant_status: str
    status: str
    review_decision: Optional[str] = None
    reviewer_comments: Optional[str] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime.datetime] = None


class HistoryOut(CamelModel):
    id: str
    grant_id: Optional[str] = None
    user_email: str
    home_tenant_id: Optional[str] = None
    target_tenant_ids: List[str]
    previous_access_level: Optional[str] = None
    new_access_level: Optional[str] = None
    previous_scope: Optional[str] = None
    new_scope: Optional[str] = None
    action: str
    changed_by: str
    ip_address: Optional[str] = None
    reason: Optional[str] = None
    approval_reference: Optional[str] = None
    created_at: datetime.datetime
