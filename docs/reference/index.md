# Reference Document Index — ThermPro Engineering Baseline

**Status:** Rev 0.2 (as of 2026-07-03)

All baseline documents reside in `docs/`. This index provides a navigational
summary. Every document must be read and approved before Milestone 1 begins.

---

## Baseline Engineering Documents

| # | File | Document ID | Rev | Status | Description |
|---|------|-------------|-----|--------|-------------|
| 01 | [requirements.md](../01-requirements.md) | THERM-REQ-001 | 0.2 | Pending Approval | All FR, NFR, and CR requirements with domain codes |
| 02 | [engineering-methodology.md](../02-engineering-methodology.md) | THERM-METH-001 | 0.2 | Pending Approval | Physics, variable table, iteration structure, applicability boundaries |
| 03 | [standards-and-applicability.md](../03-standards-and-applicability.md) | THERM-STD-001 | 0.2 | Pending Approval | IEC 61439, IEC TR 60890, CT145, IEEE 1584-2018, UL/ANSI scope |
| 04 | [thermal-network-model.md](../04-thermal-network-model.md) | THERM-NET-001 | 0.1 | Pending Approval | Node types, conductance matrix G·T=Q, radiation linearisation |
| 05 | [airflow-network-model.md](../05-airflow-network-model.md) | THERM-AFN-001 | 0.1 | Pending Approval | Pressure-node network, orifice flow, buoyancy stack, fan curves |
| 06 | [equations-and-correlations.md](../06-equations-and-correlations.md) | THERM-EQN-001 | 0.2 | Pending Approval | Full equation set with dimensional checks and validity ranges |
| 07 | [data-model.md](../07-data-model.md) | THERM-DAT-001 | 0.2 | Pending Approval | Entity hierarchy, field definitions, InputSnapshot, ResultSnapshot schemas |
| 08 | [system-architecture.md](../08-system-architecture.md) | THERM-ARCH-001 | 0.2 | Pending Approval | Component diagram, module list, tech stack, deployment topology |
| 09 | [UI-workflow.md](../09-UI-workflow.md) | THERM-UI-001 | 0.1 | Pending Approval | 10-step workflow, screen descriptions, colour conventions |
| 10 | [validation-plan.md](../10-validation-plan.md) | THERM-VAL-001 | 0.2 | Pending Approval | 35 unit tests, 8 benchmarks, L3/L4 reference examples |
| 11 | [risk-register.md](../11-risk-register.md) | THERM-RISK-001 | 0.2 | Pending Approval | 20 risks with severity scores and mitigations |
| 12 | [milestone-plan.md](../12-milestone-plan.md) | THERM-MILE-001 | 0.1 | Pending Approval | 14 milestones with deliverables, exit criteria, dependency graph |

---

## External Standards Referenced

| Standard | Scope in ThermPro |
|----------|-------------------|
| IEC 61439-1:2011+A1:2020 | General requirements; temperature-rise limits; Form types |
| IEC 61439-2:2020 | Power switchgear and controlgear assemblies |
| IEC TR 60890:2022 | Empirical method (MODE 1); licensed coefficient tables |
| Schneider CT145 | Nodal thermal network methodology (MODE 2 + 3) |
| IEC 60947 | Device ratings and derating data source |
| IEC 60909 | Short-circuit current calculations (adiabatic fault heating input) |
| IEC TR 61641:2014 | Internal arc withstand guidance |
| IEC TS 63107:2021 | Electrothermal coordination in assemblies |
| IEEE 1584-2018 | Arc-flash parametric screening (INFORMATIVE module) |
| UL 891 | Deadfront switchboards (North American compliance layer) |
| UL 1558 | Metal-enclosed switchgear (North American compliance layer) |
| ANSI/IEEE C37.20.1 | Metal-enclosed bus and switchgear |
| NFPA 70E | Arc-flash hazard disclaimer requirements |

---

## Milestone 0 Engineering Deliverables

| File | Description |
|------|-------------|
| [M0-01-domain-model.md](../engineering/M0-01-domain-model.md) | Entity-relationship diagram and field definitions |
| [M0-02-api-contract.md](../engineering/M0-02-api-contract.md) | REST API endpoint contract (OpenAPI style) |
| [M0-03-calculation-input-schema.json](../engineering/M0-03-calculation-input-schema.json) | JSON Schema for InputSnapshot v1 |
| [M0-04-calculation-result-schema.json](../engineering/M0-04-calculation-result-schema.json) | JSON Schema for ResultSnapshot v1 |
| [M0-05-test-validation-matrix.md](../engineering/M0-05-test-validation-matrix.md) | FR → test → benchmark traceability matrix |
| [M0-06-engineering-assumptions.md](../engineering/M0-06-engineering-assumptions.md) | All engineering assumptions requiring acceptance |
| [M0-07-open-questions.md](../engineering/M0-07-open-questions.md) | Unresolved questions requiring engineering approval |
