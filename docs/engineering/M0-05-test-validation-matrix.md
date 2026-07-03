# Test and Validation Matrix — LV Switchboard Thermal Digital Twin

**Document:** M0-05  
**Milestone:** 0  
**Date:** 2026-07-03  
**Status:** Pending Engineering Approval  
**Source:** THERM-VAL-001 Rev 0.2; THERM-REQ-001 Rev 0.2

---

## 1. Purpose

This matrix traces every functional requirement (FR) and constraint requirement (CR) to
the test(s) that verify it. Four validation levels are used:

| Level | Type | When Run |
|-------|------|----------|
| L1 | Unit test (pytest) | Every CI push |
| L2 | Analytical benchmark | Every CI push (benchmarks mark) |
| L3 | Reference example (IEC/CT145) | Pre-release only |
| L4 | Physical test data import | Pre-production sign-off |

---

## 2. FR → Test Traceability

### 2.1 Thermal Physics Requirements

| FR / CR | Description | L1 Tests | L2 Benchmarks | Pass Criterion |
|---------|-------------|----------|---------------|----------------|
| FR-THERM-001 | Joule loss at rated current | UT-JOULE-001 | BM-003 | ±0.001 % vs analytical |
| FR-THERM-002 | Resistance evaluated at conductor temperature | UT-JOULE-002, UT-JOULE-003 | BM-003 | R(T) within 0.01 % of formula |
| FR-THERM-003 | Quadratic device loss model | UT-JOULE-004 | BM-002 | ±0.1 W vs exact |
| FR-THERM-004 | Joint degradation model R_joint(T, f_health) | UT-JOULE-003 | BM-008 | Hotspot ΔT within ±0.5 K of analytical |
| FR-THERM-005 | Control transformer core + copper loss | (new: UT-JOULE-005) | BM-002 | ±1 % of nameplate loss |
| FR-THERM-006 | Natural convection — vertical plates | UT-CONV-001 | BM-001 | Nu within ±5 % of Churchill-Chu |
| FR-THERM-007 | Natural convection — horizontal up | UT-CONV-002 | BM-001 | Nu within ±5 % of McAdams |
| FR-THERM-008 | Natural convection — horizontal down | UT-CONV-003 | BM-001 | Nu within ±10 % |
| FR-THERM-009 | Forced convection (Gnielinski) | UT-CONV-004, UT-CONV-005 | BM-004 | Nu within ±5 % |
| FR-THERM-010 | Radiation — single surface | UT-RAD-001, UT-RAD-002 | BM-006 | ±1 % of Stefan-Boltzmann |
| FR-THERM-011 | Radiation — two-surface effective emissivity | UT-RAD-003 | BM-006 | ±1 % |
| FR-THERM-012 | Radiation MUST use absolute temperature (K) | UT-RAD-004 | — | Test passes with T[K]; fails with T[°C] input |
| FR-THERM-013 | Air transport: Q = ṁ cp ΔT | UT-AIR-001 | BM-004 | ±0.1 % energy balance |
| FR-THERM-014 | Thermal matrix G·T = Q assembly | UT-MATRIX-001, UT-MATRIX-002 | BM-002 | Residual < 1e-10 |
| FR-THERM-015 | Convergence detection | UT-MATRIX-003 | BM-002 | Converges within 50 outer iterations |
| FR-THERM-016 | Divergence → NON_CONVERGED status | UT-MATRIX-004 | — | Status = NON_CONVERGED on deliberately divergent input |
| FR-THERM-017 | De Vahl Davis cavity benchmark | — | BM-007 | Nu_avg = 8.80 ± 2 % at Ra = 10⁶ |
| FR-THERM-018 | Shell conduction for thin walls | UT-COND-003 | BM-002 | Error < 0.01 K vs analytical (thin-wall limit) |
| FR-THERM-019 | Solid conduction: Q = kA/L × ΔT | UT-COND-001, UT-COND-002 | BM-002 | ±0.001 % vs analytical |

---

### 2.2 Airflow Requirements

| FR / CR | Description | L1 Tests | L2 Benchmarks | Pass Criterion |
|---------|-------------|----------|---------------|----------------|
| FR-FLOW-001 | Orifice flow through opening | UT-FLOW-001, UT-FLOW-002 | BM-005 | ±1 % of Q = Cd·A·√(2ΔP/ρ) |
| FR-FLOW-002 | Duct resistance (K·ρ·v²/2) | UT-FLOW-003 | BM-005 | ±2 % |
| FR-FLOW-003 | Fan P-Q curve interpolation | UT-FLOW-004 | BM-004 | Operating point within ±2 Pa and ±0.001 m³/s |
| FR-FLOW-004 | Buoyancy stack pressure | UT-FLOW-005 | BM-005 | ±1 % of Δρ·g·H |
| FR-FLOW-005 | Mass balance at pressure node | UT-FLOW-006 | BM-005 | Imbalance < 0.1 % |
| FR-FLOW-006 | Forced ventilation disables MODE 1 | (new: UT-MODE-001) | — | MODE_1 returns DISABLED error when fan present |
| FR-FLOW-007 | Air density temperature dependence | UT-AIR-002, UT-AIR-003 | BM-004 | ρ within 0.1 % of ideal gas |

---

### 2.3 Solver and Numerics Requirements

| FR / CR | Description | L1 Tests | L2 Benchmarks | Pass Criterion |
|---------|-------------|----------|---------------|----------------|
| FR-SOLV-001 | Sparse matrix solver (scipy) | UT-MATRIX-001 | BM-002 | Residual < 1e-8 |
| FR-SOLV-002 | Newton-Raphson linearisation of radiation | UT-RAD-003 | BM-006 | Converges ≤ 20 inner iterations |
| FR-SOLV-003 | Under-relaxation factor configurable | UT-MATRIX-003 | — | Result independent of ω ∈ [0.3, 0.9] for simple case |
| FR-SOLV-004 | Convergence criterion configurable | UT-MATRIX-003 | — | Accepts user-defined ε_T |
| FR-SOLV-005 | Derating outer loop updates resistance at T | UT-JOULE-002 | BM-003 | R(T_final) within 0.01 % after convergence |
| CR-ENG-005 | NON_CONVERGED → status flag in result | UT-MATRIX-004 | — | ResultSnapshot.status = NON_CONVERGED |
| CR-TECH-001 | Engine accepts/returns versioned JSON only | UT-ENGINE-001 | — | Engine raises ValueError on missing schema_version |
| CR-TECH-002 | schema_version required in both I/O | UT-ENGINE-001 | — | Schema validation fails without it |
| CR-TECH-003 | De Vahl Davis regression | — | BM-007 | REGRESSION SENSITIVE; fails CI if Nu outside ±2 % |

---

### 2.4 Derating Requirements

| FR / CR | Description | L1 Tests | L2 Benchmarks | Pass Criterion |
|---------|-------------|----------|---------------|----------------|
| FR-DERV-001 | Derating table lookup by ambient temperature | UT-DERATING-001 | — | Returns correct factor for boundary and midpoint values |
| FR-DERV-002 | Interpolation between table entries | UT-DERATING-002 | — | Linear interpolation within ±0.01 % |
| FR-DERV-003 | Altitude derating | UT-DERATING-003 | — | Applies above 2000 m per IEC standard |
| FR-DERV-004 | Derating applied in outer iteration | UT-JOULE-002 | BM-003 | Converged result uses derating-adjusted P |
| CR-ENG-008 | Joint losses never in bulk resistivity | UT-JOULE-003 | BM-008 | BusbarJoint entity always separate; test checks R_total > R_bulk |

---

### 2.5 Standards Compliance Requirements

| FR / CR | Description | L1 Tests | L2 Benchmarks | Pass Criterion |
|---------|-------------|----------|---------------|----------------|
| FR-STD-001 | IEC 61439-2 temperature-rise limits applied | UT-COMP-001 | RE-001, RE-002 | Limit 70 K busbar; 80 K terminals; etc. |
| FR-STD-002 | UL/ANSI temperature limits applied when profile active | UT-COMP-002 | — | 65 K busbar rise above 40 °C for UL |
| FR-STD-003 | IEC TR 60890 MODE 1 disabled when fans present | UT-MODE-001 | — | Error response, not a silent override |
| FR-STD-004 | IEC TR 60890 dataset never shipped | (manual check) | — | Null values in template; test checks template has no non-null coefficients |
| CR-ENG-007 | Arc-flash label = "INFORMATIVE" always | UT-ARC-001 | — | label field const "INFORMATIVE" in schema; runtime check |
| CR-ENG-009 | Compliance profile-aware | UT-COMP-001, UT-COMP-002 | — | Different limits returned for IEC vs UL profile |

---

### 2.6 Geometry Requirements

| FR / CR | Description | L1 Tests | Notes |
|---------|-------------|----------|-------|
| FR-GEO-001–016 | Geometry CRUD, validation, coordinate system | UT-GEO-001 through UT-GEO-008 | Validation: overlap, clearance, busbar routing |
| FR-GEO-014 | Geometry clash detection | UT-GEO-005, UT-GEO-006 | Overlap and out-of-bounds detection |

---

### 2.7 Data Model Requirements

| FR / CR | Description | L1 Tests |
|---------|-------------|----------|
| FR-MAT-001 | Device library: quadratic loss model | UT-JOULE-004 |
| FR-MAT-002 | Device library: data_confidence field | UT-DATA-001 |
| FR-MAT-003 | BusbarJoint: f_health modifier | UT-JOULE-003 |
| FR-MAT-004 | Material library versioning | UT-LIB-001 |
| FR-AUD-001 | Calculation run stores input hash | UT-AUD-001 |
| FR-AUD-002 | Result reproducible from stored InputSnapshot | UT-AUD-002 |

---

## 3. Level 2 Benchmark Definitions

| ID | Name | Mode | Expected Result | Tolerance | Regression |
|----|------|------|-----------------|-----------|------------|
| BM-001 | Single heated vertical wall — natural convection | MODE_2 | h within ±5 % of Churchill-Chu (Ra = 10⁵) | ±5 % | No |
| BM-002 | Closed box — uniform heat source, no airflow | MODE_2 | ΔT_internal within ±1 K of analytical | ±1 K | No |
| BM-003 | Two-node conduction chain | MODE_2 | ΔT within ±0.001 °C of Q = kA/L·ΔT | ±0.001 °C | **YES** |
| BM-004 | Forced-air energy balance — single compartment | MODE_3 | ΔT_outlet within ±0.5 K; mass balance < 0.1 % | ±0.5 K | No |
| BM-005 | Natural stack opening — two-compartment enclosure | MODE_2/3 | Mass imbalance < 0.1 % | < 0.1 % | **YES** |
| BM-006 | Radiation exchange — parallel isothermal surfaces | MODE_2 | Q_rad within ±1 % of exact formula | ±1 % | No |
| BM-007 | De Vahl Davis square cavity, Ra = 10⁶ | MODE_2 | Nu_avg = 8.80 ± 2 % | ±2 % | **YES** |
| BM-008 | Degraded joint hotspot — f_health = 2.0 | MODE_2 | Joint ΔT within ±0.5 K of analytical | ±0.5 K | **YES** |

**Regression-sensitive benchmarks** (BM-003, BM-005, BM-007, BM-008) are marked in CI as
`--benchmark-compare`. Any change in result outside tolerance fails the pipeline.

---

## 4. Level 3 Reference Examples

| ID | Name | Standard | Source Data | Acceptance |
|----|------|----------|-------------|-----------|
| RE-001 | IEC TR 60890 worked example | IEC TR 60890:2022 | Licensed; imported by admin | MAE < 0.5 K vs published result |
| RE-002 | CT145 reference enclosure | Schneider CT145 | User-provided from CT145 text | MAE < 2 K |
| RE-003 | Factory acceptance test (FAT) import | IEC 61439-1 Annex D | Structured JSON from physical test | MAE < 3 K; RMSE < 4 K; max error < 8 K; bias −2 to +2 K |
| RE-004 | IEEE 1584-2018 arc-flash example | IEEE 1584-2018 | Public worked example | Incident energy within ±5 % |

---

## 5. Level 4 Physical Test Acceptance Criteria

Physical test data is imported via `POST /admin/test-data/import` in the following JSON
format:

```json
{
  "test_type": "FAT",
  "standard": "IEC_61439_1",
  "run_id": "uuid (matching a calculation run)",
  "measurement_points": [
    {
      "probe_id": "uuid",
      "location_description": "Main busbar centre, phase L1",
      "measured_temperature_rise_K": 45.2,
      "measurement_uncertainty_K": 1.0
    }
  ]
}
```

**Acceptance metrics:**
- MAE (mean absolute error): < 3 K
- RMSE (root mean square error): < 4 K
- Maximum point error: < 8 K
- Bias (mean signed error): −2 K to +2 K

---

## 6. Non-Functional Test Coverage

| NFR | Test Approach |
|-----|---------------|
| NFR-PERF-001: Calculation < 60 s for typical enclosure | Performance benchmark: 200-device enclosure, measure wall_clock_s |
| NFR-PERF-002: ROM evaluation < 1 s | UT-ROM-001: evaluate ROM on 100 random points, measure latency |
| NFR-REPR-001: Identical input → identical result | UT-AUD-002: run identical InputSnapshot twice; compare output_hash |
| NFR-AUD-001: Input snapshot stored immutably | UT-AUD-001: verify input_hash_sha256 matches stored snapshot |
| NFR-SEC-001: Unauthenticated requests rejected | Integration test: all endpoints return 401 without Bearer token |

---

## 7. CI Pipeline Test Run Order

```
1. mypy --strict thermpro_engine       (type checks; fails fast)
2. pytest tests/unit/ -x               (unit tests; stop on first fail)
3. pytest tests/unit/ --cov=thermpro_engine --cov-fail-under=90
4. pytest tests/benchmarks/ -m regression  (regression-sensitive only; fast)
5. pytest tests/benchmarks/            (all benchmarks; slower)
6. pytest tests/integration/           (requires running Docker stack)
```

---

## 8. Appendix: Unit Test List (L1)

| Test ID | Module | What is verified |
|---------|--------|-----------------|
| UT-COND-001 | physics/conduction | Q = kA/L × ΔT, single layer |
| UT-COND-002 | physics/conduction | Series conduction layers (composite wall) |
| UT-COND-003 | physics/conduction | Shell conduction: thin wall (t/H < 1/50) vs thick wall |
| UT-JOULE-001 | physics/joule | P = I²R at T_ref |
| UT-JOULE-002 | physics/joule | R(T) = R_ref[1+α(T−T_ref)] correctness |
| UT-JOULE-003 | physics/joints | R_joint(T, f_health) = R_ref·[1+α(T−T_ref)]·f_health |
| UT-JOULE-004 | physics/joule | Quadratic device loss: P = a·I² + b·I + c |
| UT-JOULE-005 | physics/transformers | P = P_core + P_cu·(I/I_n)² |
| UT-CONV-001 | physics/convection | Churchill-Chu: vertical plate, Ra = 10⁴ to 10⁹ |
| UT-CONV-002 | physics/convection | McAdams: horizontal surface facing up |
| UT-CONV-003 | physics/convection | McAdams: horizontal surface facing down |
| UT-CONV-004 | physics/convection | Gnielinski: forced convection, turbulent duct |
| UT-CONV-005 | physics/convection | Transition from natural to mixed convection |
| UT-RAD-001 | physics/radiation | Stefan-Boltzmann: Q = ε·σ·A·(T_s⁴ − T_sur⁴) |
| UT-RAD-002 | physics/radiation | Q is zero when T_s = T_sur |
| UT-RAD-003 | physics/radiation | Effective emissivity: 1/ε_eff = 1/ε₁ + 1/ε₂ − 1 |
| UT-RAD-004 | physics/radiation | Confirms kelvin input; raises ValueError on °C input |
| UT-FLOW-001 | network/airflow_network | Orifice flow: positive ΔP → positive Q |
| UT-FLOW-002 | network/airflow_network | Orifice flow: Q proportional to √ΔP |
| UT-FLOW-003 | network/airflow_network | Duct resistance: ΔP = K·ρ·v²/2 |
| UT-FLOW-004 | network/airflow_network | Fan curve interpolation: operating point on P-Q curve |
| UT-FLOW-005 | network/airflow_network | Buoyancy: ΔP_buoy = ρ·g·H·(ΔT/T_mean) |
| UT-FLOW-006 | network/airflow_network | Mass balance at each pressure node |
| UT-DERATING-001 | physics/derating | Table boundary lookup |
| UT-DERATING-002 | physics/derating | Linear interpolation between table entries |
| UT-DERATING-003 | physics/derating | Altitude derating above 2000 m |
| UT-MATRIX-001 | network/thermal_matrix | G·T = Q assembly: 3-node test case |
| UT-MATRIX-002 | network/thermal_matrix | Symmetry of G matrix for conduction-only case |
| UT-MATRIX-003 | network/thermal_matrix | Convergence with ω = 0.3, 0.5, 0.7, 0.9 |
| UT-MATRIX-004 | network/thermal_matrix | Deliberately non-convergent: status = NON_CONVERGED |
| UT-AIR-001 | physics/air_properties | ρ(T) = P/(R_specific·T): correct at 20 °C, 40 °C |
| UT-AIR-002 | physics/air_properties | μ(T) monotonically increasing with T |
| UT-AIR-003 | physics/air_properties | λ_f(T): correct at 0 °C and 100 °C |
| UT-ENGINE-001 | solver | schema_version required; ValueError without it |
| UT-MODE-001 | modes/iec_60890 | Returns DISABLED when Fan entity present |
| UT-COMP-001 | postprocess/compliance | IEC 61439-2 busbar limit 70 K |
| UT-COMP-002 | postprocess/compliance | UL 891 busbar limit differs from IEC |
| UT-ARC-001 | modes/arc_flash | label always = "INFORMATIVE" |
| UT-AUD-001 | solver | input_hash_sha256 stored in result |
| UT-AUD-002 | solver | Identical InputSnapshot → identical result |
| UT-LIB-001 | validation/data_quality | Library version pinned in InputSnapshot |
| UT-DATA-001 | validation/data_quality | data_confidence = UNKNOWN triggers warning |
| UT-GEO-001 | validation/geometry | Devices within enclosure boundary |
| UT-GEO-005 | validation/geometry | Overlapping device detection |
| UT-GEO-006 | validation/geometry | Busbar outside enclosure boundary |
| UT-ROM-001 | rom/evaluate_rom | ROM evaluation latency < 1 s for 100 points |
