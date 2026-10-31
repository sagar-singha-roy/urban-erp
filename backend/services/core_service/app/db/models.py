import datetime
import uuid
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, Numeric, JSON
)
from sqlalchemy.orm import relationship
from app.db.session import Base

class Tenant(Base):
    __tablename__ = "tenants"

    tenant_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    state_code = Column(String(10), nullable=False, default="TG")
    district = Column(String(100), nullable=False, default="Warangal")
    parent_state_tenant_id = Column(String(50), nullable=True, index=True)
    ulb_code = Column(String(30), nullable=True, index=True)
    tenant_slug = Column(String(100), nullable=True, index=True)
    ulb_type = Column(String(50), nullable=False, default="Municipal Corporation")
    administrative_grade = Column(String(50), nullable=True)
    official_website = Column(String(255), nullable=True)
    official_email = Column(String(150), nullable=True)
    contact_phone = Column(String(30), nullable=True)
    office_address = Column(Text, nullable=True)
    time_zone = Column(String(50), default="Asia/Kolkata", nullable=False)
    primary_language = Column(String(50), default="English", nullable=False)
    status = Column(String(20), default="Draft", nullable=False) # Draft, Active, Suspended
    enable_zones = Column(Boolean, default=False)
    enable_wards = Column(Boolean, default=True)
    effective_date = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    zones = relationship("Zone", back_populates="tenant", cascade="all, delete-orphan")
    wards = relationship("Ward", back_populates="tenant", cascade="all, delete-orphan")
    parcels = relationship("PropertyParcel", back_populates="tenant", cascade="all, delete-orphan")

class Zone(Base):
    __tablename__ = "zones"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)

    tenant = relationship("Tenant", back_populates="zones")
    wards = relationship("Ward", back_populates="zone")

class Ward(Base):
    __tablename__ = "wards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    zone_id = Column(String(36), ForeignKey("zones.id"), nullable=True, index=True)
    ward_number = Column(Integer, nullable=False, index=True)
    ward_code = Column(String(30), nullable=True)
    ward_name = Column(String(100), nullable=False)
    councilor_name = Column(String(100), nullable=True)
    boundary_geometry = Column(JSON, nullable=True)
    effective_from = Column(String(30), nullable=True)

    tenant = relationship("Tenant", back_populates="wards")
    zone = relationship("Zone", back_populates="wards")
    localities = relationship("Locality", back_populates="ward", cascade="all, delete-orphan")
    parcels = relationship("PropertyParcel", back_populates="ward")

class Locality(Base):
    __tablename__ = "localities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    ward_id = Column(String(36), ForeignKey("wards.id"), nullable=False, index=True)
    locality_code = Column(String(30), nullable=False)
    locality_name = Column(String(150), nullable=False)
    pincode = Column(String(10), nullable=False)

    ward = relationship("Ward", back_populates="localities")
    parcels = relationship("PropertyParcel", back_populates="locality")

class PropertyParcel(Base):
    __tablename__ = "property_parcels"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id"), nullable=False, index=True)
    ulpin = Column(String(50), unique=True, nullable=False, index=True)
    survey_number = Column(String(50), nullable=False)
    plot_number = Column(String(50), nullable=True)
    total_area_sqyd = Column(Float, nullable=False)
    
    ward_id = Column(String(36), ForeignKey("wards.id"), nullable=False, index=True)
    locality_id = Column(String(36), ForeignKey("localities.id"), nullable=True)
    
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    tenant = relationship("Tenant", back_populates="parcels")
    ward = relationship("Ward", back_populates="parcels")
    locality = relationship("Locality", back_populates="parcels")
    buildings = relationship("Building", back_populates="parcel", cascade="all, delete-orphan")

class Building(Base):
    __tablename__ = "buildings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), nullable=False, index=True)
    parcel_id = Column(String(36), ForeignKey("property_parcels.id"), nullable=False, index=True)
    
    building_name = Column(String(150), nullable=True)
    building_type = Column(String(50), nullable=False) # Residential, Commercial, Mixed, Industrial
    total_floors = Column(Integer, default=1)
    construction_year = Column(Integer, nullable=True)
    building_permission_no = Column(String(100), nullable=True)

    parcel = relationship("PropertyParcel", back_populates="buildings")
    units = relationship("PropertyUnit", back_populates="building", cascade="all, delete-orphan")

class PropertyUnit(Base):
    __tablename__ = "property_units"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), nullable=False, index=True)
    building_id = Column(String(36), ForeignKey("buildings.id"), nullable=False, index=True)
    
    ptin = Column(String(30), unique=True, nullable=False, index=True) # 10-digit Property Tax Identification Number
    unit_number = Column(String(50), nullable=False)
    floor_number = Column(Integer, default=0) # 0 = Ground
    usage_category = Column(String(50), nullable=False) # Residential, Commercial, Institutional, Vacant Land
    
    carpet_area_sqft = Column(Float, nullable=False)
    built_up_area_sqft = Column(Float, nullable=False)
    occupancy_type = Column(String(30), nullable=False) # Owner, Tenant, Vacant
    
    annual_rental_value = Column(Numeric(12, 2), default=0.0)
    current_demand_amount = Column(Numeric(12, 2), default=0.0)
    tax_status = Column(String(30), default="PAID") # PAID, DUE, ARREARS, EXEMPT

    building = relationship("Building", back_populates="units")
    owners = relationship("Owner", back_populates="unit", cascade="all, delete-orphan")

class Owner(Base):
    __tablename__ = "owners"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), nullable=False, index=True)
    unit_id = Column(String(36), ForeignKey("property_units.id"), nullable=False, index=True)
    
    full_name = Column(String(150), nullable=False)
    mobile_number = Column(String(15), nullable=False, index=True)
    email = Column(String(100), nullable=True)
    aadhaar_vault_ref = Column(String(64), nullable=True)
    ownership_share = Column(Float, default=100.0) # Percentage

    unit = relationship("PropertyUnit", back_populates="owners")

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id"), nullable=False, default="GWMC")
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), nullable=False, default="citizen") # super_admin, revenue_officer, town_planner, engineering_officer, citizen
    assigned_modules = Column(Text, nullable=False, default="GRV,PTX,WTR") # Comma-separated list of 19 module codes
    assigned_zone = Column(String(50), nullable=True)
    assigned_ward = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class StateTenant(Base):
    __tablename__ = "state_tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    state_name = Column(String(100), nullable=False)
    state_code = Column(String(10), unique=True, index=True, nullable=False)
    tenant_slug = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(20), default="Draft", nullable=False) # Draft, Active, Suspended
    country = Column(String(50), default="India", nullable=False)
    time_zone = Column(String(50), default="Asia/Kolkata", nullable=False)
    primary_language = Column(String(50), default="English", nullable=False)
    additional_languages = Column(JSON, default=list, nullable=True)
    official_state_name = Column(String(200), nullable=True)
    state_emblem_url = Column(Text, nullable=True)
    state_website = Column(String(255), nullable=True)
    administrative_email = Column(String(150), nullable=False)
    administrative_phone = Column(String(30), nullable=True)
    address = Column(Text, nullable=True)
    effective_date = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class TenantAuditLog(Base):
    __tablename__ = "tenant_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False) # CREATED, DRAFT_SAVED, ACTIVATED, SUSPENDED, UPDATED
    performed_by = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)

class State(Base):
    __tablename__ = "states"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(10), unique=True, index=True, nullable=False) # e.g. TR, TG, MH
    name = Column(String(100), nullable=False, index=True)
    official_name = Column(String(200), nullable=False)
    default_slug = Column(String(100), unique=True, nullable=False)
    primary_language = Column(String(50), default="English", nullable=False)
    additional_languages = Column(JSON, default=list, nullable=True)
    zone = Column(String(50), nullable=True) # North, South, East, West, Central, North East, UT
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    districts = relationship("District", back_populates="state", cascade="all, delete-orphan")
    cities = relationship("City", back_populates="state", cascade="all, delete-orphan")

class District(Base):
    __tablename__ = "districts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    state_code = Column(String(10), ForeignKey("states.code"), nullable=False, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False, index=True)
    headquarters = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    state = relationship("State", back_populates="districts")
    cities = relationship("City", back_populates="district", cascade="all, delete-orphan")

class City(Base):
    __tablename__ = "cities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    state_code = Column(String(10), ForeignKey("states.code"), nullable=False, index=True)
    district_id = Column(String(36), ForeignKey("districts.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    ulb_type = Column(String(50), default="Municipal Corporation", nullable=False)
    ulb_code = Column(String(30), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    state = relationship("State", back_populates="cities")
    district = relationship("District", back_populates="cities")

class ModuleModel(Base):
    __tablename__ = "modules"

    module_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(150), nullable=False)
    code = Column(String(20), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)  # Revenue & Billing, Finance & Administration, Planning & Regulation, Infrastructure & Field Operations, Citizen Engagement & Welfare
    icon = Column(String(50), nullable=True)
    display_order = Column(Integer, default=1, nullable=False)
    module_version = Column(String(20), default="1.0.0", nullable=False)
    status = Column(String(20), default="Published", nullable=False)  # Draft, Published, Deprecated
    dependencies = Column(JSON, default=list, nullable=True)
    minimum_platform_version = Column(String(20), nullable=True)
    documentation_url = Column(String(255), nullable=True)
    effective_from = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    components = relationship("ComponentModel", back_populates="module", cascade="all, delete-orphan")

class ComponentModel(Base):
    __tablename__ = "components"

    component_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_module_code = Column(String(20), ForeignKey("modules.code"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    code = Column(String(30), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    component_type = Column(String(50), default="Process", nullable=False)  # Process, Service, UI View, Report, Workflow
    route_path = Column(String(255), nullable=True)
    frontend_permission_key = Column(String(100), nullable=False)
    backend_api_permission_key = Column(String(100), nullable=False)
    supported_actions = Column(JSON, default=list, nullable=False)
    dependencies = Column(JSON, default=list, nullable=True)
    status = Column(String(20), default="Published", nullable=False)  # Draft, Published, Deprecated
    display_order = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    module = relationship("ModuleModel", back_populates="components")

class ModuleChangeHistory(Base):
    __tablename__ = "module_change_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type = Column(String(20), nullable=False)  # MODULE or COMPONENT
    entity_code = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)  # CREATED, UPDATED, PUBLISHED, DEPRECATED, IMPORTED
    performed_by = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(Text, nullable=True)

class SSOConfiguration(Base):
    __tablename__ = "sso_configurations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_name = Column(String(100), nullable=False, default="SUVIDHA Central Keycloak Identity")
    provider_type = Column(String(50), nullable=False, default="Keycloak")
    keycloak_base_url = Column(String(255), nullable=False, default="http://localhost:8080")
    keycloak_realm = Column(String(100), nullable=False, default="urban-suvidha")
    client_id = Column(String(100), nullable=False, default="urban-console")
    client_secret = Column(String(255), nullable=True)
    redirect_uri = Column(String(255), nullable=False, default="http://localhost:4200/auth/callback")
    post_logout_redirect_uri = Column(String(255), nullable=True, default="http://localhost:4200/login")
    oidc_scopes = Column(JSON, default=lambda: ["openid", "profile", "email", "roles"], nullable=False)
    discovery_url = Column(String(255), nullable=True)
    connection_status = Column(String(30), default="Connected", nullable=False)
    last_connection_test = Column(DateTime, default=datetime.datetime.utcnow)

    # Authentication & SSO Policy
    enable_sso = Column(Boolean, default=True, nullable=False)
    login_methods = Column(JSON, default=lambda: ["Password", "SSO", "OTP"], nullable=False)
    mfa_required = Column(Boolean, default=False, nullable=False)
    mfa_policy = Column(String(50), default="Admins Only", nullable=False)  # Optional, Admins Only, Mandatory All
    allowed_identity_providers = Column(JSON, default=list, nullable=True)
    session_idle_timeout_mins = Column(Integer, default=30, nullable=False)
    max_session_lifetime_mins = Column(Integer, default=480, nullable=False)
    remember_me = Column(Boolean, default=True, nullable=False)
    brute_force_protection = Column(Boolean, default=True, nullable=False)
    max_failed_attempts = Column(Integer, default=5, nullable=False)
    password_min_length = Column(Integer, default=8, nullable=False)
    password_require_uppercase = Column(Boolean, default=True, nullable=False)
    password_require_lowercase = Column(Boolean, default=True, nullable=False)
    password_require_digits = Column(Boolean, default=True, nullable=False)
    password_require_special = Column(Boolean, default=True, nullable=False)
    password_expiry_days = Column(Integer, default=90, nullable=False)
    allowed_email_domains = Column(JSON, default=lambda: ["gov.in", "nic.in", "urban.gov.in"], nullable=False)
    require_verified_email = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class IdentityProviderFederation(Base):
    __tablename__ = "identity_provider_federations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    protocol = Column(String(20), nullable=False, default="OIDC")  # OIDC, SAML
    issuer_url = Column(String(255), nullable=False)
    client_id = Column(String(100), nullable=True)
    client_secret = Column(String(255), nullable=True)
    metadata_url = Column(String(255), nullable=True)
    claim_mapping = Column(JSON, default=lambda: {"sub": "sub", "email": "email", "name": "name", "roles": "roles"}, nullable=False)
    user_linking_policy = Column(String(50), default="Auto-link by Email", nullable=False)  # Auto-link by Email, Require Manual Verification, Disabled
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class AuthenticationAuditLog(Base):
    __tablename__ = "authentication_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(50), nullable=False)  # LOGIN_SUCCESS, LOGIN_FAILURE, MFA_CHALLENGE, SSO_REDIRECT, PASSWORD_RESET, FEDERATION_TOKEN_EXCHANGED
    username = Column(String(150), nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    idp_used = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    status = Column(String(20), default="SUCCESS", nullable=False)  # SUCCESS, FAILED, BLOCKED
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class RoleModel(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    role_level = Column(String(50), nullable=False)  # Platform Super Admin, State Admin, ULB Admin, Department Admin, Officer, Auditor, Read-only User
    scope_type = Column(String(50), nullable=False)  # Platform, State, ULB, Department, Ward
    parent_role_id = Column(String(36), nullable=True)
    status = Column(String(20), default="Active", nullable=False)  # Active, Inactive, Deprecated
    effective_from = Column(DateTime, nullable=True)
    effective_until = Column(DateTime, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    is_template = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), index=True, nullable=False)
    module_code = Column(String(20), index=True, nullable=False)
    component_code = Column(String(50), index=True, nullable=False)
    can_view = Column(Boolean, default=False, nullable=False)
    can_create = Column(Boolean, default=False, nullable=False)
    can_update = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)
    can_approve = Column(Boolean, default=False, nullable=False)
    can_export = Column(Boolean, default=False, nullable=False)
    can_manage = Column(Boolean, default=False, nullable=False)
    data_scope = Column(String(50), default="Own Records", nullable=False)  # Own Records, Assigned Department, Ward, ULB, State, Platform
    conditions = Column(JSON, nullable=True)
    effective_from = Column(DateTime, nullable=True)
    effective_until = Column(DateTime, nullable=True)

class GlobalUserProfile(Base):
    __tablename__ = "global_user_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    mobile_number = Column(String(20), nullable=True)
    idp_provider = Column(String(50), default="Keycloak Suvidha", nullable=False)
    external_identity_id = Column(String(100), nullable=True)
    user_type = Column(String(50), default="Internal Staff", nullable=False)  # Internal Staff, Government Officer, Support Staff, Auditor, External Partner
    account_status = Column(String(20), default="Active", nullable=False)  # Active, Suspended, Pending Invitation, Deactivated
    preferred_language = Column(String(20), default="English", nullable=False)
    time_zone = Column(String(50), default="Asia/Kolkata", nullable=False)
    employee_id = Column(String(50), nullable=True)
    designation = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    profile_photo_url = Column(String(255), nullable=True)
    account_expiry_date = Column(DateTime, nullable=True)
    remarks = Column(Text, nullable=True)

    # Scopes
    platform_access = Column(Boolean, default=False, nullable=False)
    state_tenant_id = Column(String(50), nullable=True)
    ulb_tenant_id = Column(String(50), nullable=True)
    assigned_department = Column(String(100), nullable=True)
    assigned_zone = Column(String(50), nullable=True)
    assigned_ward = Column(String(50), nullable=True)
    assigned_roles = Column(JSON, default=list, nullable=False)
    additional_permissions = Column(JSON, default=list, nullable=False)
    access_effective_from = Column(DateTime, nullable=True)
    access_effective_until = Column(DateTime, nullable=True)
    approval_reference = Column(String(100), nullable=True)
    last_active_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class UserInvitation(Base):
    __tablename__ = "user_invitations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(150), index=True, nullable=False)
    user_type = Column(String(50), default="Internal Staff", nullable=False)
    target_tenant_id = Column(String(50), nullable=False)
    target_sub_tenant_id = Column(String(50), nullable=True)
    assigned_role = Column(String(50), nullable=False)
    department_scope = Column(String(100), nullable=True)
    ward_scope = Column(String(50), nullable=True)
    invitation_token = Column(String(100), unique=True, index=True, nullable=False)
    invitation_expiry = Column(DateTime, nullable=False)
    require_mfa = Column(Boolean, default=True, nullable=False)
    invitation_message = Column(Text, nullable=True)
    status = Column(String(20), default="Pending", nullable=False)  # Pending, Accepted, Expired, Revoked
    invited_by = Column(String(150), default="Super Admin", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class RLSPolicyModel(Base):
    __tablename__ = "rls_policy_registry"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_name = Column(String(255), nullable=False)
    policy_code = Column(String(100), unique=True, index=True, nullable=False)
    database_service = Column(String(100), default="PostgreSQL 16 (Core Service)", nullable=False)
    schema_name = Column(String(100), default="public", nullable=False)
    table_name = Column(String(100), nullable=False)
    tenant_key_column = Column(String(100), default="tenant_id", nullable=False)
    policy_type = Column(String(50), default="ALL", nullable=False)  # SELECT, INSERT, UPDATE, DELETE, ALL
    database_commands = Column(JSON, default=list, nullable=False)  # ['SELECT', 'INSERT', 'UPDATE', 'DELETE']
    applicable_tenant_levels = Column(JSON, default=list, nullable=False)  # ['State', 'ULB', 'Department']
    policy_definition = Column(Text, nullable=False)
    policy_status = Column(String(50), default="ACTIVE", nullable=False)  # ACTIVE, DISABLED, PENDING_VERIFICATION
    last_verified_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_verification_result = Column(String(50), default="VERIFIED", nullable=False)  # VERIFIED, FAILED, UNTESTED
    verification_latency_ms = Column(Float, default=1.2, nullable=False)
    enforcement_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class TenantIsolationTestRun(Base):
    __tablename__ = "tenant_isolation_test_runs"

    id = Column(String(100), primary_key=True)  # e.g. ISO-RUN-2026-001
    test_run_name = Column(String(255), nullable=False)
    environment = Column(String(100), default="Isolated Sandbox", nullable=False)
    source_tenant = Column(String(255), nullable=False)
    target_tenant = Column(String(255), nullable=False)
    test_scenarios = Column(JSON, default=list, nullable=False)
    database_services = Column(JSON, default=list, nullable=False)
    tables_in_scope = Column(JSON, default=list, nullable=False)
    test_type = Column(String(100), default="Synthetic Penetration Test", nullable=False)
    execution_mode = Column(String(50), default="Automated Batch", nullable=False)
    schedule = Column(String(100), nullable=True)
    notification_recipients = Column(JSON, default=list, nullable=False)
    stop_on_critical_failure = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), default="PASSED", nullable=False)  # PASSED, FAILED, RUNNING, SCHEDULED
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, default=datetime.datetime.utcnow)
    total_tests = Column(Integer, default=8, nullable=False)
    passed_count = Column(Integer, default=8, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    execution_latency_ms = Column(Float, default=42.5, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class IsolationFindingReport(Base):
    __tablename__ = "isolation_finding_reports"

    id = Column(String(100), primary_key=True)  # e.g. SEC-FIND-2026-001
    test_run_id = Column(String(100), nullable=True)
    severity = Column(String(50), default="HIGH", nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    finding_title = Column(String(255), nullable=False)
    finding_description = Column(Text, nullable=False)
    affected_tenant = Column(String(255), nullable=False)
    affected_resource = Column(String(255), nullable=False)
    remediation_owner = Column(String(255), nullable=False)
    remediation_due_date = Column(String(50), nullable=False)
    resolution_notes = Column(Text, nullable=True)
    retest_status = Column(String(50), default="OPEN", nullable=False)  # OPEN, IN_REMEDIATION, RESOLVED, VERIFIED
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)




