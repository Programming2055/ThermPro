"""
Thermal conductance network assembly and linear solution.

This module owns the linear algebra of the nodal model described in
THERM-NET-001 §5. It knows nothing about enclosures, compartments or
standards — it assembles

    Σ_j G_ij · (T_j − T_i) + Q_i = 0        [W]      (THERM-EQN-001 §12)

into the sparse system G·T = b and solves it. The physics (which nodes
exist and what the conductances are) lives in `thermal_core.solver.iterative`,
which rebuilds the conductances from the current temperature field on every
outer iteration.

Nodes are either *free* (temperature is an unknown) or *fixed* (a boundary
node such as ambient, whose temperature is imposed).

Solution method: dense Gaussian elimination with partial pivoting. A
switchboard model has one air node per compartment, two nodes per external
wall and one per heat-generating entity — tens to low hundreds of nodes —
for which a dense direct solve costs microseconds to milliseconds and avoids
taking a numerical-library dependency into the engine (CR-TECH-001).

All conductances in W/K, all heat sources in W, all temperatures in kelvin
(CR-ENG-003, CR-ENG-013).
"""
from __future__ import annotations

from dataclasses import dataclass, field


class SingularNetworkError(ValueError):
    """
    Raised when the conductance matrix cannot be factorised.

    In practice this means a free node has no conductive path to any fixed
    node — an island in the network — which is a model-construction error,
    not a numerical accident (THERM-NET-001 §12).
    """


@dataclass
class ThermalNetwork:
    """
    A conductance network over named nodes.

    Usage::

        net = ThermalNetwork()
        net.add_fixed_node("ambient", 303.15)
        net.add_free_node("air_c1", initial_temperature_k=333.15)
        net.add_conductance("air_c1", "ambient", 4.2)
        net.add_heat_source("air_c1", 250.0)
        temperatures = net.solve()
    """

    _fixed: dict[str, float] = field(default_factory=dict, init=False)
    _free: dict[str, float] = field(default_factory=dict, init=False)
    _conductances: dict[tuple[str, str], float] = field(default_factory=dict, init=False)
    _sources: dict[str, float] = field(default_factory=dict, init=False)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def add_fixed_node(self, node_id: str, temperature_k: float) -> None:
        """Add a boundary node whose temperature is imposed, not solved."""
        if temperature_k <= 0:
            raise ValueError(
                f"fixed node {node_id!r} temperature must be > 0 K (CR-ENG-003); "
                f"got {temperature_k}"
            )
        self._reject_duplicate(node_id)
        self._fixed[node_id] = temperature_k

    def add_free_node(self, node_id: str, initial_temperature_k: float) -> None:
        """Add a node whose temperature is an unknown of the linear system."""
        if initial_temperature_k <= 0:
            raise ValueError(
                f"free node {node_id!r} initial temperature must be > 0 K (CR-ENG-003); "
                f"got {initial_temperature_k}"
            )
        self._reject_duplicate(node_id)
        self._free[node_id] = initial_temperature_k

    def add_conductance(self, node_a: str, node_b: str, conductance_w_per_k: float) -> None:
        """
        Add a conductive path between two nodes [W/K].

        Repeated calls for the same pair accumulate, which is how parallel
        paths (convection alongside radiation, say) are expressed.
        """
        if node_a == node_b:
            raise ValueError(f"self-conductance on node {node_a!r} is meaningless")
        for node in (node_a, node_b):
            if node not in self._free and node not in self._fixed:
                raise KeyError(f"unknown node {node!r}")
        if conductance_w_per_k < 0:
            raise ValueError(
                f"conductance between {node_a!r} and {node_b!r} must be >= 0 W/K; "
                f"got {conductance_w_per_k}"
            )
        if conductance_w_per_k == 0.0:
            return
        key = (node_a, node_b) if node_a < node_b else (node_b, node_a)
        self._conductances[key] = self._conductances.get(key, 0.0) + conductance_w_per_k

    def add_heat_source(self, node_id: str, power_w: float) -> None:
        """Inject power at a node [W]. Repeated calls accumulate."""
        if node_id not in self._free and node_id not in self._fixed:
            raise KeyError(f"unknown node {node_id!r}")
        self._sources[node_id] = self._sources.get(node_id, 0.0) + power_w

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    @property
    def free_node_ids(self) -> tuple[str, ...]:
        return tuple(self._free)

    @property
    def fixed_node_ids(self) -> tuple[str, ...]:
        return tuple(self._fixed)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._free or node_id in self._fixed

    def conductance_between(self, node_a: str, node_b: str) -> float:
        """Total conductance on the edge between two nodes [W/K]; 0 if unconnected."""
        key = (node_a, node_b) if node_a < node_b else (node_b, node_a)
        return self._conductances.get(key, 0.0)

    def heat_flow_w(self, node_a: str, node_b: str, temperatures: dict[str, float]) -> float:
        """
        Heat flowing from node_a to node_b at the given temperature field [W].

        Positive means heat leaves node_a.
        """
        return self.conductance_between(node_a, node_b) * (
            temperatures[node_a] - temperatures[node_b]
        )

    # ------------------------------------------------------------------
    # Solution
    # ------------------------------------------------------------------

    def solve(self) -> dict[str, float]:
        """
        Solve G·T = b for the free-node temperatures.

        Returns a mapping of every node id (free and fixed) to its temperature
        in kelvin. Fixed nodes are echoed unchanged so callers have a single
        complete temperature field to work with.

        Raises
        ------
        SingularNetworkError
            If the matrix is singular — typically a free node with no path to
            a boundary, or a free node with no conductances at all.
        """
        order = list(self._free)
        index = {node_id: i for i, node_id in enumerate(order)}
        n = len(order)

        if n == 0:
            return dict(self._fixed)

        matrix = [[0.0] * n for _ in range(n)]
        rhs = [0.0] * n

        for node_id, power_w in self._sources.items():
            if node_id in index:
                rhs[index[node_id]] += power_w

        for (node_a, node_b), g in self._conductances.items():
            a_free = node_a in index
            b_free = node_b in index
            if a_free and b_free:
                ia, ib = index[node_a], index[node_b]
                matrix[ia][ia] += g
                matrix[ib][ib] += g
                matrix[ia][ib] -= g
                matrix[ib][ia] -= g
            elif a_free:
                ia = index[node_a]
                matrix[ia][ia] += g
                rhs[ia] += g * self._fixed[node_b]
            elif b_free:
                ib = index[node_b]
                matrix[ib][ib] += g
                rhs[ib] += g * self._fixed[node_a]
            # both fixed: the edge carries heat but constrains nothing

        solution = _gaussian_solve(matrix, rhs, order)

        temperatures = dict(self._fixed)
        for node_id, value in zip(order, solution, strict=True):
            temperatures[node_id] = value
        return temperatures

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _reject_duplicate(self, node_id: str) -> None:
        if node_id in self._free or node_id in self._fixed:
            raise ValueError(f"node {node_id!r} is already in the network")


def _gaussian_solve(
    matrix: list[list[float]],
    rhs: list[float],
    node_order: list[str],
) -> list[float]:
    """
    Solve a dense linear system by Gaussian elimination with partial pivoting.

    `node_order` is used only to name the offending node in error messages.
    """
    n = len(rhs)
    # Work on copies: the caller's matrix may be reused across iterations.
    a = [row[:] for row in matrix]
    b = rhs[:]

    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot_row][col]) < 1e-14:
            raise SingularNetworkError(
                f"Thermal network is singular at node {node_order[col]!r}: it has no "
                f"conductive path to a boundary node. Check that every compartment, "
                f"surface and entity is connected to ambient (THERM-NET-001 §12)."
            )
        if pivot_row != col:
            a[col], a[pivot_row] = a[pivot_row], a[col]
            b[col], b[pivot_row] = b[pivot_row], b[col]

        inv_pivot = 1.0 / a[col][col]
        for row in range(col + 1, n):
            factor = a[row][col] * inv_pivot
            if factor == 0.0:
                continue
            for k in range(col, n):
                a[row][k] -= factor * a[col][k]
            b[row] -= factor * b[col]

    solution = [0.0] * n
    for row in range(n - 1, -1, -1):
        acc = b[row]
        for k in range(row + 1, n):
            acc -= a[row][k] * solution[k]
        solution[row] = acc / a[row][row]
    return solution
