"""Validate the variety_stage_water_target seed (migration 0050)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .conftest import DB_SKIP_REASON, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)


def test_mahima_stage_rows_seeded(sync_engine: Engine) -> None:
    with sync_engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT stage, stage_target_l_low, stage_target_l_high, "
                "per_event_l_high, max_l_per_event, source_tier "
                "FROM variety_stage_water_target WHERE variety = 'IISR Mahima' "
                "ORDER BY stage"
            )
        ).all()
    by_stage = {r.stage: r for r in rows}
    assert set(by_stage) == {"G1", "G2", "G3", "G4", "G5", "LIFECYCLE"}
    # Peak demand at G3 (§6.1).
    assert float(by_stage["G3"].stage_target_l_low) == 90.0
    assert float(by_stage["G3"].stage_target_l_high) == 110.0
    assert float(by_stage["G3"].max_l_per_event) == 4.0
    # G5: irrigation stops (per-event target 0), no max.
    assert float(by_stage["G5"].per_event_l_high) == 0.0
    assert by_stage["G5"].max_l_per_event is None
    # Lifecycle aggregate has no daily/per-event breakdown.
    assert float(by_stage["LIFECYCLE"].stage_target_l_high) == 250.0
    assert by_stage["LIFECYCLE"].per_event_l_high is None
    assert all(r.source_tier == "L3" for r in rows)


def test_only_mahima_seeded_pending_signed_csv(sync_engine: Engine) -> None:
    # Varada/Nadia intentionally wait for Kuldip's signed CSV (handoff v1.3 §6.1).
    with sync_engine.begin() as conn:
        varieties = {
            r.variety
            for r in conn.execute(
                text("SELECT DISTINCT variety FROM variety_stage_water_target")
            ).all()
        }
    assert "IISR Mahima" in varieties
    assert "IISR Varada" not in varieties
    assert "Nadia" not in varieties
