# M1 Platform Foundation Architecture

**Document ID:** THERM-ARCH-M1-001  
**Revision:** M1r1  
**Status:** Baseline

---

## Overview

Milestone 1 establishes the immutable data platform underlying all future calculation work.
No thermal physics are computed in this milestone. All calculation submissions resolve to
`ENGINE_NOT_IMPLEMENTED`.

---

## Monorepo Layout

```
ThermPro/
├── apps/
│   ├── api/          FastAPI application (Python 3.12)
│   └── web/          React 18 SPA (TypeScript 5)
├── packages/
│   ├── units/        thermpro-units: SI unit conversion (no deps)
│   ├── schemas/      thermpro-schemas: JSON Schema validation
│   ├── engineering-types/  Re-exports domain enums
│   └── ui-components/     Shared React components (placeholder)
├── engine/
│   └── thermal_core/ Numerical engine (no FastAPI/SQLAlchemy deps)
├── infrastructure/
│   ├── docker/       Dockerfiles + nginx config
│   └── scripts/      MinIO init script
├── docs/             Engineering documentation
└── docker-compose.yml
```

## Dependency Graph

```
thermpro-units  (no deps)
      ↑
thermpro-schemas (depends on thermpro-units)
      ↑
thermpro-engine / thermal_core (depends on thermpro-units)
      ↑
thermpro-api (depends on all above + FastAPI + SQLAlchemy)
```

**CR-TECH-001 enforced:** `thermal_core` has zero dependency on FastAPI, SQLAlchemy, or any HTTP framework.

---

## Backend (apps/api)

| Layer | Technology | Notes |
|-------|-----------|-------|
| Framework | FastAPI 0.111 | Async, OpenAPI auto-gen |
| ORM | SQLAlchemy 2 async | psycopg3 dialect |
| Migrations | Alembic | Migration 0001: 9 tables |
| Validation | Pydantic v2 | Models + settings |
| Object storage | boto3 (S3/MinIO) | ObjectStorage interface |
| Auth | DevAuthProvider | JWT interface — pluggable |
| Logging | structlog | JSON output |
| Testing | pytest-asyncio | Unit + integration |

### Database Tables (M1)

1. `users` — identity (populated by DevAuthProvider in dev)
2. `projects` — analysis containers
3. `library_releases` — immutable versioned data packages
4. `library_release_files` — S3 file references per release
5. `dataset_manifests` — pinned library manifest snapshots
6. `dataset_manifest_entries` — individual pins with hash verification
7. `calculation_runs` — immutable input snapshots + ENGINE_NOT_IMPLEMENTED status
8. `calculation_artifacts` — S3 object references for run outputs
9. `audit_events` — append-only audit log

### Immutability Invariants

- **Library releases (DR-002):** Once `status = APPROVED`, no field may be modified.
  `LibraryService.approve_release()` raises `LibraryImmutabilityError` on any subsequent mutation.
- **Calculation snapshots:** `input_snapshot` JSONB is written once at submission and never modified.
  `input_checksum_sha256` is the SHA-256 of the canonical JSON; any mismatch at read-time indicates corruption.
- **Audit events:** INSERT-only; no UPDATE or DELETE paths exist in `AuditService`.

---

## Frontend (apps/web)

| Concern | Technology |
|---------|-----------|
| Framework | React 18 + TypeScript 5 |
| Build | Vite 5 |
| Forms | React Hook Form + Zod |
| State | Zustand (system readiness) |
| Routing | React Router v6 |
| Testing | Vitest + Testing Library |
| API | Type-safe fetch client (`src/api/client.ts`) |

### Pages (M1)

- `/` — Dashboard with system status
- `/projects` — Project list
- `/projects/new` — Create project (Zod-validated form)
- `/library-releases` — Library release list
- `/calculation-runs` — Calculation run list
- `/health` — Health/readiness check display

---

## Engine Isolation (CR-TECH-001)

```
engine/thermal_core/
├── domain_types.py    Enums: CalculationMode, StandardProfile, FanOperatingState,
│                      JointCondition, CalculationRunStatus, LibraryStatus
├── interfaces.py      ThermalSolverInterface (abstract) + NotImplementedSolver
└── tests/             9 unit tests — enum exclusions, ARC_FLASH absent
```

`NotImplementedSolver.solve()` returns a `SolverResult` with `status = ENGINE_NOT_IMPLEMENTED`
and `message = "Thermal solver not implemented in Milestone 1"` — no temperatures computed.
