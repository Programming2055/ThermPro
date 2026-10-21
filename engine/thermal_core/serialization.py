"""
JSON-compatible serialisation of solver results (CR-TECH-001).

The engine returns versioned JSON; this module has no framework dependency.
Temperatures stay in kelvin (CR-ENG-003); consumers convert at the boundary.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from thermal_core.result import ResultSnapshot


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, (tuple, list)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    return value


def result_to_dict(result: ResultSnapshot) -> dict[str, Any]:
    """Convert a ResultSnapshot to plain JSON types, adding the derived ``is_valid`` flag."""
    out: dict[str, Any] = _plain(result)
    out["is_valid"] = result.is_valid
    return out
