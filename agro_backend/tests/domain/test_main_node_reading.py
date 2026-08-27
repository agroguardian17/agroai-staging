"""Domain tests for the Round 17.5 :class:`MainNodeReading` pure type."""

from __future__ import annotations

import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.main_node_reading import MainNodeReading


def _base() -> MainNodeReading:
    return MainNodeReading(
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        farm_id=uuid.UUID("bbbbbbbb-2222-2222-2222-222222222222"),
        main_node_id="AGR-MN-0001",
        recorded_at=datetime(2026, 8, 27, 5, 0, 0, tzinfo=UTC),
        received_at_master=datetime(2026, 8, 27, 5, 0, 0, tzinfo=UTC),
    )


def test_defaults_are_conservative() -> None:
    r = _base()
    assert r.sub_node_online is True
    assert r.sub_node_silence_ms == 0
    assert r.time_source is None
    assert r.rain_pulses_window == 0
    assert r.wind_pulses_window == 0
    assert r.wind_dir_adc == 0
    assert r.validation_warn is False
    assert r.sensor_health_json == {}


def test_frozen_dataclass_rejects_mutation() -> None:
    r = _base()
    with pytest.raises(FrozenInstanceError):
        r.sub_node_online = False  # type: ignore[misc]


def test_with_helper_produces_new_instance() -> None:
    r = _base()
    r2 = r.with_(sub_node_online=False, sub_node_silence_ms=900_001)
    assert r2 is not r
    assert r2.sub_node_online is False
    assert r2.sub_node_silence_ms == 900_001
    # Original untouched.
    assert r.sub_node_online is True
    assert r.sub_node_silence_ms == 0


def test_with_helper_carries_clock_skew_style_fields() -> None:
    """The broker's _normalize_clock_skew relies on with_() accepting
    recorded_at + received_at_master + sensor_health_json + validation_warn."""
    r = _base()
    now = datetime(2026, 8, 27, 6, 0, 0, tzinfo=UTC)
    r2 = r.with_(
        recorded_at=now,
        received_at_master=now,
        sensor_health_json={"timestamp_corrected": True},
        validation_warn=True,
    )
    assert r2.recorded_at == now
    assert r2.received_at_master == now
    assert r2.sensor_health_json == {"timestamp_corrected": True}
    assert r2.validation_warn is True


def test_decimal_fields_stay_decimal() -> None:
    """No float sneaks through the boundary."""
    r = _base().with_(
        bme280_temp_c=Decimal("32.4"),
        ina219_bus_v=Decimal("12.1"),
    )
    assert isinstance(r.bme280_temp_c, Decimal)
    assert isinstance(r.ina219_bus_v, Decimal)
