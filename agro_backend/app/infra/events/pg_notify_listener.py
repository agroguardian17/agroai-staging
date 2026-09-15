"""Postgres ``LISTEN`` adapter — the consumer side of the event bus.

:class:`~app.infra.events.pg_notify_bus.PgNotifyEventBus` (Round 6) *publishes*
on the ``agro_events`` channel via ``pg_notify``. Round 13 adds the *consumer*:
a long-lived asyncpg connection that ``LISTEN``s on the channel and hands each
decoded envelope to an async handler.

asyncpg is used directly (not SQLAlchemy) because ``LISTEN`` needs one dedicated,
long-lived connection held outside the request pool. The listener is
self-healing: if the connection drops it reconnects and re-``LISTEN``s.

Envelope shape (see ``PgNotifyEventBus.publish``):
``{"event": "<name>", "ts": "<iso>", "payload": {...}}``.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

import asyncpg  # type: ignore[import-untyped]
import structlog

log = structlog.get_logger(__name__)

# Handler receives the decoded envelope dict.
EnvelopeHandler = Callable[[dict[str, Any]], Awaitable[None]]


class PgNotifyListener:
    """Self-healing ``LISTEN`` loop that dispatches envelopes to a handler."""

    def __init__(
        self,
        dsn: str,
        channel: str,
        handler: EnvelopeHandler,
        *,
        reconnect_delay_seconds: float = 5.0,
    ) -> None:
        # ``dsn`` must be a plain ``postgresql://`` DSN (asyncpg does NOT accept
        # SQLAlchemy's ``postgresql+asyncpg://``); pass settings.DATABASE_URL_SYNC.
        self._dsn = dsn
        self._channel = channel
        self._handler = handler
        self._reconnect_delay = reconnect_delay_seconds
        self._task: asyncio.Task[None] | None = None
        self._conn: asyncpg.Connection | None = None
        self._stopped = asyncio.Event()
        self._pending: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        self._stopped.clear()
        self._task = asyncio.create_task(self._run(), name="advisory-listener")
        log.info("pg_notify_listener.started", channel=self._channel)

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._close_conn()
        log.info("pg_notify_listener.stopped", channel=self._channel)

    async def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                conn = await asyncpg.connect(self._dsn)
                self._conn = conn
                await conn.add_listener(self._channel, self._on_notify)
                log.info("pg_notify_listener.listening", channel=self._channel)
                while not self._stopped.is_set() and not conn.is_closed():
                    # Block on the stop signal, waking every few seconds to
                    # notice a dropped connection (not a bare-sleep busy-wait).
                    with contextlib.suppress(TimeoutError):
                        await asyncio.wait_for(self._stopped.wait(), timeout=5.0)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("pg_notify_listener.connection_error", channel=self._channel)
            finally:
                await self._close_conn()
            if not self._stopped.is_set():
                await asyncio.sleep(self._reconnect_delay)

    def _on_notify(self, _conn: object, _pid: int, channel: str, payload: str) -> None:
        # asyncpg invokes this synchronously on the event loop. Decode + schedule
        # the async handler; keep a reference so the task isn't GC'd mid-flight.
        try:
            envelope = json.loads(payload)
        except (ValueError, TypeError):
            log.warning("pg_notify_listener.bad_payload", channel=channel)
            return
        task = asyncio.create_task(self._dispatch(envelope))
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    async def _dispatch(self, envelope: dict[str, Any]) -> None:
        try:
            await self._handler(envelope)
        except Exception:
            log.exception("pg_notify_listener.handler_error", channel=self._channel)

    async def _close_conn(self) -> None:
        conn = self._conn
        self._conn = None
        if conn is not None and not conn.is_closed():
            with contextlib.suppress(Exception):
                await conn.remove_listener(self._channel, self._on_notify)
            with contextlib.suppress(Exception):
                await conn.close()


__all__ = ["EnvelopeHandler", "PgNotifyListener"]
