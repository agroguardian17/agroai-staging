"""USDA soil-texture-triangle classification (pure).

Turns a lab's sand/silt/clay percentages into the KB's ``soil_texture_class``
(``light`` / ``medium`` / ``heavy``). :func:`usda_texture_class` is the standard
USDA-NRCS twelve-class triangle (computed from sand + clay, silt derived);
:func:`texture_group` collapses those twelve to the KB's three using the FAO
coarse / medium / fine convention — coarse=light, fine=heavy. That 12→3
grouping is the one agronomy choice here and is easy to retune.

Used by the farm-brain builder to override the soil-type-derived texture class
with a lab-measured one (``soil_texture_class_source = "lab"``).
"""

from __future__ import annotations

# FAO coarse/medium/fine grouping of the twelve USDA classes.
_LIGHT = frozenset({"sand", "loamy_sand", "sandy_loam"})
_HEAVY = frozenset({"sandy_clay", "silty_clay", "clay"})
# Everything else (loam, silt_loam, silt, sandy_clay_loam, clay_loam,
# silty_clay_loam) is medium.


def usda_texture_class(sand_pct: float, silt_pct: float, clay_pct: float) -> str | None:
    """The USDA twelve-class texture name, or ``None`` if the mix is invalid.

    Uses sand and clay (the triangle's two independent axes) and treats silt as
    the remainder; ``silt_pct`` is accepted for a consistency check only.
    """
    if sand_pct < 0 or silt_pct < 0 or clay_pct < 0:
        return None
    total = sand_pct + silt_pct + clay_pct
    if not (95.0 <= total <= 105.0):  # must be a ~whole composition
        return None

    sand, clay = sand_pct, clay_pct
    silt = 100.0 - sand - clay  # normalized silt for the triangle boundaries
    if silt < 0:
        return None

    if silt + 1.5 * clay < 15:
        return "sand"
    if silt + 2 * clay < 30:
        return "loamy_sand"
    if (7 <= clay < 20 and sand > 52 and silt + 2 * clay >= 30) or (clay < 7 and silt < 50):
        return "sandy_loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "silt_loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "sandy_clay_loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "clay_loam"
    if 27 <= clay < 40 and sand <= 20:
        return "silty_clay_loam"
    if clay >= 35 and sand > 45:
        return "sandy_clay"
    if clay >= 40 and silt >= 40:
        return "silty_clay"
    if clay >= 40 and sand <= 45:
        return "clay"
    return "loam"  # small interior gaps collapse to loam (the triangle's centre)


def texture_group(usda_class: str) -> str:
    """Collapse a USDA class to the KB's ``light`` / ``medium`` / ``heavy``."""
    if usda_class in _LIGHT:
        return "light"
    if usda_class in _HEAVY:
        return "heavy"
    return "medium"


def texture_class_from_fractions(sand_pct: float, silt_pct: float, clay_pct: float) -> str | None:
    """Lab sand/silt/clay % → KB ``soil_texture_class``, or ``None`` if invalid."""
    usda = usda_texture_class(sand_pct, silt_pct, clay_pct)
    return None if usda is None else texture_group(usda)


__all__ = ["texture_class_from_fractions", "texture_group", "usda_texture_class"]
