"""0017 weather altitude — barometric altitude on weather_station_readings.

The Main Node's BME280 reports pressure; the backend now derives barometric
altitude from it (``app.domain.weather_calibration.altitude_m_from_pressure_pa``)
and persists it alongside the other weather fields. This adds the single
``altitude_m`` column that lands in.

``weather_station_readings`` is RANGE-partitioned on ``recorded_at`` (0005);
``ALTER TABLE ... ADD COLUMN`` on the partitioned parent propagates to every
partition automatically, so no per-partition work is needed.

Idempotent (``ADD COLUMN IF NOT EXISTS``). Reversible.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-17
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
ALTER TABLE weather_station_readings
    ADD COLUMN IF NOT EXISTS altitude_m DOUBLE PRECISION;
"""


DOWNGRADE_SQL = r"""
ALTER TABLE weather_station_readings
    DROP COLUMN IF EXISTS altitude_m;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
