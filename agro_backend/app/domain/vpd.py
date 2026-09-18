"""Vapour Pressure Deficit (VPD) — pure derived agronomic metric.

VPD is the temperature-corrected form of humidity and is what plants and
spray droplets actually respond to. Domain 7's VPD retrofit (rules
``D07-VP-001..003``) reads ``vpd_kpa`` from the farm brain; this module is
where the number is computed, from the cluster weather station's air
temperature and relative humidity — data we already collect, no new hardware.

Saturation vapour pressure uses the Tetens (1930) equation; VPD is the
saturation deficit at the given relative humidity:

    es(T)  = 0.6108 * exp(17.27 * T / (T + 237.3))     [kPa]
    vpd    = es(T) * (1 - RH/100)                        [kPa]

Pure: stdlib ``Decimal`` only (``Decimal.exp`` for the exponential), no float,
no framework imports — same discipline as :mod:`app.domain.weather_calibration`.
"""

from __future__ import annotations

from decimal import Decimal

# Tetens coefficients for saturation vapour pressure over water (kPa, °C).
_ES_A = Decimal("0.6108")
_ES_B = Decimal("17.27")
_ES_C = Decimal("237.3")
_QUANT = Decimal("0.001")


def saturation_vapour_pressure_kpa(air_temp_c: Decimal | None) -> Decimal | None:
    """Saturation vapour pressure es(T) in kPa via the Tetens equation.

    Returns ``None`` for a missing temperature or the physically impossible
    ``T = -237.3 °C`` (which would divide by zero).
    """
    if air_temp_c is None:
        return None
    denom = air_temp_c + _ES_C
    if denom == 0:
        return None
    exponent = _ES_B * air_temp_c / denom
    return _ES_A * exponent.exp()


def vpd_kpa(air_temp_c: Decimal | None, rh_pct: Decimal | None) -> Decimal | None:
    """Vapour pressure deficit in kPa from air temperature and relative humidity.

    ``air_temp_c`` in °C, ``rh_pct`` in percent (0-100). Returns ``None`` when
    either input is missing. Supersaturation (RH > 100) is clamped to a
    non-negative VPD. Quantised to 0.001 kPa.
    """
    es = saturation_vapour_pressure_kpa(air_temp_c)
    if es is None or rh_pct is None:
        return None
    vpd = es * (Decimal(1) - rh_pct / Decimal(100))
    if vpd < 0:
        vpd = Decimal(0)
    return vpd.quantize(_QUANT)


__all__ = ["saturation_vapour_pressure_kpa", "vpd_kpa"]
