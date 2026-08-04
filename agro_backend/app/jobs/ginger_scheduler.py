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
from app.infra.persistence.pg_ai_suggestion_repo import PgAiSuggestionRepo
from app.infra.persistence.pg_crop_season_repo import PgCropSeasonRepo
from app.infra.persistence.pg_plot_repo import PgPlotRepo
from app.infra.persistence.pg_reading_repo import PgReadingRepo
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
        sync_dsn=settings.DATABASE_URL_SYNC,
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
