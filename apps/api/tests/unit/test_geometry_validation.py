"""Unit tests for the geometry validation service (GEO-001 through GEO-016).

These tests use MagicMock objects instead of real ORM instances to avoid
SQLAlchemy mapper requirements in unit tests.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from thermpro_api.models.geometry import (
    BusbarPlacement,
    Compartment,
    DevicePlacement,
    Enclosure,
    ExternalOpening,
    InternalOpening,
    Partition,
)
from thermpro_api.services.geometry_validation import validate_enclosure_geometry


def _enc(w: float = 1.0, h: float = 2.0, d: float = 0.8) -> Enclosure:
    e = MagicMock(spec=Enclosure)
    e.internal_width_m = w
    e.internal_height_m = h
    e.internal_depth_m = d
    return e


def _comp(
    name: str = "C1",
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    w: float = 0.5,
    h: float = 1.0,
    d: float = 0.4,
    ctype: str = "DEVICE_CHAMBER",
    parent_id: uuid.UUID | None = None,
) -> Compartment:
    c = MagicMock(spec=Compartment)
    c.id = uuid.uuid4()
    c.name = name
    c.compartment_type = ctype
    c.parent_compartment_id = parent_id
    c.position_x_m = x
    c.position_y_m = y
    c.position_z_m = z
    c.width_m = w
    c.height_m = h
    c.depth_m = d
    return c


def _dev(
    name: str = "D1",
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    w: float = 0.1,
    h: float = 0.2,
    d: float = 0.1,
    compartment_id: uuid.UUID | None = None,
) -> DevicePlacement:
    dev = MagicMock(spec=DevicePlacement)
    dev.id = uuid.uuid4()
    dev.name = name
    dev.position_x_m = x
    dev.position_y_m = y
    dev.position_z_m = z
    dev.width_m = w
    dev.height_m = h
    dev.depth_m = d
    dev.compartment_id = compartment_id
    return dev


def _bus(
    name: str = "B1",
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    w: float = 0.05,
    t: float = 0.01,
    length: float = 0.5,
    compartment_id: uuid.UUID | None = None,
) -> BusbarPlacement:
    b = MagicMock(spec=BusbarPlacement)
    b.id = uuid.uuid4()
    b.name = name
    b.position_x_m = x
    b.position_y_m = y
    b.position_z_m = z
    b.width_m = w
    b.thickness_m = t
    b.length_m = length
    b.compartment_id = compartment_id
    return b


def _ext_opening(
    name: str = "EO1",
    open_area: float = 0.6,
    cd: float = 0.61,
) -> ExternalOpening:
    o = MagicMock(spec=ExternalOpening)
    o.id = uuid.uuid4()
    o.name = name
    o.open_area_fraction = open_area
    o.discharge_coefficient = cd
    return o


def _int_opening(
    name: str = "IO1",
    open_area: float = 1.0,
    cd: float = 0.61,
) -> InternalOpening:
    io = MagicMock(spec=InternalOpening)
    io.id = uuid.uuid4()
    io.name = name
    io.open_area_fraction = open_area
    io.discharge_coefficient = cd
    return io


def _part(
    name: str = "P1",
    orientation: str = "VERTICAL_YZ",
    x: float = 0.5,
    y: float = 0.0,
    z: float = 0.0,
    w: float = 0.8,
    h: float = 2.0,
    t: float = 0.001,
) -> Partition:
    p = MagicMock(spec=Partition)
    p.id = uuid.uuid4()
    p.name = name
    p.orientation = orientation
    p.position_x_m = x
    p.position_y_m = y
    p.position_z_m = z
    p.width_m = w
    p.height_m = h
    p.thickness_m = t
    return p


def run(
    enc: Enclosure | None = None,
    compartments: list[Compartment] | None = None,
    partitions: list[Partition] | None = None,
    devices: list[DevicePlacement] | None = None,
    busbars: list[BusbarPlacement] | None = None,
    ext_openings: list[ExternalOpening] | None = None,
    int_openings: list[InternalOpening] | None = None,
) -> list[dict]:
    return validate_enclosure_geometry(
        enc or _enc(),
        compartments or [],
        partitions or [],
        devices or [],
        busbars or [],
        ext_openings or [],
        int_openings or [],
    )


# ── GEO-001: Compartment positive dimensions ──────────────────────────────────

def test_geo001_zero_width_raises_error() -> None:
    c = _comp(w=0.0)
    issues = run(compartments=[c])
    rule_ids = [i["rule_id"] for i in issues]
    assert "GEO-001" in rule_ids


def test_geo001_negative_height_raises_error() -> None:
    c = _comp(h=-0.1)
    issues = run(compartments=[c])
    assert any(i["rule_id"] == "GEO-001" for i in issues)


# ── GEO-002: Compartment within enclosure bounds ──────────────────────────────

def test_geo002_compartment_outside_enclosure() -> None:
    enc = _enc(w=1.0, h=2.0, d=0.8)
    c = _comp(x=0.9, w=0.5)  # x1 = 1.4 > 1.0
    issues = run(enc=enc, compartments=[c])
    assert any(i["rule_id"] == "GEO-002" for i in issues)


def test_geo002_compartment_exactly_fits() -> None:
    enc = _enc(w=1.0, h=2.0, d=0.8)
    c = _comp(x=0.0, y=0.0, z=0.0, w=1.0, h=2.0, d=0.8)
    issues = run(enc=enc, compartments=[c])
    assert not any(i["rule_id"] == "GEO-002" for i in issues)


# ── GEO-003: Compartment name uniqueness ──────────────────────────────────────

def test_geo003_duplicate_names_flagged() -> None:
    c1 = _comp(name="Bus Chamber")
    c2 = _comp(name="Bus Chamber", x=0.6)
    issues = run(compartments=[c1, c2])
    assert any(i["rule_id"] == "GEO-003" for i in issues)


def test_geo003_unique_names_ok() -> None:
    c1 = _comp(name="Chamber A")
    c2 = _comp(name="Chamber B", x=0.6)
    issues = run(compartments=[c1, c2])
    assert not any(i["rule_id"] == "GEO-003" for i in issues)


# ── GEO-004: Overlapping compartments ────────────────────────────────────────

def test_geo004_overlapping_compartments_flagged() -> None:
    enc = _enc(w=2.0)
    c1 = _comp("C1", x=0.0, w=0.8)
    c2 = _comp("C2", x=0.5, w=0.8)  # overlaps c1 from x=0.5..0.8
    issues = run(enc=enc, compartments=[c1, c2])
    assert any(i["rule_id"] == "GEO-004" for i in issues)


def test_geo004_adjacent_compartments_ok() -> None:
    enc = _enc(w=2.0)
    c1 = _comp("C1", x=0.0, w=0.5)
    c2 = _comp("C2", x=0.5, w=0.5)  # touching at x=0.5, strict exclusion
    issues = run(enc=enc, compartments=[c1, c2])
    assert not any(i["rule_id"] == "GEO-004" for i in issues)


# ── GEO-006: Device positive dimensions ───────────────────────────────────────

def test_geo006_device_zero_depth_flagged() -> None:
    d = _dev(d=0.0)
    issues = run(devices=[d])
    assert any(i["rule_id"] == "GEO-006" for i in issues)


# ── GEO-007: Device within enclosure bounds ───────────────────────────────────

def test_geo007_device_outside_enclosure() -> None:
    enc = _enc(w=1.0)
    d = _dev(x=0.95, w=0.2)  # x1 = 1.15 > 1.0
    issues = run(enc=enc, devices=[d])
    assert any(i["rule_id"] == "GEO-007" for i in issues)


def test_geo007_device_inside_enclosure_ok() -> None:
    enc = _enc(w=1.0, h=2.0, d=0.8)
    d = _dev(x=0.1, y=0.1, z=0.1, w=0.1, h=0.2, d=0.1)
    issues = run(enc=enc, devices=[d])
    assert not any(i["rule_id"] == "GEO-007" for i in issues)


# ── GEO-009: Device-device overlap ───────────────────────────────────────────

def test_geo009_device_overlap_flagged() -> None:
    d1 = _dev("D1", x=0.0, y=0.0, z=0.0, w=0.2, h=0.3, d=0.2)
    d2 = _dev("D2", x=0.1, y=0.0, z=0.0, w=0.2, h=0.3, d=0.2)
    issues = run(enc=_enc(w=2.0), devices=[d1, d2])
    assert any(i["rule_id"] == "GEO-009" for i in issues)


def test_geo009_non_overlapping_devices_ok() -> None:
    d1 = _dev("D1", x=0.0, w=0.2)
    d2 = _dev("D2", x=0.3, w=0.2)
    issues = run(enc=_enc(w=2.0), devices=[d1, d2])
    assert not any(i["rule_id"] == "GEO-009" for i in issues)


# ── GEO-013/014: External opening fractions ───────────────────────────────────

def test_geo013_open_area_fraction_out_of_range() -> None:
    o = _ext_opening(open_area=1.5)
    issues = run(ext_openings=[o])
    assert any(i["rule_id"] == "GEO-013" for i in issues)


def test_geo014_discharge_coefficient_out_of_range() -> None:
    o = _ext_opening(cd=1.1)
    issues = run(ext_openings=[o])
    assert any(i["rule_id"] == "GEO-014" for i in issues)


def test_ext_opening_valid_fractions_ok() -> None:
    o = _ext_opening(open_area=0.5, cd=0.61)
    issues = run(ext_openings=[o])
    assert not any(i["rule_id"] in ("GEO-013", "GEO-014") for i in issues)


# ── GEO-015/016: Internal opening fractions ───────────────────────────────────

def test_geo015_internal_open_area_fraction_out_of_range() -> None:
    io = _int_opening(open_area=-0.1)
    issues = run(int_openings=[io])
    assert any(i["rule_id"] == "GEO-015" for i in issues)


def test_geo016_internal_cd_out_of_range() -> None:
    io = _int_opening(cd=2.0)
    issues = run(int_openings=[io])
    assert any(i["rule_id"] == "GEO-016" for i in issues)


# ── Clean enclosure produces zero issues ──────────────────────────────────────

def test_clean_enclosure_no_issues() -> None:
    enc = _enc(w=2.0, h=2.0, d=1.0)
    c1 = _comp("Main", x=0.0, y=0.0, z=0.0, w=0.8, h=2.0, d=1.0)
    c2 = _comp("Bus", x=0.9, y=0.0, z=0.0, w=0.8, h=2.0, d=1.0)
    d1 = _dev("CB1", x=0.1, y=0.1, z=0.1, w=0.1, h=0.2, d=0.1)
    b1 = _bus("L1", x=0.9, y=0.5, z=0.0, w=0.05, t=0.01, length=0.5)
    o1 = _ext_opening(open_area=0.5, cd=0.61)
    io1 = _int_opening(open_area=1.0, cd=0.61)
    issues = run(
        enc=enc,
        compartments=[c1, c2],
        devices=[d1],
        busbars=[b1],
        ext_openings=[o1],
        int_openings=[io1],
    )
    assert issues == []
