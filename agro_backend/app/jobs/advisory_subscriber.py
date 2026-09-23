"""Wire the Round 13 advisory subscriber into the FastAPI lifespan.

Consumes ``alert.created`` events (Postgres ``LISTEN agro_events``) and drives
``dispatch_advisory`` → ``compose_advisory`` → Claude → ``ai_suggestions``.

Two coroutines share the work, both funnelling through ``dispatch_advisory``
(whose atomic claim makes the concurrency safe):

* the **listener** reacts to each ``alert.created`` NOTIFY in real time;
* the **reconciler** runs every ``ADVISORY_RECONCILE_SECONDS`` to (a) reap stale
  ``in_flight`` rows (crashed workers) and (b) process due ``pending`` rows whose
  NOTIFY was lost while no listener was connected (``pg_notify`` is
  fire-and-forget). Its first sweep at startup recovers the down-time backlog.

Skipped entirely when ``ADVISORY_SUBSCRIBER_ENABLED`` is false (tests/CI).
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import structlog

from app.application import dispatch_advisory
from app.application.compose_advisory import ComposeAdvisoryDeps
from app.application.dispatch_advisory import DispatchAdvisoryDeps
from app.application.ports.chat_model import ChatModel
from app.application.ports.event_bus import EVENT_ALERT_CREATED
from app.config import ModelRole
from app.infra.events.pg_notify_bus import CHANNEL, PgNotifyEventBus
from app.infra.events.pg_notify_listener import PgNotifyListener
from app.infra.http.deps import _ensure_engine
from app.infra.llm.claude_chat import ClaudeChatModel, ClaudeSettings
from app.infra.llm.log_only_chat import LogOnlyChatModel
from app.infra.persistence.pg_advisory_audit_repo import PgAdvisoryAuditRepo
from app.infra.persistence.pg_ai_suggestion_repo import PgAiSuggestionRepo
from app.infra.persistence.pg_alert_repo import PgAlertRepo
from app.infra.persistence.pg_crop_season_repo import PgCropSeasonRepo
from app.infra.persistence.pg_plot_repo import PgPlotRepo
from app.infra.persistence.pg_reading_repo import PgReadingRepo
from app.lib import metrics

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


@dataclass
class AdvisorySubscriberHandle:
    """Lifespan handle so the app can shut both coroutines down cleanly."""

    listener: PgNotifyListener
    reconciler_task: asyncio.Task[None]


async def build_and_start_advisory_subscriber(
    settings: Settings,
) -> AdvisorySubscriberHandle | None:
    """Construct + start the listener and reconciler. None if disabled."""
    if not settings.ADVISORY_SUBSCRIBER_ENABLED:
        log.info("advisory_subscriber.disabled", reason="ADVISORY_SUBSCRIBER_ENABLED=false")
        return None

    sm = _ensure_engine(settings)
    alert_repo = PgAlertRepo(sm)
    event_bus = PgNotifyEventBus(sm)
    compose_deps = ComposeAdvisoryDeps(
        alert_repo=alert_repo,
        plot_repo=PgPlotRepo(sm),
        crop_season_repo=PgCropSeasonRepo(sm),
        reading_repo=PgReadingRepo(sm),
        ai_suggestion_repo=PgAiSuggestionRepo(sm),
        chat_model=_build_chat_model(settings),
        chat_model_name=settings.model_id_for(ModelRole.PRIMARY),
        advisory_audit_repo=PgAdvisoryAuditRepo(sm),
    )
    deps = DispatchAdvisoryDeps(
        alert_repo=alert_repo, compose_deps=compose_deps, event_bus=event_bus
    )

    async def _handle(envelope: dict[str, Any]) -> None:
        if envelope.get("event") != EVENT_ALERT_CREATED:
            return
        payload = envelope.get("payload") or {}
        alert_id = payload.get("alert_id")
        if alert_id is None:
            return
        await _dispatch_one(int(alert_id), deps)

    listener = PgNotifyListener(settings.DATABASE_URL_SYNC, CHANNEL, _handle)
    await listener.start()
    reconciler = asyncio.create_task(_reconcile_loop(deps, settings), name="advisory-reconciler")
    log.info(
        "advisory_subscriber.started",
        reconcile_seconds=settings.ADVISORY_RECONCILE_SECONDS,
        stale_seconds=settings.ADVISORY_STALE_SECONDS,
    )
    return AdvisorySubscriberHandle(listener=listener, reconciler_task=reconciler)


async def stop_advisory_subscriber(handle: AdvisorySubscriberHandle) -> None:
    handle.reconciler_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await handle.reconciler_task
    await handle.listener.stop()
    log.info("advisory_subscriber.stopped")


def _build_chat_model(settings: Settings) -> ChatModel:
    key = settings.ANTHROPIC_API_KEY.get_secret_value()
    if key:
        return ClaudeChatModel(ClaudeSettings(api_key=key))
    # No key (staging/dev): compose still runs, just against the log-only model.
    log.warning("advisory_subscriber.no_anthropic_key", note="using log-only chat model")
    return LogOnlyChatModel()


async def _dispatch_one(alert_id: int, deps: DispatchAdvisoryDeps) -> None:
    try:
        result = await dispatch_advisory.execute(
            alert_id=alert_id, deps=deps, now=datetime.now(UTC)
        )
        metrics.advisory_composed_total.labels(outcome=result.outcome).inc()
    except Exception:
        # One bad alert must never kill the listener or reconciler.
        log.exception("advisory_subscriber.dispatch_failed", alert_id=alert_id)
        metrics.advisory_composed_total.labels(outcome="error").inc()


async def _reconcile_loop(deps: DispatchAdvisoryDeps, settings: Settings) -> None:
    interval = settings.ADVISORY_RECONCILE_SECONDS
    stale = timedelta(seconds=settings.ADVISORY_STALE_SECONDS)
    while True:
        try:
            now = datetime.now(UTC)
            reverted = await deps.alert_repo.revert_stale_in_flight(now - stale, now)
            if reverted:
                log.info("advisory_subscriber.reaped_stale", count=reverted)
            due = await deps.alert_repo.list_due_advisory_alerts(now, limit=100)
            for alert_id in due:
                await _dispatch_one(alert_id, deps)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("advisory_subscriber.reconcile_failed")
        await asyncio.sleep(interval)


__all__ = [
    "AdvisorySubscriberHandle",
    "build_and_start_advisory_subscriber",
    "stop_advisory_subscriber",
]
