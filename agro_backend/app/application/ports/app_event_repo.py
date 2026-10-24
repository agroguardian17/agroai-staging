"""Port for the lightweight notable-events stream (Round-3 R3.5).

A small, additive capture for structured notable events — chiefly errors and
warnings — that otherwise live only in ``docker logs``: the ingest drain loop's
unexpected-error branch is the first writer. This is deliberately **not** a
log-to-DB sink (that's the heavy BetterStack/Sentry path, out of scope); it's a
few explicit, best-effort writes so the dashboard can show a "Recent Errors &
Warnings" stream alongside the ``job_run`` ledger. Every write is best-effort —
the caller guards it so a capture failure never affects the path it observes.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class AppEvent:
    """One notable structured event. JSON-friendly ``detail``."""

    level: str  # error | warn | info
    source: str  # logical origin, e.g. "ingest_broker"
    event: str  # short stable label, e.g. "unexpected_error"
    detail: dict[str, Any] = field(default_factory=dict)
    entity: str | None = None  # node/plot/topic the event is about, when known


@runtime_checkable
class AppEventRepo(Protocol):
    async def record(self, event: AppEvent) -> None:
        """Persist one event. Best-effort caller — raising is tolerated."""
        ...

    async def purge_older_than(self, cutoff: _dt.datetime) -> int:
        """Delete rows older than ``cutoff``; return the number removed."""
        ...
