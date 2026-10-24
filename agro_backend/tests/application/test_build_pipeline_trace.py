"""Unit tests for pipeline-trace assembly."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.application.build_pipeline_trace import build_drop_trace, build_ingest_trace


class _Raw:
    def __init__(self, d: dict[str, Any]) -> None:
        self._d = d

    def model_dump(self) -> dict[str, Any]:
        return dict(self._d)


@dataclass
class _Model:
    raw_readings: _Raw
    node_id: str
    plot_id: str
    tenant_id: uuid.UUID
    recorded_at: datetime
    schema_id: str = "agro-guardian/telemetry/v2-raw"


@dataclass
class _Reading:
    recorded_at: datetime
    soil_moisture_1_pct: Decimal | None = None
    water_flow_lpm: Decimal | None = None


@dataclass
class _Rules:
    hits: int
    created: int
    cooldown_suppressed: int


@dataclass
class _Result:
    reading_id: int | None
    rules: _Rules | None


@dataclass
class _Cal:
    calibration_version: int


def _model(recorded: datetime, raw: dict[str, Any]) -> _Model:
    return _Model(
        raw_readings=_Raw(raw),
        node_id="AGR-SN-0001",
        plot_id="PLOT_PILOT_001",
        tenant_id=uuid.uuid4(),
        recorded_at=recorded,
    )


def test_clean_ingest_trace_is_ok_with_all_stages() -> None:
    now = datetime(2026, 10, 4, 6, 0, tzinfo=UTC)
    raw = {
        "soil_adc": 412,
        "battery_adc": 780,
        "pressure_adc": 340,
        "flow_pulses_window": 10,
        "flow_pulses_total": 10,
        "window_s": 300,
        "npk_ok": True,
    }
    model = _model(now, raw)
    reading = _Reading(
        recorded_at=now, soil_moisture_1_pct=Decimal("42.0"), water_flow_lpm=Decimal("3.2")
    )
    result = _Result(reading_id=5, rules=_Rules(hits=1, created=1, cooldown_suppressed=0))
    t = build_ingest_trace(
        topic="agro/v2/t/f/n/telemetry",
        model=model,
        reading=reading,
        result=result,
        calibration=_Cal(7),
        now=now,
    )
    assert t.overall == "ok"
    assert t.node_id == "AGR-SN-0001" and t.plot_id == "PLOT_PILOT_001"
    assert t.stages["s4_calibrate"]["calibration_version"] == 7
    assert t.stages["s6_persist"]["status"] == "inserted"
    assert t.stages["s7_rules"]["hits"] == 1
    assert t.stages["s5_clock_skew"]["applied"] is False
    assert t.raw_payload["soil_adc"] == 412
    assert t.calibrated["soil_moisture_1_pct"] == 42.0  # Decimal -> float
    assert t.drop_reason is None


def test_bad_calibrated_value_marks_trace_fail() -> None:
    now = datetime(2026, 10, 4, 6, 0, tzinfo=UTC)
    model = _model(now, {"soil_adc": 1, "window_s": 300, "npk_ok": True})
    reading = _Reading(recorded_at=now, soil_moisture_1_pct=Decimal("150"))  # impossible
    result = _Result(reading_id=5, rules=_Rules(0, 0, 0))
    t = build_ingest_trace(
        topic="x", model=model, reading=reading, result=result, calibration=_Cal(7), now=now
    )
    assert t.overall == "fail"
    assert any(v["field"] == "soil_moisture_1_pct" for v in t.validations)


def test_duplicate_persist_and_skew_detected() -> None:
    sent = datetime(2026, 10, 4, 6, 0, tzinfo=UTC)
    stored = datetime(2026, 10, 4, 6, 5, tzinfo=UTC)  # normalized → skew applied
    model = _model(sent, {"soil_adc": 1, "window_s": 300, "npk_ok": True})
    reading = _Reading(recorded_at=stored)
    result = _Result(reading_id=None, rules=None)  # duplicate
    t = build_ingest_trace(
        topic="x", model=model, reading=reading, result=result, calibration=_Cal(7), now=stored
    )
    assert t.stages["s6_persist"]["status"] == "duplicate"
    assert t.stages["s7_rules"]["status"] == "skipped"
    assert t.stages["s5_clock_skew"]["applied"] is True


def test_drop_trace() -> None:
    t = build_drop_trace(topic="agro/v2/x", reason="validation", stage="s2_validate")
    assert t.overall == "fail" and t.drop_reason == "validation"
    assert t.stages["s2_validate"]["status"] == "fail"


@dataclass
class _Rec:
    rule_id: str
    alert_type: str
    severity: str
    fired: bool
    cooldown_suppressed: bool
    alert_id: int | None
    value: str | None
    threshold: str | None


@dataclass
class _RulesVerbose:
    hits: int
    created: int
    cooldown_suppressed: int
    evaluations: list[_Rec]


def test_s7_rules_carries_per_rule_journey_and_events() -> None:
    # R3.1: the rule step records every rule's verdict plus the alert.created
    # events it emitted, and the persist step notes telemetry.ingested.
    now = datetime(2026, 10, 4, 6, 0, tzinfo=UTC)
    model = _model(now, {"soil_adc": 412, "window_s": 300, "npk_ok": True})
    reading = _Reading(recorded_at=now, soil_moisture_1_pct=Decimal("42.0"))
    evaluations = [
        _Rec("low_battery", "low_battery", "warning", True, False, 7, "3.10", "3.30"),
        _Rec("low_water", "low_water", "warning", True, True, None, "1.0", "2.0"),  # suppressed
        _Rec("frost", "frost", "critical", False, False, None, None, None),  # didn't fire
    ]
    result = _Result(
        reading_id=5,
        rules=_RulesVerbose(hits=2, created=1, cooldown_suppressed=1, evaluations=evaluations),
    )
    t = build_ingest_trace(
        topic="agro/v2/t/f/n/telemetry",
        model=model,
        reading=reading,
        result=result,
        calibration=_Cal(7),
        now=now,
    )
    s7 = t.stages["s7_rules"]
    assert [e["rule_id"] for e in s7["evaluations"]] == ["low_battery", "low_water", "frost"]
    assert s7["evaluations"][0]["alert_id"] == 7
    assert s7["evaluations"][1]["cooldown_suppressed"] is True
    assert s7["evaluations"][2]["fired"] is False
    # Exactly one alert.created event — the fired, non-suppressed rule.
    assert s7["events"] == [{"event": "alert.created", "alert_id": 7, "alert_type": "low_battery"}]
    # A fresh insert publishes telemetry.ingested.
    assert t.stages["s6_persist"]["events"] == ["telemetry.ingested"]
