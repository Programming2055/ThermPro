"""
Domain type definitions for thermpro_engine.

These types are shared between the engine, API, and frontend contracts.
No FastAPI, SQLAlchemy, or HTTP dependencies are permitted in this module.
"""
from enum import Enum


class CalculationMode(str, Enum):
    """Supported calculation modes. ARC_FLASH is not in MVP scope (DR-008)."""

    MODE_1 = "MODE_1"
    MODE_2 = "MODE_2"
    MODE_3 = "MODE_3"
    MODE_4 = "MODE_4"


class StandardProfile(str, Enum):
    """Standards profiles in MVP scope. UL/ANSI deferred to Phase 3 (DR-007)."""

    IEC_61439_1 = "IEC_61439_1"
    IEC_61439_2 = "IEC_61439_2"
    IEC_TR_60890 = "IEC_TR_60890"
    MANUFACTURER_LIMITS = "MANUFACTURER_LIMITS"
    PROJECT_DEFINED = "PROJECT_DEFINED"


class FanOperatingState(str, Enum):
    """
    Fan operating states per DR-005.

    Six states replace the previous boolean 'operating' flag.
    Reverse flow must NOT be clamped to zero without a physical damper.
    """

    RUNNING_FORWARD = "RUNNING_FORWARD"
    STOPPED_FREE_FLOW = "STOPPED_FREE_FLOW"
    STOPPED_WITH_DAMPER = "STOPPED_WITH_DAMPER"
    FAILED_OPEN = "FAILED_OPEN"
    FAILED_BLOCKED = "FAILED_BLOCKED"
    REVERSE_FLOW_ESTIMATED = "REVERSE_FLOW_ESTIMATED"


class JointCondition(str, Enum):
    """
    Busbar joint condition enum per DR-004.

    UNKNOWN condition requires sensitivity scenarios; single-value
    computation is not permitted.
    """

    NEW_VALIDATED = "NEW_VALIDATED"
    NEW_ASSUMED = "NEW_ASSUMED"
    MEASURED = "MEASURED"
    AGED = "AGED"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class ContactResistanceSource(str, Enum):
    """Data hierarchy for contact resistance per DR-004."""

    MEASURED = "MEASURED"
    MANUFACTURER = "MANUFACTURER"
    JOINT_LIBRARY = "JOINT_LIBRARY"
    USER_ASSUMPTION = "USER_ASSUMPTION"


class KAcSource(str, Enum):
    """Source of K_AC correction factor per DR-003."""

    MANUFACTURER = "MANUFACTURER"
    VALIDATED_CORRELATION = "VALIDATED_CORRELATION"
    GEOMETRY_FREQUENCY_LIBRARY = "GEOMETRY_FREQUENCY_LIBRARY"
    USER_INPUT = "USER_INPUT"
    NOT_APPLIED = "NOT_APPLIED"


class LibraryStatus(str, Enum):
    """Library release status per DR-002 / M0-09."""

    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"


class CalculationRunStatus(str, Enum):
    """Calculation run lifecycle status."""

    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    REJECTED = "REJECTED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ENGINE_NOT_IMPLEMENTED = "ENGINE_NOT_IMPLEMENTED"
