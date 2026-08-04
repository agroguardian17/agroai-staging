"""Port: JWT issue / verify.


The application layer asks for "give me an access token for this user";
the infra layer (python-jose, HS256) actually signs it. Tests can
swap a stub implementation that produces fixed strings without
involving the real signer.
"""


from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from app.domain.auth import AccessClaims, AuthRole


class InvalidTokenError(Exception):
    """Raised by ``verify_access_token`` for any invalid / expired token."""




@runtime_checkable
class TokenIssuer(Protocol):
    """Mint and verify access tokens.


    Refresh-token issuing is handled separately: it's a random opaque
    secret (no signed JWT) stored hashed in ``auth_sessions``.
    """


    def issue_access_token(
        self,
        *,
        subject: uuid.UUID,
        tenant_id: uuid.UUID,
        role: AuthRole,
        session_id: uuid.UUID,
    ) -> tuple[str, AccessClaims]:
        """Return (signed JWT, the claims that went into it)."""
        ...


    def verify_access_token(self, token: str) -> AccessClaims:
        """Parse + verify signature + check exp/iss/aud. Raise on failure."""
        ...




__all__ = ["InvalidTokenError", "TokenIssuer"]
