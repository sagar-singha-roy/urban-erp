# Rule: Pre-Push Structural Validation & Code Quality Guard

## Purpose
A push is refused when any of these fails:
1. The backend structure (`app/api/v1`, `app/core`, `app/db`, `app/schemas`).
2. Python compilation.
3. The frontend structure (`src/app/core/models`, `src/app/core/services`, `src/app/shared/components`).
4. `ng build` and the frontend unit tests.
5. The core-service tests, the `urban_common` tests and every module service's tests.

## Execution
Run it yourself before reporting work as done:
```bash
./scripts/validate_structures.sh
```

The hook is `.githooks/pre-push`, which runs the same script. Run `./scripts/install_hooks.sh` once per clone so git uses `.githooks/`.

To run only the core-service tests, use the same settings the validator does:
```bash
cd backend/services/core_service && ENVIRONMENT=test JWT_SECRET_KEY=hook-only AUDIT_SIGNING_KEY=hook-only .venv/bin/python -m unittest discover -s tests
```

Never bypass the hook with `--no-verify`. Fix the failure instead.
