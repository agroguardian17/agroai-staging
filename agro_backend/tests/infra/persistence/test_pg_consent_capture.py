"""Integration tests for consent capture + append-only consent_event (0046)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.farmer_consent_repo import ConsentCapture, FarmerConsentRepo
from app.infra.persistence.pg_farmer_consent_repo import PgFarmerConsentRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)


def _seed_farmer(eng: Engine) -> uuid.UUID:
    farmer_id = uuid.uuid4()
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
                    :farmer, :tenant, 'A', 'अ', '+910000000001', '+910000000001',
                    'marathi', 'v', 't', 'd', 'Maharashtra', 'basic',
                    '2025-06-01', '2026-06-01', 'paid'
                )
                """
            ),
            {"farmer": farmer_id, "tenant": PILOT_TENANT},
        )
    return farmer_id


@pytest.fixture
def farmer(sync_engine: Engine) -> Iterator[uuid.UUID]:
    fid = _seed_farmer(sync_engine)
    yield fid
    with sync_engine.begin() as conn:
        conn.execute(text("ALTER TABLE consent_event DISABLE TRIGGER consent_event_immutable"))
        conn.execute(text("DELETE FROM consent_event WHERE farmer_id = :f"), {"f": fid})
        conn.execute(text("ALTER TABLE consent_event ENABLE TRIGGER consent_event_immutable"))
        conn.execute(text("DELETE FROM farmer_consent WHERE farmer_id = :f"), {"f": fid})
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": fid})


def _capture(fid: uuid.UUID) -> ConsentCapture:
    return ConsentCapture(
        farmer_id=fid,
        tenant_id=uuid.UUID(PILOT_TENANT),
        consent_advisory=True,
        consent_research=True,
        third_party_share_consent_given=False,
        consent_version="dpdp-consent/v1",
        consent_notice_hash="deadbeef",
        notice_shown_at=datetime(2026, 11, 1, 9, 0, tzinfo=UTC),
        consent_channel="whatsapp",
        consent_date=date(2026, 11, 1),
        data_retention_until=date(2029, 11, 1),
    )


async def test_capture_upserts_and_reads_back(
    sessionmaker: async_sessionmaker[AsyncSession],
    farmer: uuid.UUID,
    sync_engine: Engine,
) -> None:
    repo = PgFarmerConsentRepo(sessionmaker)
    assert isinstance(repo, FarmerConsentRepo)
    await repo.capture(_capture(farmer))
    # Upsert again with research withdrawn — same row updates in place.
    await repo.capture(replace(_capture(farmer), consent_research=False))

    with sync_engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT consent_advisory, consent_research, consent_version, "
                "data_retention_until FROM farmer_consent WHERE farmer_id = :f"
            ),
            {"f": farmer},
        ).one()
    assert row.consent_advisory is True
    assert row.consent_research is False  # updated in place
    assert row.consent_version == "dpdp-consent/v1"
    assert row.data_retention_until == date(2029, 11, 1)


async def test_events_are_append_only(
    sessionmaker: async_sessionmaker[AsyncSession],
    farmer: uuid.UUID,
    sync_engine: Engine,
) -> None:
    repo = PgFarmerConsentRepo(sessionmaker)
    await repo.record_event(
        farmer_id=farmer,
        event_type="given",
        scope="advisory",
        consent_version="dpdp-consent/v1",
        channel="whatsapp",
        actor="reg_flow",
    )
    with sync_engine.begin() as conn:
        n = conn.execute(
            text("SELECT count(*) FROM consent_event WHERE farmer_id = :f"), {"f": farmer}
        ).scalar_one()
    assert n == 1
    with pytest.raises(Exception, match="append-only"), sync_engine.begin() as conn:
        conn.execute(text("DELETE FROM consent_event WHERE farmer_id = :f"), {"f": farmer})
