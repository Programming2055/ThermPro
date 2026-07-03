# Storage Model

**Document ID:** THERM-ARCH-M1-003  
**Revision:** M1r1

---

## Hybrid Storage Strategy

ThermPro uses two storage backends that serve different roles:

| Backend | What is stored | Why |
|---------|---------------|-----|
| PostgreSQL | Metadata, status, relationships, JSONB snapshots ≤ 1 MB | Transactional integrity, FK constraints, indexed queries |
| S3 / MinIO | Binary artifacts, large JSON files, library entry sets | Cost-efficient blob storage; avoids JSONB size limits |

### Rule: JSONB vs S3

- `input_snapshot` (calculation input) → stored as JSONB in `calculation_runs.input_snapshot`.
  Rationale: snapshots must be queryable and atomic with the run record.
- Library entry datasets → stored in S3 as `library_release_files`. A `LibraryReleaseFile`
  row holds the S3 key and SHA-256; the actual JSON stays out of the database (CR-ENG-002 adjacent).
- Report PDFs, CFD packages, large convergence traces → always S3 via `calculation_artifacts`.

---

## ObjectStorage Interface

```python
class ObjectStorage(Protocol):
    async def put_object(self, key: str, data: bytes, content_type: str) -> None: ...
    async def get_object(self, key: str) -> bytes: ...
    async def presigned_url(self, key: str, expires_in: int = 3600) -> str: ...
    async def delete_object(self, key: str) -> None: ...
```

`MinIOStorage` implements this using `boto3` with `endpoint_url` pointed at MinIO for development
and AWS S3 for production. No other code has a direct dependency on `boto3`.

---

## S3 Key Conventions

```
artifacts/{run_id}/{artifact_type}/{filename}
library-entries/{release_id}/{filename}
```

Keys are immutable once written — they are never overwritten. Deletion only occurs when
a library release is hard-deleted (admin operation, not exposed in M1 API).

---

## Development (MinIO)

```
THERMPRO_S3_ENDPOINT_URL=http://localhost:9000
THERMPRO_S3_ACCESS_KEY_ID=minioadmin
THERMPRO_S3_SECRET_ACCESS_KEY=minioadmin
THERMPRO_S3_BUCKET_ARTIFACTS=thermpro-artifacts
```

The `minio-init` container in `docker-compose.yml` creates the bucket on first start.

---

## Production Notes

- Replace `endpoint_url` with AWS region endpoint (or remove it entirely for AWS).
- Use IAM roles instead of static credentials.
- Enable S3 versioning on the artifacts bucket for additional protection.
- Consider S3 Object Lock (WORM) for approved library release files.
