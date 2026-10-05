# M4 Solver Theory

**Document ID:** THERM-THEORY-M4-001  
**Revision:** 0.1  
**Status:** In Progress (M4 Implementation)  
**Date:** 2026-07-21

---

## 1. Scope

This document derives and documents the mathematical foundation of the M4 zonal
(lumped-parameter) thermal solver. Every equation used in production code is listed
here with its reference, dimensional check, and implementation location.

Reference: THERM-EQN-001 (Equations & Correlations, Rev 0.2)

---

## 2. Governing Energy Balance

### 2.1 Lumped-Parameter (Zonal) Assumption

Each compartment is modelled as a single well-mixed air volume at uniform mean
temperature `T_air`. This is the classical lumped-parameter approximation. Its
validity requires:

- Compartment aspect ratio L/H < 5 (otherwise stratification is significant)
- No internal partitions splitting the air volume
- No forced jet creating strong recirculation zones

For the LV switchboard application the compartment geometry is typically
0.3 m × 0.6 m × 2 m (W × D × H), with most heat generated near the front bus,
so the well-mixed assumption introduces an error ≤ 5 K for typical loads
(validated by De Vahl Davis benchmark BM-007, periodic physics verification).

### 2.2 Steady-State Energy Balance

At steady state, heat generated inside a compartment equals heat leaving through
all boundary surfaces:

```
Q_gen = Q_dissipated
```

Where:

```
Q_gen [W] = Σ P_i   (sum of all device/busbar losses in the compartment)

Q_dissipated [W] = UA_total × (T_air - T_amb)
```

And `UA_total` [W/K] is the total conductance from interior air to ambient, summed
over all external surfaces of the compartment:

```
UA_total = Σ_surfaces  UA_surface_i
```

### 2.3 Solving for T_air

Re-arranging the steady-state balance:

```
T_air = T_amb + Q_gen / UA_total          [K]              … (EQ-SOLVE-001)
```

This is the core solver equation. Since `UA_total` is a function of `T_air` (through
temperature-dependent convection and radiation coefficients), EQ-SOLVE-001 is solved
iteratively.

---

## 3. Surface Conductance

Each external surface contributes a series thermal resistance chain:

```
Interior air  →  [h_int_conv]  →  Surface (inside face)
              →  [R_wall]      →  Surface (outside face)
              →  [h_ext_conv ∥ h_rad]  →  Ambient
```

The surface conductance (UA per surface) for a surface of area `A` [m²] is:

```
UA_surface = 1 / (R_int + R_wall + R_ext)                  … (EQ-SURF-001)

R_int  = 1 / (h_int × A)       [K/W]   internal convection resistance
R_wall = L / (k × A)           [K/W]   wall conduction resistance (Fourier)
R_ext  = 1 / ((h_ext + h_rad) × A)  [K/W]  external convection + radiation
```

Dimensional check (SI):
- `h` [W/(m²·K)], `A` [m²] → `h×A` [W/K] → `1/(h×A)` [K/W] ✓
- `L` [m], `k` [W/(m·K)], `A` [m²] → `L/(k×A)` [K/W] ✓

---

## 4. Natural Convection Correlations

### 4.1 Rayleigh Number

```
Ra = g × β × |T_s - T_f| × L³ / (ν × α)                  … (EQ-RA-001)
```

Where:
- `g = 9.80665 m/s²` — standard gravity
- `β = 1/T_film [1/K]` — thermal expansion coefficient (ideal gas)
- `T_film = (T_s + T_f) / 2 [K]` — film temperature
- `ν = μ/ρ [m²/s]` — kinematic viscosity
- `α = k/(ρ×Cp) [m²/s]` — thermal diffusivity
- `L [m]` — characteristic length

Equivalently using Prandtl number Pr = ν/α = μ×Cp/k:

```
Ra = Gr × Pr = (g × β × |ΔT| × L³ / ν²) × Pr             … (EQ-RA-002)
```

Dimensional check: [m/s²][1/K][K][m³]/[m²/s][m²/s] = dimensionless ✓

### 4.2 Vertical Plate — Churchill-Chu (1975)

Valid for all Ra in range [10⁻¹, 10¹²]:

```
Nu = { 0.825 + 0.387 × Ra^(1/6) / [1 + (0.492/Pr)^(9/16)]^(8/27) }²
                                                              … (EQ-NC-001)
```

This single correlation spans laminar and turbulent regimes without discontinuity.

Reference: Churchill, S.W. and Chu, H.H.S. (1975). "Correlating equations for
laminar and turbulent free convection from a vertical plate." Int. J. Heat Mass
Transfer 18, 1323–1329.

Floor: `Nu ≥ 1.0` (conduction limit; prevents h = 0 in fully suppressed convection).

### 4.3 Horizontal Plate — McAdams (1954)

**Heated face up (or cooled face down):**
```
Nu = 0.54 × Ra^(1/4)     for 10⁴ ≤ Ra < 10⁷   (laminar)  … (EQ-NC-002)
Nu = 0.15 × Ra^(1/3)     for Ra ≥ 10⁷          (turbulent) … (EQ-NC-003)
```

**Heated face down (or cooled face up):**
```
Nu = 0.27 × Ra^(1/4)     for 10⁵ ≤ Ra < 10¹¹              … (EQ-NC-004)
```

### 4.4 Convection Coefficient

From Nusselt number to heat transfer coefficient:

```
h = Nu × k_fluid / L     [W/(m²·K)]                         … (EQ-NC-005)
```

All fluid properties evaluated at film temperature `T_film = (T_s + T_f)/2`.

---

## 5. Radiation

### 5.1 Gray Body Stefan-Boltzmann Law

Net radiation heat flux from a gray surface to its surroundings:

```
q_rad = ε × σ × (T_s⁴ - T_surr⁴)     [W/m²]               … (EQ-RAD-001)
```

Stefan-Boltzmann constant:
```
σ = 5.670374419 × 10⁻⁸  W/(m²·K⁴)   (CODATA 2018 exact)
```

**CR-ENG-003 requirement:** All radiation computations use absolute temperature in
kelvin. Input guard rejects T < 100 K with `ValueError("CR-ENG-003")` to catch
accidental Celsius usage.

### 5.2 Linearised Radiation Coefficient

Factorising `T_s⁴ - T_surr⁴ = (T_s - T_surr)(T_s + T_surr)(T_s² + T_surr²)`:

```
h_rad = ε × σ × (T_s + T_surr) × (T_s² + T_surr²)   [W/(m²·K)]
                                                              … (EQ-RAD-002)
```

This is an **exact factorisation** (not an approximation). It allows radiation to
enter the linear energy-balance matrix at each iteration step:

```
Q_rad = h_rad × A × (T_s - T_surr)    [W]                   … (EQ-RAD-003)
```

Dimensional check: [W/(m²·K)][m²][K] = [W] ✓

### 5.3 Effective Emissivity (Two Surfaces)

For radiation exchange between two infinite parallel plates with emissivities ε₁, ε₂:

```
1/ε_eff = 1/ε₁ + 1/ε₂ - 1                                  … (EQ-RAD-004)
```

Used for enclosure interior surfaces where both emissivities are known. M4 MVP
applies this only when both surfaces are modelled explicitly.

---

## 6. Wall Conduction

Fourier's law for steady-state planar wall conduction:

```
R_wall = L / (k × A)     [K/W]                              … (EQ-COND-001)
UA_wall = k × A / L      [W/K]                              … (EQ-COND-002)
```

Composite wall (series resistances):

```
R_total = Σ (Lᵢ / (kᵢ × A))                                … (EQ-COND-003)
```

Contact resistance:

```
R_contact = r'' / A                                          … (EQ-COND-004)
```

where `r''` [m²·K/W] is the contact thermal resistance per unit area.

Dimensional check: [m]/([W/(m·K)][m²]) = [K/W] ✓

---

## 7. Air Properties

### 7.1 Density (Ideal Gas)

```
ρ(T, P) = P / (R_air × T)     [kg/m³]                      … (EQ-AIR-001)

R_air = 287.058  J/(kg·K)
```

Dimensional check: [Pa] / ([J/(kg·K)] × [K]) = [N/m²] / [J/kg] = [kg/m³] ✓

### 7.2 Dynamic Viscosity (Sutherland's Law)

```
μ(T) = μ_ref × (T/T_ref)^(3/2) × (T_ref + S) / (T + S)   … (EQ-AIR-002)

μ_ref = 1.716 × 10⁻⁵  Pa·s   (at T_ref = 273.15 K)
S     = 110.4  K               (Sutherland constant for air)
```

Valid range: 170 K – 1900 K. Error < 2% for temperatures 200–600 K.

### 7.3 Thermal Conductivity (Polynomial Fit)

NIST-fitted polynomial (3rd order) valid 200–600 K:

```
k(T) = a₀ + a₁T + a₂T² + a₃T³     [W/(m·K)]               … (EQ-AIR-003)

a₀ = -4.3 × 10⁻⁴
a₁ =  1.0 × 10⁻⁴
a₂ = -3.7 × 10⁻⁸
a₃ =  0.0
```

Gives k(293.15 K) ≈ 0.02571 W/(m·K), Pr ≈ 0.71 at 20°C.

### 7.4 Specific Heat (Polynomial Fit)

```
Cp(T) = b₀ + b₁T + b₂T² + b₃T³    [J/(kg·K)]              … (EQ-AIR-004)

b₀ =  1.048 × 10³
b₁ = -3.82 × 10⁻¹
b₂ =  9.45 × 10⁻⁴
b₃ = -5.49 × 10⁻⁷
```

### 7.5 Thermal Diffusivity and Prandtl Number

```
α(T) = k(T) / (ρ(T) × Cp(T))       [m²/s]                  … (EQ-AIR-005)
Pr(T) = μ(T) × Cp(T) / k(T)        [-]                     … (EQ-AIR-006)
```

---

## 8. Airflow Network

### 8.1 Stack Effect Pressure (Buoyancy Driving Force)

Natural ventilation is driven by the density difference between hot enclosure air
and cooler ambient air. The buoyancy (stack effect) pressure difference is:

```
ΔP_stack = ρ_amb × g × H × (T_air - T_amb) / T_avg   [Pa]  … (EQ-AFN-001)

T_avg = (T_air + T_amb) / 2   [K]
g     = 9.80665   m/s²
H     = effective stack height [m]
```

This follows from the hydrostatic pressure difference between two columns of air at
different temperatures. The ideal-gas approximation Δρ/ρ = ΔT/T_avg is used
(first-order Taylor expansion of ρ = P/(R×T)).

Dimensional check: [kg/m³][m/s²][m][K/K] = [kg/(m²·s²)] = [Pa] ✓

### 8.2 Orifice Flow (Bernoulli + Discharge Coefficient)

Flow through an opening (inlet grille, cable entry, gap):

```
Q = Cd × A × √(2|ΔP|/ρ)     [m³/s]                         … (EQ-AFN-002)
```

Where:
- `Cd` [-] — discharge coefficient (typically 0.6 for sharp-edged openings)
- `A` [m²] — free area of the opening
- `ΔP` [Pa] — pressure difference across the opening

Dimensional check: [m²] × √([Pa]/[kg/m³]) = [m²] × [m/s] = [m³/s] ✓

Mass flow rate:

```
ṁ = ρ × Q = ρ × Cd × A × √(2|ΔP|/ρ)     [kg/s]            … (EQ-AFN-003)
```

### 8.3 Natural Ventilation Flow (Single-Stack Model)

For an enclosure with one inlet (area A_in, height z_in) and one outlet
(area A_out, height z_out), the effective ventilation area is:

```
A_eff = √(A_in × A_out)     [m²]                            … (EQ-AFN-004)
```

The net buoyancy pressure is:

```
ΔP = ρ_amb × g × Δz × (T_air - T_amb) / T_avg             … (EQ-AFN-005)

Δz = z_out - z_in     [m]   (positive for outlet above inlet)
```

Volumetric flow:

```
Q = Cd × A_eff × √(2|ΔP|/ρ_amb)     [m³/s]                 … (EQ-AFN-006)
```

---

## 9. Iterative Solution Algorithm

### 9.1 Successive Substitution with Relaxation

The nonlinear system EQ-SOLVE-001 is solved by successive substitution (Picard
iteration) with under-relaxation for stability:

```
Algorithm ZonalSolver:

1. Initialise:
   T_air[0] = T_amb + 30  [K]   (warm start for natural convection)

2. For iteration n = 0, 1, …, max_iterations − 1:

   a. Compute UA_total(T_air[n]) using current temperatures
      (natural convection h depends on T_air, surface T, and T_amb;
       radiation h_rad depends on T_air and T_amb)

   b. Compute T_air_solved = T_amb + Q_gen / UA_total

   c. Apply relaxation:
      T_air[n+1] = ω × T_air_solved + (1 − ω) × T_air[n]

   d. Check convergence:
      Δ = |T_air[n+1] − T_air[n]|
      if Δ < tolerance_k → return CONVERGED

3. Return NON_CONVERGED (CR-ENG-005)
```

### 9.2 Relaxation Factor

Default `ω = 0.7`. Under-relaxation (ω < 1) damps oscillations arising from the
strong nonlinearity of radiation (`T⁴`) and natural convection (`Ra^(1/4..1/3)`).

The relaxation factor is user-configurable in `SolverSettings`. Values outside
(0, 1] are rejected by `SolverSettings.__post_init__`.

### 9.3 Convergence Criterion

Convergence is declared when the maximum temperature change per iteration across
all compartments is below the tolerance:

```
max_i |T_air[n+1][i] − T_air[n][i]| < tolerance_k          … (EQ-CONV-001)
```

Default `tolerance_k = 0.01 K`. This corresponds to approximately 0.003% error
relative to typical temperature rises of 30–50 K.

### 9.4 Energy Balance Audit

After convergence, the energy balance is computed:

```
ε_energy = |Q_in − Q_out| / Q_in × 100   [%]               … (EQ-EB-001)

Q_in  = total_heat_generation_w
Q_out = Σ_surfaces UA_surface × (T_air − T_amb)
```

`ε_energy > 1%` triggers a `SolverWarning` (code `ENERGY_BALANCE_ERROR`).

---

## 10. Dimensional Analysis Summary

| Equation | SI Check | Reference |
|----------|----------|-----------|
| T_air = T_amb + Q/UA | [K] + [W]/[W/K] = [K] ✓ | EQ-SOLVE-001 |
| R = L/(kA) | [m]/([W/m·K][m²]) = [K/W] ✓ | EQ-COND-001 |
| Ra = gβΔTL³/(να) | dimensionless ✓ | EQ-RA-001 |
| h = Nu×k/L | [W/m²·K] ✓ | EQ-NC-005 |
| q_rad = εσ(T_s⁴−T_surr⁴) | [W/m²] ✓ | EQ-RAD-001 |
| h_rad = εσ(T_s+T_surr)(T_s²+T_surr²) | [W/(m²·K)] ✓ | EQ-RAD-002 |
| Q_rad = h_rad×A×ΔT | [W] ✓ | EQ-RAD-003 |
| ΔP_stack = ρgHΔT/T_avg | [Pa] ✓ | EQ-AFN-001 |
| Q_orifice = Cd×A×√(2ΔP/ρ) | [m³/s] ✓ | EQ-AFN-002 |
| ρ(T) = P/(R_air×T) | [kg/m³] ✓ | EQ-AIR-001 |

---

## 11. Known Limitations and Assumptions

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| Single T per compartment | ±5 K vs. CFD for typical loads | Acceptable for MODE 1/2 screening |
| External surfaces to ambient only | Internal partitions treated as adiabatic | Documented in M0-06 |
| Constant wall k in MVP | ±1% for steel panels | k(T) interface ready for M5 |
| No inter-compartment radiation | Underestimates heat transfer through glass doors | Warning triggered if ε > 0.3 and compartments share open boundary |
| Well-mixed assumption invalid for H > 2.5 m | Stratification > 10 K possible in tall switchboards | VAL-007 warns if compartment H/W > 4 |
| No transient analysis | Cannot compute thermal time constant | Deferred to M5 |

---

## 12. Equation Reference Index

| Code | Name | Module |
|------|------|--------|
| EQ-SOLVE-001 | Lumped temperature solve | `solver/iterative.py` |
| EQ-SURF-001 | Surface conductance | `solver/iterative.py` |
| EQ-COND-001 | Wall resistance | `conduction/fourier.py` |
| EQ-COND-002 | Wall conductance | `conduction/fourier.py` |
| EQ-COND-003 | Composite wall resistance | `conduction/fourier.py` |
| EQ-COND-004 | Contact resistance | `conduction/fourier.py` |
| EQ-RA-001 | Rayleigh number | `natural_convection/churchill_chu.py` |
| EQ-RA-002 | Rayleigh via Grashof × Pr | `natural_convection/churchill_chu.py` |
| EQ-NC-001 | Churchill-Chu vertical plate | `natural_convection/churchill_chu.py` |
| EQ-NC-002 | McAdams horizontal up (laminar) | `natural_convection/churchill_chu.py` |
| EQ-NC-003 | McAdams horizontal up (turbulent) | `natural_convection/churchill_chu.py` |
| EQ-NC-004 | McAdams horizontal down | `natural_convection/churchill_chu.py` |
| EQ-NC-005 | h from Nu | `natural_convection/churchill_chu.py` |
| EQ-RAD-001 | Gray body heat flux | `radiation/gray_body.py` |
| EQ-RAD-002 | Linearised h_rad | `radiation/gray_body.py` |
| EQ-RAD-003 | Radiation power | `radiation/gray_body.py` |
| EQ-RAD-004 | Effective emissivity | `radiation/gray_body.py` |
| EQ-AIR-001 | Air density (ideal gas) | `materials/air_properties.py` |
| EQ-AIR-002 | Sutherland viscosity | `materials/air_properties.py` |
| EQ-AIR-003 | Thermal conductivity polynomial | `materials/air_properties.py` |
| EQ-AIR-004 | Specific heat polynomial | `materials/air_properties.py` |
| EQ-AIR-005 | Thermal diffusivity | `materials/air_properties.py` |
| EQ-AIR-006 | Prandtl number | `materials/air_properties.py` |
| EQ-AFN-001 | Stack effect pressure | `airflow/network.py` |
| EQ-AFN-002 | Orifice flow | `airflow/network.py` |
| EQ-AFN-003 | Mass flow rate | `airflow/network.py` |
| EQ-AFN-004 | Effective ventilation area | `airflow/network.py` |
| EQ-AFN-005 | Net buoyancy pressure | `airflow/network.py` |
| EQ-AFN-006 | Natural ventilation flow | `airflow/network.py` |
| EQ-CONV-001 | Convergence criterion | `solver/iterative.py` |
| EQ-EB-001 | Energy balance error | `diagnostics/diagnostics.py` |
