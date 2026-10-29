# Rule: Pre-Push Structural Validation & Code Quality Guard

## Purpose
Enforces that changes committed to git cannot be pushed if:
1. Backend directory structure deviates from established architecture (`app/api/v1`, `app/core`, `app/db`, `app/schemas`).
2. Python files contain syntax errors or invalid imports.
3. Frontend directory structure deviates from established architecture (`src/app/core/models`, `src/app/core/services`, `src/app/shared/components`).
4. Frontend Angular build fails (`ng build`).
5. Structural misalignment between backend CamelModels and frontend TypeScript interfaces occurs.

## Execution
Run manually at any time:
```bash
./scripts/validate_structures.sh
```

Automatically triggered on `git push` via `.git/hooks/pre-push`.
If any test fails, `git push` terminates immediately with exit code `1`.
