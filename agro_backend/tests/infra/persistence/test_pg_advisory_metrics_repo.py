"""Integration tests for
:class:`~app.infra.persistence.pg_advisory_metrics_repo.PgAdvisoryMetricsRepo`.

Seeds a season with four advisories - sent+on-time, sent+late, sent+ignored,
and unsent - and asserts the Domain 12 compliance counters.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.advisory_metrics_repo import AdvisoryMetricsRepo
from app.infra.persistence.pg_advisory_metrics_repo import PgAdvisoryMetricsRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)

_ISSUED_AT = datetime(2026, 8, 1, 6, 30, tzinfo=UTC)


def _seed(eng: Engine) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, str, uuid.UUID]:
    run = uuid.uuid4().hex[:8]
    farmer_id = uuid.uuid4()
    farm_id = uuid.uuid4()
    plot_id = f"PLOT_ADV_{run}"
    season_id = uuid.uuid4()
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
                    :farmer, :tenant, 'A', 'अ', '+910000000000',
                    '+910000000000', 'marathi', 'v', 't', 'd',
                    'Maharashtra', 'basic', '2025-06-01', '2026-06-01', 'paid'
                )
                """
            ),
            {"farmer": farmer_id, "tenant": PILOT_TENANT},
        )
        conn.execute(
            text(
                """
                INSERT INTO farms (
                    farm_id, tenant_id, farmer_id, total_area_acre,
                    gps_lat_center, gps_lng_center, soil_type,
                    water_source_primary, irrigation_type, electricity_source
                ) VALUES (
                    :farm, :tenant, :farmer, 1.0, 19.9, 75.7, 'black',
                    'well', 'drip', 'grid'
                )
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
                ) VALUES (
                    :plot, :tenant, :farm, 1, 1.0, 19.9, 75.7, :valve
                )
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
                    2026, 'आले', 'Ginger', 'Mahima',
                    'cash_crop', '2026-06-01', '2027-02-01'
                )
                """
            ),
            {"season": season_id, "tenant": PILOT_TENANT, "farm": farm_id, "plot": plot_id},
        )
    return farmer_id, farm_id, season_id, plot_id, uuid.UUID(PILOT_TENANT)


def _add_advisory(
    eng: Engine,
    *,
    ids: tuple[uuid.UUID, uuid.UUID, uuid.UUID, str, uuid.UUID],
    sent: bool,
    followed_after_days: int | None,
) -> uuid.UUID:
    """Insert one sent/unsent advisory and (optionally) a following action."""
    farmer_id, farm_id, season_id, plot_id, tenant_id = ids
    suggestion_id = uuid.uuid4()
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO ai_suggestions (
                    suggestion_id, tenant_id, farmer_id, farm_id, plot_id, season_id,
                    generated_at, suggestion_type, full_message_marathi,
                    ai_model_version, whatsapp_sent
                ) VALUES (
                    :sid, :tenant, :farmer, :farm, :plot, :season,
                    :gen_at, 'alert', 'सूचना', 'ginger-engine/v1.0', :sent
                )
                """
            ),
            {
                "sid": suggestion_id,
                "tenant": tenant_id,
                "farmer": farmer_id,
                "farm": farm_id,
                "plot": plot_id,
                "season": season_id,
                "gen_at": _ISSUED_AT,
                "sent": sent,
            },
        )
        if followed_after_days is not None:
            conn.execute(
                text(
                    """
                    INSERT INTO farmer_actions (
                        tenant_id, farmer_id, farm_id, plot_id, season_id,
                        action_date, action_type, ai_suggestion_id,
                        ai_suggested, farmer_followed_ai, source
                    ) VALUES (
                        :tenant, :farmer, :farm, :plot, :season,
                        :adate, 'watering', :sid, TRUE, TRUE, 'whatsapp_reply'
                    )
                    """
                ),
                {
                    "tenant": tenant_id,
                    "farmer": farmer_id,
                    "farm": farm_id,
                    "plot": plot_id,
                    "season": season_id,
                    "adate": _ISSUED_AT.date() + timedelta(days=followed_after_days),
                    "sid": suggestion_id,
                },
            )
    return suggestion_id


@pytest.fixture
def seed(sync_engine: Engine) -> Iterator[tuple[uuid.UUID, uuid.UUID, uuid.UUID, str, uuid.UUID]]:
    ids = _seed(sync_engine)
    yield ids
    _farmer, _farm, _season, plot_id, _tenant = ids
    with sync_engine.begin() as conn:
        conn.execute(text("DELETE FROM farmer_actions WHERE plot_id = :p"), {"p": plot_id})
        conn.execute(text("DELETE FROM ai_suggestions WHERE plot_id = :p"), {"p": plot_id})
        conn.execute(text("DELETE FROM crop_seasons WHERE plot_id = :p"), {"p": plot_id})
        conn.execute(text("DELETE FROM plots WHERE plot_id = :p"), {"p": plot_id})
        conn.execute(text("DELETE FROM farms WHERE farm_id = :f"), {"f": _farm})
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": _farmer})


@pytest.mark.asyncio
async def test_satisfies_protocol(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    assert isinstance(PgAdvisoryMetricsRepo(sessionmaker), AdvisoryMetricsRepo)


@pytest.mark.asyncio
async def test_counts_issued_completed_and_on_time(
    sync_engine: Engine,
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, uuid.UUID, str, uuid.UUID],
) -> None:
    _add_advisory(sync_engine, ids=seed, sent=True, followed_after_days=1)  # on time
    _add_advisory(sync_engine, ids=seed, sent=True, followed_after_days=10)  # late
    _add_advisory(sync_engine, ids=seed, sent=True, followed_after_days=None)  # ignored
    _add_advisory(sync_engine, ids=seed, sent=False, followed_after_days=1)  # not delivered

    season_id = seed[2]
    perf = await PgAdvisoryMetricsRepo(sessionmaker).performance_for_season(
        season_id, on_time_days=3
    )
    assert perf.advisory_issued_count == 3
    assert perf.advisory_completed_count == 2
    assert perf.advisory_completed_on_time_count == 1
    assert perf.action_compliance_rate == Decimal("33.3")


@pytest.mark.asyncio
async def test_no_advisories_yields_null_rate(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, uuid.UUID, str, uuid.UUID],
) -> None:
    perf = await PgAdvisoryMetricsRepo(sessionmaker).performance_for_season(seed[2])
    assert perf.advisory_issued_count == 0
    assert perf.action_compliance_rate is None
