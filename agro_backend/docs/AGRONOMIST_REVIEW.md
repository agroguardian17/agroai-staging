# Agronomist review — value choices to confirm

These defaults were applied so the KB fields flow now; each needs the agronomy
team's sign-off. All live in `app/application/build_farm_brain.py` unless noted.
Change = one edit to the named constant/map, no schema change.

| # | Field(s) | Choice applied | Where | Risk if wrong |
|---|---|---|---|---|
| 1 | `soil_type` | DB `black→vertisol, loamy→loam, sandy→sandy_loam, red→laterite, mixed→other` | `_SOIL_TYPE_MAP` | `red→laterite` is the doubtful one — many red soils are red loams, not laterite. |
| 2 | `soil_texture_class` | `black→heavy, loamy→medium, sandy→light, red/mixed→medium` (derived from soil_type) | `_SOIL_TEXTURE_CLASS_MAP` | Coarse; a lab texture (sand/silt/clay %) would be exact. |
| 3 | `agro_climatic_zone` | District→Marathwada zone (Ch. Sambhajinagar/Jalna/Beed→central; Dharashiv/Osmanabad→western; Latur/Nanded/Parbhani/Hingoli→eastern) | `_AGRO_ZONE` | Zone boundaries are approximate; confirm/extend the district list. |
| 4 | `prediction_stage` | DAP cut-points: `<0 pre_season, <90 g1_end, <200 mid_season, else pre_harvest_observation` | `_prediction_stage` | Stage timing is variety/season dependent. |
| 5 | `phi_days_remaining` | PHI-days per pesticide group (mancozeb 7, copper 5, chlorpyriphos 14, imidacloprid 40, …); **default 21** for anything unlisted | `_PHI_DAYS_BY_GROUP` | **Food safety.** Default errs long (restrictive). Confirm the per-chemical PHI table and the group codes farmers actually enter. |
| 6 | `rainfall_deviation_pct` | vs an agro-zone **seasonal normal** (western 750 / central 680 / eastern 820 mm) prorated by DAP over a 240-day season | `_ZONE_SEASON_RAIN_MM`, `_SEASON_LEN_DAYS` | Placeholder normals — replace with real **IMD district normals**. |
| 7 | `cyclone_alert_active` | **Proxy** from the forecast: any of the next 3 days with wind ≥ 60 km/h **and** rain ≥ 50 mm | `_cyclone_alert` | Not an official IMD cyclone warning; a severe-weather heuristic. |
| 8 | `vafsa_state` | too_wet ≥ `vwc_saturation`, too_dry ≤ `vwc_stress_threshold`, else workable | `_derive_composite` | Uses the **season's own** entered thresholds — no hardcoded agronomy; just confirm those thresholds are entered per plot. |
| 9 | `stage_source` | constant `"calendar"` (we stage by DAP) | `_populate_from_season` | Correct as long as staging stays calendar-based (not GDD/marker). |

## How to confirm
For each row: either "OK as-is" or give the corrected value/map. I'll apply it
in one commit. Item 5 (PHI) and item 6 (rainfall normals) are the two worth
prioritising — PHI for food safety, normals for D07 accuracy.
