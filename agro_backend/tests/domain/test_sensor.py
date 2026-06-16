"""Tests for ``app.domain.sensor``.


Verifies that:


* Construction works with the minimal required identity + timing fields.
* The dataclass is frozen (mutation raises).
* ``with_`` returns a new instance without modifying the original.
* Enum values match the schema CHECK constraints exactly.
* ``is_satellite_only`` correctly detects sensor-data-free readings.


These tests have ZERO infra imports - importable from a venv with only
stdlib + pytest installed.
"""

from __future__ import annotations

import dataclasses
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.sensor import (
    LOW_BATTERY_THRESHOLD_V,
    CadenceMode,
    Reading,
    TransmissionType,
    ValveStatus,
)

# Constants used across multiple tests; defined once for clarity.
_T1 = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
_T2 = datetime(2026, 5, 1, 12, 0, 5, tzinfo=UTC)
_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_FARMER = uuid.UUID("22222222-2222-2222-2222-222222222222")
_FARM = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _minimal_reading(**overrides: object) -> Reading:
    """Build a Reading with only required fields, allowing per-test overrides."""
    base: dict[str, object] = {
        "tenant_id": _TENANT,
        "farmer_id": _FARMER,
        "farm_id": _FARM,
        "plot_id": "PLOT_AUR_001_Z1",
        "node_id": "AGR-MH-0001",
        "recorded_at": _T1,
        "received_at_master": _T2,
        "transmission_type": TransmissionType.LORA,
    }
    base.update(overrides)
    return Reading(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Construction + identity
# ---------------------------------------------------------------------------
def test_reading_constructs_with_minimal_fields() -> None:
    r = _minimal_reading()
    assert r.tenant_id == _TENANT
    assert r.plot_id == "PLOT_AUR_001_Z1"
    assert r.transmission_type is TransmissionType.LORA
    # All optional measurement fields default to None.
    assert r.soil_moisture_1_pct is None
    assert r.battery_voltage_v is None


def test_reading_construction_with_full_measurements() -> None:
    r = _minimal_reading(
        battery_voltage_v=Decimal("3.45"),
        soil_moisture_1_pct=Decimal("32.5"),
        soil_moisture_2_pct=Decimal("33.1"),
        soil_moisture_avg_pct=Decimal("32.8"),
        soil_temp_rootzone_c=Decimal("24.3"),
        soil_ph=Decimal("6.7"),
        soil_n_mg_kg=Decimal("142"),
        cadence_mode=CadenceMode.NORMAL,
    )
    assert r.battery_voltage_v == Decimal("3.45")
    assert r.cadence_mode is CadenceMode.NORMAL


def test_reading_default_flags() -> None:
    r = _minimal_reading()
    assert r.low_battery_flag is False
    assert r.backlog_pending is False
    assert r.validation_warn is False
    assert r.sensor_health_json == {}


# ---------------------------------------------------------------------------
# Immutability (frozen=True)
# ---------------------------------------------------------------------------
def test_reading_is_frozen() -> None:
    r = _minimal_reading()
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.plot_id = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ``with_`` evolution
# ---------------------------------------------------------------------------
def test_with_returns_new_instance_and_preserves_original() -> None:
    original = _minimal_reading(soil_moisture_1_pct=Decimal("30.0"))
    evolved = original.with_(soil_moisture_1_pct=Decimal("31.5"), validation_warn=True)
    assert original.soil_moisture_1_pct == Decimal("30.0")
    assert original.validation_warn is False
    assert evolved.soil_moisture_1_pct == Decimal("31.5")
    assert evolved.validation_warn is True
    # Identity preserved.
    assert evolved.tenant_id == original.tenant_id
    assert evolved.node_id == original.node_id


def test_with_returns_distinct_object() -> None:
    r = _minimal_reading()
    assert r.with_(plot_id="other") is not r


# ---------------------------------------------------------------------------
# Enum value parity with schema CHECK constraints
# ---------------------------------------------------------------------------
def test_cadence_mode_values_match_schema() -> None:
    # Must match 0005 partition migration CHECK exactly.
    expected = {"normal", "rapid", "low_power", "storm", "maintenance"}
    assert {m.value for m in CadenceMode} == expected


def test_transmission_type_values_match_schema() -> None:
    # Must match 0001 init CHECK exactly.
    expected = {"esp_now", "lora", "rs485", "wifi"}
    assert {t.value for t in TransmissionType} == expected


def test_valve_status_values_match_schema() -> None:
    expected = {"open", "closed", "fault"}
    assert {v.value for v in ValveStatus} == expected


# ---------------------------------------------------------------------------
# is_satellite_only behavior
# ---------------------------------------------------------------------------
def test_is_satellite_only_true_when_all_sensor_fields_null() -> None:
    r = _minimal_reading()  # no soil measurements
    assert r.is_satellite_only() is True


def test_is_satellite_only_false_when_any_sensor_field_set() -> None:
    r = _minimal_reading(soil_moisture_1_pct=Decimal("28.0"))
    assert r.is_satellite_only() is False

    r = _minimal_reading(soil_temp_rootzone_c=Decimal("22.0"))
    assert r.is_satellite_only() is False

    r = _minimal_reading(soil_n_mg_kg=Decimal("100"))
    assert r.is_satellite_only() is False


# ---------------------------------------------------------------------------
# Low-battery threshold sanity
# ---------------------------------------------------------------------------
def test_low_battery_threshold_is_decimal() -> None:
    # Type integrity matters because the Phase 4 hot-rule does decimal
    # comparisons; a stray float here would silently break those.
    assert isinstance(LOW_BATTERY_THRESHOLD_V, Decimal)
    assert Decimal("3.30") == LOW_BATTERY_THRESHOLD_V
