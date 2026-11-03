# Urban Integrated Municipal ERP — Agent & Developer Context
## Shared Context for AI Agents and Human Developers

Paths here are from the repository root. This file is the rulebook for everyone who changes this repository: people, and AI agents such as Claude, Codex, Gemini, Copilot and Cursor. `.agents/AGENTS.md` is a copy of it. Keep the two identical.

Read these next:
- `docs/ENGINEERING_PLAYBOOK.md`: how a module is built here, step by step, with the files to copy from.
- `docs/SECURITY.md`: what each module enforces and its known gaps.
- `.agents/rules/` and `.agents/skills/`: short rules and task guides for agents.

---

## 1. Project Domain & Hierarchy Vision

Urban (SUVIDHA) is a multi-tier SaaS municipal ERP for Urban Local Bodies (ULBs) and State Urban Development Departments.

1. **Level 0: Platform Super Admin.** Sees every state, city and department. Owns platform administration under `/admin`.
2. **Level 1: Tenant (State, e.g. `TG`, `MH`).** Subscribes to any subset of the 19 modules and provisions child tenants.
3. **Level 2: Sub-Tenant (City / ULB / Department, e.g. `GWMC`, `GHMC`).** Receives modules only from its state's subscriptions.

---

## 2. 19 Official Modules & Component RBAC

1. **Revenue & Billing:** `PTX`, `WTR`, `TRL`, `UCH`, `MPM`
2. **Finance & Administration:** `FIN`, `HRM`, `DMS`, `INV`
3. **Planning & Regulation:** `BPM`, `TPL`, `LGL`, `FNC`
4. **Infrastructure & Field Operations:** `SWM`, `ENG`, `SLM`, `PRK`
5. **Citizen Engagement & Welfare:** `GRV`, `GSC`

The 19 modules break down into 415 components, listed in `docs/MODULE_COMPONENTS_CATALOGUE.md`. That count excludes the super admin platform features: those use `ADM-*` codes, are listed in `docs/PHASE.md`, and are never counted in the 415. Permissions are checked per component action, for example `PTX-P10:APPROVE`.

Each module is its own service under `backend/services/<code>_service/`, built with `backend/libs/urban_common`. Module services hold no identity data and ask core about every request via `POST /api/v1/auth/authorize`.

---

## 3. Strict Coding Conventions & Architecture Boundaries

### 3.1 Backend (FastAPI + Async SQLAlchemy)
- **Root:** `backend/services/core_service/app/`.
  - `api/v1/` holds routes.
  - `core/` holds auth, rules, services and workers.
  - `db/` holds models, sessions and RLS.
  - `schemas/` holds Pydantic models.
- **Tenant filtering:** every query on municipal data filters by `tenant_id`, and by `sub_tenant_id` in city context. PostgreSQL row-level security (`app/db/rls.py`) applies the same scope underneath. Add new municipal tables to `RLS_TABLES`.
- **Schemas:** request and response models inherit `CamelModel`, so JSON keys are camelCase.
- **Cache keys** in Valkey follow `stats:tenant:{tenant_id}:sub:{sub_tenant_id}:{resource}`.
- **Tenant context** comes from `get_current_tenant` and `get_current_sub_tenant`, which read `X-Tenant-ID` and `X-Sub-Tenant-ID` and check them against the user's access.
- **Permissions** use `Depends(require_permission("PTX-P10", "APPROVE"))`. Platform routes guard the whole router with `require_roles(["super_admin"])`.
- **Live checks:** `get_current_user` re-reads the account, cross-tenant grants (ADM-R02) and support sessions (ADM-R04) on every request, so revoking access works without signing out. Do not cache these in the token.
- **Listings** support `search: Optional[str] = Query(None)`, `skip: int = Query(0, ge=0)` and `limit: int = Query(50, ge=1, le=100)`. They return `PagedResponse(data, total)` and run `.offset(skip).limit(limit)`.
- **Audit:** changes to access, money or configuration are written to a readable history and to the hash-chained audit vault (`record_immutable_audit_event`).

### 3.2 Frontend (Angular 22 Standalone)
- **Root:** `frontend/urban-console/src/app/`.
- **Framework:** standalone components only, with Signals (`signal()`, `computed()`, `effect()`) for state.
- **Styling:** custom SCSS per `docs/TYPOGRAPHY_AND_DESIGN_SYSTEM.md`. Admin tables and dialogs reuse `shared/styles/_admin-table.scss`. Do NOT introduce TailwindCSS.
- **Auth and headers:** the session is an httpOnly cookie. `core/interceptors/auth-header.interceptor.ts` adds `X-Tenant-ID`, `X-Sub-Tenant-ID` and the CSRF header to every call and sends cookies. Services never set these themselves.
- **Environment:** API and auth URLs come from `src/environments/environment.ts`, never string literals. The frontend has one API address, the NGINX gateway (`gateway/`); never add a per-service URL. A module's API paths are added to the map in `gateway/gateway.conf`.
- **Clean headings:** do NOT display raw tenancy text pills (e.g. 'Level 1') in page titles. Show tenancy as a tooltip (`data-tooltip` and `title`).
- **Modular dialogs:** never put a table and its add/edit form in one component. Pages are a shell plus `tabs/` and `dialogs/` folders. See section 4 of the playbook.
- **Search and pagination:** every table has a live search input and the standard pagination bar, with rows per page `[5, 10, 20, 50]`, `skip = (page - 1) * limit` and "Showing X to Y of Z entries". Extend `shared/components/paged-tab/paged-tab.ts` and use `<app-wl-pagination>`.
- **Zero hardcoding:** the platform deploys to many state and municipal governments. Hardcoding states, ULBs, zones, wards, departments, roles or identity providers is forbidden. Load them from APIs. Never use example fallback arrays in error handlers; leave the list empty and show a toast.

### 3.3 Mobile-First Responsive Standard (Mandatory)
1. **Base styles for phones (375px-767px) without media queries.** Enhance with `min-width` queries only (768px, 1024px, 1440px). Never `max-width`.
2. **Every interactive control is at least 44×44px.**
3. **Side navigation** collapses to a drawer or icon rail below 1024px.
4. **No horizontal page overflow.** Grids use `repeat(auto-fit, minmax(..., 1fr))`; flex rows use `min-width: 0; flex-wrap: wrap;`. Wide tables scroll inside their card.
5. **High-contrast, sunlight-readable layouts** for field inspectors.

---

## 4. Pre-Push Validation Enforced
Hooks live in `.githooks/`. Run `./scripts/install_hooks.sh` once per clone to set `core.hooksPath`.

The pre-push hook runs `scripts/validate_structures.sh`, which fails the push when:
- Backend code fails Python compilation, deviates from the `app/api/v1/`, `app/core/`, `app/db/`, `app/schemas/` structure, or fails the core-service, shared-library or module-service tests.
- Frontend code fails `ng build` or its unit tests.

Run it yourself before saying work is done:

```bash
./scripts/validate_structures.sh
```

---

## 5. Mandatory Version Bump Rule Before Every Commit
Before creating any git commit, update the application version and version code:
1. **Files:**
   - `frontend/urban-console/src/app/core/constants/version.ts`
   - `frontend/urban-console/package.json`
2. **Rules:**
   - `versionCode` goes up by 1 on every commit.
   - `version` follows semantic versioning: minor for features, patch for fixes.
   - `releaseDate` is the current month and year.
3. **Helper:** run `./scripts/bump_version.sh [patch|minor|major]` before staging.
4. **No bypass:** never create a commit or propose a commit message without checking the bump. No hook enforces this, so it is on you.

Commit messages follow the history: `feat(scope): add <thing>, ADM-XXX (vX.Y.Z, build N)`.

---

## 6. How AI Agents Work in This Repository
1. **Plan new modules before writing code.** Restate the spec, read the code it touches, name the patterns to copy, state your decisions and risks, then wait for approval.
2. **Work only on the branch you are given.** Do not create branches, commit or push unless the owner asks.
3. **Copy the reference modules** listed at the top of the playbook rather than inventing new patterns. Match the surrounding code's naming, comments and layout.
4. **Enforce what a screen promises.** If something is stored but not enforced, say so in the UI and in `docs/SECURITY.md`.
5. **Verify before reporting:**
   - run the validator
   - for access changes, run a live check against the running API with temporary data you then delete
   - for UI changes, check 1440px and 375px in a browser
6. **Report honestly.** State what was tested, what failed, and what is unfinished.
7. **Never handle real credentials.** Use test values for local checks, and never repeat a password seen in a screenshot or file.
8. **Update the docs with the code.** Each module adds its section to `docs/SECURITY.md`, its line to `docs/PHASE.md`, and to `README.md` when setup changes.
