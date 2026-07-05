# Domain Model — LV Switchboard Thermal Digital Twin

**Document:** M0-01  
**Milestone:** 0 (correction commit — revision 1)  
**Date:** 2026-07-03  
**Status:** CONDITIONALLY APPROVED  
**Changes from revision 0:**
- Arc flash entities and ARC_FLASH mode removed (DR-008)
- UL/ANSI standards removed from StandardProfile enum (DR-007)
- BusbarJoint: health_state replaced with joint_condition enum (DR-004)
- BusbarJoint: universal contact resistance default removed; data hierarchy added (DR-004)
- BusbarSegment: K_AC fields added (DR-003)
- Fan: operating_state enum replaces operating bool (DR-005)
- DeviceLibrary: silent +20% margin removed; uncertainty fields added (DR-009)
- LibraryRelease entity added (DR-002)
- thermal_mass_J_K field reserved on entities for transient (DR-006)

---

## 1. Entity Hierarchy

```
Project (1)
 └─ Assembly (1..N)
     └─ Enclosure (1..N)
         ├─ Surface (0..N)           wall, door, panel, plinth, roof
         ├─ Compartment (0..N)
         │   ├─ Partition (0..N)     horizontal or vertical
         │   ├─ InternalOpening (0..N)
         │   └─ ThermalCell (N)      generated; not user-created
         ├─ Device (0..N)            breakers, contactors, meters, etc.
         ├─ BusbarRun (0..N)
         │   ├─ BusbarSegment (1..N)
         │   └─ BusbarJoint (0..N)   between segments or at device terminals
         ├─ Conductor (0..N)         cables and wires
         ├─ Fan (0..N)               forced-ventilation fans
         ├─ ExternalOpening (0..N)   louvres, gland plates, cable entries
         ├─ Filter (0..N)
         ├─ Duct (0..N)
         ├─ TemperatureProbe (0..N)  measurement points (FAT / field)
         └─ AirflowProbe (0..N)
```

---

## 2. Entity Definitions

### 2.1 Project

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK, non-null | |
| `name` | string | non-null, 1–200 chars | |
| `customer` | string | optional | |
| `assembly_designation` | string | optional | |
| `standard_profile` | string[] | ≥1 element | MVP values: see §6 enum |
| `system_voltage_V` | float | >0 | |
| `frequency_Hz` | float | >0 | 50 or 60 |
| `service_conditions` | ServiceConditions | non-null | see §2.1.1 |
| `indoor_outdoor` | enum{INDOOR,OUTDOOR} | non-null | |
| `ip_rating` | string | optional | e.g. "IP31" |
| `reference_temperature_C` | float | default 20 | |
| `notes` | string | optional | |
| `created_at` | datetime | non-null | |
| `updated_at` | datetime | non-null | |
| `revision` | int | ≥0, default 0 | auto-incremented on save |

#### 2.1.1 ServiceConditions (embedded object)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `ambient_temperature_max_C` | float | ≥−25, ≤70 | IEC 61439 clause 7.1 |
| `ambient_temperature_avg_24h_C` | float | ≤ ambient_temperature_max_C | IEC 61439 clause 7.1 |
| `ambient_temperature_min_C` | float | optional | |
| `relative_humidity_max_percent` | float | 0–100 | |
| `altitude_m` | float | ≥0, default 0 | derating applies above 2000 m |
| `pollution_degree` | int | 1, 2, 3, or 4 | IEC 60664-1 |

---

### 2.2 Assembly

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `project_id` | UUID | FK Project | |
| `name` | string | non-null | |
| `installation_type` | enum | FREE_STANDING / WALL_MOUNTED / FLOOR_MOUNTED / FLUSH_MOUNTED / CEILING_MOUNTED | |
| `form_type` | int | 1, 2, 3, or 4 | IEC 61439 Form arrangement |
| `position_x_m` | float | | absolute or relative |
| `position_y_m` | float | | |
| `position_z_m` | float | | |

---

### 2.3 Enclosure

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `assembly_id` | UUID | FK Assembly | |
| `name` | string | non-null | |
| `external_height_m` | float | >0 | all dimensions in metres |
| `external_width_m` | float | >0 | |
| `external_depth_m` | float | >0 | |
| `wall_thickness_m` | float | >0 | |
| `material_id` | UUID | FK MaterialLibrary | |
| `paint_emissivity` | float | 0–1, default 0.9 | surface emissivity |
| `ip_rating` | string | optional | |
| `position_x_m` | float | | origin: lower-left-front corner |
| `position_y_m` | float | | |
| `position_z_m` | float | | |
| `adjacent_enclosure_ids` | UUID[] | | for multi-cubicle assemblies |
| `adjacent_enclosure_conductance_W_K` | float | optional | adiabatic if null |
| `restricted_surfaces` | string[] | | e.g. `["REAR","LEFT_SIDE"]` |
| `created_at` | datetime | | |
| `updated_at` | datetime | | |

---

### 2.4 Surface

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `enclosure_id` | UUID | FK Enclosure | |
| `surface_type` | enum | WALL / DOOR / PANEL / PLINTH / ROOF / FLOOR | |
| `orientation` | enum | VERTICAL / HORIZONTAL_UP / HORIZONTAL_DOWN | |
| `area_m2` | float | >0 | computed from enclosure geometry |
| `is_restricted` | bool | default false | covered/obstructed |
| `is_perforated` | bool | default false | |
| `perforation_open_area_fraction` | float | 0–1 | |
| `emissivity` | float | 0–1 | overrides enclosure default |
| `paint_finish` | string | optional | |

---

### 2.5 Compartment

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `enclosure_id` | UUID | FK Enclosure | |
| `name` | string | optional | |
| `position_x_m` | float | | lower-left-front of compartment |
| `position_y_m` | float | | |
| `position_z_m` | float | | |
| `width_m` | float | >0 | |
| `height_m` | float | >0 | |
| `depth_m` | float | >0 | |

---

### 2.6 Partition

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `compartment_id` | UUID | FK Compartment | |
| `orientation` | enum | HORIZONTAL / VERTICAL | |
| `position_m` | float | | offset from compartment origin |
| `thickness_m` | float | >0 | |
| `material_id` | UUID | FK MaterialLibrary | |
| `is_perforated` | bool | default false | |
| `open_area_fraction` | float | 0–1 | 0 = solid |

---

### 2.7 Device

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `enclosure_id` | UUID | FK Enclosure | |
| `compartment_id` | UUID | FK Compartment, optional | |
| `device_library_id` | UUID | FK DeviceLibrary | |
| `name` | string | non-null | user label |
| `position_x_m` | float | | mounting position |
| `position_y_m` | float | | |
| `position_z_m` | float | | |
| `load_current_A` | float | ≥0 | actual operating current |
| `rated_current_A` | float | >0 | from device library |
| `loading_factor` | float | 0–1 | `load_current_A / rated_current_A` |
| `operating_mode` | enum | CONTINUOUS / INTERMITTENT / SHORT_TIME | |
| `phase_count` | int | 1, 2, or 3 | |
| `mounting_orientation` | enum | HORIZONTAL / VERTICAL | |
| `data_confidence` | enum | HIGH / MEDIUM / LOW / UNKNOWN | |
| `thermal_model` | enum | QUADRATIC / LINEAR / FIXED_POWER | |
| `power_at_rated_W` | float | >0 | from device library |
| `power_coefficient_a` | float | optional | quadratic: P = a·I² + b·I + c |
| `power_coefficient_b` | float | optional | |
| `power_coefficient_c` | float | optional | |
| `power_uncertainty_min_W` | float | optional | for sensitivity scenario |
| `power_uncertainty_max_W` | float | optional | for sensitivity scenario |
| `thermal_mass_J_K` | float | optional | reserved for future transient capability |

---

### 2.8 BusbarRun

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `enclosure_id` | UUID | FK Enclosure | |
| `name` | string | non-null | e.g. "Main Busbar L1" |
| `phase_label` | string | optional | "L1", "L2", "L3", "N", "PE" |
| `current_A` | float | ≥0 | |
| `material_id` | UUID | FK MaterialLibrary | copper or aluminium |
| `cross_section_m2` | float | >0 | width_m × thickness_m |
| `width_m` | float | >0 | bar width |
| `thickness_m` | float | >0 | bar thickness |
| `emissivity` | float | 0–1 | surface emissivity; user must confirm if not bare copper |

---

### 2.9 BusbarSegment

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `busbar_run_id` | UUID | FK BusbarRun | |
| `start_x_m` | float | | |
| `start_y_m` | float | | |
| `start_z_m` | float | | |
| `end_x_m` | float | | |
| `end_y_m` | float | | |
| `end_z_m` | float | | |
| `length_m` | float | >0 | computed |
| `resistance_ref_ohm` | float | >0 | R_DC at T_ref |
| `temp_coefficient_1_K` | float | | α (default: Cu=0.00393, Al=0.00403) |
| `temp_ref_C` | float | default 20 | |
| `k_ac_factor` | float | optional, ≥1 | Level 2 AC correction. Null = DC only with warning |
| `k_ac_source` | enum | MANUFACTURER / VALIDATED_CORRELATION / GEOMETRY_FREQUENCY_LIBRARY / USER_INPUT / NOT_APPLIED | Required when k_ac_factor is set |
| `thermal_mass_J_K` | float | optional | reserved for future transient capability |

---

### 2.10 BusbarJoint

**Changes from revision 0:** `health_state` and `health_state_modifier` replaced by
`joint_condition` and `contact_resistance_source` per DR-004. Universal 10 µΩ default removed.

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `busbar_run_id` | UUID | FK BusbarRun | |
| `segment_a_id` | UUID | FK BusbarSegment | upstream segment |
| `segment_b_id` | UUID | FK BusbarSegment, optional | downstream segment (null = terminal joint) |
| `position_x_m` | float | | |
| `position_y_m` | float | | |
| `position_z_m` | float | | |
| `joint_condition` | enum | NEW_VALIDATED / NEW_ASSUMED / MEASURED / AGED / DEGRADED / UNKNOWN | |
| `contact_resistance_ref_ohm` | float | >0, required when source is not UNKNOWN | Contact resistance at T_ref [Ω]. **No default; must be supplied.** |
| `contact_resistance_source` | enum | MEASURED / MANUFACTURER / JOINT_LIBRARY / USER_ASSUMPTION | |
| `sensitivity_min_ohm` | float | optional | Lower bound for sensitivity scenario [Ω] |
| `sensitivity_nominal_ohm` | float | optional | Nominal for sensitivity scenario [Ω] |
| `sensitivity_max_ohm` | float | optional | Upper bound for sensitivity scenario [Ω] |
| `temp_coefficient_contact_1_K` | float | | α_contact for contact resistance |
| `temp_ref_C` | float | default 20 | |
| `assembly_torque_Nm` | float | optional | measured at assembly |
| `torque_specification_Nm` | float | optional | from manufacturer |
| `torque_compliance` | enum | COMPLIANT / NON_COMPLIANT / NOT_CHECKED | |
| `data_confidence` | enum | HIGH / MEDIUM / LOW / UNKNOWN | |
| `thermal_mass_J_K` | float | optional | reserved for future transient capability |

**Validation rules:**
- When `joint_condition = UNKNOWN`: `sensitivity_min_ohm`, `sensitivity_nominal_ohm`, and
  `sensitivity_max_ohm` are required; `contact_resistance_ref_ohm` is null.
- When `joint_condition ≠ UNKNOWN`: `contact_resistance_ref_ohm` is required and
  `contact_resistance_source` must be set.
- When `contact_resistance_source = USER_ASSUMPTION`: the result carries a `DATA_ASSUMPTION`
  flag; report wording must state the assumed value.

---

### 2.11 Conductor

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `enclosure_id` | UUID | FK Enclosure | |
| `name` | string | optional | |
| `conductor_library_id` | UUID | FK ConductorLibrary | |
| `length_m` | float | >0 | |
| `current_A` | float | ≥0 | |
| `bundling_factor` | float | 0–1, default 1.0 | derating for bundled cables |
| `thermal_mass_J_K` | float | optional | reserved for future transient capability |

---

### 2.12 Fan

**Changes from revision 0:** `operating: bool` replaced by `operating_state: enum` (DR-005).

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `enclosure_id` | UUID | FK Enclosure | |
| `ventilation_device_library_id` | UUID | FK VentilationDeviceLibrary | |
| `position_x_m` | float | | |
| `position_y_m` | float | | |
| `position_z_m` | float | | |
| `orientation` | enum | INLET / OUTLET | |
| `mounting_surface` | enum | FRONT / REAR / LEFT / RIGHT / TOP / BOTTOM | |
| `operating_state` | enum | FORWARD_OPERATING / STOPPED_FREE_FLOW / STOPPED_WITH_DAMPER / FAILED_OPEN / FAILED_BLOCKED / ESTIMATED_REVERSE_FLOW | Default: FORWARD_OPERATING |
| `fan_loss_coefficient_K` | float | optional | K for fan duct resistance in non-operating states |

---

### 2.13 ExternalOpening

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `enclosure_id` | UUID | FK Enclosure | |
| `opening_type` | enum | LOUVRE / GLAND_PLATE / VENTILATION_SLOT / CABLE_ENTRY / OTHER | |
| `position_x_m` | float | | |
| `position_y_m` | float | | |
| `position_z_m` | float | | |
| `mounting_surface` | enum | same as Fan | |
| `gross_area_m2` | float | >0 | total face area (see M0-10 §4.1) |
| `open_area_fraction` | float | 0–1 | net free area = gross × fraction |
| `discharge_coefficient` | float | 0–1, default 0.6 | Cd; effective area = Cd × net free area |
| `filter_id` | UUID | FK Filter, optional | |
| `filter_pressure_drop_Pa` | float | optional | at nominal flow; fixed value |

---

### 2.14 ThermalCell (generated — not user-created)

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK | |
| `compartment_id` | UUID | FK Compartment | |
| `centre_x_m` | float | | |
| `centre_y_m` | float | | |
| `centre_z_m` | float | | |
| `volume_m3` | float | >0 | |
| `temperature_K` | float | computed | filled by solver |

---

## 3. Library Entities

### 3.1 LibraryRelease (new in revision 1)

Every library type uses this versioning structure (see M0-09 for full specification).

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `library_name` | string | e.g. "MaterialLibrary" |
| `semantic_version` | string | e.g. "1.2.0" |
| `revision_id` | UUID | immutable identifier |
| `content_hash_sha256` | string | 64 hex chars; computed over canonical entry set |
| `status` | enum | DRAFT / APPROVED / SUPERSEDED / WITHDRAWN |
| `effective_date` | date | |
| `source_reference` | string | |
| `creator` | string | email |
| `approver` | string | email |
| `approval_date` | date | |
| `supersedes_version` | string | optional |
| `change_summary` | string | |
| `entry_count` | int | |

---

### 3.2 MaterialLibrary

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `library_release_id` | UUID | FK LibraryRelease |
| `name` | string | e.g. "Mild Steel", "Copper", "Aluminium 1050" |
| `density_kg_m3` | float | |
| `thermal_conductivity_W_mK` | float | |
| `specific_heat_J_kgK` | float | |
| `electrical_resistivity_ohm_m` | float | optional; for conductors |
| `temp_coefficient_1_K` | float | optional |
| `temp_ref_C` | float | default 20 |
| `emissivity` | float | 0–1 |
| `source` | string | manufacturer / standard / measured |

---

### 3.3 DeviceLibrary

**Changes from revision 0:** Automatic +20% loss margin removed. Uncertainty fields added (DR-009).

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `library_release_id` | UUID | FK LibraryRelease |
| `manufacturer` | string | |
| `model_reference` | string | |
| `device_type` | enum | MCB / MCCB / ACB / CONTACTOR / RELAY / METER / TRANSFORMER / VSD / OTHER |
| `rated_current_A` | float | |
| `rated_voltage_V` | float | |
| `power_loss_at_rated_W` | float | Source value — **never silently modified by solver** |
| `power_loss_min_W` | float | optional; for sensitivity scenario |
| `power_loss_max_W` | float | optional; for sensitivity scenario |
| `thermal_model` | enum | QUADRATIC / LINEAR / FIXED_POWER |
| `power_coefficient_a` | float | optional |
| `power_coefficient_b` | float | optional |
| `power_coefficient_c` | float | optional |
| `max_operating_temp_C` | float | |
| `derating_table` | JSON | array of {current_A, max_ambient_C, derating_factor} |
| `width_m` | float | |
| `height_m` | float | |
| `depth_m` | float | |
| `data_confidence` | enum | HIGH / MEDIUM / LOW / UNKNOWN |
| `source_document` | string | manufacturer datasheet / IEC 60947 / measured |

---

### 3.4 ConductorLibrary

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `library_release_id` | UUID | FK LibraryRelease |
| `name` | string | |
| `cross_section_mm2` | float | stored in mm² for display; converted to m² at input boundary |
| `material` | enum | COPPER / ALUMINIUM |
| `insulation_type` | string | e.g. "PVC", "XLPE" |
| `resistance_per_m_ohm` | float | at 20 °C |
| `current_capacity_A` | float | in free air at 30 °C |
| `max_operating_temp_C` | float | |

---

### 3.5 VentilationDeviceLibrary

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `library_release_id` | UUID | FK LibraryRelease |
| `manufacturer` | string | |
| `model_reference` | string | |
| `fan_curve` | JSON | array of {static_pressure_Pa, flow_rate_m3s}; points in m³/s and Pa |
| `rated_flow_rate_m3s` | float | at zero static pressure |
| `rated_static_pressure_Pa` | float | at zero flow |
| `fan_curve_validated_min_flow_m3s` | float | lower validated extrapolation bound |
| `fan_curve_validated_max_flow_m3s` | float | upper validated extrapolation bound |
| `loss_coefficient_stopped_K` | float | duct loss coefficient when fan stopped (STOPPED_FREE_FLOW) |
| `power_W` | float | electrical power consumption |
| `noise_dBA` | float | optional |

---

### 3.6 BusbarJointLibrary

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `library_release_id` | UUID | FK LibraryRelease |
| `description` | string | e.g. "M10 bolt, Cu bar, clean, 40 Nm" |
| `joint_type` | string | BOLTED / BUSWAY / CRIMPED |
| `contact_material` | string | |
| `contact_resistance_ref_ohm` | float | at 20 °C, validated condition |
| `temp_coefficient_contact_1_K` | float | |
| `torque_specification_Nm` | float | |
| `data_source` | string | |
| `data_confidence` | enum | HIGH / MEDIUM / LOW |

---

### 3.7 ACResistanceLibrary

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `library_release_id` | UUID | FK LibraryRelease |
| `description` | string | e.g. "Cu bar 60×10mm at 50Hz" |
| `busbar_width_m` | float | |
| `busbar_thickness_m` | float | |
| `busbar_material` | enum | COPPER / ALUMINIUM |
| `frequency_Hz` | float | 50 or 60 |
| `phase_count` | int | 1, 2, or 3 |
| `phase_spacing_m` | float | |
| `k_ac_factor` | float | ≥1 |
| `source` | string | MANUFACTURER / VALIDATED_CORRELATION / PHYSICAL_TEST |
| `source_document` | string | |
| `data_confidence` | enum | HIGH / MEDIUM / LOW |

---

## 4. Calculation Artefacts

### 4.1 CalculationRun

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `project_id` | UUID | FK Project |
| `enclosure_id` | UUID | FK Enclosure |
| `mode` | enum | MODE_1 / MODE_2 / MODE_3 / MODE_4 |
| `status` | enum | PENDING / RUNNING / CONVERGED / NON_CONVERGED / FAILED / CANCELLED |
| `schema_version` | string | e.g. "1.0" |
| `input_snapshot` | JSONB | versioned InputSnapshot (stored in PostgreSQL) |
| `result_snapshot` | JSONB | versioned ResultSnapshot summary (stored in PostgreSQL) |
| `convergence_trace` | JSONB | iteration history (stored in PostgreSQL) |
| `library_manifest` | JSONB | pinned library names, versions, and hashes |
| `input_hash_sha256` | string | SHA-256 of canonical InputSnapshot JSON |
| `result_hash_sha256` | string | SHA-256 of canonical ResultSnapshot JSON |
| `engine_version` | string | thermpro_engine semver |
| `submitted_at` | datetime | |
| `started_at` | datetime | |
| `completed_at` | datetime | |
| `user_id` | UUID | FK User |
| `audit_notes` | string | optional |

**Large artefacts stored in S3/MinIO (object key stored in separate table):**
- PDF report
- XLSX report
- Dense thermal field data (HDF5)
- CFD export/import files

---

## 5. Relationships Summary

```
Project           1 ──── N   Assembly
Assembly          1 ──── N   Enclosure
Enclosure         1 ──── N   Surface
Enclosure         1 ──── N   Compartment
Enclosure         1 ──── N   Device
Enclosure         1 ──── N   BusbarRun
Enclosure         1 ──── N   Conductor
Enclosure         1 ──── N   Fan
Enclosure         1 ──── N   ExternalOpening
Enclosure         1 ──── N   Filter
Enclosure         1 ──── N   Duct
Enclosure         1 ──── N   TemperatureProbe
Enclosure         1 ──── N   AirflowProbe
Compartment       1 ──── N   Partition
Compartment       1 ──── N   InternalOpening
Compartment       1 ──── N   ThermalCell
BusbarRun         1 ──── N   BusbarSegment
BusbarRun         1 ──── N   BusbarJoint
BusbarJoint       N ──── 1   BusbarSegment  (segment_a)
BusbarJoint       N ──── 1   BusbarSegment  (segment_b, optional)
Device            N ──── 1   DeviceLibrary
BusbarSegment     N ──── 1   MaterialLibrary
Enclosure         N ──── 1   MaterialLibrary
Conductor         N ──── 1   ConductorLibrary
Fan               N ──── 1   VentilationDeviceLibrary
Project           1 ──── N   CalculationRun
LibraryRelease    1 ──── N   MaterialLibrary (entries)
LibraryRelease    1 ──── N   DeviceLibrary (entries)
LibraryRelease    1 ──── N   ConductorLibrary (entries)
LibraryRelease    1 ──── N   VentilationDeviceLibrary (entries)
LibraryRelease    1 ──── N   BusbarJointLibrary (entries)
LibraryRelease    1 ──── N   ACResistanceLibrary (entries)
```

---

## 6. Enumeration Reference

| Enum Name | Values |
|-----------|--------|
| StandardProfile (MVP) | IEC_61439_1, IEC_61439_2, IEC_TR_60890, MANUFACTURER_LIMITS, PROJECT_DEFINED |
| StandardProfile (future, not in MVP) | UL_891, UL_1558, ANSI_IEEE_C37_20_1, IEEE_1584_2018 |
| InstallationType | FREE_STANDING, WALL_MOUNTED, FLOOR_MOUNTED, FLUSH_MOUNTED, CEILING_MOUNTED |
| FormType | 1, 2, 3, 4 |
| SurfaceType | WALL, DOOR, PANEL, PLINTH, ROOF, FLOOR |
| Orientation | VERTICAL, HORIZONTAL_UP, HORIZONTAL_DOWN |
| DeviceType | MCB, MCCB, ACB, CONTACTOR, RELAY, METER, TRANSFORMER, VSD, OTHER |
| ThermalModel | QUADRATIC, LINEAR, FIXED_POWER |
| DataConfidence | HIGH, MEDIUM, LOW, UNKNOWN |
| JointCondition | NEW_VALIDATED, NEW_ASSUMED, MEASURED, AGED, DEGRADED, UNKNOWN |
| ContactResistanceSource | MEASURED, MANUFACTURER, JOINT_LIBRARY, USER_ASSUMPTION |
| TorqueCompliance | COMPLIANT, NON_COMPLIANT, NOT_CHECKED |
| CalculationMode (MVP) | MODE_1, MODE_2, MODE_3, MODE_4 |
| RunStatus | PENDING, RUNNING, CONVERGED, NON_CONVERGED, FAILED, CANCELLED |
| MountingSurface | FRONT, REAR, LEFT, RIGHT, TOP, BOTTOM |
| PollutionDegree | 1, 2, 3, 4 |
| OperatingMode | CONTINUOUS, INTERMITTENT, SHORT_TIME |
| FanOperatingState | FORWARD_OPERATING, STOPPED_FREE_FLOW, STOPPED_WITH_DAMPER, FAILED_OPEN, FAILED_BLOCKED, ESTIMATED_REVERSE_FLOW |
| KAcSource | MANUFACTURER, VALIDATED_CORRELATION, GEOMETRY_FREQUENCY_LIBRARY, USER_INPUT, NOT_APPLIED |
| LibraryStatus | DRAFT, APPROVED, SUPERSEDED, WITHDRAWN |
