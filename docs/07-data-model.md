# Data Model — LV Switchboard Thermal Digital Twin

**Document ID:** THERM-DAT-001  
**Revision:** 0.1 (Draft for Engineering Review)  
**Date:** 2026-07-03  
**Status:** Pending Approval

---

## 1. Purpose

This document specifies the data model for ThermPro: the entities, their fields,
relationships, versioning strategy, and the JSON contract between the frontend, backend
API, and numerical engine. It forms the source of truth for database schema design and
API contract definition.

---

## 2. Entity Overview

```
Project
 └─ Assembly
     └─ Enclosure  (1..N)
         ├─ Surface  (N)
         ├─ Door / Panel  (N)
         ├─ Compartment  (N)
         │   ├─ Partition  (N)
         │   ├─ InternalOpening  (N)
         │   └─ ThermalCell  (N, generated)
         ├─ Device  (N)
         ├─ BusbarRun  (N)
         │   ├─ BusbarSegment  (N)
         │   └─ BusbarJoint  (N)
         ├─ Conductor  (N)
         ├─ Fan  (N)
         ├─ ExternalOpening  (N)
         ├─ Filter  (N)
         ├─ Duct  (N)
         ├─ TemperatureProbe  (N)
         └─ AirflowProbe  (N)

Libraries (versioned, shared across projects):
 ├─ MaterialLibrary
 ├─ DeviceLibrary
 ├─ ConductorLibrary
 └─ VentilationDeviceLibrary

Calculation (one per run):
 ├─ CalculationRun
 │   ├─ InputSnapshot (immutable JSON)
 │   ├─ ResultSnapshot (immutable JSON)
 │   ├─ ConvergenceTrace
 │   └─ AuditRecord
```

---

## 3. Common Fields

Every domain entity inherits the following base fields:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID (v4) | Primary key |
| project_id | UUID | Foreign key to Project |
| enclosure_id | UUID | Foreign key to Enclosure (null for project-level entities) |
| entity_type | string | Discriminator for polymorphic queries |
| source | enum | CALCULATED, MANUFACTURER, MEASURED, ASSUMED |
| source_document | string | Document title, standard reference, or "User input" |
| source_page | string | Page or section reference |
| data_confidence | enum | HIGH, MEDIUM, LOW, UNKNOWN |
| revision | integer | Incremented on every save |
| created_at | datetime (UTC) | ISO 8601 |
| modified_at | datetime (UTC) | ISO 8601 |
| created_by | string | User identifier |
| modified_by | string | User identifier |
| notes | string | Free-text notes |

---

## 4. Core Entities

### 4.1 Project

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| name | string | Project name |
| customer | string | |
| assembly_designation | string | |
| standard_edition_id | UUID | FK → StandardEdition |
| system_voltage_V | float | [V] |
| frequency_Hz | float | [Hz] |
| ambient_temperature_max_C | float | [°C] |
| ambient_temperature_min_C | float | [°C] |
| reference_temperature_C | float | [°C], typically 20 °C or 35 °C |
| altitude_m | float | [m] above sea level |
| installation_type | enum | INDOOR, OUTDOOR |
| ip_rating | string | e.g. "IP54" |
| status | enum | DRAFT, IN_REVIEW, APPROVED, ARCHIVED |

### 4.2 Assembly

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| name | string | |
| description | string | |
| form_type | enum | FORM1, FORM2, FORM3, FORM4 per IEC 61439 |

### 4.3 Enclosure

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| assembly_id | UUID | FK → Assembly |
| name | string | |
| external_height_mm | float | [mm] stored; SI conversion at calculation time |
| external_width_mm | float | [mm] |
| external_depth_mm | float | [mm] |
| wall_thickness_mm | float | [mm] |
| material_id | UUID | FK → MaterialLibrary |
| installation_type | enum | FREE_STANDING, WALL_MOUNTED, FLOOR_MOUNTED, FLUSH_MOUNTED |
| position_x_mm | float | X position of this enclosure in the assembly [mm] |
| position_y_mm | float | Y position [mm] |
| position_z_mm | float | Z position [mm] |
| adjacent_left_id | UUID | FK → Enclosure (nullable) |
| adjacent_right_id | UUID | FK → Enclosure (nullable) |
| adjacent_rear_covered | boolean | True if rear wall is against a wall |
| plinth_height_mm | float | [mm]; 0 if no plinth |
| colour | string | RAL or hex for report |

### 4.4 Surface

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| enclosure_id | UUID | FK → Enclosure |
| face | enum | TOP, BOTTOM, FRONT, REAR, LEFT, RIGHT |
| area_m2 | float | Computed from enclosure dimensions |
| exposed | boolean | True if the face can convect to ambient |
| covering_factor | float | 0.0 (fully exposed) to 1.0 (fully covered) |
| emissivity | float | Outer surface emissivity |
| convection_factor | float | Multiplier on h_ext; 1.0 default |

### 4.5 Compartment

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| enclosure_id | UUID | FK → Enclosure |
| name | string | |
| x_min_mm | float | Internal coordinate bounds |
| x_max_mm | float | |
| y_min_mm | float | |
| y_max_mm | float | |
| z_min_mm | float | |
| z_max_mm | float | |
| form_separation | string | Separation type from adjacent compartments |

### 4.6 Partition

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| enclosure_id | UUID | |
| compartment_id_from | UUID | Compartment on one side |
| compartment_id_to | UUID | Compartment on other side |
| orientation | enum | VERTICAL, HORIZONTAL |
| x_mm, y_mm, z_mm | float | Position of partition centroid |
| width_mm | float | |
| height_mm | float | |
| thickness_mm | float | |
| material_id | UUID | FK → MaterialLibrary |
| perforation_fraction | float | 0.0 = solid, >0 = perforated |
| perforation_pattern | string | Description or ID |

### 4.7 ExternalOpening

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| enclosure_id | UUID | |
| compartment_id | UUID | Which compartment this opening serves |
| face | enum | TOP, BOTTOM, FRONT, REAR, LEFT, RIGHT |
| x_mm, y_mm | float | Position on face |
| width_mm, height_mm | float | Physical dimensions |
| free_area_m2 | float | Effective free area after frame/louvres |
| free_area_ratio | float | free_area / total_area |
| discharge_coefficient | float | Cd; default 0.6 |
| type | enum | GRILLE, LOUVRE, PLAIN_HOLE, LEAKAGE |
| filter_id | UUID | FK → Filter (nullable) |
| elevation_centroid_m | float | Height of centroid above floor [m] |

### 4.8 InternalOpening

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| partition_id | UUID | FK → Partition |
| x_mm, y_mm | float | Position on partition |
| width_mm, height_mm | float | |
| free_area_m2 | float | |
| discharge_coefficient | float | |

### 4.9 Fan

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| enclosure_id | UUID | |
| compartment_id | UUID | |
| device_library_id | UUID | FK → VentilationDeviceLibrary |
| type | enum | SUPPLY, EXHAUST, INTERNAL_CIRCULATION |
| x_mm, y_mm, z_mm | float | Centroid position |
| orientation_vector | json | Unit vector [dx, dy, dz] of flow direction |
| speed_rpm | float | Installed speed |
| control_mode | enum | FIXED, THERMOSTAT, SPEED_CONTROLLED |
| control_setpoint_on_C | float | Thermostat-on temperature |
| control_setpoint_off_C | float | Thermostat-off temperature |
| control_curve_json | json | [(T, speed_fraction), ...] for variable speed |
| is_active | boolean | User override |

### 4.10 Device

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| enclosure_id | UUID | |
| compartment_id | UUID | Assigned compartment |
| device_library_id | UUID | FK → DeviceLibrary |
| x_mm, y_mm, z_mm | float | Position of device origin (bottom-left-front corner) |
| rotation_deg | float | Rotation around Y axis |
| mounting | enum | DIN_RAIL, PANEL_MOUNTED, BUSBAR_MOUNTED, FLOOR_STANDING |
| circuit_id | UUID | FK → Circuit (electrical loading) |
| actual_current_A | float | Actual operating current |
| loss_mode | enum | CALCULATED, MANUFACTURER, MEASURED, ASSUMED |
| actual_loss_W | float | Overrides calculated loss when loss_mode ≠ CALCULATED |

### 4.11 BusbarRun

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| enclosure_id | UUID | |
| name | string | e.g. "Main busbar L1" |
| phase | enum | L1, L2, L3, N, PE |
| conductor_library_id | UUID | FK → ConductorLibrary |
| segments | UUID[] | Ordered list of BusbarSegment IDs |

### 4.12 BusbarSegment

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| busbar_run_id | UUID | |
| compartment_id | UUID | |
| x_start_mm, y_start_mm, z_start_mm | float | Start point |
| x_end_mm, y_end_mm, z_end_mm | float | End point |
| cross_section_mm2 | float | Cross-sectional area |
| width_mm, height_mm | float | Physical dimensions for thermal calc |
| current_A | float | RMS current on this segment |
| orientation | enum | HORIZONTAL_FLAT, HORIZONTAL_EDGE, VERTICAL |

### 4.13 ThermalCell

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| enclosure_id | UUID | |
| compartment_id | UUID | |
| x_centre_mm, y_centre_mm, z_centre_mm | float | Cell centroid |
| width_mm, height_mm, depth_mm | float | Cell dimensions |
| cell_type | enum | AIR, SOLID_WALL, SOLID_PARTITION, SOLID_DEVICE, SOLID_BUSBAR |
| is_generated | boolean | True = auto-generated; False = user-defined |

---

## 5. Library Schemas

### 5.1 MaterialLibrary

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| name | string | e.g. "Mild steel, painted" |
| version | integer | |
| thermal_conductivity_W_mK | float | k |
| density_kg_m3 | float | ρ |
| specific_heat_J_kgK | float | cp |
| emissivity | float | ε; outer surface |
| temperature_limit_C | float | Maximum service temperature |
| source | string | |

### 5.2 DeviceLibrary

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| manufacturer | string | |
| model_reference | string | |
| frame_size | string | |
| rated_current_A | float | I_n |
| dimensions_json | json | {"height_mm", "width_mm", "depth_mm"} |
| mounting | enum | |
| rated_loss_W | float | At I_n and rated ambient |
| fixed_loss_W | float | P_fixed (null if unavailable) |
| variable_loss_W | float | P_variable at I_n (null if unavailable) |
| reference_ambient_C | float | Ambient at which rated_loss was measured |
| max_permissible_ambient_C | float | |
| derating_curve_json | json | [{"ambient_C": x, "derating_factor": y}, ...] |
| data_confidence | enum | HIGH, MEDIUM, LOW |
| source_document | string | |
| licence_reference | string | |
| version | integer | |

### 5.3 ConductorLibrary

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| name | string | e.g. "Copper flat bar 100×10" |
| material | enum | COPPER, ALUMINIUM, OTHER |
| resistivity_ref_ohm_m | float | ρ_e at T_ref |
| temp_coefficient_1_K | float | α |
| temp_ref_C | float | T_ref for resistivity |
| cross_section_mm2 | float | |
| width_mm, height_mm | float | For busbars |
| emissivity | float | |
| plating | enum | BARE, SILVER, TIN, NICKEL |
| ac_resistance_multiplier | float | K_AC |
| joint_resistance_ohm | float | Per joint |
| version | integer | |

### 5.4 VentilationDeviceLibrary

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| manufacturer | string | |
| model_reference | string | |
| type | enum | SUPPLY_FAN, EXHAUST_FAN, INTERNAL_FAN |
| rated_airflow_m3s | float | At rated speed and free air |
| rated_pressure_Pa | float | At rated speed and zero flow (stall) |
| fan_curve_json | json | [{"flow_m3s": q, "pressure_Pa": p}, ...] |
| rated_speed_rpm | float | |
| shaft_power_W | float | |
| motor_efficiency | float | |
| heat_to_air_W | float | Heat added to airstream at rated conditions |
| filter_curve_json | json | [{"flow_m3s": q, "pressure_drop_Pa": dp}, ...] (for filter-fan units) |
| free_area_ratio | float | For grilles/filters |
| noise_dBA | float | At rated conditions (informational) |
| failure_mode | enum | FAIL_OPEN, FAIL_CLOSED, FAIL_LAST |
| version | integer | |

---

## 6. Calculation Run Schema

### 6.1 CalculationRun

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| project_id | UUID | |
| name | string | User-assigned name |
| calculation_mode | enum | IEC_60890, NODAL_THERMAL, AIRFLOW_NETWORK, COUPLED |
| status | enum | PENDING, RUNNING, CONVERGED, NON_CONVERGED, FAILED |
| submitted_at | datetime | |
| started_at | datetime | |
| completed_at | datetime | |
| submitted_by | string | User ID |
| solver_version | string | Semantic version of the solver module |
| equation_doc_revision | string | Revision of THERM-EQN-001 used |
| input_snapshot_id | UUID | FK → InputSnapshot |
| result_snapshot_id | UUID | FK → ResultSnapshot |
| convergence_trace_id | UUID | FK → ConvergenceTrace |
| audit_record_id | UUID | FK → AuditRecord |
| warnings | json | [{"code": "W001", "message": "...", "location": "..."}] |

### 6.2 InputSnapshot

Immutable. Created at calculation submission time.

```json
{
  "schema_version": "1.0",
  "snapshot_timestamp": "2026-07-03T10:00:00Z",
  "project_id": "<uuid>",
  "enclosure_geometry": { ... },
  "compartments": [ ... ],
  "devices": [ ... ],
  "busbars": [ ... ],
  "fans": [ ... ],
  "openings": [ ... ],
  "electrical_loading": { ... },
  "material_library_version": "<uuid>",
  "device_library_version": "<uuid>",
  "conductor_library_version": "<uuid>",
  "ventilation_library_version": "<uuid>",
  "standard_coefficients_version": "<uuid>",
  "solver_settings": {
    "max_outer_iterations": 50,
    "max_inner_iterations": 100,
    "convergence_T_K": 0.1,
    "convergence_flow_fraction": 0.005,
    "convergence_power_fraction": 0.005,
    "energy_imbalance_limit": 0.01,
    "mass_imbalance_limit": 0.005,
    "relaxation_factor": 0.7
  }
}
```

### 6.3 ResultSnapshot

Immutable. Created after successful convergence.

```json
{
  "schema_version": "1.0",
  "calculation_run_id": "<uuid>",
  "converged": true,
  "convergence_iterations_outer": 12,
  "convergence_iterations_inner": 8,
  "final_energy_imbalance_fraction": 0.0003,
  "final_mass_imbalance_fraction": 0.0001,
  "node_results": [
    {
      "node_id": "<uuid>",
      "node_type": "AIR",
      "temperature_K": 328.5,
      "temperature_rise_K": 13.5,
      "limit_K": 40.0,
      "margin_K": 26.5,
      "severity": "PASS",
      "heat_source_W": 0.0,
      "heat_in_W": 45.2,
      "heat_out_W": 45.2,
      "energy_balance_fraction": 0.0001
    }
  ],
  "device_results": [ ... ],
  "busbar_results": [ ... ],
  "airflow_results": [ ... ],
  "hot_spots": [ ... ],
  "mode_used": "COUPLED",
  "applicability_status": "ELIGIBLE_WITH_WARNINGS",
  "warnings": [ ... ]
}
```

### 6.4 ConvergenceTrace

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| calculation_run_id | UUID | |
| iterations | json | [{"outer_iter": 1, "inner_iter": 8, "max_delta_T_K": 12.3, "max_delta_flow_fraction": 0.15, "max_delta_power_fraction": 0.08}, ...] |
| converged | boolean | |
| termination_reason | enum | CONVERGED, MAX_ITERATIONS, DIVERGED, SINGULAR_MATRIX, INVALID_STATE |

### 6.5 AuditRecord

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| calculation_run_id | UUID | |
| checksum_algorithm | string | "SHA-256" |
| input_checksum | string | SHA-256 of serialised InputSnapshot |
| result_checksum | string | SHA-256 of serialised ResultSnapshot |
| combined_checksum | string | SHA-256 of input_checksum + result_checksum |
| created_at | datetime | |
| created_by | string | |

---

## 7. Versioning Strategy

### 7.1 Library Versioning

Every create or update to a library record:
1. Creates a new record with an incremented `version` integer.
2. The old record is retained (soft-delete or versioned table).
3. Calculation runs reference specific version UUIDs, not the latest.

### 7.2 Calculation Snapshot Immutability

Once a `CalculationRun` reaches status CONVERGED or NON_CONVERGED:
- Its `InputSnapshot` and `ResultSnapshot` are locked (immutable).
- No update operation is permitted on these records.
- If the engineer re-runs a calculation with modified inputs, a new `CalculationRun` is
  created with a new `InputSnapshot`.

### 7.3 Project Revision History

The Project entity maintains a timeline of states using event sourcing or snapshot+delta
approach. Every significant change (geometry edit, device placement, library update) is
recorded with a timestamp, user, and description.

---

## 8. Numerical Engine JSON Contract

The numerical engine is a Python module that accepts and returns versioned JSON.

**Input contract version:** `"engine_input_v1"`

The engine SHALL:
1. Validate the input JSON against the InputSnapshot schema.
2. Reject inputs with schema_version it does not recognise.
3. Perform all calculations using only data from the input JSON (no database access).
4. Return a ResultSnapshot JSON or an error structure with a reason code.
5. Include its own version in the result.
6. Never write to the database directly.

---

*End of THERM-DAT-001*
