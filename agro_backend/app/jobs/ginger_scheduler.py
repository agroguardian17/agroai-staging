"""Start/stop the ginger APScheduler in the FastAPI lifespan.

Two entry points mirror the ingest broker helpers:

* :func:`build_and_start_scheduler` — construct an ``AsyncIOScheduler``,
  register the daily job, and start it.
* :func:`stop_scheduler` — graceful shutdown.

Skips silently when ``settings.GINGER_JOB_ENABLED`` is false, so tests and
CI runs do not need a full ginger stack.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_advisory_metrics_repo import PgAdvisoryMetricsRepo
from app.infra.persistence.pg_ai_suggestion_repo import PgAiSuggestionRepo
from app.infra.persistence.pg_cluster_repo import PgClusterRepo
from app.infra.persistence.pg_crop_scouting_repo import PgCropScoutingRepo
from app.infra.persistence.pg_crop_season_repo import PgCropSeasonRepo
from app.infra.persistence.pg_farm_repo import PgFarmRepo
from app.infra.persistence.pg_farmer_consent_repo import PgFarmerConsentRepo
from app.infra.persistence.pg_farmer_repo import PgFarmerRepo
from app.infra.persistence.pg_farmer_schemes_repo import PgFarmerSchemesRepo
from app.infra.persistence.pg_lab_soil_test_repo import PgLabSoilTestRepo
from app.infra.persistence.pg_plot_repo import PgPlotRepo
from app.infra.persistence.pg_qa_counters_repo import PgQaCountersRepo
from app.infra.persistence.pg_reading_repo import PgReadingRepo
from app.infra.persistence.pg_satellite_reading_repo import PgSatelliteReadingRepo
from app.infra.persistence.pg_season_economics_repo import PgSeasonEconomicsRepo
from app.infra.persistence.pg_season_operations_repo import PgSeasonOperationsRepo
from app.infra.persistence.pg_weather_forecast_repo import PgWeatherForecastRepo
from app.infra.persistence.pg_weather_station_reading_repo import PgWeatherStationReadingRepo
from app.infra.persistence.pg_yield_model_repo import PgYieldModelRepo
from app.jobs.ginger_daily import GingerDailyDeps, run_daily

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


async def build_and_start_scheduler(settings: Settings) -> AsyncIOScheduler | None:
    """Return a running scheduler with the ginger daily job registered.

    Returns ``None`` when ``GINGER_JOB_ENABLED`` is false.
    """
    if not settings.GINGER_JOB_ENABLED:
        log.info("ginger_scheduler.disabled", reason="GINGER_JOB_ENABLED=false")
        return None

    sessionmaker = _ensure_engine(settings)
    deps = GingerDailyDeps(
        reading_repo=PgReadingRepo(sessionmaker),
        plot_repo=PgPlotRepo(sessionmaker),
        crop_season_repo=PgCropSeasonRepo(sessionmaker),
        ai_suggestion_repo=PgAiSuggestionRepo(sessionmaker),
        farmer_repo=PgFarmerRepo(sessionmaker),
        sync_dsn=settings.DATABASE_URL_SYNC,
        weather_station_reading_repo=PgWeatherStationReadingRepo(sessionmaker),
        weather_forecast_repo=PgWeatherForecastRepo(sessionmaker),
        satellite_reading_repo=PgSatelliteReadingRepo(sessionmaker),
        farm_repo=PgFarmRepo(sessionmaker),
        lab_soil_test_repo=PgLabSoilTestRepo(sessionmaker),
        crop_scouting_repo=PgCropScoutingRepo(sessionmaker),
        season_economics_repo=PgSeasonEconomicsRepo(sessionmaker),
        season_operations_repo=PgSeasonOperationsRepo(sessionmaker),
        farmer_schemes_repo=PgFarmerSchemesRepo(sessionmaker),
        farmer_consent_repo=PgFarmerConsentRepo(sessionmaker),
        advisory_metrics_repo=PgAdvisoryMetricsRepo(sessionmaker),
        yield_model_repo=PgYieldModelRepo(sessionmaker),
        cluster_repo=PgClusterRepo(sessionmaker),
        qa_counters_repo=PgQaCountersRepo(sessionmaker),
    )

    scheduler = AsyncIOScheduler(timezone=settings.GINGER_JOB_TIMEZONE)

    async def _job_wrapper() -> None:
        try:
            written = await run_daily(deps)
            log.info("ginger_scheduler.tick_ok", advisories_written=written)
        except Exception:
            log.exception("ginger_scheduler.tick_failed")

    scheduler.add_job(
        _job_wrapper,
        trigger=CronTrigger(
            hour=settings.GINGER_JOB_HOUR,
            minute=settings.GINGER_JOB_MINUTE,
            timezone=settings.GINGER_JOB_TIMEZONE,
        ),
        id="ginger_daily",
        name="Ginger daily advisories",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,  # 1 hour: run late but not skip
    )
    scheduler.start()
    log.info(
        "ginger_scheduler.started",
        timezone=settings.GINGER_JOB_TIMEZONE,
        hour=settings.GINGER_JOB_HOUR,
        minute=settings.GINGER_JOB_MINUTE,
    )
    return scheduler


async def stop_scheduler(scheduler: AsyncIOScheduler) -> None:
    """Graceful shutdown; called from the lifespan finally-block."""
    scheduler.shutdown(wait=False)
    log.info("ginger_scheduler.stopped")


__all__ = ["build_and_start_scheduler", "stop_scheduler"]
