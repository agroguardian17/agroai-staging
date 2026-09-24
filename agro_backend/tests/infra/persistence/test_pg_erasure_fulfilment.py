"""Integration test: erasure fulfilment anonymises the farmer + closes the request (A4.3)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.fulfil_erasures import fulfil_erasures
from app.infra.persistence.pg_erasure_request_repo import PgErasureRequestRepo
from app.infra.persistence.pg_farmer_repo import PgFarmerRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)

_NOW = datetime(2026, 12, 1, 2, 30, tzinfo=UTC)


def _seed(eng: Engine) -> uuid.UUID:
    fid = uuid.uuid4()
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO farmers (
                    farmer_id, tenant_id, full_name, marathi_name, phone_primary,
                    whatsapp_number, aadhar_number, date_of_birth, language_preference,
                    village, taluka, district, state, subscription_tier,
                    subscription_start, subscription_end, payment_status
                ) VALUES (
                    :f, :t, 'Real Name', 'खरे नाव', '+919876543210', '+919876543210',
                    '111122223333', '1990-05-01', 'marathi',
                    'Kannad', 'Kannad', 'Chhatrapati Sambhajinagar', 'Maharashtra', 'basic',
                    '2026-06-01', '2027-06-01', 'paid'
                )
                """
            ),
            {"f": fid, "t": PILOT_TENANT},
        )
        # A due (past) pending erasure request.
        conn.execute(
            text(
                """
                INSERT INTO erasure_request (farmer_id, due_at, method, actor)
                VALUES (:f, :due, 'db_and_backups', 'farmer_app')
                """
            ),
            {"f": fid, "due": _NOW - timedelta(days=1)},
        )
    return fid


@pytest.fixture
def farmer(sync_engine: Engine) -> Iterator[uuid.UUID]:
    fid = _seed(sync_engine)
    yield fid
    with sync_engine.begin() as conn:
        conn.execute(text("DELETE FROM erasure_request WHERE farmer_id = :f"), {"f": fid})
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": fid})


async def test_fulfil_erasures_anonymises_and_closes(
    sessionmaker: async_sessionmaker[AsyncSession],
    farmer: uuid.UUID,
    sync_engine: Engine,
) -> None:
    res = await fulfil_erasures(
        erasure_repo=PgErasureRequestRepo(sessionmaker),
        farmer_repo=PgFarmerRepo(sessionmaker),
        now=_NOW,
    )
    assert res.anonymised == 1
    assert res.processed == 1

    with sync_engine.begin() as conn:
        f = conn.execute(
            text(
                "SELECT full_name, phone_primary, whatsapp_number, aadhar_number, "
                "date_of_birth, account_status, district FROM farmers WHERE farmer_id = :f"
            ),
            {"f": farmer},
        ).one()
        status = conn.execute(
            text("SELECT status FROM erasure_request WHERE farmer_id = :f"), {"f": farmer}
        ).scalar_one()
    assert f.full_name == "ERASED"
    assert f.phone_primary == "ERASED"
    assert f.whatsapp_number == "ERASED"
    assert f.aadhar_number is None
    assert f.date_of_birth is None
    assert f.account_status == "inactive"
    assert f.district == "Chhatrapati Sambhajinagar"  # coarse location kept (§8)
    assert status == "completed"


async def test_not_yet_due_is_untouched(
    sessionmaker: async_sessionmaker[AsyncSession],
    farmer: uuid.UUID,
    sync_engine: Engine,
) -> None:
    # A sweep 5 days before the due date processes nothing.
    res = await fulfil_erasures(
        erasure_repo=PgErasureRequestRepo(sessionmaker),
        farmer_repo=PgFarmerRepo(sessionmaker),
        now=_NOW - timedelta(days=5),
    )
    assert res.processed == 0
    with sync_engine.begin() as conn:
        name = conn.execute(
            text("SELECT full_name FROM farmers WHERE farmer_id = :f"), {"f": farmer}
        ).scalar_one()
    assert name == "Real Name"  # untouched
