"""Integration tests for :class:`~app.infra.events.pg_notify_bus.PgNotifyEventBus`.


Tests cover:
  * Protocol satisfaction.
  * publish() emits a NOTIFY on the canonical channel.
  * Payload size guard rejects oversized events.


The "did the NOTIFY actually fire" assertion uses a raw asyncpg listener
on the same channel - small, real, no mocking - because that's the
behaviour Round 7 consumers will depend on.
"""


from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator

import asyncpg  # type: ignore[import-untyped]
import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.application.ports.event_bus import EVENT_TELEMETRY_INGESTED, EventBus
from app.infra.events.pg_notify_bus import (
    CHANNEL,
    MAX_PAYLOAD_BYTES,
    PgNotifyEventBus,
)
from app.infra.persistence.engine import make_async_engine, make_sessionmaker

SYNC_URL = os.getenv("DATABASE_URL_SYNC", "postgresql://agro:agro@localhost:5433/agro")
ASYNC_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://agro:agro@localhost:5433/agro",
)




def _asyncpg_connect_kwargs() -> dict[str, object]:
    """Build connect kwargs for asyncpg by parsing ASYNC_URL via SQLAlchemy.


    Why ``make_url`` and not ``urlsplit`` or os.environ directly:


    * ``urlsplit`` puts everything after the first '/' into ``path``, not
      ``netloc``, which corrupts passwords containing slashes (the dev
      compose generates base64-style passwords that can include '/', '+'
      and '='). ``make_url`` uses a libpq-aware parser that handles these.
    * Reading discrete ``POSTGRES_*`` env vars works IF those vars are
      reliably set in every shell that runs the tests - which isn't true
      when the user only exports ``DATABASE_URL_SYNC`` with the password
      inline. Parsing the URL we already trust as the source of truth
      (it works for psycopg2 via ``create_engine``) keeps the two paths
      consistent.
    """
    url = make_url(ASYNC_URL)
    return {
        "user": url.username or "",
        "password": url.password or "",
        "host": url.host or "localhost",
        "port": url.port or 5432,
        "database": url.database or "",
    }




def _db_available() -> bool:
    try:
        eng = create_engine(SYNC_URL)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
    except Exception:
        return False
    return True




pytestmark = pytest.mark.skipif(
    not _db_available(),
    reason="Postgres not reachable; run on the Mac dev stack after `alembic upgrade head`.",
)




@pytest_asyncio.fixture
async def bus() -> AsyncIterator[PgNotifyEventBus]:
    eng = make_async_engine(ASYNC_URL, pool_size=2, max_overflow=1)
    sm = make_sessionmaker(eng)
    yield PgNotifyEventBus(sm)
    await eng.dispose()




@pytest_asyncio.fixture
async def listener() -> AsyncIterator[asyncpg.Connection]:
    """Raw asyncpg listener on CHANNEL - the realistic Round 7 subscriber shape."""
    conn = await asyncpg.connect(**_asyncpg_connect_kwargs())
    yield conn
    await conn.close()




# ===========================================================================
# Protocol check
# ===========================================================================
async def test_pg_notify_bus_satisfies_protocol(bus: PgNotifyEventBus) -> None:
    assert isinstance(bus, EventBus)




# ===========================================================================
# publish - happy path
# ===========================================================================
async def test_publish_emits_notify_on_canonical_channel(
    bus: PgNotifyEventBus, listener: asyncpg.Connection
) -> None:
    received: list[tuple[str, str]] = []


    def on_notification(_conn: object, _pid: int, channel: str, payload: str) -> None:
        received.append((channel, payload))


    await listener.add_listener(CHANNEL, on_notification)
    try:
        await bus.publish(
            EVENT_TELEMETRY_INGESTED,
            {"plot_id": "PLOT_X", "reading_id": 42, "validation_warn": False},
        )
        # asyncpg dispatches NOTIFY callbacks on its event-loop's normal
        # turn; one short await is enough to let it run.
        await asyncio.sleep(0.5)
    finally:
        await listener.remove_listener(CHANNEL, on_notification)


    assert len(received) == 1
    channel, body = received[0]
    assert channel == CHANNEL
    envelope = json.loads(body)
    assert envelope["event"] == EVENT_TELEMETRY_INGESTED
    assert envelope["payload"]["reading_id"] == 42
    assert "ts" in envelope




async def test_publish_serialises_uuid_and_decimal_via_default_str(
    bus: PgNotifyEventBus, listener: asyncpg.Connection
) -> None:
    import uuid
    from decimal import Decimal


    received: list[str] = []


    def on_notification(_conn: object, _pid: int, _channel: str, payload: str) -> None:
        received.append(payload)


    await listener.add_listener(CHANNEL, on_notification)
    try:
        await bus.publish(
            "test.uuid_decimal",
            {
                "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
                "amount": Decimal("3.45"),
            },
        )
        await asyncio.sleep(0.3)
    finally:
        await listener.remove_listener(CHANNEL, on_notification)


    assert len(received) == 1
    env = json.loads(received[0])
    # Stringified to keep JSON happy; subscribers parse back as needed.
    assert env["payload"]["id"] == "11111111-1111-1111-1111-111111111111"
    assert env["payload"]["amount"] == "3.45"




# ===========================================================================
# publish - payload size guard
# ===========================================================================
async def test_publish_rejects_oversized_payload(bus: PgNotifyEventBus) -> None:
    huge = {"blob": "x" * (MAX_PAYLOAD_BYTES + 1000)}
    with pytest.raises(ValueError, match="exceeds"):
        await bus.publish("test.huge", huge)




async def test_max_payload_bytes_well_below_postgres_cap() -> None:
    # Postgres' raw NOTIFY cap is 8000 bytes (Postgres docs). We leave 500B
    # margin for envelope evolution. If someone bumps the cap closer than
    # this, surface it deliberately rather than silently.
    assert MAX_PAYLOAD_BYTES <= 7500
