"""End-to-end telemetry ingest use case.


Composes the Phase-2 pieces into a single pipeline:


   1. Validation orchestrator runs the 4 gates (Round 5)
   2. Reading repository persists with idempotent UPSERT (Round 6)
   3. Event bus publishes ``telemetry.ingested`` on success (Round 6)


Each step uses a Round-4 Protocol port - the use case never imports infra.
The concrete adapters (PgReadingRepo, PgNotifyEventBus) are constructed
by main.py's lifespan and passed in via :class:`IngestDeps`.


Per ``.cursorrules`` #13 this file imports domain + ports + stdlib only.
No fastapi, sqlalchemy, paho, etc.
"""


from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application import validate_reading
from app.application.ports.event_bus import EVENT_TELEMETRY_INGESTED, EventBus
from app.application.ports.reading_repo import ReadingRepo
from app.domain.sensor import Reading


@dataclass(frozen=True, slots=True)
class IngestDeps:
    """Ports the ingest use case needs.


    Constructed once at app startup with the concrete adapters; the broker
    drain loop passes the same instance into every ``execute`` call. Frozen
    so a misbehaving caller can't swap the bus mid-stream.
    """


    reading_repo: ReadingRepo
    event_bus: EventBus




@dataclass(frozen=True, slots=True)
class IngestResult:
    """What happened to one Reading.


    * ``reading_id`` is None when the row was a duplicate on
      ``(node_id, recorded_at)`` - the schema's idempotency guarantee.
      Callers treat None as success (the row exists) but increment
      ``metrics.ingest_dropped_total`` with reason='duplicate'.
    * ``validation_warn`` mirrors the Reading's flag after the gates ran.
    * ``flags`` is the gate-by-gate breakdown for observability.
    """


    reading_id: int | None
    validation_warn: bool
    flags: dict[str, str]




async def execute(reading: Reading, deps: IngestDeps) -> IngestResult:
    """Run one telemetry message through the full ingest pipeline.


    Side effects (in order):


    1. Calls :func:`app.application.validate_reading.execute` to run the
       4 gates. Returns the original Reading on clean or a new instance
       with ``validation_warn=True`` and ``sensor_health_json`` populated.
    2. Calls :meth:`ReadingRepo.save` with the validated Reading. Returns
       the new ``reading_id`` or None on duplicate.
    3. If a row was actually inserted (non-None id), publishes
       ``telemetry.ingested`` on the event bus with a small payload
       (IDs only - per Roadmap §1.3, NEVER full domain objects).


    Failure modes:


    * The repo or bus may raise. The caller (broker drain loop) catches
      and routes to the dropped-with-reason metric. We deliberately do
      NOT swallow exceptions here - that would hide infrastructure
      failures (.cursorrules #4).
    * If validate_reading.execute raises - that's a bug in the gates,
      not a runtime data issue - it propagates and the broker drains
      it as an unexpected error.


    The use case is intentionally pure orchestration: every line is a
    port call. No SQL, no JSON, no MQTT here.
    """
    validated = await validate_reading.execute(reading, deps.reading_repo)
    reading_id = await deps.reading_repo.save(validated)


    if reading_id is not None:
        # Payload carries IDs and a minimal status flag - subscribers
        # (Phase 4+ rule engine, dashboard live view) re-fetch from the
        # repo by reading_id when they need the full object. Keeps each
        # NOTIFY well below the 7500-byte cap (Round 6's PgNotifyEventBus
        # also enforces this server-side).
        payload: dict[str, Any] = {
            "plot_id": validated.plot_id,
            "reading_id": reading_id,
            "validation_warn": validated.validation_warn,
        }
        await deps.event_bus.publish(EVENT_TELEMETRY_INGESTED, payload)


    flags = {
        k: v
        for k, v in validated.sensor_health_json.items()
        if isinstance(v, str)  # validation flags are str; other entries may be richer
    }
    return IngestResult(
        reading_id=reading_id,
        validation_warn=validated.validation_warn,
        flags=flags,
    )




__all__ = ["IngestDeps", "IngestResult", "execute"]
