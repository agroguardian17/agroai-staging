"""Use case: rotate a refresh token, return a fresh access+refresh pair.


Refresh-token rotation policy (lives here, not in HTTP):


1. Client presents a refresh secret. We hash it and look up the session.
2. If the session is missing, revoked, or expired -> reject.
3. Otherwise: mint NEW access + NEW refresh secret. Mark the OLD
   session revoked. Persist the new session. Return the pair.


Rotation on every refresh is the OWASP recommendation and the simplest
detection for refresh-token theft (the legitimate client and the
attacker will both eventually present the same revoked token; the
second one sees a 401 and we know something's wrong).
"""


from __future__ import annotations


import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


from app.application.ports.auth_session_repo import AuthSessionRepo
from app.application.ports.farmer_repo import FarmerRepo
from app.application.ports.token_issuer import TokenIssuer
from app.domain.auth import (
    AuthRole,
    AuthSession,
    TokenPair,
    generate_refresh_secret,
    hash_refresh_token,
)




class RefreshError(Exception):
    pass




class InvalidRefreshTokenError(RefreshError):
    """Token is unknown, revoked, or expired."""




@dataclass(frozen=True, slots=True)
class RefreshTokenDeps:
    farmer_repo: FarmerRepo
    session_repo: AuthSessionRepo
    token_issuer: TokenIssuer
    refresh_ttl_seconds: int = 30 * 24 * 3600




async def execute(*, refresh_secret: str, deps: RefreshTokenDeps) -> TokenPair:
    """Rotate the refresh token. Returns a fresh TokenPair."""
    now = datetime.now(UTC)
    token_hash = hash_refresh_token(refresh_secret)


    old = await deps.session_repo.find_by_token_hash(token_hash)
    if old is None or not old.is_active(now):
        raise InvalidRefreshTokenError()


    farmer = await deps.farmer_repo.find_by_id(old.farmer_id)
    if farmer is None or farmer.account_status != "active":
        # Revoke the dangling session so future calls don't keep trying.
        await deps.session_repo.revoke(old.session_id)
        raise InvalidRefreshTokenError()


    # Mint a NEW refresh secret + session, revoke the old.
    new_secret = generate_refresh_secret()
    new_expires_at = now + timedelta(seconds=deps.refresh_ttl_seconds)
    new_session = AuthSession(
        session_id=uuid.uuid4(),
        tenant_id=old.tenant_id,
        farmer_id=old.farmer_id,
        refresh_token_hash=hash_refresh_token(new_secret),
        expires_at=new_expires_at,
        revoked_at=None,
        created_at=now,
        last_used_at=now,
    )
    new_session_id = await deps.session_repo.create(new_session)
    await deps.session_repo.revoke(old.session_id)


    access_token, claims = deps.token_issuer.issue_access_token(
        subject=farmer.farmer_id,
        tenant_id=farmer.tenant_id,
        role=AuthRole.FARMER,
        session_id=new_session_id,
    )


    return TokenPair(
        access_token=access_token,
        refresh_token=new_secret,
        access_expires_at=claims.expires_at,
        refresh_expires_at=new_expires_at,
    )




__all__ = ["InvalidRefreshTokenError", "RefreshError", "RefreshTokenDeps", "execute"]
