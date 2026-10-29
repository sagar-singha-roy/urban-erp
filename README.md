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
| **Caching** | **Redis 7** | Sub-millisecond caching for KPI metrics, ward boundaries, and session tokens |
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

## Repository Structure

```
urban/
├── docker-compose.yml               # Orchestrates Postgres, Redis, Keycloak, FastAPI, and Angular
├── .gitignore                       # Git ignore rules for Python, Angular, Node, and Docker
├── README.md                        # Documentation & setup guide
├── docker/
│   └── keycloak/
│       └── realm-export.json        # Pre-configured 'urban' realm, clients, and roles
├── backend/
│   └── services/
│       └── core_service/            # FastAPI microservice
│           ├── app/
│           │   ├── api/v1/          # Endpoints: /auth, /properties, /boundaries
│           │   ├── core/            # Config, security, JWT tokens, Redis client
│           │   ├── db/              # SQLAlchemy models, sessions, and seed data
│           │   └── schemas/         # Pydantic validation schemas
│           ├── Dockerfile
│           └── requirements.txt
└── frontend/
    └── urban-console/               # Angular 22 standalone SPA
        ├── src/app/
        │   ├── core/                # Keycloak OIDC service, property service, models
        │   ├── shared/
        │   │   └── components/
        │   │       ├── app-switcher/# Gmail-style 9-dot waffle module launcher
        │   │       └── icon/        # Custom vector SVG icons for all 19 modules
        │   └── modules/
        │       ├── auth/            # Sign In & Sign Up with demo profile chips
        │       └── dashboard/       # ULPIN property registry, KPIs, hierarchy drawer
        ├── Dockerfile
        └── nginx.conf
```

---

## Quick Start with Docker Compose

Run the entire ecosystem with one command:

```bash
docker-compose up -d --build
```

### Service Endpoints

- **Urban Console (Angular 22)**: [http://localhost:4200](http://localhost:4200)
- **FastAPI Core API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Keycloak IAM Admin Console**: [http://localhost:8080](http://localhost:8080) (`admin` / `admin`)
- **PostgreSQL Database**: `localhost:5432` (`urban_admin` / `urban_password123`)
- **Redis Cache**: `localhost:6379`

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
- **Tenant-Scoped Caching**: Redis cache keys partitioned as `stats:summary:{tenant_id}` and `boundaries:wards:{tenant_id}`.
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
uvicorn app.main:app --reload --port 8000
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
