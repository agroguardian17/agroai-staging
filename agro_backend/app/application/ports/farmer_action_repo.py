"""Port: farmer-action capture (``farmer_actions``).

When a farmer replies on WhatsApp we attribute the reply to their most recent
advisory and record what they did — the input the learning writer later turns
into ``ai_learning_log`` rows.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class AdvisoryContext:
    """The recent advisory a reply is attributed to."""

    suggestion_id: uuid.UUID
    tenant_id: uuid.UUID
    farmer_id: uuid.UUID
    farm_id: uuid.UUID
    season_id: uuid.UUID
    plot_id: str | None
    is_watering: bool


@dataclass(frozen=True, slots=True)
class FarmerActionInput:
    tenant_id: uuid.UUID
    farmer_id: uuid.UUID
    farm_id: uuid.UUID
    season_id: uuid.UUID
    plot_id: str | None
    ai_suggestion_id: uuid.UUID
    action_date: datetime.date
    action_type: str
    ai_suggested: bool
    farmer_followed_ai: bool | None
    water_liters: float | None
    farmer_note: str | None
    source: str = "whatsapp_reply"


@runtime_checkable
class FarmerActionRepo(Protocol):
    async def latest_advisory_for_farmer(
        self, farmer_id: uuid.UUID, *, within_days: int
    ) -> AdvisoryContext | None:
        """The farmer's most recent *sent* advisory in the window, or None."""
        ...

    async def record(self, action: FarmerActionInput) -> int:
        """Insert one farmer_actions row; return its action_id."""
        ...


__all__ = ["AdvisoryContext", "FarmerActionInput", "FarmerActionRepo"]
