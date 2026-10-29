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

All 19 municipal modules decompose into **415 granular RBAC components** delivered across 4 operational phases:

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

See detailed breakdown in [docs/PHASE.md](file:///Users/sagarsingharoy/Documents/urban/docs/PHASE.md) and [docs/MODULE_COMPONENTS_CATALOGUE.md](file:///Users/sagarsingharoy/Documents/urban/docs/MODULE_COMPONENTS_CATALOGUE.md).

---

## 3. Granular RBAC Standard

- Permissions evaluated at component action level: `{MODULE}-{COMPONENT_ID}:{ACTION}` (e.g. `PTX-P10:APPROVE`, `WTR-W12:SUBMIT`).
- Structural UI directive: `*hasComponentAccess="'PTX-P10:APPROVE'"`.
- Backend route protection: `@require_component_permission("PTX", "PTX-P10", "APPROVE")`.

---

## 4. Coding & Tech Stack Conventions

- **Frontend**: Angular 22.2 Standalone (no NgModules). Signals (`signal()`, `computed()`, `effect()`) for reactive state. Custom SCSS design tokens (no TailwindCSS).
- **Backend**: FastAPI + Async SQLAlchemy (PostgreSQL 16 + PostGIS 3.4). All schemas inherit from `CamelModel` (`to_camel`).
- **Tenancy Context**: Headers `X-Tenant-ID` and `X-Sub-Tenant-ID` sent on all requests; resolved via `get_current_tenant` and `get_current_sub_tenant`.
- **Cache Isolation**: Redis keys formatted as `stats:tenant:{tenant_id}:sub:{sub_tenant_id}:{resource}`.
- **Production Standard**: No mock/demo chips, no "Protected by..." badges, clean enterprise styling.
- **Pre-Push Validation**: Script `scripts/validate_structures.sh` and hook `.git/hooks/pre-push` enforce directory checks, python compilation, and clean Angular builds.
