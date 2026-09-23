"""Age gate for DPDP consent."""

from __future__ import annotations

from datetime import date

from app.domain.age import age_years, is_minor


def test_age_years_before_and_after_birthday() -> None:
    dob = date(2010, 6, 15)
    assert age_years(dob, date(2028, 6, 14)) == 17  # day before 18th birthday
    assert age_years(dob, date(2028, 6, 15)) == 18  # on the 18th birthday


def test_is_minor_boundary() -> None:
    dob = date(2010, 6, 15)
    assert is_minor(dob, date(2028, 6, 14)) is True
    assert is_minor(dob, date(2028, 6, 15)) is False  # turns 18 → not a minor


def test_clearly_adult_and_child() -> None:
    assert is_minor(date(1990, 1, 1), date(2026, 9, 24)) is False
    assert is_minor(date(2015, 1, 1), date(2026, 9, 24)) is True
