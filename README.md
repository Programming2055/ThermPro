# ThermPro — LV Switchboard Thermal Digital Twin

ThermPro is an engineering-grade platform for thermal analysis of low-voltage (LV)
electrical switchboards. It enables engineers to define enclosure geometry, place heat
sources and ventilation devices, compute internal air temperatures, identify hot spots,
and produce auditable calculation reports.

## Status

**Milestone 4 — the solver runs end to end.** Submit an M0-03 InputSnapshot,
execute it, and get an M0-04 ResultSnapshot back with temperatures,
IEC 61439 compliance checks, hotspots and derating advice.

Two things deliberately do not work:

- **MODE 1 needs a licensed dataset.** The IEC TR 60890 coefficient tables are
  licensed and are never committed here (CR-ENG-002). A MODE 1 run fails with
  that reason until an administrator imports them through
  `/api/v1/iec60890-datasets`; the empty import template is the only IEC TR
  60890 artefact this repository ships.
- **BM-007 (De Vahl Davis cavity) is outstanding.** The zonal network carries
  one air node per compartment and cannot resolve a cavity boundary layer, so
  the benchmark is skipped with that reason rather than approximated.

## Quick start

```bash
pip install -e packages/units/ -e packages/schemas/ -e engine/ -e "apps/api/[dev]"
```

```python
from thermal_core.contract import solve_json
from thermal_core.reference_model import m003_document

result = solve_json(m003_document("MODE_2"))      # M0-03 in, M0-04 out
print(result["status"], result["compliance"]["overall_compliant"])
```

The engine is a pure function from one versioned JSON document to another
(CR-TECH-001): no database, no HTTP framework, no library lookups. Everything
the physics needs is inlined on the InputSnapshot, resolved at the API
boundary before the engine is called.

See [CLAUDE.md](CLAUDE.md) for the full command set and the milestone status.

## Documents

| # | File | Description |
|---|------|-------------|
| 1 | [docs/01-requirements.md](docs/01-requirements.md) | Functional and non-functional requirements |
| 2 | [docs/02-engineering-methodology.md](docs/02-engineering-methodology.md) | Governing equations, variables, calculation flow |
| 3 | [docs/03-standards-and-applicability.md](docs/03-standards-and-applicability.md) | IEC standards, eligibility, data strategy |
| 4 | [docs/04-thermal-network-model.md](docs/04-thermal-network-model.md) | Nodal thermal network formulation |
| 5 | [docs/05-airflow-network-model.md](docs/05-airflow-network-model.md) | Pressure/airflow network formulation |
| 6 | [docs/06-equations-and-correlations.md](docs/06-equations-and-correlations.md) | All equations with dimensional checks |
| 7 | [docs/07-data-model.md](docs/07-data-model.md) | Entities, schemas, versioning strategy |
| 8 | [docs/08-system-architecture.md](docs/08-system-architecture.md) | Software architecture and technology stack |
| 9 | [docs/09-UI-workflow.md](docs/09-UI-workflow.md) | User interface and 10-step workflow |
| 10 | [docs/10-validation-plan.md](docs/10-validation-plan.md) | Four-level validation and acceptance criteria |
| 11 | [docs/11-risk-register.md](docs/11-risk-register.md) | Engineering and project risks |
| 12 | [docs/12-milestone-plan.md](docs/12-milestone-plan.md) | 14 implementation milestones |

## Calculation Modes

| Mode | Name | Applicable To |
|------|------|--------------|
| MODE 1 | IEC TR 60890 | Eligible natural-ventilation / closed enclosures |
| MODE 2 | Nodal Thermal Network | Position-sensitive distributed analysis |
| MODE 3 | Forced-Ventilation Airflow Network | Fan, grille, duct, filter systems |
| MODE 4 | CFD Export/Import Adapter | Export to an external CFD package and import the field back |

## Technology Stack

- **Frontend:** React 18 · TypeScript 5 · Vite · Zustand · Vitest
- **Backend:** Python 3.12 · FastAPI · Pydantic · SQLAlchemy 2 (async) · Alembic · PostgreSQL
- **Engine:** pure Python, no numerical dependencies. The models are tens of
  nodes, and CR-TECH-001 asks for an engine that depends on nothing, so the
  linear solve is dense Gaussian elimination with partial pivoting rather
  than NumPy.
- **Planned:** Celery · Redis for long studies; WeasyPrint and openpyxl for reports.

## Standards Referenced

- IEC 61439-1:2011+AMD1:2020 — General rules for low-voltage switchgear and controlgear assemblies
- IEC 61439-2:2011+AMD1:2020 — Power switchgear and controlgear assemblies
- IEC TR 60890:2022 — Temperature-rise evaluation method for LV switchgear assemblies

## Non-Negotiable Engineering Rules

1. Never invent thermal data.
2. Never present an unconverged calculation as valid.
3. Never label a forced-ventilation result as IEC TR 60890 compliant.
4. Never confuse average enclosure temperature with local device ambient temperature.
5. All results must be traceable and reproducible.
6. SI units internally; display units are configurable.
7. Require validation against test data before production engineering use.

---

*Reference: Schneider Electric Cahier Technique No. 145 — Thermal Study of LV Electric Switchboards.*
