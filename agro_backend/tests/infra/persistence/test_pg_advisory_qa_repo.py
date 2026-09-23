"""Integration tests for
:class:`~app.infra.persistence.pg_advisory_qa_repo.PgAdvisoryQaRepo` (D12).

Seeds one delivered advisory (with a ``rule_id``) and verifies the classification
and non-compliance upserts, including the conflict path that lets a reviewer
correct an entry in place.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.advisory_qa_repo import (
    AdvisoryQaRepo,
    ClassificationRow,
    NonComplianceRow,
)
from app.infra.persistence.pg_advisory_qa_repo import PgAdvisoryQaRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)

_FIRED_AT = datetime(2026, 6, 17, 6, 0, tzinfo=UTC)
_WEEK = date(2026, 6, 15)


def _seed(eng: Engine) -> tuple[uuid.UUID, uuid.UUID, str]:
    """One farmer/farm/plot/season + one advisory carrying a rule_id."""
    run = uuid.uuid4().hex[:8]
    farmer_id = uuid.uuid4()
    farm_id = uuid.uuid4()
    season_id = uuid.uuid4()
    advisory_id = uuid.uuid4()
    plot_id = f"PLOT_QA_{run}"
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
        conn.execute(
            text(
                """
                INSERT INTO ai_suggestions (
                    suggestion_id, tenant_id, farmer_id, farm_id, plot_id, season_id,
                    generated_at, suggestion_type, full_message_marathi,
                    ai_model_version, rule_id
                ) VALUES (
                    :sid, :tenant, :farmer, :farm, :plot, :season,
                    :gen_at, 'daily', 'सूचना', 'ginger-engine/v1.0', 'D05-RF-001'
                )
                """
            ),
            {
                "sid": advisory_id,
                "tenant": PILOT_TENANT,
                "farmer": farmer_id,
                "farm": farm_id,
                "plot": plot_id,
                "season": season_id,
                "gen_at": _FIRED_AT,
            },
        )
    return advisory_id, farmer_id, plot_id


@pytest.fixture
def seed(sync_engine: Engine) -> Iterator[tuple[uuid.UUID, uuid.UUID, str]]:
    advisory_id, farmer_id, plot_id = _seed(sync_engine)
    yield advisory_id, farmer_id, plot_id
    with sync_engine.begin() as conn:
        conn.execute(
            text("DELETE FROM advisory_classification WHERE advisory_id = :a"),
            {"a": advisory_id},
        )
        conn.execute(
            text("DELETE FROM non_compliance_reason WHERE advisory_id = :a"), {"a": advisory_id}
        )
        conn.execute(
            text("DELETE FROM ai_suggestions WHERE suggestion_id = :a"), {"a": advisory_id}
        )
        conn.execute(text("DELETE FROM crop_seasons WHERE plot_id = :p"), {"p": plot_id})
        conn.execute(text("DELETE FROM plots WHERE plot_id = :p"), {"p": plot_id})
        conn.execute(text("DELETE FROM farms WHERE farmer_id = :f"), {"f": farmer_id})
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": farmer_id})


def _classification(
    advisory_id: uuid.UUID, farmer_id: uuid.UUID, plot_id: str, *, verdict: str
) -> ClassificationRow:
    return ClassificationRow(
        advisory_id=advisory_id,
        plot_id=plot_id,
        farmer_id=farmer_id,
        rule_id="D05-RF-001",
        fired_at=_FIRED_AT,
        review_week=_WEEK,
        classification=verdict,
        evidence_source="agronomist_visit",
        classification_note="note",
        reviewer="agronomist_a",
    )


async def test_pg_advisory_qa_repo_satisfies_protocol(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    assert isinstance(PgAdvisoryQaRepo(sessionmaker), AdvisoryQaRepo)


async def test_classification_insert_then_conflict_updates_in_place(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str],
    sync_engine: Engine,
) -> None:
    advisory_id, farmer_id, plot_id = seed
    repo = PgAdvisoryQaRepo(sessionmaker)

    await repo.upsert_classification(
        _classification(advisory_id, farmer_id, plot_id, verdict="unresolved")
    )
    # Same (advisory_id, review_week) -> update, not a second row.
    await repo.upsert_classification(
        _classification(advisory_id, farmer_id, plot_id, verdict="false_positive")
    )

    with sync_engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT classification FROM advisory_classification "
                "WHERE advisory_id = :a AND review_week = :w"
            ),
            {"a": advisory_id, "w": _WEEK},
        ).all()
    assert [r.classification for r in rows] == ["false_positive"]


async def test_non_compliance_insert_then_conflict_updates_in_place(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str],
    sync_engine: Engine,
) -> None:
    advisory_id, farmer_id, plot_id = seed
    repo = PgAdvisoryQaRepo(sessionmaker)

    await repo.upsert_non_compliance(
        NonComplianceRow(
            advisory_id=advisory_id,
            plot_id=plot_id,
            farmer_id=farmer_id,
            action_state="not_acted",
            reason="forgot",
            reason_detail_mr=None,
            captured_via="whatsapp_reply",
            captured_by="agronomist_a",
        )
    )
    await repo.upsert_non_compliance(
        NonComplianceRow(
            advisory_id=advisory_id,
            plot_id=plot_id,
            farmer_id=farmer_id,
            action_state="partially_acted",
            reason="cost_barrier",
            reason_detail_mr="महाग",
            captured_via="agronomist_call",
            captured_by="agronomist_b",
        )
    )

    with sync_engine.begin() as conn:
        rows = conn.execute(
            text("SELECT action_state, reason FROM non_compliance_reason WHERE advisory_id = :a"),
            {"a": advisory_id},
        ).all()
    assert len(rows) == 1
    assert rows[0].action_state == "partially_acted"
    assert rows[0].reason == "cost_barrier"
