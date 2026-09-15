"""Wire the Round 14 advisory-delivery subscriber into the FastAPI lifespan.

Consumes ``suggestion.generated`` events (Postgres ``LISTEN agro_events``) and
drives ``deliver_advisory`` → WhatsApp. Same two-coroutine shape as the Round 13
advisory subscriber, and safe for the same reason (the atomic delivery claim):

* the **listener** reacts to each ``suggestion.generated`` NOTIFY in real time;
* the **reconciler** runs every ``ADVISORY_RECONCILE_SECONDS`` to reap stale
  ``in_flight`` rows (crashed workers) and process due ``pending`` deliveries
  whose NOTIFY was lost while no listener was connected. Its first sweep at
  startup recovers the down-time backlog.

Skipped entirely when ``ADVISORY_DELIVERY_ENABLED`` is false (tests/CI). When no
Meta WhatsApp token is configured (dev/staging), it uses the log-only sender, so
the whole path still runs end-to-end without a verified WABA.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import structlog

from app.application import deliver_advisory
from app.application.deliver_advisory import DeliverAdvisoryDeps
from app.application.ports.event_bus import EVENT_SUGGESTION_GENERATED
from app.application.ports.whatsapp_sender import WhatsappSender
from app.infra.events.pg_notify_bus import CHANNEL
from app.infra.events.pg_notify_listener import PgNotifyListener
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_ai_suggestion_repo import PgAiSuggestionRepo
from app.infra.persistence.pg_farmer_repo import PgFarmerRepo
from app.infra.whatsapp.log_only_sender import LogOnlyWhatsappSender
from app.infra.whatsapp.meta_cloud_sender import MetaCloudSettings, MetaCloudWhatsappSender
from app.lib import metrics

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


@dataclass
class DeliverySubscriberHandle:
    """Lifespan handle so the app can shut both coroutines down cleanly."""

    listener: PgNotifyListener
    reconciler_task: asyncio.Task[None]


async def build_and_start_delivery_subscriber(
    settings: Settings,
) -> DeliverySubscriberHandle | None:
    """Construct + start the listener and reconciler. None if disabled."""
    if not settings.ADVISORY_DELIVERY_ENABLED:
        log.info("delivery_subscriber.disabled", reason="ADVISORY_DELIVERY_ENABLED=false")
        return None

    sm = _ensure_engine(settings)
    deps = DeliverAdvisoryDeps(
        ai_suggestion_repo=PgAiSuggestionRepo(sm),
        farmer_repo=PgFarmerRepo(sm),
        sender=_build_sender(settings),
        template_name=settings.META_WHATSAPP_ADVISORY_TEMPLATE_NAME,
        require_review=settings.ADVISORY_REQUIRE_REVIEW,
    )

    async def _handle(envelope: dict[str, Any]) -> None:
        if envelope.get("event") != EVENT_SUGGESTION_GENERATED:
            return
        payload = envelope.get("payload") or {}
        raw = payload.get("suggestion_id")
        if raw is None:
            return
        try:
            suggestion_id = uuid.UUID(str(raw))
        except ValueError:
            log.warning("delivery_subscriber.bad_suggestion_id", value=raw)
            return
        await _deliver_one(suggestion_id, deps)

    listener = PgNotifyListener(settings.DATABASE_URL_SYNC, CHANNEL, _handle)
    await listener.start()
    reconciler = asyncio.create_task(_reconcile_loop(deps, settings), name="delivery-reconciler")
    log.info(
        "delivery_subscriber.started",
        reconcile_seconds=settings.ADVISORY_RECONCILE_SECONDS,
        stale_seconds=settings.ADVISORY_STALE_SECONDS,
        require_review=settings.ADVISORY_REQUIRE_REVIEW,
    )
    return DeliverySubscriberHandle(listener=listener, reconciler_task=reconciler)


async def stop_delivery_subscriber(handle: DeliverySubscriberHandle) -> None:
    handle.reconciler_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await handle.reconciler_task
    await handle.listener.stop()
    log.info("delivery_subscriber.stopped")


def _build_sender(settings: Settings) -> WhatsappSender:
    token = settings.META_WHATSAPP_TOKEN.get_secret_value()
    if token and settings.META_WHATSAPP_PHONE_NUMBER_ID:
        return MetaCloudWhatsappSender(
            MetaCloudSettings(
                graph_version=settings.META_WHATSAPP_GRAPH_VERSION,
                phone_number_id=settings.META_WHATSAPP_PHONE_NUMBER_ID,
                access_token=token,
            )
        )
    # No token (dev/staging): the path still runs, just against the log-only sender.
    log.warning("delivery_subscriber.no_whatsapp_token", note="using log-only sender")
    return LogOnlyWhatsappSender()


async def _deliver_one(suggestion_id: uuid.UUID, deps: DeliverAdvisoryDeps) -> None:
    try:
        result = await deliver_advisory.execute(
            suggestion_id=suggestion_id, deps=deps, now=datetime.now(UTC)
        )
        metrics.advisory_delivered_total.labels(outcome=result.outcome).inc()
    except Exception:
        # One bad suggestion must never kill the listener or reconciler.
        log.exception("delivery_subscriber.deliver_failed", suggestion_id=str(suggestion_id))
        metrics.advisory_delivered_total.labels(outcome="error").inc()


async def _reconcile_loop(deps: DeliverAdvisoryDeps, settings: Settings) -> None:
    interval = settings.ADVISORY_RECONCILE_SECONDS
    stale = timedelta(seconds=settings.ADVISORY_STALE_SECONDS)
    while True:
        try:
            now = datetime.now(UTC)
            reverted = await deps.ai_suggestion_repo.revert_stale_deliveries(now - stale, now)
            if reverted:
                log.info("delivery_subscriber.reaped_stale", count=reverted)
            due = await deps.ai_suggestion_repo.list_due_deliveries(
                now, require_review=deps.require_review, limit=100
            )
            for suggestion_id in due:
                await _deliver_one(suggestion_id, deps)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("delivery_subscriber.reconcile_failed")
        await asyncio.sleep(interval)


__all__ = [
    "DeliverySubscriberHandle",
    "build_and_start_delivery_subscriber",
    "stop_delivery_subscriber",
]
