"""Tests for the pipeline self-test harness (golden calibration fixtures)."""

from __future__ import annotations

from decimal import Decimal

from app.infra.pipeline_selftest import _calibration, _raw, make_model, run_self_test

_EPS = Decimal("0.001")


def test_self_test_all_golden_cases_pass() -> None:
    report = run_self_test()
    assert report.passed, [(c.name, c.overall, c.expected) for c in report.cases if not c.passed]
    assert len(report.cases) == 4


def test_calibration_math_lock() -> None:
    """Lock the raw→calibrated math against regressions by re-deriving the
    documented formulas independently (not by snapshotting to_domain's output)."""
    cal = _calibration()
    reading = make_model(_raw()).to_domain(cal)

    # battery_voltage = adc * vref / 1023 * divider
    expected_batt = Decimal(620) * Decimal("3.3") / Decimal(1023) * Decimal("2.0")
    assert reading.battery_voltage_v is not None
    assert abs(reading.battery_voltage_v - expected_batt) < _EPS

    # flow L/min = pulses * 60 / (window_s * pulses_per_litre), window override 300
    expected_flow = Decimal(100) * Decimal(60) / (Decimal(300) * Decimal(450))
    assert reading.water_flow_lpm is not None
    assert abs(reading.water_flow_lpm - expected_flow) < _EPS


def test_window_zero_nulls_flow() -> None:
    cal = _calibration()
    reading = make_model(_raw(window_s=0)).to_domain(cal)
    assert reading.water_flow_lpm is None
