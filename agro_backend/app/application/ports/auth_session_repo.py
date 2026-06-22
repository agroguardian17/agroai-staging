"""Port: refresh-session persistence.


One row per logged-in device. Storing the refresh secret as a SHA-256
hash gives us server-side revocation without depending on a JWT
blacklist or rotating signing keys.
"""


from __future__ import annotations


import uuid
from typing import Protocol, runtime_checkable


from app.domain.auth import AuthSession




@runtime_checkable
class AuthSessionRepo(Protocol):
    """Refresh-session CRUD against ``auth_sessions``."""


    async def create(self, session: AuthSession) -> uuid.UUID:
        """Insert a fresh session row. Returns the session_id."""
        ...


    async def find_by_token_hash(self, token_hash: str) -> AuthSession | None:
        """Look up by the SHA-256 hash of the refresh secret. Constant-time
        token comparison is the storage layer's responsibility (UNIQUE
        index on ``refresh_token_hash`` makes this an index lookup).
        """
        ...


    async def revoke(self, session_id: uuid.UUID) -> None:
        """Mark the session as revoked (``revoked_at = now()``)."""
        ...


    async def revoke_all_for_farmer(self, farmer_id: uuid.UUID) -> int:
        """Revoke every active session for this farmer. Used by /auth/logout
        when the client wants to kill every device at once.


        Returns the number of rows actually flipped.
        """
        ...


    async def touch(self, session_id: uuid.UUID) -> None:
        """Update ``last_used_at = now()``. Refresh endpoint calls this."""
        ...




__all__ = ["AuthSessionRepo"]
