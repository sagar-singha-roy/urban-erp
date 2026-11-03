# Urban Integrated Municipal ERP (GWMC Reference)

An enterprise-grade, multi-tenant municipal enterprise resource planning (ERP) platform designed for Urban Local Bodies (ULBs), with reference implementation for the **Greater Warangal Municipal Corporation (GWMC)**, Telangana.

---

## Tech Stack

| Layer | Technology | Key Responsibility |
|---|---|---|
| **Frontend** | **Angular 22.2** | Modern SPA with reactive signals, SVG icon design system, and multi-tenant UI shell |
| **Backend** | **Python (FastAPI)** | High-performance async microservices with Pydantic v2 validation |
| **SSO & IAM** | **Keycloak 24** | Centralized OIDC, RBAC, passkeys, and single sign-on across all 19 modules |
| **Database** | **PostgreSQL 16 + PostGIS** | Spatial GIS queries, ULPIN property hierarchy with Row-Level Security (RLS) |
| **Caching** | **Valkey 8** | Sub-millisecond caching for KPI metrics, ward boundaries, and session tokens |
| **Containers** | **Docker & Docker Compose** | Multi-container reproducible stack with healthchecks |

---

## 19 Integrated Modules & SSO App Launcher

Urban provides a unified Single Sign-On (SSO) session. Users switch between any authorized module via the **Gmail-style 9-dot Waffle App Launcher** located in the top navigation bar.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        URBAN MUNICIPAL APPS                            │
│  [::: Waffle Launcher]                                                 │
│                                                                        │
│   💰 [PTX] Property Tax         💧 [WTR] Water & Sewerage              │
│   📋 [GRV] Citizen Desk & RTI   📑 [FIN] Finance & Accounting          │
│   📁 [DMS] Document Management  🏪 [TRL] Trade Licences                │
│   🧾 [UCH] User Charges         🏛️ [BPM] Building Permissions          │
│   🗺️ [TPL] Town Planning        🚒 [FNC] Fire NOC Management           │
│   🚛 [SWM] Solid Waste (RFID)   🏗️ [ENG] Engineering Projects (e-MB)   │
│   💡 [SLM] Street Lights (CCMS) 🌳 [PRK] Parks & Horticulture          │
│   📦 [INV] Inventory & Stores   👥 [HRM] Payroll & Biometrics          │
│   🏢 [MPM] Municipal Property   ⚖️ [LGL] Legal Case Management (eCourts)│
│   🎯 [GSC] Government Schemes                                          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Contributing (people and AI agents)

Read [AGENTS.md](AGENTS.md) first, then [docs/ENGINEERING_PLAYBOOK.md](docs/ENGINEERING_PLAYBOOK.md). Run `./scripts/install_hooks.sh` once, and run `./scripts/validate_structures.sh` before pushing.

---

## Repository Structure

```
urban/
├── AGENTS.md                        # Rulebook for people and AI agents (copied to .agents/AGENTS.md)
├── CLAUDE.md, GEMINI.md             # Point those tools at AGENTS.md
├── .agents/                         # Agent rules, skills and project memory
├── .github/copilot-instructions.md  # Points Copilot at AGENTS.md
├── .githooks/                       # pre-push runs scripts/validate_structures.sh
├── docker-compose.yml               # Postgres + PostGIS, Valkey, Kafka, Keycloak, core and 19 module services, console, gateway
├── docs/
│   ├── ENGINEERING_PLAYBOOK.md      # How a module is built here, with files to copy from
│   ├── CODE_STYLE.md                # Coding rules in short
│   ├── TESTING.md                   # Test layers, commands and the live check
│   ├── SECURITY.md                  # What each module enforces, and known gaps
│   ├── PHASE.md                     # Delivery phases and ADM-* platform features
│   ├── SETUP_GUIDE.md               # Developer onboarding and setup
│   ├── TYPOGRAPHY_AND_DESIGN_SYSTEM.md # Design tokens and rules
│   ├── MODULE_COMPONENTS_CATALOGUE.md # 19 modules and 415 components (super admin features excluded)
│   ├── TECHNICAL_ARCHITECTURE_DOCUMENT.md
│   └── DATABASE_SCHEMA_DOCUMENT.md
├── gateway/                         # NGINX gateway: one API address, per-module path map
├── scripts/                         # validate_structures.sh, bump_version.sh, install_hooks.sh
├── backend/
│   ├── libs/urban_common/           # Shared code for module services: app factory, authorization, metering
│   └── services/
│       ├── core_service/            # Identity, tenancy and platform administration (FastAPI)
│       │   ├── app/
│       │   │   ├── api/v1/          # Routes
│       │   │   ├── core/            # Auth, config, Valkey, per-module rules, services and workers
│       │   │   ├── db/              # SQLAlchemy models, sessions, row-level security, seed data
│       │   │   └── schemas/         # Pydantic (CamelModel) schemas
│       │   ├── migrations/versions/ # Alembic migrations
│       │   └── tests/               # unittest suites
│       └── <code>_service/          # One service per municipal module (ptx, wtr, grv, ...)
└── frontend/
    └── urban-console/               # Angular 22 standalone console
        └── src/app/
            ├── core/                # Models, services, interceptors, guards
            ├── shared/              # Reusable components and styles (_admin-table.scss)
            └── modules/             # Feature pages, including admin/ for platform administration
```

---

## Quick Start with Docker Compose

Run the entire ecosystem with one command:

```bash
docker-compose up -d --build
```

### Service Endpoints

- **Urban Console (Angular 22)**: [http://localhost:4200](http://localhost:4200)
- **API gateway (NGINX, single API address)**: [http://localhost:8088](http://localhost:8088). Without Docker, run `nginx -p gateway -c nginx.local.conf` from the repository root.
- **FastAPI Core API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Keycloak IAM Admin Console**: [http://localhost:8080](http://localhost:8080) (`admin` / `admin`)
- **PostgreSQL Database**: `localhost:5432` (`urban_admin` / `urban_password123`)
- **Valkey cache**: `localhost:6379`

---

## Default SSO Demo Accounts

On the Sign In screen, click any of the 1-click quick login chips:

| Account / Role | Email / Username | Password | Module Access Scope |
|---|---|---|---|
| 👑 **Super Admin** | `admin@urban.gov.in` | `Admin@123` | **All 19 Modules** |
| 💰 **Revenue Officer (GWMC)** | `officer@gwmc.gov.in` | `Officer@123` | `PTX`, `WTR`, `TRL`, `UCH`, `MPM`, `FIN`, `DMS` |
| 💰 **Revenue Officer (GHMC)** | `officer@ghmc.gov.in` | `Officer@123` | `PTX`, `WTR`, `TRL`, `UCH`, `MPM`, `FIN`, `DMS` |
| 🗺️ **Town Planner** | `planner@gwmc.gov.in` | `Planner@123` | `BPM`, `TPL`, `FNC`, `DMS`, `LGL` |
| 👤 **Citizen User** | `citizen@gmail.com` | `Citizen@123` | `GRV`, `PTX`, `WTR`, `TRL`, `GSC`, `DMS` |

---

## Multi-Tenant SaaS Architecture

Urban ERP utilizes a **Pooled Multi-Tenant SaaS Architecture**:
- **Tenant Context Resolution**: Resolved per HTTP request via `X-Tenant-ID` header, token JWT claims (`tenant_id`), or fallback.
- **Strict Data Isolation**: Every database entity (`PropertyParcel`, `Building`, `PropertyUnit`, `Ward`, `Zone`, `Owner`) is scoped to `tenant_id`.
- **Tenant-Scoped Caching**: Valkey keys follow `stats:tenant:{tenant_id}:sub:{sub_tenant_id}:{resource}`.
- **Tenant Provisioning API**: `POST /api/v1/tenants` dynamically registers and bootstraps new Municipal Corporations (ULBs) with default zones and wards.
- **Dynamic Frontend ULB Switcher**: Instant switching between municipal tenants in the navigation bar with reactive UI reloading.


---

## Local Development Mode

### 1. Backend (FastAPI)
```bash
cd backend/services/core_service
# Activate virtual environment
source .venv/bin/activate
# Start development server
ENVIRONMENT=development uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (Angular 22)
```bash
cd frontend/urban-console
# Start Angular dev server
npm start
# Navigate to http://localhost:4200
```

---

## Core Data Architecture (ULPIN Spine)

All 19 municipal modules anchor to the core land and building hierarchy:
- **ULPIN** (`Unique Land Parcel Identification Number`)
  └── **Parcel** (`Survey Number`, `Plot Area`, `GIS Geometry`)
      └── **Building** (`Building Type`, `Floors`, `Permission No`)
          └── **Property Unit** (`PTIN`, `Carpet Area`, `Occupancy`, `Demand Status`)
              └── **Owners** (`Name`, `Mobile`, `Aadhaar Vault Ref`)

## White-labelling and custom domains (ADM-T04)

Super admins manage this under **Tenancy & Hierarchy > White-Labelling & Domain Management**.

Set these in `.env` before using it (see `.env.example`):

| Setting | Purpose |
|---|---|
| `CERT_ENCRYPTION_KEY` | Encrypts uploaded private keys. Uploads are refused without it |
| `PLATFORM_RESERVED_DOMAINS` | Domains tenants can never claim |
| `PLATFORM_CNAME_TARGET` | Hostname tenants point CNAME records at |
| `ACME_EMAIL` | Let's Encrypt account. The certificate manager stays idle without it |

Add each deployment's own hostname to `gateway/platform_hosts.conf`. The gateway refuses any other hostname unless an active domain mapping generated it.

A domain goes live in this order: claim it, publish the verification record, verify, activate, add a certificate, then create an active mapping. `core-service` writes the host configuration, and `gateway/start_gateway.sh` applies it only if `nginx -t` passes. If NGINX rejects it, the last working configuration stays, and the Domain Mapping tab shows the error.

## Quotas and usage (ADM-S04)

Super admins manage this under **Module & Subscription Management > Quota & Usage Management**.

| Resource | Enforced by | Figures come from |
|---|---|---|
| API requests | Valkey counters on every signed-in request, in core and through module services' authorization call | Each service's own request outcomes, saved each minute |
| Storage | `reserve_storage`, inside the transaction that stores the file | The `storage_objects` ledger |
| SMS credits | `consume_sms_credits`, before anything is sent | The `sms_messages` ledger and signed delivery reports |

Current limits of this version:

- **Storage:** only logos and emblems reach the ledger, because document storage is not built. Any new upload path must call `reserve_storage`. Providers other than Platform Database show as not connected.
- **SMS:** no provider is connected, so nothing is sent. Call `register_sms_provider` with an adapter, and set `SMS_WEBHOOK_SECRET` so reports can be sent to `POST /api/v1/public/quotas/sms/delivery-reports`, signed in `X-Urban-Signature` with HMAC-SHA256 of the body.
- **Email alerts:** the channel cannot be selected until `SMTP_HOST` and `SMTP_FROM` are set.
- **API limits:** each tenant has its own counters, so a state policy gives each of its ULBs that limit rather than one shared pool. API Category is stored but does not change what is limited. Super admins are exempt. Limits stop applying while Valkey is down.

## Spatial GIS viewer (ADM-A04)

Parcels, wards and zones are stored in PostGIS as EPSG:4326, with spatial indexes. Database triggers keep `geom` in step with parcel coordinates and `wards.boundary_geometry`, so every writer is covered.

- **Boundaries:** nothing is drawn at a level until boundaries exist. Import them under **City Layers > Import Boundaries**, matched to existing wards, zones or parcels. A ULB's outline is the union of its wards.
- **Remote layers:** a WMS or WFS layer must use an address on its ULB's approved services list. Addresses with a password or query, and hosts resolving to private addresses, are refused outside development.
- **WFS:** the **Sync** button copies a layer into PostGIS on the server, cut to the ULB's ward boundaries, so those must be imported first. The map reads only that copy. Sync is manual.
- **WMS:** images come straight from the service and cannot be cut to a ULB, so only approve services that hold that ULB's own data.
- **Map engine:** CesiumJS draws both the 2D map and the 3D globe, and needs WebGL. It does not use Cesium Ion.
- **CRS:** the 2D map is always Web Mercator. The chosen CRS sets the coordinates shown on click and the coordinates in exports. An import must be in its layer's declared CRS.
- **Limits:** a query returns at most 5,000 features. If a layer is cut off, moving the map fetches the area on screen.

## Cross-tenant access (ADM-R02)

Grants let a user reach tenants outside their home tenant. They are under **Global User Directory > Cross-Tenant Access**.

- **Approval:** a grant works only after its named approval authority approves it. The authority must be an active platform super admin with a user profile, other than the requester and the user. A fresh install has one super admin without a profile, so create a second one under **Global User Management** before requesting access.
- **Effect:** grants are checked on every request, so approving, revoking or expiring one applies straight away. Read Only grants refuse changes. Approved Deny rules and scope restrictions block actions whatever the role allows.
- **Departments:** department choices come from the `tenant_departments` table. Add them from the scope dialog.

## Support impersonation (ADM-R04)

Support staff can act as a user for a short, approved session without seeing their credentials. The hub is under **Global User Directory > Support Impersonation**, and at `/support/impersonation` for support roles.

- **Setup:** nobody can impersonate until a policy is active. Create one under **Impersonation Policy**, naming the support roles and tenant levels it covers. Each tenant level can have one active policy.
- **Approval:** approvers are platform super admins other than the requester. With dual approval, the first approver names a second, different super admin.
- **During a session:**
  - A red banner shows on every page with the time left and an **End session** button.
  - The session covers one tenant, and cannot reach account, admin or hub pages.
  - Personal fields are masked and downloads are blocked when the policy says so.
- **Audit:** each session is listed under **Audit Logs**, with the requests made in it.
