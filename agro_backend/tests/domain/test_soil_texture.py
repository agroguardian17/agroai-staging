"""USDA soil-texture-triangle classification."""

from __future__ import annotations

import pytest

from app.domain.soil_texture import (
    texture_class_from_fractions,
    texture_group,
    usda_texture_class,
)


@pytest.mark.parametrize(
    ("sand", "silt", "clay", "expected"),
    [
        (90, 5, 5, "sand"),
        (80, 12, 8, "loamy_sand"),
        (65, 25, 10, "sandy_loam"),
        (40, 40, 20, "loam"),
        (20, 65, 15, "silt_loam"),
        (5, 90, 5, "silt"),
        (55, 15, 30, "sandy_clay_loam"),
        (35, 33, 32, "clay_loam"),
        (10, 60, 30, "silty_clay_loam"),
        (55, 5, 40, "sandy_clay"),
        (10, 45, 45, "silty_clay"),
        (20, 20, 60, "clay"),
    ],
)
def test_usda_reference_points(sand: float, silt: float, clay: float, expected: str) -> None:
    assert usda_texture_class(sand, silt, clay) == expected


@pytest.mark.parametrize(
    ("usda", "group"),
    [
        ("sand", "light"),
        ("loamy_sand", "light"),
        ("sandy_loam", "light"),
        ("loam", "medium"),
        ("silt_loam", "medium"),
        ("clay_loam", "medium"),
        ("sandy_clay_loam", "medium"),
        ("sandy_clay", "heavy"),
        ("silty_clay", "heavy"),
        ("clay", "heavy"),
    ],
)
def test_texture_group(usda: str, group: str) -> None:
    assert texture_group(usda) == group


def test_group_light_medium_heavy_end_to_end() -> None:
    assert texture_class_from_fractions(90, 5, 5) == "light"
    assert texture_class_from_fractions(40, 40, 20) == "medium"
    assert texture_class_from_fractions(20, 20, 60) == "heavy"


@pytest.mark.parametrize(
    ("sand", "silt", "clay"),
    [
        (50, 50, 50),  # sums to 150
        (10, 10, 10),  # sums to 30
        (-1, 50, 51),  # negative
        (0, 0, 0),  # sums to 0
    ],
)
def test_invalid_compositions_return_none(sand: float, silt: float, clay: float) -> None:
    assert usda_texture_class(sand, silt, clay) is None
    assert texture_class_from_fractions(sand, silt, clay) is None


def test_rounding_tolerance_accepts_99_to_101() -> None:
    # Labs round to whole percents; a sum of 99 or 101 must still classify.
    assert texture_class_from_fractions(33, 33, 33) is not None
