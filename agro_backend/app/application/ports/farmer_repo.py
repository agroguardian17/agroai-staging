"""Port: read-side farmer lookup for auth and read endpoints.


Domain doesn't define a Farmer entity yet; for Round 8 the auth flow
only needs the minimum (farmer_id, tenant_id, phone). We model that as
a small frozen dataclass here in the application layer rather than
inventing a domain entity prematurely. Phase 4 will graduate it to
:mod:`app.domain.farmer` if the read paths grow more behavior.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class FarmerIdentity:
    """The shape /auth and /me responses carry. No PII beyond name + phone."""

    farmer_id: uuid.UUID
    tenant_id: uuid.UUID
    phone: str
    full_name: str
    language_preference: str
    account_status: str  # 'active' | 'inactive' | 'suspended'


@dataclass(frozen=True, slots=True)
class FarmerLocation:
    """Administrative location a farmer sits in — read by the ginger KB
    (D10 scheme/subsidy rules) via the farm-brain. Kept separate from
    :class:`FarmerIdentity` so the auth path carries no extra address data.
    """

    farmer_id: uuid.UUID
    district: str | None = None
    taluka: str | None = None
    language_preference: str | None = None


@runtime_checkable
class FarmerRepo(Protocol):
    """Read-only farmer repo used by auth + read endpoints."""

    async def find_by_phone(self, phone: str) -> FarmerIdentity | None:
        """Return the farmer with this phone number (E.164) or None."""
        ...

    async def find_by_id(self, farmer_id: uuid.UUID) -> FarmerIdentity | None:
        """Return the farmer with this id, or None."""
        ...

    async def owner_of_farm(self, farm_id: uuid.UUID) -> uuid.UUID | None:
        """Return the farmer_id that owns this farm, or None if unknown."""
        ...

    async def find_location(self, farmer_id: uuid.UUID) -> FarmerLocation | None:
        """District/taluka for one farmer, or None if unknown."""
        ...

    async def anonymise_identity(self, farmer_id: uuid.UUID) -> bool:
        """DPDP erasure (A4.3): tombstone the farmer's direct identifiers in
        place — name, phone, whatsapp, DOB — keeping the row and non-PII data so
        anonymised aggregate history and referential integrity survive (§8).
        Returns False if the farmer does not exist."""
        ...


__all__ = ["FarmerIdentity", "FarmerLocation", "FarmerRepo"]
