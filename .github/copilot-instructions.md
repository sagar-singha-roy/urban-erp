# Instructions for GitHub Copilot

Follow [AGENTS.md](../AGENTS.md). It is the single rulebook for every agent in this repository.

Then read:
- [docs/ENGINEERING_PLAYBOOK.md](../docs/ENGINEERING_PLAYBOOK.md) for how modules are built here
- [.agents/rules/](../.agents/rules/) for the short rules

The rules that matter most when suggesting code:
- **Backend:**
  - schemas inherit `CamelModel`
  - listings take `search`, `skip` and `limit` and return `PagedResponse`
  - permissions use `Depends(require_permission("PTX-P10", "APPROVE"))`
  - municipal queries filter by `tenant_id`
- **Frontend:**
  - standalone components and signals
  - API URLs come from `environment.apiUrl`
  - services never set auth or tenant headers
  - tables extend `PagedTab<T>`
  - forms live in `dialogs/`
- **Never hardcode** states, ULBs, wards, departments, roles or identity providers.
