# M4 Thermal Solver — Benchmark Suite

**Document ID:** THERM-BM-M4-001  
**Revision:** 0.1  
**Status:** In Progress (M4 Implementation)  
**Date:** 2026-07-21

---

## 1. Scope

This document describes the complete benchmark suite for the M4 thermal solver,
including:

- BM-001 through BM-004: analytical benchmark cases with exact closed-form solutions
- IEC TR 60890 framework benchmark (BM-IEC): applicability checks and formula verification
- BM-007: De Vahl Davis natural convection cavity (periodic physics verification)

All benchmarks implement the `BenchmarkResult` dataclass defined in
`engine/thermal_core/benchmarks/analytical.py`, which records both the analytical
value and the computed solver value for auditability.

---

## 2. Benchmark Definitions

### BM-001 — Steady-State Conduction Through a Plane Wall

**Category:** L2 Analytical (every-push CI gate)  
**Module:** `thermal_core/conduction/fourier.py`  
**Test:** `engine/tests/test_benchmarks.py::TestBM001PlaneConductionWall`

**Physical setup:**

A single-layer flat wall separates two isothermal reservoirs. A known power `Q`
is supplied at the hot face and conducted through the wall.

```
Hot face (T_hot) ──[wall: L, k, A]── Cold face (T_cold)
                         ↓ Q [W]
```

**Governing equation (Fourier's law, 1D steady):**

```
Q = k × A × (T_hot − T_cold) / L

T_cold = T_hot − Q × L / (k × A)
```

**Benchmark parameters:**

| Parameter | Symbol | Value | Unit |
|-----------|--------|-------|------|
| Heat flow | Q | 1000 | W |
| Wall thickness | L | 0.002 | m |
| Thermal conductivity | k | 50 | W/(m·K) |
| Cross-sectional area | A | 1.0 | m² |
| Hot-face temperature | T_hot | 373.15 | K |

**Exact solution:**

```
ΔT = 1000 × 0.002 / (50 × 1.0) = 0.04 K
T_cold = 373.15 − 0.04 = 373.11 K
```

**Acceptance criterion:** `|T_computed − 373.11| ≤ 1×10⁻⁹ K`

**Physical insight:** A 2 mm steel panel (k = 50 W/(m·K)) conducting 1 kW develops
only 0.04 K temperature drop — the wall resistance is negligible. This confirms
the solver correctly handles the low-resistance limit without numerical issues.

**Additional tests:**
- Q = 0 → T_cold = T_hot (isothermal)
- Higher k → smaller ΔT
- Thicker wall → larger ΔT

---

### BM-002 — Newton's Law of Cooling (Convection Only)

**Category:** L2 Analytical (every-push CI gate)  
**Module:** `thermal_core/benchmarks/analytical.py :: convection_cooling`  
**Test:** `engine/tests/test_benchmarks.py::TestBM002ConvectionCooling`

**Physical setup:**

A surface of area `A` dissipates power `Q` entirely by convection to a fluid at
temperature `T_fluid` with convection coefficient `h`.

```
Surface (T_s) ──[h, A]── Fluid (T_fluid)
                  ↓ Q [W]
```

**Governing equation (Newton's law of cooling):**

```
Q = h × A × (T_s − T_fluid)

T_s = T_fluid + Q / (h × A)
```

**Benchmark parameters:**

| Parameter | Symbol | Value | Unit |
|-----------|--------|-------|------|
| Heat loss | Q | 1000 | W |
| Convection coefficient | h | 10 | W/(m²·K) |
| Surface area | A | 2.0 | m² |
| Fluid temperature | T_fluid | 300 | K |

**Exact solution:**

```
T_s = 300 + 1000 / (10 × 2) = 350 K
```

**Acceptance criterion:** `|T_computed − 350.0| ≤ 1×10⁻⁶ K`

**Self-verification:** After solving, compute `Q_check = h × A × (T_s − T_fluid)`.
Required: `|Q_check − Q| / Q ≤ 1×10⁻⁹`.

**Physical insight:** h = 10 W/(m²·K) represents weak forced convection or strong
natural convection. The 50 K surface rise above fluid confirms the formula is
implemented correctly for the typical switchboard internal surface temperature range.

**Additional tests:**
- Q = 0 → T_s = T_fluid
- Higher h → lower T_s (better cooling)
- Dimensional check Q = h × A × ΔT recovers input Q

---

### BM-003 — Radiation Exchange Between Gray Body and Surroundings

**Category:** L2 Analytical (every-push CI gate)  
**Module:** `thermal_core/radiation/gray_body.py`  
**Test:** `engine/tests/test_benchmarks.py::TestBM003RadiationExchange`

**Physical setup:**

A gray surface (emissivity `ε`, area `A`) at temperature `T_s` exchanges
thermal radiation with a large enclosure at uniform temperature `T_surr`.

**Governing equation (Stefan-Boltzmann law for gray body):**

```
Q_rad = ε × σ × A × (T_s⁴ − T_surr⁴)    [W]

σ = 5.670374419 × 10⁻⁸  W/(m²·K⁴)   (CODATA 2018 exact)
```

**Benchmark parameters (blackbody test):**

| Parameter | Symbol | Value | Unit |
|-----------|--------|-------|------|
| Emissivity | ε | 1.0 | — |
| Surface area | A | 1.0 | m² |
| Surface temperature | T_s | 400 | K |
| Surroundings temperature | T_surr | 300 | K |

**Exact solution:**

```
Q = 5.670374419×10⁻⁸ × 1.0 × (400⁴ − 300⁴)
  = 5.670374419×10⁻⁸ × (25.6×10⁹ − 8.1×10⁹)
  = 5.670374419×10⁻⁸ × 17.5×10⁹
  ≈ 992.3 W
```

**Acceptance criterion:** `|Q_computed − Q_exact| / Q_exact ≤ 1×10⁻⁹`

**CR-ENG-003 guard test (mandatory):**

Calling `radiation_exchange(40.0, 20.0, 0.9, 1.0)` must raise:
```
ValueError: "CR-ENG-003 ... use kelvin, not °C"
```

This verifies the unit guard catches accidental Celsius input (40°C and 20°C
are realistic ambient temperatures but would be physically unreasonable as kelvin).
Without the guard, the T⁴ term would produce a wildly wrong (negative) result
instead of raising an error.

**Additional tests:**
- T_s = T_surr → Q = 0 (no net flux at thermal equilibrium)
- T_s > T_surr → Q > 0 (surface loses heat)

---

### BM-004 — Combined Convection and Radiation

**Category:** L2 Analytical (every-push CI gate)  
**Module:** `thermal_core/benchmarks/analytical.py :: combined_heat_loss`  
**Test:** `engine/tests/test_benchmarks.py::TestBM004CombinedLoss`

**Physical setup:**

A surface dissipates power `Q` to ambient at `T_amb` via two parallel heat
transfer mechanisms: constant convection coefficient `h_conv` and gray body
radiation with emissivity `ε`.

```
Surface (T_s) ──[h_conv, A]── Ambient (T_amb)
              └──[ε, A]──────┘
                  ↓ Q [W]
```

**Governing equation (iterative, linearised radiation):**

```
Q = (h_conv + h_rad(T_s)) × A × (T_s − T_amb)

h_rad(T_s) = ε × σ × (T_s + T_amb) × (T_s² + T_amb²)
```

This is solved iteratively: initial guess `T_s[0] = T_amb + Q/((h_conv+5)×A)`,
then successive substitution with convergence `|ΔT| < 1×10⁻⁶ K`.

**Benchmark parameters:**

| Parameter | Symbol | Value | Unit |
|-----------|--------|-------|------|
| Heat loss | Q | 500 | W |
| Convection coefficient | h_conv | 5 | W/(m²·K) |
| Emissivity | ε | 0.7 | — |
| Surface area | A | 1.0 | m² |
| Ambient temperature | T_amb | 300 | K |

**Energy balance verification:**

After solving for `T_s`:
```
q_conv = h_conv × A × (T_s − T_amb)
q_rad  = ε × σ × A × (T_s⁴ − T_amb⁴)

|q_conv + q_rad − Q| / Q ≤ 0.01   (1% tolerance)
```

**Acceptance criterion:** Energy balance satisfied to within 1%.

**Physical comparison:**

With ε = 0 (pure convection): `T_s_conv = T_amb + Q/(h_conv × A) = 400 K`

With ε = 0.7: radiation provides additional cooling → `T_s < T_s_conv`

The benchmark verifies `T_s_conv > T_s_combined`, confirming radiation is being
applied in the correct direction.

**Physical insight:** At `T_s ≈ 340 K` and `T_amb = 300 K`, the linearised
`h_rad ≈ 0.7 × 5.67×10⁻⁸ × 640 × 212400 ≈ 5.4 W/(m²·K)` — comparable to
natural convection. This benchmark validates that the solver correctly handles the
regime where radiation and convection are of similar magnitude.

---

## 3. IEC TR 60890 Framework Benchmark (BM-IEC)

**Category:** L3 Framework (every-push CI gate, synthetic coefficients only)  
**Module:** `thermal_core/benchmarks/iec60890.py`  
**Test:** `engine/tests/test_benchmarks.py::TestIEC60890Framework`

### 3.1 Applicability Checks

The IEC TR 60890 empirical method (MODE 1) is only valid for naturally ventilated
enclosures without forced cooling.

**BM-IEC-001:** Natural ventilation only → `is_applicable = True`

**BM-IEC-002 (CR-ENG-006):** Forced ventilation active → `is_applicable = False`

```python
result = check_iec60890_applicability(has_forced_ventilation=True, ...)
assert not result.is_applicable
assert any("CR-ENG-006" in r for r in result.reasons)
```

This test verifies that the IEC TR 60890 method cannot be bypassed for
forced-ventilation enclosures. CR-ENG-006 is non-negotiable.

**BM-IEC-003:** Unknown busbar losses → `is_applicable = False` (total losses
cannot be accurately accounted for without all significant heat sources).

### 3.2 Effective Ventilation Area

The IEC TR 60890 method uses the geometric mean of inlet and outlet areas:

```
A_eff = √(A_in × A_out)
```

**BM-IEC-004:** `effective_ventilation_area_m2(0.04, 0.09) = √(0.0036) = 0.06 m²`

**BM-IEC-005:** `effective_ventilation_area_m2(0.0, 0.09) = 0.0` (no inlet → no flow)

### 3.3 Licensed Coefficient Guard (CR-ENG-002)

**BM-IEC-006:** `IEC60890Coefficients(b=0.0, ...)` must raise:

```
ValueError: "licensed coefficient dataset has not been loaded"
```

The sentinel `b = 0.0` signals that the licensed dataset has not been injected.
The coefficient tables from IEC TR 60890:2022 Annex A are never stored in the
repository. They are imported at runtime by an administrator with a valid licence.

### 3.4 Temperature Rise Formula (Synthetic Coefficients)

The IEC TR 60890 temperature rise formula (using arbitrary synthetic coefficients
for testing — NOT the licensed values):

```
ΔT = b × P^c × (A_eff / A_ref)^d
```

**BM-IEC-007:** With `b=1.0, c=0.5, d=-0.5, A_ref=1.0`:

```
ΔT = 1.0 × 1000^0.5 × (1.0/1.0)^(-0.5) = √1000 ≈ 31.623 K
```

Acceptance: `|ΔT_computed − √1000| / √1000 ≤ 1×10⁻⁶`

### 3.5 Edge Cases

**BM-IEC-008:** Zero effective area (no openings) → `ΔT = 0.0` with a warning issued
(cannot compute temperature rise without ventilation geometry).

**BM-IEC-009:** Negative total power → `ValueError("p_total_w must be ≥ 0")`.

---

## 4. BM-007 — De Vahl Davis Natural Convection Cavity (Periodic)

**Category:** L4 Periodic Physics Verification  
**Pytest mark:** `@pytest.mark.periodic_physics`  
**Run frequency:** Pre-release and when convection correlations change

### 4.1 Problem Description

A square cavity with side `H` contains air at Ra = 10³, 10⁴, 10⁵, 10⁶. The left
wall is maintained at `T_hot`, the right wall at `T_cold`, and the horizontal walls
are adiabatic.

```
         Adiabatic (top)
    ┌──────────────────────┐
    │                      │
T_hot │                      │ T_cold
    │                      │
    └──────────────────────┘
         Adiabatic (bottom)
```

This is the classical benchmark problem for 2D natural convection codes.

### 4.2 Published Reference Values

Source: De Vahl Davis, G. (1983). "Natural convection of air in a square cavity:
A bench mark numerical solution." Int. J. Num. Meth. Fluids, 3, 249–264.

| Ra | Nu_avg (De Vahl Davis) | Nu_avg (Benchmark grid 81×81) |
|----|------------------------|-------------------------------|
| 10³ | 1.118 | 1.117 |
| 10⁴ | 2.243 | 2.238 |
| 10⁵ | 4.519 | 4.509 |
| 10⁶ | 8.800 | 8.817 |

### 4.3 M4 Solver Behaviour for This Benchmark

The M4 zonal solver computes a single mean temperature per compartment and uses
the Churchill-Chu (1975) correlation for Nu on vertical surfaces. For this cavity:

```
Nu = h × H / k_fluid
```

The zonal model cannot resolve the internal temperature field (T hot near left
wall, T cold near right wall, stratification). It gives the *integral* heat
transfer prediction.

### 4.4 Acceptance Criterion

| Ra | Expected M4 result | Acceptance |
|----|-------------------|-----------|
| 10³ | Nu ∈ [0.95, 1.30] | ±15% of 1.118 |
| 10⁴ | Nu ∈ [1.91, 2.58] | ±15% of 2.243 |
| 10⁵ | Nu ∈ [3.84, 5.20] | ±15% of 4.519 |
| 10⁶ | Outside design range | M4 logs warning; no acceptance criterion |

The ±15% tolerance for Ra ≤ 10⁵ reflects the inherent limitation of the
lumped-parameter model for resolving cavity stratification. For the switchboard
application (compartment Ra typically 10⁵–10⁸, near-vertical wall geometry),
the Churchill-Chu correlation captures the dominant heat transfer mechanism.

### 4.5 Rationale for Periodic Classification

Per DR-010 and THERM-VAL-001 §6.3:

> BM-007 requires approximately 120 seconds of CPU time per Ra value on the
> reference hardware. Running it on every push would add ~8 minutes to the CI
> pipeline for a benchmark that is not sensitive to the typical change set.
> It is therefore classified as periodic — mandatory before any release that
> touches convection correlations or the solver iteration algorithm.

---

## 5. Benchmark Result Reporting

All benchmarks use the `BenchmarkResult` dataclass:

```python
@dataclass(frozen=True)
class BenchmarkResult:
    benchmark_id: str           # "BM-001", "BM-IEC-004", etc.
    description: str            # human-readable problem statement
    analytical_value: float     # exact theoretical value
    solver_value: float         # value from the numerical solver
    tolerance: float            # acceptance tolerance (absolute or relative)
    units: str                  # "K", "W", "-", etc.
    passed: bool                # |analytical - solver| <= tolerance

    @property
    def absolute_error(self) -> float: ...

    @property
    def relative_error_percent(self) -> float: ...
```

The `passed` field is explicitly set by the calling code — it is not computed
automatically from `tolerance` vs `absolute_error`. This ensures the benchmark
report faithfully records what the test decided, without silent drift.

---

## 6. Benchmark Summary Table

| ID | Name | Type | Module | Tolerance | CI |
|----|------|------|--------|-----------|----|
| BM-001 | Plane wall conduction | L2 Analytical | `conduction/fourier.py` | 1e-9 K | Every push |
| BM-002 | Newton convection cooling | L2 Analytical | `benchmarks/analytical.py` | 1e-6 K | Every push |
| BM-003 | Gray body radiation | L2 Analytical | `radiation/gray_body.py` | 1e-9 rel | Every push |
| BM-004 | Combined convection+radiation | L2 Iterative | `benchmarks/analytical.py` | 1% energy | Every push |
| BM-IEC | IEC TR 60890 framework | L3 Framework | `benchmarks/iec60890.py` | See §3 | Every push |
| BM-007 | De Vahl Davis cavity | L4 Periodic | `natural_convection/` | ±15% Nu | Pre-release |
