"""
Tests for geometry domain types in thermal_core.geometry.

Covers:
- Point3D creation
- Dimensions3D validation (rejects zero and negative values)
- BoundingBox.contains_point (inside and outside)
- BoundingBox.overlaps (true and false)
- SurfaceFace six-member check
- CompartmentType six-member check
- ValidationSeverity four-level check
- COORDINATE_SYSTEM_VERSION type check
"""
import pytest

from thermal_core.geometry import (
    COORDINATE_SYSTEM_VERSION,
    BoundingBox,
    CompartmentType,
    CoordinateSystem,
    Dimensions3D,
    GeometryValidationIssue,
    InstallationType,
    InternalOpeningDirection,
    OpeningDirection,
    PartitionOrientation,
    Point3D,
    SurfaceFace,
    ValidationSeverity,
)


# ---------------------------------------------------------------------------
# Point3D
# ---------------------------------------------------------------------------


def test_point3d_creation() -> None:
    p = Point3D(x=1.0, y=2.5, z=0.0)
    assert p.x == 1.0
    assert p.y == 2.5
    assert p.z == 0.0


def test_point3d_negative_coordinates_allowed() -> None:
    """Points can have negative coordinates (relative positions inside an enclosure)."""
    p = Point3D(x=-0.1, y=-0.2, z=-0.3)
    assert p.x == pytest.approx(-0.1)


# ---------------------------------------------------------------------------
# Dimensions3D
# ---------------------------------------------------------------------------


def test_dimensions3d_valid() -> None:
    d = Dimensions3D(width=0.6, height=2.0, depth=0.3)
    assert d.width == pytest.approx(0.6)
    assert d.height == pytest.approx(2.0)
    assert d.depth == pytest.approx(0.3)


def test_dimensions3d_rejects_zero_width() -> None:
    with pytest.raises(ValueError, match="width"):
        Dimensions3D(width=0.0, height=1.0, depth=0.5)


def test_dimensions3d_rejects_negative() -> None:
    with pytest.raises(ValueError, match="height"):
        Dimensions3D(width=1.0, height=-0.5, depth=0.5)


def test_dimensions3d_rejects_zero_depth() -> None:
    with pytest.raises(ValueError, match="depth"):
        Dimensions3D(width=1.0, height=1.0, depth=0.0)


def test_dimensions3d_rejects_negative_depth() -> None:
    with pytest.raises(ValueError, match="depth"):
        Dimensions3D(width=1.0, height=1.0, depth=-1.0)


# ---------------------------------------------------------------------------
# BoundingBox — contains_point
# ---------------------------------------------------------------------------


def _unit_box(ox: float = 0.0, oy: float = 0.0, oz: float = 0.0) -> BoundingBox:
    """Return a 1 m × 1 m × 1 m box with origin at (ox, oy, oz)."""
    return BoundingBox(
        origin=Point3D(x=ox, y=oy, z=oz),
        dimensions=Dimensions3D(width=1.0, height=1.0, depth=1.0),
    )


def test_bounding_box_contains_point_inside() -> None:
    box = _unit_box()
    assert box.contains_point(Point3D(x=0.5, y=0.5, z=0.5)) is True


def test_bounding_box_contains_point_on_face() -> None:
    """A point exactly on a face is considered inside (inclusive boundary)."""
    box = _unit_box()
    assert box.contains_point(Point3D(x=0.0, y=0.0, z=0.0)) is True
    assert box.contains_point(Point3D(x=1.0, y=1.0, z=1.0)) is True


def test_bounding_box_contains_point_outside() -> None:
    box = _unit_box()
    assert box.contains_point(Point3D(x=1.5, y=0.5, z=0.5)) is False


def test_bounding_box_contains_point_outside_negative() -> None:
    box = _unit_box()
    assert box.contains_point(Point3D(x=-0.1, y=0.5, z=0.5)) is False


# ---------------------------------------------------------------------------
# BoundingBox — overlaps
# ---------------------------------------------------------------------------


def test_bounding_box_overlaps_true() -> None:
    """Two partially overlapping boxes."""
    box_a = _unit_box(0.0, 0.0, 0.0)
    box_b = _unit_box(0.5, 0.5, 0.5)
    assert box_a.overlaps(box_b) is True
    assert box_b.overlaps(box_a) is True


def test_bounding_box_overlaps_touching_face() -> None:
    """Boxes that share a face are considered overlapping (inclusive)."""
    box_a = _unit_box(0.0, 0.0, 0.0)
    box_b = _unit_box(1.0, 0.0, 0.0)  # right face of a == left face of b
    assert box_a.overlaps(box_b) is True


def test_bounding_box_overlaps_false() -> None:
    """Boxes separated by a gap do not overlap."""
    box_a = _unit_box(0.0, 0.0, 0.0)
    box_b = _unit_box(2.0, 0.0, 0.0)  # gap of 1 m on X axis
    assert box_a.overlaps(box_b) is False
    assert box_b.overlaps(box_a) is False


def test_bounding_box_overlaps_false_on_y() -> None:
    box_a = _unit_box(0.0, 0.0, 0.0)
    box_b = _unit_box(0.0, 5.0, 0.0)
    assert box_a.overlaps(box_b) is False


# ---------------------------------------------------------------------------
# SurfaceFace
# ---------------------------------------------------------------------------


def test_surface_face_six_values() -> None:
    faces = list(SurfaceFace)
    assert len(faces) == 6
    assert SurfaceFace.FRONT in faces
    assert SurfaceFace.REAR in faces
    assert SurfaceFace.LEFT in faces
    assert SurfaceFace.RIGHT in faces
    assert SurfaceFace.TOP in faces
    assert SurfaceFace.BOTTOM in faces


# ---------------------------------------------------------------------------
# CompartmentType
# ---------------------------------------------------------------------------


def test_compartment_type_six_values() -> None:
    types = list(CompartmentType)
    assert len(types) == 6
    assert CompartmentType.DEVICE_CHAMBER in types
    assert CompartmentType.BUSBAR_CHAMBER in types
    assert CompartmentType.CABLE_CHAMBER in types
    assert CompartmentType.AUXILIARY_CHAMBER in types
    assert CompartmentType.VENTILATION_CHAMBER in types
    assert CompartmentType.CUSTOM in types


# ---------------------------------------------------------------------------
# ValidationSeverity
# ---------------------------------------------------------------------------


def test_validation_severity_four_levels() -> None:
    levels = list(ValidationSeverity)
    assert len(levels) == 4
    assert ValidationSeverity.INFO in levels
    assert ValidationSeverity.WARNING in levels
    assert ValidationSeverity.ERROR in levels
    assert ValidationSeverity.BLOCKER in levels


# ---------------------------------------------------------------------------
# COORDINATE_SYSTEM_VERSION
# ---------------------------------------------------------------------------


def test_coordinate_system_version_is_string() -> None:
    assert isinstance(COORDINATE_SYSTEM_VERSION, str)
    assert len(COORDINATE_SYSTEM_VERSION) > 0


# ---------------------------------------------------------------------------
# CoordinateSystem
# ---------------------------------------------------------------------------


def test_coordinate_system_creation() -> None:
    cs = CoordinateSystem(
        version=COORDINATE_SYSTEM_VERSION,
        origin_description="bottom-left-front corner of the enclosure base plate",
    )
    assert cs.version == COORDINATE_SYSTEM_VERSION
    assert "bottom" in cs.origin_description


# ---------------------------------------------------------------------------
# Enum completeness spot-checks
# ---------------------------------------------------------------------------


def test_partition_orientation_three_values() -> None:
    assert len(list(PartitionOrientation)) == 3


def test_opening_direction_four_values() -> None:
    assert len(list(OpeningDirection)) == 4


def test_internal_opening_direction_three_values() -> None:
    assert len(list(InternalOpeningDirection)) == 3


def test_installation_type_four_values() -> None:
    assert len(list(InstallationType)) == 4


# ---------------------------------------------------------------------------
# GeometryValidationIssue
# ---------------------------------------------------------------------------


def test_geometry_validation_issue_creation() -> None:
    issue = GeometryValidationIssue(
        issue_id="GVI-001",
        severity=ValidationSeverity.ERROR,
        entity_type="BoundingBox",
        entity_id="bb-compartment-1",
        message="Compartment bounding box extends beyond enclosure boundary.",
        coordinate_ref=Point3D(x=0.65, y=0.3, z=1.8),
        suggested_fix="Reduce compartment height to fit within enclosure.",
        rule_id="GEO-002",
    )
    assert issue.severity == ValidationSeverity.ERROR
    assert issue.coordinate_ref is not None
    assert issue.coordinate_ref.z == pytest.approx(1.8)


def test_geometry_validation_issue_optional_fields_none() -> None:
    issue = GeometryValidationIssue(
        issue_id="GVI-002",
        severity=ValidationSeverity.INFO,
        entity_type="Partition",
        entity_id="part-01",
        message="Partition has zero area on one axis.",
        coordinate_ref=None,
        suggested_fix=None,
        rule_id="GEO-010",
    )
    assert issue.coordinate_ref is None
    assert issue.suggested_fix is None
