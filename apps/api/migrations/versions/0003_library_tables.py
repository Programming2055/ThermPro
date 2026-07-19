"""M3 engineering library tables — materials, surfaces, busbar profiles, devices,
fans, filters, ventilation openings, cables, and connections.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-19 00:00:00.000000
"""
from __future__ import annotations

import uuid
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Shared column factories
# ---------------------------------------------------------------------------

def _pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


def _fk_release() -> sa.Column:
    return sa.Column(
        "release_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("library_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


def _domain_entry_id() -> sa.Column:
    return sa.Column("domain_entry_id", sa.String(128), nullable=False)


def _library_version() -> sa.Column:
    return sa.Column("library_version", sa.String(32), nullable=False)


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def _references() -> sa.Column:
    return sa.Column("references", postgresql.JSONB, nullable=True)


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # material_library_entries                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "material_library_entries",
        _pk(),
        _fk_release(),
        _domain_entry_id(),
        _library_version(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("thermal_conductivity_w_per_m_k", sa.Float(), nullable=False),
        sa.Column("density_kg_per_m3", sa.Float(), nullable=False),
        sa.Column("specific_heat_j_per_kg_k", sa.Float(), nullable=False),
        sa.Column("electrical_resistivity_ohm_m", sa.Float(), nullable=True),
        sa.Column("temp_coeff_resistance_per_k", sa.Float(), nullable=True),
        sa.Column("emissivity", sa.Float(), nullable=True),
        sa.Column("max_operating_temp_k", sa.Float(), nullable=True),
        _references(),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("release_id", "domain_entry_id", name="uq_material_release_domain_id"),
    )

    # ------------------------------------------------------------------ #
    # surface_library_entries                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "surface_library_entries",
        _pk(),
        _fk_release(),
        _domain_entry_id(),
        _library_version(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("emissivity", sa.Float(), nullable=False),
        sa.Column("absorptivity", sa.Float(), nullable=True),
        sa.Column("roughness_um", sa.Float(), nullable=True),
        sa.Column("coating", sa.String(255), nullable=True),
        sa.Column("material_ref", sa.String(128), nullable=True),
        _references(),
        *_timestamps(),
        sa.UniqueConstraint("release_id", "domain_entry_id", name="uq_surface_release_domain_id"),
    )

    # ------------------------------------------------------------------ #
    # busbar_profile_library_entries                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "busbar_profile_library_entries",
        _pk(),
        _fk_release(),
        _domain_entry_id(),
        _library_version(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("material_ref", sa.String(128), nullable=False),
        sa.Column("profile", sa.String(32), nullable=False),
        sa.Column("coating", sa.String(32), nullable=False),
        sa.Column("thickness_m", sa.Float(), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("cross_section_area_m2", sa.Float(), nullable=False),
        sa.Column("max_continuous_current_a", sa.Float(), nullable=True),
        sa.Column("emissivity_override", sa.Float(), nullable=True),
        _references(),
        *_timestamps(),
        sa.UniqueConstraint(
            "release_id", "domain_entry_id", name="uq_busbar_profile_release_domain_id"
        ),
    )

    # ------------------------------------------------------------------ #
    # device_library_entries                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "device_library_entries",
        _pk(),
        _fk_release(),
        _domain_entry_id(),
        _library_version(),
        sa.Column("manufacturer", sa.String(128), nullable=False),
        sa.Column("family", sa.String(128), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("rated_current_a", sa.Float(), nullable=False),
        sa.Column("poles", sa.Integer(), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("height_m", sa.Float(), nullable=False),
        sa.Column("depth_m", sa.Float(), nullable=False),
        sa.Column("mounting_type", sa.String(32), nullable=False),
        sa.Column("ventilation_requirement", sa.String(64), nullable=False),
        sa.Column("max_ambient_temp_k", sa.Float(), nullable=False),
        sa.Column(
            "power_loss_curve",
            postgresql.JSONB,
            nullable=False,
            comment="[{current_fraction: float, power_loss_w: float}, ...]",
        ),
        sa.Column("loss_confidence", sa.String(64), nullable=False),
        _references(),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("release_id", "domain_entry_id", name="uq_device_release_domain_id"),
    )

    # ------------------------------------------------------------------ #
    # fan_library_entries                                                  #
    # ------------------------------------------------------------------ #
    op.create_table(
        "fan_library_entries",
        _pk(),
        _fk_release(),
        _domain_entry_id(),
        _library_version(),
        sa.Column("manufacturer", sa.String(128), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("direction", sa.String(32), nullable=False),
        sa.Column("rated_speed_rpm", sa.Float(), nullable=False),
        sa.Column("rated_flow_m3_per_s", sa.Float(), nullable=False),
        sa.Column("rated_pressure_pa", sa.Float(), nullable=False),
        sa.Column("rated_power_w", sa.Float(), nullable=False),
        sa.Column("voltage_v", sa.Float(), nullable=True),
        sa.Column("frequency_hz", sa.Float(), nullable=True),
        sa.Column(
            "fan_curve",
            postgresql.JSONB,
            nullable=False,
            comment="[{flow_m3_per_s, static_pressure_pa, power_w, efficiency}, ...]",
        ),
        _references(),
        *_timestamps(),
        sa.UniqueConstraint("release_id", "domain_entry_id", name="uq_fan_release_domain_id"),
    )

    # ------------------------------------------------------------------ #
    # filter_library_entries                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "filter_library_entries",
        _pk(),
        _fk_release(),
        _domain_entry_id(),
        _library_version(),
        sa.Column("manufacturer", sa.String(128), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("dust_class", sa.String(64), nullable=True),
        sa.Column("rated_flow_m3_per_s", sa.Float(), nullable=False),
        sa.Column("pressure_drop_pa", sa.Float(), nullable=False),
        sa.Column("loss_coefficient", sa.Float(), nullable=False),
        sa.Column("porosity", sa.Float(), nullable=True),
        sa.Column("initial_efficiency", sa.Float(), nullable=True),
        _references(),
        *_timestamps(),
        sa.UniqueConstraint("release_id", "domain_entry_id", name="uq_filter_release_domain_id"),
    )

    # ------------------------------------------------------------------ #
    # ventilation_opening_library_entries                                  #
    # ------------------------------------------------------------------ #
    op.create_table(
        "ventilation_opening_library_entries",
        _pk(),
        _fk_release(),
        _domain_entry_id(),
        _library_version(),
        sa.Column("manufacturer", sa.String(128), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("accessory", sa.String(32), nullable=False),
        sa.Column("gross_width_m", sa.Float(), nullable=False),
        sa.Column("gross_height_m", sa.Float(), nullable=False),
        sa.Column("open_area_fraction", sa.Float(), nullable=False),
        sa.Column("discharge_coefficient", sa.Float(), nullable=False),
        sa.Column("filter_ref", sa.String(128), nullable=True),
        _references(),
        *_timestamps(),
        sa.UniqueConstraint(
            "release_id", "domain_entry_id", name="uq_ventilation_opening_release_domain_id"
        ),
    )

    # ------------------------------------------------------------------ #
    # cable_library_entries                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        "cable_library_entries",
        _pk(),
        _fk_release(),
        _domain_entry_id(),
        _library_version(),
        sa.Column("manufacturer", sa.String(128), nullable=True),
        sa.Column("designation", sa.String(255), nullable=False),
        sa.Column("conductor", sa.String(32), nullable=False),
        sa.Column("insulation", sa.String(32), nullable=False),
        sa.Column("conductor_cross_section_m2", sa.Float(), nullable=False),
        sa.Column("outer_diameter_m", sa.Float(), nullable=False),
        sa.Column("rated_current_a", sa.Float(), nullable=False),
        sa.Column("resistance_ohm_per_m", sa.Float(), nullable=False),
        sa.Column("temp_coeff_resistance_per_k", sa.Float(), nullable=False),
        sa.Column("max_conductor_temp_k", sa.Float(), nullable=False),
        _references(),
        *_timestamps(),
        sa.UniqueConstraint("release_id", "domain_entry_id", name="uq_cable_release_domain_id"),
    )

    # ------------------------------------------------------------------ #
    # connection_library_entries                                           #
    # ------------------------------------------------------------------ #
    op.create_table(
        "connection_library_entries",
        _pk(),
        _fk_release(),
        _domain_entry_id(),
        _library_version(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_quality", sa.String(32), nullable=False),
        sa.Column("plating", sa.String(64), nullable=True),
        sa.Column("bolt_size_m", sa.Float(), nullable=True),
        sa.Column("bolt_torque_n_m", sa.Float(), nullable=True),
        sa.Column("contact_pressure_pa", sa.Float(), nullable=True),
        sa.Column("joint_resistance_ohm", sa.Float(), nullable=False),
        sa.Column("resistance_source", sa.String(64), nullable=False),
        sa.Column("age_factor", sa.Float(), nullable=False, server_default="1.0"),
        _references(),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint(
            "release_id", "domain_entry_id", name="uq_connection_release_domain_id"
        ),
    )


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    op.drop_table("connection_library_entries")
    op.drop_table("cable_library_entries")
    op.drop_table("ventilation_opening_library_entries")
    op.drop_table("filter_library_entries")
    op.drop_table("fan_library_entries")
    op.drop_table("device_library_entries")
    op.drop_table("busbar_profile_library_entries")
    op.drop_table("surface_library_entries")
    op.drop_table("material_library_entries")
