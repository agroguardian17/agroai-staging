"""Tests for ``app.infra.mqtt.schemas``: TelemetryIn + parse_inbound.


Covers:


* Happy-path JSON round-trip (parse -> TelemetryIn -> to_domain -> Reading).
* Field-by-field validation (missing required, wrong type, out-of-bound).
* Decimal precision preservation (float on the wire never reaches domain).
* Naive datetime rejection.
* parse_inbound topic dispatch + the two error paths.
"""


from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.sensor import CadenceMode, Reading, TransmissionType
from app.infra.mqtt.schemas import (
    SCHEMA_TELEMETRY_V2,
    TelemetryIn,
    TopicParseError,
    UnknownTopicKindError,
    parse_inbound,
)

_FULL_PAYLOAD: dict[str, object] = {
    "$schema": SCHEMA_TELEMETRY_V2,
    "tenant_id": "11111111-1111-1111-1111-111111111111",
    "farmer_id": "22222222-2222-2222-2222-222222222222",
    "farm_id": "33333333-3333-3333-3333-333333333333",
    "plot_id": "PLOT_AUR_001_Z1",
    "node_id": "AGR-MH-0001",
    "recorded_at": "2026-05-01T12:00:00+00:00",
    "received_at_master": "2026-05-01T12:00:05+00:00",
    "transmission_type": "lora",
    "signal_rssi_dbm": -72,
    "battery_voltage_v": 3.45,
    "battery_percent": 78.5,
    "soil_moisture_1_pct": 32.5,
    "soil_moisture_2_pct": 33.1,
    "soil_moisture_avg_pct": 32.8,
    "soil_temp_rootzone_c": 24.3,
    "soil_ph": 6.7,
    "soil_n_mg_kg": 142,
    "cadence_mode": "normal",
}


_TOPIC = "agro/v2/pilot/FARM_001/AGR-MH-0001/telemetry"




def _payload(**over: object) -> dict[str, object]:
    p = dict(_FULL_PAYLOAD)
    p.update(over)
    return p




# ===========================================================================
# Parsing - happy path
# ===========================================================================
def test_telemetry_parses_full_payload() -> None:
    m = TelemetryIn.model_validate(_FULL_PAYLOAD)
    assert m.tenant_id == uuid.UUID("11111111-1111-1111-1111-111111111111")
    assert m.plot_id == "PLOT_AUR_001_Z1"
    assert m.transmission_type is TransmissionType.LORA
    assert m.cadence_mode is CadenceMode.NORMAL




def test_telemetry_parses_with_only_required_fields() -> None:
    minimal = {
        "$schema": SCHEMA_TELEMETRY_V2,
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "farmer_id": "22222222-2222-2222-2222-222222222222",
        "farm_id": "33333333-3333-3333-3333-333333333333",
        "plot_id": "P",
        "node_id": "N",
        "recorded_at": "2026-05-01T12:00:00Z",
        "received_at_master": "2026-05-01T12:00:05Z",
        "transmission_type": "lora",
    }
    m = TelemetryIn.model_validate(minimal)
    assert m.battery_voltage_v is None
    assert m.soil_moisture_1_pct is None
    assert m.low_battery_flag is False  # default
    assert m.sensor_health_json == {}




# ===========================================================================
# Decimal precision preservation
# ===========================================================================
def test_floats_on_wire_become_decimals_via_string() -> None:
    # 7.2 as a binary float is 7.20000000...; we MUST get exactly Decimal("7.2").
    m = TelemetryIn.model_validate(_payload(battery_voltage_v=7.2))
    assert m.battery_voltage_v == Decimal("7.2")
    assert isinstance(m.battery_voltage_v, Decimal)




def test_ints_become_decimals_too() -> None:
    m = TelemetryIn.model_validate(_payload(soil_n_mg_kg=142))
    assert m.soil_n_mg_kg == Decimal("142")
    assert isinstance(m.soil_n_mg_kg, Decimal)




def test_decimal_string_preserved() -> None:
    m = TelemetryIn.model_validate(_payload(soil_ph="6.85"))
    assert m.soil_ph == Decimal("6.85")




def test_boolean_rejected_for_decimal_field() -> None:
    with pytest.raises(ValidationError):
        # True is an int subclass; without the explicit reject our
        # BeforeValidator would convert it to Decimal(1).
        TelemetryIn.model_validate(_payload(soil_ph=True))




# ===========================================================================
# Schema discriminator
# ===========================================================================
def test_wrong_schema_value_rejected() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn.model_validate(_payload(**{"$schema": "agro-guardian/telemetry/v1"}))




def test_missing_schema_field_rejected() -> None:
    p = dict(_FULL_PAYLOAD)
    del p["$schema"]
    with pytest.raises(ValidationError):
        TelemetryIn.model_validate(p)




# ===========================================================================
# Datetime handling
# ===========================================================================
def test_naive_recorded_at_rejected() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn.model_validate(_payload(recorded_at="2026-05-01T12:00:00"))




def test_aware_datetime_normalised_to_utc() -> None:
    m = TelemetryIn.model_validate(_payload(recorded_at="2026-05-01T17:30:00+05:30"))
    assert m.recorded_at.tzinfo == UTC
    assert m.recorded_at == datetime(2026, 5, 1, 12, 0, tzinfo=UTC)




def test_zulu_suffix_accepted() -> None:
    m = TelemetryIn.model_validate(_payload(recorded_at="2026-05-01T12:00:00Z"))
    assert m.recorded_at.tzinfo is not None




# ===========================================================================
# Bounds + enums
# ===========================================================================
def test_signal_rssi_out_of_range() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn.model_validate(_payload(signal_rssi_dbm=-200))




def test_npk_bucket_out_of_range() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn.model_validate(_payload(soil_n_bucket=99))  # bound 0..63




def test_uptime_negative_rejected() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn.model_validate(_payload(uptime_seconds=-1))





def test_invalid_transmission_type_rejected() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn.model_validate(_payload(transmission_type="bluetooth"))




def test_invalid_cadence_mode_rejected() -> None:
    with pytest.raises(ValidationError):
        TelemetryIn.model_validate(_payload(cadence_mode="turbo"))




def test_extra_field_rejected() -> None:
    # We use extra="forbid" - typo'd fields must fail loudly, not silently drop.
    with pytest.raises(ValidationError):
        TelemetryIn.model_validate(_payload(unknown_field=1))




# ===========================================================================
# Frozen model
# ===========================================================================
def test_model_is_frozen() -> None:
    m = TelemetryIn.model_validate(_FULL_PAYLOAD)
    with pytest.raises(ValidationError):
        m.plot_id = "tampered"  # type: ignore[misc]




# ===========================================================================
# to_domain() boundary
# ===========================================================================
def test_to_domain_returns_reading_with_matching_fields() -> None:
    m = TelemetryIn.model_validate(_FULL_PAYLOAD)
    r = m.to_domain()
    assert isinstance(r, Reading)
    assert r.tenant_id == m.tenant_id
    assert r.plot_id == m.plot_id
    assert r.node_id == m.node_id
    assert r.transmission_type is TransmissionType.LORA
    assert r.cadence_mode is CadenceMode.NORMAL
    assert r.soil_ph == Decimal("6.7")
    # Decimal fidelity end-to-end.
    assert r.battery_voltage_v == Decimal("3.45")




def test_to_domain_copies_sensor_health_json_defensively() -> None:
    # Mutating the result's sensor_health_json must not affect the source.
    m = TelemetryIn.model_validate(_payload(sensor_health_json={"npk": "ok"}))
    r = m.to_domain()
    # Domain layer's sensor_health_json is a dict (mutable inside a frozen
    # dataclass - we accept this; the dataclass-level frozen guarantee is
    # for *field rebinding*, not contained-mutable contents).
    r.sensor_health_json["npk"] = "tampered"
    assert m.sensor_health_json["npk"] == "ok"




def test_to_domain_aware_datetime_preserved() -> None:
    m = TelemetryIn.model_validate(_payload(recorded_at="2026-05-01T17:30:00+05:30"))
    r = m.to_domain()
    assert r.recorded_at.tzinfo is not None
    assert r.recorded_at.tzinfo.utcoffset(None) == UTC.utcoffset(None)




# ===========================================================================
# parse_inbound dispatcher
# ===========================================================================
def test_parse_inbound_telemetry_topic() -> None:
    raw = json.dumps(_FULL_PAYLOAD).encode()
    m = parse_inbound(_TOPIC, raw)
    assert isinstance(m, TelemetryIn)
    assert m.node_id == "AGR-MH-0001"




def test_parse_inbound_rejects_malformed_topic() -> None:
    raw = json.dumps(_FULL_PAYLOAD).encode()
    with pytest.raises(TopicParseError):
        parse_inbound("agro/pilot/farm/node/telemetry", raw)  # missing /v2/
    with pytest.raises(TopicParseError):
        parse_inbound("not-the-right-prefix", raw)
    with pytest.raises(TopicParseError):
        # Empty path segment.
        parse_inbound("agro/v2/pilot//AGR-MH-0001/telemetry", raw)




def test_parse_inbound_unknown_kind() -> None:
    raw = json.dumps(_FULL_PAYLOAD).encode()
    with pytest.raises(UnknownTopicKindError):
        parse_inbound("agro/v2/pilot/farm/node/weather", raw)




def test_parse_inbound_invalid_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_inbound(_TOPIC, b"not json")




def test_parse_inbound_invalid_payload() -> None:
    bad = dict(_FULL_PAYLOAD)
    bad["soil_ph"] = "not a number"
    with pytest.raises(ValidationError):
        parse_inbound(_TOPIC, json.dumps(bad).encode())




# ===========================================================================
# End-to-end smoke: wire JSON -> TelemetryIn -> Reading
# ===========================================================================
def test_full_pipeline_wire_to_domain() -> None:
    raw = json.dumps(_FULL_PAYLOAD).encode()
    inbound = parse_inbound(_TOPIC, raw)
    domain = inbound.to_domain()
    assert isinstance(domain, Reading)
    assert domain.cadence_mode is CadenceMode.NORMAL
    assert domain.soil_ph == Decimal("6.7")
    # Most importantly: float wire value preserved exactly as Decimal.
    assert domain.battery_voltage_v == Decimal("3.45")
    assert isinstance(domain.battery_voltage_v, Decimal)
