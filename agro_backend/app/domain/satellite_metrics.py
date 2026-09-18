"""Derived satellite metrics — pure, Decimal-only.

The fetch adapter returns per-scene index means/stdev and SAR backscatter from
the processing platform (server-side evalscripts). Everything that is *computed
from that* — advisory confidence from freshness, day-over-day deltas, the radar
vegetation index, the Phase-1 regional NDVI baseline and its gap, and the
acre→hectare conversion for plot area — lives here so it is unit-testable
without a network or a database.

Pure: stdlib ``Decimal`` only (``Decimal.exp``/``**`` for the SAR dB→linear
conversion). No framework imports, no float — same discipline as
:mod:`app.domain.vpd` and :mod:`app.domain.weather_calibration`.
"""

from __future__ import annotations

from decimal import Decimal
from itertools import pairwise

_ONE = Decimal(1)
_HUNDRED = Decimal(100)

# --- Freshness → confidence (D14-NV-002) -----------------------------------
# Full confidence up to 5 days old, linear decay to 0 at 20 days.
_FRESH_FULL_DAYS = Decimal(5)
_FRESH_ZERO_DAYS = Decimal(20)
_ACRE_TO_HA = Decimal("0.404686")


def advisory_confidence_from_freshness(freshness_days: int | None) -> Decimal | None:
    """Satellite advisory confidence in [0, 1] from the age of the scene.

    ``conf = clamp(0, 1 - (days - 5) / 15, 1)`` — the D14-NV-002 formula.
    Returns ``None`` when freshness is unknown.
    """
    if freshness_days is None:
        return None
    days = Decimal(freshness_days)
    if days <= _FRESH_FULL_DAYS:
        return _ONE
    span = _FRESH_ZERO_DAYS - _FRESH_FULL_DAYS
    conf = _ONE - (days - _FRESH_FULL_DAYS) / span
    if conf < 0:
        return Decimal(0)
    return conf.quantize(Decimal("0.01"))


def index_delta(current: Decimal | None, past: Decimal | None) -> Decimal | None:
    """Signed change ``current - past`` for a vegetation index, or ``None``."""
    if current is None or past is None:
        return None
    return current - past


def sar_rvi(sar_vv_db: Decimal | None, sar_vh_db: Decimal | None) -> Decimal | None:
    """Radar Vegetation Index ``4*VH / (VV + VH)`` from dB backscatter.

    Sigma-nought arrives in dB; RVI is defined on linear power, so each band is
    converted ``linear = 10 ** (dB / 10)`` first. Returns ``None`` on missing
    inputs or a non-positive denominator.
    """
    if sar_vv_db is None or sar_vh_db is None:
        return None
    lin_vv = Decimal(10) ** (sar_vv_db / Decimal(10))
    lin_vh = Decimal(10) ** (sar_vh_db / Decimal(10))
    denom = lin_vv + lin_vh
    if denom <= 0:
        return None
    return (Decimal(4) * lin_vh / denom).quantize(Decimal("0.001"))


# --- Phase-1 regional NDVI baseline (author estimate; D14-OI-01) -----------
# Piecewise-linear expected NDVI for Kannad ginger by days-after-planting.
# SRC-EST: replaced by the season-1 empirical curve once field data lands.
_NDVI_BASELINE_ANCHORS: tuple[tuple[int, Decimal], ...] = (
    (0, Decimal("0.15")),  # bare soil at planting
    (35, Decimal("0.30")),  # G1 sprouting
    (90, Decimal("0.60")),  # G2 vegetative
    (150, Decimal("0.75")),  # G3 rhizome initiation — peak canopy
    (210, Decimal("0.65")),  # G4 bulking
    (240, Decimal("0.40")),  # G5 maturation / senescence
)


def ndvi_regional_baseline(dap: int | None) -> Decimal | None:
    """Expected NDVI for the crop's day-after-planting (Phase-1 estimate).

    Clamped to the curve's ends outside [0, 240]. ``None`` when DAP is unknown.
    """
    if dap is None:
        return None
    if dap <= _NDVI_BASELINE_ANCHORS[0][0]:
        return _NDVI_BASELINE_ANCHORS[0][1]
    if dap >= _NDVI_BASELINE_ANCHORS[-1][0]:
        return _NDVI_BASELINE_ANCHORS[-1][1]
    for (d0, v0), (d1, v1) in pairwise(_NDVI_BASELINE_ANCHORS):
        if d0 <= dap <= d1:
            frac = Decimal(dap - d0) / Decimal(d1 - d0)
            return (v0 + (v1 - v0) * frac).quantize(Decimal("0.01"))
    return None  # unreachable given the clamps


def baseline_gap(observed: Decimal | None, baseline: Decimal | None) -> Decimal | None:
    """Signed ``observed - baseline`` (negative = below expectation)."""
    if observed is None or baseline is None:
        return None
    return observed - baseline


def acre_to_hectare(area_acre: Decimal | None) -> Decimal | None:
    """Convert plot area from acres to hectares (D14 uses ``plot_area_ha``)."""
    if area_acre is None:
        return None
    return (area_acre * _ACRE_TO_HA).quantize(Decimal("0.0001"))


__all__ = [
    "acre_to_hectare",
    "advisory_confidence_from_freshness",
    "baseline_gap",
    "index_delta",
    "ndvi_regional_baseline",
    "sar_rvi",
]
