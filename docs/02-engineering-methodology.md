# Engineering Methodology — LV Switchboard Thermal Digital Twin

**Document ID:** THERM-METH-001  
**Revision:** 0.1 (Draft for Engineering Review)  
**Date:** 2026-07-03  
**Status:** Pending Approval

---

## 1. Purpose and Scope

This document defines the engineering methodology governing all thermal calculations
performed by ThermPro. It specifies the governing physics, the complete variable
definitions, the calculation flow, the numerical method, the convergence requirements,
the boundary conditions, the data provenance classification, and the known limitations.

This document is the primary engineering reference for ThermPro. All other engineering
documents reference it. Any change to a governing equation or correlation must result
in a new revision of this document before it is implemented in code.

**Scope:** Steady-state thermal analysis of low-voltage (LV) switchboard enclosures
under continuous load. Transient analysis architecture is described but not initially
implemented.

---

## 2. Engineering Reference Basis

The nodal thermal network methodology (MODE 2) is founded on the approach described in:

> **Schneider Electric Cahier Technique No. 145** — *Thermal Study of LV Electric
> Switchboards*, Schneider Electric, France.

Key concepts adopted from CT145:
- Subdivision of the enclosure into isothermal volumes (thermal cells).
- Thermal admittance (conductance) matrix formulation.
- Iterative solution coupling temperature, conductor resistance, device derating, and
  ventilation flow.
- Treatment of buoyancy-driven internal air circulation.
- Comparison of calculated and experimental temperatures as the primary validation method.

**IMPORTANT:** Proprietary datasets, manufacturer-specific tables, and copyrighted
numerical values from CT145 are **not** reproduced in ThermPro. CT145 is used as a
methodology reference only.

The IEC TR 60890 empirical method (MODE 1) uses an administrator-imported licensed
dataset. See THERM-STD-001 §5.

---

## 3. Complete Variable Table

| Symbol | Name | SI Unit | Definition / Notes |
|--------|------|---------|-------------------|
| T | Absolute temperature | K | T [K] = θ [°C] + 273.15 |
| θ | Temperature in Celsius | °C | Display variable |
| Δθ | Temperature rise | K | Rise above a reference; numerically equal to ΔT |
| θ_amb | External ambient temperature | °C | Project input; measured or specified |
| θ_ref | Reference temperature | °C | Usually 20 °C for resistance; 35 °C for IEC 61439 ambient |
| T_film | Film temperature | K | (T_surface + T_fluid) / 2; used for fluid property evaluation |
| Q | Heat transfer rate | W | Positive = heat flowing from higher to lower T |
| P | Electrical power dissipated as heat | W | Heat source term |
| P_n | Rated power loss of a device | W | At rated current I_n and rated ambient |
| P_fixed | Fixed (no-load) power loss | W | Independent of current |
| P_var | Variable (load-dependent) power loss | W | At rated current I_n |
| G | Thermal conductance | W/K | G = Q / ΔT |
| R_th | Thermal resistance | K/W | R_th = 1/G |
| G_cond | Conduction conductance | W/K | G_cond = k A / L |
| G_conv | Convective conductance | W/K | G_conv = h A |
| G_rad | Radiation conductance (linearised) | W/K | G_rad = h_r A |
| G_air | Air-transport conductance | W/K | G_air = ṁ cp (directed) |
| k | Thermal conductivity | W/(m·K) | Material property |
| A | Area | m² | Surface area or cross-sectional area (context-dependent) |
| L | Length or thickness | m | Path length for conduction |
| h | Convective heat transfer coefficient | W/(m²·K) | Local value; surface- and geometry-dependent |
| h_r | Linearised radiation heat transfer coefficient | W/(m²·K) | h_r = ε_eff σ (T_s+T_sur)(T_s²+T_sur²) |
| ε | Emissivity | — | 0 (perfect reflector) to 1 (blackbody) |
| ε_eff | Effective emissivity (two-body) | — | For two grey surfaces in radiation exchange |
| σ | Stefan-Boltzmann constant | W/(m²·K⁴) | 5.670374419 × 10⁻⁸ W/(m²·K⁴) |
| Nu | Nusselt number | — | Nu = h L_c / λ_f |
| Ra | Rayleigh number | — | Ra = Gr × Pr |
| Gr | Grashof number | — | Gr = g β |ΔT| L_c³ / ν² |
| Pr | Prandtl number | — | Pr = μ cp / λ_f ≈ 0.71 for air |
| Re | Reynolds number | — | Re = ρ v L_c / μ |
| L_c | Characteristic length | m | Height for vertical plates; A/P for horizontal |
| g | Gravitational acceleration | m/s² | 9.80665 m/s² |
| β | Volumetric thermal expansion coefficient | 1/K | β = 1/T [K] for ideal gas |
| ν | Kinematic viscosity | m²/s | ν = μ/ρ |
| μ | Dynamic viscosity of air | Pa·s | Temperature-dependent |
| λ_f | Thermal conductivity of air (fluid) | W/(m·K) | Temperature-dependent |
| cp | Specific heat capacity of air | J/(kg·K) | ≈ 1007 J/(kg·K) in range 250–400 K |
| ρ | Density of air | kg/m³ | ρ = P_atm / (R_specific × T) |
| ρ_ref | Reference air density | kg/m³ | At T_amb, P_atm |
| R_specific | Specific gas constant of air | J/(kg·K) | 287.058 |
| P_atm | Atmospheric pressure | Pa | 101 325 Pa at sea level; altitude correction applied |
| I | RMS current | A | |
| I_n | Rated current | A | Device or conductor rated value |
| I_rms | Total harmonic RMS current | A | I_rms = I_1 √(1+THD²) |
| THD | Total harmonic distortion | — | As a fraction (not %) |
| R | Electrical resistance | Ω | |
| R_ref | Reference resistance | Ω | At T_ref (usually 20 °C) |
| α | Temperature coefficient of resistance | 1/K | Cu: 3.93×10⁻³; Al: 4.03×10⁻³ |
| ρ_e | Electrical resistivity | Ω·m | |
| K_AC | AC resistance multiplier | — | Skin + proximity effect; K_AC ≥ 1 |
| R_joint | Joint resistance | Ω | Per bolted or welded joint |
| f_d | Derating factor | — | f_d = I_permissible / I_n; 0 < f_d ≤ 1 |
| I_perm | Permissible current | A | I_perm = f_d × I_n |
| ṁ | Mass flow rate | kg/s | |
| Q_vol | Volumetric flow rate | m³/s | Q_vol = ṁ / ρ |
| v | Velocity | m/s | Local air velocity |
| ΔP | Pressure difference | Pa | P_high − P_low |
| ΔP_stack | Buoyancy stack pressure | Pa | Natural driving pressure |
| Cd | Discharge coefficient | — | Typically 0.6–0.65 for sharp-edged openings |
| K_loss | Pressure loss coefficient | — | ΔP = K_loss ρ v²/2 |
| H | Vertical separation between inlet and outlet centroids | m | |
| A_free | Free area of opening | m² | Physical area × free-area ratio |
| T_i | Temperature of thermal node i | K | Unknown variable |
| G_ij | Conductance from node i to node j | W/K | Off-diagonal element of conductance matrix |
| Q_i | Net heat source at node i | W | Positive = heat injected |
| C_i | Thermal capacitance of node i | J/K | C_i = m_i cp_i (for transient) |
| N | Total number of thermal nodes | — | Size of linear system |
| ω | Relaxation factor | — | 0 < ω ≤ 1; default 0.7 |
| ε_T | Temperature convergence criterion | K | Default 0.1 K |
| ε_flow | Flow convergence criterion | — | Default 0.005 (0.5%) |
| ε_power | Power convergence criterion | — | Default 0.005 (0.5%) |
| ε_energy | Energy imbalance criterion | — | Default 0.01 (1%) |
| ε_mass | Mass imbalance criterion | — | Default 0.005 (0.5%) |
| A_e | Effective cooling surface (IEC TR 60890) | m² | Σ b_j A_j |
| b_j | Surface installation factor (IEC TR 60890) | — | From licensed dataset |
| c_0 | Enclosure constant (IEC TR 60890) | K/W^n | From licensed dataset |
| n | Exponent in IEC TR 60890 formula | — | From licensed dataset |
| Δθ_mid | Mid-height temperature rise (IEC TR 60890) | K | c_0 (P_tot/A_e)^n |
| Δθ_top | Top temperature rise (IEC TR 60890) | K | d × Δθ_mid |
| d | Temperature distribution factor (IEC TR 60890) | — | From licensed dataset |
| P_tot | Total internal power dissipation | W | Σ all device + busbar + conductor losses |

---

## 4. Governing Physics

ThermPro models six heat transfer mechanisms. Each mechanism is implemented as a
conductance element connecting two thermal nodes.

### 4.1 Solid Conduction

Heat flows through solid materials (walls, busbars, mounting plates) by Fourier
conduction:

```
Q_cond = G_cond · (T_hot − T_cold)     where G_cond = k · A / L     [W]
```

For composite walls, conductances are in series. Thermal contact resistance at
interfaces is added in series as R_contact [K/W].

### 4.2 Joule (Resistive) Losses

Every current-carrying conductor and device generates heat. The fundamental model is:

```
R(T) = R_ref · [1 + α · (T − T_ref)]  [Ω]
P = I_rms² · R(T)                     [W]
```

The conductor temperature T is initially assumed; it is updated at each outer
iteration. This means loss and temperature are fully coupled.

For AC systems, the AC resistance multiplier K_AC is applied:
`R_AC = K_AC · R_DC(T)`

### 4.3 Natural Convection

At every surface in contact with internal or external air, a convective conductance is
established:
```
G_conv = h · A_surface     [W/K]
```

The coefficient h is calculated from dimensionless correlations (Nusselt number)
appropriate to the surface orientation and temperature difference. Because h depends on
the temperature difference ΔT (through Ra), it is updated at each inner iteration step.

### 4.4 Radiation

All surfaces at finite temperature radiate heat. For two surfaces exchanging radiation:

```
Q_rad = ε_eff · σ · A · (T_s⁴ − T_sur⁴)    [W]
```

**Temperatures must be in kelvin.** This is enforced by an explicit unit check.

For matrix assembly, radiation is linearised:
```
h_r = ε_eff · σ · (T_s + T_sur)(T_s² + T_sur²)    [W/(m²·K)]
G_rad = h_r · A_surface                             [W/K]
```

h_r is updated at each inner iteration step.

### 4.5 Air-Mass Transport

Air flowing at mass flow rate ṁ between two cells carries enthalpy:

```
Q_air = ṁ · cp · (T_upstream − T_downstream)    [W]
```

This is a directed (non-symmetric) conductance. The direction is determined by the
airflow network solution (Section 5.3).

### 4.6 Buoyancy

Temperature-dependent density creates buoyancy forces that drive natural convection
and stack-effect flow. For air treated as an ideal gas:

```
ρ(T) = P_atm / (R_specific · T)    [kg/m³]

ΔP_stack = (ρ_cold − ρ_hot) · g · H    [Pa]
```

The Boussinesq approximation is valid for temperature differences up to ~50 K. For larger
differences, the full ideal-gas density model is used.

---

## 5. Calculation Flow Diagram

The following diagram shows the complete calculation flow from geometry to report.
Every step is described in the sections below.

```
INPUT
│
├─── GEOMETRY PROCESSING
│    • Load enclosure, compartments, partitions, openings
│    • Load device positions and thermal cell grid
│    • Load fan positions and ventilation configuration
│    • Perform geometry validation (collision, overlap, obstruction)
│    └─── [ERROR: geometry invalid → stop, report]
│
├─── HEAT SOURCES
│    • Load device library records for each placed device
│    • Load busbar and conductor geometry and material
│    • Assign every heat source to a thermal cell
│
├─── INITIALISATION
│    • Set T_i = T_amb for all nodes
│    • Set ṁ_ij = 0 for all flow elements
│    • Set f_d = 1 (no derating) for all devices
│
│    ┌─────────────────────────────────────────────────────────┐
│    │  OUTER ITERATION LOOP (derating + airflow + thermal)    │
│    │                                                         │
│    │  ├─── ELECTRICAL LOSSES                                 │
│    │  │    • For each busbar segment:                        │
│    │  │      R(T) = R_ref [1 + α (T − T_ref)]               │
│    │  │      P_seg = I² · K_AC · R(T)                       │
│    │  │    • For each device:                                │
│    │  │      P_dev = f_d-dependent loss model                │
│    │  │    • Assign P to corresponding thermal cell Q_i      │
│    │  │                                                      │
│    │  ├─── AIRFLOW NETWORK (MODE 3 or buoyancy-only)         │
│    │  │    • Compute ρ(T_i) for each air cell                │
│    │  │    • Compute ΔP_stack from temperature distribution  │
│    │  │    • Assemble pressure-node network                  │
│    │  │    • Solve for node pressures P_i                    │
│    │  │    • Compute element flows ṁ_ij, velocities v_ij     │
│    │  │    • Check mass balance at every node                │
│    │  │    • Detect pathological flows                       │
│    │  │                                                      │
│    │  │    ┌──────────────────────────────────────────────┐  │
│    │  │    │  INNER THERMAL LOOP                          │  │
│    │  │    │                                              │  │
│    │  │    │  ├─── MATRIX ASSEMBLY                        │  │
│    │  │    │  │    • G_cond for all solid paths           │  │
│    │  │    │  │    • G_conv = h(T) · A for all surfaces   │  │
│    │  │    │  │    • G_rad = h_r(T) · A for all surfaces  │  │
│    │  │    │  │    • G_air = ṁ · cp (directed)            │  │
│    │  │    │  │    • Assemble G·T = Q (sparse CSR)        │  │
│    │  │    │  │                                           │  │
│    │  │    │  ├─── SOLVE                                  │  │
│    │  │    │  │    • T = spsolve(G, Q)                    │  │
│    │  │    │  │    • Check: T_i > 0 K; T_i < 1000 K      │  │
│    │  │    │  │                                           │  │
│    │  │    │  ├─── PROPERTY UPDATE                        │  │
│    │  │    │  │    • Recompute h_conv(T_i) for each face  │  │
│    │  │    │  │    • Recompute h_r(T_i) for each surface  │  │
│    │  │    │  │    • Recompute ρ(T_i) for air nodes       │  │
│    │  │    │  │                                           │  │
│    │  │    │  ├─── APPLY RELAXATION                       │  │
│    │  │    │  │    T_i ← ω T_i_new + (1-ω) T_i_old       │  │
│    │  │    │  │                                           │  │
│    │  │    │  └─── CONVERGENCE CHECK (inner)              │  │
│    │  │    │       max|ΔT_i| < ε_T ?                      │  │
│    │  │    │       → YES: exit inner loop                  │  │
│    │  │    │       → NO: next inner iteration             │  │
│    │  │    └──────────────────────────────────────────────┘  │
│    │  │                                                       │
│    │  ├─── RESISTANCE UPDATE                                  │
│    │  │    • Update R(T) for each busbar and conductor        │
│    │  │    • Update P for each busbar and conductor           │
│    │  │                                                       │
│    │  ├─── DEVICE DERATING                                    │
│    │  │    • For each device:                                 │
│    │  │      θ_local = T_cell(device) − 273.15               │
│    │  │      f_d_new = derating_curve(θ_local)               │
│    │  │      I_perm = f_d_new × I_n                          │
│    │  │    • Update device loss with new f_d if applicable    │
│    │  │                                                       │
│    │  └─── CONVERGENCE CHECK (outer)                         │
│    │       max|ΔT| < ε_T                                     │
│    │       max|Δṁ/ṁ| < ε_flow                               │
│    │       max|ΔP/P| < ε_power                               │
│    │       │Σ(Q_in−Q_out)/Q_in| < ε_energy                  │
│    │       │Σṁ/ṁ_inlet| < ε_mass                            │
│    │       → ALL MET: CONVERGED                              │
│    │       → ANY NOT MET: next outer iteration               │
│    └─────────────────────────────────────────────────────────┘
│
├─── HOT-SPOT ASSESSMENT
│    • For each node and component:
│      margin = θ_limit − Δθ_node
│      severity = PASS / WATCH / WARNING / FAIL / NOT_VERIFIABLE
│    • Detect hot spots (local maximum + gradient criterion)
│    • Generate recommendations linked to evidence
│
├─── POST-PROCESSING
│    • Populate ResultSnapshot
│    • Generate ConvergenceTrace
│    • Compute AuditRecord checksum
│
└─── REPORT
     • Include all input data, assumptions, method, equations,
       data provenance, convergence trace, results, hot spots,
       limitations, and audit checksum
```

---

## 6. Calculation Modes

### 6.1 MODE 1 — IEC TR 60890

**Applicable to:** Eligible natural-ventilation or sealed enclosures per the eligibility
conditions defined in THERM-STD-001 §4.

**Method:**
1. Validate all eligibility conditions. If any mandatory condition fails → not eligible.
2. Calculate P_tot = sum of all internal losses.
3. Calculate A_e = Σ b_j A_j (effective cooling surface using licensed surface factors).
4. Calculate Δθ_mid = c_0 · (P_tot / A_e)^n using licensed coefficients.
5. Calculate Δθ_top = d · Δθ_mid.
6. Interpolate temperature at any height y.

**Limitations:**
- Not applicable with forced ventilation.
- Does not give local temperatures; gives only mid-height and top temperature rise.
- Does not account for position of heat sources within the enclosure.
- Relies on empirical coefficients whose validity depends on the specific configuration.

### 6.2 MODE 2 — Nodal Thermal Network

**Applicable to:** Any enclosure geometry; position-sensitive analysis.

**Method:** Full nodal thermal network as described in Sections 4 and 5 and in
THERM-NET-001. Airflow is modelled by buoyancy stack effect (if no fans) or coupled
to MODE 3 (if fans are present).

**Limitations:**
- Isothermal-volume assumption in each cell; cell size must be appropriate.
- Natural convection correlations have ±15–20% uncertainty.
- Radiation view factors are simplified.
- Does not capture small-scale turbulence or recirculation within a cell.

### 6.3 MODE 3 — Forced-Ventilation Airflow Network

**Applicable to:** Enclosures with supply fans, exhaust fans, inlet/outlet grilles,
filters, ducts, or any combination.

**Method:** Pressure-node airflow network (THERM-AFN-001) coupled to MODE 2 thermal
network. Fan curve required for every active fan.

**Limitations:**
- Fan curve must be provided; free-delivery flow is not a valid substitute.
- Duct routing is simplified (lumped resistance); complex duct layouts require CFD.
- No acoustic or mechanical vibration modelling.

### 6.4 MODE 4 — CFD Export/Import Adapter

**Applicable to:** Future integration with validated external CFD solvers.

**Method:** Export enclosure geometry, material properties, and boundary conditions
in a defined format. Import temperature and velocity fields from the external solver.

**Limitations:**
- ThermPro is NOT a CFD solver. This mode is an adapter.
- The external solver's accuracy and validation are the engineer's responsibility.
- Results are tagged with the external solver name and version.

---

## 7. Boundary Conditions

### 7.1 External Ambient

The external ambient temperature θ_amb is a project input. It applies to all exposed
external surfaces and to the airflow network external nodes.

```
T_ext = θ_amb + 273.15    [K]
```

### 7.2 External Convection

The external convective coefficient h_ext is calculated from natural convection
correlations applied to each external face, using the external ambient temperature as
the fluid temperature. For wall-mounted or adjacent-cubicle surfaces, a covering factor
reduces h_ext.

### 7.3 Adiabatic Surfaces

Surfaces marked as adjacent to another cubicle, flush-mounted against a wall, or
plinth-to-floor are assigned covering_factor = 1.0, making them effectively adiabatic
(no heat exchange with the external environment on that face).

### 7.4 Altitude Correction

At altitudes above sea level, air density is reduced:

```
P_atm(altitude) = 101325 · exp(−altitude / 8430)    [Pa]
```

This reduces ρ, ṁ for a given velocity, and the effectiveness of natural convection.
The altitude correction is applied to all air property calculations.

---

## 8. Numerical Method

### 8.1 Matrix Assembly

The thermal network is assembled as a sparse N×N linear system:

```
G · T = Q_rhs    (CSR sparse format, scipy.sparse.csr_matrix)
```

Boundary nodes (known T) contribute to Q_rhs and are removed from the unknown vector.

### 8.2 Linear Solve

```
T = scipy.sparse.linalg.spsolve(G, Q_rhs)
```

For the initial implementation (N ≤ 5000), a direct sparse LU solver is used.
For larger problems, iterative solvers (GMRES with ILU preconditioner) may be selected.

### 8.3 Nonlinear Convergence

Convection and radiation make the system nonlinear (h and h_r depend on T). This is
handled by successive substitution (Picard iteration) in the inner loop, with
under-relaxation:

```
T^(k+1) = ω · T^(k+1)_new + (1 − ω) · T^(k)
```

The inner loop solves the linear system with fixed h and h_r (from iteration k), then
updates h and h_r for iteration k+1.

### 8.4 Outer Iteration

The outer loop couples:
- Joule losses (depend on conductor temperature T)
- Airflow (depends on air temperature distribution)
- Derating (depends on local device ambient temperature)

### 8.5 Convergence Criteria (Default Values, Configurable)

| Criterion | Symbol | Default | Description |
|-----------|--------|---------|-------------|
| Temperature change | ε_T | 0.1 K | max|T_i^(k+1) − T_i^(k)| |
| Flow change | ε_flow | 0.005 | max|ṁ^(k+1) − ṁ^(k)| / ṁ^(k) |
| Power change | ε_power | 0.005 | max|P^(k+1) − P^(k)| / P^(k) |
| Energy imbalance | ε_energy | 0.01 | |ΣQ_in − ΣQ_out| / ΣQ_in |
| Mass imbalance | ε_mass | 0.005 | |Σṁ| / ṁ_inlet |
| Max inner iterations | — | 100 | Inner loop limit |
| Max outer iterations | — | 50 | Outer loop limit |

If any criterion is not met after the maximum iterations, the result is tagged
`converged = false` and displayed as RESULT INVALID.

---

## 9. Data Provenance Classification

Every heat-source and thermal-property datum is classified:

| Classification | Meaning | Confidence | Display |
|----------------|---------|------------|---------|
| MEASURED | Directly measured value | HIGH | Green badge |
| MANUFACTURER | From manufacturer's published data | HIGH | Green badge |
| CALCULATED | Derived from first principles | MEDIUM–HIGH | Blue badge |
| ASSUMED | No data available; assumption used | LOW | Orange badge + warning |

When any ASSUMED datum is used for a device or busbar contributing > 5% of total P_tot,
the overall calculation confidence is downgraded and the result carries a
`LOW_CONFIDENCE` flag in the report.

---

## 10. Known Limitations

| Limitation | Engineering Implication |
|-----------|------------------------|
| Isothermal cell assumption | Cell must be small enough that T variation within a cell is < ε_T. Cells near strong gradients (near busbars, near openings) must be refined. |
| Simplified view factors | Radiation between non-adjacent surfaces and between small objects may be underestimated. |
| Steady-state only (initial) | Load cycling, transient start-up, and fault conditions are not modelled. |
| No humidity or condensation | Moisture effects on heat transfer are not modelled. |
| No acoustic/vibration | Fan noise and vibration are stored in the library but not used in thermal calculations. |
| Natural convection uncertainty | Nusselt correlations have ±10–20% uncertainty under ideal conditions; actual switchboard internal geometry increases this. |
| No solar load calculation | Solar radiation must be entered as an additional heat source if applicable. |
| No chemical/oxidation effects | Long-term changes in emissivity or resistance due to oxidation are not modelled. |
| Reduced-order flow model | The pressure-node network cannot capture local velocity distributions; local turbulence and recirculation within a cell are averaged. |
| IEC 61439 design verification | This software is a calculation aid only. Design verification per IEC 61439 requires a qualified engineer's review and sign-off. |

---

## 11. Applicability Boundary

ThermPro is applicable to:
- LV switchboards and distribution boards with rated voltage ≤ 1000 V AC or ≤ 1500 V DC.
- Internal ambient temperatures up to 85 °C.
- Altitudes up to 4000 m (with correction).
- Indoor and outdoor IP-rated enclosures.
- Single and multi-cubicle assemblies.

ThermPro is NOT applicable to:
- MV/HV switchgear.
- Electrical machines (motors, generators, transformers — as primary subjects of analysis).
- Enclosures with active liquid cooling.
- Environments with explosive gases or dust (ATEX) — this software does not account for ATEX thermal constraints.
- Systems where radiation is the dominant cooling mechanism in vacuum.

---

## A. Recommended MVP Scope

The Minimum Viable Product (MVP) comprises Milestones 1–5 plus basic display:

| Feature | MVP? |
|---------|------|
| Project and enclosure definition | Yes |
| Device and busbar placement | Yes |
| Manual electrical loading | Yes |
| Auto-generated thermal cell grid | Yes |
| Steady-state nodal thermal solve (conduction + fixed h) | Yes |
| Basic temperature display on drawing | Yes |
| Simple PDF report | Yes |
| Natural convection correlations (MODE 2 fully) | No — Milestone 6 |
| Radiation | No — Milestone 6 |
| Airflow network / fans (MODE 3) | No — Milestone 7 |
| Coupled thermal-airflow iteration | No — Milestone 8 |
| Derating and hot-spot engine | No — Milestone 9 |
| IEC TR 60890 (MODE 1) | No — Milestone 11 |
| Comparison and optimisation | No — Milestone 12 |
| CFD adapter (MODE 4) | No — Milestone 14 |

The MVP is sufficient to demonstrate the workflow, validate the geometry model, and
identify data requirements. It must not be used for production engineering.

---

## B. Features Deferred to Later Phases

| Feature | Rationale for Deferral |
|---------|----------------------|
| Transient thermal solve | Architecture is designed for it; steady-state is validated first |
| Full radiosity matrix | Simplified view factors acceptable for MVP; refined later |
| 3D visualisation (Three.js) | Useful but not required for engineering calculation |
| Solar load calculation | Specialist input; deferred to a specific later feature |
| Real-time SCADA integration | Requires external system interface; deferred |
| Physical test import (Level 4 validation) | Requires test data; infrastructure built in Milestone 13 |
| Sensitivity analysis | Planned for Milestone 12 |
| Multi-user collaboration | Single-user MVP; multi-user in later phase |
| Mobile / tablet view | Desktop-first; mobile read-only view deferred |
| API for third-party integration | Internal API is built; documented public API later |

---

## C. Missing Engineering Data

The following data are required for production use and are currently absent from
the application:

| Data | Impact | Mitigation |
|------|--------|-----------|
| IEC TR 60890 coefficient tables | MODE 1 cannot run | Administrator imports licensed dataset |
| Manufacturer device loss curves | Derating uses ASSUMED model | Import workflow in Milestone 3 |
| Fan P-Q curves for all specified fans | MODE 3 result is NOT_VERIFIABLE | User provides from manufacturer datasheet |
| AC resistance multipliers (K_AC) for busbar configurations | R_AC uses K_AC=1.0 assumption | User provides from manufacturer or IEC 60287 |
| Physical test thermocouple data | Level 4 validation not possible | Formal factory acceptance test required |
| Joint resistance values per connection type | Joint losses assumed zero or from generic table | User provides from manufacturer |

---

## D. Major Technical Risks

(See THERM-RISK-001 for the full register. Key risks summarised here.)

| Risk | Severity | Key Mitigation |
|------|----------|---------------|
| Incorrect local ambient used for derating (RISK-ENG-001) | HIGH | Cell-based device ambient assignment; unit test |
| Busbar loss at 20 °C only (RISK-ENG-002) | HIGH | R(T) enforced; outer iteration updates temperature |
| Forced-ventilation result labelled IEC TR 60890 (RISK-ENG-003) | HIGH | Hard-coded exclusion; no override |
| Unconverged result presented as valid (RISK-ENG-004) | HIGH | RESULT INVALID watermark; blocked display |
| Fan rated flow assumed = installed flow (RISK-ENG-005) | CRITICAL | Fan curve required; NOT_VERIFIABLE if absent |
| Assumed loss data not visible to user (RISK-DATA-001) | CRITICAL | Prominent ASSUMED badge; data provenance table |
| IEC tables included without licence (RISK-LEGAL-001) | MEDIUM | Ship without tables; administrator import only |

---

## E. Questions Requiring Engineering Approval

The following questions require explicit engineering approval before implementation:

| Q | Question |
|---|---------|
| E1 | **Partition conduction only or radiation also through perforations?** — Perforated partitions currently transmit conduction through the solid fraction and air transport through the open fraction. Should radiation through the perforation openings also be modelled? |
| E2 | **Derating beyond manufacturer's curve** — When the local ambient temperature exceeds the range of the manufacturer's derating curve, should the software extrapolate (risk: unconservative), clamp to the last value (safe but not rigorous), or halt with a FAIL? Recommendation: FAIL with explicit message. |
| E3 | **IEC TR 60890 for partitioned enclosures** — The standard requires a partition factor. The approach for applying this factor in a multi-compartment enclosure (one factor per compartment or one for the whole enclosure) needs engineering review. |
| E4 | **Air property polynomials** — The current polynomial approximations are calibrated for 250–450 K. Should the solver refuse to run if any node temperature reaches the boundary of this range? |
| E5 | **K_AC default value** — When no K_AC data are available, should the solver use K_AC = 1.0 (unconservative for high-current busbars) or K_AC = 1.05 (conservative assumption)? |
| E6 | **Energy imbalance criterion** — The 1% energy imbalance criterion is an engineering judgement. A tighter criterion (0.1%) would be more rigorous but may require more iterations or a tighter inner-loop convergence. Approval needed for the default value. |

---

## F. Traceability Matrix

This matrix links requirements (THERM-REQ-001) to governing equations (THERM-EQN-001),
software modules (THERM-ARCH-001), and validation tests (THERM-VAL-001).

| Requirement | Governing Equation | Module | Validation Test |
|-------------|-------------------|--------|----------------|
| FR-THERM-001 (cell grid) | — | thermal_matrix.py | UT-MATRIX-001 |
| FR-THERM-002 (grid refinement) | — | thermal_matrix.py | geometry integration test |
| FR-ELEC-004 (Joule loss) | EQN §4.1/4.2 | joule.py | UT-JOULE-001/002 |
| FR-ELEC-003 (harmonics) | EQN §4.3 | joule.py | UT-JOULE-003 |
| FR-SOLV-004 (airflow) | EQN §10.1/10.2 | airflow_network.py | UT-FLOW-001/002/005, BM-005 |
| FR-SOLV-005 (heat transfer) | EQN §3/6/7/8/9 | thermal_matrix.py | BM-001/002/003/006 |
| FR-SOLV-006 (derating iter.) | EQN §5.4 | derating.py / coupling.py | UT-DERATING-001/002/003 |
| FR-SOLV-007 (convergence) | Section 8.5 | coupling.py | BM-003 (exact convergence) |
| FR-SOLV-008 (invalid result) | Section 8.5 | coupling.py | UT-MATRIX-004 |
| FR-STD-001 (MODE 1) | EQN §11 | iec_60890.py | RE-001 |
| FR-STD-002 (MODE 2) | EQN §3–9, §12 | nodal.py | BM-001 to BM-006 |
| FR-STD-003 (MODE 3) | EQN §10 | forced_ventilation.py | BM-004/005 |
| FR-STD-006 (fan exclusion) | Section 6.1 | iec_60890.py | Integration test (fan + MODE 1) |
| FR-VIS-003 (hot spots) | Section 5 (post-proc) | hotspots.py | Unit test: 10 severity scenarios |
| FR-AUD-001/002/003 (audit) | Section 9 (data model) | audit.py | Snapshot re-run test |
| CR-ENG-002 (T in kelvin) | EQN §8.1 | radiation.py | UT-RAD-004 |
| CR-ENG-003 (R(T)) | EQN §4.1/4.2 | joule.py | UT-JOULE-001 |
| CR-ENG-004 (IEC 60890 exclusion) | Section 6.1 | iec_60890.py | Integration test |
| NFR-AUD-001 (reproducibility) | Section 9 (snapshot) | audit.py | Snapshot re-run test |
| NFR-MAINT-002 (90% coverage) | — | All physics/network modules | CI coverage report |

---

*End of THERM-METH-001*
