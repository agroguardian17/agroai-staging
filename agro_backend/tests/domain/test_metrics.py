"""Pure tests for app.domain.metrics."""


from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.metrics import (
    BATTERY_LOW_V,
    DEFAULT_TARGET_MOISTURE_PCT,
    DRY_RUN_FLOW_LPM_MAX,
    DRY_RUN_PUMP_CURRENT_A_MAX,
    FROST_SOIL_TEMP_C,
    BatteryState,
    DerivedMetrics,
    MetricsContext,
    battery_state_from,
    compute,
    is_dry_run_signature,
    is_frost_risk,
    moisture_deficit,
    sensor_health_warn_from,
)
from app.domain.sensor import Reading, TransmissionType

NOW = datetime(2026, 6, 20, 12, 0, tzinfo=UTC)
TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")




def _reading(**over: object) -> Reading:
    base: dict[str, object] = {
        "tenant_id": TENANT,
        "farmer_id": uuid.uuid4(),
        "farm_id": uuid.uuid4(),
        "plot_id": "P1",
        "node_id": "N1",
        "recorded_at": NOW,
        "received_at_master": NOW,
        "transmission_type": TransmissionType.LORA,
    }
    base.update(over)
    return Reading(**base)  # type: ignore[arg-type]




# ===========================================================================
# moisture_deficit
# ===========================================================================
def test_moisture_deficit_positive_when_below_target() -> None:
    assert moisture_deficit(Decimal("20"), Decimal("28")) == Decimal("8")




def test_moisture_deficit_negative_when_above_target() -> None:
    assert moisture_deficit(Decimal("35"), Decimal("28")) == Decimal("-7")




def test_moisture_deficit_none_when_actual_missing() -> None:
    assert moisture_deficit(None, Decimal("28")) is None





# ===========================================================================
# battery_state_from
# ===========================================================================
@pytest.mark.parametrize(
    ("v", "expected"),
    [
        (Decimal("3.50"), BatteryState.HEALTHY),
        (Decimal("3.40"), BatteryState.HEALTHY),  # at the healthy floor
        (Decimal("3.35"), BatteryState.LOW),  # between LOW and HEALTHY
        (Decimal("3.20"), BatteryState.LOW),  # at LOW
        (Decimal("3.10"), BatteryState.CRITICAL),  # at CRITICAL
        (Decimal("2.95"), BatteryState.CRITICAL),  # in CRITICAL range
        (Decimal("2.90"), BatteryState.DEAD),  # at DEAD
        (Decimal("2.50"), BatteryState.DEAD),  # below DEAD
    ],
)
def test_battery_state_voltage_buckets(v: Decimal, expected: BatteryState) -> None:
    assert battery_state_from(v, None) is expected




def test_battery_state_unknown_when_no_telemetry() -> None:
    assert battery_state_from(None, None) is BatteryState.UNKNOWN




def test_battery_state_picks_worst_across_voltage_and_percent() -> None:
    # Voltage says HEALTHY (3.50), but percent says CRITICAL (5%).
    # We should bucket as CRITICAL.
    assert battery_state_from(Decimal("3.50"), Decimal("5")) is BatteryState.CRITICAL




def test_battery_low_voltage_floor_matches_published_constant() -> None:
    # Round 3 published LOW_BATTERY_THRESHOLD_V = 3.30. Keep them in sync.
    assert Decimal("3.30") == BATTERY_LOW_V




# ===========================================================================
# is_frost_risk
# ===========================================================================
def test_frost_risk_true_at_threshold() -> None:
    assert is_frost_risk(FROST_SOIL_TEMP_C) is True




def test_frost_risk_false_above_threshold() -> None:
    assert is_frost_risk(Decimal("10.0")) is False




def test_frost_risk_false_when_temp_missing() -> None:
    assert is_frost_risk(None) is False




# ===========================================================================
# is_dry_run_signature
# ===========================================================================
def test_dry_run_when_pump_running_and_no_current_no_flow() -> None:
    assert (
        is_dry_run_signature(
            pump_running=True,
            pump_current_amps=DRY_RUN_PUMP_CURRENT_A_MAX,
            water_flow_lpm=DRY_RUN_FLOW_LPM_MAX,
        )
        is True
    )




def test_dry_run_false_when_pump_off() -> None:
    assert (
        is_dry_run_signature(
            pump_running=False,
            pump_current_amps=Decimal("0"),
            water_flow_lpm=Decimal("0"),
        )
        is False
    )




def test_dry_run_false_when_current_or_flow_unknown() -> None:
    assert (
        is_dry_run_signature(pump_running=True, pump_current_amps=None, water_flow_lpm=Decimal("0"))
        is False
    )
    assert (
        is_dry_run_signature(pump_running=True, pump_current_amps=Decimal("0"), water_flow_lpm=None)
        is False
    )




def test_dry_run_false_when_pump_drawing_normal_current() -> None:
    # Healthy pump draws several amps; flow is incidental.
    assert (
        is_dry_run_signature(
            pump_running=True,
            pump_current_amps=Decimal("3.5"),
            water_flow_lpm=Decimal("0"),
        )
        is False
    )




# ===========================================================================
# sensor_health_warn_from
# ===========================================================================
def test_sensor_health_warn_true_when_validation_warn() -> None:
    r = _reading(validation_warn=True)
    assert sensor_health_warn_from(r) is True




def test_sensor_health_warn_true_when_fault_flags_set() -> None:
    # fault_flags is a comma-separated freeform string per the PDF schema;
    # any non-empty value is a warning.
    r = _reading(fault_flags="range_fail")
    assert sensor_health_warn_from(r) is True




def test_sensor_health_warn_false_when_clean_reading() -> None:
    assert sensor_health_warn_from(_reading()) is False




# ===========================================================================
# compute - end-to-end orchestrator
# ===========================================================================
def test_compute_returns_clean_metrics_for_healthy_reading() -> None:
    r = _reading(
        soil_moisture_avg_pct=Decimal("32"),
        battery_voltage_v=Decimal("3.55"),
        soil_temp_rootzone_c=Decimal("25"),
    )
    m = compute(r)
    assert isinstance(m, DerivedMetrics)
    # Moisture above target (32 > 28) -> deficit negative.
    assert m.moisture_deficit_pct == Decimal("-4")
    assert m.moisture_below_target is False
    assert m.battery_state is BatteryState.HEALTHY
    assert m.frost_risk is False
    assert m.dry_run_signature is False
    assert m.sensor_health_warn is False




def test_compute_uses_custom_context_target() -> None:
    r = _reading(soil_moisture_avg_pct=Decimal("30"))
    m = compute(r, MetricsContext(target_moisture_pct=Decimal("35")))
    assert m.moisture_deficit_pct == Decimal("5")
    assert m.moisture_below_target is True




def test_compute_target_default_matches_constant() -> None:
    r = _reading(soil_moisture_avg_pct=Decimal("20"))
    m = compute(r)
    # 28 (default) - 20 = 8
    assert m.moisture_deficit_pct == Decimal("8")
    assert Decimal("28.0") == DEFAULT_TARGET_MOISTURE_PCT




def test_compute_aggregates_all_warning_signals() -> None:
    r = _reading(
        soil_moisture_avg_pct=Decimal("15"),  # below target
        battery_voltage_v=Decimal("3.05"),  # critical
        soil_temp_rootzone_c=Decimal("2.0"),  # frost
        pump_running=True,
        pump_current_amps=Decimal("0.2"),
        water_flow_lpm=Decimal("0.0"),
        validation_warn=True,
    )
    m = compute(r)
    assert m.moisture_below_target is True
    assert m.battery_state is BatteryState.CRITICAL
    assert m.frost_risk is True
    assert m.dry_run_signature is True
    assert m.sensor_health_warn is True
