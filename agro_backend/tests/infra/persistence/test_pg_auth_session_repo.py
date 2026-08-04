"""Integration tests for PgAuthSessionRepo."""


from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.auth_session_repo import AuthSessionRepo
from app.domain.auth import AuthSession
from app.infra.persistence.pg_auth_session_repo import PgAuthSessionRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)




@pytest.fixture
def seed_farmer(sync_engine: Engine) -> Iterator[uuid.UUID]:
    farmer_id = uuid.uuid4()
    with sync_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO farmers (
                    farmer_id, tenant_id, full_name, marathi_name, phone_primary,
                    whatsapp_number, language_preference, village, taluka, district,
                    state, subscription_tier, subscription_start, subscription_end,
                    payment_status
                ) VALUES (
                    :fid, :tenant, 'F', 'अ', '+919000111111', '+919000111111',
                    'marathi', 'v', 't', 'd', 'Maharashtra', 'basic',
                    '2025-06-01', '2026-06-01', 'paid'
                )
                """
            ),
            {"fid": farmer_id, "tenant": PILOT_TENANT},
        )
    yield farmer_id
    with sync_engine.begin() as conn:
        conn.execute(text("DELETE FROM auth_sessions WHERE farmer_id = :f"), {"f": farmer_id})
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": farmer_id})




def _session(farmer_id: uuid.UUID, hash_str: str) -> AuthSession:
    now = datetime.now(UTC).replace(microsecond=0)
    return AuthSession(
        session_id=uuid.uuid4(),
        tenant_id=uuid.UUID(PILOT_TENANT),
        farmer_id=farmer_id,
        refresh_token_hash=hash_str,
        expires_at=now + timedelta(days=30),
        revoked_at=None,
        created_at=now,
        last_used_at=now,
    )




async def test_pg_auth_session_repo_satisfies_protocol(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    assert isinstance(PgAuthSessionRepo(sessionmaker), AuthSessionRepo)




async def test_create_then_find_by_token_hash(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed_farmer: uuid.UUID,
) -> None:
    repo = PgAuthSessionRepo(sessionmaker)
    s = _session(seed_farmer, "hash-a")
    sid = await repo.create(s)
    assert sid == s.session_id


    found = await repo.find_by_token_hash("hash-a")
    assert found is not None
    assert found.farmer_id == seed_farmer




async def test_revoke_makes_session_inactive(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed_farmer: uuid.UUID,
) -> None:
    repo = PgAuthSessionRepo(sessionmaker)
    s = _session(seed_farmer, "hash-b")
    await repo.create(s)
    await repo.revoke(s.session_id)


    found = await repo.find_by_token_hash("hash-b")
    assert found is not None
    assert found.revoked_at is not None
    assert found.is_active(datetime.now(UTC)) is False




async def test_revoke_all_for_farmer_counts_revoked(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed_farmer: uuid.UUID,
) -> None:
    repo = PgAuthSessionRepo(sessionmaker)
    await repo.create(_session(seed_farmer, "hash-c1"))
    await repo.create(_session(seed_farmer, "hash-c2"))
    n = await repo.revoke_all_for_farmer(seed_farmer)
    assert n == 2




async def test_find_by_unknown_token_returns_none(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed_farmer: uuid.UUID,
) -> None:
    repo = PgAuthSessionRepo(sessionmaker)
    assert await repo.find_by_token_hash("no-such-hash") is None
