# Thermal Network Model — LV Switchboard Thermal Digital Twin

**Document ID:** THERM-NET-001  
**Revision:** 0.1 (Draft for Engineering Review)  
**Date:** 2026-07-03  
**Status:** Pending Approval

---

## 1. Purpose

This document specifies the nodal thermal network formulation used in MODE 2 of ThermPro.
It defines how an LV switchboard enclosure is decomposed into a network of thermal nodes
connected by conductance elements, how the governing matrix system is assembled, how the
system is solved, and how results are post-processed.

---

## 2. Physical Basis

An LV switchboard enclosure contains multiple heat sources (devices, busbars, conductors)
distributed in three-dimensional space. Heat flows from these sources to the external
environment through:

1. **Solid conduction** through walls, partitions, and mounting plates.
2. **Natural convection** from surfaces to internal air cells.
3. **Radiation** from surfaces to other surfaces and to the enclosure wall.
4. **Air-mass transport** as buoyancy-driven (or forced) airflow carries thermal energy
   between compartments and air cells.
5. **External convection and radiation** from the enclosure outer surface to the surroundings.

The fundamental modelling assumption is that each thermal cell (node) can be treated as
an **isothermal volume** at a single representative temperature. This is valid when cell
dimensions are small relative to the temperature gradient. Cell size selection is discussed
in Section 7.

---

## 3. Node Types

| Node Type | Symbol | Description |
|-----------|--------|-------------|
| Air cell | N_air | A volume of air within a compartment or zone |
| Enclosure wall surface | N_wall | Inner or outer face of an enclosure wall |
| Internal partition surface | N_part | Face of an internal partition |
| Device body | N_dev | Thermal mass and heat source of a device |
| Busbar segment | N_bus | A segment of a busbar run |
| Conductor | N_cond | A cable or conductor run |
| External environment | N_ext | Ambient air at known temperature (boundary node) |
| External surface | N_ext_surf | Outer surface of the enclosure (may be intermediate) |

Each node is assigned:
- UUID
- Position (centroid X, Y, Z)
- Volume or area
- Material thermal properties (capacitance for transient; conductivity for solid nodes)
- Heat source Q_i (W) — positive means heat is generated in this node
- Temperature T_i (K) — unknown for internal nodes; prescribed for boundary nodes

---

## 4. Conductance Elements

Every pair of nodes (i, j) that exchange heat is connected by a conductance G_ij [W/K].

### 4.1 Solid Conduction Conductance

```
G_cond_ij = k · A_contact / L_path          [W/K]
```

Used for:
- Wall node to adjacent wall node
- Device body to mounting plate
- Busbar to support bracket
- Partition to enclosure wall at attachment point

### 4.2 Convective Conductance

```
G_conv_ij = h_ij · A_surface                [W/K]
```

h_ij depends on the geometry (vertical plate, horizontal plate, enclosed space) and the
temperature difference T_i − T_j. Because h_ij is nonlinear (depends on Ra, which depends
on ΔT), it is updated at each iteration.

For the internal iteration:
- h_ij from previous iteration is used to assemble the conductance matrix.
- Temperatures are solved.
- New h_ij values are computed.
- Process repeats until convergence.

### 4.3 Radiation Conductance

Radiation is linearised to fit the matrix format (see THERM-EQN-001 §8.3):

```
G_rad_ij = h_r_ij · A_surface               [W/K]

h_r_ij = ε_eff · σ · (T_i + T_j)(T_i² + T_j²)   [W/(m²·K)]
```

h_r_ij is also nonlinear and is updated at each iteration.

### 4.4 Air-Transport Conductance

Air flowing at mass flow rate ṁ from node i to node j carries enthalpy:

```
Q_air = ṁ · cp · (T_i − T_j)               [W]
```

This can be expressed as a directed conductance:

```
G_air_ij = ṁ_ij · cp                        [W/K]  (directed, not symmetric)
```

Note that air-transport conductance is non-symmetric (ṁ is directed). The matrix
structure must handle directed edges; the standard symmetric assembly does not apply
for air transport. The implementation uses a modified assembly that handles both
symmetric (conduction, radiation) and directed (air transport) conductances.

---

## 5. Matrix Formulation

### 5.1 Node Balance

For each non-boundary node i:

```
Σ_j G_ij · (T_j − T_i) + Q_i = 0           [W]
```

Rearranging:

```
Σ_j G_ij · T_j − T_i · Σ_j G_ij + Q_i = 0
```

### 5.2 Assembly into Linear System

Defining:
- Diagonal entry: `G_ii = −Σ_j G_ij` (all conductances from node i to all others)
- Off-diagonal entry: `G_ij` (conductance between nodes i and j)

The system becomes:

```
G · T = −Q                                   (matrix equation)
```

Where G is a sparse N×N matrix (N = total non-boundary nodes), T is the N×1 temperature
vector, and Q is the N×1 heat-source vector.

For boundary nodes (external environment at known T_ext): their contribution moves to
the right-hand side:

```
G_ii_modified · T_i + Q_i_modified = Q_i_external_BC
```

### 5.3 Sparse Matrix Storage

G is stored in compressed sparse row (CSR) format using SciPy (`scipy.sparse.csr_matrix`).
For typical enclosures (50–1000 cells), N is modest and the matrix is very sparse.
Direct sparse solvers (`scipy.sparse.linalg.spsolve`) are used for steady-state.
For transient, factorised or iterative methods may be selected based on problem size.

### 5.4 Convergence Criteria (Inner Thermal Loop)

At each inner iteration step k:

```
max |T_i^(k) − T_i^(k-1)| < ε_T             (default: 0.1 K)

max |G_ij^(k) − G_ij^(k-1)| / G_ij^(k) < ε_G  (default: 1%)
```

Maximum inner iterations: configurable (default: 100).

---

## 6. Partition Treatment

### 6.1 Solid (Impermeable) Partition

A solid partition divides the enclosure into two thermally distinct zones. The conductance
across the partition is:

```
G_part = k_part · A_part / L_part           [W/K]
```

Air cannot cross a solid partition. The air-transport conductance G_air across it is zero.

### 6.2 Perforated Partition

A perforated partition has:
- A solid fraction that conducts heat: G_cond through the solid material.
- An open area fraction that permits air flow: G_air based on the airflow network result.

The effective conductance is the sum:

```
G_eff = G_cond_solid + G_air_open           [W/K]
```

The open-area conductance is supplied by the airflow network module (MODE 3 or buoyancy
calculation) and must be solved simultaneously with temperatures.

### 6.3 Radiation Across Openings

Radiation can pass through an opening from one compartment to another. A simplified
view-factor calculation is used for rectangular openings between parallel compartments.
The full radiosity matrix is an option for higher accuracy.

---

## 7. Thermal Cell (Node) Size Selection

### 7.1 General Guidelines

Cell size must be small enough that the isothermal-volume assumption is valid. As a
working guideline:

| Region | Recommended maximum cell dimension |
|--------|-----------------------------------|
| Near a busbar (within 50 mm) | 20 mm |
| Near a device (within 100 mm) | 50 mm |
| Near an opening or fan | 30 mm |
| General internal air volume | 100–200 mm |
| Enclosure walls | Single node per wall section |

### 7.2 Automatic Grid Generation

The automatic grid generator:
1. Divides each compartment into a 3D Cartesian grid with default spacing.
2. Identifies all heat sources, openings, partitions, and fans.
3. Refines cells in proximity zones around these features (halving the cell size once or
   twice as the feature is approached).
4. Merges cells where no refinement is needed.
5. Validates minimum cell count (at least 3 cells in each principal direction per compartment).

### 7.3 Manual Refinement

The user may select any region in the drawing editor and request cell refinement. The
system imposes a maximum refinement level and a maximum total cell count (configurable,
default: 5000 cells per enclosure).

---

## 8. Natural Convection Cell-to-Cell Conductance

For air convection between two adjacent air cells separated by a virtual boundary:

```
G_conv_air = h_nat · A_cell_face            [W/K]
```

The natural convection coefficient h_nat is calculated from the vertical temperature
difference between the two cells, using the vertical-plate correlation for the cell
height as the characteristic length.

### 8.1 Buoyancy-Induced Air Circulation

Within a compartment, buoyancy drives a circulation: hot air rises and cold air falls.
This is modelled as a directed airflow from lower to upper cells:

```
ṁ_buoyancy = Cd_int · A_flow_section · sqrt(2 · ΔP_stack · ρ)  [kg/s]
```

The stack pressure is calculated from the temperature difference between the bottom and
top of the compartment (see THERM-EQN-001 §10.5).

---

## 9. External Heat Transfer

### 9.1 External Convection

For each external face of the enclosure that is exposed to ambient air:

```
G_ext_conv = h_ext · A_face                 [W/K]
```

h_ext is calculated from natural-convection correlations applied to the external surfaces
(vertical plates for sides, horizontal plates for top/bottom).

### 9.2 External Radiation

```
G_ext_rad = ε_enc · σ · A_face · (T_ext_surf + T_amb)(T_ext_surf² + T_amb²)  [W/K]
```

ε_enc is the emissivity of the enclosure outer surface (e.g., 0.9 for painted steel).

### 9.3 Adjacent Cubicles and Wall Mounting

For surfaces adjacent to another cubicle or a wall:
- The heat transfer coefficient on that face is reduced to account for the reduced airflow.
- A configurable covering factor (0 = fully exposed, 1 = fully covered/adiabatic) is
  applied to both convection and radiation on the affected face.

---

## 10. Coupling with Airflow Network

Thermal and airflow solutions are inherently coupled:
- Airflow network (MODE 3) provides mass flow rates ṁ_ij for each opening element.
- These mass flows define the air-transport conductances G_air_ij in the thermal network.
- Thermal network provides temperatures for each air node.
- Temperatures determine air density ρ(T), which feeds back to the airflow network.

The coupling is resolved by outer iteration (see THERM-ARCH-001 §G):

```
1. Solve airflow network with current temperatures → get ṁ_ij
2. Assemble thermal network with updated G_air_ij
3. Solve thermal network → get new temperatures T_i
4. Update ρ(T_i) for airflow network
5. Repeat until coupled convergence
```

Convergence criterion for the coupled loop:

```
max |T_i^(k) − T_i^(k-1)| < 0.1 K  AND  max |ṁ_ij^(k) − ṁ_ij^(k-1)| / ṁ_ij^(k) < 0.5%
```

---

## 11. Under-Relaxation

To prevent oscillation in the nonlinear iterations, under-relaxation is applied:

```
T_i^(k+1) = ω · T_i^(k+1)_new + (1 − ω) · T_i^(k)   [K]
```

Default relaxation factor: ω = 0.7 (configurable, 0.1–1.0).

For radiation-dominated cases, a lower ω (0.4–0.6) may be required.

---

## 12. Divergence and Singularity Detection

The solver detects and reports:

| Condition | Detection Method | Action |
|-----------|-----------------|--------|
| Divergence | ΔT between iterations increasing monotonically for > 5 iterations | Stop, report, recommend lower ω |
| Singular matrix | scipy.linalg.det ≈ 0 or solver returns NaN | Stop, report node connectivity issue |
| Negative temperatures | T_i < 0 K after solve | Stop, report as physically invalid |
| Extremely high temperatures | T_i > 1000 K | Stop, report likely data error |
| Non-convergence at max iterations | Iterations = max_iter | Report non-converged; result flagged as INVALID |

A result flagged as INVALID is never presented to the user as a valid engineering result.
The UI displays a prominent error and prompts the user to review inputs.

---

## 13. Result Post-Processing

After convergence, the following are extracted for each node:

| Quantity | Description |
|----------|-------------|
| T_i | Absolute temperature of node i [K → displayed as °C] |
| θ_rise_i | Temperature rise above ambient [K] |
| θ_margin_i | Limit − θ_rise_i [K] — positive = safe |
| severity_i | PASS / WATCH / WARNING / FAIL / NOT_VERIFIABLE |
| Q_in_i | Total heat input at node i [W] |
| Q_out_i | Total heat output at node i [W] |
| energy_balance_i | |Q_in − Q_out| / Q_in — must be < 1% at convergence |

---

*End of THERM-NET-001*
