# Urban Integrated Municipal ERP — Technical Architecture Document
## Multi-Tier SaaS, Cascading Subscriptions, Delegated Auth & Component RBAC

**Document Version**: 2.0  
**Stack**: Angular 22.2 (Frontend) · FastAPI / Python 3.12 (Backend) · PostgreSQL 16 + PostGIS · Keycloak 24 · Redis 7  
**Architecture Style**: Asynchronous Microservice Core with Multi-Tier Logical Sharding  

---

## 1. System Overview & Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                   FRONTEND: ANGULAR 22 STANDALONE SPA                  │
│  - Signal-based Reactive Stores (User, TenantScope, SubTenantScope)     │
│  - Unified Scope Switcher & Module Waffle App Launcher                 │
│  - Directive *hasComponentAccess="'PTX-P10'" for fine-grained UI flags │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS (Bearer JWT + X-Tenant-ID + X-Sub-Tenant-ID)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY / REVERSE PROXY                     │
│  - TLS Termination, Global Rate Limiting, CORS, Path Routing           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────────┐
│       CORE FASTAPI SERVICE          │   │      KEYCLOAK 24 IDENTITY (IAM)     │
│  - Request Context Middleware       │   │  - Centralized OIDC / SAML SSO      │
│  - Multi-Tier Scope Resolver        │◄──┤  - Hierarchical Groups & User Scopes│
│  - Subscription Guard Interceptor   │   │  - JWT Claim Injection Engine       │
│  - Component RBAC Engine            │   └─────────────────────────────────────┘
└──────────┬──────────────────────┬───┘
           │                      │
           ▼                      ▼
┌────────────────────┐  ┌───────────────────────────────────────────────┐
│   REDIS 7 CACHE    │  │       POSTGRESQL 16 + POSTGIS (SHARED DB)     │
│  - Scoped KPI Keys │  │  - Table Level Tenant & Sub-Tenant Scoping    │
│  - Token Blacklist │  │  - Row-Level Security (RLS) Policies          │
│  - Session States  │  │  - GIS Boundary & Spatial Polygon Indexing    │
└────────────────────┘  └───────────────────────────────────────────────┘
```

---

## 2. Multi-Tier Tenancy Implementation Pattern

### 2.1 Request Context Headers & Resolution Order
Every HTTP request initiated by authenticated clients passes two contextual scoping headers:
1. `X-Tenant-ID`: The State Identifier (e.g. `TG` for Telangana).
2. `X-Sub-Tenant-ID`: The City / ULB / Department Identifier (e.g. `GWMC`).

**Resolution Hierarchy**:
```
Incoming Request
      │
      ▼
Has X-Tenant-ID & X-Sub-Tenant-ID Header?
   ├── YES ──► Verify caller has granted membership in this Scope
   └── NO  ──► Extract default scope from JWT Claims (active_tenant, active_sub_tenant)
                  │
                  ▼
         Inject into AsyncLocalStorage / Request.state
```

### 2.2 JWT Token Payload Specification
```json
{
  "sub": "usr_998124_uuid",
  "preferred_username": "officer@gwmc.gov.in",
  "email": "officer@gwmc.gov.in",
  "name": "Ramesh Reddy",
  "is_super_admin": false,
  "tenants": [
    {
      "tenant_id": "TG",
      "tenant_name": "Telangana State",
      "role": "state_officer",
      "sub_tenants": [
        {
          "sub_tenant_id": "GWMC",
          "sub_tenant_name": "Greater Warangal Municipal Corp",
          "role": "revenue_officer",
          "allocated_modules": ["PTX", "WTR", "TRL", "UCH", "MPM", "FIN", "DMS"]
        }
      ]
    }
  ],
  "active_tenant": "TG",
  "active_sub_tenant": "GWMC",
  "component_permissions": {
    "PTX": ["PTX-P01:CREATE", "PTX-P05:APPROVE", "PTX-P21:COLLECT"],
    "WTR": ["WTR-W01:CREATE", "WTR-W12:RECORD"]
  }
}
```

---

## 3. Security & Access Control Pipelines

### 3.1 Module Subscription Guard (FastAPI Dependency)
Before executing any business logic in a module router, the framework validates the subscription cascade:
```python
async def verify_module_access(
    module_code: str,
    tenant_id: str = Depends(get_current_tenant),
    sub_tenant_id: Optional[str] = Depends(get_current_sub_tenant),
    db: AsyncSession = Depends(get_db)
):
    # 1. Check if State Tenant has subscribed to this module
    tenant_sub = await db.scalar(
        select(TenantSubscription).where(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.module_code == module_code,
            TenantSubscription.is_active == True
        )
    )
    if not tenant_sub:
        raise HTTPException(status_code=403, detail=f"Module '{module_code}' not subscribed by State '{tenant_id}'")

    # 2. If sub_tenant context present, verify allocation from State
    if sub_tenant_id:
        sub_sub = await db.scalar(
            select(SubTenantSubscription).where(
                SubTenantSubscription.sub_tenant_id == sub_tenant_id,
                SubTenantSubscription.module_code == module_code,
                SubTenantSubscription.is_active == True
            )
        )
        if not sub_sub:
            raise HTTPException(status_code=403, detail=f"Module '{module_code}' not allocated to City/Dept '{sub_tenant_id}'")
```

### 3.2 Granular Component RBAC Decorator
Protects individual API endpoints at the component action level:
```python
def require_component(module: str, component: str, action: str):
    async def permission_checker(user: dict = Depends(get_current_user)):
        if user.get("is_super_admin"):
            return user
        perms = user.get("component_permissions", {}).get(module, [])
        required = f"{component}:{action}"
        if required not in perms and f"{component}:ALL" not in perms:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Missing required component permission: {required}"
            )
        return user
    return permission_checker
```

---

## 4. Database Partitioning & Row-Level Security (RLS)

All multi-tenant transactional and entity tables incorporate composite partition foreign keys:
```sql
ALTER TABLE property_parcels ENABLE ROW LEVEL SECURITY;

CREATE POLICY property_parcel_tenant_isolation ON property_parcels
    FOR ALL
    USING (
        current_setting('app.is_super_admin', true) = 'true'
        OR (
            tenant_id = current_setting('app.current_tenant_id', true)
            AND (
                sub_tenant_id = current_setting('app.current_sub_tenant_id', true)
                OR current_setting('app.current_sub_tenant_id', true) IS NULL
            )
        )
    );
```

---

## 5. Caching Strategy with Redis

Redis keys enforce strict namespacing to prevent cross-tenant cache contamination:
- **Global Super Admin Analytics**: `stats:global:cxo:summary` (TTL: 300s)
- **State Tenant Aggregate**: `stats:tenant:{tenant_id}:summary` (TTL: 180s)
- **Sub-Tenant Local KPI**: `stats:tenant:{tenant_id}:sub:{sub_tenant_id}:summary` (TTL: 180s)
- **Boundaries & Wards**: `boundaries:{tenant_id}:{sub_tenant_id}:wards` (TTL: 600s)

Cache invalidation triggers on mutation:
```python
async def invalidate_tenant_cache(tenant_id: str, sub_tenant_id: str):
    await redis_client.delete(f"stats:tenant:{tenant_id}:sub:{sub_tenant_id}:summary")
    await redis_client.delete(f"stats:tenant:{tenant_id}:summary")
    await redis_client.delete("stats:global:cxo:summary")
```

---

## 6. Frontend Architecture (Angular 22)

### 6.1 State Management with Signals
- `KeycloakAuthService.activeTenant`: Signal containing active State object.
- `KeycloakAuthService.activeSubTenant`: Signal containing active City/ULB object.
- `KeycloakAuthService.userEntitlements`: Signal containing accessible modules and components.

### 6.2 Component Authorization Directive
```html
<!-- Only rendered if active user role has BPM-B05 eDCR Scrutiny entitlement -->
<button *hasComponentAccess="'BPM-B05:APPROVE'" class="btn btn-primary" (click)="approvePlan()">
  Approve Architectural Plan
</button>
```
