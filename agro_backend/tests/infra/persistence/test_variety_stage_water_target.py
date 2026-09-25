"""Validate the variety_stage_water_target seed (migrations 0050 + 0051 re-seed)."""

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
                "SELECT stage, dap_start, dap_end, "
                "stage_target_l_low, stage_target_l_high, "
                "per_event_l_high, max_l_per_event, source_tier "
                "FROM variety_stage_water_target WHERE variety = 'IISR-Mahima' "
                "ORDER BY stage"
            )
        ).all()
    by_stage = {r.stage: r for r in rows}
    # G0 (pre-plant bed prep) added in the 0051 re-seed.
    assert set(by_stage) == {"G0", "G1", "G2", "G3", "G4", "G5", "LIFECYCLE"}
    # Peak demand at G3 (CSV / handoff §6.1), DAP window 91-150.
    assert float(by_stage["G3"].stage_target_l_low) == 90.0
    assert float(by_stage["G3"].stage_target_l_high) == 110.0
    assert float(by_stage["G3"].max_l_per_event) == 4.0
    assert by_stage["G3"].dap_start == 91
    assert by_stage["G3"].dap_end == 150
    # G5: irrigation stops (per-event and max both 0 in the CSV, not NULL).
    assert float(by_stage["G5"].per_event_l_high) == 0.0
    assert float(by_stage["G5"].max_l_per_event) == 0.0
    # Lifecycle aggregate has no daily/per-event breakdown.
    assert float(by_stage["LIFECYCLE"].stage_target_l_high) == 250.0
    assert by_stage["LIFECYCLE"].per_event_l_high is None
    assert all(r.source_tier == "L3" for r in rows)


def test_three_varieties_seeded(sync_engine: Engine) -> None:
    # 0051 re-seed loads all three Season-1 Kannad varieties from the signed CSV.
    with sync_engine.begin() as conn:
        varieties = {
            r.variety
            for r in conn.execute(
                text("SELECT DISTINCT variety FROM variety_stage_water_target")
            ).all()
        }
    assert varieties == {"IISR-Mahima", "IISR-Varada", "Nadia-local"}
    # The old space-keyed 0050 seed is gone.
    assert "IISR Mahima" not in varieties


def test_lower_demand_varieties_ordered(sync_engine: Engine) -> None:
    # Varada (~-10%) and Nadia (~-15%) carry lower G3 targets than Mahima.
    with sync_engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT variety, stage_target_l_high FROM variety_stage_water_target "
                "WHERE stage = 'G3' ORDER BY stage_target_l_high DESC"
            )
        ).all()
    high_by_variety = {r.variety: float(r.stage_target_l_high) for r in rows}
    assert high_by_variety["IISR-Mahima"] == 110.0
    assert high_by_variety["IISR-Varada"] == 100.0
    assert high_by_variety["Nadia-local"] == 94.0
