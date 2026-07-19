# M2 Geometry Model

**Document ID:** THERM-GEO-001  
**Date:** 2026-07-05  
**Branch:** `claude/m2-geometry-enclosure-model`  
**Status:** IMPLEMENTED

---

## 1. Coordinate System

**Version:** `1.0` (stored on every Assembly and Enclosure row)

| Axis | Direction | Quantity |
|------|-----------|----------|
| X | Left → Right | Width |
| Y | Bottom → Top | Height (vertical) |
| Z | Front → Rear | Depth |

**Origin:** lower-left-front corner of the internal envelope of the enclosure.  
All coordinates and dimensions are in **SI metres** internally (CR-ENG-013, M0-10).  
The UI converts to millimetres for display: `mm = m × 1000`.

---

## 2. Entity Hierarchy

```
Project
└── Assembly           (optional grouping of one or more enclosures)
    └── Enclosure      (physical cabinet with external + internal dimensions)
        ├── Surface    (6 faces: FRONT/REAR/LEFT/RIGHT/TOP/BOTTOM)
        │   └── ExternalOpening  (ventilation aperture on a face)
        ├── Compartment          (spatial subdivision, may be nested)
        ├── Partition            (internal dividing plate)
        │   └── InternalOpening  (aperture through a partition)
        ├── DevicePlacement      (switchgear device bounding box)
        ├── BusbarPlacement      (conductor routing box + route_points)
        └── GeometryValidationIssue  (validation findings)
```

---

## 3. Entities

### 3.1 Assembly

Top-level grouping for multi-enclosure switchboard assemblies.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| project_id | UUID FK → projects | CASCADE delete |
| name | VARCHAR(255) | required |
| description | TEXT | optional |
| coordinate_system_version | VARCHAR(16) | default "1.0" |
| revision | INTEGER | default 1 |

### 3.2 Enclosure

Physical switchboard cabinet.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| project_id | UUID FK → projects | CASCADE delete |
| assembly_id | UUID FK → assemblies | nullable, SET NULL |
| name | VARCHAR(255) | required |
| external_width_m | FLOAT | must be > 0 |
| external_height_m | FLOAT | must be > 0 |
| external_depth_m | FLOAT | must be > 0 |
| internal_width_m | FLOAT | must be > 0 |
| internal_height_m | FLOAT | must be > 0 |
| internal_depth_m | FLOAT | must be > 0 |
| wall_thickness_m | FLOAT | default 0.002 m |
| material_ref | VARCHAR(255) | FK to material library (future) |
| installation_type | VARCHAR(32) | FLOOR_STANDING / WALL_MOUNTED / RACK_MOUNTED / FREESTANDING |
| ip_rating | VARCHAR(16) | e.g. "IP54" |
| coordinate_system_version | VARCHAR(16) | default "1.0" |
| revision | INTEGER | default 1 |
| metadata | JSONB | extensible key-value store |

### 3.3 Surface

One of the six external faces of the enclosure.

| Column | Type | Notes |
|--------|------|-------|
| enclosure_id | UUID FK | CASCADE delete |
| face | VARCHAR(16) | FRONT/REAR/LEFT/RIGHT/TOP/BOTTOM |
| is_exposed | BOOLEAN | default true (false = against wall) |
| emissivity_override | FLOAT | for M3+ radiation BCs |
| bc_placeholder | JSONB | placeholder for M3 boundary conditions |

### 3.4 Compartment

Spatial subdivision within the enclosure. Supports parent-child nesting via `parent_compartment_id` (adjacency list).

| Column | Type | Notes |
|--------|------|-------|
| enclosure_id | UUID FK | CASCADE delete |
| parent_compartment_id | UUID FK → compartments | self-referential, SET NULL |
| name | VARCHAR(255) | must be unique within enclosure |
| compartment_type | VARCHAR(32) | DEVICE_CHAMBER/BUSBAR_CHAMBER/CABLE_CHAMBER/AUXILIARY_CHAMBER/VENTILATION_CHAMBER/CUSTOM |
| position_x/y/z_m | FLOAT | origin corner |
| width/height/depth_m | FLOAT | must be > 0 |
| revision | INTEGER | |

### 3.5 Partition

Internal dividing plate. Orientation determines which columns hold span dimensions.

| Orientation | width_m | height_m |
|-------------|---------|----------|
| VERTICAL_YZ | span in Z | span in Y |
| VERTICAL_XZ | span in X | span in Y |
| HORIZONTAL_XY | span in X | span in Z |

### 3.6 ExternalOpening

Ventilation aperture on an enclosure surface (cable entry, louvre, grating).

- `open_area_fraction` ∈ [0, 1] — net open area / gross area
- `discharge_coefficient` ∈ [0, 1] — Cd for orifice flow (default 0.61)
- `direction` — INLET / OUTLET / BIDIRECTIONAL / UNKNOWN
- `elevation_m` — height of opening centre above enclosure floor

### 3.7 InternalOpening

Aperture through a partition connecting two compartments.

- Linked to `compartment_a_id` and `compartment_b_id` (both nullable for staged entry)
- Same `open_area_fraction` / `discharge_coefficient` / `direction` as ExternalOpening

### 3.8 DevicePlacement

Axis-aligned bounding box of a switchgear device within the enclosure.

- Position is the minimum-coordinate corner
- `rotation_deg` records orientation (informational, not used for spatial checks in M2)
- `mounting_surface` indicates which face the device is mounted on
- Clearances (`clearance_x/y/z_m`) define the required keep-out zone around the device

### 3.9 BusbarPlacement

Spatial representation of a conductor run.

- `width_m` × `thickness_m` × `length_m` defines the bounding rectangular prism
- `route_points` JSONB stores waypoints for bent busbars
- `phase_designation` — L1 / L2 / L3 / N / PE / PEN etc.
- `clearance_m` — minimum clearance to other conductors

### 3.10 GeometryValidationIssue

Validation finding recorded against an enclosure.

| Column | Type | Notes |
|--------|------|-------|
| issue_id | VARCHAR(64) | deterministic ID (rule + entity) |
| severity | VARCHAR(16) | INFO/WARNING/ERROR/BLOCKER |
| entity_type | VARCHAR(64) | e.g. "Compartment" |
| entity_id | VARCHAR(64) | UUID or name of offending entity |
| message | TEXT | human-readable description |
| coordinate_ref | JSONB | {x, y, z} location of issue |
| suggested_fix | TEXT | optional remediation hint |
| rule_id | VARCHAR(64) | e.g. "GEO-004" |
| is_resolved | BOOLEAN | set by user after fixing |

---

## 4. Validation Rules

| Rule ID | Severity | Check |
|---------|----------|-------|
| GEO-001 | ERROR | Compartment dimensions all > 0 |
| GEO-002 | ERROR | Compartment fits within enclosure internal envelope |
| GEO-003 | ERROR | Compartment names unique within enclosure |
| GEO-004 | ERROR | Overlapping compartments |
| GEO-005 | WARNING | Partition extends outside enclosure |
| GEO-006 | ERROR | Device dimensions all > 0 |
| GEO-007 | ERROR | Device outside enclosure internal envelope |
| GEO-008 | WARNING | Device outside its assigned compartment |
| GEO-009 | ERROR | Device-device bounding box overlap |
| GEO-010 | ERROR | Busbar dimensions all > 0 |
| GEO-011 | WARNING | Busbar outside enclosure internal envelope |
| GEO-012 | WARNING | Busbar-device bounding box overlap |
| GEO-013 | ERROR | ExternalOpening.open_area_fraction ∉ [0,1] |
| GEO-014 | ERROR | ExternalOpening.discharge_coefficient ∉ [0,1] |
| GEO-015 | ERROR | InternalOpening.open_area_fraction ∉ [0,1] |
| GEO-016 | ERROR | InternalOpening.discharge_coefficient ∉ [0,1] |

---

## 5. Scope Boundary

M2 geometry is **position and dimension data only**. The following are explicitly NOT in M2:

- No thermal resistance / conductance values on surfaces or compartments
- No heat source assignment to devices (M3)
- No airflow network solution (M3)
- No IEC TR 60890 coefficient tables (M3)
- No device derating (M4+)
- No arc flash module (DR-008 — deferred)
