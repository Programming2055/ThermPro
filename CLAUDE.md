# ThermPro — LV Switchboard Thermal Digital Twin
## CLAUDE.md — Development Guidance for AI Assistants

---

## Project Overview

ThermPro is an engineering software platform for thermal analysis of low-voltage (LV)
switchboards and motor-control centres. It implements the CT145 (Schneider Cahier
Technique No. 145) methodology, IEC TR 60890:2022 empirical method, and supports
IEC 61439-1/-2 and North American standards (UL 891/1558, ANSI/IEEE C37.20.1).

**Current phase:** Milestone 0 complete (engineering baseline). No production code
has been written. Do not begin Milestone 1 until the user explicitly approves M0.

---

## Repository Layout

```
ThermPro/
├── CLAUDE.md                         ← this file
├── README.md
├── docs/
│   ├── engineering/                  ← M0 deliverables (schemas, contracts, matrices)
│   │   ├── M0-01-domain-model.md
│   │   ├── M0-02-api-contract.md
│   │   ├── M0-03-calculation-input-schema.json
│   │   ├── M0-04-calculation-result-schema.json
│   │   ├── M0-05-test-validation-matrix.md
│   │   ├── M0-06-engineering-assumptions.md
│   │   └── M0-07-open-questions.md
│   ├── reference/
│   │   └── index.md                  ← index to the 12 baseline documents
│   ├── 01-requirements.md            ← THERM-REQ-001 Rev 0.2
│   ├── 02-engineering-methodology.md ← THERM-METH-001 Rev 0.2
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
| CR-ENG-001 | No production code before engineering approval of all 12 baseline documents. |
| CR-ENG-002 | IEC TR 60890 coefficient tables NEVER shipped in repository. Admin imports licensed dataset via empty JSON template. |
| CR-ENG-003 | Radiation calculations MUST use absolute temperature in kelvin (K), never °C. |
| CR-ENG-004 | Busbar resistance evaluated at calculated conductor temperature, NOT fixed 20 °C. |
| CR-ENG-005 | Unconverged results → `status: NON_CONVERGED`; UI shows "RESULT INVALID" watermark. |
| CR-ENG-006 | Forced ventilation active → IEC TR 60890 MODE 1 automatically disabled; no user override. |
| CR-ENG-007 | Arc-flash outputs → mandatory `INFORMATIVE` label; disclaimer in all reports and UI. This label cannot be removed by configuration. |
| CR-ENG-008 | Joint losses NEVER subsumed into bulk busbar resistivity. BusbarJoint is always a separate entity. |
| CR-ENG-009 | Compliance interpretation is standard-profile-aware (IEC 61439 limits ≠ UL limits). |
| CR-TECH-001 | `thermpro_engine` accepts versioned JSON input → returns versioned JSON result. It has NO direct dependency on FastAPI, SQLAlchemy, or any HTTP framework. |
| CR-TECH-002 | `schema_version` field is required on every InputSnapshot and ResultSnapshot. |
| CR-TECH-003 | De Vahl Davis cavity benchmark (BM-007, Nu_avg = 8.80 ± 2% at Ra = 10⁶) is a mandatory regression case that must pass on every CI run. |

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

# Run benchmark tests (slow)
pytest tests/benchmarks/ -v --timeout=120

# Type checking
mypy thermpro_engine --strict

# Format
black thermpro_engine backend tests
isort thermpro_engine backend tests

# Start dev stack
docker compose up -d
```

---

## Calculation Modes Summary

| Mode | Method | Ventilation | Standards |
|------|--------|-------------|-----------|
| MODE 1 | IEC TR 60890 empirical | Natural only | IEC TR 60890:2022 |
| MODE 2 | Nodal thermal network (CT145) | Natural | IEC 61439-1/-2, CT145 |
| MODE 3 | Forced-ventilation airflow network | Forced | IEC 61439-1/-2, CT145 |
| MODE 4 | CFD Export/Import Adapter | Any | External CFD solver |
| ARC-FLASH | IEEE 1584-2018 screening | — | IEEE 1584-2018 (INFORMATIVE) |

---

## Key Documents

| Document | ID | Latest Rev |
|----------|----|-----------|
| Requirements | THERM-REQ-001 | 0.2 |
| Engineering Methodology | THERM-METH-001 | 0.2 |
| Standards & Applicability | THERM-STD-001 | 0.2 |
| Thermal Network Model | THERM-NET-001 | 0.1 |
| Airflow Network Model | THERM-AFN-001 | 0.1 |
| Equations & Correlations | THERM-EQN-001 | 0.2 |
| Data Model | THERM-DAT-001 | 0.2 |
| System Architecture | THERM-ARCH-001 | 0.2 |
| UI Workflow | THERM-UI-001 | 0.1 |
| Validation Plan | THERM-VAL-001 | 0.2 |
| Risk Register | THERM-RISK-001 | 0.2 |
| Milestone Plan | THERM-MILE-001 | 0.1 |

---

## Milestone Gates

| Milestone | Gate | Status |
|-----------|------|--------|
| M0 | Engineering approval of all 12 baseline docs + M0 deliverables | **Pending approval** |
| M1 | M0 approved + CI green + mypy clean | Blocked on M0 |
| M2–M14 | Per THERM-MILE-001 exit criteria | Blocked on M1 |
