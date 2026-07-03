# Milestone Plan — LV Switchboard Thermal Digital Twin

**Document ID:** THERM-MILE-001  
**Revision:** 0.1 (Draft for Engineering Review)  
**Date:** 2026-07-03  
**Status:** Pending Approval

---

## 1. Purpose

This document defines the 14 implementation milestones for ThermPro, their objectives,
deliverables, dependencies, exit criteria, and effort bands. Calendar dates are not
assigned here; they require project-planning input from the engineering team.

---

## 2. Milestone Dependency Graph

```
M1 ──► M2 ──► M3 ──► M4 ──► M5 ──► M6 ──► M7 ──► M8
                │                                    │
                └──────────────────────────────────► M9 ──► M10
                                                     │
                M11 (can start after M6) ──────────► │
                                                     ▼
                                               M12 ──► M13 ──► M14
```

M11 (IEC TR 60890 module) requires basic thermal calculation (M5/M6) but does not
require the coupled airflow solver (M7/M8). It can be developed in parallel with M7.

---

## 3. Milestones

---

### Milestone 1 — Project Structure, Domain Types, Units, Dataset Versioning, Validation

**Objective:** Establish the entire development skeleton: repository structure, module
packages, type definitions, unit system, library versioning, and validation framework.
This milestone produces no user-visible functionality but creates the foundation on which
all later milestones build.

**Deliverables:**
1. Repository structure per THERM-ARCH-001 §5 (`thermpro_engine/`, `backend/`, `frontend/`, `tests/`)
2. Python package `thermpro_engine` with all sub-module stubs and type stubs.
3. Pydantic models for `InputSnapshot` and `ResultSnapshot` (THERM-DAT-001 §6).
4. Air property functions (`air_properties.py`) with unit tests UT-AIR-001/002/003.
5. Unit system: SI internal; display unit conversion functions.
6. Versioning infrastructure: `MaterialLibrary`, `DeviceLibrary`, `ConductorLibrary`,
   `VentilationDeviceLibrary` database models and Alembic migrations.
7. Dataset import template files (empty JSON templates for each library).
8. CI pipeline: pytest, mypy, coverage, import-graph check.
9. Docker Compose development environment (postgres, redis, api stub, worker stub, frontend stub).

**Exit Criteria:**
- [ ] `thermpro_engine` imports cleanly with no type errors (mypy --strict).
- [ ] UT-AIR-001, UT-AIR-002, UT-AIR-003 pass.
- [ ] InputSnapshot and ResultSnapshot serialise/deserialise without data loss.
- [ ] Database migrations run cleanly from empty schema.
- [ ] CI pipeline runs and passes on every commit.
- [ ] Docker Compose `up` produces all services in healthy state.

**Effort band:** Medium (2–4 weeks)

---

### Milestone 2 — 2D Enclosure Editor and Geometry Persistence

**Objective:** A working 2D drawing editor in which the engineer can create and modify
enclosure geometry, with all objects persisted as engineering entities.

**Deliverables:**
1. React/Konva.js enclosure drawing canvas.
2. Enclosure, Surface, Compartment, Partition, ExternalOpening entity CRUD (API + database).
3. Coordinate system (origin at lower-left-front; X, Y, Z axes; SI storage).
4. Dimensioned drawing view (front elevation and plan).
5. Grid, snap, zoom, pan.
6. Inspector panel for selected entity properties.
7. Basic undo/redo (Zustand history slice).
8. FR-GEO-001 through FR-GEO-012 (basic geometry and display).

**Exit Criteria:**
- [ ] Engineer can create an enclosure, add compartments and partitions, and save.
- [ ] All geometry entities persist across page reload.
- [ ] Dimensions displayed correctly in the drawing.
- [ ] Undo/redo works for 10 consecutive operations.
- [ ] Unit tests cover geometry entity creation, update, delete.

**Effort band:** Large (4–6 weeks)

---

### Milestone 3 — Device, Busbar, Conductor, Partition, and Ventilation Placement

**Objective:** Complete heat-source and ventilation placement with collision detection
and compartment assignment.

**Deliverables:**
1. Device placement from library (drag-drop, inspector, position form).
2. Busbar run drawing (click start/end points; segment properties).
3. Conductor routing.
4. Fan and opening placement on enclosure surfaces.
5. Collision detection for all placed entities (FR-GEO-014).
6. Compartment auto-assignment for all placed entities.
7. Clearance and obstruction warnings (FR-GEO-020).
8. Loading table (Step 5 electrical loading: FR-ELEC-001 to FR-ELEC-008).

**Exit Criteria:**
- [ ] All placement entity types can be placed, moved, and deleted.
- [ ] Overlap detection fires for intersecting devices.
- [ ] Compartment assignment is correct after placement and after moving.
- [ ] Loading table shows calculated vs. actual loss for each circuit.
- [ ] Data confidence flags appear for ASSUMED loss values.

**Effort band:** Large (4–6 weeks)

---

### Milestone 4 — Heat-Loss Engine

**Objective:** Implement the complete Joule and device heat-loss calculation engine with
temperature-dependent resistance and derating.

**Deliverables:**
1. `thermpro_engine/physics/joule.py` — complete implementation.
2. `thermpro_engine/physics/derating.py` — complete implementation.
3. All UT-JOULE-* and UT-DERATING-* unit tests pass.
4. API endpoint to calculate losses for a given input snapshot (without solving temperatures).
5. Frontend: loss preview table populated from API.

**Exit Criteria:**
- [ ] All UT-JOULE unit tests pass.
- [ ] All UT-DERATING unit tests pass.
- [ ] Harmonic current multiplier applied correctly.
- [ ] Loss calculation uses R(T) at current estimated temperature, not fixed 20 °C.
- [ ] Loss table shows data provenance for each circuit.

**Effort band:** Medium (2–3 weeks)

---

### Milestone 5 — Basic Steady-State Nodal Thermal Solver

**Objective:** Implement and test the core steady-state thermal matrix solver for a
simplified model (conduction only, fixed convection coefficient).

**Deliverables:**
1. `thermpro_engine/network/thermal_matrix.py` — sparse matrix assembly and solve.
2. Automatic thermal cell grid generator.
3. Solver loop with convergence checking (simplified: conduction + fixed h).
4. ResultSnapshot populated with node temperatures.
5. Frontend: basic temperature display on drawing (text annotations).
6. All UT-MATRIX-* tests pass.
7. BM-002 (closed box) and BM-003 (two-node) benchmarks pass.

**Exit Criteria:**
- [ ] BM-002 result within ±1 K of energy-balance reference.
- [ ] BM-003 result within ±0.001 °C of analytical solution.
- [ ] All UT-MATRIX tests pass.
- [ ] Singular matrix detection tested and working.
- [ ] Convergence criteria checked; non-converged results flagged.

**Effort band:** Large (4–6 weeks)

---

### Milestone 6 — Natural Convection and Radiation Refinement

**Objective:** Replace the fixed convection coefficient with full natural convection
correlations and implement radiation between surfaces.

**Deliverables:**
1. `thermpro_engine/physics/convection.py` — Churchill-Chu, McAdams correlations.
2. `thermpro_engine/physics/radiation.py` — linearised radiation conductance.
3. Temperature-dependent air property evaluation.
4. Iterative inner loop: update h_conv and h_rad at each step.
5. All UT-CONV-* and UT-RAD-* tests pass.
6. BM-001 (single heated wall) benchmark passes.
7. BM-006 (parallel surface radiation) benchmark passes.

**Exit Criteria:**
- [ ] BM-001 T_surface within ±0.5 K of reference.
- [ ] BM-006 Q_rad within ±1% of reference.
- [ ] All UT-CONV and UT-RAD tests pass.
- [ ] Kelvin enforcement verified (UT-RAD-004).
- [ ] Film temperature used for air property evaluation.

**Effort band:** Medium (3–4 weeks)

---

### Milestone 7 — Pressure/Airflow Network and Fan Curves

**Objective:** Implement the full airflow network solver including fans, openings,
ducts, and buoyancy.

**Deliverables:**
1. `thermpro_engine/network/airflow_network.py` — complete.
2. Fan curve data model, import interface, cubic spline interpolation.
3. Buoyancy stack pressure calculation.
4. All UT-FLOW-* tests pass.
5. BM-005 (natural stack opening) benchmark passes.
6. Pathological flow detection (RISK-ENG-005 mitigation).
7. Frontend: airflow arrow visualisation on enclosure drawing.

**Exit Criteria:**
- [ ] BM-005 mass imbalance < 0.1%; flow within ±2% of hand calculation.
- [ ] All UT-FLOW tests pass.
- [ ] Fan operating point correctly found from fan curve and system resistance.
- [ ] Reverse-flow and short-circuit conditions detected and reported.
- [ ] Fan-without-curve triggers NOT_VERIFIABLE result (RISK-ENG-005 mitigation).

**Effort band:** Large (4–6 weeks)

---

### Milestone 8 — Coupled Thermal-Airflow Iteration

**Objective:** Couple the thermal and airflow solvers with the derating outer loop.
Implement the complete nested iteration described in THERM-NET-001 §10.

**Deliverables:**
1. `thermpro_engine/network/coupling.py` — outer iteration loop.
2. Under-relaxation, divergence detection, maximum iteration enforcement.
3. ConvergenceTrace populated and stored.
4. All BM-001 through BM-006 pass with the coupled solver.
5. FR-SOLV-004 through FR-SOLV-009 implemented.
6. Frontend: convergence progress display (WebSocket).

**Exit Criteria:**
- [ ] All 6 analytical benchmarks pass with the coupled solver.
- [ ] Convergence trace correctly records each iteration.
- [ ] Diverged runs produce RESULT INVALID, not a temperature value.
- [ ] Mass imbalance < 0.5% at convergence.
- [ ] Energy imbalance < 1% at convergence.

**Effort band:** Medium (3–4 weeks)

---

### Milestone 9 — Derating and Thermal-Limit Engine

**Objective:** Implement the complete hot-spot and thermal-limit assessment.

**Deliverables:**
1. `thermpro_engine/postprocess/hotspots.py` and `margins.py`.
2. Temperature limit database (configurable per project).
3. PASS / WATCH / WARNING / FAIL / NOT_VERIFIABLE classification for all entities.
4. Hot-spot detection using local gradient and limit exceedance.
5. Per-entity contributing-factor analysis.
6. Recommendations engine linked to calculated evidence.
7. Frontend: hot-spot markers on drawing.

**Exit Criteria:**
- [ ] Correct severity classification for 10 test scenarios (unit tests).
- [ ] Hot spots include coordinates, temperature, limit, margin, and recommendations.
- [ ] NOT_VERIFIABLE assigned when derating curve is absent.
- [ ] Limit table is configurable; default values match IEC 61439-1 defaults.

**Effort band:** Medium (2–3 weeks)

---

### Milestone 10 — Thermal Heat Maps, Airflow Arrows, Probes

**Objective:** Complete the results visualisation layer.

**Deliverables:**
1. False-colour heat map rendered on the enclosure drawing (Konva + colour interpolation).
2. Airflow arrows with temperature colouring and annotations.
3. Temperature probe and airflow probe entities; results shown on drawing.
4. Monochrome mode (FR-VIS-008).
5. View toggle for all 11 view modes.
6. Before/after comparison view (FR-VIS-009, FR-VIS-010).

**Exit Criteria:**
- [ ] Heat map renders correctly for BM-002 result.
- [ ] Airflow arrows correctly show direction, temperature, and velocity for BM-005.
- [ ] Monochrome mode passes visual review for report suitability.
- [ ] Comparison view shows two results side by side.

**Effort band:** Medium (3–4 weeks)

---

### Milestone 11 — IEC TR 60890 Eligibility and Calculation Module

**Objective:** Implement MODE 1: IEC TR 60890 module with eligibility checking and
administrator-import of licensed coefficient data.

**Deliverables:**
1. `thermpro_engine/modes/iec_60890.py` — complete.
2. Eligibility rule engine (FR-STD-007 through FR-STD-009).
3. Administrator interface: import, version, and activate coefficient dataset.
4. IEC TR 60890 calculation for eligible configurations (FR-STD-010).
5. Forced-ventilation exclusion enforced (FR-STD-006, RISK-ENG-003 mitigation).
6. RE-001 reference example test (pending licensed data availability).

**Exit Criteria:**
- [ ] All 8 eligibility conditions checked and reported.
- [ ] Presence of any active fan disables MODE 1 — no user override.
- [ ] Coefficient dataset import creates a versioned record.
- [ ] Calculation run report states standard edition and dataset version.
- [ ] RE-001 test passes within ±0.5 K when licensed data is available.

**Effort band:** Medium (3–4 weeks)

---

### Milestone 12 — Comparison, Optimisation, Reporting, and Audit

**Objective:** Complete the engineering workflow with multi-alternative comparison,
optimisation suggestions, PDF/XLSX reports, and the full audit trail.

**Deliverables:**
1. Design alternative management (save, name, compare).
2. Optimisation suggestion engine (FR-OPT-001 to FR-OPT-004).
3. PDF report generator (WeasyPrint; FR-RPT-001 to FR-RPT-004).
4. XLSX export (openpyxl).
5. AuditRecord with SHA-256 checksum (FR-AUD-001 to FR-AUD-003).
6. Immutable calculation snapshot locking.

**Exit Criteria:**
- [ ] Three saved alternatives can be compared side by side.
- [ ] Optimisation suggestions generated for a FAIL-status case.
- [ ] PDF report contains all required sections (FR-RPT-003 checklist).
- [ ] Audit checksum verifiable independently using sha256sum.
- [ ] Re-running a locked calculation from its snapshot produces identical results.

**Effort band:** Large (4–6 weeks)

---

### Milestone 13 — Reference-Case Validation and Physical Test Import

**Objective:** Complete Level 3 and Level 4 validation infrastructure.

**Deliverables:**
1. RE-001 and RE-002 reference cases set up and documented.
2. Physical test import format implementation (THERM-VAL-001 §6.1).
3. Comparison metrics calculation: MAE, RMSE, max error, bias, error by height.
4. Validation status field propagated to all results and reports.
5. Validation report template.
6. NOT_VALIDATED watermark on all reports until L4 criteria are met.

**Exit Criteria:**
- [ ] RE-002 nodal thermal case within ±2 K of published values (for any available case).
- [ ] Physical test import accepts the defined JSON format.
- [ ] Comparison metrics calculated and displayed correctly.
- [ ] Reports carry correct validation status.

**Effort band:** Medium (3–4 weeks)

---

### Milestone 14 — CFD Export Adapter

**Objective:** Implement the MODE 4 CFD export/import adapter architecture.

**Deliverables:**
1. `thermpro_engine/modes/cfd_adapter.py` — geometry and boundary condition export.
2. Export format: JSON + STL mesh (extensible; OpenFOAM as first target).
3. Import interface for CFD result files (temperature and velocity fields).
4. Adapter clearly labelled as an interface to an external solver in all reports.
5. Disclaimer and limitation statement displayed prominently.

**Exit Criteria:**
- [ ] Export produces a valid JSON + STL file from a completed M8 model.
- [ ] Import reads a sample CFD result file and maps temperatures to thermal cells.
- [ ] Report clearly states: solver type, external solver name/version, disclaimer.
- [ ] The words "CFD" and "Computational Fluid Dynamics" do not appear in any context
      that implies the reduced-order solver performs CFD.

**Effort band:** Medium (2–3 weeks)

---

## 4. Milestone Review Gate

At the end of every milestone, the following must be documented:

| Item | Content |
|------|---------|
| Test results | Summary of all unit and integration tests: pass count, fail count, coverage |
| Benchmark results | Deviation from analytical/reference values for each benchmark |
| Assumptions | List of all engineering assumptions active in the current implementation |
| Unresolved risks | Updated risk register rows relevant to this milestone |
| Files changed | List of all new and modified files |
| Documentation updates | Which documents were revised and why |
| Approval | Named engineer sign-off before proceeding to the next milestone |

---

## 5. Total Effort Summary (Indicative)

| Milestone | Effort Band |
|-----------|------------|
| M1 | Medium |
| M2 | Large |
| M3 | Large |
| M4 | Medium |
| M5 | Large |
| M6 | Medium |
| M7 | Large |
| M8 | Medium |
| M9 | Medium |
| M10 | Medium |
| M11 | Medium |
| M12 | Large |
| M13 | Medium |
| M14 | Medium |
| **Total** | **~14 milestone-efforts; approximately 12–18 months for a team of 3–4 engineers** |

Effort bands: Small = 1–2 weeks · Medium = 2–4 weeks · Large = 4–8 weeks.
Estimates assume a team of 1 thermal engineer + 1 numerical engineer + 2 software engineers.

---

*End of THERM-MILE-001*
