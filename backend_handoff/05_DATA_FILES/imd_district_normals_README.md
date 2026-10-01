# IMD District Normals — Marathwada + pilot expansion

**File:** `imd_district_normals_1991_2020.csv`
**Date:** 2026-09-23
**Owner:** Kuldip — Agronomy Compliance Owner

## Source & confidence

- **Source institution:** India Meteorological Department, Pune — Climatological Tables 1991–2020
- **Aurangabad (Chikalthana) row: CONFIRMED** — 811.7 mm annual, monthly values from AG-V2.0 §4 scientific validation document
- **All other rows: PROVISIONAL** — annual district normals from widely-cited IMD sources; monthly distribution proportioned from Chikalthana seasonality until per-station monthly tables are fetched from IMD Pune

## Usage

Backend loads this as `_STATION_RAINFALL_NORMAL` keyed by station_name. Plots
map to nearest station by district. Every stored value carries its full
metadata block (source, period, method, scope, verification_status) — never
strip these fields when caching or displaying.

## Verification workflow

Rows tagged `PROVISIONAL_pending_IMD_station_confirmation` should be
replaced with actual IMD Pune station monthlies as I fetch them. Update
`verification_status` to `CONFIRMED_via_IMD_Pune_YYYY-MM-DD` per row on
update.

## Coverage

- **Marathwada (primary):** Chhatrapati Sambhajinagar, Jalna, Beed, Dharashiv,
  Latur, Nanded, Parbhani, Hingoli (8 districts)
- **Pilot expansion:** Nashik, Ahmadnagar, Solapur (3 districts)

## Compliance notes

- No value in this file is fabricated. Chikalthana is the confirmed anchor;
  others are provisional and marked as such.
- Rainfall values are annual and monthly mm.
- Latitude/longitude are district-centre approximations, not station GPS.
- For the plot polygon → station mapping, use nearest-station by great-circle
  distance from the district-centre coordinates.
