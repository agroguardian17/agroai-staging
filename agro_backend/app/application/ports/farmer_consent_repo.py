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


@runtime_checkable
class FarmerConsentRepo(Protocol):
    async def for_farmer(self, farmer_id: uuid.UUID) -> FarmerConsentView | None:
        """The consent row for this farmer, or None."""
        ...


__all__ = ["FarmerConsentRepo", "FarmerConsentView"]
