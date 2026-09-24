"""Use-case: fulfil due erasure requests (A4.3, LEGAL_COMPLIANCE_CERTIFICATE §3.1/§8).

Runs on a schedule. For each pending erasure request past its 30-day due date,
anonymise the farmer's direct identifiers in place (keeping the row + non-PII
aggregate data per §8) and mark the request completed. Idempotent per request.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.ports.erasure_request_repo import ErasureRequestRepo
from app.application.ports.farmer_repo import FarmerRepo
from app.lib.time import now_utc


@dataclass(frozen=True, slots=True)
class ErasureSweepResult:
    processed: int
    anonymised: int
    missing: int


async def fulfil_erasures(
    *,
    erasure_repo: ErasureRequestRepo,
    farmer_repo: FarmerRepo,
    now: datetime | None = None,
    limit: int = 500,
) -> ErasureSweepResult:
    """Anonymise farmers with a due erasure request and close the requests."""
    when = now or now_utc()
    due = await erasure_repo.list_due(when, limit=limit)

    anonymised = 0
    missing = 0
    for req in due:
        ok = await farmer_repo.anonymise_identity(req.farmer_id)
        if ok:
            anonymised += 1
        else:
            # Farmer already gone (hard-deleted elsewhere) — still close the request.
            missing += 1
        await erasure_repo.mark_completed(req.id, completed_at=when)

    return ErasureSweepResult(processed=len(due), anonymised=anonymised, missing=missing)


__all__ = ["ErasureSweepResult", "fulfil_erasures"]
