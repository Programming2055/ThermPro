"""M4 validation — pre-solve input validation and engineering checks."""
from thermal_core.validation.pre_solve import (
    ValidationError,
    ValidationResult,
    validate_input_snapshot,
)

__all__ = ["ValidationError", "ValidationResult", "validate_input_snapshot"]
