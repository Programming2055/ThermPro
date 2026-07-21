"""
M4 benchmarks — analytical and IEC TR 60890 validation frameworks.

Usage:
  - analytical.py: exact solutions for simple cases (sanity checks)
  - iec60890.py: IEC TR 60890 empirical method for Mode 1 validation

Per CLAUDE.md CR-TECH-003 and M0-05:
  - The De Vahl Davis cavity benchmark (BM-007) is a periodic physics verification
    test, NOT a mandatory CI gate.  It is run pre-release only.
  - The benchmarks here are EVERY-PUSH gates (BM-001 through BM-006).
"""
from thermal_core.benchmarks.analytical import (
    conduction_through_plate,
    convection_cooling,
    radiation_exchange,
    BenchmarkResult,
)

__all__ = [
    "conduction_through_plate",
    "convection_cooling",
    "radiation_exchange",
    "BenchmarkResult",
]
