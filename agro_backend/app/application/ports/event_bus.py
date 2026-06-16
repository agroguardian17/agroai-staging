"""Domain event bus port.


The application emits domain events (``telemetry.ingested``,
``alert.created``, ``plot.crop_changed``, ...) on important state
transitions. Consumers (dashboard live view, learning-loop trigger,
metrics) subscribe.


Concrete pilot implementation in Round 6 is Postgres ``LISTEN``/``NOTIFY``
(``app.infra.events.pg_notify_bus.PgNotifyEventBus``) - zero new infra,
piggybacks on the database we already have. When throughput exceeds what
NOTIFY can handle (NOTIFY's 8000-byte payload cap is the practical limit),
the same Protocol lets us swap in NATS, Redis Streams, or Kafka with no
domain or use-case changes (Roadmap Part 12.6 - migration paths).


Per the Roadmap event catalogue (Part 1.3), payloads carry only IDs, not
full domain objects - consumers re-fetch from repositories. Keeps each
event well under 8000 bytes and avoids stale-copy races.
"""


from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Canonical event names. Defined once here so producer and consumer code
# import the same string constant - typos become compile-time
# (well, AttributeError-time) failures rather than silently-dropped
# subscribe calls.
# ---------------------------------------------------------------------------
EVENT_TELEMETRY_INGESTED = "telemetry.ingested"
"""Emitted by the ingest use case after a successful row write. Payload:
``{"plot_id": str, "reading_id": int, "validation_warn": bool}``."""


EVENT_ALERT_CREATED = "alert.created"
"""Emitted by the hot/warm rule paths when an alert row is inserted.
Payload: ``{"alert_id": int, "plot_id": str, "alert_type": str,
"severity": str}``."""


EVENT_ALERT_DISPATCHED = "alert.dispatched"
"""Emitted by the notification dispatcher (Round 7) after a successful
send on at least one channel. Payload:
``{"alert_id": int, "channels": [str], "dispatch_status": str}``."""


EVENT_PLOT_CROP_CHANGED = "plot.crop_changed"
"""Emitted by the crop-change wizard backend (Round 9). Payload:
``{"plot_id": str, "season_id": str, "crop_name_english": str}``."""


EVENT_SUGGESTION_GENERATED = "suggestion.generated"
"""Emitted by the AI advisory job (Round 13) after writing an
``ai_suggestions`` row. Payload:
``{"suggestion_id": str, "plot_id": str, "confidence_band": str}``."""


EVENT_DEVICE_OFFLINE = "device.offline"
"""Emitted by the heartbeat watchdog. Payload: ``{"device_id": str,
"last_seen_at": "<iso8601>"}``."""


EVENT_DEVICE_ONLINE = "device.online"
"""Reverse - emitted when a previously-offline device sends again.
Same payload shape as ``device.offline``."""




@runtime_checkable
class EventBus(Protocol):
    """Publish-only Protocol for the pilot.


    Subscription is provider-specific (Postgres NOTIFY channels need a
    long-lived ``LISTEN`` task; NATS uses subjects; Redis uses streams)
    and intentionally lives outside this Protocol. The pilot has no
    in-process subscribers - all observability flows through
    Prometheus + structlog. When we add an in-process subscriber, this
    Protocol grows a ``subscribe`` method then.
    """


    async def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        """Emit one event.


        ``payload`` MUST be JSON-serialisable. Implementations that go
        over Postgres NOTIFY MUST raise if the serialised event exceeds
        ~7500 bytes (8000-byte hard cap with margin) - Round 6 enforces
        this. Producers should always emit IDs, not full objects.
        """
        ...




__all__ = [
    "EVENT_ALERT_CREATED",
    "EVENT_ALERT_DISPATCHED",
    "EVENT_DEVICE_OFFLINE",
    "EVENT_DEVICE_ONLINE",
    "EVENT_PLOT_CROP_CHANGED",
    "EVENT_SUGGESTION_GENERATED",
    "EVENT_TELEMETRY_INGESTED",
    "EventBus",
]
