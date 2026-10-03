"""Unit tests for the ingest plausibility checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain import pipeline_validation as pv


def test_clean_raw_and_calibrated_produce_no_findings() -> None:
    raw = {
        "soil_adc": 412,
        "battery_adc": 780,
        "pressure_adc": 340,
        "flow_pulses_window": 1750,
        "flow_pulses_total": 8241,
        "window_s": 300,
        "npk_ok": True,
        "fault_flags": None,
    }
    cal = {
        "soil_moisture_1_pct": 42.0,
        "soil_temp_c": 27.5,
        "water_flow_lpm": 3.2,
        "battery_voltage_v": 3.9,
        "soil_ph": 6.4,
    }
    assert pv.validate_raw(raw) == []
    assert pv.validate_calibrated(cal) == []


def test_impossible_calibrated_values_fail() -> None:
    cal = {"soil_moisture_avg_pct": 142.0, "water_flow_lpm": -3, "soil_ph": 20}
    findings = pv.validate_calibrated(cal)
    fields = {f.field for f in findings}
    assert {"soil_moisture_avg_pct", "water_flow_lpm", "soil_ph"} <= fields
    assert pv.worst_level(findings) == pv.FAIL


def test_window_zero_and_npk_fail_are_warnings() -> None:
    raw = {
        "soil_adc": 1,
        "battery_adc": 1,
        "pressure_adc": 1,
        "flow_pulses_window": 0,
        "flow_pulses_total": 0,
        "window_s": 0,
        "npk_ok": False,
    }
    findings = pv.validate_raw(raw)
    levels = {f.field: f.level for f in findings}
    assert levels.get("window_s") == pv.WARN
    assert levels.get("npk_ok") == pv.WARN
    assert pv.worst_level(findings) == pv.WARN


def test_adc_out_of_range_fails() -> None:
    findings = pv.validate_raw({"soil_adc": 2000})
    assert any(f.field == "soil_adc" and f.level == pv.FAIL for f in findings)


def test_future_recorded_at_fails() -> None:
    now = datetime(2026, 10, 4, tzinfo=UTC)
    future = now + timedelta(hours=2)
    assert pv.validate_recorded_at(future, now)[0].level == pv.FAIL
    assert pv.validate_recorded_at(now - timedelta(minutes=1), now) == []
    assert pv.validate_recorded_at(None, now) == []
