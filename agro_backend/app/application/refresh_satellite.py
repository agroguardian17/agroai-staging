"""Use case: refresh satellite indices for every active ginger plot.

The satellite cron job calls this: for each active ginger season whose plot has
a boundary polygon, fetch recent Sentinel-2 (optical) and Sentinel-1 (SAR)
observations and upsert one ``satellite_data`` row per scene. A plot without a
polygon is skipped (D14-PL-001 keeps its D14 rules dormant); one plot's failure
never aborts the sweep.

PURE w.r.t. imports: stdlib + ports only. No infra.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.application.ports.crop_season_repo import CropSeasonRepo
from app.application.ports.plot_repo import PlotRepo
from app.application.ports.satellite_provider import (
    OpticalObservation,
    SarObservation,
    SatelliteProvider,
)
from app.application.ports.satellite_reading_repo import (
    SOURCE_OPTICAL,
    SOURCE_SAR,
    SatelliteReadingRepo,
    SatelliteScene,
)

GINGER_CROP_NAME = "Ginger"


@dataclass(frozen=True, slots=True)
class RefreshSatelliteDeps:
    crop_season_repo: CropSeasonRepo
    plot_repo: PlotRepo
    satellite_provider: SatelliteProvider
    satellite_reading_repo: SatelliteReadingRepo
    crop_name: str = GINGER_CROP_NAME
    lookback_days: int = 20
    pipeline_version: str = "cdse-sh-1.0"


@dataclass(frozen=True, slots=True)
class RefreshSatelliteResult:
    plots: int
    skipped_no_polygon: int
    optical_scenes: int
    sar_scenes: int
    failed_plots: int


def _dec(v: float | None) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def _optical_scene(o: OpticalObservation, pipeline_version: str) -> SatelliteScene:
    return SatelliteScene(
        image_date=o.image_date,
        satellite_source=SOURCE_OPTICAL,
        ndvi_mean=_dec(o.ndvi_mean),
        ndvi_std=_dec(o.ndvi_std),
        ndre_mean=_dec(o.ndre_mean),
        ndmi_mean=_dec(o.ndmi_mean),
        evi_mean=_dec(o.evi_mean),
        savi_mean=_dec(o.savi_mean),
        nbr_value=_dec(o.nbr_value),
        cloud_cover_pct=_dec(o.cloud_cover_pct),
        valid_pixel_pct=_dec(o.valid_pixel_pct),
        pipeline_version=pipeline_version,
    )


def _sar_scene(s: SarObservation, pipeline_version: str) -> SatelliteScene:
    return SatelliteScene(
        image_date=s.image_date,
        satellite_source=SOURCE_SAR,
        sar_vv_db=_dec(s.sar_vv_db),
        sar_vh_db=_dec(s.sar_vh_db),
        pipeline_version=pipeline_version,
    )


async def execute(*, deps: RefreshSatelliteDeps, today: date) -> RefreshSatelliteResult:
    seasons = await deps.crop_season_repo.list_active_by_crop(deps.crop_name)
    date_from = today - timedelta(days=deps.lookback_days)
    plots = skipped = optical_n = sar_n = failed = 0

    for season in seasons:
        plots += 1
        plot = await deps.plot_repo.find(season.plot_id)
        geometry = plot.gps_boundary_geojson if plot is not None else None
        if not geometry:
            skipped += 1
            continue
        try:
            optical = await deps.satellite_provider.optical(
                geometry=geometry, date_from=date_from, date_to=today
            )
            sar = await deps.satellite_provider.sar(
                geometry=geometry, date_from=date_from, date_to=today
            )
        except Exception:
            failed += 1
            continue

        for o in optical:
            await deps.satellite_reading_repo.save(
                tenant_id=season.tenant_id,
                farm_id=season.farm_id,
                plot_id=season.plot_id,
                scene=_optical_scene(o, deps.pipeline_version),
            )
            optical_n += 1
        for s in sar:
            await deps.satellite_reading_repo.save(
                tenant_id=season.tenant_id,
                farm_id=season.farm_id,
                plot_id=season.plot_id,
                scene=_sar_scene(s, deps.pipeline_version),
            )
            sar_n += 1

    return RefreshSatelliteResult(
        plots=plots,
        skipped_no_polygon=skipped,
        optical_scenes=optical_n,
        sar_scenes=sar_n,
        failed_plots=failed,
    )


__all__ = ["RefreshSatelliteDeps", "RefreshSatelliteResult", "execute"]
