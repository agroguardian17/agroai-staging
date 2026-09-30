"""Tests for the pure water-budget math (app/domain/water_budget.py)."""

from __future__ import annotations

from decimal import Decimal

from app.domain import water_budget as wb


def test_estimate_plants() -> None:
    assert wb.estimate_plants(Decimal("2"), 24300) == 48600
    assert wb.estimate_plants(Decimal("1.5"), 24300) == 36450
    assert wb.estimate_plants(None, 24300) is None
    assert wb.estimate_plants(Decimal("2"), None) is None
    assert wb.estimate_plants(Decimal("0"), 24300) is None


def test_classify_vwc() -> None:
    sat, stress = Decimal("45"), Decimal("20")
    assert wb.classify_vwc(Decimal("46"), sat, stress) == wb.VWC_SATURATED
    assert wb.classify_vwc(Decimal("45"), sat, stress) == wb.VWC_SATURATED  # boundary inclusive
    assert wb.classify_vwc(Decimal("18"), sat, stress) == wb.VWC_LOW
    assert wb.classify_vwc(Decimal("30"), sat, stress) == wb.VWC_OK
    assert wb.classify_vwc(None, sat, stress) is None  # no reading -> UNKNOWN


def test_per_plant_cumulative() -> None:
    assert wb.per_plant_cumulative(Decimal("48600"), 48600) == Decimal("1.00")
    assert wb.per_plant_cumulative(Decimal("97200"), 48600) == Decimal("2.00")
    assert wb.per_plant_cumulative(None, 100) is None
    assert wb.per_plant_cumulative(Decimal("100"), 0) is None


def test_deficit_ratio() -> None:
    # target 100 L/plant, delivered 60 -> 40% deficit
    assert wb.deficit_ratio(Decimal("60"), Decimal("100")) == Decimal("0.40")
    # fully met -> 0 deficit
    assert wb.deficit_ratio(Decimal("100"), Decimal("100")) == Decimal("0.00")
    # over-delivered -> clamped to 0
    assert wb.deficit_ratio(Decimal("120"), Decimal("100")) == Decimal("0.00")
    assert wb.deficit_ratio(Decimal("0"), Decimal("100")) == Decimal("1.00")
    assert wb.deficit_ratio(Decimal("50"), None) is None
    assert wb.deficit_ratio(Decimal("50"), Decimal("0")) is None


def test_cumulative_vs_lifecycle_ratio() -> None:
    assert wb.cumulative_vs_lifecycle_ratio(Decimal("300"), Decimal("250")) == Decimal("1.200")
    assert wb.cumulative_vs_lifecycle_ratio(Decimal("200"), Decimal("250")) == Decimal("0.800")
    assert wb.cumulative_vs_lifecycle_ratio(Decimal("300"), None) is None


def test_geometry_incomplete() -> None:
    complete = dict(
        planting_method="broad_ridge",
        dripper_spacing_cm=Decimal("30"),
        drippers_per_acre=24300,
        rows_per_bed=2,
        plants_per_acre=24300,
    )
    assert wb.geometry_incomplete(**complete) is False
    assert wb.geometry_incomplete(**{**complete, "planting_method": None}) is True
    assert wb.geometry_incomplete(**{**complete, "dripper_spacing_cm": None}) is True
    assert wb.geometry_incomplete(**{**complete, "rows_per_bed": None}) is True
