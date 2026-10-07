"""Daily-advisory idempotency: the partial unique index (0066) + ON CONFLICT.

A re-run (or a KB-version-reset replay) that re-emits the same
(plot, run-day, rule) ginger advisory must NOT create a duplicate row. The
second create() returns None (idempotent skip); a different rule_id still
inserts; and the index's forward cutoff means we test with a future
generated_at so it is in scope.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.ai_suggestion_repo import AiSuggestion
from app.infra.persistence.pg_ai_suggestion_repo import PgAiSuggestionRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)

# Well past the index's "start of tomorrow" cutoff, so the rows are in scope.
# Same UTC-midnight value for every row so generated_at::date matches.
_GEN_AT = (datetime.now(UTC) + timedelta(days=5)).replace(hour=0, minute=0, second=0, microsecond=0)


def _seed(eng: Engine) -> tuple[uuid.UUID, uuid.UUID, str, uuid.UUID]:
    run = uuid.uuid4().hex[:8]
    farmer_id, farm_id, season_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    plot_id = f"PLOT_IDEM_{run}"
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


def _ginger_row(seed: tuple[uuid.UUID, uuid.UUID, str, uuid.UUID], *, rule_id: str) -> AiSuggestion:
    farmer_id, farm_id, plot_id, season_id = seed
    return AiSuggestion(
        suggestion_id=uuid.uuid4(),
        tenant_id=uuid.UUID(PILOT_TENANT),
        farmer_id=farmer_id,
        farm_id=farm_id,
        plot_id=plot_id,
        season_id=season_id,
        generated_at=_GEN_AT,
        suggestion_type="daily",
        full_message_marathi="सूचना",
        ai_model_version="ginger-engine/v1.0",
        tokens_used=None,
        generation_time_ms=None,
        rule_id=rule_id,
        confidence=0.8,
        rule_version="ginger-kb/v1.0",
    )


async def test_same_rule_same_day_is_idempotent(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, uuid.UUID],
) -> None:
    repo = PgAiSuggestionRepo(sessionmaker)
    first = await repo.create(_ginger_row(seed, rule_id="D05-RF-001"))
    second = await repo.create(_ginger_row(seed, rule_id="D05-RF-001"))  # replay
    assert first is not None
    assert second is None  # skipped by the daily-unique index

    plot_id = seed[2]
    async with sessionmaker() as s:
        n = (
            await s.execute(
                text(
                    "SELECT count(*) FROM ai_suggestions "
                    "WHERE plot_id = :p AND rule_id = 'D05-RF-001'"
                ),
                {"p": plot_id},
            )
        ).scalar_one()
    assert n == 1


async def test_different_rule_same_day_inserts_separately(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, uuid.UUID],
) -> None:
    repo = PgAiSuggestionRepo(sessionmaker)
    a = await repo.create(_ginger_row(seed, rule_id="D05-RF-001"))
    b = await repo.create(_ginger_row(seed, rule_id="D07-WS-001"))
    assert a is not None and b is not None  # one row per distinct fired rule

    plot_id = seed[2]
    async with sessionmaker() as s:
        n = (
            await s.execute(
                text("SELECT count(*) FROM ai_suggestions WHERE plot_id = :p"),
                {"p": plot_id},
            )
        ).scalar_one()
    assert n == 2
