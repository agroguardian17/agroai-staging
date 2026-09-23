"""Integration tests for
:class:`~app.infra.persistence.pg_qa_digest_repo.PgQaDigestRepo` (D12).

Seeds one review week's worth of QA rows and asserts the gathered counts. Uses a
review week (2026-07-06) distinct from the write-path test's, so the windowed
counts do not collide with other modules' rows.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.qa_digest_repo import QaDigestRepo
from app.infra.persistence.pg_qa_digest_repo import PgQaDigestRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)

_WEEK_START = date(2026, 7, 6)
_WEEK_END = date(2026, 7, 13)
_GEN_AT = datetime(2026, 7, 8, 6, 0, tzinfo=UTC)  # inside the window


def _seed(eng: Engine) -> dict[str, object]:
    run = uuid.uuid4().hex[:8]
    farmer_id = uuid.uuid4()
    farm_id = uuid.uuid4()
    season_id = uuid.uuid4()
    plot_id = f"PLOT_DIG_{run}"
    adv_a = uuid.uuid4()
    adv_b = uuid.uuid4()
    photo_id = uuid.uuid4()
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
                ) VALUES (
                    :farm, :tenant, :farmer, 1.0, 19.9, 75.7, 'black', 'well', 'drip', 'grid'
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
        for adv, rule in ((adv_a, "D05-RF-001"), (adv_b, "D07-VP-002")):
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
                    "gen_at": _GEN_AT,
                    "rule": rule,
                },
            )
        # A: false positive; B: confirmed true positive.
        for adv, rule, verdict in (
            (adv_a, "D05-RF-001", "false_positive"),
            (adv_b, "D07-VP-002", "confirmed_true_positive"),
        ):
            conn.execute(
                text(
                    """
                    INSERT INTO advisory_classification (
                        advisory_id, plot_id, farmer_id, rule_id, fired_at, review_week,
                        classification, evidence_source, reviewer
                    ) VALUES (
                        :adv, :plot, :farmer, :rule, :fired, :week,
                        :verdict, 'agronomist_visit', 'agronomist_a'
                    )
                    """
                ),
                {
                    "adv": adv,
                    "plot": plot_id,
                    "farmer": farmer_id,
                    "rule": rule,
                    "fired": _GEN_AT,
                    "week": _WEEK_START,
                    "verdict": verdict,
                },
            )
        conn.execute(
            text(
                """
                INSERT INTO non_compliance_reason (
                    advisory_id, plot_id, farmer_id, action_state, reason,
                    captured_via, captured_by, captured_at
                ) VALUES (
                    :adv, :plot, :farmer, 'not_acted', 'cost_barrier',
                    'whatsapp_reply', 'agronomist_a', :cap_at
                )
                """
            ),
            {"adv": adv_a, "plot": plot_id, "farmer": farmer_id, "cap_at": _GEN_AT},
        )
        conn.execute(
            text(
                """
                INSERT INTO bias_observation (
                    observed_week, bias_type, scope_domain, scope_rule_id,
                    observation_mr, observed_by, kb_author_read
                ) VALUES (
                    :week, 'over_issuing', 'D05', 'D05-RF-001',
                    'खूप जास्त सूचना', 'agronomist_a', false
                )
                """
            ),
            {"week": _WEEK_START},
        )
        # An unlabelled photo older than 7 days -> counts toward the live backlog.
        conn.execute(
            text(
                """
                INSERT INTO farmer_photos (id, plot_id, farmer_id, submitted_at)
                VALUES (:pid, :plot, :farmer, :old)
                """
            ),
            {
                "pid": photo_id,
                "plot": plot_id,
                "farmer": farmer_id,
                "old": datetime.now(UTC) - timedelta(days=10),
            },
        )
    return {
        "farmer_id": farmer_id,
        "plot_id": plot_id,
        "adv_a": adv_a,
        "adv_b": adv_b,
        "photo_id": photo_id,
    }


@pytest.fixture
def seed(sync_engine: Engine) -> Iterator[dict[str, object]]:
    ids = _seed(sync_engine)
    yield ids
    with sync_engine.begin() as conn:
        conn.execute(text("DELETE FROM photo_label WHERE photo_id = :p"), {"p": ids["photo_id"]})
        conn.execute(text("DELETE FROM farmer_photos WHERE id = :p"), {"p": ids["photo_id"]})
        conn.execute(
            text("DELETE FROM bias_observation WHERE observed_week = :w AND scope_domain = 'D05'"),
            {"w": _WEEK_START},
        )
        conn.execute(
            text("DELETE FROM non_compliance_reason WHERE advisory_id IN (:a, :b)"),
            {"a": ids["adv_a"], "b": ids["adv_b"]},
        )
        conn.execute(
            text("DELETE FROM advisory_classification WHERE advisory_id IN (:a, :b)"),
            {"a": ids["adv_a"], "b": ids["adv_b"]},
        )
        conn.execute(
            text("DELETE FROM ai_suggestions WHERE suggestion_id IN (:a, :b)"),
            {"a": ids["adv_a"], "b": ids["adv_b"]},
        )
        conn.execute(text("DELETE FROM crop_seasons WHERE plot_id = :p"), {"p": ids["plot_id"]})
        conn.execute(text("DELETE FROM plots WHERE plot_id = :p"), {"p": ids["plot_id"]})
        conn.execute(text("DELETE FROM farms WHERE farmer_id = :f"), {"f": ids["farmer_id"]})
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": ids["farmer_id"]})


async def test_pg_qa_digest_repo_satisfies_protocol(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    assert isinstance(PgQaDigestRepo(sessionmaker), QaDigestRepo)


async def test_gather_counts_the_review_window(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: dict[str, object],
) -> None:
    repo = PgQaDigestRepo(sessionmaker)
    data = await repo.gather(_WEEK_START, _WEEK_END, top_fp_rules=5)

    assert data.classification_counts == {"false_positive": 1, "confirmed_true_positive": 1}
    assert data.classified_count == 2
    assert data.total_advisories == 2
    assert data.false_positive_rules[0].rule_id == "D05-RF-001"
    assert data.false_positive_rules[0].count == 1
    assert data.non_compliance_counts == {"cost_barrier": 1}
    assert len(data.bias_observations) == 1
    assert data.bias_observations[0].observation_mr == "खूप जास्त सूचना"
    assert data.unread_bias_total >= 1
    assert data.photo_backlog >= 1
