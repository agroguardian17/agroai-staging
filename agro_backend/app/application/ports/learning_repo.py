"""Port: the advisory-feedback learning loop (``ai_learning_log``).

A farmer_action that references an ``ai_suggestion`` records what the farmer
actually did versus what was advised. The learning writer (Round 18.5) turns
each such action into an ``ai_learning_log`` row — the raw signal a future round
uses to tune the engine. Outcome fields (NDVI/moisture deltas) are backfilled
later when the time-delayed measurements exist; the writer fills the
immediately-knowable comparison.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ActionOutcome:
    """A farmer_action joined to its advised suggestion (read side)."""

    action_id: int
    tenant_id: uuid.UUID
    farmer_id: uuid.UUID
    season_id: uuid.UUID
    suggestion_id: uuid.UUID
    action_date: datetime.date
    action_type: str
    water_liters: float | None
    farmer_followed_ai: bool | None
    suggestion_type: str | None
    ai_suggested_liters: float | None
    crop_stage: str | None
    soil_type: str | None


@dataclass(frozen=True, slots=True)
class LearningRow:
    """One ``ai_learning_log`` row (write side)."""

    tenant_id: uuid.UUID
    farmer_id: uuid.UUID
    season_id: uuid.UUID
    suggestion_id: uuid.UUID
    action_id: int
    learning_date: datetime.date
    suggestion_type: str | None
    ai_suggested_liters: float | None
    farmer_gave_liters: float | None
    water_variance_liters: float | None
    suggestion_accuracy: str | None
    crop_stage: str | None
    soil_type: str | None
    learning_applied_at: datetime.datetime


@runtime_checkable
class LearningRepo(Protocol):
    async def list_unlearned_actions(self, limit: int = 200) -> list[ActionOutcome]:
        """Actions that reference a suggestion but have no learning row yet."""
        ...

    async def record(self, row: LearningRow) -> int:
        """Insert one ai_learning_log row; return its learning_id."""
        ...


__all__ = ["ActionOutcome", "LearningRepo", "LearningRow"]
