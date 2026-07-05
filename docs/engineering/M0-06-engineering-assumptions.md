# Engineering Assumptions — LV Switchboard Thermal Digital Twin

**Document:** M0-06  
**Milestone:** 0 (correction commit — revision 1)  
**Date:** 2026-07-03  
**Status:** UPDATED — Applied DR-003, DR-004, DR-005, DR-008, DR-009  
**Source:** Extracted from THERM-METH-001, THERM-EQN-001, THERM-NET-001, THERM-AFN-001,
THERM-DAT-001, THERM-ARCH-001 Rev 0.1/0.2; M0-08-decision-record.md

---

## 1. Purpose

This document lists every engineering assumption embedded in the ThermPro thermal model.
Each assumption must be reviewed and accepted by the responsible engineer before
Milestone 1 begins. Assumptions that are found to be unacceptable must either be
addressed by a design change or flagged as a known limitation in the user manual.

**Classification:** Each assumption is classified by its potential impact if wrong:

| Impact | Description |
|--------|-------------|
| HIGH | Could cause incorrect compliance verdict or unsafe derating |
| MEDIUM | Affects accuracy but result remains conservative or flagged |
| LOW | Minor accuracy effect; covered by overall validation tolerance |

---

## 2. Air Properties Assumptions

| ID | Assumption | Impact | Verification |
|----|-----------|--------|-------------|
| ASS-AIR-001 | Air treated as an ideal gas: ρ = P/(R_specific·T). | MEDIUM | Error < 0.3 % at 40 °C, 1 atm. Validated by UT-AIR-001. |
| ASS-AIR-002 | Air properties (μ, λ_f, cp, Pr) evaluated using polynomial fits valid 0–150 °C. Extrapolation outside this range raises a solver warning. | MEDIUM | Valid for all expected operating conditions in an LV switchboard. |
| ASS-AIR-003 | Volumetric expansion coefficient β = 1/T_film (ideal gas approximation). | LOW | Standard approximation for natural convection; error < 1 % at temperatures of interest. |
| ASS-AIR-004 | Air is treated as dry (zero humidity) for thermal property calculations. Humidity affects density by < 1 % at typical conditions. | LOW | Humidity affects IP rating compliance checks only; thermal model unaffected at < 2 K impact. |

---

## 3. Convection Assumptions

| ID | Assumption | Impact | Verification |
|----|-----------|--------|-------------|
| ASS-CONV-001 | Churchill-Chu correlation (1975) used for natural convection on vertical surfaces. Applicable for Ra = 10⁻¹ to 10¹². | MEDIUM | Standard correlation; widely validated. Error vs. experimental data typically < 5 %. |
| ASS-CONV-002 | McAdams correlations used for horizontal surfaces (up-facing and down-facing). | MEDIUM | Well-established; slightly conservative for up-facing. |
| ASS-CONV-003 | Gnielinski correlation used for forced convection in ducts and over surfaces. Re range: 3000–5×10⁶. | MEDIUM | Validated by BM-004. |
| ASS-CONV-004 | Convection is treated as uncoupled from airflow within a thermal cell (one-way coupling). Full coupling requires CFD (MODE 4). | HIGH | This is a fundamental limitation of the nodal approach. Documented in known limitations. |
| ASS-CONV-005 | Internal surfaces of compartments are treated as flat plates for convection calculation. Fins, ribs, and irregular geometry are not modelled. | MEDIUM | User must verify applicability for complex geometries. |
| ASS-CONV-006 | Mixed convection effects (combined forced + natural) are not explicitly modelled. When forced ventilation is active (MODE 3), natural convection is suppressed. | MEDIUM | Conservative for upward-flow configurations; may under-predict cooling in some geometries. |

---

## 4. Radiation Assumptions

| ID | Assumption | Impact | Verification |
|----|-----------|--------|-------------|
| ASS-RAD-001 | All surfaces are diffuse grey emitters. Spectral effects are ignored. | LOW | Appropriate for surfaces in the 20–200 °C range typical of switchboards. |
| ASS-RAD-002 | External enclosure radiation is modelled as a single grey surface radiating to a large enclosure (surroundings) at ambient temperature. View factor = 1. | MEDIUM | Appropriate when enclosure is well clear of surroundings. May over-predict cooling for clustered cabinets. |
| ASS-RAD-003 | Internal radiation between surfaces within a compartment is linearised (h_r = 4·ε_eff·σ·T_mean³) for matrix assembly. Re-linearised at each outer iteration. | MEDIUM | Valid when ΔT between surfaces is small (< 50 K). Maximum linearisation error < 1 % per iteration. |
| ASS-RAD-004 | Default external surface emissivity: 0.9 (RAL-colour powder-coated steel). | MEDIUM | User must override for bare metal (ε ≈ 0.1–0.3) or other finishes. |
| ASS-RAD-005 | Default busbar emissivity: 0.05 (bright copper). | HIGH | Painted or oxidised busbars have ε ≈ 0.7–0.9. Incorrect emissivity can alter busbar temperature by 5–15 K. User must provide actual value. |
| ASS-RAD-006 | Radiation from devices is absorbed by the compartment air cell (lumped). Detailed view-factor calculation between devices is not implemented in MODE 2/3. | MEDIUM | Suitable for MODE 2/3; detailed view factors require MODE 4. |

---

## 5. Joule Loss and Electrical Assumptions

| ID | Assumption | Impact | Verification |
|----|-----------|--------|-------------|
| ASS-ELEC-001 | Skin effect and proximity effect are handled by a staged K_AC methodology (DR-003). Level 1: R_DC(T) = ρ_ref·[1+α(T−T_ref)]·L/A always computed. Level 2: R_AC = K_AC × R_DC(T) when K_AC is available from a qualified source (manufacturer, validated test, approved correlation, geometry/frequency library, or explicit user input). K_AC = 1.0 with a mandatory non-suppressible warning is the fallback when no qualified source is available. Level 3 (numerical EM) reserved for a future release. | HIGH | Skin depth in copper at 50 Hz ≈ 9.3 mm; significant for busbars > 18 mm wide. K_AC from manufacturer or validated correlation eliminates this risk. Warning is non-suppressible when K_AC = 1.0 is used. Resolved: OQ-001 → DR-003. |
| ASS-ELEC-002 | Proximity effect is included in the K_AC factor defined in ASS-ELEC-001. No separate proximity factor is applied. | HIGH | K_AC from manufacturer AC resistance measurement accounts for both skin and proximity effects together. User must not apply a separate proximity multiplier when K_AC already covers it. Resolved: OQ-001 → DR-003. |
| ASS-ELEC-003 | Current is uniformly distributed across the cross-section of each busbar segment at the Level 1 (R_DC) and Level 2 (K_AC × R_DC) computation stages. | MEDIUM | Non-uniform distribution is a consequence of skin/proximity, which are captured by K_AC at Level 2. Residual non-uniformity within the cross-section is a Level 3 concern. |
| ASS-ELEC-004 | Eddy current losses in enclosure walls (magnetic field effects) are not modelled. | MEDIUM | Typically < 5 % of total loss for steel-walled enclosures at rated current. Stainless steel: negligible. |
| ASS-ELEC-005 | Default temperature coefficient of resistance for copper: α = 0.00393 K⁻¹ at 20 °C. | LOW | Standard value per IEC 60228. User can override per conductor. |
| ASS-ELEC-006 | Default temperature coefficient of resistance for aluminium: α = 0.00403 K⁻¹ at 20 °C. | LOW | Standard value. |
| ASS-ELEC-007 | Contact resistance follows a strict data hierarchy per DR-004: MEASURED > MANUFACTURER > JOINT_LIBRARY > USER_ASSUMPTION. The universal 10 µΩ default has been removed. When joint_condition = UNKNOWN, a single-value computation is not permitted; the solver requires sensitivity_min/nominal/max_ohm and runs sensitivity scenarios. The new joint_condition enum is: NEW_VALIDATED, NEW_ASSUMED, MEASURED, AGED, DEGRADED, UNKNOWN. | HIGH | Contact resistance varies by 2–3 orders of magnitude with surface condition, torque, and age. The hierarchy forces the engineer to declare the provenance of the value used. UNKNOWN condition triggers scenarios rather than a silent worst-case. Resolved: OQ-002 → DR-004. |
| ASS-ELEC-008 | Quadratic device loss model P = a·I² + b·I + c is valid across the full current range 0 to I_rated. Extrapolation beyond rated current is flagged as a warning. | MEDIUM | Coefficients derived from manufacturer loss curves. |

---

## 6. Geometry and Network Assumptions

| ID | Assumption | Impact | Verification |
|----|-----------|--------|-------------|
| ASS-GEO-001 | Each compartment is modelled as a single thermal cell (lumped air node). Air temperature is uniform within a cell. | HIGH | Stratification within a compartment is not resolved. The nodal method is a zonal model, not a field model. User must verify appropriateness. |
| ASS-GEO-002 | Internal partitions are modelled as planar resistances. Thermal mass (transient storage) is not included in the steady-state solver. | MEDIUM | Steady-state solver only; transient thermal mass is a deferred feature. |
| ASS-GEO-003 | Busbar segments are modelled as 1D thermal resistors with heat generation. Cross-sectional temperature variation is neglected. | LOW | Valid for slender busbars (L/d > 10). |
| ASS-GEO-004 | The coordinate origin is the lower-left-front corner of each enclosure with X (width), Y (height), Z (depth). All geometry must be expressed in SI units (metres). | LOW | Enforced by geometry validator. |
| ASS-GEO-005 | Adjacent enclosures share a common adiabatic wall (no heat transfer between cubicles). | MEDIUM | Conservative (underestimates heat transfer between cubicles). User may override with specific conductance. Open question OQ-005. |

---

## 7. Airflow Network Assumptions

| ID | Assumption | Impact | Verification |
|----|-----------|--------|-------------|
| ASS-FLOW-001 | Orifice discharge coefficient Cd = 0.6 for sharp-edged openings (default). | MEDIUM | Literature range: 0.55–0.65. User must provide measured or manufacturer Cd for louvres and filters. |
| ASS-FLOW-002 | Airflow is incompressible (constant density within each network element). Density is updated between outer iterations using calculated temperature. | LOW | Mach number < 0.01 at all flow rates of interest; incompressible assumption valid. |
| ASS-FLOW-003 | Fan P-Q curve is modelled as a piecewise-linear interpolation between manufacturer data points. | LOW | Sufficient for steady-state operating point. Dynamic fan characteristics (surge, stall) are not modelled. |
| ASS-FLOW-004 | Filter pressure drop is constant at nominal flow rate. Filter blockage over time is not modelled. | MEDIUM | User must schedule filter cleaning or replace the pressure drop value for dirty filter condition. |
| ASS-FLOW-005 | Fan reverse flow is handled by six explicit operating states per DR-005: FORWARD_OPERATING, STOPPED_FREE_FLOW, STOPPED_WITH_DAMPER, FAILED_OPEN, FAILED_BLOCKED, ESTIMATED_REVERSE_FLOW. Reverse flow is NOT clamped to zero unless a physical non-return damper is present (STOPPED_WITH_DAMPER state). Normal fan P-Q curves are NOT extrapolated beyond their validated data points. | HIGH | Clamping to zero was unconservative for multi-fan configurations where reverse flow occurs at partial load. The six-state model allows the engineer to declare the actual physical situation. Resolved: OQ-006 → DR-005. |
| ASS-FLOW-006 | Buoyancy is modelled as a stack pressure: ΔP = ρ·g·H·β·ΔT. Valid for H < 3 m. | LOW | Most LV switchboards are < 2.5 m. |

---

## 8. IEC TR 60890 (MODE 1) Assumptions

| ID | Assumption | Impact | Verification |
|----|-----------|--------|-------------|
| ASS-M1-001 | IEC TR 60890 coefficient tables are supplied by the user (administrator-imported licensed dataset). The system ships with null values only. | HIGH | Missing dataset → MODE 1 unavailable. This is intentional by design (CR-ENG-002). |
| ASS-M1-002 | IEC TR 60890 is applicable only to naturally ventilated enclosures. | HIGH | Enforced automatically: any Fan entity in the enclosure disables MODE 1. |
| ASS-M1-003 | IEC TR 60890 assumes enclosure height H ≤ 2 m and power loss density below the empirical range limits. | HIGH | Applicability check performed before calculation; user warned if outside range. |

---

## 9. Arc Flash — REMOVED FROM MVP SCOPE (DR-008)

> Arc-flash functionality has been entirely removed from the ThermPro MVP (DR-008, approved
> 2026-07-03). All arc-flash assumptions (ASS-ARC-001, ASS-ARC-002, ASS-ARC-003) are
> withdrawn. CR-ENG-007 (arc-flash INFORMATIVE label) is also withdrawn (DR-012).
>
> Arc flash may become a separate future module sharing project data but with an independent
> engine, schemas, validation suite, and reports. No arc-flash architecture shall be designed
> in M1–M5.

---

## 10. Numerical and Convergence Assumptions

| ID | Assumption | Impact | Verification |
|----|-----------|--------|-------------|
| ASS-NUM-001 | The thermal network is solved at steady state. Time-dependent (transient) effects are not modelled. | HIGH | This is a steady-state design tool. Transient capability is a deferred feature. |
| ASS-NUM-002 | The linear system G·T = Q is solved using scipy.sparse.linalg.spsolve (direct sparse solver). For large models (> 10,000 nodes), iterative solvers may be required. | MEDIUM | Performance benchmark NFR-PERF-001 verifies 60 s limit for typical enclosure. |
| ASS-NUM-003 | Default relaxation factor ω = 0.7. Convergence is not guaranteed for all physically valid inputs. | MEDIUM | If non-convergence occurs, the result is flagged NON_CONVERGED. User must adjust ω or simplify model. |
| ASS-NUM-004 | Convergence criterion: max(|T_new − T_old|) < 0.1 K (default). This is tighter than required for engineering decisions but ensures result stability. | LOW | Configurable per solver_settings. |

---

## 11. Data Confidence Assumptions

| ID | Assumption | Impact | Verification |
|----|-----------|--------|-------------|
| ASS-DATA-001 | Device loss data with confidence = UNKNOWN is handled through explicit scenarios per DR-009. The silent +20 % safety margin has been removed. The engineer must supply power_loss_min_W, power_loss_nominal_W, and power_loss_max_W. The solver runs three scenario calculations (min, nominal, max). Report wording states the confidence level and the range of results. | HIGH | Resolved: silent margin was neither visible to the user nor explainable in a compliance report. Explicit scenarios are fully documented in the audit trail. Resolved: DR-009. |
| ASS-DATA-002 | Contact resistance data with confidence = UNKNOWN requires sensitivity scenarios as specified in ASS-ELEC-007. A default value is no longer permitted for UNKNOWN condition joints. See DR-004. | HIGH | Resolved: OQ-002 → DR-004. |
| ASS-DATA-003 | Manufacturer derating tables are loaded into DeviceLibrary and assumed to be valid for the stated conditions. No independent verification is performed by the software. | MEDIUM | User responsibility to ensure library data quality. |
