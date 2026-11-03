# Urban Integrated Municipal ERP — Project Memory & Architecture Truth
## Canonical Reference for AI Agents & Developers

---

## 1. Tenancy Model Law (3-Tier SaaS)

1. **Level 0: The Boss (Platform Super Admin)**
   - Cross-state, multi-tenant administrative visibility.
   - Manages all States (Tenants), Cities (Sub-Tenants), and user provisioning.
   - Consolidated executive analytics across all jurisdictions.
2. **Level 1: Tenant (State, e.g. Telangana `TG`, Maharashtra `MH`)**
   - Subscribes to any subset of the **19 Platform Modules**.
   - Manages State-level officers and provisions child Sub-Tenants (Cities / ULBs / Departments).
3. **Level 2: Sub-Tenant (City / ULB / Department, e.g. GWMC, GHMC, CDMA-TP)**:
   - Module allocations strictly cascade from parent State Tenant subscriptions.
   - Manages local city inspectors, bill collectors, citizens, and local municipal operations.

---

## 2. 19 Modules & Delivery Phasing

All 19 municipal modules decompose into **415 granular RBAC components**, delivered across 4 operational phases. The 415 excludes the super admin platform features (`ADM-*`), which are counted separately in [PHASE.md](../docs/PHASE.md).

- **Phase 0: Inception & Mobilisation** (Infra, State Data Centre, baseline architecture)
- **Phase 1: Foundation & Revenue Core (155 Components)**:
  - `PTX`: Property Tax & Revenue (33)
  - `WTR`: Water, Sewerage & Utilities (32)
  - `GRV`: Citizen Grievance & RTI (30)
  - `FIN`: Finance & Accounting (30)
  - `DMS`: Document Management System (30)
- **Phase 2: Regulation & Licensing (111 Components)**:
  - `TRL`: Trade Licences (26)
  - `UCH`: User Charges (23)
  - `BPM`: Building Permissions (22)
  - `TPL`: Town Planning (23)
  - `FNC`: Fire NOC (17)
- **Phase 3: Field Operations & Infrastructure (84 Components)**:
  - `SWM`: Solid Waste Management (17)
  - `ENG`: Engineering Projects / e-MB (20)
  - `SLM`: Street Lights (12)
  - `PRK`: Parks & Horticulture (18)
  - `INV`: Inventory & Stores (17)
- **Phase 4: Administration, Estates & Welfare (65 Components)**:
  - `HRM`: Payroll & HR (19)
  - `MPM`: Municipal Property (15)
  - `LGL`: Legal Cases (17)
  - `GSC`: Government Schemes (14)

See detailed breakdown in [docs/PHASE.md](../docs/PHASE.md) and [docs/MODULE_COMPONENTS_CATALOGUE.md](../docs/MODULE_COMPONENTS_CATALOGUE.md).

---

## 3. Granular RBAC Standard

- Permissions are checked per component action: `{MODULE}-{COMPONENT_ID}:{ACTION}`, e.g. `PTX-P10:APPROVE`. Actions are VIEW, CREATE, UPDATE, DELETE, APPROVE, EXPORT and MANAGE.
- Core routes use `Depends(require_permission("PTX-P10", "APPROVE"))`. Module services use `require_access("PTX-P10", "APPROVE")` from `urban_common.authz`, which asks core through `POST /api/v1/auth/authorize`.
- Cross-tenant grants (ADM-R02) and support sessions (ADM-R04) are applied inside that same check, so module services follow them without their own code.

---

## 4. Coding & Tech Stack Conventions

- **Frontend**: Angular 22.2 Standalone (no NgModules). Signals (`signal()`, `computed()`, `effect()`) for reactive state. Custom SCSS design tokens (no TailwindCSS).
- **Backend**: FastAPI + Async SQLAlchemy (PostgreSQL 16 + PostGIS 3.4). All schemas inherit from `CamelModel` (`to_camel`).
- **Tenancy Context**: Headers `X-Tenant-ID` and `X-Sub-Tenant-ID` sent on all requests; resolved via `get_current_tenant` and `get_current_sub_tenant`.
- **Cache Isolation**: Valkey keys formatted as `stats:tenant:{tenant_id}:sub:{sub_tenant_id}:{resource}`.
- **Production Standard**: No mock/demo chips, no "Protected by..." badges, clean enterprise styling.
- **Pre-Push Validation**: `scripts/validate_structures.sh`, run by `.githooks/pre-push`, checks directories, Python compilation, the Angular build and all unit tests.

---

## 5. Platform Modules Built So Far

Each has a section in [SECURITY.md](../docs/SECURITY.md) with what it enforces and its known gaps.

| Code | Module | Notes |
|---|---|---|
| ADM-A04 | Spatial GIS multi-city viewer | PostGIS geometry, Cesium for 2D and 3D, WFS clipped to the ULB boundary |
| ADM-T04 | White-labelling and domains | Branding, assets, domain verification, certificates, gateway host sync |
| ADM-S04 | Quotas and usage | Storage, SMS credits and API limits measured from real usage, with alerts |
| ADM-R02 | Cross-tenant access | Approved grants, scopes, Deny rules and certification, checked on every request |
| ADM-R04 | Support impersonation | Approved, time-limited sessions without credentials, with masking and a full audit trail |

How to build the next one: [ENGINEERING_PLAYBOOK.md](../docs/ENGINEERING_PLAYBOOK.md).
