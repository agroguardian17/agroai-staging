"""Unit tests for the pure satellite-metrics domain module."""

from __future__ import annotations

from decimal import Decimal

from app.domain.satellite_metrics import (
    acre_to_hectare,
    advisory_confidence_from_freshness,
    baseline_gap,
    index_delta,
    ndvi_regional_baseline,
    sar_rvi,
)


def test_confidence_full_when_fresh() -> None:
    assert advisory_confidence_from_freshness(3) == Decimal("1")
    assert advisory_confidence_from_freshness(5) == Decimal("1")


def test_confidence_decays_linearly() -> None:
    assert advisory_confidence_from_freshness(8) == Decimal("0.80")  # 1 - 3/15
    assert advisory_confidence_from_freshness(17) == Decimal("0.20")  # 1 - 12/15


def test_confidence_floor_and_none() -> None:
    assert advisory_confidence_from_freshness(20) == Decimal("0")
    assert advisory_confidence_from_freshness(30) == Decimal("0")
    assert advisory_confidence_from_freshness(None) is None


def test_index_delta() -> None:
    assert index_delta(Decimal("0.50"), Decimal("0.65")) == Decimal("-0.15")
    assert index_delta(None, Decimal("0.6")) is None
    assert index_delta(Decimal("0.6"), None) is None


def test_sar_rvi_from_db() -> None:
    # vv=-10 dB -> 0.1 linear, vh=-16 dB -> ~0.0251 linear; rvi ~ 0.803
    v = sar_rvi(Decimal("-10"), Decimal("-16"))
    assert v is not None
    assert Decimal("0.79") < v < Decimal("0.81")
    assert sar_rvi(None, Decimal("-16")) is None


def test_ndvi_baseline_curve() -> None:
    assert ndvi_regional_baseline(0) == Decimal("0.15")
    assert ndvi_regional_baseline(-10) == Decimal("0.15")  # clamped low
    assert ndvi_regional_baseline(240) == Decimal("0.40")
    assert ndvi_regional_baseline(300) == Decimal("0.40")  # clamped high
    # DAP 120 sits between the 90 (0.60) and 150 (0.75) anchors → ~0.675
    mid = ndvi_regional_baseline(120)
    assert mid is not None and Decimal("0.66") < mid < Decimal("0.69")
    assert ndvi_regional_baseline(None) is None


def test_baseline_gap() -> None:
    assert baseline_gap(Decimal("0.55"), Decimal("0.68")) == Decimal("-0.13")
    assert baseline_gap(None, Decimal("0.6")) is None


def test_acre_to_hectare() -> None:
    assert acre_to_hectare(Decimal("1")) == Decimal("0.4047")
    assert acre_to_hectare(None) is None
