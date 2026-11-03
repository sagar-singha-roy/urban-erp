# Urban Integrated Municipal ERP — Code Style & Structural Standards

The rules in short. For how to build a module step by step, with files to copy from, see [ENGINEERING_PLAYBOOK.md](ENGINEERING_PLAYBOOK.md).

---

## 1. Backend Standards (Python 3.12 / FastAPI)

- **Directory Boundary**: `backend/services/core_service/app/`
  - `api/v1/`: Controllers and endpoints only.
  - `core/`: Auth, config, Valkey, security, and per-module `<module>_rules.py`, `<module>.py` and `<module>_worker.py`.
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
- **Mandatory Search & Pagination (Limit & Skip)**:
  - Every listing endpoint MUST accept `search: Optional[str] = Query(None)`, `skip: int = Query(0, ge=0)`, and `limit: int = Query(50, ge=1, le=100)`.
  - Queries must filter by search term across key textual fields and execute `.offset(skip).limit(limit)`, returning `PagedResponse(data, total)`.
- **Permissions**: `Depends(require_permission("PTX-P10", "APPROVE"))`; platform routers use `require_roles(["super_admin"])`.
- **Errors**: `HTTPException` with a plain sentence the user can act on.
- **Comments**: say why, not what. One line where possible.

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
  - **Styling**: Vanilla SCSS using variables defined in [TYPOGRAPHY_AND_DESIGN_SYSTEM.md](TYPOGRAPHY_AND_DESIGN_SYSTEM.md); admin tables and dialogs reuse `shared/styles/_admin-table.scss`. **Do NOT install TailwindCSS.**
  - **HTTP Headers**: The session is an httpOnly cookie. `auth-header.interceptor.ts` adds `X-Tenant-ID`, `X-Sub-Tenant-ID` and the CSRF header to every call; services do not set them.
  - **Search & Pagination Controls**: Every component table listing data MUST implement an interactive search filter input and the standard pagination controls bar with limit picker (`[5, 10, 20, 50]`), computed skip offset, previous/next navigation, and "Showing X to Y of Z entries".

### 2.1 Mobile-First Architecture & Responsive Standard (Mandatory Skill)
All frontend development across SUVIDHA must strictly obey a **Mobile-First Responsive Architecture**:
1. **Base-First Mobile Breakpoint**: Default SCSS must target compact mobile viewports (`375px - 767px`) first without media queries. Progressive enhancement to tablet (`@media (min-width: 768px)`) and workstation desktop (`@media (min-width: 1024px)`, `@media (min-width: 1440px)`) must occur using `min-width` queries only. Never use `max-width` desktop-down degradation.
2. **Ergonomic Touch Targets**: All interactive controls (buttons, nav links, icon actions, pills) must maintain minimum 44x44px touch target bounds on touch viewports.
3. **Adaptive Navigation Drawer**: Side navigation must collapse to a slide-over drawer or compact icon rail on viewports <1024px, and support minimized icon-only state with accessible tooltips on desktop.
4. **Fluid Flex & Grid Layouts**: Prevent horizontal overflow. All grids must declare `grid-template-columns: repeat(auto-fit, minmax(..., 1fr))` or flex with `min-width: 0; flex-wrap: wrap;`.
5. **Field Inspector Optimization**: High-contrast, sunlight-readable color palettes and dense single-column card layouts for municipal field inspectors.

---

## 3. Pre-Push Structural Verification

Run the automated structural integrity check before pushing:
```bash
./scripts/validate_structures.sh
```
Pushes are blocked by `.githooks/pre-push` (installed by `./scripts/install_hooks.sh`) if compilation, the Angular build or any unit test fails.
