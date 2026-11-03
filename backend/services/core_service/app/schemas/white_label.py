import datetime
from typing import Dict, Generic, List, Optional, TypeVar

from pydantic import Field, field_validator, model_validator

from app.core import white_label_rules as rules
from app.schemas.tenant import CamelModel

DataT = TypeVar("DataT")


class PagedResponse(CamelModel, Generic[DataT]):
    success: bool = True
    code: int = 2000
    data: List[DataT]
    total: int


class WhiteLabelOptions(CamelModel):
    tenant_levels: List[str]
    record_statuses: List[str]
    font_families: List[str]
    logo_types: List[str]
    domain_types: List[str]
    dns_providers: List[str]
    dns_record_types: List[str]
    verification_methods: List[str]
    domain_statuses: List[str]
    certificate_providers: List[str]
    certificate_types: List[str]
    target_applications: List[str]
    target_services: List[str]
    routing_strategies: List[str]


class TenantOption(CamelModel):
    tenant_id: str
    name: str
    tenant_level: str
    state_tenant_id: str


class BrandingProfilePayload(CamelModel):
    tenant_level: str
    state_tenant_id: str = Field(min_length=1, max_length=50)
    ulb_tenant_id: Optional[str] = Field(None, max_length=50)
    profile_name: str = Field(min_length=1, max_length=150)
    display_name: str = Field(min_length=1, max_length=150)
    tagline: Optional[str] = Field(None, max_length=255)
    primary_colour: str
    secondary_colour: str
    accent_colour: Optional[str] = None
    header_background_colour: Optional[str] = None
    sidebar_background_colour: Optional[str] = None
    font_family: Optional[str] = None
    login_page_title: Optional[str] = Field(None, max_length=150)
    login_page_message: Optional[str] = Field(None, max_length=2000)
    footer_text: Optional[str] = Field(None, max_length=2000)
    custom_css: Optional[str] = None
    branding_status: str = "Draft"

    @field_validator("primary_colour", "secondary_colour", "accent_colour", "header_background_colour", "sidebar_background_colour")
    @classmethod
    def colour(cls, value):
        return rules.validate_colour(value)

    @field_validator("custom_css")
    @classmethod
    def css(cls, value):
        return rules.validate_custom_css(value)

    @model_validator(mode="after")
    def choices(self):
        if self.tenant_level not in rules.TENANT_LEVELS:
            raise ValueError("Tenant level must be State or ULB.")
        if self.tenant_level == "ULB" and not self.ulb_tenant_id:
            raise ValueError("Select the ULB / City for a ULB profile.")
        if self.branding_status not in rules.RECORD_STATUSES:
            raise ValueError("Unknown branding status.")
        if self.font_family and self.font_family not in rules.FONT_FAMILIES:
            raise ValueError("Unknown font family.")
        if not self.primary_colour or not self.secondary_colour:
            raise ValueError("Primary and secondary colours are required.")
        return self


class BrandingProfileOut(CamelModel):
    id: str
    tenant_id: str
    tenant_level: str
    state_tenant_id: str
    ulb_tenant_id: Optional[str] = None
    profile_name: str
    display_name: str
    tagline: Optional[str] = None
    primary_colour: str
    secondary_colour: str
    accent_colour: Optional[str] = None
    header_background_colour: Optional[str] = None
    sidebar_background_colour: Optional[str] = None
    font_family: Optional[str] = None
    login_page_title: Optional[str] = None
    login_page_message: Optional[str] = None
    footer_text: Optional[str] = None
    custom_css: Optional[str] = None
    branding_status: str
    updated_at: Optional[datetime.datetime] = None


class AssetFileOut(CamelModel):
    id: str
    file_kind: str
    content_type: str
    size_bytes: int


class AssetSetOut(CamelModel):
    id: str
    tenant_id: str
    logo_type: str
    alt_text: str
    effective_from: Optional[datetime.datetime] = None
    asset_status: str
    files: List[AssetFileOut] = []
    updated_at: Optional[datetime.datetime] = None


class AssetSetUpdate(CamelModel):
    alt_text: str = Field(min_length=1, max_length=255)
    effective_from: Optional[datetime.datetime] = None
    asset_status: str

    @field_validator("asset_status")
    @classmethod
    def status(cls, value):
        if value not in rules.RECORD_STATUSES:
            raise ValueError("Unknown asset status.")
        return value


class PublicBranding(CamelModel):
    display_name: str
    tagline: Optional[str] = None
    primary_colour: str
    secondary_colour: str
    accent_colour: Optional[str] = None
    header_background_colour: Optional[str] = None
    sidebar_background_colour: Optional[str] = None
    font_family: Optional[str] = None
    login_page_title: Optional[str] = None
    login_page_message: Optional[str] = None
    footer_text: Optional[str] = None
    custom_css: Optional[str] = None
    alt_text: Optional[str] = None
    assets: Dict[str, str] = {}


class DomainCreate(CamelModel):
    tenant_id: str = Field(min_length=1, max_length=50)
    domain_name: str = Field(min_length=1, max_length=253)
    domain_type: str
    subdomain: Optional[str] = Field(None, max_length=63)
    root_domain: Optional[str] = Field(None, max_length=253)
    dns_provider: Optional[str] = None
    dns_record_type: str
    dns_host: str = Field(min_length=1, max_length=253)
    dns_target: str = Field(min_length=1, max_length=253)
    verification_method: str
    is_primary: bool = False

    @model_validator(mode="after")
    def choices(self):
        self.domain_name = rules.normalize_domain(self.domain_name)
        if self.domain_type not in rules.DOMAIN_TYPES:
            raise ValueError("Unknown domain type.")
        if self.dns_record_type not in rules.DNS_RECORD_TYPES:
            raise ValueError("Unknown DNS record type.")
        if self.verification_method not in rules.VERIFICATION_METHODS:
            raise ValueError("Unknown verification method.")
        if self.dns_provider and self.dns_provider not in rules.DNS_PROVIDERS:
            raise ValueError("Unknown DNS provider.")
        if self.domain_type == "Subdomain":
            if not self.root_domain:
                raise ValueError("Root domain is required for a subdomain.")
            self.root_domain = rules.normalize_domain(self.root_domain)
            if not self.domain_name.endswith("." + self.root_domain):
                raise ValueError("The domain name must sit under the root domain.")
        elif self.root_domain:
            self.root_domain = rules.normalize_domain(self.root_domain)
        return self


class DomainUpdate(CamelModel):
    dns_provider: Optional[str] = None
    dns_record_type: str
    dns_host: str = Field(min_length=1, max_length=253)
    dns_target: str = Field(min_length=1, max_length=253)
    verification_method: str
    is_primary: bool = False
    domain_status: str

    @model_validator(mode="after")
    def choices(self):
        if self.dns_record_type not in rules.DNS_RECORD_TYPES:
            raise ValueError("Unknown DNS record type.")
        if self.verification_method not in rules.VERIFICATION_METHODS:
            raise ValueError("Unknown verification method.")
        if self.domain_status not in rules.DOMAIN_STATUSES:
            raise ValueError("Unknown domain status.")
        if self.dns_provider and self.dns_provider not in rules.DNS_PROVIDERS:
            raise ValueError("Unknown DNS provider.")
        return self


class DomainOut(CamelModel):
    id: str
    tenant_id: str
    domain_name: str
    domain_type: str
    subdomain: Optional[str] = None
    root_domain: Optional[str] = None
    dns_provider: Optional[str] = None
    dns_record_type: str
    dns_host: str
    dns_target: str
    verification_method: str
    verification_status: str
    verification_token: str
    verification_instructions: str = ""
    claim_expires_at: Optional[datetime.datetime] = None
    last_checked_at: Optional[datetime.datetime] = None
    last_check_message: Optional[str] = None
    is_primary: bool
    domain_status: str


class CertificateOut(CamelModel):
    """Deliberately has no field for key material or certificate contents."""
    id: str
    tenant_id: str
    domain_id: str
    domain_name: str = ""
    provider: str
    certificate_type: str
    has_private_key: bool = False
    auto_renewal: bool
    renewal_notification_days: int
    expiry_date: Optional[datetime.datetime] = None
    certificate_status: str
    status_message: Optional[str] = None
    last_validation_at: Optional[datetime.datetime] = None


class CertificateUpdate(CamelModel):
    auto_renewal: bool = False
    renewal_notification_days: int = Field(30, ge=1, le=120)


class MappingPayload(CamelModel):
    mapping_name: str = Field(min_length=1, max_length=150)
    tenant_id: str = Field(min_length=1, max_length=50)
    domain_id: str = Field(min_length=1, max_length=36)
    target_application: str
    target_service: str = Field(min_length=1, max_length=50)
    target_route: Optional[str] = Field(None, max_length=255)
    routing_strategy: str
    ssl_required: bool = True
    force_https: bool = True
    is_primary: bool = False
    mapping_status: str = "Draft"
    effective_from: Optional[datetime.datetime] = None

    @model_validator(mode="after")
    def choices(self):
        self.target_route = rules.validate_route(self.target_route)
        if self.target_application not in rules.TARGET_APPLICATIONS:
            raise ValueError("Unknown target application.")
        if self.routing_strategy not in rules.ROUTING_STRATEGIES:
            raise ValueError("Unknown routing strategy.")
        if self.routing_strategy == rules.ROUTING_REDIRECT and not self.target_route:
            raise ValueError("A root redirect needs a target route.")
        if self.mapping_status not in rules.RECORD_STATUSES:
            raise ValueError("Unknown mapping status.")
        if self.force_https and not self.ssl_required:
            raise ValueError("Force HTTPS needs SSL Required to be on.")
        return self


class MappingOut(CamelModel):
    id: str
    tenant_id: str
    domain_id: str
    domain_name: str = ""
    mapping_name: str
    target_application: str
    target_service: str
    target_route: Optional[str] = None
    routing_strategy: str
    ssl_required: bool
    force_https: bool
    is_primary: bool
    mapping_status: str
    effective_from: Optional[datetime.datetime] = None


class RoutingStatus(CamelModel):
    applied_version: Optional[str] = None
    pending_version: Optional[str] = None
    last_error: Optional[str] = None
