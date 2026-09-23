"""D12 use-case: assign a plot to a peer cluster."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from app.application.assign_cluster import (
    PlotNotClusterableError,
    assign_plot_to_cluster,
)
from app.domain.clustering import ClusterCandidate, PlotForClustering

_TENANT = uuid.uuid4()
_WEEK = date(2026, 6, 15)


class _FakePlotRepo:
    def __init__(self, plot: Any) -> None:
        self._plot = plot

    async def find(self, plot_id: str) -> Any:
        return self._plot


class _FakeSeasonRepo:
    def __init__(self, season: Any) -> None:
        self._season = season

    async def find_active_for_plot(self, plot_id: str) -> Any:
        return self._season


@dataclass
class _Persisted:
    chosen_cluster_id: str | None
    plot: PlotForClustering
    fit_score: float
    informational_only: bool


class _FakeClusterRepo:
    def __init__(self, active: list[ClusterCandidate]) -> None:
        self._active = active
        self.calls: list[_Persisted] = []

    async def load_config(self) -> dict[str, str]:
        return {}

    async def load_active(self, tenant_id: uuid.UUID) -> list[ClusterCandidate]:
        return self._active

    async def cluster_id_for_plot(self, plot_id: str) -> str | None:
        return None

    async def persist_assignment(
        self,
        *,
        tenant_id: uuid.UUID,
        plot_id: str,
        plot: PlotForClustering,
        chosen_cluster_id: str | None,
        distance_km: float | None,
        fit_score: float,
        informational_only: bool,
    ) -> str:
        self.calls.append(_Persisted(chosen_cluster_id, plot, fit_score, informational_only))
        return chosen_cluster_id if chosen_cluster_id is not None else "CL-newlyminted"


def _plot(lat: float = 19.86, lng: float = 75.40) -> Any:
    return SimpleNamespace(gps_lat=lat, gps_lng=lng)


def _season(variety: str = "IISR Mahima", week: date = _WEEK) -> Any:
    return SimpleNamespace(tenant_id=_TENANT, crop_variety=variety, sowing_date=week)


def _candidate(cid: str, *, lat: float = 19.861, lng: float = 75.401) -> ClusterCandidate:
    return ClusterCandidate(
        cluster_id=cid,
        variety="IISR Mahima",
        planting_week_median=_WEEK,
        centroid_lat=lat,
        centroid_lng=lng,
        plot_count=3,
    )


async def _run(
    plot: Any, season: Any, active: list[ClusterCandidate]
) -> tuple[Any, _FakeClusterRepo]:
    repo = _FakeClusterRepo(active)
    res = await assign_plot_to_cluster(
        plot_id="P1",
        plot_repo=_FakePlotRepo(plot),  # type: ignore[arg-type]
        crop_season_repo=_FakeSeasonRepo(season),  # type: ignore[arg-type]
        cluster_repo=repo,  # type: ignore[arg-type]
    )
    return res, repo


@pytest.mark.asyncio
async def test_spawns_when_no_active_clusters() -> None:
    res, repo = await _run(_plot(), _season(), [])
    assert res.spawned is True
    assert res.cluster_id == "CL-newlyminted"
    assert repo.calls[0].chosen_cluster_id is None  # domain said spawn


@pytest.mark.asyncio
async def test_joins_nearest_matching_cluster() -> None:
    res, repo = await _run(_plot(), _season(), [_candidate("C_near")])
    assert res.spawned is False
    assert res.cluster_id == "C_near"
    assert res.fit_score > 0.6
    assert repo.calls[0].chosen_cluster_id == "C_near"


@pytest.mark.asyncio
async def test_variety_mismatch_spawns_under_strict_gate() -> None:
    res, _ = await _run(_plot(), _season(variety="IISR Varada"), [_candidate("C1")])
    assert res.spawned is True  # strict gate excludes the mismatched cluster


@pytest.mark.asyncio
async def test_missing_gps_raises() -> None:
    with pytest.raises(PlotNotClusterableError):
        await _run(_plot(lat=None), _season(), [])  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_missing_season_raises() -> None:
    with pytest.raises(PlotNotClusterableError):
        await _run(_plot(), None, [])
