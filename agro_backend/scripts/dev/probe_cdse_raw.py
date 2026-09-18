"""Diagnostic: dump the RAW CDSE Statistical API response for the pilot plot.

Temporary tool to verify the live Sentinel Hub response shape against the
adapter's parser. Prints the number of intervals and the first couple of raw
items (the per-interval ``outputs`` structure) so the parser can be matched
exactly. Safe/read-only — it fetches statistics, writes nothing.

    docker compose -f docker-compose.prod.yml exec -T app \
        python - < scripts/dev/probe_cdse_raw.py
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta

import httpx

from app.config import get_settings
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_plot_repo import PgPlotRepo
from app.infra.satellite.cdse_provider import (
    _S1_EVALSCRIPT,
    _S2_EVALSCRIPT,
    CdseSentinelHubProvider,
    CdseSettings,
)

_PLOT = "PLOT_PILOT_001"


async def _main() -> int:
    settings = get_settings()
    if (
        not settings.COPERNICUS_CLIENT_ID
        or not settings.COPERNICUS_CLIENT_SECRET.get_secret_value()
    ):
        print("ERROR: COPERNICUS_CLIENT_ID / COPERNICUS_CLIENT_SECRET are not set.")
        return 2

    sm = _ensure_engine(settings)
    plot = await PgPlotRepo(sm).find(_PLOT)
    if plot is None or not plot.gps_boundary_geojson:
        print(f"ERROR: {_PLOT} has no gps_boundary_geojson.")
        return 2
    geometry = plot.gps_boundary_geojson

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
    today = datetime.now(UTC).date()
    date_from = today - timedelta(days=20)

    try:
        for label, data_type, data_filter, evalscript in (
            ("S2", "sentinel-2-l2a", {"mosaickingOrder": "leastCC"}, _S2_EVALSCRIPT),
            (
                "S1",
                "sentinel-1-grd",
                {"acquisitionMode": "IW", "polarization": "DV"},
                _S1_EVALSCRIPT,
            ),
        ):
            payload = provider._payload(
                data_type=data_type,
                data_filter=data_filter,
                evalscript=evalscript,
                geometry=geometry,
                date_from=date_from,
                date_to=today,
            )
            print(f"\n================ {label} ({data_type}) ================")
            try:
                data = await provider._statistics(payload)
            except Exception as exc:
                print(f"{label} request failed: {exc!r}")
                continue
            print(f"intervals returned: {len(data)}")
            for i, item in enumerate(data[:3]):
                print(f"--- item[{i}] ---")
                print(json.dumps(item, indent=2)[:4000])
    finally:
        await client.aclose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
