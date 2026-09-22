#!/usr/bin/env python3
"""Live smoke check for the USGS M2M LST adapter (credential-gated).

Runs the real login -> scene-search -> download-resolve -> raster read against
the USGS M2M API for a sample plot box and a recent date window, printing the
resolved land-surface-temperature observations. This is the ops-side
verification the unit tests cannot do: they mock the HTTP transport and read a
local GeoTIFF, so the live API + a real Landsat scene stay unverified until this
runs with credentials.

Usage (inside the app container, where the credentials live):

    docker compose exec app python scripts/dev/lst_smoke.py

Env (required):
    USGS_M2M_USERNAME   USGS ERS account username
    USGS_M2M_TOKEN      USGS M2M application token

Options:
    --days N            look-back window in days (default 30)
    --lng / --lat       plot centre (default a Kannad, Marathwada point)
    --half D            half-side of the sample box in degrees (default 0.01)

Exit codes: 0 success (scenes found or a clean no-scene result), 1 adapter
error, 2 skipped (credentials absent).
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import os


def main() -> int:
    username = os.environ.get("USGS_M2M_USERNAME")
    token = os.environ.get("USGS_M2M_TOKEN")
    if not username or not token:
        print("SKIP: set USGS_M2M_USERNAME and USGS_M2M_TOKEN to run the live check.")
        return 2

    parser = argparse.ArgumentParser(description="USGS M2M LST live smoke check.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--lng", type=float, default=75.32)
    parser.add_argument("--lat", type=float, default=20.01)
    parser.add_argument("--half", type=float, default=0.01)
    args = parser.parse_args()

    # Imported here so --help / the SKIP path do not require the app deps.
    from app.infra.lst.usgs_m2m import UsgsM2mLstProvider, UsgsM2mSettings

    d = args.half
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                [args.lng - d, args.lat - d],
                [args.lng + d, args.lat - d],
                [args.lng + d, args.lat + d],
                [args.lng - d, args.lat + d],
                [args.lng - d, args.lat - d],
            ]
        ],
    }
    today = datetime.date.today()
    date_from = today - datetime.timedelta(days=args.days)

    async def run() -> int:
        provider = UsgsM2mLstProvider(UsgsM2mSettings(username=username, token=token))
        print(
            f"Querying USGS M2M for box around ({args.lng}, {args.lat}) "
            f"from {date_from} to {today} ..."
        )
        try:
            observations = await provider.lst_for_polygon(
                geometry=geometry, date_from=date_from, date_to=today
            )
        except Exception as exc:  # a smoke script reports any failure verbatim
            print(f"FAIL: {type(exc).__name__}: {exc}")
            return 1
        if not observations:
            print(f"OK (no scenes): no Landsat ST scenes for the box in the last {args.days} days.")
            return 0
        print(f"OK: {len(observations)} scene(s):")
        for obs in observations:
            print(f"  {obs.image_date}  lst_c={obs.lst_c}  cloud={obs.cloud_cover_pct}%")
        return 0

    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
