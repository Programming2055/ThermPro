"""
JSON Schema validation for InputSnapshot and ResultSnapshot.

Uses the exact schemas from docs/engineering/M0-03 and M0-04.
Schema version "1.0" is the only supported version.
Missing library_manifest, invalid mode, or invalid fan state are rejected.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

import jsonschema
import jsonschema.validators

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}
_SCHEMA_DIR = pathlib.Path(__file__).parent / "schemas"


class SchemaValidationError(ValueError):
    """Raised when an InputSnapshot or ResultSnapshot fails schema validation."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


def _load_schema(filename: str) -> dict[str, Any]:
    path = _SCHEMA_DIR / filename
    with open(path, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def _validate(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = list(validator.iter_errors(instance))
    if errors:
        messages = [e.message for e in errors]
        raise SchemaValidationError(
            f"Schema validation failed ({len(errors)} error(s)): {messages[0]}",
            errors=messages,
        )


def validate_input_snapshot(data: dict[str, Any]) -> None:
    """
    Validate an InputSnapshot dict against M0-03 JSON Schema.

    Raises:
        SchemaValidationError: If validation fails, schema_version is missing,
            or schema_version is not supported.
    """
    version = data.get("schema_version")
    if version is None:
        raise SchemaValidationError(
            "InputSnapshot missing required field 'schema_version'. "
            f"Supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise SchemaValidationError(
            f"Unsupported schema_version '{version}'. "
            f"Supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    schema = _load_schema("M0-03-calculation-input-schema.json")
    _validate(data, schema)


def validate_result_snapshot(data: dict[str, Any]) -> None:
    """
    Validate a ResultSnapshot dict against M0-04 JSON Schema.

    Raises:
        SchemaValidationError: If validation fails.
    """
    version = data.get("schema_version")
    if version is None:
        raise SchemaValidationError("ResultSnapshot missing required field 'schema_version'.")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise SchemaValidationError(
            f"Unsupported schema_version '{version}'. "
            f"Supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )
    schema = _load_schema("M0-04-calculation-result-schema.json")
    _validate(data, schema)
