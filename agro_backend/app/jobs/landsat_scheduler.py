"""Start/stop the Landsat LST fetch job (Domain 14 thermal / CWSI).

Mirrors ``satellite_scheduler``: one cron job refreshes each active ginger
plot's land-surface temperature into ``satellite_data`` (``landsat8`` rows) via
the USGS M2M API. Off unless ``LANDSAT_JOB_ENABLED`` and USGS credentials are
set. A shared httpx client is held for the process lifetime.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application import refresh_landsat_lst
from app.application.refresh_landsat_lst import RefreshLandsatDeps
from app.infra.http.deps import _ensure_engine
from app.infra.lst.usgs_m2m import UsgsM2mLstProvider, UsgsM2mSettings
from app.infra.persistence.pg_crop_season_repo import PgCropSeasonRepo
from app.infra.persistence.pg_plot_repo import PgPlotRepo
from app.infra.persistence.pg_satellite_reading_repo import PgSatelliteReadingRepo

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


class LandsatSchedulerHandle:
    def __init__(self, scheduler: AsyncIOScheduler, client: httpx.AsyncClient) -> None:
        self.scheduler = scheduler
        self.client = client


async def build_and_start_landsat_scheduler(settings: Settings) -> LandsatSchedulerHandle | None:
    if not settings.LANDSAT_JOB_ENABLED:
        log.info("landsat_scheduler.disabled", reason="LANDSAT_JOB_ENABLED=false")
        return None
    if not settings.USGS_M2M_USERNAME or not settings.USGS_M2M_TOKEN.get_secret_value():
        log.warning("landsat_scheduler.no_credentials", reason="USGS_M2M_USERNAME/TOKEN unset")
        return None

    sm = _ensure_engine(settings)
    client = httpx.AsyncClient(timeout=60.0)
    provider = UsgsM2mLstProvider(
        UsgsM2mSettings(
            username=settings.USGS_M2M_USERNAME,
            token=settings.USGS_M2M_TOKEN.get_secret_value(),
        ),
        client=client,
    )
    deps = RefreshLandsatDeps(
        crop_season_repo=PgCropSeasonRepo(sm),
        plot_repo=PgPlotRepo(sm),
        lst_provider=provider,
        satellite_reading_repo=PgSatelliteReadingRepo(sm),
    )

    scheduler = AsyncIOScheduler(timezone=settings.GINGER_JOB_TIMEZONE)

    async def _job() -> None:
        try:
            res = await refresh_landsat_lst.execute(deps=deps, today=datetime.now(UTC).date())
            log.info(
                "landsat_scheduler.tick_ok",
                plots=res.plots,
                skipped_no_polygon=res.skipped_no_polygon,
                scenes=res.scenes,
                failed_plots=res.failed_plots,
            )
        except Exception:
            log.exception("landsat_scheduler.tick_failed")

    scheduler.add_job(
        _job,
        trigger=CronTrigger(
            hour=settings.LANDSAT_JOB_HOUR,
            minute=settings.LANDSAT_JOB_MINUTE,
            timezone=settings.GINGER_JOB_TIMEZONE,
        ),
        id="landsat_lst_fetch",
        name="Daily Landsat LST fetch",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,
    )
    scheduler.start()
    log.info(
        "landsat_scheduler.started",
        hour=settings.LANDSAT_JOB_HOUR,
        minute=settings.LANDSAT_JOB_MINUTE,
    )
    return LandsatSchedulerHandle(scheduler, client)


async def stop_landsat_scheduler(handle: LandsatSchedulerHandle) -> None:
    handle.scheduler.shutdown(wait=False)
    await handle.client.aclose()
    log.info("landsat_scheduler.stopped")


__all__ = [
    "LandsatSchedulerHandle",
    "build_and_start_landsat_scheduler",
    "stop_landsat_scheduler",
]
