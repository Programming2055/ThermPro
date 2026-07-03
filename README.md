# ThermPro — LV Switchboard Thermal Digital Twin

ThermPro is an engineering-grade platform for thermal analysis of low-voltage (LV)
electrical switchboards. It enables engineers to define enclosure geometry, place heat
sources and ventilation devices, compute internal air temperatures, identify hot spots,
and produce auditable calculation reports.

## Status

**Pre-implementation — Engineering Design Phase.**

All twelve engineering and architecture documents in `docs/` must be reviewed and
approved by a qualified engineer before any production code is written.

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
| MODE 4 | CFD Export/Import Adapter | Future OpenFOAM or equivalent integration |

## Technology Stack (Planned)

- **Frontend:** React 18 · TypeScript · Vite · Zustand · Konva.js · Three.js · ECharts
- **Backend:** Python 3.12 · FastAPI · Pydantic · NumPy · SciPy · SQLAlchemy · PostgreSQL
- **Queue:** Celery · Redis
- **Reports:** WeasyPrint (PDF) · openpyxl (XLSX)

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
