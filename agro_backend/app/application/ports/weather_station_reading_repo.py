"""Port for persisting Main Node weather-station readings (Round 17).

The ingest broker consumes this port on both v2-raw (bundled with Sub
Node telemetry) and v2-master (heartbeat) payload paths. Idempotent on
``(master_node_id, recorded_at)`` — a duplicate returns ``None`` and the
broker treats it as success (the row exists).

Query methods are added incrementally as the ops dashboard needs them.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.weather_station_reading import WeatherStationReading


@runtime_checkable
class WeatherStationReadingRepo(Protocol):
    """Persist and query Main Node weather readings."""

    async def save(self, reading: WeatherStationReading) -> int | None:
        """Insert one row. Returns the new ``weather_id`` or ``None`` on duplicate."""
        ...

    async def latest_for_node(
        self,
        master_node_id: str,
        limit: int,
    ) -> list[WeatherStationReading]:
        """Most-recent-first slice of weather readings for one Main Node."""
        ...

    async def most_recent(
        self,
        master_node_id: str,
    ) -> WeatherStationReading | None:
        """Convenience: the single latest weather row, or ``None`` if never seen."""
        ...


__all__ = ["WeatherStationReadingRepo"]
