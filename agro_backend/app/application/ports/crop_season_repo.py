"""Port: read-side crop season lookup.

The Round-11 advisory composer needs to know which crop is on which
plot RIGHT NOW so the prompt can be crop-stage-aware ("cotton, week 6
post-sowing"). A full CropSeason entity in the domain layer is
overkill for this use case; we surface a thin view here in the port.

Future rounds that need a richer model — sowing date, expected harvest,
variety details — can either extend :class:`CropSeasonView` or graduate
it to a domain entity. For Round 11 the view is enough.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class CropSeasonView:
    """Read-side projection of an active crop_seasons row."""

    season_id: uuid.UUID
    tenant_id: uuid.UUID
    farm_id: uuid.UUID
    plot_id: str
    crop_name_english: str
    crop_name_marathi: str
    crop_category: str
    crop_variety: str
    sowing_date: datetime.date
    expected_harvest_date: datetime.date
    current_growth_stage: str | None
    crop_age_days_today: int | None


@runtime_checkable
class CropSeasonRepo(Protocol):
    """Read-only crop season repo for prompt context + dashboards."""

    async def find_active_for_plot(self, plot_id: str) -> CropSeasonView | None:
        """Return the active (season_status='active') season for this plot,
        or None if there is no active season yet (post-harvest gap).
        """
        ...

    async def list_active_by_crop(self, crop_name_english: str) -> list[CropSeasonView]:
        """Every active season where ``crop_name_english`` matches, newest first.

        Used by the daily ginger job to iterate all ginger plots at once
        without loading every plot from every tenant. Returns an empty list
        if nothing matches.
        """
        ...


__all__ = ["CropSeasonRepo", "CropSeasonView"]
