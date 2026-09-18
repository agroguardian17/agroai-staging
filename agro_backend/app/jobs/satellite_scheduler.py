"""Start/stop the satellite fetch job (Domain 14).

Mirrors ``forecast_scheduler``: an ``AsyncIOScheduler`` with one cron job that
refreshes each active ginger plot's Sentinel-2 / Sentinel-1 indices into
``satellite_data`` via the CDSE Sentinel Hub Statistical API. Skipped when
``SATELLITE_JOB_ENABLED`` is false (the default — it stays off until a CDSE
OAuth client is provisioned and plots have boundary polygons). A shared httpx
client is held for the process lifetime and closed on shutdown.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application import refresh_satellite
from app.application.refresh_satellite import RefreshSatelliteDeps
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_crop_season_repo import PgCropSeasonRepo
from app.infra.persistence.pg_plot_repo import PgPlotRepo
from app.infra.persistence.pg_satellite_reading_repo import PgSatelliteReadingRepo
from app.infra.satellite.cdse_provider import CdseSentinelHubProvider, CdseSettings

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


class SatelliteSchedulerHandle:
    """Lifespan handle: the scheduler plus the shared httpx client to close."""

    def __init__(self, scheduler: AsyncIOScheduler, client: httpx.AsyncClient) -> None:
        self.scheduler = scheduler
        self.client = client


async def build_and_start_satellite_scheduler(
    settings: Settings,
) -> SatelliteSchedulerHandle | None:
    if not settings.SATELLITE_JOB_ENABLED:
        log.info("satellite_scheduler.disabled", reason="SATELLITE_JOB_ENABLED=false")
        return None
    if (
        not settings.COPERNICUS_CLIENT_ID
        or not settings.COPERNICUS_CLIENT_SECRET.get_secret_value()
    ):
        log.warning(
            "satellite_scheduler.no_credentials", reason="COPERNICUS_CLIENT_ID/SECRET unset"
        )
        return None

    sm = _ensure_engine(settings)
    client = httpx.AsyncClient(timeout=30.0)
    provider = CdseSentinelHubProvider(
        CdseSettings(
            client_id=settings.COPERNICUS_CLIENT_ID,
            client_secret=settings.COPERNICUS_CLIENT_SECRET.get_secret_value(),
            base_url=settings.COPERNICUS_BASE_URL,
            token_url=settings.COPERNICUS_TOKEN_URL,
        ),
        client=client,
    )
    deps = RefreshSatelliteDeps(
        crop_season_repo=PgCropSeasonRepo(sm),
        plot_repo=PgPlotRepo(sm),
        satellite_provider=provider,
        satellite_reading_repo=PgSatelliteReadingRepo(sm),
        lookback_days=settings.SATELLITE_LOOKBACK_DAYS,
        pipeline_version=settings.SATELLITE_PIPELINE_VERSION,
    )

    scheduler = AsyncIOScheduler(timezone=settings.GINGER_JOB_TIMEZONE)

    async def _job() -> None:
        try:
            res = await refresh_satellite.execute(deps=deps, today=datetime.now(UTC).date())
            log.info(
                "satellite_scheduler.tick_ok",
                plots=res.plots,
                skipped_no_polygon=res.skipped_no_polygon,
                optical_scenes=res.optical_scenes,
                sar_scenes=res.sar_scenes,
                failed_plots=res.failed_plots,
            )
        except Exception:
            log.exception("satellite_scheduler.tick_failed")

    scheduler.add_job(
        _job,
        trigger=CronTrigger(
            hour=settings.SATELLITE_JOB_HOUR,
            minute=settings.SATELLITE_JOB_MINUTE,
            timezone=settings.GINGER_JOB_TIMEZONE,
        ),
        id="satellite_fetch",
        name="Daily satellite index fetch",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,
    )
    scheduler.start()
    log.info(
        "satellite_scheduler.started",
        hour=settings.SATELLITE_JOB_HOUR,
        minute=settings.SATELLITE_JOB_MINUTE,
        lookback_days=settings.SATELLITE_LOOKBACK_DAYS,
    )
    return SatelliteSchedulerHandle(scheduler, client)


async def stop_satellite_scheduler(handle: SatelliteSchedulerHandle) -> None:
    handle.scheduler.shutdown(wait=False)
    await handle.client.aclose()
    log.info("satellite_scheduler.stopped")


__all__ = [
    "SatelliteSchedulerHandle",
    "build_and_start_satellite_scheduler",
    "stop_satellite_scheduler",
]
