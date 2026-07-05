# M1 Test Strategy

**Document ID:** THERM-TEST-M1-001  
**Revision:** M1r1  
**See also:** M0-05 Test/Validation Matrix

---

## Test Inventory

### packages/units (thermpro-units)

| Test ID | Test | CI gate |
|---------|------|---------|
| UT-UNITS-001 | Kelvin conversion (°C → K): 0°C = 273.15 K | every push |
| UT-UNITS-002 | mm → m: 1000 mm = 1 m | every push |
| UT-UNITS-003 | Radiation absolute temperature: 0K raises ValueError | every push |
| UT-UNITS-004 | Radiation rejects °C input below 0 K threshold | every push |
| UT-UNITS-005 | µΩ → Ω: 50 µΩ = 50×10⁻⁶ Ω | every push |
| UT-UNITS-006 | mm² → m²: 100 mm² = 100×10⁻⁶ m² | every push |
| UT-UNITS-007 | m³/h → m³/s: 3600 m³/h = 1 m³/s | every push |
| UT-UNITS-008 | kPa → Pa: 1 kPa = 1000 Pa | every push |
| UT-UNITS-009 | gauge → absolute pressure (101.325 kPa offset) | every push |
| UT-UNITS-010 | Round-trip conversion: m → mm → m = identity | every push |

### packages/schemas (thermpro-schemas)

| Test | Description |
|------|-------------|
| Valid input snapshot passes validation | M0-03 compliant input |
| ARC_FLASH mode rejected | `calculation_mode: "ARC_FLASH"` → SchemaValidationError |
| Missing `library_manifest` rejected | Required field |
| Invalid fan state rejected | Old name `FORWARD_OPERATING` |
| K_AC < 1.0 warning emitted | Non-blocking but logged |
| Wrong `schema_version` rejected | Version gate |

### engine/thermal_core (thermpro-engine)

| Test | Description |
|------|-------------|
| FanOperatingState excludes deprecated names | `FORWARD_OPERATING`, `ESTIMATED_REVERSE_FLOW` absent |
| CalculationMode has 4 modes, no ARC_FLASH | Enum membership |
| StandardProfile has 5 MVP profiles, no UL/ANSI | Enum membership |
| NotImplementedSolver returns ENGINE_NOT_IMPLEMENTED | Status check |
| JointCondition has 6 values | Enum membership |

### apps/api unit tests

| Test file | What is tested |
|-----------|---------------|
| `test_hashing.py` | 7 canonical JSON hashing properties |
| `test_schema_validation.py` | M0-03 validator through API layer |
| `test_library_immutability.py` | APPROVED release raises on modify |
| `test_manifest_validation.py` | Pin hash mismatch rejected |

### apps/api integration tests (requires PostgreSQL)

| Test file | What is tested |
|-----------|---------------|
| `test_projects.py` | Create + list + get project |
| `test_library_releases.py` | Create → approve → immutability |
| `test_calculation_submission.py` | Submit → ENGINE_NOT_IMPLEMENTED stored |

### apps/web (Vitest)

| Test file | What is tested |
|-----------|---------------|
| `StatusBadge.test.tsx` | Badge rendering for all status values |
| `schemas.test.ts` | FanOperatingState, StandardProfile, CalculationMode Zod validation |

---

## CI Pipeline Jobs

| Job | Trigger | Description |
|-----|---------|-------------|
| lint | every push | `ruff check` all Python |
| type-check | every push | `mypy --strict` all packages |
| schema-validation | every push | JSON Schema well-formedness + copy verification |
| backend-unit-tests | every push | All unit + contract tests |
| integration-tests | every push | PostgreSQL service container required |
| migration-test | every push | up → down → up idempotency |
| container-build | every push | `docker build` Dockerfile.api |
| periodic-physics | nightly schedule | `pytest -m periodic_physics` (BM-007 etc.) |

---

## Excluded from M1

The following test categories are **not in scope for M1** — no thermal physics are implemented:

- Thermal solver convergence tests
- IEC TR 60890 MODE 1 empirical results
- CT145 nodal temperature benchmarks
- De Vahl Davis cavity benchmark (BM-007) — periodic physics, scheduled nightly
- Device derating tests
- Heat map rendering tests
