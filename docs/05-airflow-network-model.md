# Airflow Network Model — LV Switchboard Thermal Digital Twin

**Document ID:** THERM-AFN-001  
**Revision:** 0.1 (Draft for Engineering Review)  
**Date:** 2026-07-03  
**Status:** Pending Approval

---

## 1. Purpose

This document specifies the pressure-node airflow network model used in MODE 3 of
ThermPro. It defines how enclosure compartments and openings are represented as a
hydraulic network, how the governing equations are assembled, how the system is solved,
and how pathological flow conditions are identified.

---

## 2. Physical Basis

Air movement within an LV switchboard is driven by:

1. **Buoyancy (natural convection stack effect):** Warm air is less dense and rises;
   cool inlet air falls. The pressure difference created drives flow through openings.
2. **Mechanical fans:** Create a pressure difference (fan curve) that forces air through
   a defined path.
3. **Leakage paths:** Every enclosure has imperfect sealing; small leakage openings exist.

The airflow network treats each **compartment or air zone** as a **pressure node** and
each **opening, duct, filter, or fan** as a **flow element** connecting two nodes.
The network is solved for node pressures, from which element flow rates and directions
are derived.

---

## 3. Network Components

### 3.1 Pressure Nodes

| Node Type | Description |
|-----------|-------------|
| Compartment node | Represents a sealed or partially open compartment or air zone |
| External ambient node | Fixed-pressure boundary node (gauge pressure = 0 Pa) |
| Plenum node | Ducted air volume at intermediate pressure |

Each node carries:
- Node pressure P_i [Pa] (gauge, relative to external ambient)
- Average air temperature T_i [K] (from thermal network)
- Air density ρ_i = f(T_i) [kg/m³]

### 3.2 Flow Elements

| Element Type | Flow Model | Notes |
|-------------|------------|-------|
| Natural opening (hole, slot) | Orifice: ṁ = Cd A √(2|ΔP|ρ) | Bidirectional; direction from sign of ΔP |
| Inlet grille | Orifice + loss coefficient | Free area = physical area × free-area ratio |
| Outlet grille | Orifice + loss coefficient | As inlet |
| Filter | Quadratic: ΔP = C_f1 Q + C_f2 Q² | Manufacturer curve required |
| Duct | Darcy-Weisbach: ΔP = K ρ v²/2 | Includes fittings loss |
| Fan (supply or exhaust) | Fan curve: ΔP_fan = f(Q, speed) | Adds pressure; sets flow direction |
| Internal circulation fan | Fan curve (recirculating) | Creates internal pressure loop |
| Leakage opening | Orifice with small area and Cd ≈ 0.5 | Area estimated from IP rating |
| Flap / damper (open) | Orifice with configurable Cd and area | Full-closed position = zero flow |
| Flap / damper (closed) | Leakage only | Leakage area from damper spec |

---

## 4. Governing Equations

### 4.1 Element Flow Equation

For a passive element (opening, duct, filter) from node i to node j:

```
ṁ_ij = sign(P_i − P_j) · Cd_ij · A_ij · sqrt(2 · |P_i − P_j| · ρ_ij)   [kg/s]
```

ρ_ij is the air density at the element, taken as the density of the upstream node.

For a duct with quadratic resistance:

```
P_i − P_j = (K_ij · ρ_ij) / (2 · A_ij²) · ṁ_ij · |ṁ_ij|   [Pa]
```

The product ṁ · |ṁ| preserves the sign (flow direction).

For a fan element from inlet node i to outlet node j:

```
P_j − P_i = ΔP_fan(Q_vol)   where Q_vol = ṁ_ij / ρ_ij   [Pa, m³/s]
```

### 4.2 Mass Balance at Each Node

At steady state, the sum of mass flows entering each node equals the sum leaving:

```
Σ_j ṁ_ij = 0   for each internal node i                    [kg/s]
```

External (ambient) nodes are fixed-pressure boundary conditions.

### 4.3 Linearisation for Iterative Solve

The nonlinear flow equations are linearised at each iteration step using Newton-Raphson
or a chord-slope method:

```
ṁ_ij^(k+1) = ṁ_ij^(k) + (dṁ/dΔP) · ΔP_correction          [kg/s]
```

Alternatively, a successive substitution (Picard iteration) is used for simpler networks.

The Jacobian matrix J is assembled from the linearised flow elements and solved:

```
J · ΔP = −F                                                  (pressure correction system)
```

Where F_i = Σ_j ṁ_ij (residual mass balance at node i).

---

## 5. Fan Modelling

### 5.1 Fan Curve Representation

Each fan is represented by a set of (Q_vol, ΔP_fan) data points measured at a reference
speed n_ref. The data must be supplied by the user from the manufacturer's curve.

ThermPro supports:
- Piecewise-linear interpolation between data points.
- Cubic spline interpolation (smoother; recommended for operating-point searches).

### 5.2 Fan Operating Point

The fan operating point is found iteratively. At each iteration:

1. Compute the system resistance curve: ΔP_system(Q) = Σ K_ij · ρ · Q² / (2 A²)
2. Interpolate the fan curve: ΔP_fan(Q)
3. Find Q* such that ΔP_fan(Q*) = ΔP_system(Q*) — i.e., the intersection.
4. Update ṁ* = ρ · Q*

The bisection method or regula falsi is used to find the intersection robustly.

### 5.3 Affinity Law Scaling

Fan affinity laws may be applied to scale from the manufacturer's reference speed to the
installed speed:

```
Q_2 = Q_1 · (n_2 / n_1)
ΔP_2 = ΔP_1 · (n_2 / n_1)²
P_shaft_2 = P_shaft_1 · (n_2 / n_1)³
```

These laws are valid only when:
- The fan operates in a geometrically similar flow regime.
- The density ratio ρ_2 / ρ_1 ≈ 1 (i.e., no major altitude or temperature change).
- The new operating point is within the manufacturer's data range.

The software shall display a warning and affinity-law-used flag on any result where
affinity scaling was applied.

### 5.4 Fan Heat Input

The fan motor and impeller add heat to the airstream:

```
Q_fan = (1 − η_fan) · P_shaft + P_motor_loss                [W]
```

For a fan inside the enclosure (heat not exhausted externally), Q_fan is added as a heat
source in the thermal network at the fan node.

### 5.5 Thermostat and Speed Control

For thermostat-controlled fans:
- Fan is OFF when T_sensor < T_setpoint_on
- Fan switches ON when T_sensor ≥ T_setpoint_on
- Fan switches OFF when T_sensor ≤ T_setpoint_off

For speed-controlled fans:
- Fan speed interpolated from user-supplied control curve: n = f(T_sensor)

Both control modes affect the fan curve used in the operating-point search.

---

## 6. Buoyancy Stack Pressure

Natural ventilation is driven by the density difference between warm internal air and
cooler external air. The equivalent stack pressure for a vertical separation H between
inlet and outlet centroids:

```
ΔP_stack = (ρ_ext − ρ_int) · g · H                          [Pa]
```

Using ideal-gas approximation:

```
ΔP_stack = ρ_ref · g · H · (T_int − T_ext) / T_ext          [Pa]
```

T_int is the average temperature of the air column inside the enclosure. Because T_int
depends on the thermal solution and the thermal solution depends on airflow, the stack
pressure and the thermal network are strongly coupled. The outer iteration (Section 8)
resolves this coupling.

---

## 7. Pathological Flow Condition Detection

The solver tests for and reports the following conditions after each converged solution:

| Condition | Detection Method | Severity |
|-----------|-----------------|----------|
| Reverse flow through a grille | ṁ direction opposite to design intent | WARNING |
| Short-circuit airflow | Air travels directly from inlet to outlet without passing through the device zone | WARNING |
| Recirculation loop | A closed circuit of airflow detected (sum of ṁ around closed path ≠ 0) | WARNING |
| Stagnant zone | Air cell velocity < 0.05 m/s and temperature rise > 10 K above adjacent flowing zone | WATCH |
| Inadequate exhaust area | ṁ_outlet / ṁ_required < 0.8 | WARNING |
| Blocked inlet | Inlet opening effective area < 20% of design due to obstruction | WARNING |
| Filter overload | ΔP_filter > 80% of fan stall pressure | WARNING |
| Fan stall | Q_vol < Q_stall (left of fan curve peak) | FAIL |
| Excessive local velocity | v_local > v_limit near sensitive component | WATCH |
| Mass imbalance at convergence | |Σṁ| / ṁ_inlet > 0.5% | Convergence failure |

For each detected condition, the solver records:
- Condition ID
- Location (element ID, node IDs)
- Calculated magnitude
- Threshold value
- Recommended action

---

## 8. Coupling with Thermal Network

The airflow and thermal networks are coupled as follows:

**Information from airflow to thermal:**
- Mass flow rates ṁ_ij → used as air-transport conductances G_air_ij in thermal matrix

**Information from thermal to airflow:**
- Node temperatures T_i → used to compute ρ_i(T_i) and buoyancy ΔP_stack

**Outer Iteration Procedure:**

```
Initialise T_i = T_ambient for all nodes
Initialise ṁ_ij = 0 for all elements

Loop until coupled convergence:
  1. Compute ρ_i = f(T_i) for all air nodes
  2. Compute ΔP_stack from temperature distribution
  3. Solve airflow network → get ṁ_ij, P_i, v_ij
  4. Update G_air_ij in thermal network
  5. Solve thermal network → get new T_i
  6. Compute ΔT = max|T_i_new − T_i_old|, Δṁ = max|ṁ_new − ṁ_old|/ṁ
  7. If ΔT < 0.1 K AND Δṁ < 0.5%: CONVERGED
  8. Else: apply under-relaxation and go to step 1

Max outer iterations: configurable (default: 50)
```

---

## 9. Visualisation Output

The following quantities are computed and passed to the visualisation module:

| Quantity | Unit | Display |
|----------|------|---------|
| ṁ_ij | kg/s | Arrow width proportional to mass flow |
| v_ij | m/s | Arrow label |
| P_i | Pa (gauge) | Pressure-node colour map |
| T_i | °C | Temperature colour of arrow (blue = cold, red = hot) |
| Q_vol_inlet | m³/s | Displayed at each inlet |
| Q_vol_outlet | m³/s | Displayed at each outlet |
| Direction reversal | — | Reverse-flow marker on affected element |
| Fan operating point | (Q*, ΔP*) | Plotted on fan curve chart |

Colour convention:
- Blue arrows: incoming air at or near ambient temperature
- Red/orange arrows: hot exhaust air
- Arrow temperature reflects air temperature at element midpoint
- Monochrome mode: arrows labelled with temperature value, width encodes flow rate

---

## 10. Limitations and Assumptions

| Limitation | Description |
|-----------|-------------|
| Incompressible flow | Air is treated as incompressible at each node. Valid for ΔP ≪ P_atm (always true in LV switchboards). |
| Steady-state only (initial) | Transient airflow not implemented in the first release. Architecture supports it. |
| No turbulence modelling | Turbulence effects in internal air volumes are not modelled. |
| Simplified view factor | View factors between openings use a simplified area-distance model, not a full radiosity calculation. |
| No humidity | Humidity is not modelled. Condensation risk is outside scope. |
| No acoustic effects | Sound power of fans is stored in the device library but not used in thermal calculations. |
| Fan stall instability | The solver detects stall but does not model the instability dynamics. |

---

*End of THERM-AFN-001*
