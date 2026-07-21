"""
Convergence tracking and energy balance audit for the M4 zonal solver.

The solver calls these utilities every iteration to record:
  - max |ΔT| across all nodes
  - RMS |ΔT| across all nodes
  - global energy balance error |Q_in - Q_out| [W and %]

CR-ENG-005: if convergence is not achieved within max_iterations, the solver
must return status=NON_CONVERGED — it must not raise an exception or return
temperatures without flagging them as invalid.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from thermal_core.result import ConvergenceTrace


@dataclass
class ConvergenceMonitor:
    """
    Mutable accumulator for convergence history during iteration.

    Each call to `record` appends one ConvergenceTrace row.
    After the solver loop, `to_trace` returns the immutable tuple.
    """
    tolerance_k: float
    _history: list[ConvergenceTrace] = field(default_factory=list, init=False)

    def record(
        self,
        iteration: int,
        t_old: list[float],
        t_new: list[float],
        q_in_w: float,
        q_out_w: float,
        ua_total_w_per_k: Optional[float] = None,
    ) -> ConvergenceTrace:
        """
        Record iteration diagnostics and return the trace row.

        Parameters
        ----------
        iteration:
            Iteration index (0-based).
        t_old, t_new:
            Node temperature vectors from the previous and current iteration [K].
        q_in_w:
            Total heat generation [W] — sum of all source power.
        q_out_w:
            Total heat dissipation [W] — sum of all surface losses.
        ua_total_w_per_k:
            Optional total thermal conductance for diagnostics [W/K].
        """
        if len(t_old) != len(t_new):
            raise ValueError("t_old and t_new must have the same length")
        deltas = [abs(n - o) for n, o in zip(t_new, t_old)]
        max_dt = max(deltas) if deltas else 0.0
        rms_dt = math.sqrt(sum(d * d for d in deltas) / len(deltas)) if deltas else 0.0
        eb_err = abs(q_in_w - q_out_w)

        trace = ConvergenceTrace(
            iteration=iteration,
            max_delta_k=max_dt,
            rms_delta_k=rms_dt,
            energy_balance_error_w=eb_err,
            ua_total_w_per_k=ua_total_w_per_k,
        )
        self._history.append(trace)
        return trace

    def is_converged(self, trace: ConvergenceTrace) -> bool:
        """Return True if the latest trace row meets the convergence criterion."""
        return trace.max_delta_k < self.tolerance_k

    def to_trace(self) -> tuple[ConvergenceTrace, ...]:
        """Return the full immutable convergence history."""
        return tuple(self._history)


def energy_balance_error_w(q_in_w: float, q_out_w: float) -> float:
    """
    Absolute global energy balance error |Q_in - Q_out| [W].

    A perfectly converged solution has zero energy balance error.
    In practice, values < 0.1 W are acceptable for switchboard analysis.
    """
    return abs(q_in_w - q_out_w)


def energy_balance_error_percent(q_in_w: float, q_out_w: float) -> float:
    """
    Relative global energy balance error |Q_in - Q_out| / Q_in × 100 [%].

    Returns 0.0 if Q_in is zero (no heat generation).
    """
    if q_in_w == 0.0:
        return 0.0
    return 100.0 * abs(q_in_w - q_out_w) / abs(q_in_w)
