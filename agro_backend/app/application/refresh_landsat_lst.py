"""Use case: refresh Landsat land-surface temperature for every active plot.

For each active ginger season whose plot has a boundary polygon, fetch recent
Landsat LST observations and upsert one ``satellite_data`` ``landsat8`` row per
overpass (``lst_c`` set). The farm-brain reads the latest ``lst_c`` and derives
``cwsi``. A plot without a polygon is skipped; one plot's failure never aborts
the sweep.

PURE w.r.t. imports: stdlib + ports only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.application.ports.crop_season_repo import CropSeasonRepo
from app.application.ports.lst_provider import LstError, LstProvider
from app.application.ports.plot_repo import PlotRepo
from app.application.ports.satellite_reading_repo import (
    SOURCE_THERMAL,
    SatelliteReadingRepo,
    SatelliteScene,
)

GINGER_CROP_NAME = "Ginger"


@dataclass(frozen=True, slots=True)
class RefreshLandsatDeps:
    crop_season_repo: CropSeasonRepo
    plot_repo: PlotRepo
    lst_provider: LstProvider
    satellite_reading_repo: SatelliteReadingRepo
    crop_name: str = GINGER_CROP_NAME
    lookback_days: int = 20
    pipeline_version: str = "usgs-m2m-lst-1.0"


@dataclass(frozen=True, slots=True)
class RefreshLandsatResult:
    plots: int
    skipped_no_polygon: int
    scenes: int
    failed_plots: int


def _dec(v: float | None) -> Decimal | None:
    return None if v is None else Decimal(str(v))


async def execute(*, deps: RefreshLandsatDeps, today: date) -> RefreshLandsatResult:
    seasons = await deps.crop_season_repo.list_active_by_crop(deps.crop_name)
    date_from = today - timedelta(days=deps.lookback_days)
    plots = skipped = scenes = failed = 0
    seen_plots: set[str] = set()
    for season in seasons:
        if season.plot_id in seen_plots:
            continue
        seen_plots.add(season.plot_id)
        plots += 1
        plot = await deps.plot_repo.find(season.plot_id)
        boundary = getattr(plot, "gps_boundary_geojson", None) if plot else None
        if not boundary:
            skipped += 1
            continue
        try:
            observations = await deps.lst_provider.lst_for_polygon(
                geometry=boundary, date_from=date_from, date_to=today
            )
        except (LstError, Exception):
            failed += 1
            continue
        for obs in observations:
            if obs.lst_c is None:
                continue
            await deps.satellite_reading_repo.save(
                tenant_id=season.tenant_id,
                farm_id=season.farm_id,
                plot_id=season.plot_id,
                scene=SatelliteScene(
                    image_date=obs.image_date,
                    satellite_source=SOURCE_THERMAL,
                    lst_c=_dec(obs.lst_c),
                    cloud_cover_pct=_dec(obs.cloud_cover_pct),
                    pipeline_version=deps.pipeline_version,
                ),
            )
            scenes += 1
    return RefreshLandsatResult(
        plots=plots, skipped_no_polygon=skipped, scenes=scenes, failed_plots=failed
    )


__all__ = ["RefreshLandsatDeps", "RefreshLandsatResult", "execute"]
