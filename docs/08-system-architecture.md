# System Architecture — LV Switchboard Thermal Digital Twin

**Document ID:** THERM-ARCH-001  
**Revision:** 0.1 (Draft for Engineering Review)  
**Date:** 2026-07-03  
**Status:** Pending Approval

---

## 1. Purpose

This document describes the software architecture of ThermPro: the component boundaries,
technology choices, module responsibilities, communication patterns, deployment topology,
and key architectural decisions.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              BROWSER (Desktop-first)                         │
│                                                                              │
│  ┌───────────┐  ┌──────────────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │  Library  │  │  Enclosure       │  │Properties│  │  Results &       │   │
│  │  Panel    │  │  Drawing Editor  │  │Inspector │  │  Reports         │   │
│  │  (left)   │  │  (center, SVG/  │  │  (right) │  │  (tab/overlay)   │   │
│  │           │  │   Konva.js)      │  │          │  │                  │   │
│  └───────────┘  └──────────────────┘  └──────────┘  └──────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │         Bottom Panel: Validation messages, calculation log           │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  State: Zustand stores  ──  React Hook Form  ──  Zod schemas                │
│  HTTP client: axios / fetch  ──  WebSocket: live solver progress            │
└─────────────────────────────────────┬────────────────────────────────────────┘
                                      │ HTTPS / WebSocket
┌─────────────────────────────────────▼────────────────────────────────────────┐
│                                 FastAPI (Python)                              │
│                                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ projects │ │ geometry │ │materials │ │ devices  │ │   ventilation    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ busbars  │ │conductor │ │ airflow  │ │  thermal │ │   iec_60890      │  │
│  └──────────┘ └──────────┘ └──────────┘ │ _network │ └──────────────────┘  │
│                                          └──────────┘                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ derating │ │  solver  │ │validation│ │visualiz- │ │  optimisation    │  │
│  └──────────┘ └──────────┘ └──────────┘ │  ation   │ └──────────────────┘  │
│                                          └──────────┘                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                                     │
│  │reporting │ │ datasets │ │  audit   │                                     │
│  └──────────┘ └──────────┘ └──────────┘                                     │
│                                                                              │
│  SQLAlchemy ORM ── Alembic migrations ── Pydantic request/response models   │
└────────┬──────────────────────────────────────────────────────┬─────────────┘
         │                                                      │
         ▼ SQL                                           ▼ task dispatch
┌─────────────────┐                            ┌──────────────────────────────┐
│   PostgreSQL    │                            │     Celery Worker(s)          │
│   Database      │                            │                              │
│                 │                            │  ┌────────────────────────┐  │
│  - projects     │                            │  │   Numerical Engine     │  │
│  - geometry     │  ◄────── reads from ───── │  │   (pure Python/NumPy/  │  │
│  - libraries    │                            │  │    SciPy)              │  │
│  - calc runs    │  ◄────── writes to ─────  │  │                        │  │
│  - results      │                            │  │  No DB dependency      │  │
│  - audit        │                            │  └────────────────────────┘  │
└─────────────────┘                            └──────────────┬───────────────┘
                                                              │ progress events
                                               ┌─────────────▼───────────────┐
                                               │   Redis                      │
                                               │  - task queue                │
                                               │  - result cache              │
                                               │  - WebSocket pub/sub         │
                                               └─────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│  Object Storage (S3-compatible)                                              │
│  - PDF reports                                                               │
│  - XLSX exports                                                              │
│  - Audit archives                                                            │
│  - Input/result snapshots (large JSON)                                       │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

| Layer | Technology | Version (target) | Rationale |
|-------|-----------|------------------|-----------|
| **Frontend framework** | React | 18.x | Industry standard; large ecosystem |
| **Frontend language** | TypeScript | 5.x | Type safety for complex engineering data |
| **Build tool** | Vite | 5.x | Fast HMR; excellent TS support |
| **State management** | Zustand | 4.x | Lightweight; ergonomic; avoids Redux boilerplate |
| **Form handling** | React Hook Form | 7.x | Performant; uncontrolled components |
| **Schema validation** | Zod | 3.x | Runtime type safety; TypeScript inference |
| **2D drawing editor** | Konva.js (react-konva) | 9.x | Canvas-based; performant for engineering drawing |
| **3D visualisation** | Three.js | r160+ | Optional 3D view of enclosure |
| **Charts** | ECharts (echarts-for-react) | 5.x | Engineering charts; fan curves; heat maps |
| **HTTP client** | Axios | 1.x | Interceptors; request cancellation |
| **Backend framework** | FastAPI | 0.110+ | Async; OpenAPI auto-generation; Pydantic native |
| **Backend language** | Python | 3.12 | Numerical ecosystem; type hints |
| **Data validation** | Pydantic | 2.x | Fast validation; JSON schema generation |
| **ORM** | SQLAlchemy | 2.x | Async support; mature |
| **Migrations** | Alembic | 1.x | SQLAlchemy companion |
| **Database** | PostgreSQL | 16 | ACID; JSON columns; mature |
| **Task queue** | Celery | 5.x | Mature; supports long-running tasks |
| **Message broker** | Redis | 7.x | Fast; pub/sub for WebSocket events |
| **Numerical** | NumPy + SciPy | 1.26 + 1.12 | Sparse matrices; sparse solvers |
| **PDF reports** | WeasyPrint | 60+ | HTML→PDF; CSS layout |
| **XLSX export** | openpyxl | 3.x | Pure Python; full XLSX support |
| **Object storage** | MinIO (dev) / AWS S3 (prod) | — | S3-compatible API |
| **Containerisation** | Docker + Docker Compose | — | Reproducible environments |

---

## 4. Backend Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `projects` | CRUD for Project, Assembly, StandardEdition; project history |
| `geometry` | CRUD for Enclosure, Surface, Compartment, Partition, Opening, Door; collision detection |
| `materials` | Versioned MaterialLibrary; import/export; search |
| `devices` | Versioned DeviceLibrary; import template; derating curve management |
| `busbars` | BusbarRun, BusbarSegment, BusbarJoint; routing validation |
| `conductors` | Conductor routes; ConductorLibrary |
| `ventilation` | Fan, Filter, Duct, ExternalOpening placement; VentilationDeviceLibrary |
| `airflow` | Airflow network assembly and pre-solve validation |
| `thermal_network` | Thermal matrix assembly; cell grid generation |
| `iec_60890` | Eligibility check; MODE 1 calculation; coefficient dataset management |
| `derating` | Derating curve lookup; permissible current calculation; margin reporting |
| `solver` | Orchestrates outer iteration; dispatches Celery tasks; monitors convergence |
| `validation` | Applicability, geometry, data completeness validation rules |
| `visualization` | Prepares heat map data, airflow arrow data, hot-spot annotations for frontend |
| `optimisation` | Suggestion engine; before/after comparison |
| `reporting` | PDF and XLSX generation; report template management |
| `datasets` | Import/export of library data; dataset versioning |
| `audit` | Checksum calculation; immutable record locking; audit log |

---

## 5. Numerical Engine Architecture

The numerical engine is a standalone Python package (`thermpro_engine`) with no
dependency on FastAPI, SQLAlchemy, or any database.

```
thermpro_engine/
├── __init__.py
├── schema/
│   ├── input_v1.py          # Pydantic model for CalculationInput
│   └── result_v1.py         # Pydantic model for CalculationResult
├── physics/
│   ├── conduction.py        # Solid conduction conductances
│   ├── convection.py        # Natural and forced convection correlations
│   ├── radiation.py         # Radiation conductances and linearisation
│   ├── joule.py             # Resistance, Joule loss, harmonic multiplier
│   ├── derating.py          # Derating curve interpolation
│   └── air_properties.py    # Air property polynomials
├── network/
│   ├── thermal_matrix.py    # Matrix assembly and solve
│   ├── airflow_network.py   # Pressure node network and solve
│   └── coupling.py          # Outer coupled iteration
├── modes/
│   ├── iec_60890.py         # MODE 1: IEC TR 60890 calculation
│   ├── nodal.py             # MODE 2: Nodal thermal network
│   ├── forced_ventilation.py # MODE 3: Forced-ventilation network
│   └── cfd_adapter.py       # MODE 4: CFD export/import adapter stub
├── validation/
│   ├── applicability.py     # Pre-run eligibility checks
│   ├── geometry.py          # Collision and topology checks
│   └── data_quality.py      # Completeness and consistency checks
├── postprocess/
│   ├── hotspots.py          # Hot-spot detection and ranking
│   ├── margins.py           # Thermal margin calculation
│   └── convergence.py       # Convergence trace assembly
└── solver.py                # Top-level solve() entry point
```

### 5.1 Engine Entry Point

```python
def solve(input_json: dict) -> dict:
    """
    Accept a versioned input JSON dict.
    Return a versioned result JSON dict.
    Never raises — errors are reported in the result structure.
    """
```

### 5.2 Engine Isolation

- The engine is importable independently of the web application.
- It has its own test suite with unit and integration tests.
- It is version-tagged separately from the web application.
- It can be run from the command line for batch processing:

```bash
python -m thermpro_engine solve --input input.json --output result.json
```

---

## 6. API Design

### 6.1 REST API

All API routes are versioned: `/api/v1/{module}/{resource}`

Key endpoint groups:

| Group | Example Routes |
|-------|---------------|
| Projects | `GET /api/v1/projects`, `POST /api/v1/projects`, `GET /api/v1/projects/{id}` |
| Geometry | `POST /api/v1/projects/{id}/enclosures`, `PUT /api/v1/enclosures/{id}` |
| Calculation | `POST /api/v1/calculations`, `GET /api/v1/calculations/{id}/status` |
| Results | `GET /api/v1/calculations/{id}/results`, `GET /api/v1/calculations/{id}/hotspots` |
| Libraries | `GET /api/v1/libraries/devices`, `POST /api/v1/libraries/devices/import` |
| Reports | `POST /api/v1/reports/pdf`, `GET /api/v1/reports/{id}/download` |

### 6.2 WebSocket

`WS /api/v1/calculations/{id}/progress`

The server pushes JSON messages during calculation:

```json
{"type": "progress", "outer_iter": 3, "inner_iter": 12, "max_delta_T_K": 2.3}
{"type": "converged", "outer_iter": 15, "message": "Converged in 15 iterations"}
{"type": "error", "code": "SINGULAR_MATRIX", "message": "Node 42 is isolated"}
```

### 6.3 OpenAPI Documentation

FastAPI auto-generates OpenAPI 3.1 documentation at `/api/v1/docs` (Swagger UI) and
`/api/v1/redoc`. All request and response models are defined as Pydantic models and
appear in the generated schema.

---

## 7. Security

| Concern | Approach |
|---------|---------|
| Authentication | JWT bearer tokens (OAuth2 password flow for MVP; OIDC for production) |
| Authorisation | Project-level ownership; shared-project roles (viewer, editor, owner) |
| Input validation | Pydantic on all API inputs; Zod on all frontend inputs |
| SQL injection | SQLAlchemy ORM (parameterised queries); no raw SQL |
| XSS | React renders JSX (escapes by default); CSP headers on API responses |
| CSRF | SameSite cookie policy; CORS restricted to allowed origins |
| Report integrity | SHA-256 checksum in AuditRecord; checksum printed in PDF |
| Data isolation | Row-level security or project_id filter on all queries |
| Dependency scanning | Dependabot (GitHub) or equivalent in CI |

---

## 8. Deployment Topology

### 8.1 Development

```yaml
# docker-compose.dev.yml
services:
  postgres:   image: postgres:16
  redis:      image: redis:7
  minio:      image: minio/minio
  api:        build: ./backend    (FastAPI, hot-reload)
  worker:     build: ./backend    (Celery worker)
  frontend:   build: ./frontend   (Vite dev server)
```

### 8.2 Production

```
Load Balancer (nginx or cloud LB)
  ├── Frontend (static files from Vite build, served by nginx)
  └── API (FastAPI, Gunicorn + Uvicorn workers, multiple instances)
       ├── PostgreSQL (managed RDS or equivalent)
       ├── Redis (managed ElastiCache or equivalent)
       ├── Celery Workers (container instances, auto-scaling)
       └── Object Storage (S3 or MinIO)
```

### 8.3 Environment Variables (Required)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `OBJECT_STORAGE_URL` | S3/MinIO endpoint |
| `OBJECT_STORAGE_BUCKET` | Bucket name for reports and snapshots |
| `SECRET_KEY` | JWT signing key (minimum 32 bytes) |
| `ALLOWED_ORIGINS` | CORS allowed origins |
| `CELERY_CONCURRENCY` | Number of parallel solver workers |
| `ENGINE_MAX_CELLS` | Maximum thermal cells per enclosure (default: 5000) |

No secrets shall be committed to the repository. Secrets are injected via environment
variables or a secrets manager.

---

## 9. Module Dependency Rules

```
frontend UI  →  frontend state (Zustand)  →  API client
API client   →  FastAPI routes
FastAPI      →  SQLAlchemy (database)
FastAPI      →  Celery (task dispatch only — no shared state)
Celery       →  thermpro_engine.solver.solve()
thermpro_engine  →  NumPy, SciPy, Pydantic only
thermpro_engine  ✗  FastAPI (forbidden)
thermpro_engine  ✗  SQLAlchemy (forbidden)
thermpro_engine  ✗  Redis (forbidden)
```

These rules are enforced by CI import-graph checks.

---

## 10. Future Extension Points

| Extension | Mechanism |
|-----------|----------|
| CFD adapter (MODE 4) | `cfd_adapter.py` stub; JSON export format defined in data model |
| Real-time SCADA feed | WebSocket subscriber to external data source; new input type in InputSnapshot |
| Multi-site deployment | API key per tenant; project sharing via invitation |
| Mobile view | Responsive breakpoints; read-only results view on mobile |
| Plugin device libraries | Signed dataset import with provenance verification |

---

*End of THERM-ARCH-001*
