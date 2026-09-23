"""Age gate for DPDP consent (LEGAL_COMPLIANCE_CERTIFICATE §3.1, DPDP §9).

A data principal under 18 requires verifiable parental consent. Pure date math;
the calendar age is computed as completed years as of a reference date.
"""

from __future__ import annotations

from datetime import date

MINOR_AGE_THRESHOLD = 18


def age_years(date_of_birth: date, as_of: date) -> int:
    """Completed years between ``date_of_birth`` and ``as_of``."""
    years = as_of.year - date_of_birth.year
    if (as_of.month, as_of.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years


def is_minor(date_of_birth: date, as_of: date) -> bool:
    """True if under 18 as of ``as_of``."""
    return age_years(date_of_birth, as_of) < MINOR_AGE_THRESHOLD


__all__ = ["MINOR_AGE_THRESHOLD", "age_years", "is_minor"]
