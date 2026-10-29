# Urban Integrated Municipal ERP — Code Style & Structural Standards

---

## 1. Backend Standards (Python 3.12 / FastAPI)

- **Directory Boundary**: `backend/services/core_service/app/`
  - `api/v1/`: Controllers and endpoints only.
  - `core/`: Auth, config, redis, security utilities.
  - `db/`: SQLAlchemy declarative models, session factory, seed data.
  - `schemas/`: Pydantic models.
- **Naming & Serialization**:
  - Internal Python variables and attributes: `snake_case`.
  - Pydantic models must inherit from `CamelModel`:
    ```python
    class CamelModel(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    ```
  - External JSON output will automatically serialize in `camelCase` matching frontend expectations.
- **Multi-Tenant Queries**:
  - Always use `tenant_id: str = Depends(get_current_tenant)`.
  - Filter every query by `tenant_id` and, when relevant, `sub_tenant_id`.

---

## 2. Frontend Standards (Angular 22.2 Standalone)

- **Directory Boundary**: `frontend/urban-console/src/app/`
  - `core/models/`: TypeScript interfaces corresponding to backend `CamelModel` schemas.
  - `core/services/`: Injectable singleton HTTP and state services.
  - `shared/components/`: Reusable standalone components (icons, app switcher, modal dialogs).
  - `modules/`: Feature views (dashboard, auth, property registry).
- **Framework Conventions**:
  - **Standalone Only**: Never create or import `NgModule`.
  - **Reactivity**: Use Angular **Signals** (`signal()`, `computed()`, `effect()`) for reactive state.
  - **Styling**: Vanilla SCSS using variables defined in `DESIGN_SYSTEM.md`. **Do NOT install TailwindCSS.**
  - **HTTP Headers**: All API calls must include `Authorization: Bearer <token>`, `X-Tenant-ID`, and `X-Sub-Tenant-ID`.

---

## 3. Pre-Push Structural Verification

Run the automated structural integrity check before pushing:
```bash
./scripts/validate_structures.sh
```
Pushes are blocked by `.git/hooks/pre-push` if backend Python or frontend Angular compilation fails.
