# Requirements — LV Switchboard Thermal Digital Twin

**Document ID:** THERM-REQ-001  
**Revision:** 0.1 (Draft for Engineering Review)  
**Date:** 2026-07-03  
**Status:** Pending Approval

---

## 1. Purpose

This document defines the functional requirements (FR), non-functional requirements (NFR),
and constraint requirements (CR) for the LV Switchboard Thermal Digital Twin platform
(ThermPro). Every requirement is assigned a unique code for traceability to equations,
software modules, and tests.

---

## 2. Requirement Code Structure

```
FR-{domain}-{number}   Functional requirement
NFR-{domain}-{number}  Non-functional requirement
CR-{domain}-{number}   Constraint requirement

Domains:
  PROJ   Project and session management
  GEO    Geometry and layout
  MAT    Materials and component data
  ELEC   Electrical loading
  THERM  Thermal physics and calculation
  FLOW   Airflow and ventilation
  SOLV   Solver and numerics
  DERV   Derating and thermal limits
  VIS    Visualisation and results display
  OPT    Optimisation suggestions
  RPT    Reporting and export
  AUD    Audit and reproducibility
  STD    Standards compliance
  VALID  Validation and testing
```

---

## 3. Functional Requirements

### 3.1 Project and Session Management

| ID | Requirement |
|----|------------|
| FR-PROJ-001 | The system shall allow a user to create, name, save, open, and delete thermal analysis projects. |
| FR-PROJ-002 | Each project shall store: project name, customer, assembly designation, standard profile (one or more of IEC 61439, UL 891, UL 1558, ANSI/IEEE C37.20.1, or other), system voltage, frequency, service conditions (ambient temperature maximum and 24-hour average, relative humidity, altitude, pollution degree), indoor/outdoor classification, IP rating, reference temperature, and free-text notes. |
| FR-PROJ-003 | The system shall support multiple independent enclosures within a single project. |
| FR-PROJ-004 | The system shall maintain a full revision history of every project state. |
| FR-PROJ-005 | The system shall prevent accidental loss of unsaved work with an auto-save mechanism and explicit save/discard controls. |

### 3.2 Geometry and Layout

| ID | Requirement |
|----|------------|
| FR-GEO-001 | The system shall allow the user to create an enclosure by entering external height, width, depth, wall thickness, and material. |
| FR-GEO-002 | The system shall maintain separate internal and external dimension records for every enclosure. |
| FR-GEO-003 | The system shall use a coordinate origin at the lower-left-front corner of each enclosure with X (width), Y (vertical), Z (depth) axes in SI units. |
| FR-GEO-004 | The system shall support the following installation types: free-standing, wall-mounted, floor-mounted, flush-mounted, and ceiling-mounted. |
| FR-GEO-005 | The system shall allow adjacent cubicles to be specified with their dimensions and relative positions. |
| FR-GEO-006 | The system shall allow the user to mark rear wall, side wall, ceiling, floor, plinth, and roof surfaces as restricted (covered, obstructed, or against a wall) and as exposed. |
| FR-GEO-007 | The system shall allow the user to add doors and removable panels with their hinge position, dimensions, and material. |
| FR-GEO-008 | The system shall allow the user to create internal compartments within an enclosure. |
| FR-GEO-009 | The system shall allow the user to add vertical and horizontal partitions with material, thickness, and perforation properties. |
| FR-GEO-010 | The system shall allow the user to add openings between compartments with dimensions, position, and flow resistance. |
| FR-GEO-011 | The system shall allow the user to select Form 1, 2, 3, or 4 arrangement per IEC 61439. |
| FR-GEO-012 | The system shall display a dimensioned engineering drawing of the enclosure in plan and elevation views. |
| FR-GEO-013 | The system shall assign every geometry entity a UUID, parent enclosure reference, position, orientation, material, source, and timestamps. |
| FR-GEO-014 | The system shall detect and report: overlapping devices, devices outside the enclosure boundary, busbars passing through solid objects, blocked openings, fans blocked by equipment, and insufficient clearances. |
| FR-GEO-015 | The system shall support copy, mirror, rotate, align, group, lock, and layer operations on geometry entities. |
| FR-GEO-016 | The system shall provide undo/redo with a configurable history depth. |

### 3.3 Heat-Source Placement

| ID | Requirement |
|----|------------|
| FR-GEO-017 | The system shall allow devices, busbars, and conductors to be placed at exact X, Y, Z positions with rotation. |
| FR-GEO-018 | The system shall provide drag-and-drop placement from a component library onto the enclosure drawing. |
| FR-GEO-019 | The system shall assign every heat source to a compartment and thermal cell automatically based on its position. |
| FR-GEO-020 | The system shall display clearance and obstruction warnings in real time during placement. |
| FR-GEO-021 | The system shall support grid snapping and alignment guides during placement. |

### 3.4 Ventilation Placement

| ID | Requirement |
|----|------------|
| FR-FLOW-001 | The system shall allow placement of: inlet grille, outlet grille, filtered inlet, natural opening, supply fan, exhaust fan, internal circulation fan, duct, flap/damper, and leakage opening. |
| FR-FLOW-002 | Every ventilation element shall store: position (X, Y, Z), free area, flow resistance, orientation, and elevation. |
| FR-FLOW-003 | Every fan element shall store or allow import of a pressure-flow (P-Q) curve. |
| FR-FLOW-004 | The system shall support speed-controlled and thermostat-controlled fan operation with control curves or setpoints. |
| FR-FLOW-005 | The system shall allow fan affinity-law scaling only when the user explicitly enables it and the software labels the result accordingly. |

### 3.5 Electrical Loading

| ID | Requirement |
|----|------------|
| FR-ELEC-001 | The system shall allow entry of rated and actual current for every circuit. |
| FR-ELEC-002 | The system shall allow entry of load diversity and simultaneity factors. |
| FR-ELEC-003 | The system shall allow entry of harmonic content as a total harmonic distortion factor or per-harmonic spectrum. |
| FR-ELEC-004 | The system shall calculate Joule losses from current and temperature-dependent resistance. |
| FR-ELEC-005 | The system shall accept direct manufacturer loss values as an alternative to calculated losses. |
| FR-ELEC-006 | The system shall accept measured loss values. |
| FR-ELEC-007 | The system shall clearly distinguish between data labelled: CALCULATED, MANUFACTURER, MEASURED, and ASSUMED. |
| FR-ELEC-008 | The system shall apply a low-confidence flag and sensitivity flag when ASSUMED data are used for any significant heat source. |
| FR-ELEC-009 | The system shall model busbar joint and terminal losses using an explicit joint entity with temperature-dependent contact resistance, assembly torque metadata, and a health-state modifier (NOMINAL, DEGRADED, UNKNOWN). |
| FR-ELEC-010 | The system shall model cable losses using cable length, conductor cross-section, material, insulation type, and bundle correction factor as independent inputs, not as a percentage of total losses. |
| FR-ELEC-011 | The system shall model control transformer losses as separate no-load (core) and load-dependent (copper) components. |

### 3.6 Mesh and Nodal-Grid Definition

| ID | Requirement |
|----|------------|
| FR-THERM-001 | The system shall automatically generate a thermal cell grid from the enclosure geometry. |
| FR-THERM-002 | The grid generator shall refine cells near busbars, devices, openings, partitions, and fans. |
| FR-THERM-003 | The system shall allow the user to manually refine the grid in selected regions. |
| FR-THERM-004 | The system shall display the generated thermal cells and allow the user to inspect individual cell dimensions and assignments. |

### 3.7 Calculation

| ID | Requirement |
|----|------------|
| FR-SOLV-001 | The system shall perform applicability validation before any calculation run. |
| FR-SOLV-002 | The system shall perform geometry validation before any calculation run. |
| FR-SOLV-003 | The system shall perform data completeness and consistency validation before any calculation run. |
| FR-SOLV-004 | The system shall calculate airflow through the enclosure using a pressure-node network. |
| FR-SOLV-005 | The system shall calculate heat transfer using a nodal thermal network. |
| FR-SOLV-006 | The system shall iterate device derating and power losses until convergence. |
| FR-SOLV-007 | The system shall test and report numerical convergence explicitly. |
| FR-SOLV-008 | The system shall never present a result from an unconverged calculation as valid without a prominent warning. |
| FR-SOLV-009 | The system shall generate explicit warnings for every missing data item and every weak assumption used during calculation. |

### 3.8 Calculation Modes

| ID | Requirement |
|----|------------|
| FR-STD-001 | The system shall implement MODE 1: IEC TR 60890 for eligible natural-ventilation or closed-enclosure arrangements. |
| FR-STD-002 | The system shall implement MODE 2: Nodal Thermal Network for position-sensitive analysis with distributed sources, partitions, and openings. |
| FR-STD-003 | The system shall implement MODE 3: Forced-Ventilation Airflow Network for fans, grilles, filters, ducts, and pressure-driven flow. |
| FR-STD-004 | The system shall implement MODE 4: CFD Export/Import Adapter architecture for future external solver integration. |
| FR-STD-005 | The system shall display the active calculation mode, its applicability status, assumptions, limitations, and convergence status for every result. |
| FR-STD-006 | Forced ventilation shall automatically disqualify a result from IEC TR 60890 compliance unless an authorised current method explicitly supports the configuration. |

### 3.9 IEC TR 60890 Module

| ID | Requirement |
|----|------------|
| FR-STD-007 | The system shall validate every IEC TR 60890 eligibility condition before executing MODE 1. |
| FR-STD-008 | The eligibility check shall return one of: Eligible, Eligible with warnings, Not Eligible, or Insufficient Information. |
| FR-STD-009 | The system shall report every failed eligibility condition. |
| FR-STD-010 | The system shall calculate: effective cooling surface, installation factors, partition factor, enclosure constant, temperature-distribution factor, mid-height temperature rise, top temperature rise, and interpolated temperature by height. |
| FR-STD-011 | Standard coefficient datasets shall be versioned, attributed, and replaceable by the administrator. |
| FR-STD-012 | The report shall state the standard edition and coefficient dataset version used. |

### 3.10 Results Display

| ID | Requirement |
|----|------------|
| FR-VIS-001 | The system shall display a false-colour temperature heat map overlaid on the enclosure drawing. |
| FR-VIS-002 | The system shall display directional airflow arrows with colour indicating temperature and annotations for velocity magnitude and mass-flow rate. |
| FR-VIS-003 | The system shall display hot spots with coordinates, temperature, temperature rise, limit, margin, likely contributors, and recommended actions. |
| FR-VIS-004 | The system shall display absolute temperature and temperature rise for every device, busbar segment, and air cell. |
| FR-VIS-005 | The system shall display permissible current and thermal margin for every device and busbar. |
| FR-VIS-006 | The system shall display a pass/warning/fail/not-verifiable status for every component and zone. |
| FR-VIS-007 | The system shall provide views: front, rear, left, right, top, section, 3D, thermal, airflow, losses, and validation. |
| FR-VIS-008 | The system shall provide a monochrome mode for engineering report output. |

### 3.11 Optimisation

| ID | Requirement |
|----|------------|
| FR-OPT-001 | The system shall generate optimisation suggestions when thermal margins are exceeded or are narrow. |
| FR-OPT-002 | Suggestions shall be limited to: moving devices, relocating inlet/outlet, increasing free area, changing fan capacity, reducing filter pressure loss, increasing enclosure dimensions, separating heat sources, and changing busbar size/arrangement. |
| FR-OPT-003 | The system shall never apply an optimisation change without explicit user approval. |
| FR-OPT-004 | Every suggestion shall be linked to specific calculated evidence. |

### 3.12 Comparison

| ID | Requirement |
|----|------------|
| FR-VIS-009 | The system shall allow the user to run and save multiple design alternatives. |
| FR-VIS-010 | The system shall provide a side-by-side comparison view of temperature and airflow results across alternatives. |

### 3.13 Reporting and Export

| ID | Requirement |
|----|------------|
| FR-RPT-001 | The system shall generate a PDF calculation report. |
| FR-RPT-002 | The system shall generate an XLSX data export. |
| FR-RPT-003 | The report shall include: project inputs, enclosure drawings, device and ventilation coordinates, calculation method and mode, governing equations, assumptions, data provenance, convergence records, heat maps, hot-spot table, compliance/applicability statements, limitations, and an audit checksum. |
| FR-RPT-004 | The audit checksum shall cover all inputs, geometry, library versions, solver settings, and results. |

### 3.14 Audit and Reproducibility

| ID | Requirement |
|----|------------|
| FR-AUD-001 | Every calculation run shall save a versioned, immutable snapshot of all inputs, geometry, library versions, solver settings, results, warnings, and convergence trace. |
| FR-AUD-002 | Editing a material or device library record shall never silently alter a previously saved calculation result. |
| FR-AUD-003 | Every result shall carry a timestamp, user identifier, and snapshot checksum. |

### 3.15 Material and Component Libraries

| ID | Requirement |
|----|------------|
| FR-MAT-001 | The system shall maintain versioned libraries for: enclosure materials, conductors, devices, and ventilation devices. |
| FR-MAT-002 | Every library record shall carry a source document, source page, data confidence level, and revision history. |
| FR-MAT-003 | The system shall allow an administrator to import licensed manufacturer data via a defined template format. |
| FR-MAT-004 | The system shall prohibit the use of invented manufacturer data. Missing data must either halt the calculation with an explicit request, use an ASSUMED value with a low-confidence flag, or be entered by the user. |

### 3.16 Standards Compliance — North American

| ID | Requirement |
|----|------------|
| FR-STD-013 | The system shall allow the engineer to select a standards profile (IEC, North American UL/ANSI, or both) per project. |
| FR-STD-014 | When the North American profile is selected, the system shall apply UL 891 / UL 1558 / ANSI/IEEE C37.20.1 temperature limits for compliance assessment while using the same thermal solver output. |
| FR-STD-015 | The compliance assessment layer shall be decoupled from the thermal solver so that the same temperature field can be assessed against different standard families without re-running the solver. |

### 3.17 Arc-Flash Safety Module

| ID | Requirement |
|----|------------|
| FR-ARC-001 | The system shall implement an arc-flash hazard screening module using the IEEE 1584-2018 parametric method. |
| FR-ARC-002 | The arc-flash module shall accept: bolted fault current, fault clearing time, electrode configuration (VCB, VCBB, HCB, VOA, HOA), enclosure size, and working distance. |
| FR-ARC-003 | The arc-flash module shall output: arcing current (kA), incident energy (cal/cm²), arc-flash protection boundary (m), and required PPE category per NFPA 70E. |
| FR-ARC-004 | All arc-flash results shall be labelled INFORMATIVE and shall carry a disclaimer requiring qualified engineer review before use in safety labels or work procedures. |
| FR-ARC-005 | The arc-flash module shall provide a separate adiabatic conductor-heating check: I²t_limit for the conductor versus applied I²t, with PASS / FAIL output. |
| FR-ARC-006 | The arc-flash module shall reference IEC TR 61641 for internal-arc enclosure considerations when the IEC standards profile is active. |

### 3.18 Service Conditions

| ID | Requirement |
|----|------------|
| FR-SVC-001 | The system shall store service conditions per project: maximum ambient temperature, 24-hour average ambient temperature, relative humidity, altitude, and pollution degree. |
| FR-SVC-002 | The system shall apply the 24-hour average ambient temperature as the reference for IEC 61439 temperature-rise limits (maximum ambient + 5 K average rule). |
| FR-SVC-003 | The system shall warn the engineer when service conditions exceed IEC 61439-1 Table 1 limits (40 °C max, 35 °C 24 h average, 2000 m altitude). |
| FR-SVC-004 | Altitude correction factors shall be applied to convection coefficients when the project altitude exceeds 2000 m. |

---

## 4. Non-Functional Requirements

| ID | Requirement |
|----|------------|
| NFR-PERF-001 | A steady-state nodal thermal solve for an enclosure with up to 500 thermal cells shall complete within 30 seconds on reference hardware. |
| NFR-PERF-002 | The 2D drawing editor shall maintain ≥ 30 fps with up to 200 placed objects. |
| NFR-PERF-003 | Long calculations shall run asynchronously with live progress feedback. |
| NFR-PERF-004 | Reduced-order model (ROM) evaluations for parameter sweeps and uncertainty quantification shall complete in sub-second to a few seconds per sample. |
| NFR-PERF-005 | The arc-flash screening module shall return results within 5 seconds for a single calculation. |
| NFR-ACC-001 | Temperature results shall carry an explicit accuracy statement based on validation status, data confidence, and model limitations. |
| NFR-ACC-002 | The system shall not claim absolute accuracy without supporting test-data comparison. |
| NFR-AUD-001 | All calculation results shall be reproducible bit-for-bit from the saved input snapshot. |
| NFR-SEC-001 | User data shall be isolated per authenticated user and project. |
| NFR-SEC-002 | Calculation reports shall carry an integrity checksum so any post-generation modification is detectable. |
| NFR-MAINT-001 | The numerical engine shall be deployable and testable independently of the web application. |
| NFR-MAINT-002 | All public module interfaces shall have unit tests achieving ≥ 90% line coverage. |
| NFR-USAB-001 | All engineering quantities shall display with their unit symbol. |
| NFR-USAB-002 | All model assumptions shall be visible in the UI without navigating to the report. |
| NFR-I18N-001 | Display units shall be user-configurable (SI, mixed SI/imperial for dimensions). |

---

## 5. Constraint Requirements

| ID | Constraint |
|----|-----------|
| CR-LAW-001 | The system shall not reproduce copyrighted standard tables unless a valid licence is held. |
| CR-LAW-002 | Manufacturer component data shall not be incorporated without licence or explicit permission. |
| CR-ENG-001 | SI units shall be used for all internal calculations. |
| CR-ENG-002 | Radiation calculations shall use absolute temperature in kelvin. |
| CR-ENG-003 | Busbar resistance and loss shall be evaluated at the calculated conductor temperature, not at 20 °C only. |
| CR-ENG-004 | IEC TR 60890 MODE 1 shall be disabled automatically for any configuration involving forced ventilation unless an authorised current method explicitly permits it. |
| CR-ENG-005 | The system shall not claim design verification per IEC 61439 solely on the basis of this software's calculations. |
| CR-ENG-006 | The CFD Export/Import adapter (MODE 4) shall be clearly labelled as an adapter to an external solver; the reduced-order solver shall never be described as CFD. |
| CR-TECH-001 | The numerical engine shall accept a versioned JSON calculation input and return a versioned JSON result. |
| CR-TECH-002 | The numerical engine shall have no direct dependency on FastAPI or the database. |
| CR-ENG-007 | Arc-flash results shall always carry an INFORMATIVE label and a disclaimer. The software shall never present IEEE 1584-2018 screening results as a substitute for a formal arc-flash hazard analysis. |
| CR-ENG-008 | Joint losses shall never be subsumed into homogeneous busbar resistivity. Each joint entity shall maintain its own contact resistance and health state. |
| CR-ENG-009 | Compliance interpretation (PASS/FAIL against temperature limits) shall be standard-profile-aware. The same temperature value may produce different compliance outcomes under IEC 61439 versus UL/ANSI profiles. |

---

## 6. Scope Boundary

The following are explicitly outside the scope of the initial platform:

- Full Computational Fluid Dynamics (CFD) solving — handled externally via MODE 4 adapter.
- Protection relay coordination, arc flash, or short-circuit analysis.
- Acoustic noise prediction.
- Mechanical stress analysis.
- EMC/EMI shielding calculation.
- Utility billing or power-quality monitoring.
- Real-time SCADA data integration (may be added in a later phase).

---

*End of THERM-REQ-001*
