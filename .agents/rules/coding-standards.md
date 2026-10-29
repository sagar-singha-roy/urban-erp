# Rule: Backend & Frontend Coding Structure Consistency

## 1. Backend Invariants (`backend/services/core_service/app/`)

1. **Layer Separation**:
   - `api/v1/`: Controllers and HTTP route handlers only. No raw SQL or direct DB schema alters.
   - `core/`: Authentication, security, tenant resolution, configuration, and redis clients.
   - `db/`: SQLAlchemy declarative models (`models.py`), database session (`session.py`), and seeding (`seed.py`).
   - `schemas/`: Pydantic v2 schemas (`auth.py`, `property.py`, `tenant.py`, etc.).
2. **Naming & Serialization**:
   - All response and request schemas MUST inherit from `CamelModel` (`populate_by_name=True`, `alias_generator=to_camel`).
   - Backend Python attributes use `snake_case`; external JSON payloads use `camelCase`.
3. **Multi-Tier Tenant Isolation**:
   - Every router querying municipal entities MUST declare `tenant_id: str = Depends(get_current_tenant)` and where applicable `sub_tenant_id: Optional[str] = Depends(get_current_sub_tenant)`.
   - Never perform bare queries like `select(PropertyParcel)` without `.where(PropertyParcel.tenant_id == tenant_id)`.
4. **Caching Discipline**:
   - Cache keys must be scoped with tenant context: `prefix:{tenant_id}:{sub_tenant_id}`.

---

## 2. Frontend Invariants (`frontend/urban-console/src/app/`)

1. **Architecture & Framework**:
   - Angular 22 standalone components only. No `NgModule` modules.
   - State management MUST use Angular Signals (`signal<T>()`, `computed()`, `effect()`).
2. **Model Alignment**:
   - Every entity received from FastAPI must have a corresponding TypeScript interface in `src/app/core/models/` matching the camelCase fields of the backend `CamelModel`.
3. **Styling & Design System**:
   - Use custom SCSS with variables defined in `src/styles.scss` and `docs/TYPOGRAPHY_AND_DESIGN_SYSTEM.md`.
   - Do NOT introduce TailwindCSS or bootstrap utility bloat.
4. **Header Injection**:
   - All HTTP requests initiated through Angular services MUST inject `Authorization`, `X-Tenant-ID`, and `X-Sub-Tenant-ID` headers.
