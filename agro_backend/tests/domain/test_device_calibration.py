"""Unit tests for the pure device_calibration domain module."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.device_calibration import (
    DeviceCalibration,
    calibrate_battery_v,
    calibrate_flow_lpm,
    calibrate_npk_moisture_pct,
    calibrate_npk_ph,
    calibrate_npk_temp_c,
    calibrate_pressure_bar,
    calibrate_soil_moisture_pct,
    npk_ec_ms_cm,
)


def _cal(**overrides: object) -> DeviceCalibration:
    """Default calibration matching migration 0012 seeds + firmware defaults."""
    base = {
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "device_id": "AGR-SN-0001",
        "soil_dry_adc": 750,
        "soil_wet_adc": 350,
        "battery_vref_v": Decimal("3.300"),
        "battery_divider_ratio": Decimal("3.200"),
        "pressure_offset_v": Decimal("0.500"),
        "pressure_scale_bar_per_v": Decimal("2.500"),
        "flow_pulses_per_litre": Decimal("450.000"),
        "flow_window_seconds": Decimal("16.00"),
        "npk_temp_divisor": Decimal("10.000"),
        "npk_moisture_divisor": Decimal("10.000"),
        "npk_ph_divisor": Decimal("100.000"),
        "calibration_version": 1,
    }
    base.update(overrides)
    return DeviceCalibration(**base)  # type: ignore[arg-type]


# ---------- Soil moisture ----------

def test_soil_moisture_at_dry_endpoint_is_zero_pct() -> None:
    cal = _cal()
    assert calibrate_soil_moisture_pct(750, cal) == Decimal("0")


def test_soil_moisture_at_wet_endpoint_is_hundred_pct() -> None:
    cal = _cal()
    assert calibrate_soil_moisture_pct(350, cal) == Decimal("100")


def test_soil_moisture_midpoint() -> None:
    cal = _cal()
    # halfway between wet=350 and dry=750 is adc=550 → 50%
    assert calibrate_soil_moisture_pct(550, cal) == Decimal("50")


def test_soil_moisture_below_wet_clamps_to_hundred() -> None:
    cal = _cal()
    assert calibrate_soil_moisture_pct(200, cal) == Decimal("100")


def test_soil_moisture_above_dry_clamps_to_zero() -> None:
    cal = _cal()
    assert calibrate_soil_moisture_pct(900, cal) == Decimal("0")


def test_soil_moisture_zero_span_returns_zero() -> None:
    # Uncalibrated row where DRY == WET must not divide by zero.
    cal = _cal(soil_dry_adc=500, soil_wet_adc=500)
    assert calibrate_soil_moisture_pct(500, cal) == Decimal("0")


# ---------- Battery ----------

def test_battery_voltage_pilot_default() -> None:
    cal = _cal()
    # ADC=780, VREF=3.3, ratio=3.2 → 780 * 3.3/1023 * 3.2 ≈ 8.052 V
    v = calibrate_battery_v(780, cal)
    assert v == Decimal("780") * Decimal("3.300") / Decimal("1023") * Decimal("3.200")
    assert v > Decimal("8.0") and v < Decimal("8.1")


def test_battery_voltage_zero_adc_is_zero() -> None:
    assert calibrate_battery_v(0, _cal()) == Decimal("0")


# ---------- Pressure ----------

def test_pressure_at_offset_is_zero() -> None:
    """When the transducer's DC output equals `offset_v`, bar = 0."""
    cal = _cal()
    # V_pin at offset (0.5V) → ADC = 0.5 * 1023 / 3.3 ≈ 155
    adc_at_offset = int(Decimal("0.500") * Decimal("1023") / Decimal("3.300"))
    assert calibrate_pressure_bar(adc_at_offset, cal) < Decimal("0.02")


def test_pressure_below_offset_clamps_to_zero() -> None:
    cal = _cal()
    assert calibrate_pressure_bar(0, cal) == Decimal("0")


def test_pressure_positive_reading() -> None:
    cal = _cal()
    # ADC=340 → V_pin ≈ 1.097 → bar = (1.097 - 0.5) * 2.5 ≈ 1.49
    bar = calibrate_pressure_bar(340, cal)
    assert bar > Decimal("1.4") and bar < Decimal("1.6")


# ---------- Flow ----------

def test_flow_lpm_zero_pulses_is_zero() -> None:
    assert calibrate_flow_lpm(0, _cal()) == Decimal("0")


def test_flow_lpm_default_window() -> None:
    cal = _cal()
    # 12 pulses in 16 s at 450 pulses/L → 12*60 / (16*450) = 0.1 L/min
    lpm = calibrate_flow_lpm(12, cal)
    assert lpm == Decimal("12") * Decimal("60") / (Decimal("16.00") * Decimal("450.000"))
    assert Decimal("0.09") < lpm < Decimal("0.11")


def test_flow_lpm_zero_pulses_per_litre_returns_zero() -> None:
    """Misconfigured calibration must not raise ZeroDivisionError."""
    cal = _cal(flow_pulses_per_litre=Decimal("0"))
    assert calibrate_flow_lpm(999, cal) == Decimal("0")


def test_flow_lpm_zero_window_returns_zero() -> None:
    cal = _cal(flow_window_seconds=Decimal("0"))
    assert calibrate_flow_lpm(999, cal) == Decimal("0")


def test_flow_lpm_window_override_positive_uses_override() -> None:
    """2026-08-27 v2 firmware: on-device measured window trumps calibration constant.

    Sub Node WDT-timed sleep drifts ±10-15% vs nominal, so the actual
    on-device window (from raw_readings.window_s) is the correct divisor
    for flow rate. Here: 12 pulses in 300 s at 450 pulses/L →
    12*60 / (300*450) = ~0.00533 L/min. Note this differs from the
    calibration row's flow_window_seconds=16.
    """
    cal = _cal()
    lpm = calibrate_flow_lpm(12, cal, Decimal("300"))
    expected = Decimal("12") * Decimal("60") / (Decimal("300") * Decimal("450.000"))
    assert lpm == expected


def test_flow_lpm_window_override_zero_returns_none() -> None:
    """window_seconds_override=0 signals "unknown window" — first cycle after boot.

    Backend then treats water_flow_lpm as no-data; flow_pulses_total delta
    between adjacent rows is the authoritative volume signal.
    """
    cal = _cal()
    assert calibrate_flow_lpm(12, cal, Decimal("0")) is None


def test_flow_lpm_window_override_none_falls_back_to_calibration_row() -> None:
    """No override -> use cal.flow_window_seconds (legacy behaviour)."""
    cal = _cal()
    lpm_default = calibrate_flow_lpm(12, cal)
    lpm_explicit_none = calibrate_flow_lpm(12, cal, None)
    assert lpm_default == lpm_explicit_none


# ---------- NPK ----------

def test_npk_temp_divides_by_ten() -> None:
    cal = _cal()
    # register 291 → 29.1 °C
    assert calibrate_npk_temp_c(291, cal) == Decimal("29.1")


def test_npk_moisture_divides_by_ten() -> None:
    cal = _cal()
    assert calibrate_npk_moisture_pct(357, cal) == Decimal("35.7")


def test_npk_ph_divides_by_hundred() -> None:
    cal = _cal()
    assert calibrate_npk_ph(645, cal) == Decimal("6.45")


def test_npk_ec_conversion() -> None:
    assert npk_ec_ms_cm(1045) == Decimal("1.045")


def test_npk_zero_divisor_returns_zero() -> None:
    cal = _cal(npk_temp_divisor=Decimal("0"))
    assert calibrate_npk_temp_c(999, cal) == Decimal("0")


# ---------- Purity ----------

def test_all_returns_are_decimal() -> None:
    """Ensure no float sneaks through the boundary."""
    cal = _cal()
    for value in (
        calibrate_soil_moisture_pct(500, cal),
        calibrate_battery_v(780, cal),
        calibrate_pressure_bar(340, cal),
        calibrate_flow_lpm(12, cal),
        calibrate_npk_temp_c(291, cal),
        calibrate_npk_moisture_pct(357, cal),
        calibrate_npk_ph(645, cal),
        npk_ec_ms_cm(1045),
    ):
        assert isinstance(value, Decimal), f"got {type(value).__name__}"


def test_calibration_dataclass_is_frozen() -> None:
    cal = _cal()
    with pytest.raises(Exception):  # noqa: B017 — FrozenInstanceError or similar
        cal.soil_dry_adc = 999  # type: ignore[misc]
