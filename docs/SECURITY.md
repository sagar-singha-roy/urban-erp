# Urban Integrated Municipal ERP — Security Policy & Architecture

---

## 1. Authentication & Identity Management

- **Centralized IAM**: Keycloak 24 OpenID Connect (OIDC) / OAuth 2.0 with RS256 JWT tokens.
- **Unified Login**: All actors (Super Admin, State Officers, City Officers, Citizens) authenticate through `/login`.
- **JWT Claim Integrity**: Tokens contain cryptographically verified user claims, memberships (`tenants`, `sub_tenants`), and assigned component permissions.

---

## 2. Multi-Tenant Data Isolation Enforcement

Multi-tenant isolation is enforced at 3 separate architectural layers:

1. **Application Layer (FastAPI Dependencies)**:
   - Request context extracted via `get_current_tenant` and `get_current_sub_tenant`.
   - ORM queries explicitly append `.where(Model.tenant_id == tenant_id, Model.sub_tenant_id == sub_tenant_id)`.
2. **Database Layer (PostgreSQL Row-Level Security)**:
   - RLS policies configured on all municipal domain tables.
   - DB connection sets session variables `app.current_tenant_id` and `app.current_sub_tenant_id`.
3. **Cache Layer (Redis Key Scoping)**:
   - Cache keys prefixed by tenant hierarchy: `stats:tenant:{tenant_id}:sub:{sub_tenant_id}:{resource}`.

---

## 3. Granular Component RBAC (415 Processes)

- Permissions are evaluated at the component action level:
  `{MODULE_CODE}-{COMPONENT_CODE}:{ACTION}` (e.g. `PTX-P10:APPROVE`, `WTR-W12:RECORD`).
- Endpoints protected by `@require_component(module, component, action)`.
- Super Admin ("The Boss") possesses wildcard `*:*:*` rights for cross-tenant operations.

---

## 4. Audit Logging & Data Protection

- **Audit Trails**: Every state change (assessments, approvals, mutations, payment waivers) records:
  - `user_id`, `tenant_id`, `sub_tenant_id`, `timestamp`, `ip_address`, `before_state`, `after_state`.
- **Sensitive Citizen Data**:
  - Masked in UI outputs (Aadhaar/PAN last 4 digits only).
  - Passwords hashed using PBKDF2-HMAC-SHA256 (100,000 rounds) or Keycloak Argon2/bcrypt.
