"""Geodesic plot-area helper."""

from __future__ import annotations

import pytest

from app.domain.geo_area import (
    m2_to_acre,
    polygon_area_m2_from_wkt,
    ring_area_m2,
    wkt_polygon_outer_ring,
)


def test_one_degree_square_at_equator() -> None:
    # A 1°x1° cell straddling the equator ~ 12,308 km².
    ring = [(0.0, -0.5), (1.0, -0.5), (1.0, 0.5), (0.0, 0.5)]
    area = ring_area_m2(ring)
    assert 1.22e10 < area < 1.24e10


def test_small_plot_near_kannad() -> None:
    # ~0.001°x0.001° near lat 19.86 (Kannad): ~104.7 m x ~110.6 m ~ 11,580 m².
    lat, lon = 19.86, 75.40
    d = 0.001
    ring = [(lon, lat), (lon + d, lat), (lon + d, lat + d), (lon, lat + d)]
    area = ring_area_m2(ring)
    assert 11_000 < area < 12_200


def test_winding_and_closure_invariant() -> None:
    ring_open = [(75.40, 19.86), (75.41, 19.86), (75.41, 19.87), (75.40, 19.87)]
    ring_closed = [*ring_open, ring_open[0]]
    ring_reversed = list(reversed(ring_open))
    a = ring_area_m2(ring_open)
    assert ring_area_m2(ring_closed) == pytest.approx(a)
    assert ring_area_m2(ring_reversed) == pytest.approx(a)  # abs → winding-agnostic


def test_degenerate_ring_is_zero() -> None:
    assert ring_area_m2([(75.4, 19.8), (75.41, 19.8)]) == 0.0
    assert ring_area_m2([]) == 0.0


def test_m2_to_acre() -> None:
    assert m2_to_acre(4046.8564224) == pytest.approx(1.0)


def test_wkt_outer_ring_parse() -> None:
    wkt = "POLYGON((75.40 19.86, 75.41 19.86, 75.41 19.87, 75.40 19.87, 75.40 19.86))"
    ring = wkt_polygon_outer_ring(wkt)
    assert ring is not None
    assert ring[0] == (75.40, 19.86)
    assert len(ring) == 5
    area = polygon_area_m2_from_wkt(wkt)
    assert area is not None
    assert 1.1e6 < area < 1.22e6  # ~0.01°x0.01° near Kannad


@pytest.mark.parametrize(
    "bad",
    ["not wkt", "POINT(75 19)", "POLYGON()", "POLYGON((75.4))", "", "POLYGON((a b, c d))"],
)
def test_wkt_invalid_returns_none(bad: str) -> None:
    assert wkt_polygon_outer_ring(bad) is None
    assert polygon_area_m2_from_wkt(bad) is None
