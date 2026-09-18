"""One-shot satellite fetch for live verification (dev/ops).

Runs ``refresh_satellite.execute`` a single time against the real CDSE Sentinel
Hub API, so you can pull scenes immediately after provisioning instead of
waiting for the 2:30 AM cron. Fetches every active ginger plot that has a
boundary polygon (plots without one are skipped, exactly like the cron).

Run it inside the app container (it has the app settings + DB access):

    docker compose -f docker-compose.prod.yml exec -T app \
        python - < scripts/dev/fetch_satellite_once.py

Prerequisites (same as enabling the cron):
  - COPERNICUS_CLIENT_ID / COPERNICUS_CLIENT_SECRET set in the app env
  - at least one active ginger plot with plots.gps_boundary_geojson populated

It does NOT require SATELLITE_JOB_ENABLED=true — that flag only gates the cron;
this script fetches on demand regardless, which is the point for verification.
Prints the per-run summary (plots / skipped / optical / sar / failed).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx

from app.application import refresh_satellite
from app.application.refresh_satellite import RefreshSatelliteDeps
from app.config import get_settings
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_crop_season_repo import PgCropSeasonRepo
from app.infra.persistence.pg_plot_repo import PgPlotRepo
from app.infra.persistence.pg_satellite_reading_repo import PgSatelliteReadingRepo
from app.infra.satellite.cdse_provider import CdseSentinelHubProvider, CdseSettings


async def _main() -> int:
    settings = get_settings()
    if (
        not settings.COPERNICUS_CLIENT_ID
        or not settings.COPERNICUS_CLIENT_SECRET.get_secret_value()
    ):
        print("ERROR: COPERNICUS_CLIENT_ID / COPERNICUS_CLIENT_SECRET are not set in the app env.")
        print("Provision a CDSE OAuth client and set them before running this.")
        return 2

    sm = _ensure_engine(settings)
    client = httpx.AsyncClient(timeout=30.0)
    provider = CdseSentinelHubProvider(
        CdseSettings(
            client_id=settings.COPERNICUS_CLIENT_ID,
            client_secret=settings.COPERNICUS_CLIENT_SECRET.get_secret_value(),
            base_url=settings.COPERNICUS_BASE_URL,
            token_url=settings.COPERNICUS_TOKEN_URL,
        ),
        client=client,
    )
    deps = RefreshSatelliteDeps(
        crop_season_repo=PgCropSeasonRepo(sm),
        plot_repo=PgPlotRepo(sm),
        satellite_provider=provider,
        satellite_reading_repo=PgSatelliteReadingRepo(sm),
        lookback_days=settings.SATELLITE_LOOKBACK_DAYS,
        pipeline_version=settings.SATELLITE_PIPELINE_VERSION,
    )
    try:
        res = await refresh_satellite.execute(deps=deps, today=datetime.now(UTC).date())
    finally:
        await client.aclose()

    print(
        "satellite fetch complete: "
        f"plots={res.plots} skipped_no_polygon={res.skipped_no_polygon} "
        f"optical_scenes={res.optical_scenes} sar_scenes={res.sar_scenes} "
        f"failed_plots={res.failed_plots}"
    )
    if res.plots and res.skipped_no_polygon == res.plots:
        print("NOTE: every plot was skipped — populate plots.gps_boundary_geojson first.")
    if res.failed_plots:
        print("NOTE: some plots failed — check app logs for CDSE errors (auth / quota / shape).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
