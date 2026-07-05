# Development Setup

**Document ID:** THERM-DEV-M1-001

---

## Prerequisites

- Python 3.12
- Node.js 20
- Docker + Docker Compose
- `git`

---

## Quick Start (Docker)

```bash
# Start the full stack
docker compose up -d

# View logs
docker compose logs -f api

# API: http://localhost:8000/api/docs
# Web: http://localhost:5173
# MinIO console: http://localhost:9001 (minioadmin / minioadmin)
```

---

## Local Development (Without Docker)

### 1. Start infrastructure only

```bash
docker compose up -d postgres minio minio-init
```

### 2. Python backend

```bash
# Install packages
pip install -e packages/units
pip install -e packages/schemas
pip install -e engine
pip install -e "apps/api[dev]"

# Run migrations
cd apps/api
alembic upgrade head

# Start API
uvicorn thermpro_api.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd apps/web
npm install
npm run dev
# → http://localhost:5173
```

---

## Running Tests

```bash
# All Python unit tests (no DB required)
pytest packages/units/tests packages/schemas/tests engine/tests apps/api/tests/unit -v

# Unit conversion tests (UT-UNITS-001 through UT-UNITS-010)
pytest packages/units/tests -v

# Integration tests (requires running PostgreSQL)
THERMPRO_DATABASE_URL=postgresql+psycopg://thermpro:thermpro@localhost:5432/thermpro \
  pytest apps/api/tests/integration -v

# Every-push benchmark gates (excludes periodic physics BM-007)
pytest engine/tests -m "not periodic_physics" -v

# Frontend tests
cd apps/web
npm run test        # watch mode
npm run test -- --run  # single run

# Type checking
mypy packages/units/src --strict
mypy engine/thermal_core --strict
mypy apps/api/src --strict
cd apps/web && npm run typecheck
```

---

## Environment Variables

Copy `.env.example` to `.env` to customise. The defaults work with `docker-compose.yml`.

| Variable | Default | Description |
|----------|---------|-------------|
| `THERMPRO_DATABASE_URL` | `postgresql+psycopg://thermpro:thermpro@localhost:5432/thermpro` | PostgreSQL DSN |
| `THERMPRO_S3_ENDPOINT_URL` | `http://localhost:9000` | MinIO endpoint |
| `THERMPRO_S3_ACCESS_KEY_ID` | `minioadmin` | MinIO access key |
| `THERMPRO_S3_SECRET_ACCESS_KEY` | `minioadmin` | MinIO secret |
| `THERMPRO_S3_BUCKET_ARTIFACTS` | `thermpro-artifacts` | Artifacts bucket |
| `THERMPRO_DEV_AUTH_ENABLED` | `true` | Use DevAuthProvider (no JWT needed) |
| `THERMPRO_DEBUG` | `false` | Enable debug logging |
| `THERMPRO_LOG_LEVEL` | `INFO` | Log level |

---

## Alembic Migrations

```bash
cd apps/api

# Apply all migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Roll back all (for a clean test DB)
alembic downgrade base

# Generate a new migration (after model changes)
alembic revision --autogenerate -m "description_of_change"
```
