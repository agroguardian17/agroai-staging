"""Unit tests for PgNotifyListener envelope decoding + dispatch (no DB).

We exercise the notify callback directly: it decodes the JSON envelope and
schedules the async handler. A malformed payload is dropped, never raised.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from app.infra.events.pg_notify_listener import PgNotifyListener


async def _drain() -> None:
    # Let the fire-and-forget task created by _on_notify run to completion.
    for _ in range(10):
        await asyncio.sleep(0)


async def test_on_notify_decodes_and_dispatches_envelope() -> None:
    received: list[dict[str, Any]] = []

    async def handler(env: dict[str, Any]) -> None:
        received.append(env)

    listener = PgNotifyListener("postgresql://unused", "agro_events", handler)
    envelope = {
        "event": "alert.created",
        "ts": "2026-01-01T00:00:00+00:00",
        "payload": {"alert_id": 7, "plot_id": "PLOT_PILOT_001"},
    }
    listener._on_notify(None, 0, "agro_events", json.dumps(envelope))
    await _drain()

    assert received == [envelope]


async def test_on_notify_ignores_malformed_payload() -> None:
    received: list[dict[str, Any]] = []

    async def handler(env: dict[str, Any]) -> None:
        received.append(env)

    listener = PgNotifyListener("postgresql://unused", "agro_events", handler)
    listener._on_notify(None, 0, "agro_events", "{ not json")
    await _drain()

    assert received == []
