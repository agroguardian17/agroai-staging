"""0019 satellite D14 index panel — extend satellite_data for Domain 14.

The ``satellite_data`` table (migration 0001) already carries the optical
indices ``ndvi/ndre/evi/savi/ndmi`` and cloud cover. Domain 14 additionally
needs the SAR block (Sentinel-1), a thermal block (Landsat LST/CWSI, Phase-2),
the burn ratio, per-scene NDVI dispersion, and the valid-pixel fraction that
gates every optical rule. This migration adds those columns plus a
(plot_id, image_date, satellite_source) idempotency constraint so the fetch
job can upsert one row per plot per scene.

All columns are nullable and additive; no existing row or column is touched.
Reversible.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# New columns: (name, type). Double precision throughout (indices/backscatter).
_NEW_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("ndvi_std", sa.Double()),
    ("nbr_value", sa.Double()),
    ("valid_pixel_pct", sa.Double()),
    # SAR (Sentinel-1)
    ("sar_vv_db", sa.Double()),
    ("sar_vh_db", sa.Double()),
    ("sar_rvi", sa.Double()),
    ("sar_coherence", sa.Double()),
    # Thermal (Landsat) — Phase 2 source, column ready now.
    ("lst_c", sa.Double()),
    ("cwsi", sa.Double()),
    # Processing provenance for freshness/version rules.
    ("pipeline_version", sa.Text()),
)

_UNIQUE = "satellite_data_plot_scene_idem"


def upgrade() -> None:
    for name, coltype in _NEW_COLUMNS:
        op.add_column("satellite_data", sa.Column(name, coltype, nullable=True))
    op.create_unique_constraint(
        _UNIQUE, "satellite_data", ["plot_id", "image_date", "satellite_source"]
    )


def downgrade() -> None:
    op.drop_constraint(_UNIQUE, "satellite_data", type_="unique")
    for name, _ in reversed(_NEW_COLUMNS):
        op.drop_column("satellite_data", name)
