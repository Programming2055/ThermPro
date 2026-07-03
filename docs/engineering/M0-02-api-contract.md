# API Contract — LV Switchboard Thermal Digital Twin

**Document:** M0-02  
**Milestone:** 0  
**Date:** 2026-07-03  
**Status:** Pending Engineering Approval  
**Source:** THERM-ARCH-001 Rev 0.2; THERM-DAT-001 Rev 0.2

---

## 1. Conventions

- Base URL: `https://{host}/api/v1`
- Authentication: Bearer JWT (`Authorization: Bearer <token>`)
- Content-Type: `application/json`
- All timestamps: ISO 8601 UTC (`2026-07-03T12:00:00Z`)
- All UUIDs: RFC 4122 v4 (`xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`)
- Pagination: `?page=1&page_size=20`; response includes `total`, `page`, `page_size`
- Error response shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": [{"field": "name", "issue": "required"}]
  }
}
```

- API version strategy: URL-path versioned (`/api/v1/`, `/api/v2/`). Breaking changes
  require a new version prefix.

---

## 2. Endpoint Groups

| Group | Prefix | Description |
|-------|--------|-------------|
| Projects | `/projects` | CRUD for projects and assemblies |
| Enclosures | `/enclosures` | Enclosure geometry and properties |
| Devices | `/devices` | Device placement and loading |
| Busbars | `/busbars` | BusbarRun, Segment, and Joint management |
| Fans & Openings | `/ventilation` | Fans, openings, filters, ducts |
| Libraries | `/libraries` | Material, device, conductor, ventilation device libraries |
| Calculations | `/calculations` | Submit and retrieve calculation runs |
| Results | `/results` | Result retrieval and export |
| Arc Flash | `/arc-flash` | IEEE 1584-2018 screening (INFORMATIVE) |
| ROM | `/rom` | Reduced-order model build and evaluate |
| Reports | `/reports` | Report generation and download |
| Audit | `/audit` | Calculation audit trail |
| Admin | `/admin` | Library administration (licensed dataset import) |
| Auth | `/auth` | Authentication tokens |

---

## 3. Endpoint Definitions

### 3.1 Projects

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `GET` | `/projects` | List all projects (paginated) | — | `ProjectListResponse` |
| `POST` | `/projects` | Create a new project | `ProjectCreate` | `Project` |
| `GET` | `/projects/{project_id}` | Get project by ID | — | `Project` |
| `PUT` | `/projects/{project_id}` | Replace project | `ProjectUpdate` | `Project` |
| `PATCH` | `/projects/{project_id}` | Partial update | `ProjectPatch` | `Project` |
| `DELETE` | `/projects/{project_id}` | Delete project (soft delete) | — | `204 No Content` |
| `GET` | `/projects/{project_id}/history` | Revision history | — | `RevisionList` |
| `POST` | `/projects/{project_id}/duplicate` | Clone project | `DuplicateOptions` | `Project` |

**ProjectCreate body:**
```json
{
  "name": "string (required)",
  "customer": "string (optional)",
  "assembly_designation": "string (optional)",
  "standard_profile": ["IEC_61439_2"],
  "system_voltage_V": 400.0,
  "frequency_Hz": 50.0,
  "service_conditions": {
    "ambient_temperature_max_C": 40.0,
    "ambient_temperature_avg_24h_C": 35.0,
    "relative_humidity_max_percent": 50.0,
    "altitude_m": 0.0,
    "pollution_degree": 2
  },
  "indoor_outdoor": "INDOOR",
  "ip_rating": "IP31",
  "reference_temperature_C": 20.0,
  "notes": "string (optional)"
}
```

---

### 3.2 Enclosures

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `GET` | `/projects/{project_id}/enclosures` | List enclosures | — | `EnclosureList` |
| `POST` | `/projects/{project_id}/enclosures` | Create enclosure | `EnclosureCreate` | `Enclosure` |
| `GET` | `/enclosures/{enclosure_id}` | Get enclosure | — | `Enclosure` |
| `PUT` | `/enclosures/{enclosure_id}` | Replace enclosure | `EnclosureUpdate` | `Enclosure` |
| `DELETE` | `/enclosures/{enclosure_id}` | Delete enclosure | — | `204` |
| `GET` | `/enclosures/{enclosure_id}/geometry` | Full geometry tree | — | `GeometryTree` |
| `POST` | `/enclosures/{enclosure_id}/validate` | Geometry validation | — | `ValidationReport` |

**ValidationReport response:**
```json
{
  "valid": false,
  "errors": [
    {"code": "OVERLAP", "entity_ids": ["uuid1", "uuid2"], "message": "Devices overlap"}
  ],
  "warnings": [
    {"code": "CLEARANCE", "entity_ids": ["uuid3"], "message": "Clearance < 25mm"}
  ]
}
```

---

### 3.3 Devices

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `GET` | `/enclosures/{enclosure_id}/devices` | List devices | — | `DeviceList` |
| `POST` | `/enclosures/{enclosure_id}/devices` | Add device | `DeviceCreate` | `Device` |
| `GET` | `/devices/{device_id}` | Get device | — | `Device` |
| `PUT` | `/devices/{device_id}` | Replace device | `DeviceUpdate` | `Device` |
| `DELETE` | `/devices/{device_id}` | Remove device | — | `204` |

---

### 3.4 Busbars

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `GET` | `/enclosures/{enclosure_id}/busbars` | List busbar runs | — | `BusbarRunList` |
| `POST` | `/enclosures/{enclosure_id}/busbars` | Create busbar run | `BusbarRunCreate` | `BusbarRun` |
| `GET` | `/busbars/{run_id}` | Get busbar run with segments and joints | — | `BusbarRunDetail` |
| `PUT` | `/busbars/{run_id}` | Replace | `BusbarRunUpdate` | `BusbarRun` |
| `DELETE` | `/busbars/{run_id}` | Delete | — | `204` |
| `POST` | `/busbars/{run_id}/segments` | Add segment | `SegmentCreate` | `BusbarSegment` |
| `PUT` | `/segments/{segment_id}` | Replace segment | `SegmentUpdate` | `BusbarSegment` |
| `DELETE` | `/segments/{segment_id}` | Delete segment | — | `204` |
| `POST` | `/busbars/{run_id}/joints` | Add joint | `JointCreate` | `BusbarJoint` |
| `PUT` | `/joints/{joint_id}` | Replace joint | `JointUpdate` | `BusbarJoint` |
| `DELETE` | `/joints/{joint_id}` | Delete joint | — | `204` |

---

### 3.5 Calculations

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `POST` | `/calculations` | Submit calculation | `CalculationSubmit` | `CalculationRun` |
| `GET` | `/calculations/{run_id}` | Get run status | — | `CalculationRun` |
| `DELETE` | `/calculations/{run_id}` | Cancel run | — | `204` |
| `GET` | `/calculations/{run_id}/progress` | SSE stream of progress | — | `text/event-stream` |
| `GET` | `/projects/{project_id}/calculations` | List runs for project | — | `CalculationRunList` |
| `GET` | `/enclosures/{enclosure_id}/calculations` | List runs for enclosure | — | `CalculationRunList` |

**CalculationSubmit body:**
```json
{
  "enclosure_id": "uuid",
  "mode": "MODE_2",
  "solver_settings": {
    "max_outer_iterations": 50,
    "max_inner_iterations": 100,
    "convergence_T_K": 0.1,
    "convergence_flow_fraction": 0.005,
    "convergence_power_fraction": 0.005,
    "energy_imbalance_limit": 0.01,
    "mass_imbalance_limit": 0.005,
    "relaxation_factor": 0.7
  },
  "overrides": {}
}
```

**CalculationRun response:**
```json
{
  "id": "uuid",
  "enclosure_id": "uuid",
  "mode": "MODE_2",
  "status": "RUNNING",
  "schema_version": "1.0",
  "engine_version": "0.1.0",
  "submitted_at": "2026-07-03T10:00:00Z",
  "started_at": "2026-07-03T10:00:01Z",
  "completed_at": null,
  "result_snapshot": null
}
```

**SSE Progress stream:**
```
event: progress
data: {"iteration": 5, "max_delta_T_K": 2.1, "status": "RUNNING"}

event: complete
data: {"status": "CONVERGED", "run_id": "uuid"}
```

---

### 3.6 Results

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `GET` | `/calculations/{run_id}/result` | Full result snapshot | `ResultSnapshot` |
| `GET` | `/calculations/{run_id}/result/temperatures` | Temperature field only | `TemperatureField` |
| `GET` | `/calculations/{run_id}/result/hotspots` | Hotspot list | `HotspotList` |
| `GET` | `/calculations/{run_id}/result/derating` | Derating recommendations | `DeratingReport` |
| `GET` | `/calculations/{run_id}/result/compliance` | Compliance check | `ComplianceReport` |
| `GET` | `/calculations/{run_id}/result/convergence` | Convergence trace | `ConvergenceTrace` |

**ComplianceReport response:**
```json
{
  "run_id": "uuid",
  "standard_profile": ["IEC_61439_2"],
  "compliant": true,
  "checks": [
    {
      "id": "TEMP_RISE_BUSBAR",
      "entity_id": "uuid",
      "standard": "IEC_61439_2",
      "limit_K": 70.0,
      "actual_rise_K": 52.3,
      "margin_K": 17.7,
      "status": "PASS"
    }
  ]
}
```

---

### 3.7 Arc Flash (INFORMATIVE)

> **DISCLAIMER:** Arc-flash outputs are INFORMATIVE screening results only, based on
> IEEE 1584-2018 parametric equations. They do not constitute an arc-flash hazard study.
> A qualified engineer must perform a complete arc-flash analysis per NFPA 70E before
> any work on energised equipment.

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `POST` | `/arc-flash/screen` | Run IEEE 1584-2018 screening | `ArcFlashInput` | `ArcFlashResult` |
| `GET` | `/arc-flash/{run_id}` | Get previous screening result | — | `ArcFlashResult` |

**ArcFlashInput body:**
```json
{
  "enclosure_id": "uuid",
  "working_distance_mm": 610.0,
  "bolted_fault_current_kA": 25.0,
  "arcing_fault_current_kA": null,
  "upstream_clearing_time_s": 0.1,
  "system_voltage_V": 400.0,
  "electrode_configuration": "VCB",
  "conductor_gap_mm": 32.0
}
```

**ArcFlashResult response:**
```json
{
  "label": "INFORMATIVE",
  "disclaimer": "This is a screening result only. See full disclaimer in report.",
  "incident_energy_J_cm2": 4.2,
  "arc_flash_boundary_mm": 920.0,
  "ppe_category": 2,
  "standard": "IEEE 1584-2018",
  "inputs_used": {}
}
```

---

### 3.8 ROM (Reduced-Order Model)

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| `POST` | `/rom/build` | Build ROM from parameter sweep | `ROMBuildRequest` | `ROMBuildJob` |
| `GET` | `/rom/{rom_id}` | Get ROM metadata | — | `ROM` |
| `POST` | `/rom/{rom_id}/evaluate` | Evaluate ROM at parameter point | `ROMEvaluateRequest` | `ROMResult` |
| `GET` | `/rom/{rom_id}/uncertainty` | UQ analysis results | — | `UQReport` |
| `GET` | `/projects/{project_id}/roms` | List ROMs for project | — | `ROMList` |

---

### 3.9 Libraries (Admin-controlled)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/libraries/materials` | List materials | Any |
| `POST` | `/libraries/materials` | Add material | Admin |
| `PUT` | `/libraries/materials/{id}` | Update material | Admin |
| `GET` | `/libraries/devices` | List device library entries | Any |
| `POST` | `/libraries/devices` | Add device | Admin |
| `GET` | `/libraries/conductors` | List conductors | Any |
| `POST` | `/libraries/conductors` | Add conductor | Admin |
| `GET` | `/libraries/ventilation` | List fans/filters | Any |
| `POST` | `/libraries/ventilation` | Add ventilation device | Admin |
| `POST` | `/admin/iec60890/import` | Import licensed IEC TR 60890 dataset | Super-Admin |
| `GET` | `/admin/iec60890/status` | Check if dataset is present | Admin |

**Note on IEC TR 60890 import:** The import endpoint accepts the administrator's JSON
file which contains the licensed coefficient tables. The system ships with a null-valued
template only. The template is returned by `GET /admin/iec60890/template`.

---

### 3.10 Reports

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `POST` | `/reports` | Generate report | `ReportJob` |
| `GET` | `/reports/{report_id}` | Get report status | `ReportJob` |
| `GET` | `/reports/{report_id}/download` | Download PDF | `application/pdf` |
| `GET` | `/reports/{report_id}/excel` | Download Excel | `application/vnd.openxmlformats…` |

**ReportJob request:**
```json
{
  "run_id": "uuid",
  "format": "PDF",
  "include_sections": ["SUMMARY", "TEMPERATURES", "DERATING", "COMPLIANCE", "CONVERGENCE"],
  "monochrome": false,
  "include_arc_flash": false
}
```

---

### 3.11 Audit

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/audit/runs/{run_id}` | Full audit record for a run |
| `GET` | `/audit/projects/{project_id}` | All audit events for a project |

**AuditRecord response:**
```json
{
  "run_id": "uuid",
  "engine_version": "0.1.0",
  "schema_version": "1.0",
  "input_hash_sha256": "abc123...",
  "result_hash_sha256": "def456...",
  "library_versions": {
    "material_library": "1.0.0",
    "device_library": "1.2.3"
  },
  "reproduced_at": null
}
```

---

## 4. HTTP Status Code Usage

| Code | Meaning |
|------|---------|
| 200 | Success (GET, PUT, PATCH) |
| 201 | Created (POST) |
| 204 | No content (DELETE, cancel) |
| 400 | Bad request (validation error) |
| 401 | Unauthenticated |
| 403 | Forbidden (insufficient role) |
| 404 | Not found |
| 409 | Conflict (duplicate name, locked run) |
| 422 | Unprocessable entity (schema error) |
| 429 | Rate limited |
| 500 | Internal server error |
| 503 | Solver unavailable (queue full) |

---

## 5. Authentication

- POST `/auth/token` — login; returns `access_token` (JWT, 1h) and `refresh_token` (7d)
- POST `/auth/refresh` — exchange refresh token for new access token
- POST `/auth/logout` — revoke refresh token

JWT payload includes: `user_id`, `role` (`VIEWER / ENGINEER / ADMIN / SUPER_ADMIN`),
`organisation_id`, `exp`.

---

## 6. Role-Based Access

| Role | Can Read | Can Modify | Can Submit Calc | Can Admin Libraries |
|------|----------|------------|-----------------|---------------------|
| VIEWER | Own org | No | No | No |
| ENGINEER | Own org | Own projects | Yes | No |
| ADMIN | Own org | All org | Yes | Yes |
| SUPER_ADMIN | All | All | Yes | Yes + IEC 60890 import |

---

## 7. WebSocket / SSE

Calculation progress uses Server-Sent Events (SSE) on:
`GET /calculations/{run_id}/progress`

The connection stays open until the run reaches a terminal status
(CONVERGED, NON_CONVERGED, FAILED, CANCELLED).
