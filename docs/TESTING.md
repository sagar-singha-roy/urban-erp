# Urban Integrated Municipal ERP — Testing & Quality Assurance Guide

---

## 1. Testing Pyramid & Verification Layers

| Test Layer | Framework | Primary Objective | Run Command |
|---|---|---|---|
| **Structural & Build** | Custom Bash Validator | Directory invariants, Python compilation, Angular production build | `./scripts/validate_structures.sh` |
| **Backend Unit & Integration** | `pytest` + `pytest-asyncio` | FastAPI endpoint contracts, Pydantic serialization, business logic | `pytest backend/services/core_service` |
| **Multi-Tenant Leakage Tests** | `pytest` | Verifies zero cross-tenant data visibility between States & Cities | `pytest -m multi_tenant` |
| **Frontend Unit Tests** | Angular CLI / Jasmine | Signal state transitions, component rendering, HTTP headers | `npm test --prefix frontend/urban-console` |

---

## 2. Multi-Tenant Isolation Testing Strategy

Every endpoint must have tests proving tenant data cannot be accessed across boundaries:

```python
@pytest.mark.asyncio
async def test_tenant_data_isolation(async_client, auth_tokens):
    # 1. Fetch properties with GWMC tenant header
    gwmc_resp = await async_client.get(
        "/api/v1/properties",
        headers={"Authorization": f"Bearer {auth_tokens['gwmc_officer']}", "X-Tenant-ID": "GWMC"}
    )
    gwmc_ulpins = [p["ulpin"] for p in gwmc_resp.json()]
    assert all("GWMC" in u for u in gwmc_ulpins)

    # 2. Fetch properties with GHMC tenant header
    ghmc_resp = await async_client.get(
        "/api/v1/properties",
        headers={"Authorization": f"Bearer {auth_tokens['ghmc_officer']}", "X-Tenant-ID": "GHMC"}
    )
    ghmc_ulpins = [p["ulpin"] for p in ghmc_resp.json()]
    assert all("GHMC" in u for u in ghmc_ulpins)

    # 3. Prove disjoint sets (zero data leakage)
    assert set(gwmc_ulpins).isdisjoint(set(ghmc_ulpins))
```

---

## 3. Pre-Push Structural Verification (Mandatory Gate)

A git pre-push hook is active. It must pass before code can be pushed to remote:
```bash
./scripts/validate_structures.sh
```
Checks:
1. Backend directories: `app/api/v1`, `app/core`, `app/db`, `app/schemas`.
2. Python compilation: `python3 -m py_compile` across all files.
3. Frontend directories: `src/app/core/models`, `src/app/core/services`, `src/app/shared/components`.
4. Angular production build: `ng build` passes with 0 errors.
