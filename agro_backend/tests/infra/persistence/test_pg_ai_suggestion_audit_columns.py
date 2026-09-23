"""Round-trip the advisory-audit columns on ai_suggestions (migration 0044).

Covers create() → find_by_id() carrying rule_id (0043) + confidence + rule_version
(0044), so the audit fields the daily job stamps survive a DB round trip.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.ai_suggestion_repo import AiSuggestion
from app.infra.persistence.pg_ai_suggestion_repo import PgAiSuggestionRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)


def _seed(eng: Engine) -> tuple[uuid.UUID, uuid.UUID, str, uuid.UUID]:
    run = uuid.uuid4().hex[:8]
    farmer_id = uuid.uuid4()
    farm_id = uuid.uuid4()
    season_id = uuid.uuid4()
    plot_id = f"PLOT_AUD_{run}"
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
    return farmer_id, farm_id, plot_id, season_id


@pytest.fixture
def seed(sync_engine: Engine) -> Iterator[tuple[uuid.UUID, uuid.UUID, str, uuid.UUID]]:
    farmer_id, farm_id, plot_id, season_id = _seed(sync_engine)
    yield farmer_id, farm_id, plot_id, season_id
    with sync_engine.begin() as conn:
        conn.execute(text("DELETE FROM ai_suggestions WHERE plot_id = :p"), {"p": plot_id})
        conn.execute(text("DELETE FROM crop_seasons WHERE plot_id = :p"), {"p": plot_id})
        conn.execute(text("DELETE FROM plots WHERE plot_id = :p"), {"p": plot_id})
        conn.execute(text("DELETE FROM farms WHERE farm_id = :f"), {"f": farm_id})
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": farmer_id})


async def test_audit_columns_round_trip(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, uuid.UUID],
) -> None:
    farmer_id, farm_id, plot_id, season_id = seed
    repo = PgAiSuggestionRepo(sessionmaker)
    sid = uuid.uuid4()
    await repo.create(
        AiSuggestion(
            suggestion_id=sid,
            tenant_id=uuid.UUID(PILOT_TENANT),
            farmer_id=farmer_id,
            farm_id=farm_id,
            plot_id=plot_id,
            season_id=season_id,
            generated_at=datetime(2026, 8, 3, 6, 0, tzinfo=UTC),
            suggestion_type="daily",
            full_message_marathi="सूचना",
            ai_model_version="ginger-engine/v1.0",
            tokens_used=None,
            generation_time_ms=None,
            rule_id="D05-RF-001",
            confidence=0.82,
            rule_version="ginger-kb/v1.0",
        )
    )
    got = await repo.find_by_id(sid)
    assert got is not None
    assert got.rule_id == "D05-RF-001"
    assert got.confidence == pytest.approx(0.82)
    assert got.rule_version == "ginger-kb/v1.0"
