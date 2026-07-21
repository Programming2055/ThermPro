# M4 Thermal Solver — Validation Plan

**Document ID:** THERM-VAL-M4-001  
**Revision:** 0.1  
**Status:** In Progress (M4 Implementation)  
**Date:** 2026-07-21

---

## 1. Scope

This document defines the four-level validation plan for the M4 zonal thermal solver.
Each level provides independent evidence that the solver is correct. Together they
satisfy the requirements of THERM-VAL-001 (Validation Plan, Rev 0.2) for the
lumped-parameter MODE 1/2 solver.

---

## 2. Validation Levels

| Level | Type | Purpose | CI Gate |
|-------|------|---------|---------|
| L1 | Unit tests | Verify each equation/module in isolation | Every push |
| L2 | Analytical benchmarks | Verify physics against exact closed-form solutions | Every push |
| L3 | Reference case framework | Structured comparison against known results | Pre-release |
| L4 | Periodic physics | Full solver against published CFD benchmarks | Pre-release (periodic) |

---

## 3. Level 1 — Unit Tests

All unit tests reside in `engine/tests/`. They are Python pytest tests run with
`pytest tests/ -v` on every push (CI gate).

### 3.1 Air Properties

| Test ID | What is checked | Pass criterion |
|---------|----------------|---------------|
| UT-AIR-001 | Density at 20°C, 101325 Pa | ρ ∈ [1.20, 1.21] kg/m³ |
| UT-AIR-002 | Density decreases with temperature | ρ(350 K) < ρ(300 K) |
| UT-AIR-003 | Prandtl number at 20°C | Pr ∈ [0.6, 0.8] |
| UT-AIR-004 | Viscosity increases with temperature | μ(400 K) > μ(300 K) |
| UT-AIR-005 | Thermal expansion β = 1/T | |β(T) − 1/T| / (1/T) < 1e-9 |
| UT-AIR-006 | Film temperature is midpoint | T_film = (T_s + T_f)/2 |

### 3.2 Wall Conduction

| Test ID | What is checked | Pass criterion |
|---------|----------------|---------------|
| UT-COND-001 | Resistance R = L/(kA) | Exact match |
| UT-COND-002 | Zero thickness → R = 0 | R = 0.0 |
| UT-COND-003 | Composite wall: series addition | R_total = ΣRᵢ |
| UT-COND-004 | Contact resistance: r''/A | Exact match |

### 3.3 Natural Convection

| Test ID | What is checked | Pass criterion |
|---------|----------------|---------------|
| UT-NC-001 | Ra = 0 when ΔT = 0 | Ra = 0 |
| UT-NC-002 | Ra scales as L³ | Ra(2L) / Ra(L) = 8 |
| UT-NC-003 | Churchill-Chu at Ra = 0 | Nu ≥ 1 (conduction floor) |
| UT-NC-004 | Churchill-Chu typical switchboard Ra (~10⁶) | Nu ∈ [10, 200] |
| UT-NC-005 | h_conv positive when surface hotter than air | h > 0 |
| UT-NC-006 | Horizontal heated-up, all Ra regimes | Nu > 0 |
| UT-NC-007 | Horizontal heated-down | Nu > 0, lower than heated-up |
| UT-NC-008 | All SurfaceOrientation dispatch paths reach a result | h > 0 |

### 3.4 Radiation

| Test ID | What is checked | Pass criterion |
|---------|----------------|---------------|
| UT-RAD-001 | CR-ENG-003: T < 100 K raises ValueError | "CR-ENG-003" in message |
| UT-RAD-002 | Linearised h_rad: Q = h_rad×A×ΔT matches q_rad×A | rel error < 1e-9 |
| UT-RAD-003 | Effective emissivity: 1/ε_eff = 1/ε₁ + 1/ε₂ − 1 | Exact match |
| UT-RAD-004 | Zero flux when T_s = T_surr | q = 0 |

### 3.5 Airflow Network

| Test ID | What is checked | Pass criterion |
|---------|----------------|---------------|
| UT-AFN-001 | Stack pressure = 0 when T_air = T_amb | ΔP = 0 |
| UT-AFN-002 | Stack pressure positive when T_air > T_amb | ΔP > 0 |
| UT-AFN-003 | Stack pressure scales linearly with height | ΔP(2H) / ΔP(H) ≈ 2 |
| UT-AFN-004 | Orifice flow: Q = Cd × A × √(2ΔP/ρ) | rel error < 1e-9 |
| UT-AFN-005 | Natural ventilation flow positive when T_air > T_amb | Q > 0 |
| UT-AFN-006 | Zero ventilation flow when ΔT = 0 | Q = 0 |

### 3.6 Solver Integration

| Test ID | What is checked | Pass criterion |
|---------|----------------|---------------|
| UT-SOL-001 | Zero heat generation → T_air ≈ T_amb | |T_air − T_amb| < 2 K |
| UT-SOL-002 | 1000 W → CONVERGED status | status = CONVERGED |
| UT-SOL-003 | T_air > T_amb when Q > 0 | T_air > T_amb |
| UT-SOL-004 | Higher Q → higher T_air | T_air(2Q) > T_air(Q) |
| UT-SOL-005 | NON_CONVERGED when max_iter = 1 | status = NON_CONVERGED |
| UT-SOL-006 | is_valid = False when NON_CONVERGED | CR-ENG-005 |
| UT-SOL-007 | NON_CONVERGED result has SolverWarning | len(warnings) > 0 |
| UT-SOL-008 | MODE_1 + forced ventilation → FAILED | status = FAILED (CR-ENG-006) |
| UT-SOL-009 | Determinism: identical inputs → identical outputs | Exact equality |
| UT-SOL-010 | Higher ambient → higher air temperature | Tracks T_amb |

### 3.7 Pre-Solve Validation

| Test ID | What is checked | Pass criterion |
|---------|----------------|---------------|
| UT-VAL-001 | Missing schema_version → error VAL-001 | ValidationError code = VAL-001 |
| UT-VAL-002 | Missing library_manifest → error VAL-002 | ValidationError code = VAL-002 |
| UT-VAL-003 | T_amb < 233 K → error VAL-004 | ValidationError code = VAL-004 |
| UT-VAL-004 | T_amb > 373 K → error VAL-004 | ValidationError code = VAL-004 |
| UT-VAL-005 | Zero compartments → error VAL-005 | ValidationError code = VAL-005 |
| UT-VAL-006 | MODE_1 + forced → error VAL-006 (CR-ENG-006) | ValidationError code = VAL-006 |
| UT-VAL-007 | Compartment references non-existent surface → error VAL-007 | ValidationError code = VAL-007 |
| UT-VAL-008 | Compartment references non-existent heat source → error VAL-008 | ValidationError code = VAL-008 |
| UT-VAL-009 | max_iterations < 1 → error VAL-010 | ValidationError code = VAL-010 |

---

## 4. Level 2 — Analytical Benchmarks

These are exact closed-form solutions implemented in `engine/thermal_core/benchmarks/analytical.py`
and tested in `engine/tests/test_benchmarks.py`. They are run on every push.

### BM-001: Steady-State Conduction — Plane Wall

**Problem:** Single planar wall with known heat flux `Q`, thickness `L`, thermal
conductivity `k`, area `A`, and hot-face temperature `T_hot`. Find cold-face temperature.

**Exact solution:** `T_cold = T_hot − Q×L/(k×A)`

**Test parameters:**
- `Q = 1000 W`, `L = 0.002 m`, `k = 50 W/(m·K)`, `A = 1 m²`, `T_hot = 373.15 K`
- Expected: `ΔT = 1000 × 0.002 / 50 = 0.04 K` → `T_cold = 373.11 K`

**Acceptance criterion:** `|T_computed − T_exact| ≤ 1×10⁻⁹` (machine precision, no approximation)

**Module:** `conduction/fourier.py :: conduction_through_plate`

---

### BM-002: Newton's Law of Cooling — Convection Only

**Problem:** Surface losing heat `Q` by convection with coefficient `h` over area `A`
to fluid at temperature `T_fluid`. Find surface temperature.

**Exact solution:** `T_s = T_fluid + Q / (h × A)`

**Test parameters:**
- `Q = 1000 W`, `h = 10 W/(m²·K)`, `A = 2 m²`, `T_fluid = 300 K`
- Expected: `T_s = 300 + 1000/(10×2) = 350 K`

**Acceptance criterion:** `|T_computed − T_exact| ≤ 1×10⁻⁶ K`

**Verification:** Computed `Q = h×A×(T_s − T_fluid)` must recover the input `Q` to
relative tolerance `1×10⁻⁹`.

**Module:** `benchmarks/analytical.py :: convection_cooling`

---

### BM-003: Gray Body Radiation — Two Isothermal Surfaces

**Problem:** Gray surface with emissivity `ε`, area `A`, at temperature `T_s`
radiating to surroundings at `T_surr`. Find net radiation power.

**Exact solution:** `Q = ε × σ × A × (T_s⁴ − T_surr⁴)`

**Test parameters (blackbody):**
- `ε = 1.0`, `A = 1 m²`, `T_s = 400 K`, `T_surr = 300 K`
- Expected: `Q = σ × (400⁴ − 300⁴) = 1452.8 W` (approx.)

**Acceptance criterion:** `|Q_computed − Q_exact| / Q_exact ≤ 1×10⁻⁹`

**CR-ENG-003 guard test:** Calling with `T_s = 40 K` must raise `ValueError` with
"CR-ENG-003" in the message.

**Module:** `radiation/gray_body.py :: gray_body_heat_flux`

---

### BM-004: Combined Convection + Radiation

**Problem:** Surface losing heat `Q` by combined convection (constant `h_conv`) and
radiation (emissivity `ε`) to ambient at `T_amb`. Find surface temperature.

**Solution method:** Iterative (linearised radiation coefficient at each step):
```
T_s = T_amb + Q / ((h_conv + h_rad(T_s)) × A)
```

**Test:** Energy balance verification — `Q_conv + Q_rad = Q_in` to within 1%.

**Comparison:** `T_s(ε > 0) < T_s(ε = 0, pure convection)` because radiation
provides an additional heat dissipation path.

**Module:** `benchmarks/analytical.py :: combined_heat_loss`

---

## 5. Level 3 — Reference Case Framework

Level 3 tests use the `IEC60890` benchmark framework from
`engine/thermal_core/benchmarks/iec60890.py`. The licensed coefficient tables from
IEC TR 60890:2022 Annex A are **not stored** in the repository (CR-ENG-002).

### Framework Tests (CI gate — synthetic coefficients only)

| Test ID | What is checked | Pass criterion |
|---------|----------------|---------------|
| BM-IEC-001 | Applicability: no forced vent → applicable | is_applicable = True |
| BM-IEC-002 | Applicability: forced vent → not applicable | is_applicable = False, CR-ENG-006 in reasons |
| BM-IEC-003 | Applicability: unknown busbar losses → not applicable | is_applicable = False |
| BM-IEC-004 | Effective area = √(A_in × A_out) | rel error < 1e-9 |
| BM-IEC-005 | Zero inlet area → A_eff = 0 | A_eff = 0 |
| BM-IEC-006 | b = 0 raises ValueError with "licensed" | CR-ENG-002 guard |
| BM-IEC-007 | Formula ΔT = b × P^c × (A_eff/A_ref)^d with synthetic b=1.0 | rel error < 1e-6 |
| BM-IEC-008 | Zero effective area → ΔT = 0 with warning | warning issued |
| BM-IEC-009 | Negative power rejected | ValueError p_total_w |

### Production Framework Tests (admin-injected coefficients — pre-release)

When licensed coefficients are injected via admin import (outside CI):

| Enclosure Type | Expected ΔT range | Acceptance |
|---------------|------------------|------------|
| Type 1 — IP30 bottom inlet | Published table value | ±5 K |
| Type 2 — IP31 front grill | Published table value | ±5 K |
| Type 3 — IP41 louvres | Published table value | ±5 K |

---

## 6. Level 4 — Periodic Physics Verification

Level 4 benchmarks are marked `@pytest.mark.periodic_physics` and run pre-release
only (not in every-push CI). They test the solver against published fluid dynamics
benchmarks where analytical solutions or highly resolved numerical solutions exist.

### BM-007: De Vahl Davis Natural Convection Cavity

**Reference:** De Vahl Davis, G. (1983). "Natural convection of air in a square
cavity: A bench mark numerical solution." Int. J. Num. Meth. Fluids 3, 249–264.

**Problem:** Square cavity heated on one vertical wall, cooled on the other, adiabatic
horizontal walls. Aspect ratio 1:1. Ra = 10³, 10⁴, 10⁵, 10⁶.

**Published values (Nu_avg):**
| Ra | Nu_avg (De Vahl Davis) |
|----|------------------------|
| 10³ | 1.118 |
| 10⁴ | 2.243 |
| 10⁵ | 4.519 |
| 10⁶ | 8.800 |

**Acceptance criterion:** M4 zonal solver Nu within ±15% of De Vahl Davis for
Ra ≤ 10⁵ (lumped model is not designed to resolve cavity structure at Ra = 10⁶).

**Note:** The M4 zonal model gives a single mean temperature per compartment and
cannot reproduce the full cavity temperature field. BM-007 validates that the
*integral* heat transfer prediction (overall Nu) is consistent with the published
reference within the expected error of the lumped approximation.

**Rationale for periodic:** This benchmark requires a moderately sized numerical
solution and takes ~30 s per Ra value. Running on every push is wasteful; it is
scheduled pre-release and when the convection correlations change.

---

## 7. Error Metrics

For each benchmark, the following error metrics are reported in the test output:

| Metric | Definition | Symbol |
|--------|-----------|--------|
| Absolute error | |computed − exact| | Δ |
| Relative error | |Δ| / |exact| × 100 | ε_rel [%] |
| Mean absolute error | Σ|Δᵢ| / N | MAE |
| RMS error | √(Σ Δᵢ² / N) | RMSE |
| Max error | max|Δᵢ| | ε_max |
| Bias | Σ Δᵢ / N | — |

---

## 8. Acceptance Criteria Before Production Engineering Use

All of the following must be satisfied before the M4 solver is marked
`status: PRODUCTION`:

| # | Criterion | Evidence |
|---|-----------|---------|
| 1 | All L1 unit tests pass (`284+ tests`, 0 failures) | CI green |
| 2 | All L2 BM-001..BM-004 pass within specified tolerances | CI green |
| 3 | All L3 framework tests pass | CI green |
| 4 | BM-007 (De Vahl Davis) within ±15% for Ra ≤ 10⁵ | Pre-release run |
| 5 | Energy balance error < 1% for all benchmark cases | Logged in ResultSnapshot |
| 6 | Zero NON_CONVERGED results on all benchmark cases | All status = CONVERGED |
| 7 | No SolverWarning of type ENERGY_BALANCE_ERROR on benchmark cases | warnings = () |
| 8 | CR-ENG-003 guard tested and passing | UT-RAD-001 in CI |
| 9 | CR-ENG-005 (NON_CONVERGED → is_valid = False) tested | UT-SOL-006 in CI |
| 10 | CR-ENG-006 (forced vent → MODE_1 FAIL) tested | UT-SOL-008 + UT-VAL-006 in CI |

---

## 9. Regression Strategy

The benchmark test suite in `engine/tests/test_benchmarks.py` serves as the
regression barrier. Any change to a physics module that causes a benchmark to fail
is a regression and must be corrected before merging.

The `BenchmarkResult` dataclass records both `analytical_value` and `solver_value`
for every benchmark. Any change that shifts a result by more than the tolerance
must be documented in the commit message with the physical justification.

---

## 10. Test File Index

| File | Coverage | Run frequency |
|------|---------|---------------|
| `engine/tests/test_snapshot.py` | InputSnapshot, ResultSnapshot | Every push |
| `engine/tests/test_materials.py` | AirProperties, ThermalMaterial | Every push |
| `engine/tests/test_physics.py` | Fourier, Churchill-Chu, gray_body, airflow | Every push |
| `engine/tests/test_solver.py` | ZonalSolver end-to-end | Every push |
| `engine/tests/test_benchmarks.py` | BM-001..BM-004, IEC 60890 framework | Every push |
| De Vahl Davis (future) | BM-007 periodic | Pre-release |
