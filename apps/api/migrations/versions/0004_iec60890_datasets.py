"""M4 — storage for the administrator-imported IEC TR 60890 coefficient dataset.

CR-ENG-002: the coefficients themselves are licensed and are never shipped in
this repository. This migration creates the table a licensed deployment
imports them into; it inserts no data.

The calculation_runs table already carries result_snapshot and
result_checksum_sha256 from revision 0001, so storing a ResultSnapshot needs
no schema change — only the partial index below, which makes "the runs that
have a result" a cheap question for the run list.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-05 00:00:00.000000
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "iec60890_datasets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("content_hash_sha256", sa.String(64), nullable=False),
        sa.Column("coefficients", postgresql.JSONB(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "imported_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("version", name="uq_iec60890_datasets_version"),
    )

    # At most one dataset may be active: two would make a MODE 1 result
    # depend on which row the query happened to return first.
    op.create_index(
        "uq_iec60890_datasets_single_active",
        "iec60890_datasets",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_index(
        "ix_calculation_runs_with_result",
        "calculation_runs",
        ["project_id", "created_at"],
        postgresql_where=sa.text("result_snapshot IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_calculation_runs_with_result", table_name="calculation_runs")
    op.drop_index(
        "uq_iec60890_datasets_single_active", table_name="iec60890_datasets"
    )
    op.drop_table("iec60890_datasets")
