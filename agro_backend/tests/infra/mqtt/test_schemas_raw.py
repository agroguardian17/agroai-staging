"""Round 16 — TelemetryInRaw round-trip tests.

Cover:

* ``$schema`` dispatch in ``parse_inbound`` (v2, v2-raw, unknown).
* Full raw payload → ``to_domain(calibration)`` → ``Reading`` invariants.
* NPK-fail short-circuit: when ``npk_ok=false`` the NPK-derived fields
  land as ``None`` on the Reading.
* Unknown fields are rejected (``extra="forbid"``).
* Naive timestamps are rejected.
"""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.device_calibration import DeviceCalibration
from app.infra.mqtt.schemas import (
    SCHEMA_TELEMETRY_V2,
    SCHEMA_TELEMETRY_V2_RAW,
    TelemetryIn,
    TelemetryInRaw,
    parse_inbound,
)

PILOT_TOPIC = (
    "agro/v2/11111111-1111-1111-1111-111111111111"
    "/bbbbbbbb-2222-2222-2222-222222222222"
    "/AGR-SN-0001/telemetry"
)


def _cal() -> DeviceCalibration:
    return DeviceCalibration(
        tenant_id="11111111-1111-1111-1111-111111111111",
        device_id="AGR-SN-0001",
        soil_dry_adc=750,
        soil_wet_adc=350,
        battery_vref_v=Decimal("3.300"),
        battery_divider_ratio=Decimal("3.200"),
        pressure_offset_v=Decimal("0.500"),
        pressure_scale_bar_per_v=Decimal("2.500"),
        flow_pulses_per_litre=Decimal("450.000"),
        flow_window_seconds=Decimal("16.00"),
        npk_temp_divisor=Decimal("10.000"),
        npk_moisture_divisor=Decimal("10.000"),
        npk_ph_divisor=Decimal("100.000"),
        calibration_version=1,
    )


def _raw_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "$schema": SCHEMA_TELEMETRY_V2_RAW,
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "farmer_id": "aaaaaaaa-1111-1111-1111-111111111111",
        "farm_id":   "bbbbbbbb-2222-2222-2222-222222222222",
        "plot_id":   "PLOT_PILOT_001",
        "node_id":   "AGR-SN-0001",
        "seq": 42,
        "recorded_at":        "2026-08-26T10:45:00+00:00",
        "received_at_master": "2026-08-26T10:45:03+00:00",
        "transmission_type":  "lora",
        "raw_readings": {
            "soil_adc": 550,       # midpoint between dry=750, wet=350 → 50%
            "battery_adc": 780,
            "pressure_adc": 340,
            "flow_pulses_window": 12,
            "flow_pulses_total": 145,
            "ds18b20_temp_c": 27.5,
            "npk_ok": True,
            "npk_temp_raw": 291,
            "npk_moisture_raw": 357,
            "npk_ec_us_cm": 1045,
            "npk_ph_raw": 645,
            "npk_nitrogen_mg_kg": 58,
            "npk_phosphorus_mg_kg": 79,
            "npk_potassium_mg_kg": 197,
            "sub_node_fw": "viraai-sn-1.0.0-raw",
        },
        "master_readings": {
            "bme280_temp_c": 32.4,
            "bme280_humidity_pct": 65.1,
            "bme280_pressure_pa": 95000.0,
            "ina219_bus_v": 12.1,
            "ina219_current_ma": 250.0,
            "rain_pulses_window": 3,
            "wind_pulses_window": 12,
            "wind_dir_adc": 976,
            "lora_rssi_dbm": -71,
            "lora_snr_db": 8.5,
        },
        "firmware_version": "viraai-mn-1.0.0-raw",
        "main_node_id": "AGR-MN-0001",
    }
    payload.update(overrides)
    return payload


# ---------- parse_inbound dispatch ----------

def test_parse_inbound_routes_raw_schema_to_telemetry_in_raw() -> None:
    payload = _raw_payload()
    model = parse_inbound(PILOT_TOPIC, json.dumps(payload).encode())
    assert isinstance(model, TelemetryInRaw)
    assert model.node_id == "AGR-SN-0001"
    assert model.raw_readings.npk_ok is True


def test_parse_inbound_routes_v2_schema_to_telemetry_in() -> None:
    payload = {
        "$schema": SCHEMA_TELEMETRY_V2,
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "farmer_id": "aaaaaaaa-1111-1111-1111-111111111111",
        "farm_id":   "bbbbbbbb-2222-2222-2222-222222222222",
        "plot_id":   "PLOT_PILOT_001",
        "node_id":   "AGR-SN-0001",
        "recorded_at":        "2026-08-26T10:45:00+00:00",
        "received_at_master": "2026-08-26T10:45:03+00:00",
        "transmission_type":  "lora",
    }
    model = parse_inbound(PILOT_TOPIC, json.dumps(payload).encode())
    assert isinstance(model, TelemetryIn)


def test_parse_inbound_unknown_schema_raises_value_error() -> None:
    payload = _raw_payload(**{"$schema": "agro-guardian/telemetry/v99"})
    with pytest.raises(ValueError, match="unknown \\$schema"):
        parse_inbound(PILOT_TOPIC, json.dumps(payload).encode())


def test_parse_inbound_non_object_payload_raises_value_error() -> None:
    with pytest.raises(ValueError, match="must be a JSON object"):
        parse_inbound(PILOT_TOPIC, b"[1,2,3]")


# ---------- to_domain calibration ----------

def test_to_domain_applies_soil_moisture_calibration() -> None:
    model = TelemetryInRaw.model_validate(_raw_payload())
    reading = model.to_domain(_cal())
    # ADC=550 with DRY=750 WET=350 → midpoint → 50%
    assert reading.soil_moisture_avg_pct == Decimal("50")
    assert reading.soil_moisture_1_pct == Decimal("50")


def test_to_domain_carries_calibration_version_in_sensor_health() -> None:
    model = TelemetryInRaw.model_validate(_raw_payload())
    reading = model.to_domain(_cal())
    assert reading.sensor_health_json["calibration_version"] == 1
    assert reading.sensor_health_json["main_node_id"] == "AGR-MN-0001"
    assert reading.sensor_health_json["npk_ok"] is True
    assert reading.sensor_health_json["seq"] == 42
    assert "master_readings" in reading.sensor_health_json


def test_to_domain_populates_battery_from_adc() -> None:
    model = TelemetryInRaw.model_validate(_raw_payload())
    reading = model.to_domain(_cal())
    # 780 * 3.3/1023 * 3.2 ≈ 8.052 V
    assert reading.battery_voltage_v is not None
    assert Decimal("8.0") < reading.battery_voltage_v < Decimal("8.1")


def test_to_domain_populates_pressure_from_adc() -> None:
    model = TelemetryInRaw.model_validate(_raw_payload())
    reading = model.to_domain(_cal())
    # ADC=340 → V_pin ≈ 1.097 → bar ≈ 1.49
    assert reading.water_pressure_bar is not None
    assert Decimal("1.4") < reading.water_pressure_bar < Decimal("1.6")


def test_to_domain_populates_flow_from_pulses() -> None:
    model = TelemetryInRaw.model_validate(_raw_payload())
    reading = model.to_domain(_cal())
    # 12 pulses / 16 s / 450 pulses/L → ~0.1 L/min
    assert reading.water_flow_lpm is not None
    assert Decimal("0.09") < reading.water_flow_lpm < Decimal("0.11")


def test_to_domain_populates_npk_fields_when_npk_ok_true() -> None:
    model = TelemetryInRaw.model_validate(_raw_payload())
    reading = model.to_domain(_cal())
    assert reading.soil_ph == Decimal("6.45")
    assert reading.soil_ec_ms_cm == Decimal("1.045")
    assert reading.soil_n_mg_kg == Decimal("58")
    assert reading.soil_p_mg_kg == Decimal("79")
    assert reading.soil_k_mg_kg == Decimal("197")
    assert reading.soil_temp_rootzone_c == Decimal("29.1")
    assert reading.soil_moisture_2_pct == Decimal("35.7")


def test_to_domain_nulls_npk_fields_when_npk_ok_false() -> None:
    payload = copy.deepcopy(_raw_payload())
    payload["raw_readings"]["npk_ok"] = False
    model = TelemetryInRaw.model_validate(payload)
    reading = model.to_domain(_cal())
    assert reading.soil_ph is None
    assert reading.soil_ec_ms_cm is None
    assert reading.soil_n_mg_kg is None
    assert reading.soil_p_mg_kg is None
    assert reading.soil_k_mg_kg is None
    assert reading.soil_temp_rootzone_c is None
    assert reading.soil_moisture_2_pct is None
    # DS18B20 temp still lands (independent of NPK)
    assert reading.soil_temp_c == Decimal("27.5")


def test_to_domain_ds18b20_passthrough() -> None:
    model = TelemetryInRaw.model_validate(_raw_payload())
    reading = model.to_domain(_cal())
    assert reading.soil_temp_c == Decimal("27.5")


def test_to_domain_rssi_from_master_readings() -> None:
    model = TelemetryInRaw.model_validate(_raw_payload())
    reading = model.to_domain(_cal())
    assert reading.signal_rssi_dbm == -71


def test_to_domain_firmware_version_prefers_sub_node_string() -> None:
    model = TelemetryInRaw.model_validate(_raw_payload())
    reading = model.to_domain(_cal())
    assert reading.firmware_version == "viraai-sn-1.0.0-raw"


# ---------- Validation guards ----------

def test_unknown_field_at_top_level_rejected() -> None:
    payload = _raw_payload(evil="hax")
    with pytest.raises(ValidationError):
        TelemetryInRaw.model_validate(payload)


def test_unknown_field_in_raw_readings_rejected() -> None:
    payload = copy.deepcopy(_raw_payload())
    payload["raw_readings"]["evil"] = "hax"
    with pytest.raises(ValidationError):
        TelemetryInRaw.model_validate(payload)


def test_unknown_field_in_master_readings_rejected() -> None:
    payload = copy.deepcopy(_raw_payload())
    payload["master_readings"]["evil"] = "hax"
    with pytest.raises(ValidationError):
        TelemetryInRaw.model_validate(payload)


def test_naive_timestamp_rejected() -> None:
    payload = _raw_payload(recorded_at="2026-08-26T10:45:00")
    with pytest.raises(ValidationError):
        TelemetryInRaw.model_validate(payload)


def test_soil_adc_out_of_range_rejected() -> None:
    payload = copy.deepcopy(_raw_payload())
    payload["raw_readings"]["soil_adc"] = 1500
    with pytest.raises(ValidationError):
        TelemetryInRaw.model_validate(payload)


def test_wrong_schema_id_rejected_by_model() -> None:
    payload = _raw_payload(**{"$schema": SCHEMA_TELEMETRY_V2})
    with pytest.raises(ValidationError):
        TelemetryInRaw.model_validate(payload)
