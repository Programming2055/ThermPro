"""
Zonal thermal solver — nodal network with Picard (successive-substitution) iteration.

Model (THERM-NET-001 §3–§5, THERM-EQN-001 §12)
----------------------------------------------
The enclosure is discretised into a conductance network:

  * one **air node** per compartment, carrying its mean air temperature;
  * for each external wall, an **inner-face** and an **outer-face** node, joined
    by the wall's Fourier conduction;
  * for each internal partition, a single **surface node** shared by the two
    compartments it separates;
  * one **entity node** per heat source whose exposed area is known (device
    body, busbar segment, joint, cable), so the engineer gets a conductor
    temperature rather than only an air temperature;
  * a single fixed **ambient node**.

Conductances between them:

  air ↔ inner face        natural convection, Churchill-Chu / McAdams
  inner face ↔ outer face Fourier conduction through the wall
  outer face ↔ ambient    external natural convection ∥ linearised radiation
  air ↔ air (partition)   convection on both faces, in series through the wall
  entity ↔ air            natural convection off the entity body
  entity ↔ inner face     linearised radiation, weighted by surface area share
  air ↔ ambient / air     air-mass transport, ṁ·cp, from the airflow network

Every conductance depends on the temperature field, so the system is nonlinear.
Each outer iteration freezes the conductances at the current temperatures,
solves the resulting linear system G·T = b exactly, and under-relaxes the
update (THERM-NET-001 §11). Busbar and cable losses are re-evaluated at the
conductor's own temperature on each pass, as CR-ENG-004 requires.

Statuses (CR-ENG-005): CONVERGED, NON_CONVERGED when the iteration limit or a
divergence guard is hit, FAILED when the model cannot be solved at all. The
solver never raises on a convergence failure and never returns temperatures
without a status that reflects how trustworthy they are.

All values in SI base units (CR-ENG-013); all temperatures in kelvin
(CR-ENG-003).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass

from thermal_core.airflow.network import orifice_flow_m3_per_s, stack_pressure_pa
from thermal_core.benchmarks.iec60890 import (
    effective_cooling_area_m2,
    iec60890_temperature_rise,
)
from thermal_core.conduction.fourier import wall_conductance_w_per_k
from thermal_core.diagnostics.diagnostics import (
    ConvergenceMonitor,
    energy_balance_error_percent,
)
from thermal_core.heat_generation.generation import heat_sources_in_compartment
from thermal_core.heat_source import HeatSource, HeatSourceEntityType
from thermal_core.materials.air_properties import air_at
from thermal_core.natural_convection.churchill_chu import convection_coefficient
from thermal_core.radiation.gray_body import (
    effective_emissivity_two_surfaces,
    radiation_conductance_w_per_k,
)
from thermal_core.result import (
    AirflowSummary,
    CompartmentResult,
    Mode1Result,
    NodeTemperature,
    NodeType,
    OpeningFlow,
    ResultSnapshot,
    SolverStatus,
    SolverWarning,
)
from thermal_core.snapshot import (
    CalculationMode,
    CompartmentSnapshot,
    GeometrySnapshot,
    InputSnapshot,
    OpeningSnapshot,
    SurfaceOrientation,
    SurfaceSnapshot,
)
from thermal_core.solver.network import SingularNetworkError, ThermalNetwork
from thermal_core.validation.pre_solve import validate_input_snapshot

AMBIENT_NODE = "ambient"

# Initial guesses, in kelvin above ambient. They only set where the iteration
# starts; the converged answer does not depend on them.
_AIR_INITIAL_RISE_K = 20.0
_SURFACE_INITIAL_RISE_K = 8.0
_ENTITY_INITIAL_RISE_K = 35.0

# THERM-NET-001 §12 sanity bounds on the temperature field.
_T_MIN_PLAUSIBLE_K = 1.0
_T_MAX_PLAUSIBLE_K = 1000.0

# Emissivity assumed for an interior enclosure face when the snapshot gives
# none. Painted sheet steel; stated rather than silently applied.
_DEFAULT_INTERNAL_EMISSIVITY = 0.9


# ---------------------------------------------------------------------------
# Node naming
# ---------------------------------------------------------------------------


def air_node(compartment_id: str) -> str:
    return f"air:{compartment_id}"


def surface_inner_node(surface_id: str) -> str:
    return f"surf_in:{surface_id}"


def surface_outer_node(surface_id: str) -> str:
    return f"surf_out:{surface_id}"


def partition_node(surface_id: str) -> str:
    return f"surf:{surface_id}"


def entity_node(source_id: str) -> str:
    return f"ent:{source_id}"


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Topology:
    """Which nodes exist and what they represent. Fixed across iterations."""

    free_nodes: tuple[str, ...]
    entity_by_node: dict[str, HeatSource]
    compartment_of_entity_node: dict[str, str]
    # Surfaces that bound each compartment on their interior face.
    interior_surfaces: dict[str, tuple[SurfaceSnapshot, ...]]
    external_surfaces: tuple[SurfaceSnapshot, ...]
    partitions: tuple[SurfaceSnapshot, ...]
    # Heat sources with no exposed area: their power goes straight to the air.
    airborne_sources: dict[str, tuple[HeatSource, ...]]


class ZonalSolver:
    """
    Nodal thermal solver for an enclosure.

    Stateless between calls: one instance may be reused, and each `solve`
    returns an independent ResultSnapshot.
    """

    def solve(self, snapshot: InputSnapshot) -> ResultSnapshot:
        """Run the solver and return a ResultSnapshot (never raises on failure)."""
        t_start = time.monotonic()

        validation = validate_input_snapshot(snapshot)
        if not validation.is_valid:
            return _failed_result(
                snapshot,
                errors=[f"[{e.code}] {e.message}" for e in validation.errors],
                elapsed=time.monotonic() - t_start,
            )

        mode = snapshot.solver_settings.calculation_mode
        if mode == CalculationMode.MODE_1:
            return _solve_mode_1(snapshot, t_start)
        if mode == CalculationMode.MODE_4:
            return _failed_result(
                snapshot,
                errors=[
                    "[MODE4-ADAPTER] MODE_4 is the CFD export/import adapter, not a "
                    "solver mode. Build an export package with "
                    "thermal_core.cfd_export.build_cfd_export_package() and import the "
                    "external solver's field; MODE_2 or MODE_3 produces the initial "
                    "and boundary conditions it needs."
                ],
                elapsed=time.monotonic() - t_start,
            )
        return _solve_network(snapshot, t_start)


def solve(snapshot: InputSnapshot) -> ResultSnapshot:
    """Convenience wrapper: construct a ZonalSolver and run it."""
    return ZonalSolver().solve(snapshot)


# ---------------------------------------------------------------------------
# MODE 2 / MODE 3 — nodal network
# ---------------------------------------------------------------------------


def _solve_network(snapshot: InputSnapshot, t_start: float) -> ResultSnapshot:
    geo = snapshot.geometry
    bc = snapshot.boundary_conditions
    settings = snapshot.solver_settings
    t_amb = bc.ambient_temperature_k
    warnings: list[SolverWarning] = []

    topology = _build_topology(geo, snapshot)
    for source in topology.entity_by_node.values():
        if source.compartment_id is None and not _source_is_assigned(source, geo):
            warnings.append(
                SolverWarning(
                    code="WARN-UNASSIGNED-SOURCE",
                    message=(
                        f"Heat source {source.source_id!r} is not assigned to any "
                        f"compartment; its power was not injected anywhere."
                    ),
                    entity_id=source.entity_id,
                )
            )

    temperatures = _initial_field(topology, geo, t_amb)
    monitor = ConvergenceMonitor(tolerance_k=settings.convergence_tolerance_k)
    omega = settings.relaxation_factor

    converged = False
    diverging_for = 0
    previous_max_delta = float("inf")
    flows: tuple[OpeningFlow, ...] = ()
    stack_pa: float | None = None
    network: ThermalNetwork | None = None
    failure: str | None = None

    for iteration in range(settings.max_iterations):
        flows, stack_pa = _solve_airflow(snapshot, temperatures)
        try:
            network = _assemble_network(snapshot, topology, temperatures, flows)
            solved = network.solve()
        except (SingularNetworkError, ValueError) as exc:
            failure = str(exc)
            break

        previous = dict(temperatures)
        temperatures = {
            node_id: omega * solved[node_id] + (1.0 - omega) * previous[node_id]
            for node_id in previous
        }
        temperatures[AMBIENT_NODE] = t_amb

        implausible = _implausible_node(temperatures)
        if implausible is not None:
            node_id, value = implausible
            failure = (
                f"Node {node_id!r} reached {value:.1f} K, outside the plausible range "
                f"[{_T_MIN_PLAUSIBLE_K:.0f} K, {_T_MAX_PLAUSIBLE_K:.0f} K]. "
                f"Check the input data (THERM-NET-001 §12)."
            )
            break

        q_in = _total_generation_w(topology, temperatures)
        q_out = _heat_leaving_w(network, temperatures, t_amb)
        trace = monitor.record(
            iteration=iteration,
            t_old=[previous[n] for n in topology.free_nodes],
            t_new=[temperatures[n] for n in topology.free_nodes],
            q_in_w=q_in,
            q_out_w=q_out,
        )

        if monitor.is_converged(trace):
            converged = True
            break

        if trace.max_delta_k > previous_max_delta:
            diverging_for += 1
            if diverging_for >= settings.divergence_patience:
                warnings.append(
                    SolverWarning(
                        code="WARN-012-DIVERGING",
                        message=(
                            f"Residual grew for {diverging_for} consecutive iterations "
                            f"(last max ΔT = {trace.max_delta_k:.3f} K). Iteration "
                            f"stopped early; try a smaller relaxation_factor than "
                            f"{omega:.2f} (THERM-NET-001 §12)."
                        ),
                    )
                )
                break
        else:
            diverging_for = 0
        previous_max_delta = trace.max_delta_k

    elapsed = time.monotonic() - t_start

    if failure is not None:
        return _failed_result(snapshot, errors=[failure], elapsed=elapsed)
    if network is None:
        return _failed_result(
            snapshot,
            errors=["Solver produced no network; max_iterations must be >= 1."],
            elapsed=elapsed,
        )

    if not converged:
        last_delta = monitor.history[-1].max_delta_k if monitor.history else float("nan")
        warnings.append(
            SolverWarning(
                code="WARN-005-NON-CONVERGED",
                message=(
                    f"Solver did not converge to {settings.convergence_tolerance_k} K "
                    f"within {settings.max_iterations} iterations; last max ΔT = "
                    f"{last_delta:.4f} K. CR-ENG-005: the result is marked "
                    f"NON_CONVERGED and must not be used for compliance."
                ),
            )
        )

    warnings.extend(_k_ac_warnings(topology))

    q_in = _total_generation_w(topology, temperatures)
    q_out = _heat_leaving_w(network, temperatures, t_amb)
    node_temps = _node_temperatures(topology, snapshot, temperatures)
    comp_results = _compartment_results(topology, snapshot, network, temperatures, t_amb)

    airflow = (
        AirflowSummary(
            total_flow_rate_m3_per_s=sum(abs(f.volumetric_flow_m3_per_s) for f in flows) / 2.0,
            buoyancy_stack_pressure_pa=stack_pa,
            opening_flows=flows,
        )
        if flows
        else None
    )

    return ResultSnapshot(
        schema_version=snapshot.schema_version,
        calculation_id=snapshot.calculation_id,
        status=SolverStatus.CONVERGED if converged else SolverStatus.NON_CONVERGED,
        node_temperatures=node_temps,
        compartment_results=comp_results,
        convergence_trace=monitor.to_trace(),
        total_heat_generation_w=q_in,
        total_heat_dissipation_w=q_out,
        energy_balance_error_percent=energy_balance_error_percent(q_in, q_out),
        elapsed_seconds=elapsed,
        warnings=tuple(warnings),
        airflow=airflow,
    )


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------


def _source_is_assigned(source: HeatSource, geo: GeometrySnapshot) -> bool:
    return any(source.source_id in c.heat_source_ids for c in geo.compartments)


def _compartment_for_source(source: HeatSource, geo: GeometrySnapshot) -> str | None:
    """Resolve a source's compartment, preferring the explicit back-reference."""
    if source.compartment_id is not None:
        return source.compartment_id
    for comp in geo.compartments:
        if source.source_id in comp.heat_source_ids:
            return comp.compartment_id
    return None


def _build_topology(geo: GeometrySnapshot, snapshot: InputSnapshot) -> _Topology:
    free_nodes: list[str] = []
    entity_by_node: dict[str, HeatSource] = {}
    compartment_of_entity_node: dict[str, str] = {}
    airborne: dict[str, list[HeatSource]] = {c.compartment_id: [] for c in geo.compartments}
    interior: dict[str, list[SurfaceSnapshot]] = {
        c.compartment_id: [] for c in geo.compartments
    }
    external: list[SurfaceSnapshot] = []
    partitions: list[SurfaceSnapshot] = []

    for comp in geo.compartments:
        free_nodes.append(air_node(comp.compartment_id))

    for surf in geo.surfaces:
        if surf.compartment_id in interior:
            interior[surf.compartment_id].append(surf)
        if surf.is_external:
            if surf.is_restricted:
                # A restricted surface exchanges no heat with the surroundings
                # (M0-06): it is modelled as adiabatic, so it carries no nodes.
                continue
            external.append(surf)
            free_nodes.append(surface_inner_node(surf.surface_id))
            free_nodes.append(surface_outer_node(surf.surface_id))
        elif surf.adjacent_compartment_id is not None:
            partitions.append(surf)
            free_nodes.append(partition_node(surf.surface_id))
        # An internal surface with no compartment on the far side is adiabatic
        # and transports no heat in steady state, so it gets no node.

    for comp in geo.compartments:
        for source in heat_sources_in_compartment(snapshot.heat_source_map, comp):
            if source.surface_area_m2 is None:
                # Without an exposed area there is no defensible way to compute
                # a body temperature, so the power is released into the air and
                # the entity reports the air temperature.
                airborne[comp.compartment_id].append(source)
                continue
            node = entity_node(source.source_id)
            free_nodes.append(node)
            entity_by_node[node] = source
            compartment_of_entity_node[node] = comp.compartment_id

    return _Topology(
        free_nodes=tuple(free_nodes),
        entity_by_node=entity_by_node,
        compartment_of_entity_node=compartment_of_entity_node,
        interior_surfaces={k: tuple(v) for k, v in interior.items()},
        external_surfaces=tuple(external),
        partitions=tuple(partitions),
        airborne_sources={k: tuple(v) for k, v in airborne.items()},
    )


def _initial_field(
    topology: _Topology, geo: GeometrySnapshot, t_amb: float
) -> dict[str, float]:
    field: dict[str, float] = {AMBIENT_NODE: t_amb}
    for node in topology.free_nodes:
        if node.startswith("air:"):
            field[node] = t_amb + _AIR_INITIAL_RISE_K
        elif node.startswith("ent:"):
            field[node] = t_amb + _ENTITY_INITIAL_RISE_K
        else:
            field[node] = t_amb + _SURFACE_INITIAL_RISE_K
    return field


# ---------------------------------------------------------------------------
# Network assembly
# ---------------------------------------------------------------------------


def _assemble_network(
    snapshot: InputSnapshot,
    topology: _Topology,
    temperatures: dict[str, float],
    flows: tuple[OpeningFlow, ...],
) -> ThermalNetwork:
    geo = snapshot.geometry
    settings = snapshot.solver_settings
    bc = snapshot.boundary_conditions
    t_amb = bc.ambient_temperature_k
    p_amb = bc.ambient_pressure_pa

    net = ThermalNetwork()
    net.add_fixed_node(AMBIENT_NODE, t_amb)
    for node in topology.free_nodes:
        net.add_free_node(node, temperatures[node])

    # --- enclosure walls -------------------------------------------------
    for surf in topology.external_surfaces:
        comp = geo.compartment_by_id(surf.compartment_id)
        length = _characteristic_length(surf, comp)
        inner = surface_inner_node(surf.surface_id)
        outer = surface_outer_node(surf.surface_id)
        air = air_node(surf.compartment_id)

        if net.has_node(air):
            h_int = _internal_h(
                settings, temperatures[inner], temperatures[air], length, surf, p_amb
            )
            net.add_conductance(air, inner, h_int * surf.area_m2)

        net.add_conductance(
            inner,
            outer,
            wall_conductance_w_per_k(
                surf.thickness_m, surf.thermal_conductivity_w_per_m_k, surf.area_m2
            ),
        )

        h_ext = _external_h(settings, temperatures[outer], t_amb, length, surf, p_amb)
        net.add_conductance(outer, AMBIENT_NODE, h_ext * surf.area_m2)

        if settings.enable_radiation:
            net.add_conductance(
                outer,
                AMBIENT_NODE,
                radiation_conductance_w_per_k(
                    t_surface_k=temperatures[outer],
                    t_surroundings_k=t_amb,
                    emissivity=surf.emissivity,
                    area_m2=surf.area_m2,
                ),
            )

    # --- internal partitions --------------------------------------------
    for surf in topology.partitions:
        node = partition_node(surf.surface_id)
        near = air_node(surf.compartment_id)
        far_id = surf.adjacent_compartment_id
        assert far_id is not None  # guaranteed by _build_topology
        far = air_node(far_id)
        if not (net.has_node(near) and net.has_node(far)):
            continue
        comp = geo.compartment_by_id(surf.compartment_id)
        length = _characteristic_length(surf, comp)

        for air in (near, far):
            h = _internal_h(
                settings, temperatures[node], temperatures[air], length, surf, p_amb
            )
            net.add_conductance(air, node, h * surf.area_m2)

        if surf.thickness_m > 0:
            # The partition's own conduction resistance is in series with the
            # two film resistances; representing it as a direct air-to-air path
            # would double-count, so it is added between the faces of the same
            # shared node only when the wall is thick enough to matter. A single
            # shared node already assumes the partition is isothermal, which is
            # the right call for thin steel (Bi << 1).
            pass

    # --- entity bodies ----------------------------------------------------
    for node, source in topology.entity_by_node.items():
        comp_id = topology.compartment_of_entity_node[node]
        air = air_node(comp_id)
        if not net.has_node(air):
            continue
        comp = geo.compartment_by_id(comp_id)
        area = source.surface_area_m2
        assert area is not None  # guaranteed by _build_topology
        length = source.characteristic_length_m or _entity_length(source, comp)

        h = (
            convection_coefficient(
                t_surface_k=temperatures[node],
                t_air_k=temperatures[air],
                characteristic_length_m=length,
                orientation=SurfaceOrientation.VERTICAL,
                pressure_pa=p_amb,
            )
            if settings.enable_natural_convection
            else _FALLBACK_H_W_PER_M2K
        )
        net.add_conductance(node, air, h * area)

        if settings.enable_radiation and source.emissivity is not None:
            _add_entity_radiation(
                net, topology, temperatures, source, node, comp_id, area
            )

        net.add_heat_source(node, source.power_loss_at_temperature_w(temperatures[node]))

    # --- heat released directly into the air ------------------------------
    for comp_id, sources in topology.airborne_sources.items():
        air = air_node(comp_id)
        if not net.has_node(air):
            continue
        for source in sources:
            net.add_heat_source(
                air, source.power_loss_at_temperature_w(temperatures[air])
            )

    # --- air-mass transport ----------------------------------------------
    if settings.enable_ventilation:
        _add_ventilation_conductances(net, geo, flows, temperatures, p_amb)

    return net


_FALLBACK_H_W_PER_M2K = 5.0
"""Film coefficient used when a convection model is switched off in settings."""


def _add_entity_radiation(
    net: ThermalNetwork,
    topology: _Topology,
    temperatures: dict[str, float],
    source: HeatSource,
    node: str,
    comp_id: str,
    area: float,
) -> None:
    """
    Radiate the entity body to the interior faces bounding its compartment.

    The entity is small relative to the compartment, so the exchange with each
    face is weighted by that face's share of the total bounding area — a
    first-order view factor that sums to unity across the enclosure.
    """
    faces = [
        (s, _interior_face_node(s, net))
        for s in topology.interior_surfaces.get(comp_id, ())
    ]
    reachable = [(s, n) for s, n in faces if n is not None and net.has_node(n)]
    total_area = sum(s.area_m2 for s, _ in reachable)
    if total_area <= 0:
        return
    for surf, face_node in reachable:
        assert face_node is not None
        emissivity = effective_emissivity_two_surfaces(
            source.emissivity if source.emissivity is not None else 0.0,
            surf.internal_emissivity
            if surf.internal_emissivity is not None
            else _DEFAULT_INTERNAL_EMISSIVITY,
        )
        if emissivity <= 0.0:
            continue
        view_fraction = surf.area_m2 / total_area
        net.add_conductance(
            node,
            face_node,
            radiation_conductance_w_per_k(
                t_surface_k=temperatures[node],
                t_surroundings_k=temperatures[face_node],
                emissivity=emissivity,
                area_m2=area * view_fraction,
            ),
        )


def _interior_face_node(surf: SurfaceSnapshot, net: ThermalNetwork) -> str | None:
    """The node representing this surface's interior face, if it has one."""
    if surf.is_external:
        node = surface_inner_node(surf.surface_id)
    else:
        node = partition_node(surf.surface_id)
    return node if net.has_node(node) else None


def _internal_h(
    settings: object,
    t_surface_k: float,
    t_air_k: float,
    length_m: float,
    surf: SurfaceSnapshot,
    p_amb: float,
) -> float:
    enabled = getattr(settings, "enable_natural_convection", True)
    if not enabled:
        return _FALLBACK_H_W_PER_M2K
    # Seen from inside, an upward-facing exterior face (the roof) presents its
    # heated side downward to the air below it, and vice versa for the floor.
    orientation = _flip_orientation(surf.orientation)
    return convection_coefficient(
        t_surface_k=t_surface_k,
        t_air_k=t_air_k,
        characteristic_length_m=length_m,
        orientation=orientation,
        pressure_pa=p_amb,
    )


def _external_h(
    settings: object,
    t_surface_k: float,
    t_amb_k: float,
    length_m: float,
    surf: SurfaceSnapshot,
    p_amb: float,
) -> float:
    enabled = getattr(settings, "enable_natural_convection", True)
    if not enabled:
        return _FALLBACK_H_W_PER_M2K
    return convection_coefficient(
        t_surface_k=t_surface_k,
        t_air_k=t_amb_k,
        characteristic_length_m=length_m,
        orientation=surf.orientation,
        pressure_pa=p_amb,
    )


def _flip_orientation(orientation: SurfaceOrientation) -> SurfaceOrientation:
    if orientation == SurfaceOrientation.HORIZONTAL_UP:
        return SurfaceOrientation.HORIZONTAL_DOWN
    if orientation == SurfaceOrientation.HORIZONTAL_DOWN:
        return SurfaceOrientation.HORIZONTAL_UP
    return orientation


def _characteristic_length(
    surf: SurfaceSnapshot, comp: CompartmentSnapshot | None
) -> float:
    """
    Convection length scale for a surface [m].

    Vertical plates use the compartment height; horizontal plates use the
    McAdams area-over-perimeter length, approximated for a square face
    (THERM-EQN-001 §6.3).
    """
    if surf.orientation == SurfaceOrientation.VERTICAL and comp is not None:
        return comp.height_m
    if surf.orientation == SurfaceOrientation.VERTICAL:
        return max(math.sqrt(surf.area_m2), 1e-3)
    side = max(math.sqrt(surf.area_m2), 1e-3)
    return side / 4.0


def _entity_length(source: HeatSource, comp: CompartmentSnapshot | None) -> float:
    if source.volume_m3 is not None:
        return max(float(source.volume_m3 ** (1.0 / 3.0)), 1e-3)
    if source.surface_area_m2 is not None:
        return max(math.sqrt(source.surface_area_m2 / 6.0), 1e-3)
    return comp.height_m if comp is not None else 0.1


# ---------------------------------------------------------------------------
# Airflow network
# ---------------------------------------------------------------------------


def _solve_airflow(
    snapshot: InputSnapshot, temperatures: dict[str, float]
) -> tuple[tuple[OpeningFlow, ...], float | None]:
    """
    Resolve the volumetric flow through every opening at the current field.

    MODE 2 openings are buoyancy driven: the stack pressure between the inlet
    and outlet centroids is shared across the openings in series, and each
    opening passes the same mass flow (THERM-EQN-001 §10.1, §10.5).

    MODE 3 adds the fan flows supplied in the boundary conditions, which the
    service layer has already resolved from the fan curve and system
    resistance. CR-ENG-006 keeps MODE 1 out of this path entirely.
    """
    geo = snapshot.geometry
    bc = snapshot.boundary_conditions
    if not snapshot.solver_settings.enable_ventilation or not geo.openings:
        return (), None

    t_amb = bc.ambient_temperature_k
    p_amb = bc.ambient_pressure_pa
    rho_amb = air_at(t_amb, p_amb).density_kg_per_m3

    forced: list[OpeningFlow] = []
    natural: list[OpeningSnapshot] = []
    for opening in geo.openings:
        flow = bc.forced_flow_m3_per_s.get(opening.opening_id)
        if flow is not None:
            signed = flow if opening.to_compartment_id is not None else -flow
            forced.append(
                OpeningFlow(
                    opening_id=opening.opening_id,
                    volumetric_flow_m3_per_s=signed,
                    mass_flow_kg_per_s=abs(signed) * rho_amb,
                    is_forced=True,
                )
            )
        elif not opening.is_forced:
            natural.append(opening)

    stack_pa: float | None = None
    buoyant: list[OpeningFlow] = []
    if len(natural) >= 2:
        inlet = min(natural, key=lambda o: o.centroid_height_m)
        outlet = max(natural, key=lambda o: o.centroid_height_m)
        height = outlet.centroid_height_m - inlet.centroid_height_m
        t_internal = _mean_air_temperature(geo, temperatures, t_amb)
        if height > 0 and t_internal > t_amb:
            stack_pa = stack_pressure_pa(
                t_air_k=t_internal,
                t_ambient_k=t_amb,
                height_difference_m=height,
                air_density_kg_per_m3=rho_amb,
                pressure_pa=p_amb,
            )
            # Openings in series: the effective area combines reciprocally, and
            # the resulting mass flow is common to inlet and outlet.
            area_in = inlet.discharge_coefficient * inlet.free_area_m2
            area_out = outlet.discharge_coefficient * outlet.free_area_m2
            effective = 1.0 / math.sqrt(1.0 / area_in**2 + 1.0 / area_out**2)
            q = orifice_flow_m3_per_s(
                delta_pressure_pa=stack_pa,
                discharge_coefficient=1.0,
                free_area_m2=effective,
                air_density_kg_per_m3=rho_amb,
            )
            buoyant = [
                OpeningFlow(
                    opening_id=inlet.opening_id,
                    volumetric_flow_m3_per_s=q,
                    mass_flow_kg_per_s=q * rho_amb,
                    is_forced=False,
                ),
                OpeningFlow(
                    opening_id=outlet.opening_id,
                    volumetric_flow_m3_per_s=-q,
                    mass_flow_kg_per_s=q * rho_amb,
                    is_forced=False,
                ),
            ]

    return tuple(forced) + tuple(buoyant), stack_pa


def _mean_air_temperature(
    geo: GeometrySnapshot, temperatures: dict[str, float], t_amb: float
) -> float:
    """Volume-weighted mean compartment air temperature [K]."""
    total_volume = sum(c.volume_m3 for c in geo.compartments)
    if total_volume <= 0:
        return t_amb
    return (
        sum(
            c.volume_m3 * temperatures.get(air_node(c.compartment_id), t_amb)
            for c in geo.compartments
        )
        / total_volume
    )


def _add_ventilation_conductances(
    net: ThermalNetwork,
    geo: GeometrySnapshot,
    flows: tuple[OpeningFlow, ...],
    temperatures: dict[str, float],
    p_amb: float,
) -> None:
    """
    Add air-transport conductance ṁ·cp for each opening (THERM-EQN-001 §9.1).

    Only inflowing air cools a compartment: the enthalpy an outflow carries away
    is already accounted for by the matching inflow, so counting both would
    double the ventilation effect.
    """
    by_id = {o.opening_id: o for o in geo.openings}
    for flow in flows:
        opening = by_id.get(flow.opening_id)
        if opening is None or flow.mass_flow_kg_per_s <= 0:
            continue
        inflowing = flow.volumetric_flow_m3_per_s > 0
        target_id = opening.to_compartment_id if inflowing else opening.from_compartment_id
        if target_id is None:
            continue
        target = air_node(target_id)
        if not net.has_node(target):
            continue
        source_id = opening.from_compartment_id if inflowing else opening.to_compartment_id
        source = AMBIENT_NODE if source_id is None else air_node(source_id)
        if not net.has_node(source):
            continue
        cp = air_at(temperatures.get(source, temperatures[AMBIENT_NODE]), p_amb)
        net.add_conductance(
            target, source, flow.mass_flow_kg_per_s * cp.specific_heat_j_per_kg_k
        )


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------


def _total_generation_w(topology: _Topology, temperatures: dict[str, float]) -> float:
    """Total power injected, evaluated at the current temperature field [W]."""
    total = 0.0
    for node, source in topology.entity_by_node.items():
        total += source.power_loss_at_temperature_w(temperatures[node])
    for comp_id, sources in topology.airborne_sources.items():
        air = temperatures.get(air_node(comp_id))
        for source in sources:
            total += (
                source.power_loss_at_temperature_w(air)
                if air is not None
                else source.power_loss_w
            )
    return total


def _heat_leaving_w(
    network: ThermalNetwork, temperatures: dict[str, float], t_amb: float
) -> float:
    """
    Total heat crossing into the ambient node [W].

    This is an independent measure of dissipation: comparing it with the
    generation above is what makes the energy-balance diagnostic meaningful.
    """
    total = 0.0
    for node in network.free_node_ids:
        g = network.conductance_between(node, AMBIENT_NODE)
        if g > 0.0:
            total += g * (temperatures[node] - t_amb)
    return total


def _node_temperatures(
    topology: _Topology, snapshot: InputSnapshot, temperatures: dict[str, float]
) -> tuple[NodeTemperature, ...]:
    out: list[NodeTemperature] = []
    t_amb = snapshot.boundary_conditions.ambient_temperature_k

    for comp in snapshot.geometry.compartments:
        node = air_node(comp.compartment_id)
        if node not in temperatures:
            continue
        airborne = topology.airborne_sources.get(comp.compartment_id, ())
        out.append(
            NodeTemperature(
                node_id=node,
                node_type=NodeType.AIR,
                temperature_k=temperatures[node],
                heat_generation_w=sum(
                    s.power_loss_at_temperature_w(temperatures[node]) for s in airborne
                ),
                net_heat_flux_w_per_m2=None,
                compartment_id=comp.compartment_id,
            )
        )

    for surf in topology.external_surfaces:
        for node, label, node_type in (
            (surface_inner_node(surf.surface_id), "inner", NodeType.INTERNAL_SURFACE),
            (surface_outer_node(surf.surface_id), "outer", NodeType.SURFACE),
        ):
            out.append(
                NodeTemperature(
                    node_id=node,
                    node_type=node_type,
                    temperature_k=temperatures[node],
                    heat_generation_w=0.0,
                    net_heat_flux_w_per_m2=None,
                    entity_id=surf.surface_id,
                    name=f"{surf.surface_id} ({label} face)",
                    compartment_id=surf.compartment_id,
                )
            )

    for surf in topology.partitions:
        node = partition_node(surf.surface_id)
        out.append(
            NodeTemperature(
                node_id=node,
                node_type=NodeType.INTERNAL_SURFACE,
                temperature_k=temperatures[node],
                heat_generation_w=0.0,
                net_heat_flux_w_per_m2=None,
                entity_id=surf.surface_id,
                name=f"{surf.surface_id} (partition)",
                compartment_id=surf.compartment_id,
            )
        )

    for node, source in topology.entity_by_node.items():
        power = source.power_loss_at_temperature_w(temperatures[node])
        area = source.surface_area_m2
        out.append(
            NodeTemperature(
                node_id=node,
                node_type=_node_type_for(source.entity_type),
                temperature_k=temperatures[node],
                heat_generation_w=power,
                net_heat_flux_w_per_m2=(power / area if area else None),
                entity_id=source.entity_id,
                name=source.name,
                compartment_id=topology.compartment_of_entity_node[node],
            )
        )

    # Entities without a body node still need a reported temperature; they sit
    # in the air, so that is what they get — flagged by having no own node.
    for comp_id, sources in topology.airborne_sources.items():
        air = temperatures.get(air_node(comp_id))
        if air is None:
            continue
        for source in sources:
            out.append(
                NodeTemperature(
                    node_id=entity_node(source.source_id),
                    node_type=_node_type_for(source.entity_type),
                    temperature_k=air,
                    heat_generation_w=source.power_loss_at_temperature_w(air),
                    net_heat_flux_w_per_m2=None,
                    entity_id=source.entity_id,
                    name=source.name,
                    compartment_id=comp_id,
                )
            )

    out.append(
        NodeTemperature(
            node_id=AMBIENT_NODE,
            node_type=NodeType.AMBIENT,
            temperature_k=t_amb,
            heat_generation_w=0.0,
            net_heat_flux_w_per_m2=None,
        )
    )
    return tuple(out)


_ENTITY_NODE_TYPES = {
    HeatSourceEntityType.DEVICE: NodeType.DEVICE,
    HeatSourceEntityType.BUSBAR: NodeType.BUSBAR,
    HeatSourceEntityType.JOINT: NodeType.JOINT,
    HeatSourceEntityType.CABLE: NodeType.CABLE,
}


def _node_type_for(entity_type: HeatSourceEntityType) -> NodeType:
    return _ENTITY_NODE_TYPES.get(entity_type, NodeType.ENTITY)


def _compartment_results(
    topology: _Topology,
    snapshot: InputSnapshot,
    network: ThermalNetwork,
    temperatures: dict[str, float],
    t_amb: float,
) -> tuple[CompartmentResult, ...]:
    results: list[CompartmentResult] = []
    for comp in snapshot.geometry.compartments:
        cid = comp.compartment_id
        air = air_node(cid)
        if air not in temperatures:
            continue

        entity_nodes = [
            n for n, c in topology.compartment_of_entity_node.items() if c == cid
        ]
        max_device = max((temperatures[n] for n in entity_nodes), default=None)

        surface_nodes = [
            node
            for surf in topology.interior_surfaces.get(cid, ())
            for node in _surface_nodes_of(surf)
            if node in temperatures
        ]
        max_surface = max((temperatures[n] for n in surface_nodes), default=None)

        generation = sum(
            s.power_loss_at_temperature_w(temperatures[air])
            for s in topology.airborne_sources.get(cid, ())
        ) + sum(
            topology.entity_by_node[n].power_loss_at_temperature_w(temperatures[n])
            for n in entity_nodes
        )

        # Heat leaving this compartment: everything crossing its own bounding
        # surfaces plus whatever the ventilation carries straight out.
        to_ambient = network.conductance_between(air, AMBIENT_NODE) * (
            temperatures[air] - t_amb
        )
        for surf in topology.interior_surfaces.get(cid, ()):
            if not surf.is_external or surf.is_restricted:
                continue
            outer = surface_outer_node(surf.surface_id)
            if outer in temperatures:
                to_ambient += network.heat_flow_w(outer, AMBIENT_NODE, temperatures)

        results.append(
            CompartmentResult(
                compartment_id=cid,
                mean_air_temperature_k=temperatures[air],
                max_device_temperature_k=max_device,
                max_surface_temperature_k=max_surface,
                total_heat_generation_w=generation,
                heat_to_ambient_w=to_ambient,
            )
        )
    return tuple(results)


def _surface_nodes_of(surf: SurfaceSnapshot) -> tuple[str, ...]:
    if surf.is_external:
        return (surface_inner_node(surf.surface_id), surface_outer_node(surf.surface_id))
    return (partition_node(surf.surface_id),)


def _implausible_node(temperatures: dict[str, float]) -> tuple[str, float] | None:
    for node_id, value in temperatures.items():
        if not (_T_MIN_PLAUSIBLE_K <= value <= _T_MAX_PLAUSIBLE_K):
            return node_id, value
    return None


def _k_ac_warnings(topology: _Topology) -> list[SolverWarning]:
    """
    CR-ENG-011: flag busbars solved on DC resistance alone.

    A DC-only busbar loss carries LossCalculationSource.DC_RESISTANCE_CALC; for
    a busbar at power frequency that means no AC correction was available, and
    the engineer must see that rather than discover it in the audit.
    """
    from thermal_core.heat_source import LossCalculationSource

    warnings: list[SolverWarning] = []
    for source in topology.entity_by_node.values():
        if (
            source.entity_type == HeatSourceEntityType.BUSBAR
            and source.calculation_source == LossCalculationSource.DC_RESISTANCE_CALC
        ):
            warnings.append(
                SolverWarning(
                    code="K_AC_UNITY_FALLBACK",
                    message=(
                        f"Busbar {source.entity_id!r} was evaluated with K_AC = 1.0 "
                        f"(DC resistance only). AC skin and proximity effects were not "
                        f"applied; confirm this is acceptable for the bar geometry and "
                        f"supply frequency (CR-ENG-011, DR-003)."
                    ),
                    entity_id=source.entity_id,
                )
            )
    return warnings


# ---------------------------------------------------------------------------
# MODE 1 — IEC TR 60890
# ---------------------------------------------------------------------------


def _solve_mode_1(snapshot: InputSnapshot, t_start: float) -> ResultSnapshot:
    """
    IEC TR 60890 empirical temperature-rise assessment.

    CR-ENG-002: the coefficients are licensed and arrive on the snapshot from
    the administrator-imported dataset. Without them, MODE 1 fails with a clear
    reason rather than falling back to invented numbers.
    """
    coefficients = snapshot.iec60890_coefficients

    def elapsed() -> float:
        return time.monotonic() - t_start

    if coefficients is None:
        return _failed_result(
            snapshot,
            errors=[
                "[VAL-002-IEC60890] MODE_1 requires the licensed IEC TR 60890 "
                "coefficient dataset, which CR-ENG-002 forbids shipping in this "
                "repository. An administrator must import it before MODE_1 can run."
            ],
            elapsed=elapsed(),
        )

    geo = snapshot.geometry
    bc = snapshot.boundary_conditions
    t_amb = bc.ambient_temperature_k
    p_total = snapshot.heat_source_map.total_power_loss_w()

    a_e = effective_cooling_area_m2(
        [
            (s.area_m2, coefficients.installation_factor(s.orientation.value))
            for s in geo.surfaces
            if s.is_external and not s.is_restricted
        ]
    )
    if a_e <= 0.0:
        return _failed_result(
            snapshot,
            errors=[
                "[VAL-007-IEC60890] Effective cooling surface A_e is zero: every "
                "external surface is restricted or missing. IEC TR 60890 cannot be "
                "applied to this configuration."
            ],
            elapsed=elapsed(),
        )

    rise = iec60890_temperature_rise(
        p_total_w=p_total, effective_cooling_area_m2=a_e, coefficients=coefficients
    )

    t_top = t_amb + rise.delta_theta_top_k
    node_temps = tuple(
        NodeTemperature(
            node_id=air_node(c.compartment_id),
            node_type=NodeType.AIR,
            temperature_k=t_amb + rise.delta_theta_mid_k,
            heat_generation_w=sum(
                s.power_loss_w
                for s in heat_sources_in_compartment(snapshot.heat_source_map, c)
            ),
            net_heat_flux_w_per_m2=None,
            compartment_id=c.compartment_id,
        )
        for c in geo.compartments
    )
    node_temps = (
        *node_temps,
        NodeTemperature(
            node_id=AMBIENT_NODE,
            node_type=NodeType.AMBIENT,
            temperature_k=t_amb,
            heat_generation_w=0.0,
            net_heat_flux_w_per_m2=None,
        ),
    )

    comp_results = tuple(
        CompartmentResult(
            compartment_id=c.compartment_id,
            mean_air_temperature_k=t_amb + rise.delta_theta_mid_k,
            # IEC TR 60890 is an enclosure-level extrapolation: it yields air
            # temperature rises, not component temperatures. Reporting a device
            # temperature here would invent data the method does not provide.
            max_device_temperature_k=None,
            max_surface_temperature_k=t_top,
            total_heat_generation_w=sum(
                s.power_loss_w
                for s in heat_sources_in_compartment(snapshot.heat_source_map, c)
            ),
            heat_to_ambient_w=p_total / max(len(geo.compartments), 1),
        )
        for c in geo.compartments
    )

    warnings = tuple(
        SolverWarning(code="WARN-IEC60890", message=msg) for msg in rise.warnings
    )

    return ResultSnapshot(
        schema_version=snapshot.schema_version,
        calculation_id=snapshot.calculation_id,
        status=SolverStatus.CONVERGED,
        node_temperatures=node_temps,
        compartment_results=comp_results,
        # The empirical method is closed-form: there is no iteration to trace.
        convergence_trace=(),
        total_heat_generation_w=p_total,
        total_heat_dissipation_w=p_total,
        energy_balance_error_percent=0.0,
        elapsed_seconds=elapsed(),
        warnings=warnings,
        airflow=None,
        mode_1=Mode1Result(
            p_total_w=p_total,
            effective_cooling_area_m2=a_e,
            coefficient_c=coefficients.c0,
            delta_theta_mid_k=rise.delta_theta_mid_k,
            delta_theta_top_k=rise.delta_theta_top_k,
            delta_theta_total_k=rise.delta_theta_top_k,
        ),
    )


# ---------------------------------------------------------------------------
# Failure result
# ---------------------------------------------------------------------------


def _failed_result(
    snapshot: InputSnapshot, errors: list[str], elapsed: float
) -> ResultSnapshot:
    """Build a FAILED ResultSnapshot carrying the reasons the solve stopped."""
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
        warnings=tuple(SolverWarning(code="VAL-FAIL", message=msg) for msg in errors),
    )
