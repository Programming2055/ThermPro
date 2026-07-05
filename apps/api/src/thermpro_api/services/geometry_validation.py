"""Geometry validation service — spatial rule checks, no thermal calculations."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from thermpro_api.models.geometry import (
    BusbarPlacement,
    Compartment,
    DevicePlacement,
    Enclosure,
    ExternalOpening,
    InternalOpening,
    Partition,
)


@dataclass(frozen=True)
class _Box3D:
    x0: float
    y0: float
    z0: float
    x1: float
    y1: float
    z1: float

    def overlaps(self, other: _Box3D) -> bool:
        """Return True if boxes share any interior volume (strict exclusion on boundary)."""
        return not (
            self.x1 <= other.x0
            or other.x1 <= self.x0
            or self.y1 <= other.y0
            or other.y1 <= self.y0
            or self.z1 <= other.z0
            or other.z1 <= self.z0
        )

    def contains(self, other: _Box3D) -> bool:
        """Return True if other lies entirely within (or touching boundary of) this box."""
        return (
            other.x0 >= self.x0
            and other.y0 >= self.y0
            and other.z0 >= self.z0
            and other.x1 <= self.x1
            and other.y1 <= self.y1
            and other.z1 <= self.z1
        )


def _enclosure_box(e: Enclosure) -> _Box3D:
    return _Box3D(0.0, 0.0, 0.0, e.internal_width_m, e.internal_height_m, e.internal_depth_m)


def _compartment_box(c: Compartment) -> _Box3D:
    return _Box3D(
        c.position_x_m,
        c.position_y_m,
        c.position_z_m,
        c.position_x_m + c.width_m,
        c.position_y_m + c.height_m,
        c.position_z_m + c.depth_m,
    )


def _device_box(d: DevicePlacement) -> _Box3D:
    return _Box3D(
        d.position_x_m,
        d.position_y_m,
        d.position_z_m,
        d.position_x_m + d.width_m,
        d.position_y_m + d.height_m,
        d.position_z_m + d.depth_m,
    )


def _busbar_box(b: BusbarPlacement) -> _Box3D:
    return _Box3D(
        b.position_x_m,
        b.position_y_m,
        b.position_z_m,
        b.position_x_m + b.width_m,
        b.position_y_m + b.thickness_m,
        b.position_z_m + b.length_m,
    )


def _new_issue(
    issue_id: str,
    severity: str,
    entity_type: str,
    entity_id: str,
    message: str,
    rule_id: str,
    coordinate_ref: dict[str, Any] | None = None,
    suggested_fix: str | None = None,
) -> dict[str, Any]:
    return {
        "id": uuid.uuid4(),
        "issue_id": issue_id,
        "severity": severity,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "message": message,
        "rule_id": rule_id,
        "coordinate_ref": coordinate_ref,
        "suggested_fix": suggested_fix,
        "is_resolved": False,
    }


def validate_enclosure_geometry(
    enclosure: Enclosure,
    compartments: list[Compartment],
    partitions: list[Partition],
    device_placements: list[DevicePlacement],
    busbar_placements: list[BusbarPlacement],
    external_openings: list[ExternalOpening],
    internal_openings: list[InternalOpening],
) -> list[dict[str, Any]]:
    """
    Run all geometry validation rules against an enclosure and its sub-entities.

    Returns a list of issue dicts ready for ORM insertion. Does not persist to DB.
    No thermal or airflow calculations (M2 scope boundary).
    """
    issues: list[dict[str, Any]] = []
    enc_box = _enclosure_box(enclosure)

    # ── GEO-001/002: Compartment dimensions and bounds ─────────────────────────
    compartment_map: dict[uuid.UUID, Compartment] = {c.id: c for c in compartments}
    compartment_names: list[str] = []

    for comp in compartments:
        eid = str(comp.id)

        if comp.width_m <= 0 or comp.height_m <= 0 or comp.depth_m <= 0:
            issues.append(_new_issue(
                f"GEO-001-{eid}", "ERROR", "Compartment", eid,
                f"Compartment '{comp.name}' has non-positive dimension: "
                f"({comp.width_m:.4f}, {comp.height_m:.4f}, {comp.depth_m:.4f}) m",
                "GEO-001",
                suggested_fix="Set width, height, and depth > 0.",
            ))
            continue  # skip spatial checks for degenerate box

        cbox = _compartment_box(comp)
        if not enc_box.contains(cbox):
            issues.append(_new_issue(
                f"GEO-002-{eid}", "ERROR", "Compartment", eid,
                f"Compartment '{comp.name}' extends outside the enclosure internal volume.",
                "GEO-002",
                coordinate_ref={
                    "x": comp.position_x_m, "y": comp.position_y_m, "z": comp.position_z_m,
                },
                suggested_fix="Reduce dimensions or reposition within internal envelope.",
            ))

        compartment_names.append(comp.name)

    # GEO-003: Compartment name uniqueness
    seen_names: set[str] = set()
    for name in compartment_names:
        if name in seen_names:
            issues.append(_new_issue(
                f"GEO-003-{name}", "ERROR", "Compartment", name,
                f"Duplicate compartment name: '{name}'",
                "GEO-003",
                suggested_fix="Give each compartment a unique name within the enclosure.",
            ))
        seen_names.add(name)

    # GEO-004: Overlapping compartments
    comp_boxes = [(c, _compartment_box(c)) for c in compartments
                  if c.width_m > 0 and c.height_m > 0 and c.depth_m > 0]
    for i, (ca, ba) in enumerate(comp_boxes):
        for cb, bb in comp_boxes[i + 1:]:
            if ba.overlaps(bb):
                issues.append(_new_issue(
                    f"GEO-004-{ca.id}-{cb.id}", "ERROR", "Compartment", str(ca.id),
                    f"Compartment '{ca.name}' overlaps with '{cb.name}'.",
                    "GEO-004",
                    suggested_fix="Reposition compartments so they do not share volume.",
                ))

    # ── GEO-005: Partition within enclosure ────────────────────────────────────
    for part in partitions:
        pid = str(part.id)
        if part.width_m <= 0 or part.height_m <= 0:
            issues.append(_new_issue(
                f"GEO-005-{pid}", "WARNING", "Partition", pid,
                f"Partition '{part.name or pid}' has non-positive dimension.",
                "GEO-005",
            ))
            continue
        # Build a thin box for the partition
        if part.orientation == "VERTICAL_YZ":
            pbox = _Box3D(
                part.position_x_m, part.position_y_m, part.position_z_m,
                part.position_x_m + part.thickness_m,
                part.position_y_m + part.height_m,
                part.position_z_m + part.width_m,
            )
        elif part.orientation == "HORIZONTAL_XY":
            pbox = _Box3D(
                part.position_x_m, part.position_y_m, part.position_z_m,
                part.position_x_m + part.width_m,
                part.position_y_m + part.thickness_m,
                part.position_z_m + part.height_m,
            )
        else:  # VERTICAL_XZ
            pbox = _Box3D(
                part.position_x_m, part.position_y_m, part.position_z_m,
                part.position_x_m + part.width_m,
                part.position_y_m + part.thickness_m,
                part.position_z_m + part.height_m,
            )
        if not enc_box.contains(pbox):
            issues.append(_new_issue(
                f"GEO-005-{pid}", "WARNING", "Partition", pid,
                f"Partition '{part.name or pid}' extends outside the enclosure.",
                "GEO-005",
                coordinate_ref={
                    "x": part.position_x_m, "y": part.position_y_m, "z": part.position_z_m,
                },
            ))

    # ── GEO-006/007/008: Device placement checks ───────────────────────────────
    device_boxes: list[tuple[DevicePlacement, _Box3D]] = []
    for dev in device_placements:
        did = str(dev.id)
        if dev.width_m <= 0 or dev.height_m <= 0 or dev.depth_m <= 0:
            issues.append(_new_issue(
                f"GEO-006-{did}", "ERROR", "DevicePlacement", did,
                f"Device '{dev.name}' has non-positive dimension.",
                "GEO-006",
            ))
            continue
        dbox = _device_box(dev)
        device_boxes.append((dev, dbox))

        if not enc_box.contains(dbox):
            issues.append(_new_issue(
                f"GEO-007-{did}", "ERROR", "DevicePlacement", did,
                f"Device '{dev.name}' extends outside the enclosure internal volume.",
                "GEO-007",
                coordinate_ref={
                    "x": dev.position_x_m, "y": dev.position_y_m, "z": dev.position_z_m,
                },
                suggested_fix="Reposition device within the enclosure internal envelope.",
            ))

        # GEO-008: Device outside assigned compartment
        if dev.compartment_id is not None:
            parent = compartment_map.get(dev.compartment_id)
            if parent is not None and parent.width_m > 0:
                cbox = _compartment_box(parent)
                if not cbox.contains(dbox):
                    issues.append(_new_issue(
                        f"GEO-008-{did}", "WARNING", "DevicePlacement", did,
                        f"Device '{dev.name}' extends outside its assigned compartment "
                        f"'{parent.name}'.",
                        "GEO-008",
                    ))

    # GEO-009: Device-device overlap
    for i, (da, ba) in enumerate(device_boxes):
        for db, bb in device_boxes[i + 1:]:
            if ba.overlaps(bb):
                issues.append(_new_issue(
                    f"GEO-009-{da.id}-{db.id}", "ERROR", "DevicePlacement", str(da.id),
                    f"Device '{da.name}' overlaps with device '{db.name}'.",
                    "GEO-009",
                ))

    # ── GEO-010/011/012: Busbar placement checks ───────────────────────────────
    busbar_boxes: list[tuple[BusbarPlacement, _Box3D]] = []
    for bus in busbar_placements:
        bid = str(bus.id)
        if bus.width_m <= 0 or bus.thickness_m <= 0 or bus.length_m <= 0:
            issues.append(_new_issue(
                f"GEO-010-{bid}", "ERROR", "BusbarPlacement", bid,
                f"Busbar '{bus.name}' has non-positive dimension.",
                "GEO-010",
            ))
            continue
        bbox = _busbar_box(bus)
        busbar_boxes.append((bus, bbox))

        if not enc_box.contains(bbox):
            issues.append(_new_issue(
                f"GEO-011-{bid}", "WARNING", "BusbarPlacement", bid,
                f"Busbar '{bus.name}' extends outside the enclosure internal volume.",
                "GEO-011",
                coordinate_ref={
                    "x": bus.position_x_m, "y": bus.position_y_m, "z": bus.position_z_m,
                },
            ))

        # GEO-012: Busbar-device overlap
        for dev, dbox in device_boxes:
            if bbox.overlaps(dbox):
                issues.append(_new_issue(
                    f"GEO-012-{bid}-{dev.id}", "WARNING", "BusbarPlacement", bid,
                    f"Busbar '{bus.name}' overlaps with device '{dev.name}'.",
                    "GEO-012",
                ))

    # ── GEO-013/014: External opening checks ───────────────────────────────────
    for opening in external_openings:
        oid = str(opening.id)
        if not (0.0 <= opening.open_area_fraction <= 1.0):
            issues.append(_new_issue(
                f"GEO-013-{oid}", "ERROR", "ExternalOpening", oid,
                f"External opening '{opening.name or oid}' has invalid "
                f"open_area_fraction={opening.open_area_fraction:.4f}; must be in [0, 1].",
                "GEO-013",
            ))
        if not (0.0 <= opening.discharge_coefficient <= 1.0):
            issues.append(_new_issue(
                f"GEO-014-{oid}", "ERROR", "ExternalOpening", oid,
                f"External opening '{opening.name or oid}' has invalid "
                f"discharge_coefficient={opening.discharge_coefficient:.4f}; must be in [0, 1].",
                "GEO-014",
            ))

    # ── GEO-015/016: Internal opening checks ──────────────────────────────────
    for io in internal_openings:
        iid = str(io.id)
        if not (0.0 <= io.open_area_fraction <= 1.0):
            issues.append(_new_issue(
                f"GEO-015-{iid}", "ERROR", "InternalOpening", iid,
                f"Internal opening '{io.name or iid}' has invalid "
                f"open_area_fraction={io.open_area_fraction:.4f}; must be in [0, 1].",
                "GEO-015",
            ))
        if not (0.0 <= io.discharge_coefficient <= 1.0):
            issues.append(_new_issue(
                f"GEO-016-{iid}", "ERROR", "InternalOpening", iid,
                f"Internal opening '{io.name or iid}' has invalid "
                f"discharge_coefficient={io.discharge_coefficient:.4f}; must be in [0, 1].",
                "GEO-016",
            ))

    return issues
