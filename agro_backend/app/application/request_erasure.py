"""Use-case: farmer right-to-erasure request (A3.4, LEGAL_COMPLIANCE_CERTIFICATE §3.1).

Records an erasure request with a 30-day due date and flags the consent row for
deletion; the retention/purge job (A4.3) fulfils it by the due date. Idempotent —
a second request while one is pending returns the existing one.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.ports.erasure_request_repo import ErasureRequest, ErasureRequestRepo
from app.application.ports.farmer_consent_repo import FarmerConsentRepo
from app.lib.time import now_utc

# DPDP §3.1 / §27: erasure honoured within 30 days of receipt.
ERASURE_SLA_DAYS = 30


@dataclass(frozen=True, slots=True)
class ErasureResult:
    farmer_id: uuid.UUID
    due_at: datetime
    already_pending: bool


async def request_erasure(
    *,
    farmer_id: uuid.UUID,
    actor: str,
    erasure_repo: ErasureRequestRepo,
    consent_repo: FarmerConsentRepo,
    method: str = "db_and_backups",
    now: datetime | None = None,
) -> ErasureResult:
    """Record a 30-day-SLA erasure request and flag the consent row for deletion."""
    when = now or now_utc()
    due_at = when + timedelta(days=ERASURE_SLA_DAYS)

    created = await erasure_repo.create(
        farmer_id=farmer_id, due_at=due_at, method=method, actor=actor
    )
    # Flag the consent row so reads (and the purge job) see the pending erasure.
    await consent_repo.mark_deletion_requested(farmer_id, requested=True)

    if created:
        return ErasureResult(farmer_id=farmer_id, due_at=due_at, already_pending=False)

    existing: ErasureRequest | None = await erasure_repo.pending_for(farmer_id)
    effective_due = existing.due_at if existing is not None else due_at
    return ErasureResult(farmer_id=farmer_id, due_at=effective_due, already_pending=True)


__all__ = ["ERASURE_SLA_DAYS", "ErasureResult", "request_erasure"]
