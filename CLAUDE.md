# ThermPro — LV Switchboard Thermal Digital Twin
## CLAUDE.md — Development Guidance for AI Assistants

---

## Project Overview

ThermPro is an engineering software platform for thermal analysis of low-voltage (LV)
switchboards and motor-control centres. It implements the CT145 (Schneider Cahier
Technique No. 145) methodology and IEC TR 60890:2022 empirical method, supporting
IEC 61439-1/-2 compliance.

North American standards (UL 891/1558, ANSI/IEEE C37.20.1) and the IEEE 1584-2018
arc-flash module are **deferred to future releases** and are not in MVP scope.

**Current phase:** Milestone 0 conditionally approved. Correction commit applied.
Milestone 1 may begin after the correction commit is reviewed and confirmed complete.

---

## Repository Layout

```
ThermPro/
├── CLAUDE.md                         ← this file
├── README.md
├── docs/
│   ├── engineering/                  ← M0 deliverables
│   │   ├── M0-01-domain-model.md
│   │   ├── M0-02-api-contract.md
│   │   ├── M0-03-calculation-input-schema.json
│   │   ├── M0-04-calculation-result-schema.json
│   │   ├── M0-05-test-validation-matrix.md
│   │   ├── M0-06-engineering-assumptions.md
│   │   ├── M0-07-open-questions.md
│   │   ├── M0-08-decision-record.md    ← engineering review decisions
│   │   ├── M0-09-dataset-versioning.md ← library versioning policy
│   │   └── M0-10-units-policy.md       ← units and dimensional analysis policy
│   ├── reference/
│   │   └── index.md                  ← index to the 12 baseline documents
│   ├── 01-requirements.md
│   ├── 02-engineering-methodology.md
│   ├── 03-standards-and-applicability.md
│   ├── 04-thermal-network-model.md
│   ├── 05-airflow-network-model.md
│   ├── 06-equations-and-correlations.md
│   ├── 07-data-model.md
│   ├── 08-system-architecture.md
│   ├── 09-UI-workflow.md
│   ├── 10-validation-plan.md
│   ├── 11-risk-register.md
│   └── 12-milestone-plan.md
├── thermpro_engine/                  ← [M1+] Python numerical engine (isolated)
│   ├── schema/
│   ├── physics/
│   ├── network/
│   ├── modes/
│   ├── rom/
│   ├── validation/
│   ├── postprocess/
│   └── solver.py
├── backend/                          ← [M1+] FastAPI application
│   ├── api/
│   ├── models/
│   ├── services/
│   ├── tasks/
│   └── main.py
├── frontend/                         ← [M1+] React 18 + TypeScript 5 SPA
│   ├── src/
│   └── vite.config.ts
├── tests/                            ← [M1+] pytest test suite
│   ├── unit/
│   ├── benchmarks/
│   └── integration/
├── infra/                            ← Docker Compose, CI configs
│   ├── docker-compose.yml
│   └── .github/workflows/
└── scripts/                          ← Utility scripts (migrations, imports)
```

---

## Non-Negotiable Engineering Rules

These rules apply to every commit. Any AI assistant or developer MUST enforce them:

| ID | Rule |
|----|------|
| CR-ENG-001 | No production code before engineering approval of all M0 documents. |
| CR-ENG-002 | IEC TR 60890 coefficient tables NEVER shipped in repository. Admin imports licensed dataset via empty JSON template. |
| CR-ENG-003 | Radiation calculations MUST use absolute temperature in kelvin (K), never °C. Unit test UT-UNITS-003 and UT-UNITS-004 enforce this. |
| CR-ENG-004 | Busbar resistance evaluated at calculated conductor temperature (DC base). K_AC correction applied per M0-08 DR-003. |
| CR-ENG-005 | Unconverged results → `status: NON_CONVERGED`; UI shows "RESULT INVALID" watermark. |
| CR-ENG-006 | Forced ventilation active → IEC TR 60890 MODE 1 automatically disabled; no user override. |
| CR-ENG-007 | **WITHDRAWN — arc flash removed from MVP scope (DR-012 / DR-008).** |
| CR-ENG-008 | Joint losses NEVER subsumed into bulk busbar resistivity. BusbarJoint is always a separate entity. |
| CR-ENG-009 | Compliance interpretation is standard-profile-aware. Each profile defines its own applicability, inputs, limits, datasets, and report wording (DR-007). |
| CR-ENG-010 | Contact resistance must follow the data hierarchy in DR-004. Universal default values are forbidden. Unknown contacts require sensitivity scenarios. |
| CR-ENG-011 | K_AC = 1.0 (DC-only) must trigger a visible engineering warning when AC effects are potentially significant for the busbar geometry and frequency. |
| CR-ENG-012 | Library data is immutable once APPROVED. Any change creates a new release with a new semantic version and SHA-256 hash (DR-002 / M0-09). |
| CR-ENG-013 | All internal computation uses SI base units without exception (M0-10). Unit conversion occurs only at input/output boundaries. |
| CR-TECH-001 | `thermpro_engine` accepts versioned JSON input → returns versioned JSON result. It has NO direct dependency on FastAPI, SQLAlchemy, or any HTTP framework. |
| CR-TECH-002 | `schema_version` and `library_manifest` fields are required on every InputSnapshot. |
| CR-TECH-003 | De Vahl Davis cavity benchmark (BM-007) is a **periodic physics verification** test, not a mandatory every-push CI gate. See DR-010 and M0-05 for CI gate assignments. |

---

## MVP Standards Scope

| Standard | MVP | Future |
|----------|-----|--------|
| IEC 61439-1 | ✓ | |
| IEC 61439-2 | ✓ | |
| IEC TR 60890:2022 | ✓ | |
| Manufacturer limits (DeviceLibrary) | ✓ | |
| Project-defined limits | ✓ | |
| UL 891 | | Phase 3+ |
| UL 1558 | | Phase 3+ |
| ANSI/IEEE C37.20.1 | | Phase 3+ |
| IEEE 1584-2018 (arc flash) | | Separate future module |

---

## Calculation Modes Summary

| Mode | Method | Ventilation | MVP |
|------|--------|-------------|-----|
| MODE 1 | IEC TR 60890 empirical | Natural only | ✓ |
| MODE 2 | Nodal thermal network (CT145) | Natural | ✓ |
| MODE 3 | Forced-ventilation airflow network | Forced | ✓ |
| MODE 4 | CFD Export/Import Adapter | Any | ✓ |
| ARC-FLASH | IEEE 1584-2018 screening | — | Removed — future separate module |

---

## Branch Convention

- **Development branch:** `claude/lv-switchboard-thermal-twin-66cjd8`
- **Main branch:** `main` (protected; requires PR)
- All PRs must reference a milestone number (e.g. `[M1]`) in the title.

---

## Development Commands (after M1 scaffolding)

```bash
# Install engine in editable mode
pip install -e ".[dev]"

# Run all unit tests
pytest tests/unit/ -v

# Run every-push benchmark gates
pytest tests/benchmarks/ -m "not periodic_physics" -v

# Run periodic physics verification (pre-release only)
pytest tests/benchmarks/ -m periodic_physics -v

# Run unit conversion tests
pytest tests/unit/test_unit_conversions.py -v

# Type checking
mypy thermpro_engine --strict

# Format
black thermpro_engine backend tests
isort thermpro_engine backend tests

# Start dev stack
docker compose up -d
```

---

## Key Documents

| Document | ID | Rev | Notes |
|----------|----|-----|-------|
| Requirements | THERM-REQ-001 | 0.2 | |
| Engineering Methodology | THERM-METH-001 | 0.2 | |
| Standards & Applicability | THERM-STD-001 | 0.2 | Needs update for deferred standards |
| Thermal Network Model | THERM-NET-001 | 0.1 | |
| Airflow Network Model | THERM-AFN-001 | 0.1 | |
| Equations & Correlations | THERM-EQN-001 | 0.2 | |
| Data Model | THERM-DAT-001 | 0.2 | |
| System Architecture | THERM-ARCH-001 | 0.2 | |
| UI Workflow | THERM-UI-001 | 0.1 | |
| Validation Plan | THERM-VAL-001 | 0.2 | |
| Risk Register | THERM-RISK-001 | 0.2 | |
| Milestone Plan | THERM-MILE-001 | 0.1 | |
| Domain Model | M0-01 | M0r1 | |
| API Contract | M0-02 | M0r1 | |
| Input Schema | M0-03 | M0r1 | |
| Result Schema | M0-04 | M0r1 | |
| Test/Validation Matrix | M0-05 | M0r1 | |
| Engineering Assumptions | M0-06 | M0r1 | |
| Open Questions | M0-07 | M0r1 | |
| Decision Record | M0-08 | M0r1 | DR-001 through DR-012 |
| Dataset Versioning | M0-09 | M0r1 | |
| Units Policy | M0-10 | M0r1 | |

---

## Milestone Gates

| Milestone | Gate | Status |
|-----------|------|--------|
| M0 | Engineering approval of all baseline docs + M0 deliverables + correction commit | **CONDITIONALLY APPROVED** |
| M1 | M0 correction commit confirmed complete + CI green + mypy clean | **Ready to start** |
| M2–M14 | Per THERM-MILE-001 exit criteria | Blocked on M1 |
