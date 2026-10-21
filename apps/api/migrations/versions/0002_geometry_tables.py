"""M2 geometry tables — assemblies, enclosures, surfaces, compartments, partitions,
openings, device/busbar placements, and validation issues.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-05 00:00:00.000000
"""
from __future__ import annotations

import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # assemblies                                                           #
    # ------------------------------------------------------------------ #
    op.create_table(
        "assemblies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "coordinate_system_version",
            sa.String(16),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_assemblies_project_id", "assemblies", ["project_id"])

    # ------------------------------------------------------------------ #
    # enclosures                                                           #
    # ------------------------------------------------------------------ #
    op.create_table(
        "enclosures",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assembly_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assemblies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("external_width_m", sa.Float(), nullable=False),
        sa.Column("external_height_m", sa.Float(), nullable=False),
        sa.Column("external_depth_m", sa.Float(), nullable=False),
        sa.Column("internal_width_m", sa.Float(), nullable=False),
        sa.Column("internal_height_m", sa.Float(), nullable=False),
        sa.Column("internal_depth_m", sa.Float(), nullable=False),
        sa.Column(
            "wall_thickness_m", sa.Float(), nullable=False, server_default="0.002"
        ),
        sa.Column("material_ref", sa.String(255), nullable=True),
        sa.Column(
            "installation_type",
            sa.String(32),
            nullable=False,
            server_default="FLOOR_STANDING",
        ),
        sa.Column("ip_rating", sa.String(16), nullable=True),
        sa.Column(
            "coordinate_system_version",
            sa.String(16),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_enclosures_project_id", "enclosures", ["project_id"])
    op.create_index("ix_enclosures_assembly_id", "enclosures", ["assembly_id"])

    # ------------------------------------------------------------------ #
    # surfaces                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "surfaces",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "enclosure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enclosures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("face", sa.String(16), nullable=False),
        sa.Column("is_exposed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("material_override", sa.String(255), nullable=True),
        sa.Column("emissivity_override", sa.Float(), nullable=True),
        sa.Column("bc_placeholder", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_surfaces_enclosure_id", "surfaces", ["enclosure_id"])

    # ------------------------------------------------------------------ #
    # compartments (self-referential adjacency list)                       #
    # ------------------------------------------------------------------ #
    op.create_table(
        "compartments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "enclosure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enclosures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_compartment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("compartments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("compartment_type", sa.String(32), nullable=False),
        sa.Column("position_x_m", sa.Float(), nullable=False, server_default="0"),
        sa.Column("position_y_m", sa.Float(), nullable=False, server_default="0"),
        sa.Column("position_z_m", sa.Float(), nullable=False, server_default="0"),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("height_m", sa.Float(), nullable=False),
        sa.Column("depth_m", sa.Float(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_compartments_enclosure_id", "compartments", ["enclosure_id"])
    op.create_index(
        "ix_compartments_parent_compartment_id",
        "compartments",
        ["parent_compartment_id"],
    )

    # ------------------------------------------------------------------ #
    # partitions                                                           #
    # ------------------------------------------------------------------ #
    op.create_table(
        "partitions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "enclosure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enclosures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("orientation", sa.String(16), nullable=False),
        sa.Column("position_x_m", sa.Float(), nullable=False),
        sa.Column("position_y_m", sa.Float(), nullable=False),
        sa.Column("position_z_m", sa.Float(), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("height_m", sa.Float(), nullable=False),
        sa.Column(
            "thickness_m", sa.Float(), nullable=False, server_default="0.001"
        ),
        sa.Column("material_ref", sa.String(255), nullable=True),
        sa.Column(
            "is_removable", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_partitions_enclosure_id", "partitions", ["enclosure_id"])

    # ------------------------------------------------------------------ #
    # external_openings                                                    #
    # ------------------------------------------------------------------ #
    op.create_table(
        "external_openings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "enclosure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enclosures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "surface_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("surfaces.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("position_x_m", sa.Float(), nullable=False),
        sa.Column("position_y_m", sa.Float(), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("height_m", sa.Float(), nullable=False),
        sa.Column("gross_area_m2", sa.Float(), nullable=True),
        sa.Column(
            "open_area_fraction", sa.Float(), nullable=False, server_default="1.0"
        ),
        sa.Column(
            "discharge_coefficient", sa.Float(), nullable=False, server_default="0.61"
        ),
        sa.Column(
            "direction",
            sa.String(16),
            nullable=False,
            server_default="BIDIRECTIONAL",
        ),
        sa.Column("elevation_m", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "has_grille", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "has_filter", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("airflow_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_external_openings_enclosure_id", "external_openings", ["enclosure_id"]
    )
    op.create_index(
        "ix_external_openings_surface_id", "external_openings", ["surface_id"]
    )

    # ------------------------------------------------------------------ #
    # internal_openings                                                    #
    # ------------------------------------------------------------------ #
    op.create_table(
        "internal_openings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "partition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("partitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "compartment_a_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("compartments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "compartment_b_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("compartments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("position_x_m", sa.Float(), nullable=False),
        sa.Column("position_y_m", sa.Float(), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("height_m", sa.Float(), nullable=False),
        sa.Column("gross_area_m2", sa.Float(), nullable=True),
        sa.Column(
            "open_area_fraction", sa.Float(), nullable=False, server_default="1.0"
        ),
        sa.Column(
            "discharge_coefficient", sa.Float(), nullable=False, server_default="0.61"
        ),
        sa.Column(
            "direction",
            sa.String(16),
            nullable=False,
            server_default="BIDIRECTIONAL",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_internal_openings_partition_id", "internal_openings", ["partition_id"]
    )
    op.create_index(
        "ix_internal_openings_compartment_a_id",
        "internal_openings",
        ["compartment_a_id"],
    )
    op.create_index(
        "ix_internal_openings_compartment_b_id",
        "internal_openings",
        ["compartment_b_id"],
    )

    # ------------------------------------------------------------------ #
    # device_placements                                                    #
    # ------------------------------------------------------------------ #
    op.create_table(
        "device_placements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "enclosure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enclosures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "compartment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("compartments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("device_library_ref", sa.String(255), nullable=True),
        sa.Column("position_x_m", sa.Float(), nullable=False),
        sa.Column("position_y_m", sa.Float(), nullable=False),
        sa.Column("position_z_m", sa.Float(), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("height_m", sa.Float(), nullable=False),
        sa.Column("depth_m", sa.Float(), nullable=False),
        sa.Column(
            "rotation_deg", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column("mounting_surface", sa.String(16), nullable=True),
        sa.Column(
            "clearance_x_m", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column(
            "clearance_y_m", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column(
            "clearance_z_m", sa.Float(), nullable=False, server_default="0"
        ),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_device_placements_enclosure_id", "device_placements", ["enclosure_id"]
    )
    op.create_index(
        "ix_device_placements_compartment_id",
        "device_placements",
        ["compartment_id"],
    )

    # ------------------------------------------------------------------ #
    # busbar_placements                                                    #
    # ------------------------------------------------------------------ #
    op.create_table(
        "busbar_placements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "enclosure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enclosures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "compartment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("compartments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("busbar_library_ref", sa.String(255), nullable=True),
        sa.Column("position_x_m", sa.Float(), nullable=False),
        sa.Column("position_y_m", sa.Float(), nullable=False),
        sa.Column("position_z_m", sa.Float(), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("thickness_m", sa.Float(), nullable=False),
        sa.Column("length_m", sa.Float(), nullable=False),
        sa.Column("phase_designation", sa.String(16), nullable=True),
        sa.Column(
            "clearance_m", sa.Float(), nullable=False, server_default="0.005"
        ),
        sa.Column("route_points", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_busbar_placements_enclosure_id", "busbar_placements", ["enclosure_id"]
    )
    op.create_index(
        "ix_busbar_placements_compartment_id",
        "busbar_placements",
        ["compartment_id"],
    )

    # ------------------------------------------------------------------ #
    # geometry_validation_issues                                           #
    # ------------------------------------------------------------------ #
    op.create_table(
        "geometry_validation_issues",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "enclosure_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("enclosures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("issue_id", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("coordinate_ref", postgresql.JSONB(), nullable=True),
        sa.Column("suggested_fix", sa.Text(), nullable=True),
        sa.Column("rule_id", sa.String(64), nullable=False),
        sa.Column(
            "is_resolved", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_geometry_validation_issues_enclosure_id",
        "geometry_validation_issues",
        ["enclosure_id"],
    )


def downgrade() -> None:
    op.drop_table("geometry_validation_issues")
    op.drop_table("busbar_placements")
    op.drop_table("device_placements")
    op.drop_table("internal_openings")
    op.drop_table("external_openings")
    op.drop_table("partitions")
    op.drop_table("compartments")
    op.drop_table("surfaces")
    op.drop_table("enclosures")
    op.drop_table("assemblies")
