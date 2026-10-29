# Urban Integrated Municipal ERP — Developer & System Setup Guide

This document provides a clean, step-by-step onboarding guide for developers, system administrators, and DevOps engineers setting up the **Urban Integrated Municipal ERP** platform locally or on a cloud server.

---

## 1. System Architecture & Prerequisites

The Urban ERP platform is composed of:
1. **Frontend Console (`urban-console`)**: Angular 22.2 Standalone + Signals + Vanilla SCSS adhering to Hake Technologies design tokens (`#0E3A52`, `#1B8C77`, `#D98A2B`).
2. **Backend Core Service (`core-service`)**: FastAPI + Async SQLAlchemy + Asyncpg with dual-engine read/write replication split.
3. **Database Layer (`urban-postgres`)**: PostgreSQL 16.3 with PostGIS 3.4 extensions for cadastral GIS mapping.
4. **Cache & Scoped Session Store (`urban-redis`)**: Redis 7.2 Alpine for tenant-partitioned caching.
5. **Identity & Access Management (`urban-keycloak`)**: Keycloak 24.0.5 SSO with pre-configured `urban` realm.

### Minimum System Requirements:
- **OS**: macOS (Apple Silicon / Intel), Ubuntu 22.04+ LTS, or Windows 11 with WSL2.
- **CPU**: 4+ Cores recommended.
- **RAM**: Minimum 8 GB (16 GB recommended for full Docker mesh).
- **Disk Space**: At least 15 GB free space.
- **Software Dependencies**:
  - [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v25+) & Docker Compose v2.
  - [Node.js](https://nodejs.org/) (v22.x LTS) & npm (v10+).
  - [Python](https://www.python.org/) (v3.11+).
  - [Git](https://git-scm.com/) (v2.38+).

---

## 2. Quick Start (Recommended: Docker Compose)

The fastest way to spin up the entire multi-container enterprise environment:

### Step 1: Clone the Repository
```bash
git clone https://github.com/sagar-singha-roy/urban-erp.git
cd urban-erp
```

### Step 2: Install Git Pre-Push Hook (Mandatory)
Urban enforces strict architectural invariants before git push:
```bash
chmod +x scripts/validate_structures.sh
cp scripts/validate_structures.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

### Step 3: Launch the Full SaaS Stack
```bash
docker compose build
docker compose up -d
```

### Step 4: Verify Container Health
```bash
docker compose ps
```
All 5 containers should report `Up` / `healthy`:
| Container Name | Service | Internal Port | Host Port | Purpose |
|---|---|---|---|---|
| `urban-console-ui` | `urban-console` | 80 | **4200** | Angular 22 Web Console |
| `urban-core-service` | `core-service` | 8000 | **8000** | FastAPI Core Backend |
| `urban-keycloak` | `keycloak` | 8080 | **8080** | SSO & Federated Auth |
| `urban-postgres` | `postgres` | 5432 | **5432** | PostgreSQL 16 + PostGIS |
| `urban-redis` | `redis` | 6379 | **6379** | Scoped Redis Cache |

---

## 3. Local Development Setup (Running Outside Docker)

For active feature development with hot reloading:

### 3.1 Start Data & Auth Containers Only
```bash
docker compose up -d postgres redis keycloak
```

### 3.2 Backend Core Service Setup (FastAPI)
```bash
cd backend/services/core_service

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Seed municipal jurisdictions and demo properties (Warangal GWMC & Hyderabad GHMC)
python app/db/seed.py

# Start development server with reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 3.3 Frontend Console Setup (Angular 22)
```bash
cd frontend/urban-console

# Install exact dependencies
npm ci

# Launch local development server
npm start
```
Console UI will be live at:
- Web Application: `http://localhost:4200`
- State Directorate Console: `http://localhost:4200/admin`

---

## 4. Default Seed Credentials & Access Scopes

The seed script creates initial municipal officers and jurisdictions:

| Role / Scope | Email Identifier | Default Password | Access Level |
|---|---|---|---|
| **State Director (IAS)** | `dir-ma@telangana.gov.in` | `urban@123` | Level 0: Apex State Directorate Console (`/admin`) |
| **Municipal Commissioner** | `commissioner@gwmc.gov.in` | `urban@123` | Level 2: Greater Warangal Corporation (`GWMC`) |
| **Revenue Officer** | `officer@gwmc.gov.in` | `urban@123` | Level 2: PTX, WTR, TRL, UCH, FIN, DMS |
| **Chief City Planner** | `chiefplanner@ghmc.gov.in` | `urban@123` | Level 2: Greater Hyderabad (`GHMC`) - BPM, TPL, FNC |
| **Keycloak Realm Admin** | `admin` | `admin` | Keycloak Administration Console (`http://localhost:8080`) |

---

## 5. Architectural Invariants & Coding Laws

Any developer contributing to this repository must follow these rules:

1. **Multi-Tenancy Filtering**:
   - Every database query touching municipal entities **must** filter by `tenant_id` and (when in city context) `sub_tenant_id`.
   - Never write tenant-blind queries.
2. **Dual Database Engine Rules**:
   - For queries/reads: Use `db: AsyncSession = Depends(get_read_db)`.
   - For mutations/inserts/updates: Use `db: AsyncSession = Depends(get_write_db)`.
3. **Frontend Styling**:
   - **No TailwindCSS**: Vanilla SCSS using tokens from `docs/TYPOGRAPHY_AND_DESIGN_SYSTEM.md`.
   - Primary: `--hake-navy` (`#0E3A52`), `--hake-teal` (`#1B8C77`), `--hake-saffron` (`#D98A2B`), `--hake-sidebar` (`#071532`).
4. **Angular 22 Standalone**:
   - Do not create NgModules. Use standalone components and Angular Signals (`signal()`, `computed()`, `effect()`).
5. **Pre-Push Validation**:
   - Always run `./scripts/validate_structures.sh` before committing.
   - Pushes failing Python compilation or Angular build are automatically blocked.

---

## 6. Troubleshooting & Diagnostics

### Database Connection Refused:
```bash
# Verify PostGIS is ready
docker exec -it urban-postgres pg_isready -U urban_admin -d urban_erp
```

### Inspect Microservice Cluster Health via API:
```bash
curl -s http://localhost:8000/api/v1/admin/cluster/health
```

### Reset / Re-seed Local Data:
```bash
# Re-run seeder inside container
docker exec -it urban-core-service python app/db/seed.py
```

### Purge All Docker Volumes & Rebuild Fresh:
```bash
docker compose down -v
docker compose build --no-cache
docker compose up -d
```
