# M2 Test Strategy

**Document ID:** THERM-GEO-003  
**Date:** 2026-07-05  
**Status:** IMPLEMENTED

---

## Test Levels

### Level 1 — Engine Domain Type Unit Tests

**Location:** `engine/tests/test_geometry_domain.py`  
**Runner:** `cd engine && pytest tests/ -v`  
**Count:** 26 tests

Tests cover:
- `Point3D` creation
- `Dimensions3D` rejects zero and negative dimensions
- `BoundingBox.contains_point()` — inside, outside, boundary
- `BoundingBox.overlaps()` — true (overlap), false (separated), false (adjacent)
- All 7 enum classes have expected values and correct member counts
- `COORDINATE_SYSTEM_VERSION` is a string
- `CoordinateSystem` holds version and origin description
- `GeometryValidationIssue` stores all required fields

No FastAPI, SQLAlchemy, or HTTP dependencies (CR-TECH-001 verified).

### Level 2 — Geometry Validation Service Unit Tests

**Location:** `apps/api/tests/unit/test_geometry_validation.py`  
**Runner:** `pytest apps/api/tests/unit/test_geometry_validation.py -v`  
**Count:** 20 tests

All tests use `MagicMock(spec=OrmModel)` to avoid ORM mapper requirements.

| Test | Rule |
|------|------|
| `test_geo001_zero_width_raises_error` | GEO-001 |
| `test_geo001_negative_height_raises_error` | GEO-001 |
| `test_geo002_compartment_outside_enclosure` | GEO-002 |
| `test_geo002_compartment_exactly_fits` | GEO-002 |
| `test_geo003_duplicate_names_flagged` | GEO-003 |
| `test_geo003_unique_names_ok` | GEO-003 |
| `test_geo004_overlapping_compartments_flagged` | GEO-004 |
| `test_geo004_adjacent_compartments_ok` | GEO-004 |
| `test_geo006_device_zero_depth_flagged` | GEO-006 |
| `test_geo007_device_outside_enclosure` | GEO-007 |
| `test_geo007_device_inside_enclosure_ok` | GEO-007 |
| `test_geo009_device_overlap_flagged` | GEO-009 |
| `test_geo009_non_overlapping_devices_ok` | GEO-009 |
| `test_geo013_open_area_fraction_out_of_range` | GEO-013 |
| `test_geo014_discharge_coefficient_out_of_range` | GEO-014 |
| `test_ext_opening_valid_fractions_ok` | GEO-013/014 |
| `test_geo015_internal_open_area_fraction_out_of_range` | GEO-015 |
| `test_geo016_internal_cd_out_of_range` | GEO-016 |
| `test_clean_enclosure_no_issues` | All rules |

### Level 3 — Frontend Unit Tests (Vitest)

**Location:** `apps/web/src/tests/geometry.test.ts`  
**Runner:** `npx vitest run --reporter=verbose`  
**Count:** 16 tests (geometry.test.ts) + 20 pre-existing = 36 total Vitest

Tests cover:
- `computeScale` produces positive scale, respects canvas padding, constraint axis logic
- `mx`, `mz`, `mLen` — correct mapping of metres to pixels
- `CreateEnclosureSchema` — valid request accepted, invalid dimensions rejected, empty name rejected
- `CreateCompartmentSchema` — valid accepted, zero depth rejected, invalid enum rejected

### Level 4 — API Integration Tests (PostgreSQL required)

**Location:** `apps/api/tests/integration/` (not yet written — M2 integration tests require live PostgreSQL)

These are marked `@pytest.mark.integration` and run only in the CI integration-tests job with a PostgreSQL service container. They will cover:

- Full CRUD lifecycle for Assembly, Enclosure, Compartment, Partition
- Geometry validation endpoint returns correct issue counts
- Audit events recorded on every write
- Cascade delete propagates to all sub-entities

These will be added in the M2 integration test pass (post-CI enablement).

---

## Execution Commands

```bash
# All M2 unit tests (engine + API + frontend)
cd engine && pytest tests/ -v && cd ..
pytest apps/api/tests/unit/ -v
npx vitest run --reporter=verbose

# M2 geometry validation tests only
pytest apps/api/tests/unit/test_geometry_validation.py -v

# Engine geometry domain tests only
cd engine && pytest tests/test_geometry_domain.py -v
```

---

## CI Gate Assignment

Per DR-010 and the CI pipeline in `.github/workflows/ci.yml`:

| Test Level | CI Job | Every Push |
|------------|--------|-----------|
| Engine domain types | `backend-unit-tests` | ✓ |
| Geometry validation service | `backend-unit-tests` | ✓ |
| Frontend geometry tests | `build` (vitest in build step) | ✓ |
| Integration tests | `integration-tests` | ✓ (requires PostgreSQL) |

No M2 test is tagged `periodic_physics` — all M2 geometry tests run on every push.

---

## Scope Boundary

M2 tests do not cover:
- Thermal resistance values (M3)
- Heat source assignment (M3)
- IEC TR 60890 calculations (M3)
- Device derating (M4+)
- Arc flash (DR-008 — deferred)
