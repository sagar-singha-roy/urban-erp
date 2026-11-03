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

## 3. Granular Component RBAC (415 Processes, super admin features excluded)

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

## Tenant domains and certificates (ADM-T04)

- A domain cannot activate until a DNS or HTTP check proves ownership. Verified domains are re-checked every 6 hours and suspended if the proof is gone. DNS outages never revoke a domain.
- A unique database index allows one verified owner per domain. A tenant also cannot take a parent of, or a host beneath, another tenant's domain.
- Pending claims hold nothing and expire after 7 days, so a name cannot be reserved by typing it in.
- Private keys are encrypted with `CERT_ENCRYPTION_KEY`. No response schema has a field for them. They are written unencrypted only to the gateway's private generated folder, with owner-only permissions, because NGINX needs them.
- Logo uploads are judged by their content, not their name. SVG is refused because it can carry scripts.
- Tenant Custom CSS cannot use `url()`, `@import`, escapes or HTML. It can still change how pages look, so only super admins may set it.
- HTTP verification refuses domains that resolve to private addresses.

## Quotas (ADM-S04)

- The tenant whose API limit applies comes from the signed token, so `X-Tenant-ID` cannot change it.
- Storage and SMS checks lock their allocation rows, so simultaneous requests cannot overshoot.
- SMS delivery reports have no signed-in user. They need an HMAC-SHA256 signature, and are refused until `SMS_WEBHOOK_SECRET` is set.
- The SMS ledger holds no phone numbers or message text.

## GIS data isolation (ADM-A04)

- Every ULB-specific query checks access first, and row-level security applies the same scope underneath.
- Geographic Scope is resolved on the server. Asking for a state or ULB outside the user's access returns 403, and saved workspaces are checked the same way.
- WFS responses are fetched by the server without following redirects, and cut to the ULB's boundary before storage.
- WMS images cannot be cut. The approved services list is the only control, so approving a service is a decision about whose data it holds.

## Cross-tenant access (ADM-R02)

- Access outside a user's home tenant comes only from an approved grant. Grants are read from the database on every request, so revoking or expiring one applies to tokens already issued.
- Approval needs the named approval authority, who must be a platform super admin other than the requester and the user. Changing approved access sends it back for approval.
- Read Only access refuses any change to the target tenant. Read/Write cannot approve or manage. An approved Deny rule or a scope restriction blocks the action whatever the user's role allows.
- A scope can only narrow a grant. With child tenants left out, a state grant reaches only the ULBs listed.
- Tenant, module and component limits are enforced. Department, zone and ward limits are stored and attached to the signed-in user, but no module filters by them yet.
- Grants apply to tokens this service issues. Keycloak tokens are not checked against them yet.
- Every change is written to the access history and, hash-chained, to the audit vault, with the caller's address as seen by the gateway.

## Support impersonation (ADM-R04)

- The agent never receives the target user's password or credentials. Starting an approved request issues a separate session token in its own httpOnly cookie, naming the agent as the actor.
- That token is only honoured next to the agent's own sign-in cookie, for the agent it names. On its own, as a Bearer token, or beside another person's sign-in it is refused.
- Every request checks the session row, so ending, terminating or expiring a session applies on the next request. The token also expires with the session.
- A session covers one tenant. It cannot reach account, IAM, hub or super-admin routes, and cannot change records in core_service. Module actions pass only if the mode allows them: Read Only allows viewing, Restricted Actions adds the component actions the policy lists.
- Super admins cannot be impersonated, and nobody can impersonate themselves. Approvers are super admins other than the requester; with dual approval the second approver is named and must be a third person.
- An approval must be used within its validity, at most 24 hours. Requests copy the policy, so editing a policy does not change an approved request.
- With masking on, JSON fields whose names contain email, mobile, phone, Aadhaar, PAN number, address, date of birth, bank account or IFSC are partly hidden, in core_service and in every module service. A sensitive field with another name is not masked.
- With downloads disabled, file responses and exports are refused.
- Each request in a recorded session is logged by method, path, permission asked and result. Request bodies are not stored. Requests, approvals, starts and ends are also written to the audit vault.
