"""Port for persisting Main Node master-only heartbeats (Round 17.5).

The ingest broker consumes this port when a v2-master heartbeat lands:

* ``save`` — idempotent UPSERT on ``(main_node_id, recorded_at)``.
* ``latest_for_node`` — recent-history read (used by the ops API when it
  ships).

Small surface today; more read paths (aggregates, silence-window
queries) will be additive.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.main_node_reading import MainNodeReading


@runtime_checkable
class MainNodeReadingRepo(Protocol):
    """Persist and query Main Node heartbeats."""

    async def save(self, reading: MainNodeReading) -> int | None:
        """Insert a heartbeat row.

        Idempotent on ``(main_node_id, recorded_at)``: a duplicate returns
        ``None`` and the broker treats that as success (the row exists).
        Returns the newly-minted ``reading_id`` on a real insert.
        """
        ...

    async def latest_for_node(
        self,
        main_node_id: str,
        limit: int,
    ) -> list[MainNodeReading]:
        """Most-recent-first slice of heartbeats for one Main Node."""
        ...

    async def most_recent(
        self,
        main_node_id: str,
    ) -> MainNodeReading | None:
        """Convenience: the single latest heartbeat, or ``None`` if never seen."""
        ...


__all__ = ["MainNodeReadingRepo"]
