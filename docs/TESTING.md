# Urban Integrated Municipal ERP — Testing & Quality Assurance Guide

---

## 1. Test Layers

| Layer | Framework | What it proves | Run |
|---|---|---|---|
| **Everything below, as the push hook runs it** | `scripts/validate_structures.sh` | Structure, compilation, build and all unit tests | `./scripts/validate_structures.sh` |
| **Core service** | Python `unittest` | Routes, schemas, rules, enforcement, tenant isolation | see 2.1 |
| **Shared library** | Python `unittest` | `urban_common`: authorization client, metering, support-session guard | see 2.2 |
| **Module services** | Python `unittest` | Each service starts and asks core about every request | run by the validator |
| **Frontend** | Angular CLI | Services, helpers and components | `cd frontend/urban-console && CI=true npx ng test --watch=false` |
| **Live check** | Script against the running API | Access rules work end to end on the real database | see section 4 |

---

## 2. Running Tests

### 2.1 Core service
Each test file sets `ENVIRONMENT`, `JWT_SECRET_KEY` and `AUDIT_SIGNING_KEY` before importing the app. Run the whole suite with the validator's settings:
```bash
cd backend/services/core_service && ENVIRONMENT=test JWT_SECRET_KEY=hook-only AUDIT_SIGNING_KEY=hook-only .venv/bin/python -m unittest discover -s tests
```
Run one file with `-m unittest tests.test_cross_tenant`.

### 2.2 Shared library
```bash
cd backend/libs/urban_common && ENVIRONMENT=test PYTHONPATH=. ../../services/core_service/.venv/bin/python -m unittest discover -s tests
```

---

## 3. What Every Module Tests

Put the tests in `tests/test_<module>.py`. Copy the style of `test_cross_tenant.py` and `test_impersonation.py`.

1. **Pure rules** in `core/<module>_rules.py`: each allowed and refused case.
2. **Schema refusals**: one `assertRaises(ValidationError)` per rule in the `CamelModel` validators.
3. **Enforcement**:
   - Call `auth` functions directly, with `patch.object(auth, "_tenant_identifiers", AsyncMock(...))` and a fake `AsyncReadSessionLocal`.
   - Prove the refused path as well as the allowed one.
   - Prove that revoking takes effect without signing in again.
4. **Middleware**: mount it on a small `FastAPI()` app and call it with `TestClient`.
5. **Route protection** comes free. `tests/test_access_control.py` calls every route anonymously and expects 401. For prefixes in its `SUPER_ADMIN_PREFIXES`, it also expects 403 from other roles, so add new admin prefixes there.

Tenant isolation itself is covered by `test_access_control.py` (`TenantScopeTests`) and the row-level security checks in `test_real_operations.py`.

---

## 4. Live Check Against the Running API

Unit tests mock the database. Changes to access or security also get a live check before they are reported done:

1. Start the API locally (see [SETUP_GUIDE.md](SETUP_GUIDE.md)) with test-only keys.
2. Write a script outside the repository. It inserts temporary users whose emails carry a random tag, and mints tokens with the local development signing key.
3. Walk every allowed and refused path, printing PASS or FAIL for each.
4. Delete everything the script created in a `finally` block. Audit vault events stay, because the vault is append-only.

Never use real accounts or real passwords for this.

---

## 5. Browser Check

For UI changes, open the page at 1440px and at 375px and confirm:
- the page never scrolls sideways
- every control is at least 44×44px
- dialogs fit on a phone
- empty states and errors read clearly

Remove any test sign-in afterwards.
