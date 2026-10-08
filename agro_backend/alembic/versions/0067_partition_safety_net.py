"""0067 partition safety net — refresh the monthly window + DEFAULT partitions.

Migration 0005 made node_sensor_readings / weather_station_readings /
weather_forecasts monthly range partitions, but pre-created only a fixed window
(current + 12 months) and nothing extends it. Once the window is exhausted,
Postgres rejects any insert whose partition key falls outside every existing
child — ingest silently stops for that table.

This migration (a) re-creates the current + 6 months-ahead child partitions
(idempotent; refreshes a possibly-stale window) and (b) adds a DEFAULT partition
per table as a catch-all so an insert can NEVER be rejected for lack of a
partition. The nightly partition-maintenance job keeps the month window ahead so
the DEFAULT partitions stay empty in normal operation; DEFAULT only ever catches
surprises (e.g. a wildly skewed device clock).

Additive and non-destructive (all CREATE ... IF NOT EXISTS). Forward-only in
spirit; downgrade drops only the DEFAULT partitions this migration adds.

Revision ID: 0067
Revises: 0066
Create Date: 2026-10-07
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0067"
down_revision: str | None = "0066"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
DO $$
DECLARE
    i          INT;
    start_date DATE;
    end_date   DATE;
    base_date  DATE := date_trunc('month', now())::date;
    suffix     TEXT;
    tbl        TEXT;
    tables     TEXT[] := ARRAY[
        'node_sensor_readings', 'weather_station_readings', 'weather_forecasts'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        FOR i IN 0..6 LOOP
            start_date := (base_date + (i      || ' month')::interval)::date;
            end_date   := (base_date + ((i + 1) || ' month')::interval)::date;
            suffix     := to_char(start_date, 'YYYYMM');
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I '
                'FOR VALUES FROM (%L) TO (%L);',
                tbl || '_p' || suffix, tbl, start_date, end_date);
        END LOOP;
        -- Catch-all so a key outside every month partition is never rejected.
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I DEFAULT;',
            tbl || '_pdefault', tbl);
    END LOOP;
END
$$;
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS node_sensor_readings_pdefault;
DROP TABLE IF EXISTS weather_station_readings_pdefault;
DROP TABLE IF EXISTS weather_forecasts_pdefault;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
