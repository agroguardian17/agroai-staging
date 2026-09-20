"""0028 weather_forecasts += et0_mm, solar_radiation_mj_m2 (Phase 3 — weather).

The Open-Meteo adapter now also fetches reference evapotranspiration (ET0, a
pan-evaporation proxy) and daily shortwave radiation, and fetches ``past_days``
of actuals alongside the forecast. These two daily values need columns; the
past-vs-future split is captured by ``forecast_for_date`` relative to
``fetched_at`` (no schema change needed for that).

Additive + reversible. ``weather_forecasts`` is RANGE-partitioned on
``fetched_at``; ADD COLUMN on the parent cascades to all partitions.

Revision ID: 0028
Revises: 0027
Create Date: 2026-09-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE weather_forecasts ADD COLUMN IF NOT EXISTS et0_mm DOUBLE PRECISION")
    op.execute(
        "ALTER TABLE weather_forecasts "
        "ADD COLUMN IF NOT EXISTS solar_radiation_mj_m2 DOUBLE PRECISION"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE weather_forecasts DROP COLUMN IF EXISTS solar_radiation_mj_m2")
    op.execute("ALTER TABLE weather_forecasts DROP COLUMN IF EXISTS et0_mm")
