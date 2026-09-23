"""Start/stop the D12 weekly-QA-digest job (D12_QA_WORKFLOW §5.4).

A small AsyncIOScheduler with one cron job that fires Sunday 18:00 IST, builds
the agronomist + KB-author documents from the four QA tables, and writes them to
``QA_DIGEST_DIR``. DB-only reads, no external calls. Skipped when
``QA_DIGEST_JOB_ENABLED`` is false (tests/CI).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application.build_qa_digest import build_weekly_digest
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_qa_digest_repo import PgQaDigestRepo
from app.infra.qa_digest_writer import write_digest_docs
from app.lib.time import now_ist

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


async def build_and_start_qa_digest_scheduler(settings: Settings) -> AsyncIOScheduler | None:
    if not settings.QA_DIGEST_JOB_ENABLED:
        log.info("qa_digest_scheduler.disabled", reason="QA_DIGEST_JOB_ENABLED=false")
        return None

    sm = _ensure_engine(settings)
    repo = PgQaDigestRepo(sm)
    out_dir = settings.QA_DIGEST_DIR
    top_fp = settings.QA_DIGEST_TOP_FP_RULES
    scheduler = AsyncIOScheduler(timezone=settings.GINGER_JOB_TIMEZONE)

    async def _job() -> None:
        try:
            digest = await build_weekly_digest(repo=repo, now=now_ist(), top_fp_rules=top_fp)
            paths = write_digest_docs(out_dir, [digest.weekly_report, digest.bias_digest])
            log.info(
                "qa_digest_scheduler.tick_ok",
                week_start=digest.data.week_start.isoformat(),
                files=[str(p) for p in paths],
                classified=digest.data.classified_count,
            )
        except Exception:
            log.exception("qa_digest_scheduler.tick_failed")

    scheduler.add_job(
        _job,
        trigger=CronTrigger(
            day_of_week=settings.QA_DIGEST_JOB_DAY_OF_WEEK,
            hour=settings.QA_DIGEST_JOB_HOUR,
            minute=settings.QA_DIGEST_JOB_MINUTE,
            timezone=settings.GINGER_JOB_TIMEZONE,
        ),
        id="qa_weekly_digest",
        name="D12 weekly QA digest",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,  # 1 hour: run late but not skip
    )
    scheduler.start()
    log.info(
        "qa_digest_scheduler.started",
        day_of_week=settings.QA_DIGEST_JOB_DAY_OF_WEEK,
        hour=settings.QA_DIGEST_JOB_HOUR,
        minute=settings.QA_DIGEST_JOB_MINUTE,
    )
    return scheduler


async def stop_qa_digest_scheduler(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
    log.info("qa_digest_scheduler.stopped")


__all__ = ["build_and_start_qa_digest_scheduler", "stop_qa_digest_scheduler"]
