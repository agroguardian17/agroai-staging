"""Integration tests for consent withdrawal (set_scope) + erasure workflow (0047)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.erasure_request_repo import ErasureRequestRepo
from app.application.ports.farmer_consent_repo import ConsentCapture
from app.infra.persistence.pg_erasure_request_repo import PgErasureRequestRepo
from app.infra.persistence.pg_farmer_consent_repo import PgFarmerConsentRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)


def _seed_farmer(eng: Engine) -> uuid.UUID:
    fid = uuid.uuid4()
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO farmers (
                    farmer_id, tenant_id, full_name, marathi_name, phone_primary,
                    whatsapp_number, language_preference, village, taluka, district,
                    state, subscription_tier, subscription_start, subscription_end,
                    payment_status
                ) VALUES (
                    :f, :t, 'A', 'अ', '+910000000002', '+910000000002', 'marathi',
                    'v', 't', 'd', 'Maharashtra', 'basic', '2025-06-01', '2026-06-01', 'paid'
                )
                """
            ),
            {"f": fid, "t": PILOT_TENANT},
        )
    return fid


@pytest.fixture
def farmer(sync_engine: Engine) -> Iterator[uuid.UUID]:
    fid = _seed_farmer(sync_engine)
    yield fid
    with sync_engine.begin() as conn:
        conn.execute(text("DELETE FROM erasure_request WHERE farmer_id = :f"), {"f": fid})
        conn.execute(text("DELETE FROM farmer_consent WHERE farmer_id = :f"), {"f": fid})
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": fid})


async def _capture(repo: PgFarmerConsentRepo, fid: uuid.UUID) -> None:
    await repo.capture(
        ConsentCapture(
            farmer_id=fid,
            tenant_id=uuid.UUID(PILOT_TENANT),
            consent_advisory=True,
            consent_research=True,
            third_party_share_consent_given=True,
            consent_version="dpdp-consent/v1",
            consent_notice_hash="h",
            notice_shown_at=datetime(2026, 11, 1, tzinfo=UTC),
            consent_channel="whatsapp",
            consent_date=date(2026, 11, 1),
        )
    )


async def test_set_scope_flips_only_that_scope(
    sessionmaker: async_sessionmaker[AsyncSession],
    farmer: uuid.UUID,
    sync_engine: Engine,
) -> None:
    repo = PgFarmerConsentRepo(sessionmaker)
    await _capture(repo, farmer)
    ok = await repo.set_scope(
        farmer, "research", granted=False, withdrawn_at=datetime(2026, 11, 2, tzinfo=UTC)
    )
    assert ok is True
    with sync_engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT consent_advisory, consent_research, withdrawn_at "
                "FROM farmer_consent WHERE farmer_id = :f"
            ),
            {"f": farmer},
        ).one()
    assert row.consent_advisory is True  # advisory untouched (§3.2)
    assert row.consent_research is False  # only research withdrawn
    assert row.withdrawn_at is not None


async def test_set_scope_false_when_no_row(
    sessionmaker: async_sessionmaker[AsyncSession], farmer: uuid.UUID
) -> None:
    repo = PgFarmerConsentRepo(sessionmaker)
    assert await repo.set_scope(farmer, "advisory", granted=False) is False  # no consent row yet


async def test_mark_deletion_requested(
    sessionmaker: async_sessionmaker[AsyncSession],
    farmer: uuid.UUID,
    sync_engine: Engine,
) -> None:
    repo = PgFarmerConsentRepo(sessionmaker)
    await _capture(repo, farmer)
    await repo.mark_deletion_requested(farmer, requested=True)
    with sync_engine.begin() as conn:
        flag = conn.execute(
            text("SELECT deletion_requested FROM farmer_consent WHERE farmer_id = :f"),
            {"f": farmer},
        ).scalar_one()
    assert flag is True


async def test_erasure_create_is_idempotent(
    sessionmaker: async_sessionmaker[AsyncSession], farmer: uuid.UUID
) -> None:
    repo = PgErasureRequestRepo(sessionmaker)
    assert isinstance(repo, ErasureRequestRepo)
    due = datetime.now(UTC) + timedelta(days=30)
    assert (
        await repo.create(farmer_id=farmer, due_at=due, method="db_and_backups", actor="app")
        is True
    )
    # A second pending request for the same farmer is a no-op (partial unique index).
    assert (
        await repo.create(farmer_id=farmer, due_at=due, method="db_and_backups", actor="app")
        is False
    )
    pending = await repo.pending_for(farmer)
    assert pending is not None
    assert pending.status == "pending"
