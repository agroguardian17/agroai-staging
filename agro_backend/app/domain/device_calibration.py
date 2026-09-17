"""Per-device calibration constants + pure conversion functions.

PURE module (stdlib + Decimal only). Enforced by
``tests/domain/test_domain_purity.py``.

The Sub Node emits raw sensor outputs — raw ADC counts, pulse counters,
Modbus register integers. This module converts them into engineering
units (VWC%, volts, bar, L/min, °C, pH, µS/cm) using per-device
constants stored in the ``device_calibration`` Postgres table
(Alembic migration 0012).

Design rationale (see project skill §16 / Round 16):
* Firmware stays simple — no per-device tables in flash, no fixed-point math
  on the 8 MHz ATmega328P.
* Calibration drift over months of field use is fixed by a single SQL
  UPDATE — no USBasp reflash, no bricked probe.
* Each `Reading` row can carry the calibration version that produced it,
  so historical data can be retroactively recomputed if a mistake is
  found in the DRY_ADC / WET_ADC baselines.

All functions return ``Decimal`` (never ``float``). Clamping is applied
at obvious physical bounds (moisture 0-100 %, pressure ≥ 0 bar) so
downstream rule evaluation never sees a value that couldn't exist in
reality — a sensor glitch reads as "at the boundary", never as a rule-
firing pathology.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

# ---------------------------------------------------------------------------
# Type aliases for clarity at call sites.
# ---------------------------------------------------------------------------
ZERO: Decimal = Decimal("0")
HUNDRED: Decimal = Decimal("100")
ADC_MAX: Decimal = Decimal("1023")  # 10-bit ADC full-scale
SECONDS_PER_MINUTE: Decimal = Decimal("60")
US_CM_PER_MS_CM: Decimal = Decimal("1000")  # µS/cm → mS/cm


@dataclass(frozen=True, slots=True)
class DeviceCalibration:
    """Per-Sub-Node calibration constants.

    All fields are Decimal — no floats survive the boundary.

    Field-populated by the pilot's commissioning script; defaults in
    migration 0012 match the firmware team's tested constants so the
    system works out of the box before human intervention.
    """

    tenant_id: str
    device_id: str

    # Soil moisture (VWC%)
    soil_dry_adc: int
    soil_wet_adc: int

    # Battery voltage
    battery_vref_v: Decimal  # ADC reference voltage (typ. 3.300 V)
    battery_divider_ratio: Decimal  # resistor divider (typ. 3.200 for 220k+100k)

    # Pressure transducer
    pressure_offset_v: Decimal  # 0.5 V at 0 bar (typ.)
    pressure_scale_bar_per_v: Decimal  # bar per volt above offset (typ. 2.5)

    # Flow sensor
    flow_pulses_per_litre: Decimal  # hall-effect ticks per litre (typ. 450)
    flow_window_seconds: Decimal  # firmware reporting cadence (typ. 16.0)

    # NPK register scaling
    npk_temp_divisor: Decimal  # register / 10  → °C
    npk_moisture_divisor: Decimal  # register / 10  → %
    npk_ph_divisor: Decimal  # register / 100 → pH

    # Audit
    calibration_version: int


# ---------------------------------------------------------------------------
# Pure conversion functions.  Each is total (no exceptions) so that a
# single bad row in Postgres cannot crash the ingest pipeline — it
# clamps or returns None.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Capacitive soil-moisture probe — piecewise-linear ADC → VWC% calibration.
#
# Anchors from the firmware team's field calibration (Kuldip, Sep 2026):
# black cotton soil (vertisol), 160 cm3 container, capacitive probe. Ordered
# ADC-descending (dry → wet): a capacitive probe reads HIGH ADC when dry and
# LOW ADC when saturated. The curve is a fixed property of the probe model +
# soil type (not per-unit drift), so it lives here as a module constant rather
# than in the per-device ``device_calibration`` row. The endpoints are the
# probe's real physical range for this soil: 4.0 % VWC air-dry, 50.0 % VWC at
# natural saturation.
# ---------------------------------------------------------------------------
_SOIL_VWC_ANCHORS: tuple[tuple[int, Decimal], ...] = (
    (1019, Decimal("4.0")),  # air-dry baseline
    (844, Decimal("7.6")),
    (678, Decimal("11.3")),
    (540, Decimal("22.2")),
    (459, Decimal("33.2")),  # ~field-capacity zone (FC ≈ 35 % near ADC 449)
    (340, Decimal("50.0")),  # natural saturation
)


def capacitive_adc_to_vwc(adc: int) -> Decimal:
    """Convert a capacitive soil-moisture ADC count to volumetric water content %.

    Piecewise-linear over the field-measured anchors in ``_SOIL_VWC_ANCHORS``,
    clamped to the dry (4.0 %) and saturated (50.0 %) endpoints. This is the
    Sep-2026 corrected calibration for the pilot's capacitive probe in black
    cotton soil — it supersedes the old 2-point linear map, which assumed a
    0-100 % range the probe does not actually span.

    Total (never raises): an out-of-range or glitched ADC reads at a boundary,
    never as a rule-firing pathology.
    """
    hi_adc, hi_vwc = _SOIL_VWC_ANCHORS[0]  # driest anchor (1019, 4.0)
    lo_adc, lo_vwc = _SOIL_VWC_ANCHORS[-1]  # wettest anchor (340, 50.0)
    if adc >= hi_adc:
        return hi_vwc
    if adc <= lo_adc:
        return lo_vwc
    for (a_hi, v_hi), (a_lo, v_lo) in pairwise(_SOIL_VWC_ANCHORS):
        if a_lo <= adc <= a_hi:
            # Interpolate within [a_lo, a_hi] (ADC) → [v_hi, v_lo] (VWC).
            frac = (Decimal(a_hi) - Decimal(adc)) / (Decimal(a_hi) - Decimal(a_lo))
            return v_hi + frac * (v_lo - v_hi)
    return lo_vwc  # unreachable given the clamps; satisfies the type-checker


def calibrate_soil_moisture_pct(raw_adc: int, cal: DeviceCalibration) -> Decimal:
    """Legacy 2-point linear ADC → VWC% map (DRY_ADC=0 %, WET_ADC=100 %).

    Retained for probes/soils that follow a straight-line response and for
    back-compat with historical rows. **The pilot's capacitive probe uses
    :func:`capacitive_adc_to_vwc` instead** — its response is piecewise, not
    linear, and it spans 4-50 % VWC rather than 0-100 %.

    ``pct = (DRY - raw) / (DRY - WET) * 100``, clamped [0, 100]. If DRY == WET
    (uncalibrated row) returns 0 rather than raising.
    """
    dry = Decimal(cal.soil_dry_adc)
    wet = Decimal(cal.soil_wet_adc)
    span = dry - wet
    if span == ZERO:
        return ZERO
    pct = (dry - Decimal(raw_adc)) / span * HUNDRED
    if pct < ZERO:
        return ZERO
    if pct > HUNDRED:
        return HUNDRED
    return pct


def calibrate_battery_v(raw_adc: int, cal: DeviceCalibration) -> Decimal:
    """Convert battery-pin ADC to volts at the battery terminal.

    ``voltage_at_pin = raw x VREF / 1023``
    ``voltage_at_battery = voltage_at_pin x divider_ratio``
    """
    v_pin = Decimal(raw_adc) * cal.battery_vref_v / ADC_MAX
    return v_pin * cal.battery_divider_ratio


def calibrate_pressure_bar(raw_adc: int, cal: DeviceCalibration) -> Decimal:
    """Convert pressure-transducer ADC to bar.

    Transducer output is 0.5 V at 0 bar and 4.5 V at full scale (typ.).
    ``bar = ((raw x VREF / 1023) - offset) x scale``. Negative values
    (transducer noise below offset) are clamped to 0 — a small
    negative reading has no physical meaning.
    """
    v_pin = Decimal(raw_adc) * cal.battery_vref_v / ADC_MAX
    bar = (v_pin - cal.pressure_offset_v) * cal.pressure_scale_bar_per_v
    return bar if bar > ZERO else ZERO


def calibrate_flow_lpm(
    pulses_window: int,
    cal: DeviceCalibration,
    window_seconds_override: Decimal | None = None,
) -> Decimal | None:
    """Convert per-window pulse count to litres/minute.

    ``L/min = pulses x 60 / (window_seconds x pulses_per_L)``

    Round 16 used ``cal.flow_window_seconds`` as a fixed compile-time
    constant. 2026-08-27 v2 firmware (Sub Node 5-min cadence + LowPower
    WDT-timed sleep, RC ±10-15%) measures the actual wall-clock window
    on-device and emits it as ``raw_readings.window_s``; the ingest
    layer passes that through as ``window_seconds_override``.

    Contract:
    * ``window_seconds_override is None`` → fall back to the calibration
      row's fixed ``flow_window_seconds`` (legacy behaviour; used by the
      calibrated ``v2`` producer and by tests that don't exercise the new
      path).
    * ``window_seconds_override == 0`` → firmware signalled "unknown
      window" (first cycle after boot). Return ``None`` so the backend
      treats the derived flow rate as no-data; the totalizer
      ``flow_pulses_total`` remains the authoritative volume signal.
    * ``window_seconds_override > 0`` → use that value.

    If ``pulses_per_L`` or the effective ``window_seconds`` is zero
    (misconfigured calibration row) we return ``Decimal(0)`` rather than
    raising — downstream rules treat 0 flow as "no water", which is a
    safer default than crashing.
    """
    if window_seconds_override is not None:
        if window_seconds_override == ZERO:
            return None
        window = window_seconds_override
    else:
        window = cal.flow_window_seconds

    if cal.flow_pulses_per_litre == ZERO or window == ZERO:
        return ZERO
    return Decimal(pulses_window) * SECONDS_PER_MINUTE / (window * cal.flow_pulses_per_litre)


def calibrate_npk_temp_c(raw: int, cal: DeviceCalibration) -> Decimal:
    """Convert NPK Modbus temp register to °C (typ. divisor = 10)."""
    if cal.npk_temp_divisor == ZERO:
        return ZERO
    return Decimal(raw) / cal.npk_temp_divisor


def calibrate_npk_moisture_pct(raw: int, cal: DeviceCalibration) -> Decimal:
    """Convert NPK Modbus moisture register to % (typ. divisor = 10)."""
    if cal.npk_moisture_divisor == ZERO:
        return ZERO
    return Decimal(raw) / cal.npk_moisture_divisor


def calibrate_npk_ph(raw: int, cal: DeviceCalibration) -> Decimal:
    """Convert NPK Modbus pH register to pH units (typ. divisor = 100)."""
    if cal.npk_ph_divisor == ZERO:
        return ZERO
    return Decimal(raw) / cal.npk_ph_divisor


def npk_ec_ms_cm(us_cm: int) -> Decimal:
    """Convert sensor-native µS/cm to mS/cm (the DB column unit).

    No per-device calibration required — this is a pure unit conversion
    (1 mS/cm = 1000 µS/cm). Kept in this module for a single
    "raw sensor → Reading field" surface.
    """
    return Decimal(us_cm) / US_CM_PER_MS_CM


__all__ = [
    "ADC_MAX",
    "DeviceCalibration",
    "calibrate_battery_v",
    "calibrate_flow_lpm",
    "calibrate_npk_moisture_pct",
    "calibrate_npk_ph",
    "calibrate_npk_temp_c",
    "calibrate_pressure_bar",
    "calibrate_soil_moisture_pct",
    "capacitive_adc_to_vwc",
    "npk_ec_ms_cm",
]
