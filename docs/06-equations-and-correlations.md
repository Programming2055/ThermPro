# Equations and Correlations — LV Switchboard Thermal Digital Twin

**Document ID:** THERM-EQN-001  
**Revision:** 0.1 (Draft for Engineering Review)  
**Date:** 2026-07-03  
**Status:** Pending Approval

---

## 1. Purpose

This document catalogues every governing equation and empirical correlation used in
ThermPro, together with the variable definitions, units, dimensional checks, validity
ranges, and literature references. No equation may be implemented in the solver without
an entry in this document.

---

## 2. Notation and Units

All equations use SI units internally. Display units are configurable.

| Symbol | Name | SI Unit | Notes |
|--------|------|---------|-------|
| T | Absolute temperature | K | T [K] = θ [°C] + 273.15 |
| θ | Temperature in degrees Celsius | °C | Display unit |
| Δθ | Temperature rise above reference | K or °C | Numerically equal |
| Q | Heat transfer rate / power | W | |
| P | Electrical power loss | W | |
| G | Thermal conductance | W/K | |
| R_th | Thermal resistance | K/W | R_th = 1/G |
| k | Thermal conductivity | W/(m·K) | |
| A | Area | m² | |
| L | Length / thickness | m | |
| h | Convective heat transfer coefficient | W/(m²·K) | |
| ε | Emissivity (surface) | — | 0 ≤ ε ≤ 1 |
| ε_eff | Effective emissivity (two-surface) | — | |
| σ | Stefan-Boltzmann constant | W/(m²·K⁴) | 5.670374419 × 10⁻⁸ |
| Nu | Nusselt number | — | Nu = h L / λ_f |
| Ra | Rayleigh number | — | Ra = Gr · Pr |
| Gr | Grashof number | — | Gr = g β ΔT L³ / ν² |
| Pr | Prandtl number | — | Pr = μ cp / λ_f |
| Re | Reynolds number | — | Re = ρ v L / μ |
| g | Gravitational acceleration | m/s² | 9.80665 |
| β | Volumetric thermal expansion coefficient | 1/K | β = 1/T_film for ideal gas |
| ν | Kinematic viscosity of air | m²/s | |
| μ | Dynamic viscosity of air | Pa·s | |
| λ_f | Thermal conductivity of air | W/(m·K) | |
| cp | Specific heat capacity of air | J/(kg·K) | |
| ρ | Density of air | kg/m³ | |
| ρ_ref | Density of air at reference conditions | kg/m³ | |
| I | RMS current | A | |
| I_n | Rated current | A | |
| R | Electrical resistance | Ω | |
| R_ref | Resistance at reference temperature | Ω | |
| α | Temperature coefficient of resistance | 1/K | |
| T_ref | Reference temperature for resistance | K | typically 293.15 K (20 °C) |
| ṁ | Mass flow rate | kg/s | |
| Q_vol | Volumetric flow rate | m³/s | |
| v | Velocity | m/s | |
| ΔP | Pressure difference | Pa | |
| Cd | Discharge coefficient | — | typically 0.6–0.65 for sharp edges |
| K | Loss coefficient | — | pressure loss = K ρ v² / 2 |
| F_h | Power loss fraction (harmonic) | — | |
| K_AC | AC resistance multiplier | — | skin + proximity effect |
| η_fan | Fan efficiency | — | |
| Δθ_mid | Mid-height temperature rise | K | IEC TR 60890 output |
| Δθ_top | Top temperature rise above ambient | K | IEC TR 60890 output |
| P_tot | Total internal power dissipation | W | |
| A_e | Effective cooling surface area | m² | IEC TR 60890 |
| c_0 | Enclosure constant | K/W^n | IEC TR 60890 |

---

## 3. Solid Conduction

### 3.1 Fourier Conduction (Simple Path)

```
Q_cond = G_cond · (T_hot − T_cold)          [W]

G_cond = k · A / L                           [W/K]
```

**Dimensional check:**

```
G_cond: [W/(m·K)] · [m²] / [m] = [W/K]  ✓
Q_cond: [W/K] · [K] = [W]               ✓
```

**Applicability:** One-dimensional steady-state heat flow through a uniform slab. For
composite walls, conductances are assembled in series: 1/G_total = Σ(1/G_i).

**Thermal contact resistance** is included as R_contact [K/W] added in series at interfaces.

### 3.2 Temperature-Dependent Conductivity

For materials where k varies with temperature:

```
k(T) = k_ref [1 + β_k (T − T_ref)]         [W/(m·K)]
```

k is evaluated at the mean temperature of the path.

---

## 4. Joule (Resistive) Losses

### 4.1 Temperature-Dependent Resistance

```
R(T) = R_ref [1 + α (T − T_ref)]            [Ω]
```

**Dimensional check:**  
`[Ω] · [1 + (1/K) · K] = [Ω]  ✓`

**Values for copper:**  
`R_ref` at 20 °C; `α` = 3.93 × 10⁻³ K⁻¹

**Values for aluminium:**  
`R_ref` at 20 °C; `α` = 4.03 × 10⁻³ K⁻¹

### 4.2 Joule Loss

```
P = I_rms² · R(T)                            [W]
```

**Dimensional check:**  
`[A²] · [Ω] = [W]  ✓`

### 4.3 Harmonic Current Multiplier

For conductors carrying non-sinusoidal current, the RMS current including harmonics:

```
I_rms = sqrt(I_1² + I_2² + I_3² + … + I_n²)  [A]
```

Equivalently, using total harmonic distortion (THD):

```
I_rms = I_1 · sqrt(1 + THD²)                [A]
```

### 4.4 AC Resistance Multiplier

```
R_AC = K_AC · R_DC(T)                        [Ω]
```

K_AC accounts for skin effect and proximity effect. For busbars, K_AC is obtained from
manufacturer data or IEC 60287. K_AC ≥ 1.0.

### 4.5 Joint and Terminal Losses

For each joint or terminal connection:

```
P_joint = I² · R_joint                       [W]
```

R_joint is taken from manufacturer data or standard contact resistance tables (user-provided dataset required).

### 4.6 Per-Segment Busbar Loss

For a busbar segment of length L_seg, cross-sectional area A_cs:

```
R_seg(T) = (ρ_e(T) · L_seg) / A_cs          [Ω]

ρ_e(T) = ρ_e_ref [1 + α (T − T_ref)]        [Ω·m]

P_seg = I² · R_seg(T)                        [W]
```

**Dimensional check:**  
`[Ω·m] · [m] / [m²] = [Ω]  ✓`

---

## 5. Device Heat Loss

### 5.1 Direct Input

```
P_device = P_user_entered                     [W]
```

Data confidence = MANUFACTURER or MEASURED.

### 5.2 Fixed Plus Load-Dependent Loss

```
P_device(I) = P_fixed + P_variable · (I / I_n)²  [W]
```

**Dimensional check:**  
`[W] + [W] · ([A]/[A])² = [W]  ✓`

P_fixed and P_variable are from manufacturer data.

### 5.3 Quadratic Approximation

When only rated loss P_n at I_n is available:

```
P_device(I) = P_n · (I / I_n)²               [W]
```

This is a simplification. The software shall flag it as ASSUMED when manufacturer
load-loss data are absent.

### 5.4 Derating Iteration

Device derating factor f_d (0 < f_d ≤ 1) is applied to the rated current:

```
I_permissible = f_d(θ_ambient_local) · I_n   [A]
```

f_d(θ) is interpolated from the manufacturer's derating curve. When the derating curve
is absent, a linear approximation with explicit ASSUMED flag is used:

```
f_d(θ) ≈ 1 − k_dr · (θ − θ_ref_device)      [—]
```

k_dr is a gradient taken from IEC 61439 guidelines or entered by the user.

---

## 6. Natural Convection

### 6.1 Rayleigh and Related Numbers

```
Gr = g · β · |ΔT| · L_c³ / ν²              [—]
Ra = Gr · Pr                                 [—]
Pr = μ · cp / λ_f                           [—]
```

Air properties (ν, λ_f, cp, Pr) are evaluated at the film temperature:

```
T_film = (T_surface + T_ambient) / 2         [K]
```

Air property polynomials are stored in the materials library, calibrated against published
data for air from 250 K to 400 K.

**Dimensional check for Gr:**  
`[m/s²] · [1/K] · [K] · [m³] / [m²/s]² = [m⁴/s²] / [m⁴/s²] = [—]  ✓`

### 6.2 Vertical Plate (Enclosure Side Walls, Internal Partitions)

Churchill-Chu correlation (Churchill and Chu, 1975):

```
Nu_L = {0.825 + 0.387 · [Ra_L / f(Pr)]^(1/6)}²

f(Pr) = [1 + (0.492/Pr)^(9/16)]^(16/9)
```

Valid for: 10⁻¹ ≤ Ra_L ≤ 10¹²  
Characteristic length: L_c = plate height

### 6.3 Upward-Facing Horizontal Surface (Enclosure Ceiling, Top of Devices)

Morgan / McAdams correlation:

```
Laminar (10⁴ ≤ Ra ≤ 10⁷):   Nu = 0.54 · Ra^(1/4)
Turbulent (10⁷ ≤ Ra ≤ 10¹¹): Nu = 0.15 · Ra^(1/3)
```

Characteristic length: L_c = A_surface / Perimeter

### 6.4 Downward-Facing Horizontal Surface (Enclosure Floor, Underside of Shelves)

```
Laminar (10⁵ ≤ Ra ≤ 10¹¹):  Nu = 0.27 · Ra^(1/4)
```

### 6.5 Convection Coefficient from Nusselt Number

```
h = Nu · λ_f / L_c                           [W/(m²·K)]
```

**Dimensional check:**  
`[—] · [W/(m·K)] / [m] = [W/(m²·K)]  ✓`

### 6.6 Convective Heat Transfer from Surface

```
Q_conv = h · A · (T_surface − T_air)         [W]
```

---

## 7. Forced Convection

### 7.1 Internal Duct / Channel Flow

Dittus-Boelter equation (turbulent, Re > 10 000):

```
Nu = 0.023 · Re^0.8 · Pr^n                  [—]

n = 0.4 (heating of fluid),  n = 0.3 (cooling of fluid)
```

Entry-length correction applied for L/D < 60 per Sieder-Tate or Gnielinski.

### 7.2 Gnielinski (Preferred, valid 0.5 ≤ Pr ≤ 2000, 3000 ≤ Re ≤ 5×10⁶):

```
f = (0.790 ln(Re) − 1.64)^(−2)

Nu = (f/8)(Re − 1000) Pr / [1 + 12.7 √(f/8) (Pr^(2/3) − 1)]
```

### 7.3 Reynolds Number

```
Re = ρ · v · L_c / μ                         [—]
```

**Dimensional check:**  
`[kg/m³] · [m/s] · [m] / [Pa·s] = [kg/(m²·s)] / [kg/(m·s²) · s] = [—]  ✓`

---

## 8. Thermal Radiation

### 8.1 Fundamental Equation

```
Q_rad = ε_eff · σ · A · (T_s⁴ − T_sur⁴)    [W]
```

**CRITICAL:** T_s and T_sur MUST be in kelvin.

**Dimensional check:**  
`[—] · [W/(m²·K⁴)] · [m²] · [K⁴] = [W]  ✓`

### 8.2 Effective Emissivity (Two Grey Surfaces)

For two parallel flat surfaces with areas A_1 ≈ A_2:

```
ε_eff = 1 / (1/ε_1 + 1/ε_2 − 1)            [—]
```

For a small body in a large enclosure:

```
ε_eff = ε_1                                  [—]
```

### 8.3 Linearised Radiation Coefficient

To allow linear matrix assembly, radiation is linearised:

```
Q_rad = h_r · A · (T_s − T_sur)             [W]

h_r = ε_eff · σ · (T_s + T_sur)(T_s² + T_sur²)  [W/(m²·K)]
```

h_r is updated at each iteration. The linearisation converges quickly for small ΔT but
must be iterated for large temperature differences.

**Dimensional check:**  
`[—] · [W/(m²·K⁴)] · [K] · [K²] = [W/(m²·K)]  ✓`

---

## 9. Air-Mass Transport

### 9.1 Convective Air Transport Between Cells

```
Q_air = ṁ · cp · (T_i − T_j)               [W]
```

**Dimensional check:**  
`[kg/s] · [J/(kg·K)] · [K] = [W]  ✓`

### 9.2 Mass Flow Rate from Velocity and Area

```
ṁ = ρ · v · A_eff                           [kg/s]
```

**Dimensional check:**  
`[kg/m³] · [m/s] · [m²] = [kg/s]  ✓`

### 9.3 Mass Conservation at Each Air Cell

```
Σ ṁ_in − Σ ṁ_out = 0                       [kg/s]
```

This must hold to within the specified mass-imbalance tolerance at convergence.

---

## 10. Airflow Network

### 10.1 Opening (Orifice) Flow

```
ṁ = Cd · A_free · sqrt(2 · |ΔP| · ρ)       [kg/s]
Q_vol = ṁ / ρ                               [m³/s]
```

Direction is determined by the sign of ΔP.

**Dimensional check:**  
`[—] · [m²] · sqrt([Pa] · [kg/m³]) = [m²] · sqrt([kg/(m·s²)] · [kg/m³])`  
`= [m²] · [kg/(m²·s)] = [kg/s]  ✓`

### 10.2 Duct / Grille Resistance

```
ΔP = K · ρ · v² / 2                         [Pa]

Equivalently: ΔP = (K · ρ) / (2 · A_eff²) · Q_vol²  [Pa]
```

**Dimensional check:**  
`[—] · [kg/m³] · [m/s]² = [kg/(m·s²)] = [Pa]  ✓`

### 10.3 Filter Pressure Drop

```
ΔP_filter = C_f1 · Q_vol + C_f2 · Q_vol²   [Pa]
```

C_f1 and C_f2 are from the filter manufacturer's pressure-drop curve (mandatory input).
The quadratic term dominates at high flows.

### 10.4 Fan Pressure-Flow Curve

Fan is represented by a tabulated P-Q curve interpolated using cubic spline or
piecewise-linear interpolation:

```
ΔP_fan = f_interp(Q_vol, speed)              [Pa]
```

Fan operating point is found at the intersection of the fan curve and the system
resistance curve (equal-pressure node iteration).

**Affinity law scaling (must be labelled when used):**

```
Q_2 / Q_1 = n_2 / n_1                       [—]
ΔP_2 / ΔP_1 = (n_2 / n_1)²                 [—]
P_fan_2 / P_fan_1 = (n_2 / n_1)³           [—]
```

Affinity laws are valid only for geometrically similar operating points. They shall not
be applied outside the original curve's measured speed range.

### 10.5 Buoyancy Stack Pressure

Natural convection pressure driving force (stack effect):

```
ΔP_stack = ρ_ref · g · H · (ΔT / T_ref)    [Pa]
```

Or equivalently using ideal-gas density variation:

```
ΔP_stack = (ρ_cold − ρ_hot) · g · H        [Pa]

ρ = P_atm / (R_specific · T)                [kg/m³]

R_specific_air = 287.058 J/(kg·K)
```

H is the vertical distance between inlet and outlet centroids.

**Dimensional check:**  
`[kg/m³] · [m/s²] · [m] = [kg/(m²·s²)] = [Pa]  ✓`

---

## 11. IEC TR 60890 Calculation Equations

The following is the structural form of the calculation. Numerical coefficients MUST come
from a licensed administrator-imported dataset (see THERM-STD-001 §5).

### 11.1 Total Internal Power Loss

```
P_tot = Σ P_i                                [W]
```

Includes all device losses, busbar losses, conductor losses, and fan motor losses
dissipated inside the enclosure.

### 11.2 Effective Cooling Surface

```
A_e = Σ (b_j · A_j)                         [m²]
```

where b_j is the installation factor for surface j (top, sides, front, rear) from the
licensed dataset, and A_j is the actual area of that surface.

### 11.3 Mid-Height Temperature Rise

```
Δθ_mid = c_0 · (P_tot / A_e)^n             [K]
```

c_0 and n are from the licensed coefficient dataset.

### 11.4 Top Temperature Rise

```
Δθ_top = d · Δθ_mid                         [K]
```

d is the temperature-distribution factor from the licensed dataset.

### 11.5 Temperature at Height y

```
Δθ(y) = Δθ_mid · f(y / H_enc)              [K]
```

f is the height-interpolation function from the licensed dataset.

---

## 12. Thermal Matrix — Node Balance

For each air-mass node i in the nodal thermal network:

```
Σ_j G_ij · (T_j − T_i) + Q_i = 0           [W]
```

Where:
- G_ij = conductance between node i and node j (includes conduction, convection, radiation, air transport)
- Q_i = net heat source at node i (positive = heat added)

In matrix form:

```
G · T = Q_ext                                (sparse linear system)
```

G is the thermal conductance matrix (symmetric, positive semi-definite for well-posed problems).  
T is the vector of unknown node temperatures.  
Q_ext is the vector of external heat sources.

---

## 13. Air Property Polynomials

Air properties are evaluated at the local film temperature T_film. The following
polynomial forms are used (coefficients calibrated for 250 K ≤ T ≤ 450 K):

```
ρ(T) = P_atm / (287.058 · T)                [kg/m³]  (ideal gas)

μ(T) = μ_ref · (T / T_ref)^0.7              [Pa·s]   (power law)

λ_f(T) = λ_ref · (T / T_ref)^0.85          [W/(m·K)] (power law)

cp ≈ 1007 J/(kg·K)                          [J/(kg·K)] (approximately constant 250–450 K)

Pr ≈ 0.713 − 0.00018 · (T − 300)           [—]
```

Reference values at 300 K:  
μ_ref = 1.846 × 10⁻⁵ Pa·s  
λ_ref = 0.02624 W/(m·K)  
ρ_ref = 1.177 kg/m³ (at 1 atm)

---

## 14. Transient Node Balance (Future Implementation)

The transient energy balance for node i:

```
C_i · dT_i/dt = Q_i + Σ_j G_ij · (T_j − T_i)   [W]

C_i = m_i · cp_i                                  [J/K]
```

Discretised using implicit Euler (unconditionally stable):

```
C_i · (T_i^(n+1) − T_i^n) / Δt = Q_i^(n+1) + Σ_j G_ij · (T_j^(n+1) − T_i^(n+1))
```

This requires solving the full matrix system at each time step. Δt is selected to resolve
the fastest thermal time constant of interest (typically 1–60 seconds for device
temperature, minutes for air cells, hours for heavy busbars).

---

## 15. Dimensional Check Summary

| Equation | LHS Unit | RHS Unit | Status |
|----------|----------|----------|--------|
| Q_cond = G · ΔT | W | (W/K) · K | ✓ |
| G_cond = k A / L | W/K | (W/(m·K)) · m² / m | ✓ |
| R(T) = R_ref[1+α(T−T_ref)] | Ω | Ω · [1+(1/K)·K] | ✓ |
| P = I² R | W | A² · Ω | ✓ |
| Gr = g β ΔT L³/ν² | — | (m/s²)(1/K)(K)(m³)/(m²/s)² | ✓ |
| h = Nu λ_f / L_c | W/(m²·K) | (—)(W/(m·K))/(m) | ✓ |
| Q_conv = h A ΔT | W | (W/(m²·K)) m² K | ✓ |
| Q_rad = ε σ A ΔT⁴ | W | (—)(W/(m²·K⁴)) m² K⁴ | ✓ |
| Q_air = ṁ cp ΔT | W | (kg/s)(J/(kg·K)) K | ✓ |
| ṁ = ρ v A | kg/s | (kg/m³)(m/s)(m²) | ✓ |
| ṁ_orifice = Cd A √(2|ΔP|ρ) | kg/s | m² √(Pa·kg/m³) | ✓ |
| ΔP_duct = K ρ v²/2 | Pa | (—)(kg/m³)(m/s)² | ✓ |
| ΔP_stack = ρ g H | Pa | (kg/m³)(m/s²)(m) | ✓ |
| G·T = Q | W | (W/K)·K | ✓ |
| C dT/dt = Q + Σ G ΔT | W | (J/K)(K/s) = W | ✓ |

---

## 16. Equation Version Control

Every change to a correlation or equation in this document must increment the document
revision and be recorded in the change log. Calculation runs reference the equation
document revision.

---

*End of THERM-EQN-001*
