# Urban Integrated Municipal ERP — Agent & Developer Context
## Shared Context for AI Agents and Human Developers

Welcome to the Urban Integrated Municipal ERP repository. This document defines the architectural laws, tenancy models, and directory boundaries that all contributors must obey.

---

## 1. Project Domain & Hierarchy Vision

Urban is an enterprise-grade, multi-tier SaaS municipal enterprise resource planning (ERP) platform designed for Urban Local Bodies (ULBs) and State Urban Development Departments.

### Hierarchical Administrative Model:
1. **Level 0: "The Boss" (Platform Super Admin)**:
   - Global multi-tenant visibility across all States, Cities, and Departments.
   - Cross-state analytics, financial consolidation, and system administration.
2. **Level 1: Tenant (State, e.g. Telangana `TG`, Maharashtra `MH`)**:
   - Subscribes to any subset of the **19 Platform Modules**.
   - Manages State-level officers and provisions child Sub-Tenants (Cities/ULBs/Departments).
3. **Level 2: Sub-Tenant (City / ULB / Department, e.g. GWMC, GHMC, CDMA-TP)**:
   - Receives module allocations strictly from the parent State Tenant's active subscriptions.
   - Manages local city inspectors, bill collectors, citizens, and local municipal operations.

---

## 2. 19 Official Modules & Component RBAC

The platform incorporates 19 standardized municipal modules across 5 domains:
1. **Revenue & Billing**: Property Tax (`PTX`), Water & Sewerage (`WTR`), Trade Licences (`TRL`), User Charges (`UCH`), Municipal Property (`MPM`).
2. **Finance & Administration**: Finance & Accounting (`FIN`), Payroll & HR (`HRM`), Document Management (`DMS`), Inventory & Stores (`INV`).
3. **Planning & Regulation**: Building Permissions (`BPM`), Town Planning (`TPL`), Legal Cases (`LGL`), Fire NOC (`FNC`).
4. **Infrastructure & Field Operations**: Solid Waste (`SWM`), Engineering Projects (`ENG`), Street Lights (`SLM`), Parks & Horticulture (`PRK`).
5. **Citizen Engagement & Welfare**: Citizen Grievance & RTI (`GRV`), Government Schemes (`GSC`).

**Granular Component RBAC**:
- Every module decomposes into 12 to 33 specific processes/components (total 405 components).
- Refer to [docs/MODULE_COMPONENTS_CATALOGUE.md](file:///Users/sagarsingharoy/Documents/urban/docs/MODULE_COMPONENTS_CATALOGUE.md) for the complete list.
- Permissions must be validated at the component action level (e.g., `PTX-P10:APPROVE`).

---

## 3. Strict Coding Conventions & Architecture Boundaries

### 3.1 Backend Architecture (FastAPI + Async SQLAlchemy)
- Root: `backend/services/core_service/app/`
- Every database query touching municipal entities MUST filter by `tenant_id` and (when in city context) `sub_tenant_id`.
- Pydantic models must inherit from `CamelModel` (`app/schemas/`) with `to_camel` alias generator so JSON keys match frontend conventions.
- Cache keys in Redis must follow strict scoped formatting:
  `stats:tenant:{tenant_id}:sub:{sub_tenant_id}:{resource}`
- Authentication must resolve active context via `get_current_tenant` and `get_current_sub_tenant` dependencies from `X-Tenant-ID` and `X-Sub-Tenant-ID` headers.

### 3.2 Frontend Architecture (Angular 22 Standalone)
- Root: `frontend/urban-console/src/app/`
- Framework: **Angular 22.2 Standalone Components** (no obsolete NgModules).
- State: Use Angular **Signals** (`signal()`, `computed()`, `effect()`) for reactive state.
- Styling: Custom SCSS adhering to [docs/TYPOGRAPHY_AND_DESIGN_SYSTEM.md](file:///Users/sagarsingharoy/Documents/urban/docs/TYPOGRAPHY_AND_DESIGN_SYSTEM.md). Do NOT introduce TailwindCSS.
- API Services: Must pass `Authorization: Bearer <token>`, `X-Tenant-ID`, and `X-Sub-Tenant-ID` headers on every call.

---

## 4. Pre-Push Validation Enforced
A Git pre-push hook (`.git/hooks/pre-push` and `scripts/validate_structures.sh`) is active. Pushes will be rejected automatically if:
- Backend code fails Python compilation or deviates from the `app/api/v1/`, `app/core/`, `app/db/`, `app/schemas/` structure.
- Frontend code fails `ng build` or introduces broken imports / missing models.
