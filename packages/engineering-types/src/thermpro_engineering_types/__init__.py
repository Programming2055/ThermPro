"""
Shared engineering domain types for ThermPro.

Re-exports all domain type enums from thermal_core.domain_types so that
API, frontend contracts, and other packages can import from a stable
top-level namespace without depending on thermpro-engine directly.
"""
from thermal_core.domain_types import (
    CalculationMode,
    StandardProfile,
    FanOperatingState,
    JointCondition,
    ContactResistanceSource,
    KAcSource,
    LibraryStatus,
    CalculationRunStatus,
)

__all__ = [
    "CalculationMode",
    "StandardProfile",
    "FanOperatingState",
    "JointCondition",
    "ContactResistanceSource",
    "KAcSource",
    "LibraryStatus",
    "CalculationRunStatus",
]
