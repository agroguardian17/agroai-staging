"""Unit tests for the pure VPD domain module."""

from __future__ import annotations

from decimal import Decimal

from app.domain.vpd import saturation_vapour_pressure_kpa, vpd_kpa


def test_vpd_typical_reading() -> None:
    # T=30 C, RH=60% -> es ~ 4.245 kPa, vpd ~ 1.698 kPa.
    v = vpd_kpa(Decimal("30"), Decimal("60"))
    assert v is not None
    assert Decimal("1.69") < v < Decimal("1.71")
    # quantised to 3 decimals
    assert v == v.quantize(Decimal("0.001"))


def test_vpd_hot_dry_is_high() -> None:
    # Kannad spring afternoon: 40 C, 20% RH -> well above the 2.0 kPa spray ceiling.
    v = vpd_kpa(Decimal("40"), Decimal("20"))
    assert v is not None and v > Decimal("2.0")


def test_vpd_at_saturation_is_zero() -> None:
    assert vpd_kpa(Decimal("30"), Decimal("100")) == Decimal("0.000")


def test_vpd_supersaturation_clamped_to_zero() -> None:
    # RH > 100 would give a negative deficit; clamp to non-negative.
    assert vpd_kpa(Decimal("20"), Decimal("120")) == Decimal("0")


def test_vpd_missing_inputs_return_none() -> None:
    assert vpd_kpa(None, Decimal("60")) is None
    assert vpd_kpa(Decimal("30"), None) is None
    assert vpd_kpa(None, None) is None


def test_saturation_vapour_pressure_monotonic_in_temperature() -> None:
    lo = saturation_vapour_pressure_kpa(Decimal("20"))
    hi = saturation_vapour_pressure_kpa(Decimal("35"))
    assert lo is not None and hi is not None
    assert hi > lo  # es rises with temperature


def test_saturation_vapour_pressure_none_and_singularity() -> None:
    assert saturation_vapour_pressure_kpa(None) is None
    assert saturation_vapour_pressure_kpa(Decimal("-237.3")) is None  # would divide by zero
