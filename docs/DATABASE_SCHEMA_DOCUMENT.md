# Urban Integrated Municipal ERP — Database Schema Specification
## Multi-Tier Tenancy, Subscription Cascades & Component-Level RBAC

**Database Engine**: PostgreSQL 16 + PostGIS Extension  
**Naming Standard**: `snake_case` for tables and columns  
**Primary Keys**: UUID v4 (`CHAR(36)`) or standardized uppercase codes (`VARCHAR(50)`)  

---

## 1. Entity-Relationship Overview

```
┌─────────────────────────────────┐
│            tenants              │ (Level 1: State Tenant)
│  PK tenant_id (e.g., 'TG')      │
└────────────────┬────────────────┘
                 │ 1:N
                 ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│          sub_tenants            │       │             modules             │ (19 Official Modules)
│  PK id (UUID)                   │       │  PK code (e.g., 'PTX')          │
│  FK tenant_id                   │       └────────────────┬────────────────┘
│     code ('GWMC')               │                        │ 1:N
└──────┬──────────────────────────┘                        ▼
       │ 1:N                               ┌─────────────────────────────────┐
       │                                   │        module_components        │ (405 Processes)
       │                                   │  PK component_code ('PTX-P01')  │
       │                                   │  FK module_code                 │
       │                                   └────────────────┬────────────────┘
       │                                                    │ 1:N
       ├────────────────────────┐                           │
       ▼                        ▼                           ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────────┐
│ tenant_subscriptions │ │sub_tenant_subscript's│ │role_component_permissions│
│  FK tenant_id        │ │  FK sub_tenant_id    │ │  FK role_id              │
│  FK module_code      │ │  FK module_code      │ │  FK component_code       │
│  status: 'ACTIVE'    │ │  status: 'ACTIVE'    │ │  action: 'APPROVE'       │
└──────────────────────┘ └──────────────────────┘ └──────────────────────────┘
```

---

## 2. Table Specifications & DDL Definitions

### 2.1 Multi-Tier Tenancy Tables

```sql
-- Level 1: State Tenant
CREATE TABLE tenants (
    tenant_id VARCHAR(50) PRIMARY KEY, -- e.g. 'TG', 'MH', 'KA'
    name VARCHAR(150) NOT NULL,        -- 'Telangana State Municipal Administration'
    state_code VARCHAR(10) NOT NULL,   -- 'TG'
    capital_city VARCHAR(100),
    contact_email VARCHAR(150),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Level 2: Sub-Tenant (City / ULB / Municipal Corporation / Department)
CREATE TABLE sub_tenants (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenants(tenant_id) ON DELETE RESTRICT,
    code VARCHAR(50) NOT NULL,         -- e.g. 'GWMC', 'GHMC', 'CDMA-TP'
    name VARCHAR(150) NOT NULL,        -- 'Greater Warangal Municipal Corporation'
    entity_type VARCHAR(50) NOT NULL,  -- 'MUNICIPAL_CORP', 'MUNICIPALITY', 'DEPARTMENT'
    district VARCHAR(100) NOT NULL,
    pincode_headquarter VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tenant_subtenant UNIQUE (tenant_id, code)
);
```

### 2.2 Module Catalogue & Cascading Subscriptions

```sql
-- Master 19 Modules Directory
CREATE TABLE modules (
    code VARCHAR(10) PRIMARY KEY,      -- 'PTX', 'WTR', 'GRV', 'FIN', etc.
    name VARCHAR(150) NOT NULL,
    domain VARCHAR(100) NOT NULL,      -- 'Revenue & Billing', 'Planning & Regulation'
    phase INTEGER NOT NULL DEFAULT 1,
    icon VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Granular 405 Components / Processes
CREATE TABLE module_components (
    component_code VARCHAR(30) PRIMARY KEY, -- 'PTX-P01', 'BPM-B05', etc.
    module_code VARCHAR(10) NOT NULL REFERENCES modules(code) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Level 1: State Tenant Subscriptions
CREATE TABLE tenant_subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    module_code VARCHAR(10) NOT NULL REFERENCES modules(code) ON DELETE RESTRICT,
    is_active BOOLEAN DEFAULT TRUE,
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_tenant_module UNIQUE (tenant_id, module_code)
);

-- Level 2: Sub-Tenant Module Allocations (Must be subset of State Subscriptions)
CREATE TABLE sub_tenant_subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    sub_tenant_id VARCHAR(36) NOT NULL REFERENCES sub_tenants(id) ON DELETE CASCADE,
    module_code VARCHAR(10) NOT NULL REFERENCES modules(code) ON DELETE RESTRICT,
    is_active BOOLEAN DEFAULT TRUE,
    allocated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_subtenant_module UNIQUE (sub_tenant_id, module_code)
);
```

### 2.3 User Identity & Delegated Administration

```sql
-- Global User Records
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    mobile_number VARCHAR(20),
    is_super_admin BOOLEAN DEFAULT FALSE, -- "The Boss" global platform administrator
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Roles (Defined at Global, State, or Sub-Tenant Level)
CREATE TABLE roles (
    id VARCHAR(36) PRIMARY KEY,
    scope_level VARCHAR(20) NOT NULL,     -- 'GLOBAL', 'TENANT', 'SUB_TENANT'
    tenant_id VARCHAR(50) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    sub_tenant_id VARCHAR(36) REFERENCES sub_tenants(id) ON DELETE CASCADE,
    role_code VARCHAR(50) NOT NULL,       -- 'state_revenue_commissioner', 'city_revenue_officer'
    name VARCHAR(150) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_role_code_scope UNIQUE (scope_level, COALESCE(tenant_id, ''), COALESCE(sub_tenant_id, ''), role_code)
);

-- Component-Level RBAC Permissions
CREATE TABLE role_component_permissions (
    id VARCHAR(36) PRIMARY KEY,
    role_id VARCHAR(36) NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    module_code VARCHAR(10) NOT NULL REFERENCES modules(code) ON DELETE CASCADE,
    component_code VARCHAR(30) NOT NULL REFERENCES module_components(component_code) ON DELETE CASCADE,
    can_view BOOLEAN DEFAULT TRUE,
    can_create BOOLEAN DEFAULT FALSE,
    can_update BOOLEAN DEFAULT FALSE,
    can_approve BOOLEAN DEFAULT FALSE,
    can_delete BOOLEAN DEFAULT FALSE,
    CONSTRAINT uq_role_component UNIQUE (role_id, component_code)
);

-- User Multi-Tenant Scope Memberships
CREATE TABLE user_memberships (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    sub_tenant_id VARCHAR(36) REFERENCES sub_tenants(id) ON DELETE CASCADE,
    role_id VARCHAR(36) NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    is_default_scope BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_membership UNIQUE (user_id, tenant_id, COALESCE(sub_tenant_id, ''))
);
```

### 2.4 Multi-Tenant Domain Schema (ULPIN Property Spine)

```sql
-- All municipal transactional entities inherit dual scoping: tenant_id and sub_tenant_id
CREATE TABLE property_parcels (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenants(tenant_id) ON DELETE RESTRICT,
    sub_tenant_id VARCHAR(36) NOT NULL REFERENCES sub_tenants(id) ON DELETE RESTRICT,
    ulpin VARCHAR(50) UNIQUE NOT NULL,    -- 'TG-GWMC-506001-00123'
    survey_number VARCHAR(50) NOT NULL,
    plot_number VARCHAR(50),
    total_area_sqyd DOUBLE PRECISION NOT NULL,
    ward_id VARCHAR(36) NOT NULL,
    locality_id VARCHAR(36),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    address TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_parcels_tenant_subtenant ON property_parcels (tenant_id, sub_tenant_id);
CREATE INDEX idx_parcels_ulpin ON property_parcels (ulpin);
```
