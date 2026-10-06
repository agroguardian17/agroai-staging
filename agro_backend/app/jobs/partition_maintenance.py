"""Monthly-partition maintenance — keep the range window ahead of "now".

The three high-volume time-series tables (``node_sensor_readings``,
``weather_station_readings``, ``weather_forecasts``) are monthly range
partitions (migration 0005). Nothing extends the window, so without maintenance
the system would eventually reach a month with no partition and Postgres would
reject the insert (ingest stops). This job ensures the current + N months-ahead
child partitions always exist.

It runs once at startup (immediate coverage) and then on a daily cron. Pure DDL
(``CREATE TABLE IF NOT EXISTS ... PARTITION OF``), idempotent, DB-only. A DEFAULT
partition (migration 0067) is the belt-and-braces catch-all beneath this; the job
keeps the month window ahead so DEFAULT stays empty in normal operation. Skipped
when ``PARTITION_MAINTENANCE_ENABLED`` is false (tests/CI).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.http.deps import _ensure_engine

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)

_PARTITIONED_TABLES = (
    "node_sensor_readings",
    "weather_station_readings",
    "weather_forecasts",
)


def _ensure_sql(months_ahead: int) -> str:
    """DO block that creates current + ``months_ahead`` child partitions.

    ``months_ahead`` is a trusted int from settings, interpolated into the loop
    bound only (never user input); table names are fixed literals.
    """
    return f"""
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
        FOR i IN 0..{int(months_ahead)} LOOP
            start_date := (base_date + (i      || ' month')::interval)::date;
            end_date   := (base_date + ((i + 1) || ' month')::interval)::date;
            suffix     := to_char(start_date, 'YYYYMM');
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF %I '
                'FOR VALUES FROM (%L) TO (%L);',
                tbl || '_p' || suffix, tbl, start_date, end_date);
        END LOOP;
    END LOOP;
END
$$;
"""


async def ensure_partitions(sm: async_sessionmaker[AsyncSession], months_ahead: int) -> None:
    """Create any missing current/future month partitions. Idempotent."""
    async with sm() as session:
        await session.execute(text(_ensure_sql(months_ahead)))
        await session.commit()


async def build_and_start_partition_maintenance(
    settings: Settings,
) -> AsyncIOScheduler | None:
    if not settings.PARTITION_MAINTENANCE_ENABLED:
        log.info("partition_maintenance.disabled", reason="PARTITION_MAINTENANCE_ENABLED=false")
        return None

    sm = _ensure_engine(settings)
    months = settings.PARTITION_MONTHS_AHEAD

    # Run once now so a freshly-booted process has coverage immediately, before
    # the first cron tick. Best-effort: a failure here must not block startup.
    try:
        await ensure_partitions(sm, months)
        log.info("partition_maintenance.ensured_at_startup", months_ahead=months)
    except Exception:
        log.exception("partition_maintenance.startup_ensure_failed")

    scheduler = AsyncIOScheduler(timezone=settings.GINGER_JOB_TIMEZONE)

    async def _job() -> None:
        try:
            await ensure_partitions(sm, months)
            log.info("partition_maintenance.tick_ok", months_ahead=months)
        except Exception:
            log.exception("partition_maintenance.tick_failed")

    scheduler.add_job(
        _job,
        trigger=CronTrigger(
            hour=settings.PARTITION_JOB_HOUR,
            minute=settings.PARTITION_JOB_MINUTE,
            timezone=settings.GINGER_JOB_TIMEZONE,
        ),
        id="partition_maintenance",
        name="Monthly partition maintenance",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,
    )
    scheduler.start()
    log.info(
        "partition_maintenance.started",
        hour=settings.PARTITION_JOB_HOUR,
        minute=settings.PARTITION_JOB_MINUTE,
        months_ahead=months,
    )
    return scheduler


async def stop_partition_maintenance(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
    log.info("partition_maintenance.stopped")


__all__ = [
    "build_and_start_partition_maintenance",
    "ensure_partitions",
    "stop_partition_maintenance",
]
