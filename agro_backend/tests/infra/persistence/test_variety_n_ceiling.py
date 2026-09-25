"""Validate the variety_n_ceiling seed (migration 0052)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .conftest import DB_SKIP_REASON, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)


def test_variety_ceilings_seeded(sync_engine: Engine) -> None:
    with sync_engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT variety, total_n_ceiling_kg_per_acre, late_stage_n_cutoff_dap, "
                "source_tier FROM variety_n_ceiling ORDER BY total_n_ceiling_kg_per_acre DESC"
            )
        ).all()
    by_variety = {r.variety: r for r in rows}
    assert set(by_variety) == {"IISR-Mahima", "IISR-Varada", "Nadia-local"}
    # Ceilings per CSV (kg N/acre): Mahima 61 (L3 baseline), Varada 55, Nadia 52 (L4 derived).
    assert float(by_variety["IISR-Mahima"].total_n_ceiling_kg_per_acre) == 61.0
    assert float(by_variety["IISR-Varada"].total_n_ceiling_kg_per_acre) == 55.0
    assert float(by_variety["Nadia-local"].total_n_ceiling_kg_per_acre) == 52.0
    assert by_variety["IISR-Mahima"].source_tier == "L3"
    assert by_variety["IISR-Varada"].source_tier == "L4"
    # DAP-150 hard cutoff shared across varieties (D04-NS-003).
    assert all(r.late_stage_n_cutoff_dap == 150 for r in rows)


def test_split_schedule_sums_to_ceiling(sync_engine: Engine) -> None:
    # basal + two top-dresses reconcile with the total ceiling (rounding tolerance).
    with sync_engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT variety, total_n_ceiling_kg_per_acre, basal_dap_0_kg_per_acre, "
                "top_dress_45_dap_kg_per_acre, top_dress_120_dap_kg_per_acre "
                "FROM variety_n_ceiling"
            )
        ).all()
    for r in rows:
        split_sum = (
            float(r.basal_dap_0_kg_per_acre)
            + float(r.top_dress_45_dap_kg_per_acre)
            + float(r.top_dress_120_dap_kg_per_acre)
        )
        assert abs(split_sum - float(r.total_n_ceiling_kg_per_acre)) <= 1.0, r.variety
