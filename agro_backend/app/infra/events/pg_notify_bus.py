"""Postgres ``LISTEN``/``NOTIFY`` adapter for :class:`~app.application.ports.event_bus.EventBus`.


Round 6 ships the **publish** side only. Subscribers (a long-lived
``LISTEN`` task driving in-process consumers) are not needed in the Fast
Path - all observability flows through Prometheus + structlog. When a
real subscriber lands we extend the Protocol with ``subscribe``; this
file is the canonical place to add the new behaviour.


Why ``NOTIFY`` and not Redis/NATS/Kafka at pilot scale:


* Zero new infrastructure (the DB is already there).
* Transactional: ``NOTIFY`` is delivered if and only if the enclosing
  transaction commits. Failed writes never produce orphan events.
* Sufficient throughput at <100 farms (the 8000-byte payload cap is the
  real ceiling, not raw throughput; we keep payloads tiny by design).


Payload size guard: Postgres truncates ``NOTIFY`` payloads at 8000 bytes.
We refuse to publish anything over 7500 to leave margin for the envelope.
Producers should always emit IDs, not full domain objects (Roadmap 1.3).
"""


from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Single canonical channel - all events flow on one topic and consumers
# discriminate by the ``event`` field. Multiple channels could be added
# later (per-event-name) if subscriber selectivity matters; until then
# one channel is simpler.
CHANNEL: str = "agro_events"


# Postgres hard cap is 8000 bytes for the payload. Leave a 500-byte
# margin to account for any future envelope evolution.
MAX_PAYLOAD_BYTES: int = 7500




class PgNotifyEventBus:
    """Concrete :class:`EventBus` over Postgres ``LISTEN``/``NOTIFY``."""


    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker


    async def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        envelope = {
            "event": event_name,
            "ts": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        # ``default=str`` lets us serialise UUIDs / Decimals without each
        # producer pre-converting. Subscribers parse the JSON back; strings
        # are fine on the wire.
        body = json.dumps(envelope, default=str, separators=(",", ":"))
        size = len(body.encode("utf-8"))
        if size > MAX_PAYLOAD_BYTES:
            raise ValueError(
                f"event {event_name!r} payload is {size} bytes, exceeds "
                f"{MAX_PAYLOAD_BYTES}-byte safety margin; emit IDs not "
                "full objects (Roadmap §1.3)"
            )
        # Postgres' ``pg_notify(channel, payload)`` function is the
        # programmatic equivalent of the bare ``NOTIFY`` statement and
        # accepts parameterised payload binding (the bare NOTIFY syntax
        # does not - it requires string interpolation, which we refuse).
        stmt = text("SELECT pg_notify(:channel, :body)")
        async with self._sm() as session:
            await session.execute(stmt, {"channel": CHANNEL, "body": body})
            await session.commit()




__all__ = ["CHANNEL", "MAX_PAYLOAD_BYTES", "PgNotifyEventBus"]
