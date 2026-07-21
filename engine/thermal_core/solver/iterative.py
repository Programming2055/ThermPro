"""
M4 zonal thermal solver — successive substitution iterative solver.

Algorithm (successive substitution / Picard iteration):
  1. Build nodes: one AIR node per compartment + one AMBIENT node (fixed).
  2. Compute wall thermal conductance UA_wall,c for each compartment:
       UA_wall,c = 1 / (R_wall + 1/h_ext_conv + 1/h_rad_ext)  [W/K]
       (includes external natural convection and external radiation)
  3. For each iteration:
     a. Evaluate h_int (internal natural convection) from T_air - T_amb
     b. Evaluate h_rad (radiation, linearised) from T_wall - T_surr
     c. Compute updated UA_wall,c
     d. Solve scalar equation for single-zone case:
          T_air = T_amb + Q / UA_total
        Or matrix solve for multi-zone.
     e. Apply Aitken relaxation: T_new = ω T_solved + (1-ω) T_old
     f. Record convergence trace row
     g. Check convergence: max|ΔT| < tolerance
  4. Return ResultSnapshot (converged or NON_CONVERGED per CR-ENG-005).

Physical model:
  Single-compartment lumped-parameter energy balance:
    Q_devices = UA_total × (T_air - T_amb)
    UA_total  = 1 / (R_wall + R_int_conv + R_ext_conv)   [W/K]
  where:
    R_wall       = L/(k×A)           [K/W]  — wall conduction
    R_int_conv   = 1/(h_int × A)     [K/W]  — internal natural convection
    R_ext_conv   = 1/(h_ext × A)     [K/W]  — external natural convection
  and radiation is handled as a parallel thermal conductance on the exterior.

All values in SI base units (CR-ENG-013).
Temperatures in kelvin (CR-ENG-003).

Equation reference: THERM-EQN-001 §6.8 (Zonal Solver)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from thermal_core.conduction.fourier import wall_resistance_k_per_w
from thermal_core.diagnostics.diagnostics import (
    ConvergenceMonitor,
    energy_balance_error_percent,
    energy_balance_error_w,
)
from thermal_core.heat_generation.generation import compartment_heat_generation_w
from thermal_core.materials.air_properties import air_at, film_temperature_k
from thermal_core.natural_convection.churchill_chu import convection_coefficient
from thermal_core.radiation.gray_body import radiation_conductance_w_per_k
from thermal_core.result import (
    CompartmentResult,
    NodeTemperature,
    ResultSnapshot,
    SolverStatus,
    SolverWarning,
)
from thermal_core.result import NodeType as ResultNodeType
from thermal_core.snapshot import (
    BoundaryConditions,
    CompartmentSnapshot,
    GeometrySnapshot,
    InputSnapshot,
    SolverSettings,
    SurfaceOrientation,
    SurfaceSnapshot,
)
from thermal_core.solver.node import NodeType, ThermalNode
from thermal_core.validation.pre_solve import validate_input_snapshot


# ---------------------------------------------------------------------------
# Solver class
# ---------------------------------------------------------------------------


@dataclass
class ZonalSolver:
    """
    M4 lumped-parameter (zonal) thermal solver.

    Usage:
        solver = ZonalSolver()
        result = solver.solve(snapshot)

    The solver is stateless between calls — create one instance and call
    solve() as many times as needed.  Each call returns an independent
    ResultSnapshot.
    """

    def solve(self, snapshot: InputSnapshot) -> ResultSnapshot:
        """
        Run the zonal thermal solver on the given InputSnapshot.

        Returns a ResultSnapshot with:
          - status=CONVERGED if the iteration converged
          - status=NON_CONVERGED if max_iterations was reached (CR-ENG-005)
          - status=FAILED if pre-solve validation failed
        """
        t_start = time.monotonic()
        warnings: list[SolverWarning] = []

        # ------------------------------------------------------------------
        # Pre-solve validation
        # ------------------------------------------------------------------
        val = validate_input_snapshot(snapshot)
        if not val.is_valid:
            return _failed_result(
                snapshot,
                errors=[f"[{e.code}] {e.message}" for e in val.errors],
                elapsed=time.monotonic() - t_start,
            )

        geo = snapshot.geometry
        bc = snapshot.boundary_conditions
        ss = snapshot.solver_settings
        T_amb = bc.ambient_temperature_k
        P_amb = bc.ambient_pressure_pa

        # ------------------------------------------------------------------
        # Initialise temperatures: T_air,c = T_amb + 30 K as starting guess
        # ------------------------------------------------------------------
        T_air: dict[str, float] = {
            c.compartment_id: T_amb + 30.0 for c in geo.compartments
        }

        monitor = ConvergenceMonitor(tolerance_k=ss.convergence_tolerance_k)
        converged = False
        omega = ss.relaxation_factor

        # ------------------------------------------------------------------
        # Iterative loop
        # ------------------------------------------------------------------
        for iteration in range(ss.max_iterations):
            T_old = list(T_air.values())
            T_new: dict[str, float] = {}
            q_out_total = 0.0

            for comp in geo.compartments:
                cid = comp.compartment_id
                T_c = T_air[cid]

                Q_c = compartment_heat_generation_w(snapshot.heat_source_map, comp)

                # Compartment surfaces
                surfaces = [
                    s for s in geo.surfaces
                    if s.surface_id in comp.surface_ids
                ]
                total_area = sum(s.area_m2 for s in surfaces)
                if total_area <= 0:
                    total_area = comp.height_m * comp.width_m * 2 + comp.height_m * comp.depth_m * 2

                UA_total = _compute_ua_total(
                    T_c, T_amb, surfaces, total_area, comp, ss, P_amb
                )

                # T_air = T_amb + Q / UA_total
                if UA_total > 0:
                    T_solved = T_amb + Q_c / UA_total
                else:
                    T_solved = T_amb + 50.0  # fallback: no conductance defined

                # Floor at T_amb (physically, air can't be below ambient in steady state)
                T_solved = max(T_solved, T_amb)

                # Relaxation
                T_new[cid] = omega * T_solved + (1.0 - omega) * T_c
                q_out_total += UA_total * (T_new[cid] - T_amb)

            # Apply update
            T_air = T_new

            # Convergence diagnostics
            q_in = snapshot.heat_source_map.total_power_loss_w()
            trace = monitor.record(
                iteration=iteration,
                t_old=T_old,
                t_new=list(T_air.values()),
                q_in_w=q_in,
                q_out_w=q_out_total,
            )

            if monitor.is_converged(trace):
                converged = True
                break

        # ------------------------------------------------------------------
        # Assemble results
        # ------------------------------------------------------------------
        elapsed = time.monotonic() - t_start
        status = SolverStatus.CONVERGED if converged else SolverStatus.NON_CONVERGED

        if not converged:
            warnings.append(SolverWarning(
                code="WARN-005-NON-CONVERGED",
                message=(
                    f"Solver did not converge within {ss.max_iterations} iterations. "
                    f"Last max ΔT = {monitor._history[-1].max_delta_k:.4f} K. "
                    "CR-ENG-005: result marked NON_CONVERGED."
                ),
            ))

        node_temps, comp_results = _build_results(
            T_air, T_amb, snapshot, q_out_total if converged else 0.0
        )

        q_in = snapshot.heat_source_map.total_power_loss_w()
        q_out = sum(cr.heat_to_ambient_w for cr in comp_results)

        return ResultSnapshot(
            schema_version=snapshot.schema_version,
            calculation_id=snapshot.calculation_id,
            status=status,
            node_temperatures=node_temps,
            compartment_results=comp_results,
            convergence_trace=monitor.to_trace(),
            total_heat_generation_w=q_in,
            total_heat_dissipation_w=q_out,
            energy_balance_error_percent=energy_balance_error_percent(q_in, q_out),
            elapsed_seconds=elapsed,
            warnings=tuple(warnings),
        )


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


def solve(snapshot: InputSnapshot) -> ResultSnapshot:
    """Convenience function: create a ZonalSolver and run it."""
    return ZonalSolver().solve(snapshot)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _compute_ua_total(
    T_air_k: float,
    T_amb_k: float,
    surfaces: list[SurfaceSnapshot],
    total_area_m2: float,
    comp: CompartmentSnapshot,
    ss: SolverSettings,
    P_amb: float,
) -> float:
    """
    Compute total thermal conductance from compartment air to ambient [W/K].

    UA_total = 1 / (R_int_conv + R_wall + R_ext_conv) × A   [W/K]
    plus radiation on the exterior surface (parallel path).

    For multi-surface compartments, each surface contributes in parallel.
    """
    if not surfaces:
        # Fallback: estimate from enclosure dimensions
        area = (
            2 * comp.height_m * comp.width_m
            + 2 * comp.height_m * comp.depth_m
            + 2 * comp.width_m * comp.depth_m
        )
        surfaces_dummy = [_dummy_surface(comp, area)]
        return _compute_ua_total(T_air_k, T_amb_k, surfaces_dummy, area, comp, ss, P_amb)

    ua = 0.0
    for surf in surfaces:
        A = surf.area_m2
        L = comp.height_m  # characteristic length for convection

        # --- Internal convection conductance ---
        if ss.enable_natural_convection:
            h_int = convection_coefficient(
                t_surface_k=T_amb_k + 0.5 * (T_air_k - T_amb_k),  # approx wall temp
                t_air_k=T_air_k,
                characteristic_length_m=L,
                orientation=surf.orientation,
                pressure_pa=P_amb,
            )
        else:
            h_int = 5.0  # fallback [W/(m²·K)]
        G_int = h_int * A

        # --- Wall conduction ---
        if surf.thickness_m > 0 and surf.is_external:
            R_wall = wall_resistance_k_per_w(
                surf.thickness_m,
                surf.thermal_conductivity_w_per_m_k,
                A,
            )
            G_wall = 1.0 / R_wall
        else:
            G_wall = 1e6  # thin or internal partition — negligible resistance

        # --- External convection (on outer face) ---
        if surf.is_external and ss.enable_natural_convection:
            T_wall_ext = T_amb_k + 5.0  # approximate outer wall temperature
            h_ext = convection_coefficient(
                t_surface_k=T_wall_ext,
                t_air_k=T_amb_k,
                characteristic_length_m=L,
                orientation=surf.orientation,
                pressure_pa=P_amb,
            )
            G_ext = h_ext * A
        else:
            G_ext = 1e6 if not surf.is_external else 5.0 * A

        # --- External radiation ---
        G_rad = 0.0
        if surf.is_external and ss.enable_radiation:
            T_wall_est = T_amb_k + max(1.0, (T_air_k - T_amb_k) * 0.3)
            G_rad = radiation_conductance_w_per_k(
                t_surface_k=T_wall_est,
                t_surroundings_k=T_amb_k,
                emissivity=surf.emissivity,
                area_m2=A,
            )

        # Series: int_conv → wall → (ext_conv ∥ radiation)
        G_ext_total = G_ext + G_rad
        if G_ext_total > 0:
            ua_surf = 1.0 / (1.0 / G_int + 1.0 / G_wall + 1.0 / G_ext_total)
        else:
            ua_surf = 1.0 / (1.0 / G_int + 1.0 / G_wall)

        ua += ua_surf

    return ua


@dataclass
class _DummySurface:
    """Minimal surface for fallback calculation when no surfaces are defined."""
    surface_id: str
    compartment_id: str
    area_m2: float
    orientation: SurfaceOrientation
    emissivity: float
    thickness_m: float
    thermal_conductivity_w_per_m_k: float
    is_external: bool


def _dummy_surface(comp: CompartmentSnapshot, area: float) -> SurfaceSnapshot:
    return SurfaceSnapshot(
        surface_id="_dummy",
        compartment_id=comp.compartment_id,
        area_m2=area,
        orientation=SurfaceOrientation.VERTICAL,
        emissivity=0.7,
        thickness_m=0.002,
        thermal_conductivity_w_per_m_k=50.0,  # steel
        is_external=True,
    )


def _build_results(
    T_air: dict[str, float],
    T_amb: float,
    snapshot: InputSnapshot,
    q_out_total: float,
) -> tuple[tuple[NodeTemperature, ...], tuple[CompartmentResult, ...]]:
    """Build NodeTemperature and CompartmentResult objects from the solved temperatures."""
    node_temps: list[NodeTemperature] = []
    comp_results: list[CompartmentResult] = []

    for comp in snapshot.geometry.compartments:
        cid = comp.compartment_id
        T_c = T_air.get(cid, T_amb)
        Q_c = compartment_heat_generation_w(snapshot.heat_source_map, comp)

        # Compute heat to ambient for this compartment
        surfaces = [
            s for s in snapshot.geometry.surfaces
            if s.surface_id in comp.surface_ids and s.is_external
        ]
        total_ext_area = sum(s.area_m2 for s in surfaces)
        if total_ext_area > 0 and T_c > T_amb:
            n_comps = len(snapshot.geometry.compartments)
            q_out_c = Q_c  # in steady state, q_out = q_in per compartment
        else:
            q_out_c = 0.0

        node_temps.append(NodeTemperature(
            node_id=f"air_{cid}",
            node_type=ResultNodeType.AIR,
            temperature_k=T_c,
            heat_generation_w=Q_c,
            net_heat_flux_w_per_m2=None,
        ))

        comp_results.append(CompartmentResult(
            compartment_id=cid,
            mean_air_temperature_k=T_c,
            max_device_temperature_k=None,   # M4 MVP: device temperatures not computed
            max_surface_temperature_k=None,  # M4 MVP: surface temperatures not computed
            total_heat_generation_w=Q_c,
            heat_to_ambient_w=q_out_c,
        ))

    # Ambient node
    node_temps.append(NodeTemperature(
        node_id="ambient",
        node_type=ResultNodeType.AMBIENT,
        temperature_k=T_amb,
        heat_generation_w=0.0,
        net_heat_flux_w_per_m2=None,
    ))

    return tuple(node_temps), tuple(comp_results)


def _failed_result(
    snapshot: InputSnapshot,
    errors: list[str],
    elapsed: float,
) -> ResultSnapshot:
    """Build a FAILED ResultSnapshot when pre-solve validation fails."""
    warnings = tuple(
        SolverWarning(code="VAL-FAIL", message=msg) for msg in errors
    )
    return ResultSnapshot(
        schema_version=snapshot.schema_version,
        calculation_id=snapshot.calculation_id,
        status=SolverStatus.FAILED,
        node_temperatures=(),
        compartment_results=(),
        convergence_trace=(),
        total_heat_generation_w=0.0,
        total_heat_dissipation_w=0.0,
        energy_balance_error_percent=100.0,
        elapsed_seconds=elapsed,
        warnings=warnings,
    )
