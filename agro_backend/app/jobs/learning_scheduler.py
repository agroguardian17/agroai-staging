"""Start/stop the nightly learning-writer job.

A small AsyncIOScheduler with one cron job that sweeps farmer_actions into
ai_learning_log (see ``app.application.write_learnings``). DB-only, no external
calls. Skipped when ``LEARNING_JOB_ENABLED`` is false (tests/CI).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application import write_learnings
from app.application.write_learnings import WriteLearningsDeps
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_learning_repo import PgLearningRepo

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


async def build_and_start_learning_scheduler(settings: Settings) -> AsyncIOScheduler | None:
    if not settings.LEARNING_JOB_ENABLED:
        log.info("learning_scheduler.disabled", reason="LEARNING_JOB_ENABLED=false")
        return None

    sm = _ensure_engine(settings)
    deps = WriteLearningsDeps(
        learning_repo=PgLearningRepo(sm), batch_limit=settings.LEARNING_BATCH_LIMIT
    )
    scheduler = AsyncIOScheduler(timezone=settings.GINGER_JOB_TIMEZONE)

    async def _job() -> None:
        try:
            res = await write_learnings.execute(deps=deps, now=datetime.now(UTC))
            log.info("learning_scheduler.tick_ok", written=res.written)
        except Exception:
            log.exception("learning_scheduler.tick_failed")

    scheduler.add_job(
        _job,
        trigger=CronTrigger(
            hour=settings.LEARNING_JOB_HOUR,
            minute=settings.LEARNING_JOB_MINUTE,
            timezone=settings.GINGER_JOB_TIMEZONE,
        ),
        id="ai_learning_writer",
        name="Nightly learning writer",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,
    )
    scheduler.start()
    log.info(
        "learning_scheduler.started",
        hour=settings.LEARNING_JOB_HOUR,
        minute=settings.LEARNING_JOB_MINUTE,
    )
    return scheduler


async def stop_learning_scheduler(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
    log.info("learning_scheduler.stopped")


__all__ = ["build_and_start_learning_scheduler", "stop_learning_scheduler"]
