"""
Engine interfaces for thermpro_engine.

These abstract interfaces decouple the numerical solver from the API layer.
Milestone 1: All solver methods raise NotImplementedError.
Transient interfaces are reserved but not exposed (DR-006).
"""
from __future__ import annotations

import abc
from typing import Any


class ThermalSolverInterface(abc.ABC):
    """Abstract interface for the thermal solver."""

    @abc.abstractmethod
    def solve(self, input_snapshot: dict[str, Any]) -> dict[str, Any]:
        """
        Run the thermal solver on a validated InputSnapshot.

        Args:
            input_snapshot: Validated InputSnapshot dict (schema_version required).

        Returns:
            ResultSnapshot dict.

        Raises:
            NotImplementedError: Until the solver is implemented (M2+).
        """
        raise NotImplementedError


class NotImplementedSolver(ThermalSolverInterface):
    """
    Placeholder solver for Milestone 1.

    Returns ENGINE_NOT_IMPLEMENTED status without computing temperatures.
    This is the correct behaviour: do NOT return fabricated results.
    """

    def solve(self, input_snapshot: dict[str, Any]) -> dict[str, Any]:
        schema_version = input_snapshot.get("schema_version", "1.0")
        mode = input_snapshot.get("mode", "UNKNOWN")
        return {
            "schema_version": schema_version,
            "status": "ENGINE_NOT_IMPLEMENTED",
            "mode": mode,
            "message": (
                "Thermal solver not yet implemented. "
                "Milestone 1 platform foundation only. "
                "No thermal results have been computed."
            ),
        }
