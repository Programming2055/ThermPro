# Open Questions — Information Requiring Engineering Approval

**Document:** M0-07  
**Milestone:** 0  
**Date:** 2026-07-03  
**Status:** Pending Engineering Approval  
**Source:** THERM-METH-001 §Appendix E; THERM-RISK-001; M0-06

---

## 1. Purpose

This document lists every question that must be resolved by an authorised engineer or
project decision-maker before the corresponding feature can be designed or implemented.
Items in this list are **blockers** for the milestones identified in the "Blocks" column.

Grouped by topic. Each item has:
- **OQ-ID:** unique identifier
- **Question:** what must be decided
- **Options:** possible answers
- **Default assumed:** what the current documentation assumes if no answer is given
- **Engineering impact:** what changes if the answer differs from the default
- **Blocks:** which milestone(s) cannot proceed without this answer

---

## 2. Electrical Physics Questions

### OQ-001 — Skin and Proximity Effects in Busbar Resistance
**Question:** Should the solver apply a skin-effect and proximity-effect correction factor to
busbar DC resistance at power frequency (50/60 Hz)?

**Options:**
- A. User provides measured AC resistance directly (recommended; most accurate)
- B. Solver computes skin-effect correction factor from busbar geometry using analytical formula
   (rectangular cross-section; Rogowski/Lorenz method)
- C. User applies external multiplier (skin_proximity_factor) field in BusbarSegment entity;
   solver multiplies R_dc by this factor

**Default assumed (current documentation):** No skin or proximity effect modelled (option C
with factor = 1.0). Warning issued for busbars wider than 18 mm.

**Engineering impact:** For busbars 60 mm × 10 mm at 50 Hz, AC resistance can be 5–10 %
higher than DC resistance. Combined with proximity effect in a 3-phase set, effective
resistance can be 15–30 % higher than DC. Underestimating resistance directly underestimates
busbar temperature — a potentially unconservative error.

**Blocks:** M2 (busbar thermal model), M5 (thermal network solver).

---

### OQ-002 — Default Contact Resistance for BusbarJoint
**Question:** What default contact resistance should be used when `data_confidence = UNKNOWN`
and no measured value is provided?

**Options:**
- A. 10 µΩ per joint (IEC 61439 informal guidance for new well-torqued joint)
- B. 50 µΩ per joint (conservative estimate for field-assembled joint, moderate torque)
- C. Calculation is blocked when contact resistance is unknown (engineer must supply value)
- D. Contact resistance is set to zero if unknown (optimistic; not recommended)

**Default assumed (current documentation):** 10 µΩ with a warning flag and LOW data
confidence propagated to result.

**Engineering impact:** A 3-phase busbar system with 20 joints at 1600 A: difference between
10 µΩ and 50 µΩ default ≈ 640 W additional heating ≈ 5–10 K additional rise in worst-case
joint hotspot. This could change a PASS compliance verdict to FAIL.

**Blocks:** M2 (busbar joint model), M4 (data model entity).

---

### OQ-003 — Control Transformer Loss Model
**Question:** The current model for control transformers uses `P = P_core + P_cu_rated·(I/I_n)²`.
Should harmonics loading of transformer secondary circuits be modelled?

**Options:**
- A. Not modelled; user applies de-rating factor externally (current approach)
- B. Add harmonic loss factor `k_harm` field to DeviceLibrary for transformer type
- C. Defer to external calculation; transformer treated as FIXED_POWER device

**Default assumed:** Option A (no harmonic modelling).

**Engineering impact:** VSD-loaded transformers can have k_harm up to 1.5×, substantially
increasing copper losses. Ignoring this underestimates transformer temperature.

**Blocks:** M3 (device loss models).

---

### OQ-004 — Eddy Current Losses in Steel Enclosure Walls
**Question:** Should eddy current losses induced by busbar magnetic fields in steel enclosure
walls be modelled?

**Options:**
- A. Not modelled; user applies power loss directly as a Device entity (current approach)
- B. Implement simplified analytical model (rectangular enclosure, 3-phase busbar)
- C. Provide a lookup table for common busbar-to-wall spacings

**Default assumed:** Option A (no eddy current model).

**Engineering impact:** At high busbar currents (> 1600 A) in steel enclosures, wall eddy
current losses can be 5–15 % of busbar Joule loss. For stainless steel or aluminium walls
the effect is negligible.

**Blocks:** M2/M3 if option B or C is chosen.

---

## 3. Thermal Network Questions

### OQ-005 — Heat Transfer Between Adjacent Cubicles
**Question:** How should heat transfer between side-by-side enclosures in a multi-cubicle
assembly be modelled?

**Options:**
- A. Adiabatic wall between adjacent cubicles (current approach; conservative)
- B. Allow user to specify a thermal conductance value for the shared wall
- C. Compute conductance from shared wall geometry and material

**Default assumed:** Option A (adiabatic, conservative).

**Engineering impact:** Adiabatic assumption is conservative: it overestimates temperature
of the hotter cubicle and underestimates temperature of the cooler one. For a highly loaded
cubicle adjacent to a lightly loaded one, the error could be 2–5 K.

**Blocks:** M2 (thermal network, enclosure coupling).

---

### OQ-006 — Reverse Flow Through Fans
**Question:** How should the solver handle reverse flow through a fan (calculated flow
direction opposite to fan operating direction)?

**Options:**
- A. Set flow to zero and issue a warning (current assumed approach)
- B. Model fan as a resistance in reverse-flow direction (manufacturer data required)
- C. Raise a NON_CONVERGED error if reverse flow is detected

**Default assumed:** Option A.

**Engineering impact:** Reverse flow is physically possible in multi-fan parallel configurations.
Option A is conservative (blocks hot return air) but may give incorrect mass balance in
complex airflow networks.

**Blocks:** M6 (forced-ventilation airflow network).

---

### OQ-007 — Transient Thermal Analysis
**Question:** Is transient (time-domain) thermal analysis required within the platform scope?

**Options:**
- A. Not required; steady-state only (current documentation)
- B. Required for short-time loading scenarios (e.g. motor starting, switchgear duty cycles)
- C. Required as a separate calculation mode (would require thermal capacitance model)

**Default assumed:** Option A (steady-state only; transient deferred).

**Engineering impact:** If option B or C is required, significant additional modelling
effort is needed: thermal capacitance per entity, time-stepping solver, input format for
load profiles. This is a major scope change.

**Blocks:** Does not block M1–M9, but must be resolved before M10 (system integration)
if transient is in scope.

---

## 4. Standards and Compliance Questions

### OQ-008 — IEC TR 60890 Licensed Dataset Availability
**Question:** Has a licensed copy of the IEC TR 60890:2022 coefficient tables been procured
for import into the system?

**Context:** The system ships with a null-valued template only (CR-ENG-002). MODE 1
calculations are unavailable until the dataset is imported by a Super-Admin.

**Options:**
- A. Dataset procured; will be imported at deployment
- B. Dataset not yet procured; MODE 1 will be unavailable at launch
- C. Organisation will derive their own coefficients from physical testing (non-standard)

**Default assumed:** Dataset must be procured separately; system design is not affected
either way (null template is the correct default by design).

**Engineering impact:** If not procured, MODE 1 is unavailable and the IEC TR 60890
reference example (RE-001) cannot be validated.

**Blocks:** RE-001 validation only.

---

### OQ-009 — North American Compliance Temperature Limits
**Question:** What are the precise temperature-rise limits for UL 891, UL 1558, and
ANSI/IEEE C37.20.1 that should be programmed into the compliance check?

**Context:** The current documentation states "65 K rise above 40 °C max for UL vs IEC 61439
70 K busbar limit." A comprehensive table of all limits (busbars, terminals, accessible
surfaces, operator controls, air inside enclosure) for each North American standard is
required before implementing the compliance interpretation layer.

**Action required:** Engineering team must supply or confirm the limit table from the
licensed standards text.

**Blocks:** M8 (compliance reporting module).

---

### OQ-010 — IEEE 1584-2018 Electrode Configuration Mapping
**Question:** How should the software map a given switchboard design (Form type, bus
configuration, enclosure dimensions) to an IEEE 1584-2018 electrode configuration
(VCB, VCBB, HCB, VOA, HOA)?

**Options:**
- A. User selects electrode configuration manually
- B. Software proposes configuration based on Form type and orientation; user confirms
- C. Software automatically assigns configuration (risk of incorrect assignment)

**Default assumed:** Option A (manual selection; user responsible).

**Engineering impact:** Incorrect electrode configuration can change incident energy by
a factor of 2–4. Automatic assignment (option C) introduces risk without adequate geometric
analysis.

**Blocks:** M11 (arc-flash module).

---

## 5. Architecture and Implementation Questions

### OQ-011 — Celery Worker Concurrency
**Question:** How many simultaneous calculation jobs should the Celery worker queue support?

**Context:** Each MODE 2/3 calculation for a large enclosure may take 10–60 seconds.
Multiple simultaneous users could overwhelm a single worker.

**Options:**
- A. Single worker, single queue (simplest; suitable for small teams)
- B. Auto-scaling workers with a maximum concurrency limit (requires Kubernetes or similar)
- C. Fixed 4-worker pool behind a Redis priority queue

**Default assumed:** Option A for MVP; option B or C for production.

**Engineering impact:** This is an infrastructure and licensing decision. Affects deployment
cost and user experience under load.

**Blocks:** M12 (deployment and operations).

---

### OQ-012 — Object Storage for Calculation Snapshots
**Question:** Should InputSnapshot and ResultSnapshot JSON be stored in the PostgreSQL JSONB
column or in an S3-compatible object store (MinIO)?

**Options:**
- A. PostgreSQL JSONB column (simpler; suitable for snapshots < 16 MB)
- B. S3-compatible object store; store object key in PostgreSQL (required for large field
   data, CFD results, HDF5 files)
- C. PostgreSQL for InputSnapshot; S3 for ResultSnapshot (hybrid)

**Default assumed:** Option B (S3 for all large objects; JSONB for metadata only).

**Engineering impact:** S3 adds infrastructure complexity (MinIO deployment, IAM policies,
backup configuration) but enables MODE 4 (CFD file exchange) and ROM snapshot storage
without database bloat.

**Blocks:** M1 (repository scaffolding), M12 (deployment).

---

### OQ-013 — ROM Training Data Generation Strategy
**Question:** How should the ROM training parameter space be sampled for
BuildParametricROM?

**Options:**
- A. Latin Hypercube Sampling (LHS) — good space-filling; default in ThermalUQ
- B. Sobol quasi-random sequences — better coverage for high-dimensional spaces
- C. Full-factorial grid (expensive; only practical for ≤ 3 parameters)
- D. User-defined sample points (most flexible)

**Default assumed:** LHS for Tier 1 ROM (ASS-NUM-002). Sobol recommended for > 5 parameters.

**Engineering impact:** Sample strategy affects ROM accuracy in extrapolation regions.
Poor sampling can cause ROM to fail validation tests (BM-007 surrogate equivalent).

**Blocks:** M9 (ROM build).

---

## 6. Data and Library Questions

### OQ-014 — Initial Device Library Population
**Question:** Who supplies the initial DeviceLibrary entries, and from what source?

**Options:**
- A. Engineering team manually enters data from manufacturer datasheets
- B. Bulk import from manufacturer's published data (requires import script)
- C. Start with empty library; users enter their own data
- D. Licensed third-party component database

**Default assumed:** Option C for MVP (empty library; users import or enter data).

**Engineering impact:** An empty library at launch means users cannot run calculations
until they have populated device data. This is a significant usability constraint.

**Blocks:** M1 (library schema), M3 (device loss models) — not a code blocker, but a
deployment readiness blocker.

---

### OQ-015 — Library Versioning Strategy for Field Deployments
**Question:** When a DeviceLibrary entry is updated after calculation runs have been
performed, should existing runs be:

**Options:**
- A. Frozen at the library version used at submission time (current approach; immutable audit)
- B. Flagged as "library outdated" but result retained
- C. Automatically re-run with the updated library (risky; changes historical results)

**Default assumed:** Option A (immutable InputSnapshot with pinned library version).

**Engineering impact:** Option A is the only approach compatible with the auditability
requirement (FR-AUD-001). This must be confirmed before implementing library versioning
in M1.

**Blocks:** M1 (library versioning).

---

## 7. Summary Table

| OQ-ID | Topic | Blocks | Priority |
|-------|-------|--------|----------|
| OQ-001 | Skin/proximity effect in busbar | M2, M5 | HIGH |
| OQ-002 | Default contact resistance | M2, M4 | HIGH |
| OQ-003 | Transformer harmonic loading | M3 | MEDIUM |
| OQ-004 | Wall eddy current losses | M2/M3 | MEDIUM |
| OQ-005 | Adjacent cubicle heat transfer | M2 | MEDIUM |
| OQ-006 | Reverse flow through fans | M6 | HIGH |
| OQ-007 | Transient thermal analysis in scope? | M10 | HIGH |
| OQ-008 | IEC TR 60890 licensed dataset | RE-001 only | LOW |
| OQ-009 | North American temperature limits table | M8 | HIGH |
| OQ-010 | IEEE 1584-2018 electrode config mapping | M11 | MEDIUM |
| OQ-011 | Celery worker concurrency | M12 | LOW |
| OQ-012 | Object storage strategy | M1, M12 | HIGH |
| OQ-013 | ROM training sampling strategy | M9 | MEDIUM |
| OQ-014 | Initial device library population | M1 | MEDIUM |
| OQ-015 | Library versioning for field deployments | M1 | HIGH |

---

## 8. Approval Record

| OQ-ID | Resolved Date | Decision | Approved By |
|-------|---------------|----------|-------------|
| — | — | — | — |

*This table is to be completed during the engineering review meeting before M0 approval.*
