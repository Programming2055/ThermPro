# Open Questions — Information Requiring Engineering Approval

**Document:** M0-07  
**Milestone:** 0 (correction commit — revision 1)  
**Date:** 2026-07-03  
**Status:** UPDATED — All critical OQs resolved at conditional engineering approval

---

## 1. Purpose

This document records all open questions raised during Milestone 0 engineering review.
Questions have been resolved by the conditional engineering approval decision on 2026-07-03.
Full decision details are in `docs/engineering/M0-08-decision-record.md`.

Status key:
- **APPROVED**: Decision made; implementation must follow decision record.
- **DEFERRED**: Not in MVP scope; interfaces may be preserved; re-evaluate in named phase.
- **REMOVED FROM SCOPE**: Feature entirely excluded from the platform MVP.
- **OPEN**: Not yet resolved (none remain in this revision).

---

## 2. Electrical Physics Questions

### OQ-001 — AC Busbar Resistance Correction

**Status:** ✅ APPROVED WITH STAGED IMPLEMENTATION (DR-003, 2026-07-03)

**Decision summary:** A three-level staged methodology:
- Level 1: R_DC(T) always computed.
- Level 2: K_AC correction applied when K_AC is provided from a qualified source
  (manufacturer, validated test, approved correlation, geometry/frequency library,
  or explicit user input). K_AC = 1.0 with a non-suppressible warning is the fallback.
- Level 3: Numerical EM calculation reserved for future release.
- Sensitivity scenarios required when K_AC source is USER_INPUT.

See DR-003 in M0-08.

---

### OQ-002 — Default Contact Resistance for BusbarJoint

**Status:** ✅ APPROVED (DR-004, 2026-07-03)

**Decision summary:** Universal 10 µΩ default removed. Contact resistance must follow
a strict data hierarchy (MEASURED > MANUFACTURER > JOINT_LIBRARY > USER_ASSUMPTION >
sensitivity scenario). When joint_condition = UNKNOWN, sensitivity scenarios are required;
single-value computation is not permitted.

New joint_condition enum: NEW_VALIDATED, NEW_ASSUMED, MEASURED, AGED, DEGRADED, UNKNOWN.

See DR-004 in M0-08.

---

### OQ-003 — Control Transformer Harmonic Loading

**Status:** ⏸ OPEN — LOW PRIORITY (not a blocker for M1–M5)

**Decision:** Not resolved in this review. Harmonic de-rating remains outside MVP scope.
The device thermal model uses P = P_core + P_cu_rated·(I/I_n)². A `k_harm` field is
reserved in the DeviceLibrary schema for future use. User must apply an external
de-rating factor for VSD-loaded transformers.

---

### OQ-004 — Eddy Current Losses in Enclosure Walls

**Status:** ⏸ OPEN — LOW PRIORITY (not a blocker for M1–M5)

**Decision:** Not resolved in this review. User applies additional power as a
FIXED_POWER Device entity. Analytical or lookup model deferred.

---

## 3. Thermal Network Questions

### OQ-005 — Heat Transfer Between Adjacent Cubicles

**Status:** ⏸ OPEN — LOW PRIORITY (not a blocker for M1–M5)

**Decision:** Not resolved in this review. Adiabatic wall assumption retained as default
(conservative). User may override with a user-defined thermal conductance in a future
enhancement. The domain model reserves an `adjacent_enclosure_conductance_W_K` field
for this purpose.

---

### OQ-006 — Reverse Flow Through Fans

**Status:** ✅ APPROVED (DR-005, 2026-07-03)

**Decision summary:** Five fan operating states replace the previous binary `operating`
flag: FORWARD_OPERATING, STOPPED_FREE_FLOW, STOPPED_WITH_DAMPER, FAILED_OPEN,
FAILED_BLOCKED, ESTIMATED_REVERSE_FLOW.

Reverse flow must not be clamped to zero unless a non-return damper is present.
Normal fan P-Q curve must not be extrapolated beyond validated bounds.

See DR-005 in M0-08.

---

### OQ-007 — Transient Thermal Analysis

**Status:** ✅ DEFERRED — Phase 2 or later (DR-006, 2026-07-03)

**Decision summary:** Transient analysis is excluded from MVP. The domain model must
preserve `thermal_mass_J_K` fields per entity. Engine interfaces must reserve but not
expose transient entry points. Not an M1 blocker.

See DR-006 in M0-08.

---

## 4. Standards and Compliance Questions

### OQ-008 — IEC TR 60890 Licensed Dataset Availability

**Status:** ⏸ OPEN — DEPLOYMENT CONCERN (not a code blocker)

**Decision:** Not a platform design question. System ships with null template as designed
(CR-ENG-002). Dataset procurement is an operator responsibility. MODE 1 is unavailable
without the dataset; this is correct by design.

---

### OQ-009 — North American Compliance Temperature Limits

**Status:** ✅ DEFERRED (DR-007, 2026-07-03)

**Decision summary:** UL 891, UL 1558, and ANSI/IEEE C37.20.1 are removed from MVP scope.
MVP standards scope: IEC 61439-1, IEC 61439-2, IEC TR 60890, manufacturer limits,
project-defined limits.

Standards profiles must not be assumed to differ only by limit tables; each profile
requires its own applicability conditions, verification logic, limits, datasets, and
report wording. This architecture must be built into the compliance module from M1 even
though only IEC profiles are implemented in MVP.

North American profiles will be separately licensed in Phase 3 or later.

See DR-007 in M0-08.

---

### OQ-010 — IEEE 1584-2018 Electrode Configuration Mapping

**Status:** ✅ REMOVED FROM SCOPE (DR-008, 2026-07-03)

**Decision summary:** Arc-flash functionality is entirely removed from the thermal platform
MVP. All arc-flash input fields, result fields, API endpoints, tests, and milestone items
are removed.

Arc flash may become a separate future module sharing project data but with an independent
engine, schemas, validation suite, and reports.

See DR-008 in M0-08.

---

## 5. Architecture and Implementation Questions

### OQ-011 — Celery Worker Concurrency

**Status:** ⏸ OPEN — INFRASTRUCTURE DECISION (not a code blocker for M1)

**Decision:** Not resolved in this review. Default to single worker for MVP; scale
configuration documented in infra README for production deployments.

---

### OQ-012 — Object Storage for Calculation Snapshots

**Status:** ✅ APPROVED (DR-001, 2026-07-03)

**Decision summary:** Hybrid model — PostgreSQL JSONB + S3-compatible object storage.
Both services are required; they are complementary.

PostgreSQL JSONB: InputSnapshot, structured result summaries, convergence summaries,
checksums, library manifests, audit metadata.

S3/MinIO: PDF/XLSX reports, CAD files, test imports, screenshots, dense thermal fields,
meshes, CFD files, ROM snapshots (HDF5).

Database records for S3 objects store: immutable object key, SHA-256 checksum, MIME type,
file size.

See DR-001 in M0-08.

---

### OQ-013 — ROM Training Data Generation Strategy

**Status:** ⏸ OPEN — Resolved at M9 design phase

**Decision:** LHS is the default; Sobol recommended for > 5 parameters. Design details
deferred to M9 planning.

---

## 6. Data and Library Questions

### OQ-014 — Initial Device Library Population

**Status:** ⏸ OPEN — DEPLOYMENT CONCERN (not a code blocker)

**Decision:** MVP ships with empty library; users import or enter data.
Import tooling is part of M1 deliverables (empty JSON templates + import script stubs).

---

### OQ-015 — Library Versioning Strategy for Field Deployments

**Status:** ✅ APPROVED (DR-002, 2026-07-03)

**Decision summary:** Immutable library releases with semantic version, SHA-256 content
hash, status, effective date, source reference, creator, approver, and approval date.

InputSnapshot must pin library name, version, and content hash. Historical calculations
must always resolve to their original library data.

Signed offline dataset-manifest package required for field deployments (format defined
in M0-09).

See DR-002 in M0-08 and M0-09 for full specification.

---

## 7. Status Summary

| OQ-ID | Topic | Status |
|-------|-------|--------|
| OQ-001 | Skin/proximity effect (K_AC staged method) | ✅ APPROVED |
| OQ-002 | Contact resistance hierarchy (joint_condition enum) | ✅ APPROVED |
| OQ-003 | Transformer harmonic loading | ⏸ OPEN (low priority) |
| OQ-004 | Wall eddy current losses | ⏸ OPEN (low priority) |
| OQ-005 | Adjacent cubicle heat transfer | ⏸ OPEN (low priority) |
| OQ-006 | Reverse fan flow (5 operating states) | ✅ APPROVED |
| OQ-007 | Transient thermal analysis | ✅ DEFERRED — Phase 2 |
| OQ-008 | IEC TR 60890 licensed dataset | ⏸ OPEN (deployment) |
| OQ-009 | North American temperature limits | ✅ DEFERRED — Phase 3 |
| OQ-010 | IEEE 1584-2018 electrode configuration | ✅ REMOVED FROM SCOPE |
| OQ-011 | Celery worker concurrency | ⏸ OPEN (infrastructure) |
| OQ-012 | Object storage strategy | ✅ APPROVED |
| OQ-013 | ROM training sampling strategy | ⏸ OPEN (M9 phase) |
| OQ-014 | Initial device library population | ⏸ OPEN (deployment) |
| OQ-015 | Library versioning for field deployments | ✅ APPROVED |

**M1 blockers remaining:** None. All questions blocking M1 are resolved or deferred.

---

## 8. Approval Record

| OQ-ID | Resolved Date | Decision | Approved By |
|-------|---------------|----------|-------------|
| OQ-001 | 2026-07-03 | APPROVED — staged K_AC methodology (DR-003) | Conditional engineering approval |
| OQ-002 | 2026-07-03 | APPROVED — data hierarchy; joint_condition enum (DR-004) | Conditional engineering approval |
| OQ-006 | 2026-07-03 | APPROVED — 5 fan operating states (DR-005) | Conditional engineering approval |
| OQ-007 | 2026-07-03 | DEFERRED — Phase 2; preserve interfaces (DR-006) | Conditional engineering approval |
| OQ-009 | 2026-07-03 | DEFERRED — Phase 3; profile architecture required (DR-007) | Conditional engineering approval |
| OQ-010 | 2026-07-03 | REMOVED FROM SCOPE — arc flash excluded from MVP (DR-008) | Conditional engineering approval |
| OQ-012 | 2026-07-03 | APPROVED — hybrid PostgreSQL + S3 (DR-001) | Conditional engineering approval |
| OQ-015 | 2026-07-03 | APPROVED — immutable library releases (DR-002) | Conditional engineering approval |
