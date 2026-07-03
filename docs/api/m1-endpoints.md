# M1 API Endpoints

**Document ID:** THERM-API-M1-001  
**Revision:** M1r1  
**Base URL:** `/api/v1`

---

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe — 200 if process running |
| GET | `/ready` | Readiness probe — returns check results |

### GET /health

```json
{
  "status": "ok",
  "version": "0.1.0",
  "service": "ThermPro API"
}
```

### GET /ready

```json
{
  "status": "ready",
  "checks": {
    "engine": "not_implemented_m1",
    "db": "unchecked_m1"
  }
}
```

---

## Projects

| Method | Path | Description |
|--------|------|-------------|
| POST | `/projects` | Create project |
| GET | `/projects` | List projects (paginated) |
| GET | `/projects/{id}` | Get project by ID |

### POST /projects

Request:
```json
{ "name": "MCC-A Analysis", "description": "Optional" }
```

Response `201`:
```json
{
  "id": "uuid",
  "name": "MCC-A Analysis",
  "description": null,
  "owner_id": "uuid",
  "is_archived": false,
  "created_at": "2026-07-03T12:00:00Z"
}
```

---

## Library Releases

| Method | Path | Description |
|--------|------|-------------|
| POST | `/library-releases` | Create DRAFT release |
| GET | `/library-releases` | List releases (paginated) |
| GET | `/library-releases/{id}` | Get release |
| POST | `/library-releases/{id}/approve` | Approve (ADMIN/REVIEWER only) |

Once approved, a release cannot be modified (DR-002). The `content_hash_sha256` is computed
from canonical JSON of all entries at creation time.

---

## Dataset Manifests

| Method | Path | Description |
|--------|------|-------------|
| POST | `/dataset-manifests` | Create manifest (pin libraries) |
| GET | `/dataset-manifests/{id}` | Get manifest |

A manifest pins one or more library releases by `name + version + content_hash_sha256`.
All pins are verified at creation time — any unknown hash rejects the manifest.

---

## Calculation Runs

| Method | Path | Description |
|--------|------|-------------|
| POST | `/calculation-runs` | Submit calculation |
| GET | `/calculation-runs` | List runs (paginated) |
| GET | `/calculation-runs/{id}` | Get run |

### POST /calculation-runs

Request:
```json
{
  "project_id": "uuid",
  "input_snapshot": { ... }  // M0-03 schema
}
```

M1 Response `201` — **no thermal result computed**:
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "mode": "MODE_2",
  "schema_version": "1.0.0",
  "status": "ENGINE_NOT_IMPLEMENTED",
  "input_checksum_sha256": "sha256hex",
  "rejection_reason": null,
  "submitted_at": "2026-07-03T12:00:00Z",
  "completed_at": null
}
```

---

## Artifacts

| Method | Path | Description |
|--------|------|-------------|
| POST | `/calculation-runs/{id}/artifacts` | Upload artifact (multipart) |
| GET | `/artifacts/{id}` | Get artifact metadata |
| GET | `/artifacts/{id}/download` | Presigned download URL |

---

## Error Shape (M0-02)

All error responses follow:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": [{ "field": "field_path", "issue": "description" }]
  }
}
```

HTTP status → error code mapping:
- `400` → `BAD_REQUEST`
- `404` → `NOT_FOUND`
- `409` → `CONFLICT` (immutability violation)
- `422` → `VALIDATION_ERROR` (schema or manifest errors)
- `500` → `INTERNAL_ERROR`
