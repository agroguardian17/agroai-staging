"""Alert repository port.

Persistence + cooldown-query operations against ``alerts_notifications``.
Concrete implementation in Round 6 (``app.infra.persistence.pg_alert_repo``).

The cooldown query (``last_triggered_at``) returns just a timestamp rather
than a full Alert dataclass, because the dispatch decision (Round 7) only
needs "when was this alert_type last fired for this plot?" - not the full
row. Keeps the port surface area minimal.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from app.domain.alert import AlertCandidate, AlertType, Severity


@dataclass(frozen=True, slots=True)
class AlertFull:
    """Full alert row including the identity needed for advisory composition.

    Returned by ``AlertRepo.find_by_id``. Carries the trigger-time
    measurement + threshold so the Round 11 advisory composer can
    surface "actual / expected" in the Marathi message without
    re-querying the reading.
    """

    alert_id: int
    tenant_id: uuid.UUID
    farm_id: uuid.UUID
    farmer_id: uuid.UUID
    device_id: str | None
    alert_type: AlertType
    severity: Severity
    alert_message_marathi: str
    alert_value: Decimal | None
    alert_threshold: Decimal | None
    triggered_at: datetime
    resolved: bool
    resolved_at: datetime | None


@dataclass(frozen=True, slots=True)
class PlotAlertView:
    """Read-side projection of an alert row. The shape /plots/{id}/alerts returns.

    Defined here in the port file (not in domain) because it's a
    presentation concern: which columns we expose to the HTTP layer.
    Domain entities stay free of HTTP/serialization concerns.
    """

    alert_id: int
    alert_type: AlertType
    severity: Severity
    alert_message_marathi: str
    triggered_at: datetime
    resolved: bool
    resolved_at: datetime | None
    device_id: str | None
    farmer_id: uuid.UUID


@runtime_checkable
class AlertRepo(Protocol):
    """Operations the ingest hot-rule path + notification dispatcher need."""

    async def create(self, candidate: AlertCandidate) -> int:
        """Insert one alert row; return the new ``alert_id``.

        Implementations MUST set ``dispatch_status='pending'`` (the
        server default in migration 0002), so the Round 7 notification
        dispatcher picks it up. The triggered_at column gets ``now()``
        on the server side if the candidate's ``triggered_at`` is None;
        we never write naive datetimes.
        """
        ...

    async def last_triggered_at(self, plot_id: str, alert_type: AlertType) -> datetime | None:
        """Most recent trigger time for this (plot, alert_type) pair, or None.

        Powers the cooldown check in the Phase 4 hot-rule evaluator
        (Round 7) - "skip this alert if its sibling fired in the last
        ``COOLDOWN_MINUTES`` (per alert_type) minutes". The cooldown
        table itself lives in domain constants, not in the repo.
        """
        ...

    async def resolve(self, alert_id: int, notes: str | None = None) -> None:
        """Mark an alert resolved (sets ``resolved=true``, ``resolved_at=now()``).

        Used by the agronomist queue UI (Round 17) and by the auto-resolve
        path when the firing condition clears for ``CLEAR_FOR_MINUTES``
        consecutive cycles.
        """
        ...

    async def list_for_plot(self, plot_id: str, limit: int = 50) -> list[PlotAlertView]:
        """Recent alerts visible on the /plots/{id}/alerts endpoint.

        Most-recent first. The join is alerts_notifications.device_id ->
        plots.node_id, so satellite-only plots (with no node) return [].
        """
        ...

    async def find_by_id(self, alert_id: int) -> AlertFull | None:
        """Single alert by primary key. Returns None if not found.

        Used by the Round-11 advisory composer when it receives an
        ``alert.created`` event (the payload carries the alert_id) and
        needs the full row to build the Claude prompt context.
        """
        ...


__all__ = ["AlertFull", "AlertRepo", "PlotAlertView"]
