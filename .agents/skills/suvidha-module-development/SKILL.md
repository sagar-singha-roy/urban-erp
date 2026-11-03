---
name: suvidha-module-development
description: Builds a complete SUVIDHA platform module (an ADM-* feature or a municipal module screen) end to end. Covers planning, the FastAPI backend with enforcement, audit and migrations, the Angular console with tabs and dialogs, tests, a live check and docs. Use whenever a spec for a new module or a large change to one arrives.
---

# SUVIDHA Module Development Skill

The full guide is [docs/ENGINEERING_PLAYBOOK.md](../../../docs/ENGINEERING_PLAYBOOK.md). This skill is the order of work.

## 1. Plan (wait for approval)
1. Restate the spec as tabs and fields.
2. Read the code it touches: `app/core/auth.py`, the nearest reference module, and any table it reads.
3. Write the plan:
   - what exists and the gap
   - decisions you made, numbered so the owner can overrule one
   - phases: data, enforcement, API, console, tests, docs
   - risks and complexity
4. Stop and wait for "proceed".

## 2. Backend (`backend/services/core_service/app/`)
1. **`core/<module>_rules.py`:** option lists, statuses, pure checks and number formatters.
2. **`db/models.py`:**
   - append tables with docstrings
   - add a `Sequence` for readable IDs
   - add the migration `migrations/versions/NNNN_<name>.py`
   - add municipal tables to `RLS_TABLES`
3. **Enforcement:** if the module changes what a request may do, wire it into `core/auth.py` (`get_current_user`, `require_permission`, and `/auth/authorize` for module services). Read state from the database per request.
4. **`schemas/<module>.py`:** `CamelModel` classes, with validators that give plain-sentence errors.
5. **`api/v1/<module>.py`:**
   - a guarded router
   - `/options`
   - lookups limited to 50 rows
   - paged listings with search, skip and limit
   - mutations that check the tenant, separate duties and write the audit history and the vault
6. **`main.py`:** register the routers, plus any worker or middleware.

## 3. Console (`frontend/urban-console/src/app/`)
1. **`core/models/<module>.model.ts` and `core/services/<module>.service.ts`:** use `environment.apiUrl` and set no headers.
2. **`modules/admin/<area>/<module>/`:** a shell with `tabs/` (extend `PagedTab<T>`) and `dialogs/`, plus one stylesheet that `@use`s `shared/styles/_admin-table`.
3. **Register:** a sidebar item in `core/models/super-admin.model.ts`, the `subMap`, imports and template in `modules/admin/admin-dashboard.component.*`, and `app.routes.ts` if non-admins need it.
4. **Mobile first:** 44px controls, no sideways page scroll, labels on every input.

## 4. Verify
1. **Unit tests** in `tests/test_<module>.py`: rules, schema refusals, enforcement and middleware.
2. **Validator:** `./scripts/validate_structures.sh`.
3. **Live check** against the running API with temporary, tagged users. Try every allowed and refused path, then delete the data.
4. **Browser** at 1440px and 375px. Remove any test sign-in.

## 5. Document and report
1. Add a section to `docs/SECURITY.md` with what is enforced and the gaps. Update the line in `docs/PHASE.md`, and `README.md` if setup changed.
2. Report what was built, what was verified and how, what is not enforced, and what is uncommitted. Do not commit unless asked.
