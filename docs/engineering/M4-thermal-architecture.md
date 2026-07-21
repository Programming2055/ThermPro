# M4 Thermal Architecture

**Document ID:** THERM-ARCH-M4-001  
**Revision:** 0.1  
**Status:** In Progress (M4 Implementation)  
**Date:** 2026-07-21

---

## 1. Scope

Milestone 4 adds the first production-grade thermal physics solver to the ThermPro platform.
M4 implements a lumped-parameter (zonal) thermal model that computes steady-state air
temperatures for each enclosure compartment.

M4 does NOT implement:
- Device surface temperatures (planned for M5)
- Transient analysis (deferred)
- CFD coupling (MODE 4 — deferred)
- Arc flash (removed from MVP, DR-012)

M3 must be complete before M4 is run: M3 produces the `HeatSourceMap` that M4 consumes
as a boundary condition.

---

## 2. Non-Negotiable Rules (M4)

| # | Rule |
|---|------|
| 1 | Solver never queries the database |
| 2 | Solver never queries the library |
| 3 | `LibraryResolver` layer is mandatory |
| 4 | Inputs are immutable (`frozen=True` dataclasses) |
| 5 | Outputs are immutable (`frozen=True` dataclasses) |
| 6 | Results are deterministic — identical inputs produce identical outputs |
| 7 | All internal computation in SI base units (CR-ENG-013) |
| 8 | No hidden assumptions — all solver parameters exposed in `SolverSettings` |
| 9 | Every engineering warning is surfaced in `ResultSnapshot.warnings` |
| 10 | No fake temperatures — solver never invents results it cannot justify |
| 11 | No CFD coupling in M4 |
| 12 | No transient analysis |
| 13 | No optimization |
| 14 | No AI prediction |
| 15 | No visualization |
| 16 | No Three.js |
| 17 | No heat maps |
| 18 | No frontend temperature rendering |
| 19 | No API shortcuts around the solver |
| 20 | Every equation documented in THERM-EQN-001 |

---

## 3. Module Layout

```
engine/thermal_core/
├── snapshot.py           ← InputSnapshot (solver input boundary)
├── result.py             ← ResultSnapshot (solver output boundary)
├── resolver.py           ← LibraryResolver (M3 → M4 bridge)
├── materials/
│   ├── air_properties.py    ← Temperature-dependent air properties
│   └── thermal_material.py  ← ThermalMaterial (T-dependent interface)
├── conduction/
│   └── fourier.py           ← Planar wall thermal resistance / conductance
├── natural_convection/
│   └── churchill_chu.py     ← Churchill-Chu (1975) vertical plate + horizontal
├── radiation/
│   └── gray_body.py         ← Gray body Stefan-Boltzmann, linearised h_rad
├── forced_convection/
│   └── fan_model.py         ← Fan curve interpolation, operating point
├── airflow/
│   └── network.py           ← Stack effect, orifice flow, natural ventilation
├── heat_generation/
│   └── generation.py        ← Compartment power aggregation
├── solver/
│   ├── node.py              ← ThermalNode dataclass
│   └── iterative.py         ← ZonalSolver (successive substitution)
├── diagnostics/
│   └── diagnostics.py       ← ConvergenceMonitor, energy balance audit
├── validation/
│   └── pre_solve.py         ← Pre-solve engineering checks (VAL-001..010)
└── benchmarks/
    ├── analytical.py        ← BM-001..004 exact solutions
    └── iec60890.py          ← IEC TR 60890 framework (CR-ENG-002)
```

---

## 4. Data Flow

```
                    M3 Output
                       │
                       ▼
            ┌────────────────────┐
            │   HeatSourceMap    │ (power loss per entity, location, confidence)
            └────────────────────┘
                       │
                       │  + Geometry snapshot
                       │  + Boundary conditions
                       │  + Solver settings
                       ▼
            ┌────────────────────┐
            │   InputSnapshot    │ ← immutable frozen dataclass (CR-TECH-002)
            └────────────────────┘
                       │
                       ▼
            ┌────────────────────┐
            │  Pre-solve         │ VAL-001..010
            │  Validation        │ CR-ENG-006 (MODE 1 + forced ventilation)
            └────────────────────┘
                       │
                    is_valid?
                   /         \
                 YES           NO
                  │             │
                  ▼             ▼
          ┌──────────┐   ┌──────────────┐
          │ Zonal    │   │ ResultSnapshot│
          │ Solver   │   │ status=FAILED │
          └──────────┘   └──────────────┘
                  │
             (iterate)
                  │
                  ▼
          ┌────────────────────┐
          │   ResultSnapshot   │ ← immutable frozen dataclass
          │ status=CONVERGED   │   CR-ENG-005: NON_CONVERGED if
          │ status=NON_CONVERGED│  iteration limit reached
          └────────────────────┘
```

---

## 5. Solver Boundary: InputSnapshot

The `InputSnapshot` is the complete, versioned input to the solver. It contains:

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | `str` | CR-TECH-002: required |
| `library_manifest` | `dict[str, str]` | CR-TECH-002: required |
| `calculation_id` | `str` | UUID for audit trail |
| `geometry` | `GeometrySnapshot` | Compartments, surfaces, openings |
| `heat_source_map` | `HeatSourceMap` | M3 output: all heat sources |
| `boundary_conditions` | `BoundaryConditions` | Ambient T [K], P [Pa], humidity |
| `solver_settings` | `SolverSettings` | Mode, max_iter, tolerance, relaxation |

The solver receives exactly one `InputSnapshot` and returns exactly one `ResultSnapshot`.
It performs no I/O, no database queries, no library lookups (CR-TECH-001, M4 rule 1-2).

---

## 6. Solver Output: ResultSnapshot

| Field | Type | Description |
|-------|------|-------------|
| `status` | `SolverStatus` | CONVERGED / NON_CONVERGED / FAILED |
| `node_temperatures` | `tuple[NodeTemperature, ...]` | T [K] per node |
| `compartment_results` | `tuple[CompartmentResult, ...]` | Per-compartment aggregates |
| `convergence_trace` | `tuple[ConvergenceTrace, ...]` | Per-iteration diagnostics |
| `total_heat_generation_w` | `float` | Sum of all source power [W] |
| `total_heat_dissipation_w` | `float` | Total heat leaving via surfaces [W] |
| `energy_balance_error_percent` | `float` | |Q_in - Q_out| / Q_in × 100 [%] |
| `warnings` | `tuple[SolverWarning, ...]` | Engineering warnings |

CR-ENG-005: `status=NON_CONVERGED` must cause the UI to show "RESULT INVALID" and
refuse to generate a compliance report.

---

## 7. LibraryResolver

The `LibraryResolver` is the mandatory M3→M4 bridge. It converts library ORM objects
into immutable solver-ready types. The service layer calls the resolver before creating
the `InputSnapshot`. The solver never sees ORM objects or UUIDs.

```
Service layer:
  entry = db.query(MaterialLibraryEntry).filter_by(...)
  material = LibraryResolver().resolve_material(entry)
  # → ThermalMaterial (immutable, SI units, T-dependent interface)

Solver:
  # receives ThermalMaterial — never the DB entry
```

---

## 8. Engineering Constraints Implemented

| Constraint | Where Enforced |
|-----------|----------------|
| CR-ENG-003: kelvin for radiation | `gray_body.py` — T < 100 K raises ValueError |
| CR-ENG-005: NON_CONVERGED → invalid | `iterative.py` + `SolverStatus` enum |
| CR-ENG-006: MODE_1 + forced → FAIL | `pre_solve.py` VAL-006 |
| CR-TECH-001: no ORM in solver | Solver imports are pure Python only |
| CR-TECH-002: schema_version required | `InputSnapshot.__post_init__` |
| M4 Rule 6: deterministic | Stateless `ZonalSolver` — no global state |
| M4 Rule 7: SI units | All values in Pa, K, W, m throughout |
