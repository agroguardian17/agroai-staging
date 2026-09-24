"""Port: DPDP erasure-request workflow (LEGAL_COMPLIANCE_CERTIFICATE §3.1, A3.4).

Records a farmer's right-to-erasure request with a 30-day due date; the
retention/purge job (A4.3) consumes the pending, due requests.

Concrete implementation:
:class:`app.infra.persistence.pg_erasure_request_repo.PgErasureRequestRepo`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ErasureRequest:
    id: uuid.UUID
    farmer_id: uuid.UUID
    requested_at: datetime
    due_at: datetime
    status: str
    method: str | None = None
    actor: str | None = None


@runtime_checkable
class ErasureRequestRepo(Protocol):
    async def create(
        self,
        *,
        farmer_id: uuid.UUID,
        due_at: datetime,
        method: str | None,
        actor: str | None,
    ) -> bool:
        """Create a pending erasure request. Returns False if one is already
        pending for the farmer (idempotent — the partial unique index enforces)."""
        ...

    async def pending_for(self, farmer_id: uuid.UUID) -> ErasureRequest | None:
        """The farmer's pending erasure request, if any."""
        ...

    async def list_due(self, now: datetime, *, limit: int = 500) -> list[ErasureRequest]:
        """Pending requests whose ``due_at`` has passed (for the purge job)."""
        ...

    async def mark_completed(self, request_id: uuid.UUID, *, completed_at: datetime) -> None:
        """Mark a request fulfilled (status='completed')."""
        ...


__all__ = ["ErasureRequest", "ErasureRequestRepo"]
