"""Domain tests for the Round 17 :class:`WeatherStationReading` pure type."""

from __future__ import annotations

import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.weather_station_reading import WeatherStationReading


def _base() -> WeatherStationReading:
    return WeatherStationReading(
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        master_node_id="AGR-MN-0001",
        farm_id=uuid.UUID("bbbbbbbb-2222-2222-2222-222222222222"),
        recorded_at=datetime(2026, 9, 5, 5, 0, 0, tzinfo=UTC),
    )


def test_defaults_are_conservative() -> None:
    r = _base()
    assert r.air_temp_c is None
    assert r.humidity_pct is None
    assert r.atmospheric_pressure_hpa is None
    assert r.wind_speed_kmh is None
    assert r.rain_mm_today is None
    assert r.validation_warn is False
    assert r.sensor_health_json == {}


def test_frozen_dataclass_rejects_mutation() -> None:
    r = _base()
    with pytest.raises(FrozenInstanceError):
        r.air_temp_c = Decimal("30")  # type: ignore[misc]


def test_with_helper_produces_new_instance() -> None:
    r = _base()
    r2 = r.with_(
        air_temp_c=Decimal("32.4"),
        humidity_pct=Decimal("65.1"),
        atmospheric_pressure_hpa=Decimal("950"),
    )
    assert r2 is not r
    assert r2.air_temp_c == Decimal("32.4")
    assert r.air_temp_c is None


def test_with_helper_carries_clock_skew_style_fields() -> None:
    """Broker's _normalize_clock_skew relies on with_() accepting these keys."""
    r = _base()
    now = datetime(2026, 9, 5, 6, 0, 0, tzinfo=UTC)
    r2 = r.with_(
        recorded_at=now,
        sensor_health_json={"timestamp_corrected": True},
        validation_warn=True,
    )
    assert r2.recorded_at == now
    assert r2.sensor_health_json == {"timestamp_corrected": True}
    assert r2.validation_warn is True


def test_decimal_fields_stay_decimal() -> None:
    r = _base().with_(
        air_temp_c=Decimal("32.4"),
        humidity_pct=Decimal("65.1"),
        wind_speed_kmh=Decimal("14.2"),
    )
    assert isinstance(r.air_temp_c, Decimal)
    assert isinstance(r.humidity_pct, Decimal)
    assert isinstance(r.wind_speed_kmh, Decimal)


def test_slots_enforced_no_dict() -> None:
    r = _base()
    assert not hasattr(r, "__dict__")
