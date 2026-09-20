"""0029 Phase-3 columns: forecast night-VPD/fog + k_source + labour date.

- weather_forecasts += vpd_night_mean_kpa, fog_observed (from the adapter's
  new hourly aggregation).
- crop_seasons += k_source (K fertiliser source, D04 enum MOP/SOP/mixed).
- season_operations += labour_arranged_date (D08/D13).

Additive, reversible.

Revision ID: 0029
Revises: 0028
Create Date: 2026-09-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE weather_forecasts ADD COLUMN IF NOT EXISTS vpd_night_mean_kpa DOUBLE PRECISION"
    )
    op.execute("ALTER TABLE weather_forecasts ADD COLUMN IF NOT EXISTS fog_observed BOOLEAN")
    op.execute(
        "ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS k_source TEXT "
        "CHECK (k_source IN ('MOP', 'SOP', 'mixed'))"
    )
    op.execute("ALTER TABLE season_operations ADD COLUMN IF NOT EXISTS labour_arranged_date DATE")


def downgrade() -> None:
    op.execute("ALTER TABLE season_operations DROP COLUMN IF EXISTS labour_arranged_date")
    op.execute("ALTER TABLE crop_seasons DROP COLUMN IF EXISTS k_source")
    op.execute("ALTER TABLE weather_forecasts DROP COLUMN IF EXISTS fog_observed")
    op.execute("ALTER TABLE weather_forecasts DROP COLUMN IF EXISTS vpd_night_mean_kpa")
