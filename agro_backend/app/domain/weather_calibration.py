"""Main Node weather-station calibration — pure pulse/ADC → engineering units.

PURE module (stdlib + ``Decimal`` only). Enforced by
``tests/domain/test_domain_purity.py``.

The Main Node emits raw counts for its own weather sensors (rain-gauge tips,
anemometer pulses, wind-vane ADC); this module converts them to engineering
units using the firmware team's field-measured constants (Sep 2026):

* **Rain gauge** — tipping bucket, 1 tip = 1 pulse = ``0.386 mm``.
* **Anemometer** — 2 pulses per rotation; ``K = 1.060 m/s per rotation/second``
  (the field-measured constant, replacing the old generic 1.2 factor). The
  firmware counts pulses over a fixed **10-second** sample window; the v2.1
  gust field is the max pulses in any **3-second** bucket.
* **Wind vane** — 8-direction resistive vane read on the ESP32 12-bit ADC
  (0-4095); nearest-ADC match to a compass point.

Every function is total (never raises) so a single bad count cannot crash the
ingest pipeline.

.. note::
   ``WIND_SAMPLE_WINDOW_SECONDS`` is the anemometer's fixed sample window. The
   MQTT ``master_readings`` block carries the pulse count but **not** the window
   duration, so this constant is the single source of truth for it. If the
   firmware's window ever changes, update it here — the whole wind-speed scale
   depends on it.
"""

from __future__ import annotations

from decimal import Decimal

ZERO: Decimal = Decimal("0")

# --- Barometric altitude ----------------------------------------------------
SEA_LEVEL_PRESSURE_PA: Decimal = Decimal("101325")
_ALTITUDE_COEFF: Decimal = Decimal("44330")
_ALTITUDE_EXPONENT: Decimal = Decimal("0.1903")
_ALTITUDE_QUANTUM: Decimal = Decimal("0.01")  # store to centimetre precision

# --- Rain gauge -------------------------------------------------------------
RAIN_MM_PER_TIP: Decimal = Decimal("0.386")

# --- Anemometer -------------------------------------------------------------
ANEMOMETER_K_MPS_PER_ROT_SEC: Decimal = Decimal("1.060")
WIND_PULSES_PER_ROTATION: Decimal = Decimal("2")
WIND_SAMPLE_WINDOW_SECONDS: Decimal = Decimal("10")  # firmware's fixed window
WIND_GUST_BUCKET_SECONDS: Decimal = Decimal("3")  # v2.1 max-pulse bucket
MPS_TO_KMH: Decimal = Decimal("3.6")

# --- Wind vane: (ADC, cardinal, degrees) ------------------------------------
# ADC anchors from the Main Node firmware's ``directionADC[]`` table (12-bit).
_WIND_VANE: tuple[tuple[int, str, Decimal], ...] = (
    (2965, "N", Decimal("0")),
    (1666, "NE", Decimal("45")),
    (218, "E", Decimal("90")),
    (576, "SE", Decimal("135")),
    (976, "S", Decimal("180")),
    (2330, "SW", Decimal("225")),
    (3920, "W", Decimal("270")),
    (3505, "NW", Decimal("315")),
)


def altitude_m_from_pressure_pa(pressure_pa: Decimal | None) -> Decimal | None:
    """Barometric altitude in metres from BME280 pressure in pascals.

    ``altitude = 44330 * (1 - (P / 101325) ** 0.1903)`` — the international
    barometric formula, identical to the one the Main Node firmware computes
    for serial output. Evaluated fully in ``Decimal`` (the fractional power
    goes through Decimal's ln/exp), then quantised to centimetre precision.

    Returns ``None`` when pressure is missing or non-positive. Above-sea-level
    pressures (a storm high) legitimately yield a small negative altitude; that
    is left unclamped, matching the firmware.
    """
    if pressure_pa is None or pressure_pa <= ZERO:
        return None
    ratio = pressure_pa / SEA_LEVEL_PRESSURE_PA
    altitude = _ALTITUDE_COEFF * (Decimal("1") - ratio**_ALTITUDE_EXPONENT)
    return altitude.quantize(_ALTITUDE_QUANTUM)


def rain_mm_from_pulses(pulses: int) -> Decimal:
    """Tipping-bucket pulse count → millimetres of rain (0.386 mm/tip)."""
    if pulses <= 0:
        return ZERO
    return Decimal(pulses) * RAIN_MM_PER_TIP


def _rot_per_sec_to_kmh(rot_per_sec: Decimal) -> Decimal:
    """rotations/second → km/h via the field-measured anemometer constant."""
    return rot_per_sec * ANEMOMETER_K_MPS_PER_ROT_SEC * MPS_TO_KMH


def wind_speed_kmh_from_pulses(
    pulses: int, window_seconds: Decimal = WIND_SAMPLE_WINDOW_SECONDS
) -> Decimal | None:
    """Anemometer pulses over the sample window → wind speed in km/h.

    ``rotations = pulses / 2``; ``rot/sec = rotations / window``;
    ``km/h = rot/sec * 1.060 * 3.6``. Returns ``None`` when the window is
    non-positive (unknown window); ``0`` when there were no pulses (calm).
    """
    if window_seconds <= ZERO:
        return None
    if pulses <= 0:
        return ZERO
    rotations = Decimal(pulses) / WIND_PULSES_PER_ROTATION
    return _rot_per_sec_to_kmh(rotations / window_seconds)


def wind_gust_kmh_from_pulses(
    gust_pulses: int, bucket_seconds: Decimal = WIND_GUST_BUCKET_SECONDS
) -> Decimal | None:
    """Max pulses in any 3-second bucket → gust speed in km/h."""
    if bucket_seconds <= ZERO:
        return None
    if gust_pulses <= 0:
        return ZERO
    rotations = Decimal(gust_pulses) / WIND_PULSES_PER_ROTATION
    return _rot_per_sec_to_kmh(rotations / bucket_seconds)


def wind_direction_from_adc(adc: int) -> tuple[Decimal, str]:
    """Nearest-match a wind-vane ADC count to a compass direction.

    Returns ``(degrees, cardinal)`` for the closest of the 8 calibrated
    anchors. Callers should treat ``adc <= 0`` as "no reading" and skip this
    (an open/disconnected vane floats near 0, far from every real anchor).
    """
    best_adc, best_cardinal, best_degrees = _WIND_VANE[0]
    smallest = abs(adc - best_adc)
    for anchor_adc, cardinal, degrees in _WIND_VANE[1:]:
        diff = abs(adc - anchor_adc)
        if diff < smallest:
            smallest = diff
            best_cardinal, best_degrees = cardinal, degrees
    return best_degrees, best_cardinal


__all__ = [
    "ANEMOMETER_K_MPS_PER_ROT_SEC",
    "RAIN_MM_PER_TIP",
    "SEA_LEVEL_PRESSURE_PA",
    "WIND_GUST_BUCKET_SECONDS",
    "WIND_SAMPLE_WINDOW_SECONDS",
    "altitude_m_from_pressure_pa",
    "rain_mm_from_pulses",
    "wind_direction_from_adc",
    "wind_gust_kmh_from_pulses",
    "wind_speed_kmh_from_pulses",
]
