import datetime
from typing import Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from app.core import quota_rules as rules
from app.schemas.tenant import CamelModel


class QuotaOptions(CamelModel):
    tenant_levels: List[str]
    record_statuses: List[str]
    storage_types: List[str]
    storage_providers: List[str]
    measured_providers: List[str]
    storage_units: List[str]
    file_types: List[str]
    modules: List[str]
    sms_providers: List[str]
    sms_categories: List[str]
    sms_connected: bool
    api_gateways: List[str]
    api_services: List[str]
    api_categories: List[str]
    quota_periods: List[str]
    resource_types: List[str]
    alert_conditions: List[str]
    operators: List[str]
    severities: List[str]
    notification_channels: List[str]


class RecipientOption(CamelModel):
    id: str
    full_name: str
    email: str
    tenant_id: str


class ModuleAllocation(CamelModel):
    module_code: str = Field(min_length=1, max_length=20)
    allocation_bytes: int = Field(gt=0)


class TenantScoped(CamelModel):
    tenant_level: str
    state_tenant_id: str = Field(min_length=1, max_length=50)
    ulb_tenant_id: Optional[str] = Field(None, max_length=50)

    @model_validator(mode="after")
    def level(self):
        if self.tenant_level not in rules.TENANT_LEVELS:
            raise ValueError("Tenant level must be State or ULB.")
        if self.tenant_level == "ULB" and not self.ulb_tenant_id:
            raise ValueError("Select the ULB / City.")
        return self


class StorageAllocationPayload(TenantScoped):
    allocation_name: str = Field(min_length=1, max_length=150)
    storage_type: str
    storage_provider: str
    storage_bucket: str = Field(min_length=1, max_length=100)
    allocation_amount: float = Field(gt=0)
    storage_unit: str
    max_file_size_mb: float = Field(gt=0)
    allowed_file_types: List[str] = Field(min_length=1)
    module_allocations: List[ModuleAllocation] = []
    effective_from: datetime.datetime
    effective_until: Optional[datetime.datetime] = None
    allocation_status: str = "Draft"
    remarks: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def choices(self):
        if self.storage_type not in rules.STORAGE_TYPES:
            raise ValueError("Unknown storage type.")
        if self.storage_provider not in rules.STORAGE_PROVIDERS:
            raise ValueError("Unknown storage provider.")
        if self.storage_unit not in rules.STORAGE_UNITS:
            raise ValueError("Unknown storage unit.")
        if self.allocation_status not in rules.RECORD_STATUSES:
            raise ValueError("Unknown allocation status.")
        if not set(self.allowed_file_types) <= set(rules.FILE_TYPES):
            raise ValueError("Unknown file type.")
        if self.effective_until and self.effective_until < self.effective_from:
            raise ValueError("Effective Until cannot be before Effective From.")
        total = rules.to_bytes(self.allocation_amount, self.storage_unit)
        if sum(m.allocation_bytes for m in self.module_allocations) > total:
            raise ValueError("Module allocations cannot exceed the storage allocation.")
        if self.max_file_size_mb * 1024 * 1024 > total:
            raise ValueError("Maximum file size cannot exceed the storage allocation.")
        codes = [m.module_code for m in self.module_allocations]
        if len(codes) != len(set(codes)):
            raise ValueError("Each module can appear once.")
        return self


class StorageAllocationOut(CamelModel):
    id: str
    tenant_id: str
    tenant_level: str
    state_tenant_id: str
    ulb_tenant_id: Optional[str] = None
    allocation_name: str
    storage_type: str
    storage_provider: str
    storage_bucket: str
    allocation_amount: float
    storage_unit: str
    allocation_bytes: int
    max_file_size_mb: float
    allowed_file_types: List[str]
    module_allocations: List[ModuleAllocation] = []
    effective_from: datetime.datetime
    effective_until: Optional[datetime.datetime] = None
    allocation_status: str
    remarks: Optional[str] = None


class LargestFile(CamelModel):
    object_name: str
    size_bytes: int
    module_code: str


class StorageUsageRow(CamelModel):
    allocation_id: str
    allocation_name: str
    tenant_id: str
    tenant_level: str
    storage_type: str
    storage_provider: str
    telemetry_connected: bool
    allocated_bytes: int
    used_bytes: Optional[int] = None
    available_bytes: Optional[int] = None
    utilisation_percentage: Optional[float] = None
    total_files: Optional[int] = None
    largest_files: List[LargestFile] = []
    module_usage: Dict[str, int] = {}
    usage_status: str


class SmsAllocationPayload(CamelModel):
    allocation_name: str = Field(min_length=1, max_length=150)
    state_tenant_id: str = Field(min_length=1, max_length=50)
    ulb_tenant_id: Optional[str] = Field(None, max_length=50)
    sms_provider: str
    dlt_entity_id: Optional[str] = Field(None, max_length=30)
    sender_id: Optional[str] = Field(None, max_length=11)
    dlt_template_id: Optional[str] = Field(None, max_length=30)
    credit_allocation: int = Field(gt=0)
    valid_from: datetime.datetime
    valid_until: datetime.datetime
    sms_categories: List[str] = []
    low_credit_threshold: Optional[int] = Field(None, ge=0)
    notification_recipients: List[str] = []
    allocation_status: str = "Draft"

    @model_validator(mode="after")
    def choices(self):
        if self.sms_provider not in rules.SMS_PROVIDERS:
            raise ValueError("Unknown SMS provider.")
        if self.allocation_status not in rules.RECORD_STATUSES:
            raise ValueError("Unknown allocation status.")
        if not set(self.sms_categories) <= set(rules.SMS_CATEGORIES):
            raise ValueError("Unknown SMS category.")
        if self.valid_until <= self.valid_from:
            raise ValueError("Credit Validity Until must be after Credit Validity From.")
        # Indian regulations need these before an allocation can send anything.
        if self.allocation_status == "Active" and not (self.dlt_entity_id and self.sender_id and self.dlt_template_id):
            raise ValueError("An active allocation needs the DLT Entity ID, Sender ID and DLT Template ID.")
        return self


class SmsAllocationOut(CamelModel):
    id: str
    tenant_id: str
    state_tenant_id: str
    ulb_tenant_id: Optional[str] = None
    allocation_name: str
    sms_provider: str
    dlt_entity_id: Optional[str] = None
    sender_id: Optional[str] = None
    dlt_template_id: Optional[str] = None
    credit_allocation: int
    credits_consumed: int
    remaining_credits: int = 0
    delivered_messages: int = 0
    failed_messages: int = 0
    delivery_percentage: Optional[float] = None
    valid_from: datetime.datetime
    valid_until: datetime.datetime
    sms_categories: List[str] = []
    low_credit_threshold: Optional[int] = None
    notification_recipients: List[str] = []
    allocation_status: str


class DeliveryReport(CamelModel):
    message_id: str = Field(min_length=1, max_length=36)
    status: str

    @field_validator("status")
    @classmethod
    def known(cls, value):
        if value not in ("Delivered", "Failed"):
            raise ValueError("Status must be Delivered or Failed.")
        return value


class ApiPolicyPayload(TenantScoped):
    api_gateway: str
    api_services: List[str] = []
    api_category: Optional[str] = None
    rate_limit_per_minute: int = Field(gt=0)
    rate_limit_per_hour: Optional[int] = Field(None, gt=0)
    rate_limit_per_day: Optional[int] = Field(None, gt=0)
    burst_limit: Optional[int] = Field(None, gt=0)
    concurrent_limit: Optional[int] = Field(None, gt=0)
    quota_period: str
    effective_from: datetime.datetime
    effective_until: Optional[datetime.datetime] = None
    policy_status: str = "Draft"

    @model_validator(mode="after")
    def choices(self):
        if self.api_gateway not in rules.API_GATEWAYS:
            raise ValueError("Unknown API gateway.")
        if self.api_category and self.api_category not in rules.API_CATEGORIES:
            raise ValueError("Unknown API category.")
        if self.quota_period not in rules.QUOTA_PERIODS:
            raise ValueError("Unknown quota period.")
        if self.policy_status not in rules.RECORD_STATUSES:
            raise ValueError("Unknown policy status.")
        if self.quota_period == rules.PERIOD_HOUR and not self.rate_limit_per_hour:
            raise ValueError("A per-hour quota period needs Rate Limit Per Hour.")
        if self.quota_period == rules.PERIOD_DAY and not self.rate_limit_per_day:
            raise ValueError("A per-day quota period needs Rate Limit Per Day.")
        if self.effective_until and self.effective_until < self.effective_from:
            raise ValueError("Effective Until cannot be before Effective From.")
        return self


class ApiPolicyOut(CamelModel):
    id: str
    tenant_id: str
    tenant_level: str
    state_tenant_id: str
    ulb_tenant_id: Optional[str] = None
    api_gateway: str
    api_services: List[str] = []
    api_category: Optional[str] = None
    rate_limit_per_minute: int
    rate_limit_per_hour: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    burst_limit: Optional[int] = None
    concurrent_limit: Optional[int] = None
    quota_period: str
    effective_from: datetime.datetime
    effective_until: Optional[datetime.datetime] = None
    policy_status: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    throttled_requests: int = 0
    average_response_ms: Optional[float] = None
    peak_requests_per_minute: int = 0
    remaining_quota: Optional[int] = None


class ThresholdLevelOut(CamelModel):
    id: str
    level_name: str
    percentage: float


class ThresholdLevelUpdate(CamelModel):
    percentage: float = Field(gt=0, le=100)


class AlertRulePayload(TenantScoped):
    alert_name: str = Field(min_length=1, max_length=150)
    alert_code: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    resource_type: str
    alert_condition: str
    threshold_percentage: Optional[float] = Field(None, ge=0, le=100)
    threshold_value: Optional[float] = Field(None, ge=0)
    comparison_operator: str
    alert_severity: str
    notification_channels: List[str] = Field(min_length=1)
    notification_recipients: List[str] = Field(min_length=1)
    repeat_interval_minutes: Optional[int] = Field(None, gt=0)
    is_active: bool = True
    description: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def choices(self):
        if self.resource_type not in rules.RESOURCE_TYPES:
            raise ValueError("Unknown resource type.")
        if self.alert_condition not in rules.ALERT_CONDITIONS:
            raise ValueError("Unknown alert condition.")
        if self.comparison_operator not in rules.OPERATORS:
            raise ValueError("Unknown comparison operator.")
        if self.alert_severity not in rules.SEVERITIES:
            raise ValueError("Unknown severity.")
        if self.alert_condition == rules.CONDITION_PERCENT and self.threshold_percentage is None:
            raise ValueError("Enter a threshold percentage.")
        if self.alert_condition == rules.CONDITION_VALUE and self.threshold_value is None:
            raise ValueError("Enter a threshold value.")
        return self


class AlertRuleOut(CamelModel):
    id: str
    tenant_id: str
    tenant_level: str
    state_tenant_id: str
    ulb_tenant_id: Optional[str] = None
    alert_name: str
    alert_code: str
    resource_type: str
    alert_condition: str
    threshold_percentage: Optional[float] = None
    threshold_value: Optional[float] = None
    comparison_operator: str
    alert_severity: str
    notification_channels: List[str]
    notification_recipients: List[str]
    repeat_interval_minutes: Optional[int] = None
    is_active: bool
    description: Optional[str] = None
    is_firing: bool
    last_notified_at: Optional[datetime.datetime] = None
    last_value: Optional[float] = None


class AlertEventOut(CamelModel):
    id: str
    tenant_id: str
    severity: str
    message: str
    delivery_summary: Optional[str] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
