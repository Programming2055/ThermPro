# Validation Plan — LV Switchboard Thermal Digital Twin

**Document ID:** THERM-VAL-001  
**Revision:** 0.1 (Draft for Engineering Review)  
**Date:** 2026-07-03  
**Status:** Pending Approval

---

## 1. Purpose

This document defines the four-level validation strategy for ThermPro. It specifies the
unit tests, analytical benchmarks, reference examples, and physical-test comparison
protocol that must be passed before the software is used for production engineering
calculations.

**The software SHALL NOT be used for production engineering until:**
- All Level 1 unit tests pass with ≥ 90% line coverage.
- All Level 2 analytical benchmarks produce results within defined tolerances.
- At least one Level 3 reference example is successfully reproduced.
- Level 4 acceptance criteria are defined (physical test data may not be available
  at initial release but the infrastructure must be ready).

---

## 2. Validation Framework

| Level | Name | Method | Authority |
|-------|------|--------|-----------|
| L1 | Unit Tests | Automated pytest; known analytical answer | CI pipeline |
| L2 | Analytical Benchmarks | Known closed-form or simple solutions | Engineer review |
| L3 | Reference Examples | Published or authorised cases | Senior engineer review |
| L4 | Physical Test Comparison | Import of thermocouple/airflow measurements | Qualified engineer sign-off |

---

## 3. Level 1 — Unit Tests

All unit tests live in `tests/unit/` and run on every commit via CI.

### 3.1 Physics Module Tests

| Test ID | Module | Test Description | Expected Result |
|---------|--------|-----------------|-----------------|
| UT-COND-001 | conduction | Single slab: k=50 W/(m·K), A=1 m², L=0.01 m, ΔT=10 K | Q = 50 000 W |
| UT-COND-002 | conduction | Series wall: two layers, different k and L | 1/G_total = 1/G1 + 1/G2 |
| UT-COND-003 | conduction | k(T): k increases linearly with T | G computed at mean T |
| UT-JOULE-001 | joule | R(T): copper at 75 °C vs 20 °C | R₇₅ = R₂₀ × [1 + 0.00393×55] |
| UT-JOULE-002 | joule | P = I²R: I=100 A, R=0.001 Ω | P = 10 W |
| UT-JOULE-003 | joule | Harmonic multiplier: THD=30% | I_rms = I_1 × √(1.09) |
| UT-JOULE-004 | joule | AC multiplier K_AC=1.2 | R_AC = 1.2 × R_DC |
| UT-CONV-001 | convection | Churchill-Chu: vertical plate H=0.5 m, ΔT=20 K (air, 300 K) | Nu within 5% of reference value |
| UT-CONV-002 | convection | Horizontal upward: Ra=10⁶ | Nu = 0.54 × 10^(6×0.25) within 2% |
| UT-CONV-003 | convection | Horizontal downward | Nu = 0.27 × Ra^0.25 |
| UT-CONV-004 | convection | h = Nu × λ_f / L_c; check units | h in W/(m²·K) |
| UT-CONV-005 | convection | Gnielinski: Re=10000, Pr=0.71 | Compare to reference Nu value |
| UT-RAD-001 | radiation | Q_rad: ε=0.9, A=1 m², T_s=350 K, T_sur=300 K | Q = 0.9×5.67e-8×1×(350⁴−300⁴) |
| UT-RAD-002 | radiation | Effective emissivity, two surfaces | ε_eff = 1/(1/ε1 + 1/ε2 − 1) |
| UT-RAD-003 | radiation | Linearised h_r: result matches Q_rad / A / ΔT | Within 0.01% of nonlinear |
| UT-RAD-004 | radiation | T in kelvin enforcement: 350 °C input raises error | ValueError |
| UT-FLOW-001 | airflow | Orifice flow: Cd=0.6, A=0.01 m², ΔP=5 Pa, ρ=1.2 | ṁ = Cd×A×√(2×5×1.2) |
| UT-FLOW-002 | airflow | Duct resistance: K=2, ρ=1.2, v=2 m/s | ΔP = K×1.2×4/2 = 4.8 Pa |
| UT-FLOW-003 | airflow | Fan curve interpolation: 3-point P-Q curve | Cubic spline passes through all points |
| UT-FLOW-004 | airflow | Affinity law: speed increase 10% | Q×1.1, ΔP×1.21, P_shaft×1.331 |
| UT-FLOW-005 | airflow | Mass balance 2-node: Σṁ=0 | Residual < 1e-10 kg/s |
| UT-FLOW-006 | airflow | Stack pressure: H=1 m, T_int=330 K, T_ext=300 K | ΔP = 1.2×9.81×1×(30/300) |
| UT-DERATING-001 | derating | Linear derating: f_d at θ_limit | f_d = 0.0 at max ambient |
| UT-DERATING-002 | derating | Derating curve interpolation: 3 breakpoints | Piecewise-linear interpolation check |
| UT-DERATING-003 | derating | Permissible current: I_perm = f_d × I_n | Correct at boundary points |
| UT-MATRIX-001 | thermal_matrix | 2-node conduction system | T solved analytically ± 1e-6 K |
| UT-MATRIX-002 | thermal_matrix | Diagonal dominance check | G matrix is diagonally dominant |
| UT-MATRIX-003 | thermal_matrix | Boundary node moves to RHS | Correct assembly |
| UT-MATRIX-004 | thermal_matrix | Singular matrix detection | Returns error, not NaN |
| UT-AIR-001 | air_properties | ρ(T): ideal gas at 300 K, 101325 Pa | ρ = 1.177 kg/m³ ± 0.5% |
| UT-AIR-002 | air_properties | μ(T): power law at 300 K | μ = 1.846×10⁻⁵ Pa·s ± 1% |
| UT-AIR-003 | air_properties | λ(T): power law at 300 K | λ = 0.02624 W/(m·K) ± 1% |

### 3.2 Coverage Requirement

All tests run via `pytest --cov=thermpro_engine --cov-report=term-missing`.

**Acceptance criterion:** ≥ 90% line coverage on `thermpro_engine/physics/` and
`thermpro_engine/network/`.

---

## 4. Level 2 — Analytical Benchmark Cases

These cases have known closed-form or simple-network solutions. The solver result
is compared to the analytical result.

### 4.1 BM-001 — Single Heated Wall

**Setup:** A flat plate (height 0.5 m, width 1 m) dissipating 200 W by natural convection
and radiation on one face; other face insulated. Ambient = 25 °C.

**Analytical solution:** Steady-state surface temperature found iteratively using
combined convection + radiation = 200 W. Reference solution computed using the
Churchill-Chu correlation and Stefan-Boltzmann law.

**Acceptance criterion:** Solver T_surface within ±0.5 K of reference solution.

### 4.2 BM-002 — Closed Box with Uniform Heat

**Setup:** A sealed cubic enclosure (0.6 m × 0.6 m × 0.6 m), steel walls (k=50),
uniform heat sources totalling 500 W. No openings; heat lost by external convection
and radiation only.

**Expected:** Uniform internal air temperature; enclosure temperature rise computable
from external thermal resistance.

**Acceptance criterion:** Internal temperature rise within ±1 K of energy-balance result.

### 4.3 BM-003 — Two-Node Conduction Chain

**Setup:** Two nodes connected by a 10 W/K conductance. Node 1 = boundary at 100 °C.
Node 2: heat source Q = 50 W.

**Analytical:** T_2 = T_1 + Q/G = 100 + 5 = 105 °C

**Acceptance criterion:** Solver T_2 = 105.000 °C ± 0.001 °C.

### 4.4 BM-004 — Forced-Air Energy Balance

**Setup:** A duct with airflow Q_vol = 0.05 m³/s, inlet temperature 25 °C, heat source
Q = 500 W inside.

**Analytical:** ΔT = Q / (ρ × Q_vol × cp) = 500 / (1.2 × 0.05 × 1007) ≈ 8.3 K
Outlet temperature ≈ 33.3 °C.

**Acceptance criterion:** Solver outlet temperature within ±0.5 K.

### 4.5 BM-005 — Natural Stack Opening

**Setup:** Two chambers connected by a lower opening (inlet) and upper opening (outlet),
separated by H = 1 m. Internal air at T_int = 50 °C; external at T_ext = 25 °C.
Opening areas and Cd = 0.6 given.

**Analytical:** Stack pressure from buoyancy formula; orifice flow from pressure.
Mass balance requires inlet flow = outlet flow.

**Acceptance criterion:** Mass imbalance at convergence < 0.1%; flow within ±2% of
hand calculation.

### 4.6 BM-006 — Radiation Between Parallel Surfaces

**Setup:** Two parallel plates, 0.5 m × 0.5 m, separated by 0.1 m. ε_1 = 0.9, ε_2 = 0.85.
T_1 = 80 °C, T_2 = 40 °C. ε_eff = 1/(1/0.9 + 1/0.85 − 1) ≈ 0.778.

**Analytical:** Q_rad = ε_eff × σ × A × (T_1⁴ − T_2⁴)
= 0.778 × 5.67×10⁻⁸ × 0.25 × (353⁴ − 313⁴) ≈ 34.7 W

**Acceptance criterion:** Solver Q_rad within ±1% of 34.7 W.

### 4.7 BM-007 — De Vahl Davis Differentially Heated Cavity

**Setup:** 2D square cavity (side length H = 1 m) filled with air. Left vertical wall held
at T_hot; right vertical wall at T_cold = T_hot − ΔT; top and bottom walls adiabatic.
Rayleigh number Ra = 10⁶ (achieved by setting appropriate ΔT and air properties).
The gravity vector is downward (along the cavity height).

**Purpose:** Verification of the buoyancy (Boussinesq) solver implementation. This is
the canonical benchmark for natural-convection codes (de Vahl Davis, 1983). Any
buoyancy solver implementation must pass this benchmark before deployment to real
enclosure cases.

**Analytical/reference:** Average Nusselt number on the heated wall at Ra = 10⁶:
**Nu_avg ≈ 8.80** (de Vahl Davis benchmark; high-accuracy finite-difference solution).

The correct circulation cell must be reproduced: hot air rises along the left wall,
crosses the top, descends along the cold wall, and returns along the bottom.

**Acceptance criteria:**
- Average Nu on the hot wall within ±2% of 8.80 (i.e., 8.62 ≤ Nu ≤ 8.98).
- Correct single-cell circulation pattern.
- Maximum temperature: at top-left corner; minimum: at bottom-right corner.
- Top and bottom boundary: zero heat flux (adiabatic).

**Note:** This benchmark is designated regression-sensitive. It must be re-run on every
release and every change to the convection or airflow solver modules.

### 4.8 BM-008 — Degraded Joint Hotspot Sensitivity

**Setup:** A simple two-busbar-segment configuration with one joint between them. Current
I = 400 A. Nominal case: R_joint = 1 × 10⁻⁶ Ω (nominal contact resistance, f_health = 1.0).
Degraded case: f_health = 5.0 (five-fold resistance increase representing loose joint).

**Purpose:** Verify that the joint entity model (THERM-EQN-001 §4.5) correctly amplifies
local hotspot temperature when f_health > 1, without proportionally affecting the
global average temperature.

**Expected behaviour:**
- Nominal case: joint temperature rise ≈ I² × R_joint / G_joint (close to segment temperature).
- Degraded case (f_health = 5): joint power = 5× nominal; localised hotspot at joint rises
  while global average changes by less than 5 K.
- A NOT_VERIFIABLE flag shall be raised if R_joint_ref has data_confidence = LOW.

**Acceptance criteria:**
- Degraded case joint temperature ≥ nominal case joint temperature + 4 × (nominal P_joint / G_local).
- Solver correctly propagates the health-state modifier through R_joint(T, health).
- Audit trail confirms f_health = 5.0 was the source of hotspot.

---

## 5. Level 3 — Published/Reference Examples

These cases reproduce examples from authorised sources to demonstrate that the solver
agrees with established methods within the published tolerances.

### 5.1 RE-001 — IEC TR 60890 Example Calculation

Once a licensed IEC TR 60890 coefficient dataset is loaded by the administrator, the
software shall reproduce the example calculation from IEC TR 60890:2022 (if such an
example is provided in the standard) within ±0.5 K.

If no example is provided in the standard, an alternative authorised worked example
(e.g., from a licensed manufacturer's technical guide) shall be used and referenced.

**Required inputs for this case:** Full enclosure geometry, power losses, surface factors,
partition factor, installation type — all from the authorised source.

**Acceptance criterion:** Δθ_mid and Δθ_top within ±0.5 K of the reference values.

### 5.2 RE-002 — CT145 Reference Cases

The Schneider Cahier Technique No. 145 contains comparison tables of calculated versus
experimental temperatures. ThermPro shall attempt to reproduce the nodal thermal network
results from those cases using legally available input data.

**Note:** Because the CT145 document may contain proprietary datasets not available to
ThermPro, this test uses only input data the engineer can enter manually (geometry,
power losses, boundary conditions). Proprietary material properties or device curves
must be substituted with general values, clearly flagged as ASSUMED.

**Acceptance criterion:** Calculated temperatures within ±2 K of the published experimental
values, or within the stated uncertainty of the experimental data.

### 5.3 RE-003 — Manufacturer Acceptance Test Data

When a manufacturer provides a formal acceptance test result for an assembly (temperatures
measured at specified points under defined load conditions), ThermPro shall be able to
reproduce the test setup and compare to the measured temperatures.

**Acceptance criterion:** MAE < 3 K; maximum error < 5 K.

### 5.4 RE-004 — IEEE 1584-2018 Arc-Flash Screening Case

**Purpose:** Verify that the arc-flash module correctly implements the IEEE 1584-2018
parametric workflow for at least one electrode configuration.

**Required inputs:** Bolted fault current, system voltage, electrode configuration
(e.g., HCB — horizontal conductors in a box), enclosure dimensions, working distance,
arc duration.

**Expected output:** Arcing current (kA), incident energy (cal/cm²), arc-flash boundary (m).

**Acceptance criterion:** When the licensed IEEE 1584-2018 standard is available,
reproduce the standard's own verification examples within ±5% of the published
incident-energy values. If IEEE 1584-2018 examples are not directly available, use
a published worked example from an IEEE tutorial document or equivalent authorised
source with the same acceptance tolerance.

**Scope restriction:** This benchmark verifies the parametric model implementation only.
It does not validate the model against physical arc-flash tests. The software module
carries an INFORMATIVE label at all times (CR-ENG-007).

---

## 6. Level 4 — Physical Test Validation

### 6.1 Test Data Import Format

Physical test data shall be imported using the following JSON format:

```json
{
  "schema_version": "1.0",
  "test_reference": "Panel DB-A, Factory Acceptance Test, 2026-06-01",
  "test_date": "2026-06-01",
  "conducted_by": "Engineer name / organisation",
  "calibration_reference": "Thermocouple calibration cert no. TC-2026-001",
  "ambient_temperature_C": [
    {"time_s": 0, "value_C": 23.5},
    {"time_s": 3600, "value_C": 24.1}
  ],
  "test_current_A": {
    "circuit_id": "CB-01", "values": [
      {"time_s": 0, "value_A": 250},
      {"time_s": 3600, "value_A": 250}
    ]
  },
  "measurements": [
    {
      "probe_id": "TC-01",
      "description": "Top busbar, centre",
      "x_mm": 400, "y_mm": 1600, "z_mm": 300,
      "values": [
        {"time_s": 0, "value_C": 23.5},
        {"time_s": 3600, "value_C": 68.2}
      ]
    }
  ],
  "fan_speed_rpm": [
    {"fan_id": "FAN-01", "values": [{"time_s": 0, "value_rpm": 1450}]}
  ],
  "air_velocity_measurements": [
    {"location": "Outlet grille OG-01", "x_mm": 200, "y_mm": 1800, "z_mm": 100,
     "value_m_s": 1.2, "measurement_device": "Hot-wire anemometer"}
  ]
}
```

### 6.2 Comparison Metrics

For each probe location that corresponds to a thermal cell in the model:

| Metric | Formula | Acceptance Criterion |
|--------|---------|---------------------|
| Mean Absolute Error (MAE) | mean(|T_calc − T_meas|) | < 3 K |
| Root Mean Square Error (RMSE) | √mean((T_calc − T_meas)²) | < 4 K |
| Maximum Error | max(|T_calc − T_meas|) | < 8 K |
| Systematic Bias | mean(T_calc − T_meas) | −2 K to +2 K |
| Error by Height | MAE per 20% height band | No systematic trend with height > 2 K/band |
| Error by Compartment | MAE per compartment | All compartments MAE < 5 K |

Criteria apply to steady-state temperature rise (final values only). Transient comparison
requires agreement within ±20% of time to reach 90% of steady-state rise.

### 6.3 Validation Status

ThermPro shall report a validation status on every result based on the test comparison:

| Status | Condition |
|--------|-----------|
| VALIDATED | L4 comparison performed; all acceptance criteria met |
| VALIDATION IN PROGRESS | Test data imported; comparison underway |
| NOT VALIDATED | No L4 test data available; result is informative only |
| VALIDATION FAILED | L4 comparison performed; one or more criteria not met |

Until the software achieves VALIDATED status for a given enclosure type and configuration,
all results carry a `NOT VALIDATED` watermark on the report.

---

## 7. Regression Testing

### 7.1 Continuous Integration

Every pull request must pass:
1. All L1 unit tests (pytest CI run).
2. All L2 benchmark cases (automated comparison against reference values).
3. Code coverage check (≥ 90% on physics and network modules).
4. Static type checking (mypy --strict on thermpro_engine).
5. Import graph check (no forbidden dependencies from thermpro_engine to database/API).

### 7.2 Release Gate

Before any version is tagged for release:
1. All CI checks pass.
2. L3 reference examples produce results within tolerance.
3. A release validation report is generated and signed by a senior engineer.
4. The release validation report is archived with the release tag.

### 7.3 Sensitive Cases

The following cases are designated as regression-sensitive and must be re-run on every
release:

| Case | Why Sensitive |
|------|--------------|
| BM-003 Two-node conduction | Core matrix solve correctness |
| BM-005 Natural stack opening | Buoyancy coupling; often breaks when ρ(T) changes |
| BM-007 De Vahl Davis cavity | Buoyancy solver verification; Nu ≈ 8.8 at Ra = 10⁶ |
| BM-008 Degraded joint hotspot | Joint entity model; sensitivity to f_health modifier |
| UT-RAD-004 Temperature unit check | Radiation in kelvin; a °C/K confusion causes large errors |
| UT-MATRIX-004 Singular matrix | Solver robustness |
| UT-FLOW-005 Mass balance | Mass conservation is a fundamental constraint |

---

## 8. Limitations of This Validation Plan

1. Physical test data (Level 4) may not be available at initial release. The application
   SHALL NOT claim "validated" status until real measurements are compared.
2. All tests use air as the working fluid. Other gases (SF₆, N₂) are outside scope.
3. The validation plan covers steady-state only at initial release. Transient validation
   is deferred to a later milestone.
4. The plan does not include EMC, mechanical, or acoustic testing.

---

*End of THERM-VAL-001*
