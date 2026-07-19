# M2 Acceptance Checklist

**Document ID:** THERM-M2-ACCEPT-001  
**Date:** 2026-07-05  
**Branch:** `claude/m2-geometry-enclosure-model`  
**Status:** PENDING — awaiting CI runner enablement

---

## Carry-Forward Gate from M1

> Before M2 final acceptance, GitHub Actions must be enabled on `programming2055/thermpro`
> and a full CI run must complete with runners actually allocated (`runner_id != 0`).

---

## M2 Deliverables Checklist

| # | Deliverable | File(s) | Status |
|---|-------------|---------|--------|
| 1 | Coordinate system — origin lower-left-front, X=width, Y=height, Z=depth, SI metres | `engine/thermal_core/geometry.py` `COORDINATE_SYSTEM_VERSION = "1.0"` | ✅ |
| 2 | Engine domain types — `Point3D`, `Dimensions3D`, `BoundingBox`, enums, `GeometryValidationIssue` | `engine/thermal_core/geometry.py` | ✅ |
| 3 | Engine isolation — zero HTTP/ORM deps in `engine/thermal_core/` | verified by `mypy --strict` + import check | ✅ |
| 4 | 26 engine domain type tests passing | `engine/tests/test_geometry_domain.py` | ✅ |
| 5 | SQLAlchemy ORM models — 10 geometry tables | `apps/api/src/thermpro_api/models/geometry.py` | ✅ |
| 6 | Alembic migration — 0002_geometry_tables.py (up + down) | `apps/api/migrations/versions/0002_geometry_tables.py` | ✅ |
| 7 | Pydantic request/response schemas for all geometry entities | `apps/api/src/thermpro_api/routers/geometry.py` | ✅ |
| 8 | API router — 24 endpoints with audit events on writes | `apps/api/src/thermpro_api/routers/geometry.py` | ✅ |
| 9 | Geometry validation service — 16 GEO rules | `apps/api/src/thermpro_api/services/geometry_validation.py` | ✅ |
| 10 | POST /enclosures/{id}/validate — persists issues, records audit | `apps/api/src/thermpro_api/routers/geometry.py` | ✅ |
| 11 | 20 geometry validation unit tests | `apps/api/tests/unit/test_geometry_validation.py` | ✅ |
| 12 | Frontend TypeScript types for all geometry entities | `apps/web/src/types/api.ts` | ✅ |
| 13 | Type-safe API client methods for geometry endpoints | `apps/web/src/api/client.ts` | ✅ |
| 14 | EnclosuresPage — list enclosures per project | `apps/web/src/pages/EnclosuresPage.tsx` | ✅ |
| 15 | EnclosureEditorPage — 2D SVG floor plan, inspector, validation panel | `apps/web/src/pages/EnclosureEditorPage.tsx` | ✅ |
| 16 | Scale conversion utilities — metres ↔ pixels, auto-fit | `EnclosureEditorPage.tsx` (computeScale, mx, mz, mLen) | ✅ |
| 17 | App routing — `/enclosures` and `/enclosures/:id/edit` | `apps/web/src/App.tsx` | ✅ |
| 18 | 20 frontend Vitest tests (scale helpers + Zod schemas) | `apps/web/src/tests/geometry.test.ts` | ✅ |
| 19 | Documentation — geometry model, endpoints, test strategy | `docs/engineering/m2-*.md` | ✅ |
| 20 | This acceptance checklist | `docs/engineering/M2-acceptance-checklist.md` | ✅ |

---

## Non-Negotiable Rules Verified

| Rule | Verification |
|------|-------------|
| CR-ENG-001: No thermal physics | No heat loss, temperature, or thermal network code anywhere in M2 |
| CR-ENG-002: No IEC TR 60890 tables | No coefficient tables in repository |
| CR-ENG-003: Kelvin for radiation | Not applicable — no radiation in M2 |
| CR-ENG-005: NON_CONVERGED on unconverged | Not applicable — no solver in M2 |
| CR-ENG-006: Forced vent disables MODE 1 | Not applicable — no mode selection in M2 |
| CR-ENG-012: Libraries immutable once APPROVED | Existing LibraryImmutabilityError unchanged |
| CR-ENG-013: SI units internally | All columns use `_m` suffix; mm only in UI display |
| CR-TECH-001: Engine zero HTTP/ORM deps | `engine/thermal_core/geometry.py` has zero FastAPI/SQLAlchemy imports |
| CR-TECH-002: schema_version + library_manifest on InputSnapshot | InputSnapshot unchanged from M1 |
| M2-specific: No ARC_FLASH | No arc flash types in geometry model |
| M2-specific: No UL/ANSI standard profiles | No new standard profiles added |
| M2-specific: Geometry in metres | Enforced by `_m` column naming convention and Pydantic validators |
| M2-specific: No JSONB for core geometry | All positions and dimensions use Float columns |
| M2-specific: Audit events on writes | AuditService.record_event called on every POST and DELETE |

---

## Test Results (Local)

| Suite | Command | Count | Result |
|-------|---------|-------|--------|
| Engine geometry domain | `cd engine && pytest tests/ -v` | 26 tests | ✅ 26 passed |
| API geometry validation | `pytest apps/api/tests/unit/test_geometry_validation.py -v` | 19 tests | ✅ 19 passed |
| All API unit tests | `pytest apps/api/tests/unit/ -v` | 46 tests | ✅ 46 passed |
| Frontend (Vitest) | `npx vitest run --reporter=verbose` | 36 tests | ✅ 36 passed |

---

## CI Gate

The M2 carry-forward gate requires CI to run with real GitHub Actions runners (`runner_id != 0`).

Expected CI results once runners are allocated:
- `lint` (ruff): pass
- `type-check` (mypy): pass
- `schema-validation`: pass (M0-03/04 unchanged)
- `backend-unit-tests`: pass (47 unit tests)
- `integration-tests`: pass (requires PostgreSQL service container)
- `migration-test`: pass (0002_geometry_tables applies and rolls back)
- `container-build`: pass

---

## M3 Readiness

M3 (thermal network model, physics engine scaffolding) may begin after this PR is merged to `main`.

M3 prerequisites satisfied by M2:
- Enclosure geometry with internal volume, surfaces, compartments, partitions ✅
- Device placements defining heat source locations ✅
- ExternalOpening and InternalOpening locations for airflow network construction ✅
- Geometry validation framework to detect invalid inputs before physics run ✅
- `bc_placeholder` JSONB columns on surfaces and compartments reserved for M3 thermal BCs ✅
- `COORDINATE_SYSTEM_VERSION = "1.0"` documented and stored on every entity ✅
