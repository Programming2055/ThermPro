# M2 Geometry API Endpoints

**Document ID:** THERM-GEO-002  
**Date:** 2026-07-05  
**Base URL:** `/api/v1`  
**Auth:** `DevAuthProvider` (X-Dev-User header or auto-admin in dev mode)

---

## Assembly

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{project_id}/assemblies` | Create assembly |
| GET | `/projects/{project_id}/assemblies` | List assemblies for project |

### POST /projects/{project_id}/assemblies

**Request:**
```json
{
  "name": "Panel Assembly A",
  "description": "Main distribution board"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "name": "Panel Assembly A",
  "description": "Main distribution board",
  "coordinate_system_version": "1.0",
  "revision": 1,
  "created_at": "2026-07-05T10:00:00Z"
}
```

---

## Enclosure

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects/{project_id}/enclosures` | Create enclosure |
| GET | `/projects/{project_id}/enclosures` | List enclosures for project |
| GET | `/enclosures/{enclosure_id}` | Get enclosure by ID |
| DELETE | `/enclosures/{enclosure_id}` | Delete enclosure (cascades) |

### POST /projects/{project_id}/enclosures

All dimension fields are in **metres**.

**Request:**
```json
{
  "name": "MCC Panel A",
  "external_width_m": 0.6,
  "external_height_m": 2.0,
  "external_depth_m": 0.4,
  "internal_width_m": 0.556,
  "internal_height_m": 1.95,
  "internal_depth_m": 0.356,
  "wall_thickness_m": 0.002,
  "installation_type": "FLOOR_STANDING",
  "ip_rating": "IP54"
}
```

**Response 201:** Full `EnclosureResponse` object.

---

## Surface

| Method | Path | Description |
|--------|------|-------------|
| POST | `/enclosures/{enclosure_id}/surfaces` | Create surface |
| GET | `/enclosures/{enclosure_id}/surfaces` | List surfaces |

**face** values: `FRONT` `REAR` `LEFT` `RIGHT` `TOP` `BOTTOM`

---

## Compartment

| Method | Path | Description |
|--------|------|-------------|
| POST | `/enclosures/{enclosure_id}/compartments` | Create compartment |
| GET | `/enclosures/{enclosure_id}/compartments` | List compartments |
| DELETE | `/compartments/{compartment_id}` | Delete compartment |

**compartment_type** values: `DEVICE_CHAMBER` `BUSBAR_CHAMBER` `CABLE_CHAMBER` `AUXILIARY_CHAMBER` `VENTILATION_CHAMBER` `CUSTOM`

**Request:**
```json
{
  "name": "Device Bay 1",
  "compartment_type": "DEVICE_CHAMBER",
  "position_x_m": 0.0,
  "position_y_m": 0.0,
  "position_z_m": 0.0,
  "width_m": 0.556,
  "height_m": 0.9,
  "depth_m": 0.356
}
```

---

## Partition

| Method | Path | Description |
|--------|------|-------------|
| POST | `/enclosures/{enclosure_id}/partitions` | Create partition |
| GET | `/enclosures/{enclosure_id}/partitions` | List partitions |
| DELETE | `/partitions/{partition_id}` | Delete partition |

**orientation** values: `VERTICAL_XZ` `VERTICAL_YZ` `HORIZONTAL_XY`

---

## ExternalOpening

| Method | Path | Description |
|--------|------|-------------|
| POST | `/enclosures/{enclosure_id}/external-openings` | Create external opening |
| GET | `/enclosures/{enclosure_id}/external-openings` | List external openings |

**direction** values: `INLET` `OUTLET` `BIDIRECTIONAL` `UNKNOWN`

**Request:**
```json
{
  "surface_id": "uuid",
  "name": "Bottom inlet louvre",
  "position_x_m": 0.1,
  "position_y_m": 0.05,
  "width_m": 0.3,
  "height_m": 0.08,
  "open_area_fraction": 0.6,
  "discharge_coefficient": 0.61,
  "direction": "INLET",
  "elevation_m": 0.05
}
```

---

## InternalOpening

| Method | Path | Description |
|--------|------|-------------|
| POST | `/partitions/{partition_id}/internal-openings` | Create internal opening |
| GET | `/partitions/{partition_id}/internal-openings` | List internal openings |

---

## DevicePlacement

| Method | Path | Description |
|--------|------|-------------|
| POST | `/enclosures/{enclosure_id}/device-placements` | Create device placement |
| GET | `/enclosures/{enclosure_id}/device-placements` | List device placements |
| DELETE | `/device-placements/{device_id}` | Delete device placement |

---

## BusbarPlacement

| Method | Path | Description |
|--------|------|-------------|
| POST | `/enclosures/{enclosure_id}/busbar-placements` | Create busbar placement |
| GET | `/enclosures/{enclosure_id}/busbar-placements` | List busbar placements |
| DELETE | `/busbar-placements/{busbar_id}` | Delete busbar placement |

---

## Geometry Validation

| Method | Path | Description |
|--------|------|-------------|
| POST | `/enclosures/{enclosure_id}/validate` | Run validation, persist issues |

**Response 200:**
```json
{
  "enclosure_id": "uuid",
  "issue_count": 2,
  "error_count": 1,
  "warning_count": 1,
  "blocker_count": 0,
  "issues": [
    {
      "id": "uuid",
      "enclosure_id": "uuid",
      "issue_id": "GEO-002-...",
      "severity": "ERROR",
      "entity_type": "Compartment",
      "entity_id": "...",
      "message": "Compartment 'Bay 1' extends outside the enclosure internal volume.",
      "coordinate_ref": {"x": 0.9, "y": 0.0, "z": 0.0},
      "suggested_fix": "Reduce dimensions or reposition within internal envelope.",
      "rule_id": "GEO-002",
      "is_resolved": false
    }
  ]
}
```

**Side effects:**
- Deletes existing unresolved `GeometryValidationIssue` rows for this enclosure
- Inserts new issue rows
- Records an `enclosure.validated` audit event

---

## Audit Events

Every write endpoint (POST, DELETE) records an `audit_events` row. Event names follow the pattern `{entity}.{action}`:

| Event | Trigger |
|-------|---------|
| `assembly.created` | POST /assemblies |
| `enclosure.created` | POST /enclosures |
| `enclosure.deleted` | DELETE /enclosures/{id} |
| `enclosure.validated` | POST /enclosures/{id}/validate |
| `surface.created` | POST /surfaces |
| `compartment.created` | POST /compartments |
| `compartment.deleted` | DELETE /compartments/{id} |
| `partition.created` | POST /partitions |
| `partition.deleted` | DELETE /partitions/{id} |
| `external_opening.created` | POST /external-openings |
| `internal_opening.created` | POST /internal-openings |
| `device_placement.created` | POST /device-placements |
| `device_placement.deleted` | DELETE /device-placements/{id} |
| `busbar_placement.created` | POST /busbar-placements |
| `busbar_placement.deleted` | DELETE /busbar-placements/{id} |

---

## Error Responses

All errors follow the M0-02 error shape:

```json
{
  "detail": "Enclosure not found"
}
```

| HTTP Status | Condition |
|-------------|-----------|
| 201 | Entity created |
| 204 | Entity deleted |
| 400 | Validation error (invalid body) |
| 404 | Parent entity not found |
| 422 | Request body schema violation (FastAPI) |
