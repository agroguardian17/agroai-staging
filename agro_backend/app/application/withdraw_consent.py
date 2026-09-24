"""Use-case: withdraw one consent scope (A3.5, LEGAL_COMPLIANCE_CERTIFICATE §3.1/§3.2).

One-click withdrawal per scope. Per §3.2, withdrawing the *research* or
*third-party* scope must not stop the advisory service — only withdrawing the
*advisory* scope is a full opt-out. This use-case flips exactly the requested
scope and appends a ``consent_event``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.application.ports.farmer_consent_repo import FarmerConsentRepo
from app.lib.time import now_utc

_SCOPES = frozenset({"advisory", "research", "third_party"})


class NoConsentError(Exception):
    """The farmer has no consent row to withdraw from."""


@dataclass(frozen=True, slots=True)
class WithdrawalResult:
    farmer_id: uuid.UUID
    scope: str
    advisory_still_active: bool


async def withdraw_consent(
    *,
    farmer_id: uuid.UUID,
    scope: str,
    actor: str,
    channel: str,
    consent_repo: FarmerConsentRepo,
    now: datetime | None = None,
) -> WithdrawalResult:
    """Withdraw one consent scope. Raises if the scope is unknown or the farmer
    has no consent row."""
    if scope not in _SCOPES:
        raise ValueError(f"unknown consent scope: {scope!r}")

    when = now or now_utc()
    updated = await consent_repo.set_scope(farmer_id, scope, granted=False, withdrawn_at=when)
    if not updated:
        raise NoConsentError(str(farmer_id))

    await consent_repo.record_event(
        farmer_id=farmer_id,
        event_type="withdrawn",
        scope=scope,
        consent_version=None,
        channel=channel,
        actor=actor,
    )
    return WithdrawalResult(
        farmer_id=farmer_id,
        scope=scope,
        advisory_still_active=scope != "advisory",
    )


__all__ = ["NoConsentError", "WithdrawalResult", "withdraw_consent"]
