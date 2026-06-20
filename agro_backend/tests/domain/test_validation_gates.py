"""Tests for ``app.domain.validation_gates``.


All four gates here are PURE (or pure modulo a pre-fetched window). The
tests assert behaviour without any DB, MQTT, or pydantic dependency.
"""


from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.sensor import LOW_BATTERY_THRESHOLD_V, Reading, TransmissionType
from app.domain.validation_gates import (
    MAD_K,
    MAD_MIN_WINDOW,
    MOISTURE_DISAGREE_PCT,
    RANGES,
    STUCK_MIN_IDENTICAL,
    GateResult,
    ValidationFlag,
    check_cross_sensor,
    check_range,
    is_mad_outlier,
    is_stuck,
)


def _r(**over: object) -> Reading:
    """Minimal Reading factory; same shape as test_sensor's _minimal_reading."""
    base: dict[str, object] = {
        "tenant_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "farmer_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "farm_id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "plot_id": "P1",
        "node_id": "N1",
        "recorded_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        "received_at_master": datetime(2026, 5, 1, 12, 0, 5, tzinfo=UTC),
        "transmission_type": TransmissionType.LORA,
    }
    base.update(over)
    return Reading(**base)  # type: ignore[arg-type]




# ===========================================================================
# Gate 1 - check_range
# ===========================================================================
def test_check_range_passes_for_in_bounds() -> None:
    assert check_range("soil_moisture_1_pct", Decimal("32.5")) is None
    assert check_range("soil_ph", Decimal("6.8")) is None
    assert check_range("battery_voltage_v", Decimal("3.45")) is None




def test_check_range_fires_for_below_min() -> None:
    res = check_range("soil_moisture_1_pct", Decimal("-5"))
    assert isinstance(res, GateResult)
    assert res.flag is ValidationFlag.RANGE_FAIL
    assert res.field == "soil_moisture_1_pct"
    assert "-5" in res.detail




def test_check_range_fires_for_above_max() -> None:
    res = check_range("soil_ph", Decimal("15"))
    assert res is not None
    assert res.flag is ValidationFlag.RANGE_FAIL




def test_check_range_fires_for_above_max_npk() -> None:
    res = check_range("soil_n_mg_kg", Decimal("5000"))
    assert res is not None
    assert res.flag is ValidationFlag.RANGE_FAIL




def test_check_range_none_value_is_pass() -> None:
    assert check_range("soil_moisture_1_pct", None) is None




def test_check_range_unknown_field_returns_none() -> None:
    # Don't blow up on a field name we don't have a bound for - that's
    # the orchestrator's concern (it iterates over RANGES.keys() anyway).
    assert check_range("some_brand_new_field", Decimal("999")) is None




def test_ranges_dict_contains_expected_fields() -> None:
    # Schema contract: any field a user asks check_range about that's in
    # RANGES is a documented domain field. Guards against accidental
    # deletions of bounds during refactors.
    must_have = {
        "soil_moisture_1_pct",
        "soil_moisture_2_pct",
        "soil_moisture_avg_pct",
        "soil_temp_c",
        "soil_temp_rootzone_c",
        "soil_ph",
        "soil_ec_ms_cm",
        "soil_n_mg_kg",
        "soil_p_mg_kg",
        "soil_k_mg_kg",
        "battery_voltage_v",
    }
    assert must_have.issubset(RANGES.keys())




# ===========================================================================
# Gate 2 - is_stuck
# ===========================================================================
def test_is_stuck_returns_false_for_empty_history() -> None:
    assert is_stuck([], Decimal("30")) is False




def test_is_stuck_returns_false_when_latest_is_none() -> None:
    # If we don't even have a latest value, "stuck" is undefined.
    assert is_stuck([Decimal("30")] * 5, None) is False




def test_is_stuck_fires_when_min_identical_threshold_met() -> None:
    same = Decimal("31.5")
    history = [same, same, same]  # 3 + latest = 4 -> meets STUCK_MIN_IDENTICAL
    assert STUCK_MIN_IDENTICAL == 4, "test assumes STUCK_MIN_IDENTICAL=4"
    assert is_stuck(history, same) is True




def test_is_stuck_passes_when_one_differs() -> None:
    same = Decimal("31.5")
    # 2 same in history + latest=same -> 3 total. Below threshold of 4.
    less_history = [same, Decimal("32"), same]
    assert is_stuck(less_history, same) is False




def test_is_stuck_skips_none_in_history() -> None:
    same = Decimal("31.5")
    # 3 non-null same + 1 None + latest=same -> 4 same total, threshold met.
    history = [same, None, same, same]
    assert is_stuck(history, same) is True




def test_is_stuck_returns_false_when_insufficient_non_null_samples() -> None:
    # Only 2 historical + 1 latest = 3 non-null. Below threshold of 4.
    assert is_stuck([Decimal("30"), Decimal("30")], Decimal("30")) is False




# ===========================================================================
# Gate 3 - is_mad_outlier
# ===========================================================================
def _norm_window(n: int, center: Decimal = Decimal("30")) -> list[Decimal]:
    """Build a synthetic window of small jitter around ``center``."""
    deltas = [Decimal(i) / Decimal("10") for i in range(-n // 2, n // 2 + 1)]
    return [center + d for d in deltas[:n]]




def test_is_mad_outlier_returns_false_for_small_window() -> None:
    # Below MAD_MIN_WINDOW samples -> always returns False (insufficient).
    window = [Decimal("30")] * (MAD_MIN_WINDOW - 1)
    assert is_mad_outlier(window, Decimal("999")) is False




def test_is_mad_outlier_detects_clear_outlier() -> None:
    window = _norm_window(20, center=Decimal("30"))
    # 30 + huge delta should be flagged.
    assert is_mad_outlier(window, Decimal("200")) is True




def test_is_mad_outlier_passes_for_normal_value() -> None:
    window = _norm_window(20, center=Decimal("30"))
    assert is_mad_outlier(window, Decimal("30.5")) is False




def test_is_mad_outlier_equal_to_median_passes() -> None:
    window = _norm_window(20, center=Decimal("30"))
    median = window[len(window) // 2]
    assert is_mad_outlier(window, median) is False




def test_is_mad_outlier_degenerate_window_all_identical() -> None:
    # MAD=0; any different value is an outlier; identical value is not.
    window = [Decimal("30")] * 20
    assert is_mad_outlier(window, Decimal("30")) is False
    assert is_mad_outlier(window, Decimal("31")) is True




def test_is_mad_outlier_respects_custom_k() -> None:
    window = _norm_window(20, center=Decimal("30"))
    # With a very loose k, even a far value passes.
    assert is_mad_outlier(window, Decimal("100"), k=Decimal("999")) is False




def test_mad_k_default_is_decimal() -> None:
    # The default must be Decimal, not float, to avoid mixing types under
    # the comparison ``abs(...) > k * mad``.
    assert isinstance(MAD_K, Decimal)




# ===========================================================================
# Gate 4 - check_cross_sensor
# ===========================================================================
def test_cross_sensor_passes_when_moisture_probes_agree() -> None:
    r = _r(
        soil_moisture_1_pct=Decimal("30.0"),
        soil_moisture_2_pct=Decimal("31.0"),
    )
    assert check_cross_sensor(r) == []




def test_cross_sensor_fires_when_moisture_probes_disagree() -> None:
    r = _r(
        soil_moisture_1_pct=Decimal("20"),
        soil_moisture_2_pct=Decimal("50"),
    )
    results = check_cross_sensor(r)
    assert any(
        x.flag is ValidationFlag.CROSS_SENSOR and x.field == "soil_moisture_avg_pct"
        for x in results
    )




def test_cross_sensor_threshold_value() -> None:
    # The exact threshold is documented; test guards a refactor breaking it.
    assert Decimal("15") == MOISTURE_DISAGREE_PCT




def test_cross_sensor_skips_when_one_moisture_missing() -> None:
    # Half-data is not "disagreement" - the gate has nothing to compare.
    r = _r(soil_moisture_1_pct=Decimal("20"), soil_moisture_2_pct=None)
    moisture_flags = [x for x in check_cross_sensor(r) if x.field == "soil_moisture_avg_pct"]
    assert moisture_flags == []




def test_cross_sensor_fires_when_low_voltage_but_no_firmware_flag() -> None:
    # Firmware should have set low_battery_flag. If it didn't, that's a
    # cross-sensor inconsistency we report.
    bv = LOW_BATTERY_THRESHOLD_V - Decimal("0.5")
    r = _r(battery_voltage_v=bv, low_battery_flag=False)
    results = check_cross_sensor(r)
    assert any(x.field == "low_battery_flag" for x in results)




def test_cross_sensor_does_not_fire_when_low_voltage_and_firmware_flag_set() -> None:
    bv = LOW_BATTERY_THRESHOLD_V - Decimal("0.5")
    r = _r(battery_voltage_v=bv, low_battery_flag=True)
    results = check_cross_sensor(r)
    assert not any(x.field == "low_battery_flag" for x in results)




def test_cross_sensor_partial_npk_frame() -> None:
    # Two of N/P/K present -> probe partial failure.
    r = _r(
        soil_n_mg_kg=Decimal("100"),
        soil_p_mg_kg=Decimal("50"),
        soil_k_mg_kg=None,
    )
    results = check_cross_sensor(r)
    assert any(x.field == "npk_sensor_raw_hex" for x in results)




def test_cross_sensor_npk_present_but_ec_missing() -> None:
    # Full NPK should always come with EC from the JXBS probe.
    r = _r(
        soil_n_mg_kg=Decimal("100"),
        soil_p_mg_kg=Decimal("50"),
        soil_k_mg_kg=Decimal("80"),
        soil_ec_ms_cm=None,
    )
    results = check_cross_sensor(r)
    assert any(x.field == "soil_ec_ms_cm" for x in results)




def test_cross_sensor_full_consistent_npk_passes() -> None:
    r = _r(
        soil_n_mg_kg=Decimal("100"),
        soil_p_mg_kg=Decimal("50"),
        soil_k_mg_kg=Decimal("80"),
        soil_ec_ms_cm=Decimal("0.45"),
    )
    npk_flags = [x for x in check_cross_sensor(r) if "npk" in x.field or "ec" in x.field]
    assert npk_flags == []
