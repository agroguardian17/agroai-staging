"""Integration tests for
:class:`~app.infra.persistence.pg_qa_counters_repo.PgQaCountersRepo` (D12).

Seeds a plot with 1 confirmed-true-positive + 2 false-positive classifications
and 3 photos (2 labelled), and asserts the per-plot counters. Also checks that a
plot with no QA activity returns all zeros, not NULLs.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.qa_counters_repo import QaCountersRepo
from app.infra.persistence.pg_qa_counters_repo import PgQaCountersRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)

_FIRED_AT = datetime(2026, 8, 3, 6, 0, tzinfo=UTC)


def _seed(eng: Engine) -> dict[str, object]:
    run = uuid.uuid4().hex[:8]
    farmer_id = uuid.uuid4()
    farm_id = uuid.uuid4()
    season_id = uuid.uuid4()
    plot_id = f"PLOT_CNT_{run}"
    advisories = [uuid.uuid4() for _ in range(3)]
    photos = [uuid.uuid4() for _ in range(3)]
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
        # 3 advisories, classified 1 TP + 2 FP (distinct review weeks keep the
        # (advisory_id, review_week) uniqueness happy — one per advisory anyway).
        verdicts = [
            "confirmed_true_positive",
            "false_positive",
            "false_positive",
        ]
        for i, (adv, verdict) in enumerate(zip(advisories, verdicts, strict=True)):
            conn.execute(
                text(
                    """
                    INSERT INTO ai_suggestions (
                        suggestion_id, tenant_id, farmer_id, farm_id, plot_id, season_id,
                        generated_at, suggestion_type, full_message_marathi,
                        ai_model_version, rule_id
                    ) VALUES (
                        :sid, :tenant, :farmer, :farm, :plot, :season,
                        :gen_at, 'daily', 'सूचना', 'ginger-engine/v1.0', :rule
                    )
                    """
                ),
                {
                    "sid": adv,
                    "tenant": PILOT_TENANT,
                    "farmer": farmer_id,
                    "farm": farm_id,
                    "plot": plot_id,
                    "season": season_id,
                    "gen_at": _FIRED_AT,
                    "rule": f"D05-RF-00{i + 1}",
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO advisory_classification (
                        advisory_id, plot_id, farmer_id, rule_id, fired_at, review_week,
                        classification, reviewer
                    ) VALUES (
                        :adv, :plot, :farmer, :rule, :fired, :week, :verdict, 'agronomist_a'
                    )
                    """
                ),
                {
                    "adv": adv,
                    "plot": plot_id,
                    "farmer": farmer_id,
                    "rule": f"D05-RF-00{i + 1}",
                    "fired": _FIRED_AT,
                    "week": date(2026, 8, 3),
                    "verdict": verdict,
                },
            )
        # 3 photos; label 2 of them.
        for j, pid in enumerate(photos):
            conn.execute(
                text(
                    """
                    INSERT INTO farmer_photos (id, plot_id, farmer_id, submitted_at)
                    VALUES (:pid, :plot, :farmer, :at)
                    """
                ),
                {"pid": pid, "plot": plot_id, "farmer": farmer_id, "at": _FIRED_AT},
            )
            if j < 2:
                conn.execute(
                    text(
                        """
                        INSERT INTO photo_label (
                            photo_id, plot_id, farmer_id, submitted_at, label, labelled_by
                        ) VALUES (:pid, :plot, :farmer, :at, 'healthy', 'agronomist_a')
                        """
                    ),
                    {"pid": pid, "plot": plot_id, "farmer": farmer_id, "at": _FIRED_AT},
                )
    return {
        "farmer_id": farmer_id,
        "plot_id": plot_id,
        "advisories": advisories,
        "photos": photos,
    }


@pytest.fixture
def seed(sync_engine: Engine) -> Iterator[dict[str, object]]:
    ids = _seed(sync_engine)
    yield ids
    advisories = ids["advisories"]
    photos = ids["photos"]
    with sync_engine.begin() as conn:
        conn.execute(text("DELETE FROM photo_label WHERE photo_id = ANY(:p)"), {"p": photos})
        conn.execute(text("DELETE FROM farmer_photos WHERE id = ANY(:p)"), {"p": photos})
        conn.execute(
            text("DELETE FROM advisory_classification WHERE advisory_id = ANY(:a)"),
            {"a": advisories},
        )
        conn.execute(
            text("DELETE FROM ai_suggestions WHERE suggestion_id = ANY(:a)"), {"a": advisories}
        )
        conn.execute(text("DELETE FROM crop_seasons WHERE plot_id = :p"), {"p": ids["plot_id"]})
        conn.execute(text("DELETE FROM plots WHERE plot_id = :p"), {"p": ids["plot_id"]})
        conn.execute(text("DELETE FROM farms WHERE farmer_id = :f"), {"f": ids["farmer_id"]})
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": ids["farmer_id"]})


async def test_pg_qa_counters_repo_satisfies_protocol(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    assert isinstance(PgQaCountersRepo(sessionmaker), QaCountersRepo)


async def test_counts_for_plot(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: dict[str, object],
) -> None:
    repo = PgQaCountersRepo(sessionmaker)
    c = await repo.counts_for_plot(str(seed["plot_id"]))
    assert c.true_alarm_count == 1
    assert c.false_alarm_count == 2
    assert c.photo_uploaded_count == 3
    assert c.photo_labelled_count == 2


async def test_counts_for_plot_with_no_activity_is_zeros(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = PgQaCountersRepo(sessionmaker)
    c = await repo.counts_for_plot("PLOT_DOES_NOT_EXIST")
    assert c == c.__class__(0, 0, 0, 0)
