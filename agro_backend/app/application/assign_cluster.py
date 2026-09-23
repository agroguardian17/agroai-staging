"""D12 use-case: assign a plot to a peer cluster (D12_QA_WORKFLOW §4.6, §5.3).

Runs at plot enrollment (and on demand, e.g. after a variety change). Resolves
the plot's clustering inputs — variety and planting date from the active crop
season, centroid from the plot's GPS point — loads the tenant's active clusters
and the ``cluster_config`` knobs, runs the pure gating algorithm, and persists
the outcome. Returns the resolved cluster id (existing or freshly spawned).

Pure orchestration: the decision lives in :func:`app.domain.clustering.assign_cluster`;
the writes live in :class:`app.application.ports.cluster_repo.ClusterRepo`.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.cluster_repo import ClusterRepo
from app.application.ports.crop_season_repo import CropSeasonRepo
from app.application.ports.plot_repo import PlotRepo
from app.domain.clustering import PlotForClustering, assign_cluster


@dataclass(frozen=True, slots=True)
class ClusterAssignmentResult:
    plot_id: str
    cluster_id: str
    spawned: bool
    distance_km: float | None
    fit_score: float
    informational_only: bool


class PlotNotClusterableError(Exception):
    """The plot lacks a GPS centroid or an active season with a variety."""


def _int(config: dict[str, str], key: str, default: int) -> int:
    try:
        return int(config[key])
    except (KeyError, ValueError):
        return default


def _float(config: dict[str, str], key: str, default: float) -> float:
    try:
        return float(config[key])
    except (KeyError, ValueError):
        return default


async def assign_plot_to_cluster(
    *,
    plot_id: str,
    plot_repo: PlotRepo,
    crop_season_repo: CropSeasonRepo,
    cluster_repo: ClusterRepo,
) -> ClusterAssignmentResult:
    """Assign ``plot_id`` to its nearest fitting cluster, or spawn a new one."""
    plot = await plot_repo.find(plot_id)
    if plot is None or plot.gps_lat is None or plot.gps_lng is None:
        raise PlotNotClusterableError(f"plot {plot_id} has no GPS centroid")

    season = await crop_season_repo.find_active_for_plot(plot_id)
    if season is None or not season.crop_variety:
        raise PlotNotClusterableError(f"plot {plot_id} has no active season with a variety")

    inputs = PlotForClustering(
        variety=season.crop_variety,
        planting_week=season.sowing_date,
        centroid_lat=float(plot.gps_lat),
        centroid_lng=float(plot.gps_lng),
    )

    config = await cluster_repo.load_config()
    candidates = await cluster_repo.load_active(season.tenant_id)

    decision = assign_cluster(
        inputs,
        candidates,
        variety_gate=config.get("variety_gate", "strict"),
        max_plots_per_cluster=_int(config, "max_plots_per_cluster", 12),
        proximity_km=_float(config, "proximity_km", 3.0),
        planting_week_bucket_days=_int(config, "planting_week_bucket_days", 7),
    )

    final_id = await cluster_repo.persist_assignment(
        tenant_id=season.tenant_id,
        plot_id=plot_id,
        plot=inputs,
        chosen_cluster_id=decision.cluster_id,
        distance_km=decision.distance_km,
        fit_score=decision.fit_score,
        informational_only=decision.informational_only,
    )

    return ClusterAssignmentResult(
        plot_id=plot_id,
        cluster_id=final_id,
        spawned=decision.cluster_id is None,
        distance_km=decision.distance_km,
        fit_score=decision.fit_score,
        informational_only=decision.informational_only,
    )


__all__ = ["ClusterAssignmentResult", "PlotNotClusterableError", "assign_plot_to_cluster"]
