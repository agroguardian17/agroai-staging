"""0033 weather_forecasts += wind_gust_kmph (D07-CY-WX-001 severe-weather rule).

Daily max wind gust from Open-Meteo (wind_gusts_10m_max). Feeds the mapper's
wind_gust_kmph farm-brain field, which the new D07-CY-WX-001 rule reads.
Reversible, no backfill.

Revision ID: 0033
Revises: 0032
Create Date: 2026-09-22
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE weather_forecasts ADD COLUMN IF NOT EXISTS wind_gust_kmph DOUBLE PRECISION"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE weather_forecasts DROP COLUMN IF EXISTS wind_gust_kmph")
