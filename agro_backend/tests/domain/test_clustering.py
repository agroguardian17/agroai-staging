"""D12 peer-cluster assignment — the deterministic gating algorithm."""

from __future__ import annotations

from datetime import date

from app.domain.clustering import (
    ClusterCandidate,
    PlotForClustering,
    assign_cluster,
    haversine_km,
)

_WEEK = date(2026, 6, 15)


def _plot(
    variety: str = "IISR Mahima", lat: float = 19.86, lng: float = 75.40
) -> PlotForClustering:
    return PlotForClustering(
        variety=variety, planting_week=_WEEK, centroid_lat=lat, centroid_lng=lng
    )


def _cluster(
    cid: str, *, variety="IISR Mahima", week=_WEEK, lat=19.86, lng=75.40, count=3
) -> ClusterCandidate:
    return ClusterCandidate(
        cluster_id=cid,
        variety=variety,
        planting_week_median=week,
        centroid_lat=lat,
        centroid_lng=lng,
        plot_count=count,
    )


def test_haversine_known_distance() -> None:
    # ~1 deg of latitude ~= 111 km.
    assert 110.0 < haversine_km(19.0, 75.0, 20.0, 75.0) < 112.0
    assert haversine_km(19.86, 75.40, 19.86, 75.40) == 0.0


def test_assign_picks_nearest_passing_cluster() -> None:
    plot = _plot(lat=19.860, lng=75.400)
    clusters = [
        _cluster("C_far", lat=19.880, lng=75.400),  # ~2.2 km
        _cluster("C_near", lat=19.862, lng=75.401),  # ~0.25 km
    ]
    res = assign_cluster(plot, clusters)
    assert res.cluster_id == "C_near"
    assert res.distance_km is not None and res.distance_km < 0.5
    assert res.fit_score > 0.6
    assert res.informational_only is False


def test_assign_spawns_new_when_no_fit() -> None:
    assert assign_cluster(_plot(), []).cluster_id is None


def test_variety_gate_strict_excludes_mismatch() -> None:
    res = assign_cluster(_plot(variety="IISR Mahima"), [_cluster("C1", variety="IISR Varada")])
    assert res.cluster_id is None  # strict variety gate -> no fit -> spawn


def test_variety_gate_loose_allows_mismatch_but_lowers_fit() -> None:
    res = assign_cluster(
        _plot(variety="IISR Mahima"),
        [_cluster("C1", variety="IISR Varada")],
        variety_gate="loose",
    )
    assert res.cluster_id == "C1"
    assert res.fit_score <= 0.5  # variety mismatch halves the score


def test_planting_week_gate_excludes_out_of_bucket() -> None:
    res = assign_cluster(_plot(), [_cluster("C1", week=date(2026, 6, 30))])  # 15 days apart > 7
    assert res.cluster_id is None


def test_proximity_gate_excludes_far_cluster() -> None:
    res = assign_cluster(
        _plot(lat=19.86, lng=75.40), [_cluster("C1", lat=19.90, lng=75.40)]
    )  # ~4.4 km > 3
    assert res.cluster_id is None


def test_capacity_gate_excludes_full_cluster() -> None:
    res = assign_cluster(_plot(), [_cluster("C1", count=12)])  # at max
    assert res.cluster_id is None


def test_fit_below_threshold_is_informational_only() -> None:
    # A cluster right at the proximity edge -> low fit -> informational only.
    plot = _plot(lat=19.86, lng=75.40)
    # ~2.9 km away (just inside 3 km).
    res = assign_cluster(plot, [_cluster("C1", lat=19.886, lng=75.40)])
    assert res.cluster_id == "C1"
    assert res.fit_score < 0.6
    assert res.informational_only is True
