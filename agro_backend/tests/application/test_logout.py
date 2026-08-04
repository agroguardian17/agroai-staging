"""Tests for app.application.logout."""


from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.application.logout import LogoutDeps, logout_everywhere, logout_one
from app.domain.auth import AuthSession, hash_refresh_token

TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
NOW = datetime.now(UTC)




class _StubSessionRepo:
    def __init__(self, existing: AuthSession | None = None) -> None:
        self._existing = existing
        self.revoked: list[uuid.UUID] = []
        self.revoke_all_count = 0


    async def create(self, s: AuthSession) -> uuid.UUID:
        return s.session_id


    async def find_by_token_hash(self, h: str) -> AuthSession | None:
        if self._existing is None:
            return None
        return self._existing if self._existing.refresh_token_hash == h else None


    async def revoke(self, sid: uuid.UUID) -> None:
        self.revoked.append(sid)


    async def revoke_all_for_farmer(self, farmer_id: uuid.UUID) -> int:
        self.revoke_all_count += 1
        return 3  # Pretend 3 devices were active.


    async def touch(self, sid: uuid.UUID) -> None:
        pass




def _session(secret: str) -> AuthSession:
    return AuthSession(
        session_id=uuid.uuid4(),
        tenant_id=TENANT,
        farmer_id=uuid.uuid4(),
        refresh_token_hash=hash_refresh_token(secret),
        expires_at=NOW + timedelta(days=30),
        revoked_at=None,
        created_at=NOW,
        last_used_at=NOW,
    )




async def test_logout_one_revokes_session_for_matching_token() -> None:
    secret = "token-secret"
    s = _session(secret)
    repo = _StubSessionRepo(existing=s)
    ok = await logout_one(refresh_secret=secret, deps=LogoutDeps(session_repo=repo))
    assert ok is True
    assert s.session_id in repo.revoked




async def test_logout_one_returns_false_for_unknown_token() -> None:
    repo = _StubSessionRepo(existing=None)
    ok = await logout_one(refresh_secret="garbage", deps=LogoutDeps(session_repo=repo))
    assert ok is False
    assert repo.revoked == []




async def test_logout_everywhere_returns_count() -> None:
    repo = _StubSessionRepo()
    out = await logout_everywhere(farmer_id=uuid.uuid4(), deps=LogoutDeps(session_repo=repo))
    assert out == 3
    assert repo.revoke_all_count == 1
