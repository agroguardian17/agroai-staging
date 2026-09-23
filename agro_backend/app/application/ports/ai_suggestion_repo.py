"""Port: AI advisory persistence.

The Round-11 composer writes one row per alert advisory. Other
``suggestion_type`` values (daily / weekly / end_of_season) land in
later rounds; the same repo + table serves all of them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class AiSuggestion:
    """The persisted advisory row.

    Round 11 populates the minimum fields needed by the alert flow.
    Future rounds populate the structured advisory columns
    (water_action, fertilizer_*, etc.) as their use cases land.
    """

    suggestion_id: uuid.UUID
    tenant_id: uuid.UUID
    farmer_id: uuid.UUID
    farm_id: uuid.UUID
    plot_id: str | None
    season_id: uuid.UUID
    generated_at: datetime
    suggestion_type: str  # 'alert' | 'daily' | 'weekly' | 'monthly' | 'end_of_season'
    full_message_marathi: str
    ai_model_version: str
    tokens_used: int | None
    generation_time_ms: int | None
    crop_age_days: int | None = None
    crop_stage: str | None = None
    # The KB rule that produced this advisory (migration 0043). NULL for rows
    # written before rule-level QA, and for non-engine (LLM daily) advisories.
    rule_id: str | None = None


@runtime_checkable
class AiSuggestionRepo(Protocol):
    """CRUD against ``ai_suggestions``."""

    async def create(self, suggestion: AiSuggestion) -> uuid.UUID:
        """Insert a row; return the (server-side) suggestion_id."""
        ...

    async def find_by_id(self, suggestion_id: uuid.UUID) -> AiSuggestion | None: ...

    async def list_for_plot(self, plot_id: str, limit: int = 50) -> list[AiSuggestion]:
        """Recent advisories for one plot, newest first.

        Powers the dashboard's plot-detail page (Round 12).
        """
        ...

    # --- Round 14 delivery state machine (migration 0016) -----------------

    async def claim_for_delivery(
        self, suggestion_id: uuid.UUID, now: datetime, *, require_review: bool
    ) -> int | None:
        """Atomically move a due ``pending`` row to ``in_flight``.

        Returns the prior ``delivery_attempts`` on success, or ``None`` if the
        row was not claimable (already handled, not yet due, or — when
        ``require_review`` is set — not yet ``review_status='approved'``). The
        atomic UPDATE...RETURNING makes concurrent listener+reconciler safe.
        """
        ...

    async def set_delivery_outcome(
        self,
        suggestion_id: uuid.UUID,
        *,
        status: str,
        attempts: int | None = None,
        next_retry_at: datetime | None = None,
        last_error: str | None = None,
        provider_message_id: str | None = None,
        sent_at: datetime | None = None,
    ) -> None:
        """Record the terminal (or retry) delivery outcome.

        On ``status='sent'`` implementations also set the base ``whatsapp_sent``
        / ``whatsapp_sent_at`` markers (0001) from ``sent_at``.
        """
        ...

    async def list_due_deliveries(
        self, now: datetime, *, require_review: bool, limit: int = 100
    ) -> list[uuid.UUID]:
        """Pending, due (and — if required — approved) suggestion ids."""
        ...

    async def revert_stale_deliveries(self, cutoff: datetime, now: datetime) -> int:
        """Reap ``in_flight`` rows claimed before ``cutoff`` (crashed workers)."""
        ...


__all__ = ["AiSuggestion", "AiSuggestionRepo"]
