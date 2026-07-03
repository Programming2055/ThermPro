# Dataset and Library Versioning Policy — LV Switchboard Thermal Digital Twin

**Document:** M0-09  
**Milestone:** 0 (correction commit)  
**Date:** 2026-07-03  
**Status:** APPROVED (DR-002)  
**Source:** OQ-015 resolution; THERM-DAT-001 Rev 0.2

---

## 1. Purpose

This document defines the versioning, immutability, content-hashing, and manifest
requirements for all data libraries used by thermpro_engine. Every calculation run must
be reproducible from its original library data at any future date.

---

## 2. Library Types Covered

| Library | Covers | Administrator-controlled |
|---------|--------|--------------------------|
| `MaterialLibrary` | Wall materials, conductors, surface finishes | Yes |
| `DeviceLibrary` | Device thermal loss models, derating tables | Yes |
| `ConductorLibrary` | Cable cross-sections, current capacity | Yes |
| `VentilationDeviceLibrary` | Fan P-Q curves, filter pressure drops | Yes |
| `IEC60890CoefficientLibrary` | Licensed IEC TR 60890 empirical coefficients | Super-Admin only |
| `BusbarJointLibrary` | Approved joint contact resistance table | Yes |
| `ACResistanceLibrary` | Manufacturer / correlation K_AC factors | Yes |

---

## 3. Library Release Structure

Every library release is an immutable record with the following mandatory fields:

```json
{
  "library_name": "MaterialLibrary",
  "semantic_version": "1.2.0",
  "revision_id": "uuid",
  "content_hash_sha256": "a1b2c3d4...",
  "status": "APPROVED",
  "effective_date": "2026-07-01",
  "source_reference": "Manufacturer datasheet Rev C, 2026-06-15",
  "creator": "j.smith@example.com",
  "approver": "p.jones@example.com",
  "approval_date": "2026-07-01",
  "supersedes_version": "1.1.0",
  "change_summary": "Added stainless steel 316L entry; corrected emissivity of mild steel",
  "entry_count": 42
}
```

### 3.1 Semantic Version Rules

- **MAJOR** increment: Entries removed or renamed; schema of entry record changed.
  Existing InputSnapshots pinning this version may fail to resolve.
- **MINOR** increment: New entries added; existing entries unchanged.
  Backward compatible.
- **PATCH** increment: Typo or unit correction that does not change calculated values
  by more than the stated precision.

### 3.2 Status Values

| Status | Meaning |
|--------|---------|
| `DRAFT` | Under preparation; not usable in production calculations |
| `APPROVED` | Approved by authorised approver; usable in calculations |
| `SUPERSEDED` | A newer APPROVED version exists; still resolvable for historical runs |
| `WITHDRAWN` | Found to be incorrect or unsafe; calculations using this version must be flagged |

Only `APPROVED` versions may be selected by the solver for new calculation runs.
`SUPERSEDED` versions remain in the database and resolvable indefinitely.
`WITHDRAWN` versions are preserved but flagged; any run that used a withdrawn version
must be flagged `RESULT_REQUIRES_REVIEW` in the UI.

### 3.3 Content Hash

The `content_hash_sha256` is computed over the canonical JSON serialisation of the full
library entry set, sorted by entry ID, with no insignificant whitespace. This hash is
computed at the time of APPROVED status transition and is immutable thereafter.

Any change to any entry — including a decimal correction — creates a new library release
with a new version and a new content hash.

---

## 4. InputSnapshot Library Pinning

Every `InputSnapshot` must include a `library_manifest` block:

```json
{
  "schema_version": "1.0",
  "library_manifest": {
    "material_library": {
      "name": "MaterialLibrary",
      "version": "1.2.0",
      "content_hash_sha256": "a1b2c3d4..."
    },
    "device_library": {
      "name": "DeviceLibrary",
      "version": "2.0.1",
      "content_hash_sha256": "e5f6a7b8..."
    },
    "conductor_library": {
      "name": "ConductorLibrary",
      "version": "1.0.0",
      "content_hash_sha256": "c9d0e1f2..."
    },
    "ventilation_device_library": {
      "name": "VentilationDeviceLibrary",
      "version": "1.1.0",
      "content_hash_sha256": "a3b4c5d6..."
    },
    "iec60890_coefficient_library": {
      "name": "IEC60890CoefficientLibrary",
      "version": "2022.1.0",
      "content_hash_sha256": "..."
    },
    "busbar_joint_library": {
      "name": "BusbarJointLibrary",
      "version": "1.0.0",
      "content_hash_sha256": "..."
    },
    "ac_resistance_library": {
      "name": "ACResistanceLibrary",
      "version": "1.0.0",
      "content_hash_sha256": "..."
    }
  }
}
```

Only libraries that are actually referenced by the calculation need to be included.
For example, if no joints are present, `busbar_joint_library` may be omitted.

The solver validates that each pinned hash matches the hash of the current APPROVED
version. If any hash does not match:
- Status `LIBRARY_VERSION_MISMATCH` is returned immediately.
- The solver does not proceed.
- The UI shows which library(ies) have changed.

---

## 5. Historical Resolution

The audit endpoint (`GET /audit/runs/{run_id}`) must return:
- The complete `library_manifest` as stored at submission time.
- For each library entry referenced by the run, the full entry data as it was at
  that version (not the current version).
- A flag `all_libraries_resolvable: bool` — false if any library has been WITHDRAWN
  or its version deleted.

The database must retain all library entries for all APPROVED and SUPERSEDED versions
indefinitely. Deletion of a library version record is not permitted; WITHDRAWN is the
correct terminal state.

---

## 6. Signed Offline Dataset Manifest (Field Deployments)

Field deployments (installations without continuous internet connectivity) require a
signed offline manifest package. This package enables the solver to verify library
integrity without querying the central database.

### 6.1 Manifest Package Contents

```
thermpro-dataset-manifest-v1.2.0.zip
├── manifest.json          ← top-level manifest (signed)
├── manifest.json.sig      ← detached signature (RSA-4096 or Ed25519)
├── MaterialLibrary-1.2.0.json
├── DeviceLibrary-2.0.1.json
├── ConductorLibrary-1.0.0.json
├── VentilationDeviceLibrary-1.1.0.json
└── ACResistanceLibrary-1.0.0.json
```

Note: `IEC60890CoefficientLibrary` is **never** included in manifest packages distributed
through this system. It is imported separately through the administrator's own secure
channel.

### 6.2 Manifest JSON Structure

```json
{
  "manifest_version": "1.0",
  "generated_at": "2026-07-03T12:00:00Z",
  "generated_by": "thermpro-admin-cli v1.0.0",
  "organisation": "Example Engineering Ltd",
  "engine_min_version": "1.0.0",
  "libraries": [
    {
      "name": "MaterialLibrary",
      "version": "1.2.0",
      "content_hash_sha256": "a1b2c3d4...",
      "file": "MaterialLibrary-1.2.0.json",
      "file_hash_sha256": "f7e8d9c0...",
      "status": "APPROVED",
      "effective_date": "2026-07-01"
    }
  ]
}
```

### 6.3 Signature Verification

The solver in field mode must verify the signature on `manifest.json` using the
organisation's public key embedded in the installed engine. If the signature is invalid
or the manifest is missing, the field engine must refuse to run calculations and display
a `MANIFEST_VERIFICATION_FAILED` error.

Key management (key rotation, revocation) is an administrative concern outside the scope
of this document.

---

## 7. Version Resolution Algorithm

When the solver receives an `InputSnapshot`:

```
FOR EACH library in input.library_manifest:
  1. Retrieve library record from database WHERE
       name = library.name AND version = library.version
  2. IF not found → return LIBRARY_NOT_FOUND error
  3. IF status = WITHDRAWN → return LIBRARY_WITHDRAWN error
  4. Compute SHA-256 of current stored entries (canonical form)
  5. IF computed_hash ≠ library.content_hash_sha256 → return LIBRARY_HASH_MISMATCH error
  6. PASS: use this library data for the calculation

IF all libraries verified:
  Proceed with calculation using verified library data
ELSE:
  Return LIBRARY_VERIFICATION_FAILED; do not run solver
```

---

## 8. IEC TR 60890 Coefficient Library — Special Rules

In addition to the general rules above:
- This library is importable only by a user with `SUPER_ADMIN` role.
- The import tool (`POST /admin/iec60890/import`) reads the administrator's own JSON file,
  computes the content hash, creates the library release record at status `APPROVED`,
  and stores the full entry set.
- The coefficient data is never transmitted over the API to end users; only the version
  and hash are exposed.
- The empty template (`GET /admin/iec60890/template`) contains null values for all
  coefficients; it is used only as a format guide for the administrator's import process.

---

## 9. Migration Between Library Versions

When an administrator releases a new library version, existing projects are not
automatically updated. The engineer must:
1. Open the project.
2. Review the change summary for the new version.
3. Choose to upgrade the project to the new version (creates a new calculation run
   with the new library pinned).
4. The previous run remains in history with its original library pinned.

The system must never silently update library references in existing InputSnapshots.
