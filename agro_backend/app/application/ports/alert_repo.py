"""Alert repository port.


Persistence + cooldown-query operations against ``alerts_notifications``.
Concrete implementation in Round 6 (``app.infra.persistence.pg_alert_repo``).


The cooldown query (``last_triggered_at``) returns just a timestamp rather
than a full Alert dataclass, because the dispatch decision (Round 7) only
needs "when was this alert_type last fired for this plot?" - not the full
row. Keeps the port surface area minimal.
"""


from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from app.domain.alert import AlertCandidate, AlertType


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




__all__ = ["AlertRepo"]
