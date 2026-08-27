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

# ---------------------------------------------------------------------------
# Type aliases for clarity at call sites.
# ---------------------------------------------------------------------------
ZERO: Decimal = Decimal("0")
HUNDRED: Decimal = Decimal("100")
ADC_MAX: Decimal = Decimal("1023")  # 10-bit ADC full-scale
SECONDS_PER_MINUTE: Decimal = Decimal("60")
US_CM_PER_MS_CM: Decimal = Decimal("1000")   # µS/cm → mS/cm


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
    battery_vref_v: Decimal          # ADC reference voltage (typ. 3.300 V)
    battery_divider_ratio: Decimal   # resistor divider (typ. 3.200 for 220k+100k)

    # Pressure transducer
    pressure_offset_v: Decimal        # 0.5 V at 0 bar (typ.)
    pressure_scale_bar_per_v: Decimal # bar per volt above offset (typ. 2.5)

    # Flow sensor
    flow_pulses_per_litre: Decimal    # hall-effect ticks per litre (typ. 450)
    flow_window_seconds: Decimal      # fallback reporting cadence (typ. 300.0)

    # NPK register scaling
    npk_temp_divisor: Decimal         # register / 10  → °C
    npk_moisture_divisor: Decimal     # register / 10  → %
    npk_ph_divisor: Decimal           # register / 100 → pH

    # Audit
    calibration_version: int


# ---------------------------------------------------------------------------
# Pure conversion functions.  Each is total (no exceptions) so that a
# single bad row in Postgres cannot crash the ingest pipeline — it
# clamps or returns None.
# ---------------------------------------------------------------------------

def calibrate_soil_moisture_pct(raw_adc: int, cal: DeviceCalibration) -> Decimal:
    """Convert soil-moisture ADC to volumetric water content %.

    Linear map between DRY_ADC (0 % VWC) and WET_ADC (100 % VWC), clamped
    [0, 100]. Capacitive probes read HIGH ADC in dry soil and LOW ADC in
    wet soil (DRY_ADC > WET_ADC on a well-behaved probe); the formula is
    written so it also works if the calibration row has WET > DRY (e.g. a
    resistive probe with inverted polarity) — the sign of the span picks
    the right end.

    ``pct = (DRY - raw) / (DRY - WET) * 100``

    If DRY == WET (uncalibrated row) we return 0 rather than raising.
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
    return (
        Decimal(pulses_window) * SECONDS_PER_MINUTE
        / (window * cal.flow_pulses_per_litre)
    )


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
    "npk_ec_ms_cm",
]
