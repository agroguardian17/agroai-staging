"""Port: read-side farmer-consent lookup for the ginger farm-brain (D12/D14)."""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class FarmerConsentView:
    farmer_id: uuid.UUID
    consent_advisory: bool | None = None
    consent_research: bool | None = None
    consent_date: datetime.date | None = None
    third_party_share_consent_given: bool | None = None
    data_retention_until: datetime.date | None = None
    deletion_requested: bool | None = None
    cluster_anonymised: bool | None = None
    sat_attribution_shown: bool | None = None
    sat_public_display_context: str | None = None


@dataclass(frozen=True, slots=True)
class ConsentCapture:
    """A captured consent to upsert onto ``farmer_consent`` (A3.1)."""

    farmer_id: uuid.UUID
    tenant_id: uuid.UUID
    consent_advisory: bool
    consent_research: bool
    third_party_share_consent_given: bool
    consent_version: str
    consent_notice_hash: str
    notice_shown_at: datetime.datetime
    consent_channel: str
    consent_date: datetime.date
    data_retention_until: datetime.date | None = None
    parental_consent_by: str | None = None
    parental_consent_verified: bool | None = None


@runtime_checkable
class FarmerConsentRepo(Protocol):
    async def for_farmer(self, farmer_id: uuid.UUID) -> FarmerConsentView | None:
        """The consent row for this farmer, or None."""
        ...

    async def capture(self, record: ConsentCapture) -> None:
        """Upsert the farmer's consent row (create or replace on farmer_id)."""
        ...

    async def record_event(
        self,
        *,
        farmer_id: uuid.UUID,
        event_type: str,
        scope: str,
        consent_version: str | None,
        channel: str | None,
        actor: str | None,
    ) -> None:
        """Append one immutable ``consent_event`` (given / withdrawn / updated)."""
        ...


__all__ = ["ConsentCapture", "FarmerConsentRepo", "FarmerConsentView"]
