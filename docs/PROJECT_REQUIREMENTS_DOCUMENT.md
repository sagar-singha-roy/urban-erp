# Urban Integrated Municipal ERP — Project Requirements Document (PRD)
## Multi-Tier SaaS, Cascading Subscriptions, Granular RBAC & Global Analytics

**Document Version**: 2.0  
**Status**: Approved Architecture Specification  
**Reference Deployment**: Greater Warangal Municipal Corporation (GWMC) & Greater Hyderabad Municipal Corporation (GHMC), Telangana  
**Target Platform**: National / Pan-State Municipal SaaS Platform  

---

## 1. Product Vision & Hierarchy Model

Urban Integrated Municipal ERP is designed as a **Multi-Tier Hierarchical SaaS Platform** capable of serving multiple States, Urban Local Bodies (Municipal Corporations, Municipalities, Nagar Panchayats), and specialized municipal departments from a unified, cloud-native deployment.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        LEVEL 0: "THE BOSS"                             │
│                  Platform Super Admin (Global Scope)                   │
│  - Cross-Tenant & Cross-Subtenant Visual Analytics & CXO Dashboard     │
│  - Full Provisioning Rights: States, Cities, Departments, System Users │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────────┐
│      LEVEL 1: TENANT (STATE A)      │   │      LEVEL 1: TENANT (STATE B)      │
│     e.g., Telangana State (TG)      │   │    e.g., Maharashtra State (MH)     │
│  - Subscribes to N of 19 Modules    │   │  - Subscribes to M of 19 Modules    │
│  - State-level User Management      │   │  - State-level User Management      │
│  - Sub-Tenant Provisioning & Alloc  │   │  - Sub-Tenant Provisioning & Alloc  │
└──────────────────┬──────────────────┘   └──────────────────┬──────────────────┘
                   │                                         │
     ┌─────────────┴─────────────┐             ┌─────────────┴─────────────┐
     ▼                           ▼             ▼                           ▼
┌──────────────┐          ┌──────────────┐ ┌──────────────┐          ┌──────────────┐
│ LEVEL 2:     │          │ LEVEL 2:     │ │ LEVEL 2:     │          │ LEVEL 2:     │
│ SUB-TENANT 1 │          │ SUB-TENANT 2 │ │ SUB-TENANT 1 │          │ SUB-TENANT 2 │
│ (GWMC City)  │          │ (GHMC City)  │ │ (BMC Mumbai) │          │ (NMMC Navi)  │
│ - Allocated  │          │ - Allocated  │ │ - Allocated  │          │ - Allocated  │
│   Modules    │          │   Modules    │ │   Modules    │          │   Modules    │
│ - Local Users│          │ - Local Users│ │ - Local Users│          │ - Local Users│
└──────────────┘          └──────────────┘ └──────────────┘          └──────────────┘
```

---

## 2. Core Functional Pillars

### 2.1 Multi-Tier Tenancy Structure
1. **Level 1 (Tenant = State)**:
   - Represents a sovereign state administrative body (e.g., Directorate of Municipal Administration - CDMA Telangana).
   - Holds billing, master contract, state-wide tax rules, and master module subscriptions.
2. **Level 2 (Sub-Tenant = City / ULB / Department)**:
   - Represents an operational entity: Municipal Corporation (e.g. GWMC, GHMC), Municipality, or standalone Municipal Department (e.g., Town Planning Authority, Water Board).
   - Operates strictly within the boundary and module scope authorized by its parent State Tenant.

### 2.2 Cascading Module Subscriptions (19 Modules)
- The platform defines **19 Official Modules** (Revenue, Engineering, Citizen Services, GIS, Operations).
- **Tenant Subscription**: A State Tenant can subscribe to any subset $S \subseteq \{1 \dots 19\}$ of the 19 platform modules.
- **Sub-Tenant Allocation**: A Sub-Tenant can only receive an allocation $A$ such that:
  $$A_{\text{sub-tenant}} \subseteq S_{\text{parent-tenant}}$$
- If a State Tenant revokes or unsubscribes from a module, that module is automatically disabled for all its child Sub-Tenants.

### 2.3 Delegated User Administration & RBAC Hierarchy
The system enforces strict multi-level delegation:

| Administrative Tier | Can Create / Manage Users For | Can Assign Roles In | Access Scope |
|---|---|---|---|
| **Level 0: Super Admin ("The Boss")** | • Super Admins<br>• Tenant Admins (State)<br>• Sub-Tenant Admins (City/Dept)<br>• End Users (All Levels) | All Roles across all 19 modules | Global (All Tenants & Sub-Tenants) |
| **Level 1: Tenant Admin (State Admin)** | • State-level Officers & Specialists<br>• Sub-Tenant Admins (City Mayors/Commissioners)<br>• Sub-Tenant Local Users | Roles within the State's Subscribed Modules | Parent State + All Child Sub-Tenants |
| **Level 2: Sub-Tenant Admin (City/Dept Admin)** | • City/Department Officers<br>• Inspectors, Bill Collectors, Citizens | Roles within the Sub-Tenant's Allocated Modules | Restricted strictly to own Sub-Tenant |

### 2.4 Granular RBAC & Component-Level Access Control
Access is not merely module-level; it is enforced down to the **Component / Process Level**:
- Each of the 19 modules consists of 12 to 33 granular functional components (total 405 components catalogued).
- Roles are configured with a set of `component_permissions`:
  - **Component Code**: e.g. `PTX-P01` (Property Registration), `PTX-P10` (General Rate Revision), `WTR-W12` (Spot Meter Billing), `BPM-B05` (eDCR Plan Scrutiny).
  - **Permissions Matrix**: `CAN_VIEW`, `CAN_CREATE`, `CAN_UPDATE`, `CAN_APPROVE`, `CAN_DELETE`.
- UI shell conditionally renders buttons, forms, drawer tabs, and menu items based on the user's component entitlements.
- Backend FastAPI endpoints enforce component permission verification via decorators:
  ```python
  @require_component_access(module="PTX", component="PTX-P10", action="APPROVE")
  ```

### 2.5 "The Boss" Global Visual Analytics Dashboard
Platform Super Admins have dedicated global visibility:
- **Macro Performance Metrics**: Aggregated property tax collection, water revenue, trade licences, and grievance SLA compliance across all States.
- **Comparative ULB Benchmarking**: Ranking of Sub-Tenants by collection efficiency, grievance turnaround time, and digitisation rate.
- **Financial Consolidation**: Double-entry accounting roll-up, municipal bond indicators, and 15th Finance Commission compliance monitoring.
- **Drill-Down Capability**: Ability to zoom in from National $\to$ State $\to$ City $\to$ Ward $\to$ ULPIN Parcel.

### 2.6 Unified Single Login & Dynamic Scope Switching
- **Universal Entry Point**: Single login portal for all users (`/login`).
- **Identity Resolution**: Upon valid authentication, the user identity token returns all associated Tenant and Sub-Tenant memberships.
- **Scope Selection**:
  - Single-membership users are redirected straight to their assigned workspace.
  - Multi-membership users (e.g. State Inspectors overseeing multiple cities, or Super Admin) receive a **Scope Selection Dialog** upon sign-in.
  - Active scope can be switched on-the-fly via the top navigation bar without logging out.

---

## 3. Non-Functional Requirements (NFRs)

1. **Security & Data Isolation**:
   - Multi-tenant data segregation must be provable: zero data leakage between Sub-Tenants.
   - Database queries must enforce `tenant_id` and `sub_tenant_id` at ORM and SQL filter levels.
2. **Auditability**:
   - Every state change (approvals, assessments, mutations, fee waivers) must log `user_id`, `tenant_id`, `sub_tenant_id`, timestamp, and previous/new values.
3. **Response Time**:
   - Authenticated API response time $\le 250\text{ ms}$ at 95th percentile.
   - Redis caching scoped by `{tenant_id}:{sub_tenant_id}`.
