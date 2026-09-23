"""Integration tests for the immutable advisory-audit log (A4.2, migration 0045).

Verifies the repo appends a row, and that the table is genuinely append-only —
UPDATE and DELETE both raise (the trigger holds even for the table owner).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.advisory_audit_repo import AdvisoryAuditRepo, AdvisoryAuditRow
from app.infra.persistence.pg_advisory_audit_repo import PgAdvisoryAuditRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)


def _seed(eng: Engine) -> tuple[str, uuid.UUID, uuid.UUID, uuid.UUID]:
    run = uuid.uuid4().hex[:8]
    farmer_id = uuid.uuid4()
    farm_id = uuid.uuid4()
    season_id = uuid.uuid4()
    plot_id = f"PLOT_AUDT_{run}"
    sid = uuid.uuid4()
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
                    :farmer, :tenant, 'A', 'अ', '+910000000000', '+910000000000',
                    'marathi', 'v', 't', 'd', 'Maharashtra', 'basic',
                    '2025-06-01', '2026-06-01', 'paid'
                )
                """
            ),
            {"farmer": farmer_id, "tenant": PILOT_TENANT},
        )
        conn.execute(
            text(
                """
                INSERT INTO farms (
                    farm_id, tenant_id, farmer_id, total_area_acre, gps_lat_center,
                    gps_lng_center, soil_type, water_source_primary, irrigation_type,
                    electricity_source
                ) VALUES (:farm, :tenant, :farmer, 1.0, 19.9, 75.7, 'black', 'well', 'drip', 'grid')
                """
            ),
            {"farm": farm_id, "tenant": PILOT_TENANT, "farmer": farmer_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO plots (
                    plot_id, tenant_id, farm_id, plot_number, area_acre,
                    gps_lat, gps_lng, irrigation_valve_id
                ) VALUES (:plot, :tenant, :farm, 1, 1.0, 19.9, 75.7, :valve)
                """
            ),
            {"plot": plot_id, "tenant": PILOT_TENANT, "farm": farm_id, "valve": f"V_{run}"},
        )
        conn.execute(
            text(
                """
                INSERT INTO crop_seasons (
                    season_id, tenant_id, farm_id, plot_id, season_name, season_type,
                    year, crop_name_marathi, crop_name_english, crop_variety,
                    crop_category, sowing_date, expected_harvest_date
                ) VALUES (
                    :season, :tenant, :farm, :plot, 'Kharif 2026', 'kharif',
                    2026, 'आले', 'Ginger', 'Mahima', 'cash_crop',
                    '2026-06-01', '2027-02-01'
                )
                """
            ),
            {"season": season_id, "tenant": PILOT_TENANT, "farm": farm_id, "plot": plot_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO ai_suggestions (
                    suggestion_id, tenant_id, farmer_id, farm_id, plot_id, season_id,
                    generated_at, suggestion_type, full_message_marathi, ai_model_version
                ) VALUES (
                    :sid, :tenant, :farmer, :farm, :plot, :season,
                    :gen, 'daily', 'सूचना', 'ginger-engine/v1.0'
                )
                """
            ),
            {
                "sid": sid,
                "tenant": PILOT_TENANT,
                "farmer": farmer_id,
                "farm": farm_id,
                "plot": plot_id,
                "season": season_id,
                "gen": datetime(2026, 8, 3, 6, 0, tzinfo=UTC),
            },
        )
    return plot_id, sid, farm_id, farmer_id


@pytest.fixture
def seed(sync_engine: Engine) -> Iterator[tuple[str, uuid.UUID]]:
    plot_id, sid, farm_id, farmer_id = _seed(sync_engine)
    yield plot_id, sid
    with sync_engine.begin() as conn:
        # advisory_audit is append-only; disable the guard to clean up in teardown.
        conn.execute(text("ALTER TABLE advisory_audit DISABLE TRIGGER advisory_audit_immutable"))
        conn.execute(text("DELETE FROM advisory_audit WHERE suggestion_id = :s"), {"s": sid})
        conn.execute(text("ALTER TABLE advisory_audit ENABLE TRIGGER advisory_audit_immutable"))
        conn.execute(text("DELETE FROM ai_suggestions WHERE suggestion_id = :s"), {"s": sid})
        conn.execute(text("DELETE FROM crop_seasons WHERE plot_id = :p"), {"p": plot_id})
        conn.execute(text("DELETE FROM plots WHERE plot_id = :p"), {"p": plot_id})
        conn.execute(text("DELETE FROM farms WHERE farm_id = :f"), {"f": farm_id})
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": farmer_id})


async def test_record_appends_row(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[str, uuid.UUID],
    sync_engine: Engine,
) -> None:
    _, sid = seed
    repo = PgAdvisoryAuditRepo(sessionmaker)
    assert isinstance(repo, AdvisoryAuditRepo)
    await repo.record(
        AdvisoryAuditRow(
            suggestion_id=sid,
            rule_id="D05-RF-001",
            rule_version="ginger-kb/v1.0",
            model_version="ginger-engine/v1.0",
            confidence=0.82,
            gate_results={"blocklist_hit": False, "phi_days_remaining": 12},
            inputs={"dap": 63, "stage": "vegetative"},
        )
    )
    with sync_engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT rule_id, confidence, gate_results->>'phi_days_remaining' AS phi "
                "FROM advisory_audit WHERE suggestion_id = :s"
            ),
            {"s": sid},
        ).one()
    assert row.rule_id == "D05-RF-001"
    assert float(row.confidence) == pytest.approx(0.82)
    assert row.phi == "12"


async def test_update_is_blocked(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[str, uuid.UUID],
    sync_engine: Engine,
) -> None:
    _, sid = seed
    await PgAdvisoryAuditRepo(sessionmaker).record(
        AdvisoryAuditRow(
            suggestion_id=sid,
            rule_id="D05-RF-001",
            rule_version=None,
            model_version=None,
            confidence=None,
        )
    )
    with pytest.raises(Exception, match="append-only"), sync_engine.begin() as conn:
        conn.execute(
            text("UPDATE advisory_audit SET rule_id = 'x' WHERE suggestion_id = :s"), {"s": sid}
        )


async def test_delete_is_blocked(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[str, uuid.UUID],
    sync_engine: Engine,
) -> None:
    _, sid = seed
    await PgAdvisoryAuditRepo(sessionmaker).record(
        AdvisoryAuditRow(
            suggestion_id=sid,
            rule_id=None,
            rule_version=None,
            model_version=None,
            confidence=None,
        )
    )
    with pytest.raises(Exception, match="append-only"), sync_engine.begin() as conn:
        conn.execute(text("DELETE FROM advisory_audit WHERE suggestion_id = :s"), {"s": sid})
