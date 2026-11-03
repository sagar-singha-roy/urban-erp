# Engineering Playbook

How modules are built in this repository, for people and AI agents alike. `AGENTS.md` holds the rules; this file shows how to apply them, with the files to copy from.

The reference modules are recent and complete. When unsure, copy them:

| Module | Backend | Frontend |
|---|---|---|
| ADM-T04 White-labelling | `app/api/v1/white_label.py`, `white_label_domains.py`, `core/white_label_rules.py` | `modules/admin/tenants/white-label/` |
| ADM-S04 Quotas | `app/api/v1/quotas.py`, `quota_alerts.py`, `core/quota_rules.py`, `quota_worker.py` | `modules/admin/modules/quota-usage/` |
| ADM-R02 Cross-tenant access | `app/api/v1/cross_tenant_access.py`, `cross_tenant_reviews.py`, `core/cross_tenant_*.py` | `modules/admin/iam/cross-tenant-access/` |
| ADM-R04 Support impersonation | `app/api/v1/impersonation*.py`, `core/impersonation*.py` | `modules/admin/iam/support-impersonation/`, `shared/components/support-session-banner/` |

Backend paths are under `backend/services/core_service/`. Frontend paths are under `frontend/urban-console/src/app/`.

---

## 1. Working agreement

1. **Plan before code for any new module.** Restate the spec, read the code it touches, and list the patterns you will copy. Say what exists, what is missing, the decisions you made, and the risks. Wait for approval.
2. **Decide, then say so.** Where the spec is open, pick the safer option and write it down as a decision the owner can overrule. Do not leave it as a question.
3. **Enforce, do not just record.** A permission screen that stores rules nobody checks is worse than none. If something is only stored, say so in the UI and in `docs/SECURITY.md`.
4. **Work on the branch you are told to use.** Do not create branches, commit or push unless asked.
5. **Before a commit:** run `./scripts/bump_version.sh [patch|minor|major]`, then `./scripts/validate_structures.sh`. Commit messages follow the history: `feat(scope): add <thing>, ADM-XXX (v1.9.0, build 117)`.
6. **Report what is true.** Say what was tested and how, what failed, and what is not done. Never call something verified that was not run.

---

## 2. Backend module recipe

### 2.1 Files

| File | Holds |
|---|---|
| `app/core/<module>_rules.py` | Option lists, constants and pure functions. No database, no FastAPI. Easy to unit test. |
| `app/core/<module>.py` | Enforcement or services that need the database or the request. |
| `app/core/<module>_worker.py` | A background loop (`TICK_SECONDS`, `run_once()`, `<module>_loop()`), started and cancelled in `main.py` lifespan. |
| `app/schemas/<module>.py` | Request and response models. All inherit `CamelModel`. |
| `app/api/v1/<module>.py` | Routes. Split into two routers when a file passes about 400 lines (see `cross_tenant_access.py` and `cross_tenant_reviews.py`). |
| `app/db/models.py` | New tables appended at the end, each with a one-line docstring. |
| `migrations/versions/NNNN_<name>.py` | `TABLES = [...]`, `create_all` up, `drop_all(reversed)` down. Chain `down_revision` to the latest. |
| `tests/test_<module>.py` | Unit tests (section 5). |

Register routers in `app/main.py`. A new path prefix under `/api/v1` reaches core through the gateway's default. Only module services need an entry in `gateway/gateway.conf`.

### 2.2 Routes

- **Guard the whole router.** Use `APIRouter(prefix=..., dependencies=[Depends(require_roles(["super_admin"]))])`, and repeat it per route when you need the user: `user: dict = SUPER_ADMIN`.
- **Listings** take `search`, `skip` and `limit` and return `PagedResponse(data=[...], total=...)`. Count with `select(func.count(...)).where(*conditions)`, then `.order_by(...).offset(skip).limit(limit)`.
- **Single results** return `ApiResponse(data=...)`.
- **An `/options` endpoint** returns every dropdown list from the rules file, so the frontend never hardcodes choices.
- **Lookups** return at most `LOOKUP_LIMIT = 50` rows and take `search`.
- **Errors** are `HTTPException` with a sentence the user can act on. Examples: `"Select an active user."`, `"The policy allows at most 15 minutes."`. Use 400 for bad input, 403 for not allowed, 404 for not found, and 409 for a state conflict.

### 2.3 Validation

- **Field shape** belongs in the schema. Use `Field(min_length=..., max_length=...)` and `model_validator(mode="after")` for rules across fields. Messages are plain sentences.
- **Rules that need the database** go in a `_check_<thing>(db, payload, ...)` helper in the route file. Examples: the target belongs to this state, the role exists, two policies do not overlap.
- **Datetimes are stored as naive UTC.** Convert incoming values with the `_naive()` helper in each schema file.

### 2.4 Data and IDs

- **Human-readable record numbers** come from a PostgreSQL `Sequence` column plus a formatter in the rules file, for example `XTA-000001`, `IMP-000001` and `IMP-POL-001`. Search accepts the formatted number.
- **Sequence values after insert:** `await db.flush()`, then `await db.refresh(row, ["<sequence_column>"])`.
- **Relationships on new objects:** set them when constructing, for example `targets=[], scope=None`. Async code cannot lazy-load.
- **Copy the rules a request was approved under.** When a request is approved under a policy, store a copy of the policy on the request (`policy_snapshot`), so later policy edits cannot change it.

### 2.5 Tenancy and row-level security

- **Municipal tables** carry `tenant_id` and are added to `RLS_TABLES` in `app/db/rls.py`.
- **Platform tables** that only super admins manage, or that sign-in reads before a tenant exists (IAM grants, impersonation), carry no row-level security. Write a comment above them saying why.
- **Check the tenant on the server.** Use `ensure_tenant_access` / `require_tenant`. Never trust a tenant ID from the body without it.
- **No hardcoded states, ULBs, wards, departments, roles or providers.** Read them from tables.

### 2.6 Audit

- **Every change to access, money or configuration** writes a row people can read (a history table or `TenantAuditLog` via `add_audit`). It also writes a hash-chained event via `record_immutable_audit_event`, with actor, IP (`client_ip(request)`), reason and reference.
- **Exports** are CSV, capped by `EXPORT_LIMIT`. Every cell passes through `safe_cell`, so spreadsheets cannot run it as a formula.

### 2.7 Approvals and other people's actions

- **Compare people by email**, lower-cased (`actor_of(user)`), never by display name.
- **Segregation of duties.** The requester cannot approve. A rule's author cannot review it. A second approver is named and must be a third person. Only the named owner decides on a campaign item.
- **Status changes that widen access** (editing an approved grant) send it back for approval.

---

## 3. Authentication and enforcement

All of this lives in `app/core/auth.py`. Read it before touching access.

- **`get_current_user`** authenticates from the Bearer header or the `urban_session` cookie. It re-reads the account, role, cross-tenant grants and support session from the database on every request. Revocation therefore works without signing out. Keep it that way.
- **Cookie requests** that change state must carry `X-Requested-With` (CSRF).
- **`require_permission(component, action)`** is the component check (`PTX-P10:APPROVE`). It is a dependency, used as `Depends(require_permission(...))`. Module services reach it through `POST /auth/authorize`, which forwards the caller's cookies and tenant headers.
- **A rule that changes what a request may do** goes in this path, and both `get_current_user` and `require_permission` need tests.
- **Special tokens carry a `typ` claim.** Ordinary sign-in refuses any token with a `typ` (see `impersonation_rules.TOKEN_TYPE`).
- **Module services** get session rules (masking, downloads) from the authorize answer. `urban_common.impersonation.SupportSessionGuard` applies them, so all 19 services behave the same.

---

## 4. Frontend module recipe

### 4.1 Files

```
modules/admin/<area>/<feature>/
├── <feature>.component.ts      # shell: header, tabs-bar, options + reference data, @switch on the active tab
├── <feature>.component.scss    # page wrapper, header, tabs (copy from quota-usage)
├── <feature>-utils.ts          # small pure helpers, if needed
├── hub.scss or tabs/tab.scss   # one shared stylesheet: @use '.../shared/styles/admin-table'
├── tabs/                       # one component per tab, each extends PagedTab<T>
├── dialogs/                    # one component per add/edit/decision form
└── shared/                     # pickers used by several dialogs
core/models/<feature>.model.ts  # interfaces mirroring the CamelModel JSON
core/services/<feature>.service.ts
```

Register the page in three places:
- `core/models/super-admin.model.ts`, as a sidebar item
- `modules/admin/admin-dashboard.component.ts`, in `subMap` and `imports`
- `admin-dashboard.component.html`, in an `@if (activeItemId() === '...')` block

Pages that non-super-admins must reach also get a route in `app.routes.ts` with `authGuard`.

### 4.2 Building blocks to reuse

| Need | Use |
|---|---|
| Table with search and paging | `extends PagedTab<T>` (`shared/components/paged-tab/paged-tab.ts`), implement `fetch(query)`, use `items()`, `total()`, `search()`, `onSearch`, `onPage`, `onLimit` |
| Pagination bar | `<app-wl-pagination>` |
| Multi-select | `<app-check-list [options] [value] (valueChange)>` |
| Styles | classes from `shared/styles/_admin-table.scss`: `wl-toolbar`, `wl-search`, `wl-card`, `wl-scroll`, `wl-table`, `wl-status good/warn/bad`, `wl-link`, `wl-notice`, `dialog-overlay`, `dialog-card`, `dialog-header`, `dialog-form`, `dialog-body`, `field`, `field wide`, `hint`, `required`, `toggle`, `dialog-footer`, `btn btn-primary/btn-outline` |
| Errors | `this.dialogs.showToast(apiError(err, 'Could not save this.'), 'error', 5000)` |
| Confirm | `await this.dialogs.confirm({ title, message, confirmText })` |
| Dates | API dates are naive UTC: display `asUtc(v) \| date`, inputs use `toLocalInput` / `fromLocalInput` (`cross-tenant-utils.ts`) |
| Tenants | `WhiteLabelService.getTenants()`, filtered by `tenantLevel` and `stateTenantId` |

### 4.3 Conventions

- **Components:** standalone, signals for state, and `input()` / `input.required()` in tabs. Dialogs use `@Input` with `saved` and `closed` `EventEmitter`s, and are opened with `@if (editing() !== undefined)`.
- **Services** use `environment.apiUrl` and never set auth or tenant headers. `auth-header.interceptor.ts` adds them and sends cookies (`withCredentials`).
- **Mobile first:** base styles for 375px, `min-width` queries only. Controls are at least 44×44px, tables scroll inside `.wl-scroll`, and the page never scrolls sideways.
- **Accessibility:**
  - dialogs have `role="dialog" aria-modal="true" aria-labelledby`
  - every input has a `<label for>` or `aria-label`
  - icon-only buttons have `aria-label`
- **Page titles** carry the tenancy level as a tooltip (`data-tooltip` and `title`), never as a visible pill.
- **Errors leave lists empty.** A failed load does not fill in example data.

---

## 5. Testing

### 5.1 Unit tests

Python tests use `unittest`. Each file sets its environment before importing the app:

```python
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key"
os.environ["AUDIT_SIGNING_KEY"] = "test-only-audit-key"
```

Run them the way the validator does:

```bash
cd backend/services/core_service && ENVIRONMENT=test JWT_SECRET_KEY=hook-only AUDIT_SIGNING_KEY=hook-only .venv/bin/python -m unittest discover -s tests
```

Cover:
- the pure rules
- every schema refusal
- enforcement, using `patch.object(auth, "_tenant_identifiers", ...)` and fake `AsyncReadSessionLocal` sessions
- middleware, via a small `FastAPI()` app and `TestClient`

`tests/test_access_control.py` already checks that every route refuses anonymous callers. It also checks that routes under its `SUPER_ADMIN_PREFIXES` refuse other roles, so add a new admin prefix there.

Shared library tests live in `backend/libs/urban_common/tests`.

### 5.2 Live check

For anything touching access, also run a live check against the running API before reporting it done. Keep the script in a scratch folder, not the repository. It:
1. inserts temporary users with a random tag
2. mints tokens with the local development signing key
3. walks every allowed and refused path
4. deletes everything it created in a `finally` block

Audit vault events stay, because the vault is append-only.

### 5.3 Browser check

Check the page at 1440px and at 375px. Confirm that the page does not scroll sideways and that no control is under 44px. Remove any test sign-in afterwards.

---

## 6. Writing style

- **Code comments say why**, not what. One line where possible.
- **Messages users read** are short, plain sentences that say what to do: `"Choose a decision."`, `"Without child tenants, select the ULBs this access covers."`. No jargon, no exclamation marks, no emoji.
- **Names** follow the domain (`grant`, `scope`, `session`, `policy`). Constants are named: `LOOKUP_LIMIT`, `EXPORT_LIMIT`, `TICK_SECONDS`.
- **Match the surrounding file** in naming, comment density and layout.
- **Docs:**
  - each module adds a short section to `docs/SECURITY.md`, covering what is enforced and the known gaps
  - each module updates its line in `docs/PHASE.md`
  - `README.md` changes when setup changes

---

## 7. Security checklist for every module

- [ ] Router guarded, and the role checked again on routes that need it.
- [ ] Tenant checked on the server for every tenant ID in the request.
- [ ] No hardcoded tenants, roles, providers, URLs or secrets.
- [ ] The person who asks is not the person who approves.
- [ ] Access changes take effect on the next request, not the next sign-in.
- [ ] Changes recorded in a readable history and in the audit vault.
- [ ] Exports escaped with `safe_cell` and capped.
- [ ] Gaps written in `docs/SECURITY.md` and shown in the UI where a user could assume otherwise.
