"""0061 crop_seasons.sensor_pipe_position — flow-sensor pipe location.

The water-budget compute engine scales one drip pipe's flow reading up to a
per-plant dose. To judge whether that single measured pipe is representative of
the whole plot, ops record **which pipe** the flow sensor sits on. This is the
last piece of the plot-geometry set the farmer/ops team captures (the rest —
planting_layout, bed dims, dripper spacing, drippers_per_acre, rows_per_bed,
plants_per_acre — already landed in 0022 / 0024).

One value per season → a column on crop_seasons, nullable (captured via the
dashboard's Plot Geometry form, often after sowing). CHECK matches the capture
form's vocabulary. Reversible; no backfill.

Revision ID: 0061
Revises: 0060
Create Date: 2026-09-30
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0061"
down_revision: str | None = "0060"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS sensor_pipe_position
    TEXT CHECK (sensor_pipe_position IN ('first', 'middle', 'last', 'representative'));
"""

DOWNGRADE_SQL = r"""
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS sensor_pipe_position;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
