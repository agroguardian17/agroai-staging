"""D12 peer-cluster assignment — the deterministic gating algorithm (pure).

A plot joins the nearest existing cluster that passes four gates (D12_QA_WORKFLOW
§4.6): same variety (strict mode), planting week within +/-7 days, centroid within
3 km (great-circle), and spare capacity (< max_plots). No fit -> spawn a new
cluster (the caller mints its id). A cluster activates its peer baseline for the
D14 satellite rules once it reaches min_plots (8) members.

``cluster_fit_score`` in [0,1] grades how well the chosen cluster fits (1.0 =
perfect); a plot scoring < 0.6 is flagged INFORMATIONAL_ONLY for D14 (D14-AN-002).

Pure: stdlib ``math`` only. The application layer loads the active clusters,
calls these, then persists the assignment.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

_EARTH_RADIUS_KM = 6371.0


@dataclass(frozen=True, slots=True)
class PlotForClustering:
    variety: str
    planting_week: date
    centroid_lat: float
    centroid_lng: float


@dataclass(frozen=True, slots=True)
class ClusterCandidate:
    cluster_id: str
    variety: str
    planting_week_median: date
    centroid_lat: float
    centroid_lng: float
    plot_count: int


@dataclass(frozen=True, slots=True)
class ClusterAssignment:
    cluster_id: str | None  # None -> spawn a new cluster
    distance_km: float | None
    fit_score: float
    informational_only: bool


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km between two lat/lng points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _fit_score(distance_km: float, proximity_km: float, variety_match: bool) -> float:
    """1.0 = centroid-coincident + variety match; falls to 0 at the proximity edge."""
    proximity = 1.0 - min(distance_km / proximity_km, 1.0) if proximity_km > 0 else 0.0
    return round(proximity * (1.0 if variety_match else 0.5), 3)


def assign_cluster(
    plot: PlotForClustering,
    clusters: list[ClusterCandidate],
    *,
    variety_gate: str = "strict",
    max_plots_per_cluster: int = 12,
    proximity_km: float = 3.0,
    planting_week_bucket_days: int = 7,
    fit_threshold: float = 0.6,
) -> ClusterAssignment:
    """The nearest passing cluster, or a spawn (cluster_id None). Deterministic."""
    candidates: list[tuple[ClusterCandidate, float]] = []
    for c in clusters:
        if variety_gate == "strict" and c.variety != plot.variety:
            continue
        if abs((c.planting_week_median - plot.planting_week).days) > planting_week_bucket_days:
            continue
        distance = haversine_km(
            c.centroid_lat, c.centroid_lng, plot.centroid_lat, plot.centroid_lng
        )
        if distance > proximity_km:
            continue
        if c.plot_count >= max_plots_per_cluster:
            continue
        candidates.append((c, distance))

    if not candidates:
        return ClusterAssignment(
            cluster_id=None, distance_km=None, fit_score=0.0, informational_only=False
        )

    cluster, distance = min(candidates, key=lambda x: x[1])
    fit = _fit_score(distance, proximity_km, cluster.variety == plot.variety)
    return ClusterAssignment(
        cluster_id=cluster.cluster_id,
        distance_km=round(distance, 3),
        fit_score=fit,
        informational_only=fit < fit_threshold,
    )


__all__ = [
    "ClusterAssignment",
    "ClusterCandidate",
    "PlotForClustering",
    "assign_cluster",
    "haversine_km",
]
