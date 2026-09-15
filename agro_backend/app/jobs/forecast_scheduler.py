"""Start/stop the nightly weather-forecast job (Round 18).

Mirrors ``ginger_scheduler``: an ``AsyncIOScheduler`` with one cron job that
refreshes every farm's daily forecast into ``weather_forecasts``. Skipped when
``FORECAST_JOB_ENABLED`` is false (tests/CI). A shared httpx client is held for
the process lifetime and closed on shutdown.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application import refresh_forecasts
from app.application.refresh_forecasts import RefreshForecastsDeps
from app.infra.forecast.open_meteo import OpenMeteoForecastProvider, OpenMeteoSettings
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_farm_repo import PgFarmRepo
from app.infra.persistence.pg_weather_forecast_repo import PgWeatherForecastRepo

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


class ForecastSchedulerHandle:
    """Lifespan handle: the scheduler plus the shared httpx client to close."""

    def __init__(self, scheduler: AsyncIOScheduler, client: httpx.AsyncClient) -> None:
        self.scheduler = scheduler
        self.client = client


async def build_and_start_forecast_scheduler(
    settings: Settings,
) -> ForecastSchedulerHandle | None:
    if not settings.FORECAST_JOB_ENABLED:
        log.info("forecast_scheduler.disabled", reason="FORECAST_JOB_ENABLED=false")
        return None

    sm = _ensure_engine(settings)
    client = httpx.AsyncClient(timeout=10.0)
    deps = RefreshForecastsDeps(
        farm_repo=PgFarmRepo(sm),
        forecast_provider=OpenMeteoForecastProvider(
            OpenMeteoSettings(base_url=settings.OPEN_METEO_BASE_URL), client=client
        ),
        forecast_repo=PgWeatherForecastRepo(sm),
        source_api=settings.FORECAST_SOURCE_API,
        days=settings.FORECAST_DAYS,
    )

    scheduler = AsyncIOScheduler(timezone=settings.GINGER_JOB_TIMEZONE)

    async def _job() -> None:
        try:
            res = await refresh_forecasts.execute(deps=deps, now=datetime.now(UTC))
            log.info(
                "forecast_scheduler.tick_ok",
                farms=res.farms,
                rows_written=res.rows_written,
                failed_farms=res.failed_farms,
            )
        except Exception:
            log.exception("forecast_scheduler.tick_failed")

    scheduler.add_job(
        _job,
        trigger=CronTrigger(
            hour=settings.FORECAST_JOB_HOUR,
            minute=settings.FORECAST_JOB_MINUTE,
            timezone=settings.GINGER_JOB_TIMEZONE,
        ),
        id="weather_forecast",
        name="Nightly weather forecast",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,
    )
    scheduler.start()
    log.info(
        "forecast_scheduler.started",
        hour=settings.FORECAST_JOB_HOUR,
        minute=settings.FORECAST_JOB_MINUTE,
        days=settings.FORECAST_DAYS,
    )
    return ForecastSchedulerHandle(scheduler, client)


async def stop_forecast_scheduler(handle: ForecastSchedulerHandle) -> None:
    handle.scheduler.shutdown(wait=False)
    await handle.client.aclose()
    log.info("forecast_scheduler.stopped")


__all__ = [
    "ForecastSchedulerHandle",
    "build_and_start_forecast_scheduler",
    "stop_forecast_scheduler",
]
