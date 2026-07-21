"""
Pre-solve validation of InputSnapshot.

These checks run before the solver starts and catch engineering errors that
would cause silent bad results:
  - Schema version present (CR-TECH-002)
  - Ambient temperature > 0 K and plausible (CR-ENG-003)
  - Geometry consistency (compartments reference valid surfaces)
  - CR-ENG-006: MODE_1 must not be used with forced ventilation
  - CR-ENG-005: solver must always return a result (no raise on convergence fail)
  - CR-ENG-013: all values in SI

A failed validation means the solver MUST NOT run and must return
status=FAILED in the ResultSnapshot.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from thermal_core.snapshot import CalculationMode, InputSnapshot


# ---------------------------------------------------------------------------
# Validation result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationError:
    """One engineering validation error."""
    code: str       # e.g. "VAL-006-MODE1-FORCED"
    message: str
    entity_id: str = ""


@dataclass(frozen=True)
class ValidationResult:
    """Collection of all pre-solve validation errors."""
    errors: tuple[ValidationError, ...]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------


def validate_input_snapshot(snapshot: InputSnapshot) -> ValidationResult:
    """
    Run all pre-solve engineering validation checks on an InputSnapshot.

    Returns a ValidationResult.  If result.is_valid is False, the caller
    must not invoke the solver.

    Checks performed:
      VAL-001: schema_version present (CR-TECH-002)
      VAL-002: library_manifest present (CR-TECH-002)
      VAL-003: calculation_id present
      VAL-004: ambient_temperature_k in plausible range (233 K to 373 K)
      VAL-005: geometry has at least one compartment
      VAL-006: MODE_1 disabled when any forced opening present (CR-ENG-006)
      VAL-007: all compartment surface_ids reference existing surfaces
      VAL-008: all compartment heat_source_ids reference existing heat sources
      VAL-009: total heat generation >= 0 W
      VAL-010: max_iterations >= 1 and convergence_tolerance_k > 0
    """
    errors: list[ValidationError] = []

    _check_schema(snapshot, errors)
    _check_boundary_conditions(snapshot, errors)
    _check_geometry(snapshot, errors)
    _check_mode_6(snapshot, errors)
    _check_heat_sources(snapshot, errors)
    _check_solver_settings(snapshot, errors)

    return ValidationResult(errors=tuple(errors))


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def _check_schema(snap: InputSnapshot, errors: list[ValidationError]) -> None:
    if not snap.schema_version:
        errors.append(ValidationError(
            code="VAL-001",
            message="InputSnapshot.schema_version must not be empty (CR-TECH-002)",
        ))
    if not snap.library_manifest:
        errors.append(ValidationError(
            code="VAL-002",
            message="InputSnapshot.library_manifest must not be empty (CR-TECH-002)",
        ))
    if not snap.calculation_id:
        errors.append(ValidationError(
            code="VAL-003",
            message="InputSnapshot.calculation_id must not be empty",
        ))


def _check_boundary_conditions(snap: InputSnapshot, errors: list[ValidationError]) -> None:
    bc = snap.boundary_conditions
    # IEC 61439-1 Table 2: ambient range -5 °C to +40 °C (268.15 K to 313.15 K)
    # We apply a slightly wider guard: -40 °C to +100 °C (233 K to 373 K)
    T_amb = bc.ambient_temperature_k
    if not (233.0 <= T_amb <= 373.0):
        errors.append(ValidationError(
            code="VAL-004",
            message=(
                f"ambient_temperature_k = {T_amb} K is outside the plausible range "
                f"[233 K, 373 K] (−40 °C to +100 °C). CR-ENG-003: use kelvin."
            ),
        ))


def _check_geometry(snap: InputSnapshot, errors: list[ValidationError]) -> None:
    geo = snap.geometry
    if not geo.compartments:
        errors.append(ValidationError(
            code="VAL-005",
            message="GeometrySnapshot must have at least one compartment",
        ))
        return

    surface_ids = {s.surface_id for s in geo.surfaces}
    for comp in geo.compartments:
        for sid in comp.surface_ids:
            if sid not in surface_ids:
                errors.append(ValidationError(
                    code="VAL-007",
                    message=(
                        f"Compartment {comp.compartment_id!r} references "
                        f"surface {sid!r} which does not exist in geometry.surfaces"
                    ),
                    entity_id=comp.compartment_id,
                ))


def _check_mode_6(snap: InputSnapshot, errors: list[ValidationError]) -> None:
    """CR-ENG-006: MODE_1 must not be used when forced ventilation is present."""
    if snap.solver_settings.calculation_mode != CalculationMode.MODE_1:
        return
    has_forced = any(o.is_forced for o in snap.geometry.openings)
    if has_forced:
        errors.append(ValidationError(
            code="VAL-006",
            message=(
                "CR-ENG-006: CalculationMode.MODE_1 (IEC TR 60890 empirical) is "
                "automatically disabled when forced ventilation openings are present. "
                "Use MODE_3 for forced ventilation."
            ),
        ))


def _check_heat_sources(snap: InputSnapshot, errors: list[ValidationError]) -> None:
    source_ids = {s.source_id for s in snap.heat_source_map.sources}
    for comp in snap.geometry.compartments:
        for sid in comp.heat_source_ids:
            if sid not in source_ids:
                errors.append(ValidationError(
                    code="VAL-008",
                    message=(
                        f"Compartment {comp.compartment_id!r} references "
                        f"heat_source {sid!r} which does not exist in heat_source_map"
                    ),
                    entity_id=comp.compartment_id,
                ))

    if snap.heat_source_map.total_power_loss_w() < 0:
        errors.append(ValidationError(
            code="VAL-009",
            message="Total heat generation must be >= 0 W",
        ))


def _check_solver_settings(snap: InputSnapshot, errors: list[ValidationError]) -> None:
    ss = snap.solver_settings
    if ss.max_iterations < 1:
        errors.append(ValidationError(
            code="VAL-010",
            message=f"SolverSettings.max_iterations must be >= 1; got {ss.max_iterations}",
        ))
    if ss.convergence_tolerance_k <= 0:
        errors.append(ValidationError(
            code="VAL-010",
            message=(
                f"SolverSettings.convergence_tolerance_k must be > 0 K; "
                f"got {ss.convergence_tolerance_k}"
            ),
        ))
