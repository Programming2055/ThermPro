# Risk Register — LV Switchboard Thermal Digital Twin

**Document ID:** THERM-RISK-001  
**Revision:** 0.1 (Draft for Engineering Review)  
**Date:** 2026-07-03  
**Status:** Pending Approval

---

## 1. Purpose

This register identifies engineering, technical, legal, and project risks for ThermPro.
Each risk is assessed for likelihood and impact before mitigation, and a mitigation
strategy is defined. The register must be reviewed at every milestone gate.

---

## 2. Risk Scoring

**Likelihood:** 1 (Rare) · 2 (Unlikely) · 3 (Possible) · 4 (Likely) · 5 (Almost certain)

**Impact:** 1 (Negligible) · 2 (Minor) · 3 (Moderate) · 4 (Major) · 5 (Critical)

**Severity = Likelihood × Impact**

| Severity | Band |
|----------|------|
| 1–4 | LOW |
| 5–9 | MEDIUM |
| 10–15 | HIGH |
| 16–25 | CRITICAL |

---

## 3. Risk Register

### RISK-ENG-001 — Incorrect derating due to wrong local ambient temperature

| Field | Value |
|-------|-------|
| **Category** | Engineering |
| **Description** | The device derating calculation uses the average enclosure temperature instead of the local air temperature surrounding the device, leading to unconservative results. |
| **Likelihood** | 3 |
| **Impact** | 5 |
| **Severity** | 15 — HIGH |
| **Mitigation** | Assign each device to a specific thermal cell. Derating uses the temperature of that cell. Code review explicitly checks this assignment. Unit test UT-DERATING-001/002/003 validates the calculation path. |
| **Owner** | Lead thermal engineer |
| **Status** | OPEN — mitigation required in architecture |

---

### RISK-ENG-002 — Busbar loss calculated only at 20 °C

| Field | Value |
|-------|-------|
| **Category** | Engineering |
| **Description** | Busbar resistance is evaluated only at 20 °C (the reference temperature), ignoring the increase in resistance at elevated conductor temperature. This underestimates losses by up to 20% at 75 °C. |
| **Likelihood** | 3 |
| **Impact** | 4 |
| **Severity** | 12 — HIGH |
| **Mitigation** | Enforce temperature-dependent R(T) = R_ref[1+α(T−T_ref)] in the Joule module (UT-JOULE-001). The outer iteration loop updates busbar temperature and re-evaluates resistance at each step. Architectural rule: no busbar loss calculation may use a fixed 20 °C temperature. |
| **Owner** | Lead thermal engineer |
| **Status** | OPEN |

---

### RISK-ENG-003 — Forced-ventilation result labelled as IEC TR 60890 compliant

| Field | Value |
|-------|-------|
| **Category** | Engineering / Legal |
| **Description** | A user configures fans in the enclosure and runs a calculation; the report incorrectly states compliance with IEC TR 60890. |
| **Likelihood** | 2 |
| **Impact** | 5 |
| **Severity** | 10 — HIGH |
| **Mitigation** | Hard-coded eligibility rule: presence of any active fan → MODE 1 disabled for that enclosure. No user override. Eligibility check is the first step in FR-STD-006 and is tested by dedicated integration test. |
| **Owner** | Lead software engineer |
| **Status** | OPEN |

---

### RISK-ENG-004 — Solver non-convergence presented as a valid result

| Field | Value |
|-------|-------|
| **Category** | Engineering |
| **Description** | The iterative solver fails to converge but the result is displayed without a clear warning, leading the engineer to accept incorrect temperatures. |
| **Likelihood** | 2 |
| **Impact** | 5 |
| **Severity** | 10 — HIGH |
| **Mitigation** | Convergence status is a mandatory field in ResultSnapshot. Any result with converged=false receives a RESULT INVALID watermark in the UI and report. The "Run Calculation" button is replaced by "View Convergence Failure" when the status is NON_CONVERGED. |
| **Owner** | Lead software engineer |
| **Status** | OPEN |

---

### RISK-ENG-005 — Fan rated airflow assumed equal to installed airflow

| Field | Value |
|-------|-------|
| **Category** | Engineering |
| **Description** | The fan curve is not entered; the software defaults to using the rated free-delivery airflow, ignoring system resistance. The actual installed airflow may be 30–60% lower. |
| **Likelihood** | 4 |
| **Impact** | 4 |
| **Severity** | 16 — CRITICAL |
| **Mitigation** | Fan curve is a required input for MODE 3. If not entered, the fan is flagged as data_confidence=LOW and the result for any airflow-dependent quantity is marked NOT_VERIFIABLE. A pre-calculation validation error (not warning) blocks the run until either the fan curve is provided or the user acknowledges the NOT_VERIFIABLE flag. |
| **Owner** | Lead thermal engineer |
| **Status** | OPEN |

---

### RISK-ENG-006 — Partitions and internal obstructions ignored

| Field | Value |
|-------|-------|
| **Category** | Engineering |
| **Description** | Internal partitions and mounted equipment blocking airflow paths are not modelled, leading to over-predicted cooling and under-predicted temperatures in segregated zones. |
| **Likelihood** | 3 |
| **Impact** | 4 |
| **Severity** | 12 — HIGH |
| **Mitigation** | Partitions are first-class geometry entities. The thermal network model assigns zero air-transport conductance across solid partitions. Perforated partitions use the open-area fraction. Collision detection prevents equipment placement that fully blocks an opening. |
| **Owner** | Lead thermal engineer |
| **Status** | OPEN |

---

### RISK-LEGAL-001 — IEC TR 60890 coefficient tables included without licence

| Field | Value |
|-------|-------|
| **Category** | Legal / Intellectual Property |
| **Description** | The empirical coefficient tables from IEC TR 60890 are distributed with the application without an IEC licence, constituting copyright infringement. |
| **Likelihood** | 1 |
| **Impact** | 5 |
| **Severity** | 5 — MEDIUM |
| **Mitigation** | The application ships without any IEC TR 60890 coefficient data. An administrator-import workflow requires the user to enter or import licensed data. The template file contains only structure and null values. Legal review of the import mechanism before release. |
| **Owner** | Legal counsel + lead software engineer |
| **Status** | OPEN |

---

### RISK-LEGAL-002 — Manufacturer device data incorporated without permission

| Field | Value |
|-------|-------|
| **Category** | Legal |
| **Description** | Device loss curves, derating curves, and dimensions from manufacturer datasheets are bundled in the application library without permission, infringing the manufacturer's database rights. |
| **Likelihood** | 3 |
| **Impact** | 4 |
| **Severity** | 12 — HIGH |
| **Mitigation** | The default device library ships empty. Users and administrators import data under their own licences. Import template includes a licence reference field. Legal policy document governs what may be imported. |
| **Owner** | Legal counsel |
| **Status** | OPEN |

---

### RISK-TECH-001 — Numerical solver divergence for large or poorly configured models

| Field | Value |
|-------|-------|
| **Category** | Technical |
| **Description** | Large models with many thermal cells and nonlinear radiation terms may oscillate or diverge under the default relaxation factor, particularly for high-temperature configurations. |
| **Likelihood** | 3 |
| **Impact** | 3 |
| **Severity** | 9 — MEDIUM |
| **Mitigation** | Under-relaxation (default ω=0.7, configurable). Divergence detection halts the solver after 5 consecutive iterations with increasing ΔT. Error message directs user to reduce relaxation factor or simplify model. Benchmark BM-001 through BM-006 must pass before release. |
| **Owner** | Numerical methods specialist |
| **Status** | OPEN |

---

### RISK-TECH-002 — Singular or ill-conditioned thermal matrix

| Field | Value |
|-------|-------|
| **Category** | Technical |
| **Description** | Isolated thermal nodes (no conductance connections) or model topology errors produce a singular conductance matrix that the sparse solver cannot invert. |
| **Likelihood** | 2 |
| **Impact** | 4 |
| **Severity** | 8 — MEDIUM |
| **Mitigation** | Pre-solve topology check: every non-boundary node must have at least one non-zero conductance. Singular matrix detection in the solver wrapper catches scipy.linalg.LinAlgError and reports the isolated node. Unit test UT-MATRIX-004 validates this path. |
| **Owner** | Numerical methods specialist |
| **Status** | OPEN |

---

### RISK-TECH-003 — CFD adapter produces misleading results when used without validated external solver

| Field | Value |
|-------|-------|
| **Category** | Technical |
| **Description** | The MODE 4 CFD adapter exports geometry and boundary conditions. A user imports results from an unvalidated solver and presents them as authoritative CFD output. |
| **Likelihood** | 2 |
| **Impact** | 4 |
| **Severity** | 8 — MEDIUM |
| **Mitigation** | MODE 4 results are tagged with solver_type=EXTERNAL_CFD and the name/version of the external solver must be entered by the user. The report displays a prominent disclaimer that the external solver's validation is the responsibility of the engineer. The application cannot validate the external solver's results. |
| **Owner** | Lead software engineer |
| **Status** | OPEN |

---

### RISK-TECH-004 — Performance degradation with large models

| Field | Value |
|-------|-------|
| **Category** | Technical |
| **Description** | An enclosure with 5000 thermal cells and complex airflow network exceeds the 30-second solve time target, leading to poor user experience and pressure to skip iterations. |
| **Likelihood** | 3 |
| **Impact** | 3 |
| **Severity** | 9 — MEDIUM |
| **Mitigation** | Asynchronous Celery tasks prevent UI blocking. Maximum cell count enforced (configurable; default 5000). Profile the solver on a 1000-cell model in Milestone 5 and optimise before increasing the limit. Use scipy.sparse.linalg.spsolve (highly optimised). |
| **Owner** | Lead software engineer |
| **Status** | OPEN |

---

### RISK-DATA-001 — Assumed data used for major heat sources without user awareness

| Field | Value |
|-------|-------|
| **Category** | Data Quality |
| **Description** | A device has no manufacturer loss data. The software silently uses the quadratic approximation. The engineer is unaware that the largest heat source in the enclosure is based on an assumption. |
| **Likelihood** | 4 |
| **Impact** | 4 |
| **Severity** | 16 — CRITICAL |
| **Mitigation** | ASSUMED loss values are shown with a distinct visual indicator (orange background) in the loading table. The summary banner states "X devices have ASSUMED losses." The report shows the data provenance table prominently. Sensitivity analysis (planned for later milestone) shows how the result changes if the assumed value is ±50%. |
| **Owner** | Lead thermal engineer |
| **Status** | OPEN |

---

### RISK-DATA-002 — Physical test data unavailable for validation

| Field | Value |
|-------|-------|
| **Category** | Data / Validation |
| **Description** | No physical test data are available to perform Level 4 validation, meaning the software cannot achieve VALIDATED status. |
| **Likelihood** | 3 |
| **Impact** | 4 |
| **Severity** | 12 — HIGH |
| **Mitigation** | Software ships with NOT_VALIDATED status prominently displayed. The validation-plan infrastructure (Level 4 import format) is built in Milestone 13. The software is not offered for production engineering use until a client is willing to run a formal acceptance test. |
| **Owner** | Project engineer |
| **Status** | OPEN |

---

### RISK-PROJ-001 — IEC TR 60890 standard changes invalidate the implemented method

| Field | Value |
|-------|-------|
| **Category** | Project / Standards |
| **Description** | A new edition of IEC TR 60890 is published with revised eligibility criteria or different coefficient tables, requiring rework of the MODE 1 implementation. |
| **Likelihood** | 2 |
| **Impact** | 3 |
| **Severity** | 6 — MEDIUM |
| **Mitigation** | The coefficient dataset is versioned and user-imported (not hard-coded). Standard edition is a configurable project parameter. When a new edition is released, only a new import template and eligibility rule update are required; core solver logic is unchanged. |
| **Owner** | Lead thermal engineer |
| **Status** | OPEN |

---

### RISK-PROJ-002 — User applies software outside its validated scope

| Field | Value |
|-------|-------|
| **Category** | Project / Safety |
| **Description** | An engineer uses ThermPro for outdoor enclosures with solar loading, or for MV switchgear, or for configurations not covered by the validation. |
| **Likelihood** | 3 |
| **Impact** | 4 |
| **Severity** | 12 — HIGH |
| **Mitigation** | Applicability validation in FR-SOLV-001 checks scope. Out-of-scope configurations return a NOT_ELIGIBLE or NOT_VERIFIABLE status. The report states limitations explicitly. A clear disclaimer is shown in the UI at all times. User training and documentation describe the scope boundary. |
| **Owner** | Project engineer |
| **Status** | OPEN |

---

### RISK-ENG-007 — Contact Resistance Uncertainty Causing Hotspot Underprediction

| Field | Value |
|-------|-------|
| **Category** | Engineering / Data Quality |
| **Description** | Bolted joint and terminal contact resistance values are often unavailable from manufacturers. When R_joint is ASSUMED, the thermal model may underpredict local hotspot temperatures by a wide margin. Published LV switchgear CFD studies show average underprediction of ~10 °C in hermetic and ~6 °C in ventilated enclosures, partly attributable to uncertain contact and emissivity inputs. |
| **Likelihood** | 4 |
| **Impact** | 4 |
| **Severity** | 16 — CRITICAL |
| **Mitigation** | (1) Joint entities are first-class data model objects with explicit health state and data confidence. (2) When R_joint has data_confidence = LOW or health_state = UNKNOWN, all affected zone results are marked NOT_VERIFIABLE. (3) The ThermalUQ module (ROM tier) includes contact resistance as a primary uncertainty parameter in sensitivity analysis. (4) Sensitivity report ranks which joints most influence peak hotspot temperature so the engineer can prioritise measurement. |
| **Owner** | Lead thermal engineer |
| **Status** | OPEN |

---

### RISK-ENG-008 — Emissivity Assumption Error Causing Systematic Temperature Underprediction

| Field | Value |
|-------|-------|
| **Category** | Engineering / Data Quality |
| **Description** | Surface emissivity strongly influences radiative heat transfer in sealed and lightly vented enclosures. Bare aluminium may have emissivity below 0.1; painted or oxidised steel may be 0.7–0.9. Using the wrong emissivity value can cause systematic underprediction of wall temperatures. The validated LV switchgear CFD paper identified emissivity as a key error driver (~10 °C underprediction in hermetic configurations). |
| **Likelihood** | 3 |
| **Impact** | 4 |
| **Severity** | 12 — HIGH |
| **Mitigation** | (1) Emissivity is a first-class surface property in the geometry model, not a hard-coded constant. (2) The material library includes emissivity ranges for common finishes (bare, painted, oxidised) with explicit data confidence. (3) The ThermalUQ module includes emissivity as a primary uncertain parameter. (4) When emissivity is ASSUMED, affected surface temperatures carry a reduced-confidence flag. |
| **Owner** | Lead thermal engineer |
| **Status** | OPEN |

---

### RISK-ENG-009 — Arc-Flash Module Results Mistaken for a Formal Hazard Study

| Field | Value |
|-------|-------|
| **Category** | Engineering / Legal / Safety |
| **Description** | The IEEE 1584-2018 arc-flash screening module produces incident energy and PPE category values. A user could present these results in a safety label or work procedure without conducting a full arc-flash hazard analysis by a qualified person, creating unsafe working conditions and legal liability. |
| **Likelihood** | 3 |
| **Impact** | 5 |
| **Severity** | 15 — HIGH |
| **Mitigation** | (1) All arc-flash outputs carry a mandatory INFORMATIVE label (CR-ENG-007). (2) The report prominently states: "These results are a screening calculation only. A formal arc-flash hazard analysis per IEEE 1584-2018 and NFPA 70E must be performed by a qualified person before affixing arc-flash labels or establishing work practices." (3) The module cannot be configured to remove this disclaimer. (4) Legal review of the disclaimer text before release. |
| **Owner** | Legal counsel + lead software engineer |
| **Status** | OPEN |

---

### RISK-TECH-005 — ROM Surrogate Model Extrapolating Beyond Training Range

| Field | Value |
|-------|-------|
| **Category** | Technical |
| **Description** | The reduced-order model (ROM) trained over a parameter grid may be queried for parameter combinations outside the training range. Extrapolated ROM results can be wildly inaccurate and will not carry a convergence warning from the underlying thermal matrix solver. |
| **Likelihood** | 3 |
| **Impact** | 3 |
| **Severity** | 9 — MEDIUM |
| **Mitigation** | (1) BuildParametricROM stores the training parameter bounds in the ROM record. (2) ROM evaluator checks each query point against training bounds before evaluation; out-of-bounds queries return a EXTRAPOLATION_WARNING flag. (3) ROM results always carry a label stating the training parameter range and the fact that the result is a ROM approximation, not a full-order solve. (4) Benchmark BM-008 and uncertainty analysis runs validate ROM accuracy within the training range. |
| **Owner** | Numerical methods specialist |
| **Status** | OPEN |

---

## 4. Risk Review Schedule

| Milestone | Review Action |
|-----------|--------------|
| Milestone 1 | Initial register populated (this document). |
| Milestone 5 | Review engineering risks after first solver implementation. |
| Milestone 8 | Review after coupled thermal-airflow solver complete. |
| Milestone 11 | Review after IEC TR 60890 module complete; legal review of IP risks. |
| Milestone 13 | Review after Level 4 validation data imported. |
| Each release | Full register review; update status, likelihood, impact. |

---

| Milestone | Review Action |
|-----------|--------------|
| Milestone 1 | Initial register populated (this document). |
| Milestone 5 | Review engineering risks after first solver implementation. |
| Milestone 8 | Review after coupled thermal-airflow solver complete. |
| Milestone 11 | Review after IEC TR 60890 module complete; legal review of IP risks. |
| Milestone 13 | Review after Level 4 validation data imported. |
| Each release | Full register review; update status, likelihood, impact. |

---

*End of THERM-RISK-001*
