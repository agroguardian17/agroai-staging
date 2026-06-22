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




@runtime_checkable
class FarmerRepo(Protocol):
    """Read-only farmer repo used by auth + read endpoints."""


    async def find_by_phone(self, phone: str) -> FarmerIdentity | None:
        """Return the farmer with this phone number (E.164) or None."""
        ...


    async def find_by_id(self, farmer_id: uuid.UUID) -> FarmerIdentity | None:
        """Return the farmer with this id, or None."""
        ...




__all__ = ["FarmerIdentity", "FarmerRepo"]
