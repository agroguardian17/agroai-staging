"""Geodesic polygon area for plot boundaries (pure).

The farmer-app plot polygon (``plot_polygon_wkt``) is stored as lon/lat
**degrees**. A planar shoelace over degrees yields degrees², not m² — so plot
area is computed with the spherical-excess formula over the WGS84 mean radius,
which is accurate to well under 1% at plot scale (hectares). Used by the water-
budget engine to derive ``plot_area_m2`` / ``plot_area_acre`` from the polygon.

Pure: stdlib ``math`` only.
"""

from __future__ import annotations

import math
from itertools import pairwise

_EARTH_MEAN_RADIUS_M = 6_371_008.8  # WGS84 mean radius
_M2_PER_ACRE = 4046.8564224

# A ring is a list of (lon, lat) vertices in decimal degrees.
Ring = list[tuple[float, float]]


def ring_area_m2(ring: Ring) -> float:
    """Geodesic area of a lon/lat polygon ring, in m² (always non-negative).

    Uses the spherical-excess line-integral form; the ring may be open or
    closed and either winding. Returns 0.0 for a degenerate ring (< 3 vertices).
    """
    if len(ring) < 3:
        return 0.0
    pts: Ring = list(ring)
    if pts[0] != pts[-1]:
        pts.append(pts[0])

    total = 0.0
    for (lon1, lat1), (lon2, lat2) in pairwise(pts):
        total += math.radians(lon2 - lon1) * (
            2.0 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2))
        )
    return abs(total * _EARTH_MEAN_RADIUS_M * _EARTH_MEAN_RADIUS_M / 2.0)


def m2_to_acre(area_m2: float) -> float:
    return area_m2 / _M2_PER_ACRE


def wkt_polygon_outer_ring(wkt: str) -> Ring | None:
    """Parse the outer ring of a ``POLYGON((lon lat, ...))`` WKT string.

    Returns the vertices as (lon, lat) floats, or ``None`` if the string is not
    a well-formed POLYGON (inner rings/holes are ignored — plot area uses the
    outer boundary).
    """
    if not isinstance(wkt, str):
        return None
    s = wkt.strip()
    if not s.upper().startswith("POLYGON"):
        return None
    start = s.find("((")
    end = s.find("))", start)
    if start == -1 or end == -1:
        return None
    body = s[start + 2 : end]  # first (outer) ring only
    ring: Ring = []
    for pair in body.split(","):
        parts = pair.split()
        if len(parts) < 2:
            return None
        try:
            ring.append((float(parts[0]), float(parts[1])))
        except ValueError:
            return None
    return ring or None


def polygon_area_m2_from_wkt(wkt: str) -> float | None:
    """Plot area in m² from a POLYGON WKT, or ``None`` if it can't be parsed."""
    ring = wkt_polygon_outer_ring(wkt)
    return None if ring is None else ring_area_m2(ring)


__all__ = [
    "Ring",
    "m2_to_acre",
    "polygon_area_m2_from_wkt",
    "ring_area_m2",
    "wkt_polygon_outer_ring",
]
