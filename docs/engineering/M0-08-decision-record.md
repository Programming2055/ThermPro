# Engineering Review Decision Record — LV Switchboard Thermal Digital Twin

**Document:** M0-08  
**Milestone:** 0 (correction commit)  
**Date:** 2026-07-03  
**Status:** APPROVED — Conditional Engineering Approval  
**Approval basis:** Engineering review of all 12 baseline documents and M0 deliverables

---

## 1. Purpose

This document records every engineering decision made during the Milestone 0 conditional
approval review. Each decision is binding. Implementation must conform to the decisions
recorded here; any deviation requires a new decision record entry.

---

## 2. Decisions

---

### DR-001 — Storage Architecture (resolves OQ-012)

**Decision:** APPROVED — Hybrid model

The platform uses **both** PostgreSQL and S3-compatible object storage. These are
complementary, not alternatives.

**PostgreSQL JSONB stores:**
- Complete calculation input snapshots (`InputSnapshot`)
- Structured result summaries, hotspot lists, compliance checks
- Convergence summaries, solver settings, warnings
- SHA-256 checksums for all artefacts
- Dataset manifests (library name, version, content hash) for every run
- All audit metadata

**S3-compatible object storage (MinIO or equivalent) stores:**
- PDF and XLSX reports
- CAD files and imported geometry
- Test data imports (FAT / field test JSON packages)
- Screenshots and project images
- Dense thermal field data (temperature arrays, full result grids)
- Mesh files for CFD export/import
- CFD result files and animations
- ROM snapshot files (HDF5)

**Database records for object-stored files contain:** immutable object key, SHA-256
checksum, MIME type, file size in bytes, created timestamp, and owning run or project ID.

**Implementation note:** Do not frame this as a choice. Every deployment requires both
services. The object store is not optional for production use.

**Effective from:** M1

---

### DR-002 — Library Versioning Strategy (resolves OQ-015)

**Decision:** APPROVED — Immutable semantic releases with content hashing

See `docs/engineering/M0-09-dataset-versioning.md` for the full specification.

**Summary:**
- Every library release carries: semantic version, immutable revision ID, SHA-256 content
  hash, status (DRAFT/APPROVED/SUPERSEDED/WITHDRAWN), effective date, source reference,
  creator, approver, and approval date.
- Every `InputSnapshot` must pin: library name, semantic version, and exact content hash.
- Historical calculations must always be resolvable to their original library data.
- A signed offline dataset-manifest is required for field deployments.
- Library records in the database are immutable once status = APPROVED; any change creates
  a new release.

**Effective from:** M1

---

### DR-003 — AC Busbar Resistance Correction (resolves OQ-001)

**Decision:** APPROVED WITH STAGED IMPLEMENTATION

A staged methodology replaces the prior single-value approach.

**Level 1 — DC resistance at temperature (always computed):**
```
R_DC(T) = ρ_ref · [1 + α · (T − T_ref)] · L / A
```

**Level 2 — AC resistance correction (when K_AC is provided):**
```
R_AC(T, f) = K_AC · R_DC(T)
```

`K_AC` must come from one of the following sources, in order of preference:
1. Manufacturer published AC resistance data
2. Results of validated physical tests
3. Approved analytical correlations (e.g. Rogowski/Lorenz method for rectangular bars)
4. A geometry/frequency-specific joint library entry
5. Explicit user-provided scalar input (clearly documented as a user assumption)

`K_AC = 1.0` (i.e., pure DC resistance) is permissible but **must** trigger a visible
engineering warning whenever the busbar cross-section and current frequency make AC effects
potentially significant. The warning is not suppressible by default configuration.

**Level 3 — Numerical electromagnetic calculation:** Reserved for a future release.
Not in MVP scope.

**Sensitivity scenarios:** When `K_AC` source is `USER_INPUT` or the solver detects
significant AC-effect risk, the solver must support evaluation at a minimum, nominal,
and maximum `K_AC` scenario to bound the uncertainty.

**Effective from:** M2 (busbar thermal model)

---

### DR-004 — Contact Resistance Data Hierarchy (resolves OQ-002)

**Decision:** APPROVED

Remove any universal default contact resistance. The solver must use the following
data precedence hierarchy:

| Priority | Source | Enum value |
|----------|--------|------------|
| 1 | Measured value (instrument, test report) | `MEASURED` |
| 2 | Validated manufacturer value (datasheet, qualification test) | `MANUFACTURER` |
| 3 | Approved joint library value (organisation-approved table) | `JOINT_LIBRARY` |
| 4 | Explicit user assumption (user accepts responsibility) | `USER_ASSUMPTION` |
| 5 | Sensitivity range only (no single value used) | — |

When source is `MEASURED`, `MANUFACTURER`, or `JOINT_LIBRARY`, a scalar
`contact_resistance_ref_ohm` is required.

When source is `USER_ASSUMPTION`, the user must explicitly set the value AND confirm
the assumption; the result carries a `DATA_ASSUMPTION` flag visible in the report.

When no source is available (condition = `UNKNOWN`), the solver **must** run a sensitivity
scenario with a user-supplied or library-supplied minimum/nominal/maximum range. Using a
single fixed default silently is not permitted.

**Joint condition enumeration (replaces health_state):**

| Value | Meaning |
|-------|---------|
| `NEW_VALIDATED` | New joint, validated torque and clean surfaces; high confidence |
| `NEW_ASSUMED` | New joint, assembly assumed correct; medium confidence |
| `MEASURED` | Contact resistance directly measured; highest confidence |
| `AGED` | Joint has been in service; condition estimated |
| `DEGRADED` | Known degradation (discolouration, overheating history, low torque) |
| `UNKNOWN` | Condition not assessed; sensitivity scenario required |

**Effective from:** M2

---

### DR-005 — Reverse Fan Flow Modelling (resolves OQ-006)

**Decision:** APPROVED

Five fan operating states replace the previous binary `operating: bool`:

| State | Description | Modelling treatment |
|-------|-------------|---------------------|
| `FORWARD_OPERATING` | Fan running in designed direction | P-Q curve interpolation |
| `STOPPED_FREE_FLOW` | Fan stopped; no damper (or damper open) | Resistance element using fan duct area and measured/estimated K_loss |
| `STOPPED_WITH_DAMPER` | Fan stopped; non-return damper closed | Closed element: zero flow |
| `FAILED_OPEN` | Fan failed with flow path unobstructed | Same as STOPPED_FREE_FLOW |
| `FAILED_BLOCKED` | Fan failed with flow path blocked | Same as STOPPED_WITH_DAMPER |
| `ESTIMATED_REVERSE_FLOW` | Reverse flow present; no physical block | Reverse resistance model using fan duct geometry |

**Rules:**
- Do not clamp reverse flow to zero unless `STOPPED_WITH_DAMPER` or `FAILED_BLOCKED` is set.
- Do not extrapolate the normal fan P-Q curve beyond validated bounds; use resistance
  model instead.
- If reverse flow is detected in `FORWARD_OPERATING` state, emit a `REVERSE_FLOW_DETECTED`
  warning and switch to `ESTIMATED_REVERSE_FLOW` treatment for that iteration.

**Effective from:** M6

---

### DR-006 — Transient Thermal Analysis Scope (resolves OQ-007)

**Decision:** DEFERRED — Not an M1 blocker; Phase 2 or later

Transient (time-domain) thermal analysis is excluded from the MVP.

**Requirements for MVP:**
- Domain model must preserve fields for thermal capacitance (`thermal_mass_J_K` per entity)
  so that the data model does not need to be broken when transient is implemented.
- `thermpro_engine` interfaces must reserve but not expose transient entry points.
- The steady-state solver is the only exposed calculation method in MVP.

**Phase 2 scope (not designed now):**
- Time-stepping outer loop
- Thermal capacitance per entity (material density × specific heat × volume)
- Load profile input (current vs. time curve per device/busbar)
- Duty-cycle and motor-starting scenarios

**Effective from:** Phase 2

---

### DR-007 — North American Standards Scope (resolves OQ-009)

**Decision:** DEFERRED — Not in MVP; future licensed standards profile

North American standards (UL 891, UL 1558, ANSI/IEEE C37.20.1) are **excluded from MVP**.

**MVP standards scope:**
- IEC 61439-1
- IEC 61439-2
- IEC TR 60890:2022
- Manufacturer-defined temperature limits (from DeviceLibrary)
- Project-defined limits (user-entered)

**Architectural requirement:** Standards profiles must not be assumed to differ only by
limit tables. Each profile must define:
- Its own applicability conditions and eligibility checks
- Its own required inputs
- Its own verification logic
- Its own temperature-rise limit tables and clauses
- Its own required datasets
- Its own report wording and disclaimer text

This architecture must be designed into the compliance module from M1, even though only
IEC profiles are active in MVP. North American profiles will be added as separately
licensed profile packages in a future phase.

**Remove from MVP:**
- All UL_891, UL_1558, ANSI_IEEE_C37_20_1 enum values from StandardProfile
- All North American limit tables and compliance checks
- UT-COMP-002 (UL compliance test) — deferred

**Effective from:** M1 (architecture); North American profiles: Phase 3 or later

---

### DR-008 — Arc Flash Module (resolves OQ-010)

**Decision:** REMOVED FROM MVP SCOPE

IEEE 1584-2018 arc-flash functionality is **entirely removed from the thermal platform MVP**.

**Remove from all documents and schemas:**
- ARC_FLASH calculation mode
- Arc-flash input fields in InputSnapshot
- Electrode configuration mappings
- Arc-flash result fields in ResultSnapshot
- INFORMATIVE arc-flash label constant
- Arc-flash API endpoint group (`/arc-flash`)
- Arc-flash tests (UT-ARC-001)
- Arc-flash milestone items
- Arc-flash compliance check type
- CR-ENG-007 (arc-flash INFORMATIVE label rule — no longer enforced in MVP)

**Future module architecture (not designed now):**
- Arc flash may become a separate future module sharing project data
- It must have an independent engine, input/output schemas, validation suite, and reports
- It must never share result schema space with thermal calculations

**Effective from:** M0 correction commit (immediate removal)

---

### DR-009 — Device Loss Uncertainty for Unknown Data (resolves assumption ASS-DATA-001)

**Decision:** APPROVED — Replace silent margin with explicit scenario framework

The automatic universal +20% power-loss margin for `data_confidence = UNKNOWN` is
**removed**.

**Replacement:**
- The `data_confidence` field is retained but its semantics change.
- Instead of a silent multiplier, the solver must:
  1. Record the confidence level and source provenance on the result entity.
  2. Require the user to supply or confirm an uncertainty distribution or range
     (minimum, nominal, maximum power loss values).
  3. Support sensitivity scenario evaluation at the supplied minimum, nominal, and maximum.
  4. Emit explicit `DATA_CONFIDENCE_LOW` or `DATA_CONFIDENCE_UNKNOWN` flags visible in
     the report and UI.
  5. Report wording must state the assumed value and its confidence level; it must not
     present the result as if the input data is known.

**Do not:** silently modify source values. The source value from the library must be
preserved unchanged; uncertainty is handled through scenario evaluation.

**Effective from:** M3 (device loss models)

---

### DR-010 — De Vahl Davis Benchmark Classification (resolves assumption about BM-007)

**Decision:** APPROVED — Reclassified from mandatory every-push gate

The De Vahl Davis differentially heated cavity benchmark (BM-007, Nu_avg = 8.80 ± 2% at
Ra = 10⁶) is **not** a mandatory CI gate for every push of the basic nodal thermal network.

**Rationale:** The basic nodal thermal network (MODE 2) uses lumped air nodes, not a
full-field natural convection solver. BM-007 is a CFD benchmark; requiring it to pass on
every push implies the nodal solver resolves natural convection field structure, which it
does not. Imposing it as a gate would create false assurance.

**Reclassified to:**
- Advanced airflow solver validation (when MODE 2 uses spatially resolved convection cells)
- CFD adapter (MODE 4) validation
- Periodic physics verification (e.g. pre-release, major physics updates)
- Not a per-push gate; tagged `@pytest.mark.periodic_physics`

**Every-push nodal benchmarks (regression-sensitive CI gates):**
1. BM-001 — Single heated vertical wall (Churchill-Chu)
2. BM-002 — Closed-box energy balance
3. BM-003 — Two-node conduction chain (REGRESSION SENSITIVE)
4. BM-004 — Forced-air heat balance
5. BM-005 — Two-compartment mass balance (REGRESSION SENSITIVE)
6. BM-006 — Radiation balance
7. BM-008 — Degraded joint hotspot (f_health modifier) (REGRESSION SENSITIVE)

**Effective from:** M1 (CI pipeline design)

---

### DR-011 — Units and Dimensional Analysis Policy (resolves gap in baseline documents)

**Decision:** APPROVED — Explicit units policy required

SI units are used internally for all calculations without exception. A formal units policy
is required. See `docs/engineering/M0-10-units-policy.md` for the full specification.

**Mandatory unit conversion tests added to CI (every push):**
- mm input converted to m before calculation
- µΩ input converted to Ω before calculation
- °C input converted to K before radiation calculation (existing CR-ENG-003)
- m³/h input converted to m³/s
- Gross area vs. net free area (Cd applied at the right point)
- Gauge pressure vs. absolute pressure (Pa absolute used internally)
- W/(m·K) and J/(kg·K) units checked for conductivity and heat capacity

**Effective from:** M1 (unit system implementation)

---

### DR-012 — CR-ENG-007 Withdrawn from MVP Engineering Rules

**Decision:** The arc-flash INFORMATIVE label rule (CR-ENG-007) is withdrawn from the
non-negotiable engineering rules because arc-flash is removed from MVP scope (DR-008).

If arc flash is re-introduced as a separate future module, a new CR must be written for
that module and approved at that time.

CR-ENG-007 is marked **WITHDRAWN (scope removed)** in all documents.

---

## 3. Summary Table

| DR-ID | OQ / Source | Decision | Status |
|-------|-------------|----------|--------|
| DR-001 | OQ-012 | Hybrid storage: PostgreSQL JSONB + S3 | APPROVED |
| DR-002 | OQ-015 | Immutable library releases with SHA-256 | APPROVED |
| DR-003 | OQ-001 | Staged K_AC methodology (Level 1/2/3) | APPROVED |
| DR-004 | OQ-002 | Contact resistance data hierarchy; new joint_condition enum | APPROVED |
| DR-005 | OQ-006 | Five fan operating states; no clamping without damper | APPROVED |
| DR-006 | OQ-007 | Transient deferred to Phase 2; preserve interfaces | DEFERRED |
| DR-007 | OQ-009 | North American standards deferred; profile architecture required | DEFERRED |
| DR-008 | OQ-010 | Arc flash entirely removed from MVP | REMOVED FROM SCOPE |
| DR-009 | ASS-DATA-001 | Remove silent +20% margin; use explicit scenario framework | APPROVED |
| DR-010 | BM-007 | Reclassify De Vahl Davis to periodic; define nodal CI gates | APPROVED |
| DR-011 | Gap | Explicit units policy and unit conversion tests | APPROVED |
| DR-012 | CR-ENG-007 | Withdraw arc-flash INFORMATIVE label rule from MVP | WITHDRAWN |

---

## 4. Approval Record

| Decision | Date | Approved By | Notes |
|----------|------|-------------|-------|
| All DR-001 through DR-012 | 2026-07-03 | Conditional engineering approval | Correction commit required before M1 |
