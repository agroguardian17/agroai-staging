"""Unit tests for the pure weather_calibration domain module."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.weather_calibration import (
    RAIN_MM_PER_TIP,
    altitude_m_from_pressure_pa,
    rain_mm_from_pulses,
    wind_direction_from_adc,
    wind_gust_kmh_from_pulses,
    wind_speed_kmh_from_pulses,
)


# ---------- Altitude ----------
def test_altitude_at_sea_level_pressure_is_zero() -> None:
    assert altitude_m_from_pressure_pa(Decimal("101325")) == Decimal("0.00")


def test_altitude_from_pressure_matches_barometric_formula() -> None:
    # 95000 Pa → ~540 m (the pilot's elevation band); 90000 Pa is higher.
    low = altitude_m_from_pressure_pa(Decimal("95000"))
    high = altitude_m_from_pressure_pa(Decimal("90000"))
    assert low is not None and high is not None
    assert Decimal("530") < low < Decimal("550")
    assert high > low  # lower pressure = higher altitude


def test_altitude_none_or_nonpositive_pressure_is_none() -> None:
    assert altitude_m_from_pressure_pa(None) is None
    assert altitude_m_from_pressure_pa(Decimal("0")) is None
    assert altitude_m_from_pressure_pa(Decimal("-1")) is None


# ---------- Rain ----------
def test_rain_mm_scales_by_0_386_per_tip() -> None:
    assert rain_mm_from_pulses(1) == RAIN_MM_PER_TIP == Decimal("0.386")
    assert rain_mm_from_pulses(10) == Decimal("3.860")


def test_rain_mm_zero_pulses_is_zero() -> None:
    assert rain_mm_from_pulses(0) == Decimal("0")
    assert rain_mm_from_pulses(-5) == Decimal("0")


# ---------- Wind speed ----------
def test_wind_speed_kmh_uses_k_and_two_pulses_per_rotation() -> None:
    # 20 pulses over the 10 s window = 10 rotations = 1 rot/sec.
    # km/h = 1 rot/sec * K(1.060 m/s per rot/sec) * 3.6 = 3.816 km/h.
    assert wind_speed_kmh_from_pulses(20) == Decimal("3.816")


def test_wind_speed_kmh_zero_pulses_is_calm() -> None:
    assert wind_speed_kmh_from_pulses(0) == Decimal("0")


def test_wind_speed_kmh_custom_window() -> None:
    # 12 rotations (24 pulses) over 6 s = 2 rot/sec → 2 * 1.060 * 3.6 = 7.632.
    assert wind_speed_kmh_from_pulses(24, Decimal("6")) == Decimal("7.632")


def test_wind_speed_kmh_nonpositive_window_is_none() -> None:
    assert wind_speed_kmh_from_pulses(20, Decimal("0")) is None


# ---------- Wind gust ----------
def test_wind_gust_kmh_over_three_second_bucket() -> None:
    # 6 pulses = 3 rotations over the 3 s bucket = 1 rot/sec → 3.816 km/h.
    assert wind_gust_kmh_from_pulses(6) == Decimal("3.816")


def test_wind_gust_kmh_zero_is_zero() -> None:
    assert wind_gust_kmh_from_pulses(0) == Decimal("0")


# ---------- Wind direction ----------
@pytest.mark.parametrize(
    ("adc", "cardinal", "degrees"),
    [
        (218, "E", Decimal("90")),
        (576, "SE", Decimal("135")),
        (976, "S", Decimal("180")),
        (2330, "SW", Decimal("225")),
        (3920, "W", Decimal("270")),
        (3505, "NW", Decimal("315")),
        (2965, "N", Decimal("0")),
        (1666, "NE", Decimal("45")),
    ],
)
def test_wind_direction_hits_exact_anchors(adc: int, cardinal: str, degrees: Decimal) -> None:
    deg, card = wind_direction_from_adc(adc)
    assert card == cardinal
    assert deg == degrees


def test_wind_direction_nearest_match_between_anchors() -> None:
    # 1000 is closest to S (976) among the anchors.
    deg, card = wind_direction_from_adc(1000)
    assert card == "S"
    assert deg == Decimal("180")
