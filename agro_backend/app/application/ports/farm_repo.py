"""Port: farm lookups needed by background jobs.

Round 18's forecast sweep needs each farm's centre coordinates + tenant. Kept
minimal (no domain Farm entity yet) — a small read-side dataclass, mirroring
``farmer_repo``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class FarmLocation:
    farm_id: uuid.UUID
    tenant_id: uuid.UUID
    lat: float
    lng: float


@runtime_checkable
class FarmRepo(Protocol):
    async def list_with_location(self) -> list[FarmLocation]:
        """Every farm with its centre coordinates (for per-farm forecasts)."""
        ...


__all__ = ["FarmLocation", "FarmRepo"]
