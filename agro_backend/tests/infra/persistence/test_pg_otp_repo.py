"""Integration tests for PgOtpRepo. Uses the conftest sync_engine + sessionmaker."""


from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.otp_repo import OtpRepo
from app.domain.auth import OtpChallenge, OtpTransport, hash_otp_code
from app.infra.persistence.pg_otp_repo import PgOtpRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)




@pytest.fixture
def clean_otp(sync_engine: Engine) -> Iterator[None]:
    with sync_engine.begin() as conn:
        conn.execute(text("DELETE FROM otp_challenges WHERE phone LIKE '+91900%'"))
    yield
    with sync_engine.begin() as conn:
        conn.execute(text("DELETE FROM otp_challenges WHERE phone LIKE '+91900%'"))




def _challenge(phone: str, *, expires_at: datetime | None = None) -> OtpChallenge:
    now = datetime.now(UTC).replace(microsecond=0)
    return OtpChallenge(
        challenge_id=uuid.uuid4(),
        tenant_id=uuid.UUID(PILOT_TENANT),
        phone=phone,
        code_hash=hash_otp_code("123456", "salt"),
        transport=OtpTransport.LOG_ONLY,
        expires_at=expires_at or now + timedelta(minutes=5),
        consumed_at=None,
        attempt_count=0,
        max_attempts=5,
        created_at=now,
    )




async def test_pg_otp_repo_satisfies_protocol(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    assert isinstance(PgOtpRepo(sessionmaker), OtpRepo)




async def test_create_then_find_latest_active(
    sessionmaker: async_sessionmaker[AsyncSession],
    clean_otp: None,
) -> None:
    repo = PgOtpRepo(sessionmaker)
    c = _challenge("+919000000001")
    cid = await repo.create(c)
    assert cid == c.challenge_id


    found = await repo.find_latest_active("+919000000001")
    assert found is not None
    assert found.phone == "+919000000001"
    assert found.code_hash == c.code_hash




async def test_find_latest_active_skips_expired(
    sessionmaker: async_sessionmaker[AsyncSession],
    clean_otp: None,
) -> None:
    repo = PgOtpRepo(sessionmaker)
    expired = _challenge("+919000000002", expires_at=datetime.now(UTC) - timedelta(seconds=1))
    await repo.create(expired)
    assert await repo.find_latest_active("+919000000002") is None




async def test_increment_attempt_returns_new_count(
    sessionmaker: async_sessionmaker[AsyncSession],
    clean_otp: None,
) -> None:
    repo = PgOtpRepo(sessionmaker)
    c = _challenge("+919000000003")
    await repo.create(c)
    n1 = await repo.increment_attempt(c.challenge_id)
    n2 = await repo.increment_attempt(c.challenge_id)
    assert n1 == 1
    assert n2 == 2




async def test_mark_consumed_makes_latest_active_return_none(
    sessionmaker: async_sessionmaker[AsyncSession],
    clean_otp: None,
) -> None:
    repo = PgOtpRepo(sessionmaker)
    c = _challenge("+919000000004")
    await repo.create(c)
    await repo.mark_consumed(c.challenge_id)
    assert await repo.find_latest_active("+919000000004") is None




async def test_recent_attempts_count_counts_window(
    sessionmaker: async_sessionmaker[AsyncSession],
    clean_otp: None,
) -> None:
    repo = PgOtpRepo(sessionmaker)
    phone = "+919000000005"
    for _ in range(3):
        await repo.create(_challenge(phone))
    n = await repo.recent_attempts_count(phone, since_minutes=60)
    assert n == 3
