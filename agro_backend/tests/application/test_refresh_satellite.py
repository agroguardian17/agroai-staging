"""Use-case tests for refresh_satellite (fakes, no network/DB)."""

from __future__ import annotations

import datetime
import uuid

import pytest

from app.application import refresh_satellite
from app.application.ports.satellite_provider import OpticalObservation, SarObservation
from app.application.refresh_satellite import RefreshSatelliteDeps
from app.domain.plot import Plot

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_FARM = uuid.UUID("bbbbbbbb-2222-2222-2222-222222222222")
_TODAY = datetime.date(2026, 8, 3)


class _Season:
    def __init__(self, plot_id: str) -> None:
        self.plot_id = plot_id
        self.tenant_id = _TENANT
        self.farm_id = _FARM


class _FakeSeasonRepo:
    def __init__(self, plot_ids: list[str]) -> None:
        self._ids = plot_ids

    async def list_active_by_crop(self, crop):
        return [_Season(pid) for pid in self._ids]


def _plot(plot_id: str, *, boundary: dict | None):
    return Plot(
        plot_id=plot_id,
        tenant_id=_TENANT,
        farm_id=_FARM,
        plot_number=1,
        area_acre=__import__("decimal").Decimal("1.0"),
        gps_lat=20.1,
        gps_lng=75.2,
        irrigation_valve_id="V1",
        data_tier="full",
        plot_status="active",
        gps_boundary_geojson=boundary,
    )


class _FakePlotRepo:
    def __init__(self, plots: dict) -> None:
        self._plots = plots

    async def find(self, plot_id):
        return self._plots.get(plot_id)


class _FakeProvider:
    async def optical(self, *, geometry, date_from, date_to):
        return [
            OpticalObservation(
                image_date=_TODAY - datetime.timedelta(days=3),
                ndvi_mean=0.55,
                ndvi_std=0.05,
                ndre_mean=0.3,
                ndmi_mean=0.4,
                evi_mean=1.2,
                savi_mean=0.5,
                nbr_value=0.2,
                cloud_cover_pct=10.0,
                valid_pixel_pct=90.0,
            )
        ]

    async def sar(self, *, geometry, date_from, date_to):
        return [
            SarObservation(
                image_date=_TODAY - datetime.timedelta(days=4), sar_vv_db=-9.5, sar_vh_db=-15.2
            )
        ]


class _FakeSatRepo:
    def __init__(self) -> None:
        self.saved: list[tuple[str, str]] = []

    async def save(self, *, tenant_id, farm_id, plot_id, scene):
        self.saved.append((plot_id, scene.satellite_source))

    async def recent(self, plot_id, satellite_source, limit):  # pragma: no cover
        return []


@pytest.mark.asyncio
async def test_fetches_and_saves_for_plot_with_polygon() -> None:
    geom = {
        "type": "Polygon",
        "coordinates": [[[75.2, 20.1], [75.21, 20.1], [75.21, 20.11], [75.2, 20.1]]],
    }
    repo = _FakeSatRepo()
    deps = RefreshSatelliteDeps(
        crop_season_repo=_FakeSeasonRepo(["PLOT_PILOT_001"]),
        plot_repo=_FakePlotRepo({"PLOT_PILOT_001": _plot("PLOT_PILOT_001", boundary=geom)}),
        satellite_provider=_FakeProvider(),
        satellite_reading_repo=repo,
    )
    res = await refresh_satellite.execute(deps=deps, today=_TODAY)
    assert res.plots == 1
    assert res.skipped_no_polygon == 0
    assert res.optical_scenes == 1
    assert res.sar_scenes == 1
    assert ("PLOT_PILOT_001", "sentinel2") in repo.saved
    assert ("PLOT_PILOT_001", "sentinel1") in repo.saved


@pytest.mark.asyncio
async def test_skips_plot_without_polygon() -> None:
    repo = _FakeSatRepo()
    deps = RefreshSatelliteDeps(
        crop_season_repo=_FakeSeasonRepo(["PLOT_NO_GEOM"]),
        plot_repo=_FakePlotRepo({"PLOT_NO_GEOM": _plot("PLOT_NO_GEOM", boundary=None)}),
        satellite_provider=_FakeProvider(),
        satellite_reading_repo=repo,
    )
    res = await refresh_satellite.execute(deps=deps, today=_TODAY)
    assert res.plots == 1
    assert res.skipped_no_polygon == 1
    assert res.optical_scenes == 0
    assert repo.saved == []
