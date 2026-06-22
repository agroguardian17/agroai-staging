"""Tests for app.application.refresh_token.execute."""


from __future__ import annotations


import uuid
from datetime import UTC, datetime, timedelta


import pytest


from app.application.ports.farmer_repo import FarmerIdentity
from app.application.refresh_token import (
    InvalidRefreshTokenError,
    RefreshTokenDeps,
    execute,
)
from app.domain.auth import (
    AccessClaims,
    AuthRole,
    AuthSession,
    hash_refresh_token,
)


PHONE = "+918123456789"
TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
FARMER = uuid.uuid4()
NOW = datetime.now(UTC)




def _farmer(status: str = "active") -> FarmerIdentity:
    return FarmerIdentity(
        farmer_id=FARMER,
        tenant_id=TENANT,
        phone=PHONE,
        full_name="Test",
        language_preference="marathi",
        account_status=status,
    )




class _StubFarmerRepo:
    def __init__(self, f: FarmerIdentity | None) -> None:
        self._f = f


    async def find_by_phone(self, phone: str) -> FarmerIdentity | None:
        return self._f


    async def find_by_id(self, farmer_id: uuid.UUID) -> FarmerIdentity | None:
        return self._f




class _StubSessionRepo:
    def __init__(self, existing: AuthSession | None) -> None:
        self._existing = existing
        self.created: list[AuthSession] = []
        self.revoked: list[uuid.UUID] = []


    async def create(self, s: AuthSession) -> uuid.UUID:
        self.created.append(s)
        return s.session_id


    async def find_by_token_hash(self, h: str) -> AuthSession | None:
        if self._existing is None:
            return None
        if self._existing.refresh_token_hash != h:
            return None
        return self._existing


    async def revoke(self, sid: uuid.UUID) -> None:
        self.revoked.append(sid)


    async def revoke_all_for_farmer(self, farmer_id: uuid.UUID) -> int:
        return 0


    async def touch(self, sid: uuid.UUID) -> None:
        pass




class _StubTokenIssuer:
    def issue_access_token(
        self,
        *,
        subject: uuid.UUID,
        tenant_id: uuid.UUID,
        role: AuthRole,
        session_id: uuid.UUID,
    ) -> tuple[str, AccessClaims]:
        return "fresh.access", AccessClaims(
            subject=subject,
            tenant_id=tenant_id,
            role=role,
            issued_at=NOW,
            expires_at=NOW + timedelta(minutes=15),
            session_id=session_id,
        )


    def verify_access_token(self, token: str) -> AccessClaims:
        raise AssertionError




def _session(
    secret: str, *, revoked_at: datetime | None = None, expires_at: datetime | None = None
) -> AuthSession:
    return AuthSession(
        session_id=uuid.uuid4(),
        tenant_id=TENANT,
        farmer_id=FARMER,
        refresh_token_hash=hash_refresh_token(secret),
        expires_at=expires_at or NOW + timedelta(days=30),
        revoked_at=revoked_at,
        created_at=NOW,
        last_used_at=NOW,
    )




def _deps(
    *, farmer: FarmerIdentity | None, existing: AuthSession | None
) -> tuple[RefreshTokenDeps, _StubSessionRepo]:
    sess = _StubSessionRepo(existing)
    return (
        RefreshTokenDeps(
            farmer_repo=_StubFarmerRepo(farmer),
            session_repo=sess,
            token_issuer=_StubTokenIssuer(),
        ),
        sess,
    )




async def test_refresh_rotates_session_and_returns_new_pair() -> None:
    secret = "old-secret-value"
    old = _session(secret)
    deps, sess = _deps(farmer=_farmer(), existing=old)
    new_pair = await execute(refresh_secret=secret, deps=deps)


    assert new_pair.access_token == "fresh.access"
    assert new_pair.refresh_token != secret  # rotated
    assert old.session_id in sess.revoked  # old killed
    assert len(sess.created) == 1  # new created




async def test_refresh_rejects_unknown_token() -> None:
    deps, _ = _deps(farmer=_farmer(), existing=None)
    with pytest.raises(InvalidRefreshTokenError):
        await execute(refresh_secret="bogus", deps=deps)




async def test_refresh_rejects_revoked_session() -> None:
    secret = "revoked-secret"
    old = _session(secret, revoked_at=NOW - timedelta(minutes=1))
    deps, _ = _deps(farmer=_farmer(), existing=old)
    with pytest.raises(InvalidRefreshTokenError):
        await execute(refresh_secret=secret, deps=deps)




async def test_refresh_rejects_expired_session() -> None:
    secret = "expired"
    old = _session(secret, expires_at=NOW - timedelta(seconds=1))
    deps, _ = _deps(farmer=_farmer(), existing=old)
    with pytest.raises(InvalidRefreshTokenError):
        await execute(refresh_secret=secret, deps=deps)




async def test_refresh_rejects_inactive_farmer_and_revokes() -> None:
    secret = "good-secret"
    old = _session(secret)
    deps, sess = _deps(farmer=_farmer(status="suspended"), existing=old)
    with pytest.raises(InvalidRefreshTokenError):
        await execute(refresh_secret=secret, deps=deps)
    # The dangling session is revoked.
    assert old.session_id in sess.revoked
