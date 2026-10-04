"""Unit tests for daily-run trace assembly."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.build_plot_run_trace import build_plot_run_trace


@dataclass
class _Season:
    plot_id: str
    season_id: uuid.UUID
    tenant_id: uuid.UUID
    farm_id: uuid.UUID


@dataclass
class _State:
    state: dict
    filled: frozenset
    unknown: frozenset


class _Msg:
    def __init__(self, rid: str) -> None:
        self.rule_id = rid


def _season() -> _Season:
    return _Season("PLOT_PILOT_001", uuid.uuid4(), uuid.uuid4(), uuid.uuid4())


def test_run_trace_ok_with_coverage_and_rules() -> None:
    state = _State(
        state={"dap": 100, "plot_status": "growing", "stage_water_deficit_ratio": Decimal("0.4")},
        filled=frozenset(
            {"dap", "plot_status", "stage_water_deficit_ratio"} | {f"x{i}" for i in range(70)}
        ),
        unknown=frozenset({f"u{i}" for i in range(10)}),
    )
    engine = {
        "messages": [_Msg("D03-WB-001"), _Msg("D04-MC-005")],
        "delivery": {"D03-WB-001": "WINDOW"},
    }
    t = build_plot_run_trace(
        plot_id="PLOT_PILOT_001",
        season=_season(),
        run_date=date(2026, 10, 4),
        state=state,
        engine_result=engine,
        advisories_written=2,
    )
    assert t.overall == "ok"
    assert t.coverage["filled"] == 73 and t.coverage["unknown"] == 10
    assert t.coverage["coverage_pct"] == round(73 / 83, 3)
    assert t.derived["dap"] == 100
    assert t.derived["stage_water_deficit_ratio"] == 0.4  # Decimal -> float
    assert t.engine["messages"] == 2
    assert "D03-WB-001" in t.engine["rule_ids"]
    assert t.stages["s10_advisory"]["advisories_written"] == 2


def test_low_coverage_warns() -> None:
    state = _State(
        state={}, filled=frozenset({"a", "b"}), unknown=frozenset({f"u{i}" for i in range(20)})
    )
    t = build_plot_run_trace(
        plot_id="P",
        season=_season(),
        run_date=date(2026, 10, 4),
        state=state,
        engine_result={"messages": []},
        advisories_written=0,
    )
    assert t.overall == "warn"
    assert any(v["field"] == "coverage_pct" for v in t.validations)


def test_error_run_is_fail_and_tolerates_none_state() -> None:
    t = build_plot_run_trace(
        plot_id="P",
        season=_season(),
        run_date=date(2026, 10, 4),
        state=None,
        engine_result=None,
        advisories_written=0,
        error="boom",
    )
    assert t.overall == "fail" and t.error == "boom"
    assert t.stages["s8_farm_brain"]["status"] == "fail"
    assert t.coverage["total"] == 0
