# KB ↔ DB Field Mapping Specification

**Generated:** 2026-09-19 · **Status:** review draft · **Owner:** backend

The single source of truth for wiring every Ginger-KB field to a database home. The knowledge base is **frozen** — all reconciliation happens in the DB schema and in the mapper [`app/application/build_farm_brain.py`](../app/application/build_farm_brain.py). The engine reads a `farm_brain` dict keyed by `kb_farm_brain_fields`; the mapper is the **only** place DB columns become KB field names, so KB and column names may legitimately differ as long as the mapper bridges them.

## How this was derived

- KB field vocabulary + per-rule usage: `kb_farm_brain_fields` / `kb_rule_fields` in `ginger/generated/agroguardian_ginger_kb*.sql`.
- DB columns: SQLAlchemy metadata over `app/infra/persistence/models/` (39 tables, 597 cols).
- Current mapper coverage: parsed from `build_farm_brain.py`.
- **KB integrity:** 0 fields are used-but-undeclared — no conflicts inside the KB.

## Summary

| Status | Fields | Action |
|---|---:|---|
| **Mapped/derived today** | 40 | none — already bridged |
| **Exact same-name column** | 8 | Phase 1: wire in mapper |
| **Differently-named column** | 11 | Phase 1: map in mapper |
| **No DB home** | 287 | Phase 2/3: new schema + adapters |
| **Total KB-used fields** | 346 | |

Naming rule for all new work: **name every new column identically to its KB field.** Do **not** rename existing columns (breaks ORM/domain/queries for no functional gain — the mapper already reconciles names).

## 1. Already mapped / derived — no change (40)

Bridged by the mapper today. (Live data depends on the source existing: satellite + season flow now; sensor + weather need the hardware/rollups.)

| KB field | DB source (via mapper) | Type |
|---|---|---|
| `air_temp_max_c` | weather_station_readings.air_temp_max_c | number |
| `air_temp_min_c` | weather_station_readings.air_temp_min_c | number |
| `current_stage` | crop_seasons.current_growth_stage | enum:stage_codes |
| `dap` | DERIVED — dap | integer, computed |
| `days_to_planting` | crop_seasons (computed from sowing/harvest date vs today) | integer — days from today to the plot's planne… |
| `dew_point_c` | weather_station_readings.dew_point_c | number |
| `ec_current` | node_sensor_readings.soil_ec_ms_cm | number |
| `evi_mean` | satellite_data (optical).evi_mean | number — enhanced vegetation index; used where… |
| `nbr_delta_10d` | DERIVED — index_delta(o.nbr_value, prev10.nbr_value | number — NBR change over the last 10 days |
| `nbr_mean` | satellite_data (optical).nbr_value | number — normalized burn ratio; residue burnin… |
| `ndmi_delta_10d` | DERIVED — index_delta(o.ndmi_mean, prev10.ndmi_mean | number — NDMI change over the last 10 days |
| `ndmi_mean` | satellite_data (optical).ndmi_mean | number — mean NDMI canopy moisture index |
| `ndre_mean` | satellite_data (optical).ndre_mean | number — mean NDRE red-edge chlorophyll index |
| `ndre_slope_5d` | DERIVED — d / Decimal(days | number — NDRE trend over last 5 days (per day) |
| `ndvi_delta_10d` | DERIVED — index_delta(o.ndvi_mean, prev10.ndvi_mean | number — NDVI change over the last 10 days (po… |
| `ndvi_freshness_days` | DERIVED — fresh | integer — age of ndvi_mean in days; used to de… |
| `ndvi_mean` | satellite_data (optical).ndvi_mean | number — mean NDVI over valid pixels in the mo… |
| `ndvi_std` | satellite_data (optical).ndvi_std | number — standard deviation of NDVI across the… |
| `optical_gap_days` | DERIVED — fresh | integer — days since the last cloud-clear Sent… |
| `plot_area_ha` | DERIVED — acre_to_hectare(plot.area_acre | number — plot area in hectares, derived from p… |
| `plot_cloud_pct` | satellite_data (optical).cloud_cover_pct | number — cloud percentage over the plot polygo… |
| `plot_ndvi_baseline_regional` | DERIVED — base | number — regional expected NDVI for the curren… |
| `plot_ndvi_gap_regional` | DERIVED — baseline_gap(o.ndvi_mean, base | number — signed difference plot NDVI minus reg… |
| `plot_polygon_wkt` | DERIVED — _geojson_polygon_to_wkt(plot.gps_boundary_geojson | text — plot boundary as Well-Known Text; the g… |
| `rh_pct` | weather_station_readings.humidity_pct | number |
| `sar_coherence` | satellite_data (SAR).sar_coherence | number — InSAR coherence between last two same… |
| `sar_gap_days` | DERIVED — (today - s.image_date | integer — days since the last Sentinel-1 acqui… |
| `sar_rvi` | DERIVED — rvi | number — radar vegetation index, 4*VH/(VV+VH) |
| `sar_vh_db` | satellite_data (SAR).sar_vh_db | number — Sentinel-1 sigma-nought VH in dB |
| `sar_vv_db` | satellite_data (SAR).sar_vv_db | number — Sentinel-1 sigma-nought VV in dB |
| `sar_vv_delta_db` | DERIVED — index_delta(s.sar_vv_db, prev_sar.sar_vv_db | number — change in VV between last two acquisi… |
| `sat_advisory_confidence` | DERIVED — advisory_confidence_from_freshness(fresh | number — confidence in [0,1] the current satel… |
| `sat_pipeline_version` | satellite_data (optical).pipeline_version | text — version tag of the processing chain tha… |
| `sat_source` | satellite_data (optical).satellite_source | text — enum: sentinel-2, sentinel-1, landsat-8… |
| `savi_mean` | satellite_data (optical).savi_mean | number — soil-adjusted NDVI; used in G0 and ea… |
| `scene_valid_pixel_pct` | satellite_data (optical).valid_pixel_pct | number — percentage of plot pixels that are ne… |
| `soil_moisture_vwc` | node_sensor_readings.soil_moisture_avg_pct | number |
| `soil_ph` | node_sensor_readings.soil_ph | number |
| `soil_temp_c` | node_sensor_readings.soil_temp_c | number |
| `vpd_kpa` | DERIVED — vpd_kpa(w.air_temp_max_c, w.humidity_pct | number — vapour pressure deficit in kilopascal… |

## 2. Phase 1a — exact same-name column, wire only (8)

Column already exists with the same name; add a `_set` in the mapper. No schema change.

| KB field | DB column | Type | Rules |
|---|---|---|---:|
| `area_acre` | `plots.area_acre` | number | 20 |
| `district` | `farmers.district` | string | 2 |
| `farmer_id` | `farmers.farmer_id` | string | 2 |
| `plot_id` | `crop_seasons.plot_id` | string | 1 |
| `seed_cost_per_kg` | `crop_seasons.seed_cost_per_kg` | number | 2 |
| `soil_depth_cm` | `farms.soil_depth_cm` | number | 1 |
| `soil_type` | `farms.soil_type` | enum:[vertisol, loam, sandy_loam, laterite, ot… | 3 |
| `taluka` | `farmers.taluka` | string | 2 |

## 3. Phase 1b — differently-named existing column, map only (11)

Data already lives in the DB under a different column name; bridge in the mapper. No new column.

| KB field | DB source | Type | Rules | Note |
|---|---|---|---:|---|
| `dripper_lph` | `farms.drip_emitter_lph` | number | 2 |  |
| `harvest_date` | `crop_seasons.actual_harvest_date` | date | 6 |  |
| `has_drip` | `farms.irrigation_type (== 'drip')` | boolean | 13 | boolean derive |
| `planting_date` | `crop_seasons.sowing_date` | date | 24 |  |
| `previous_crops_3yr` | `farms.previous_crops_json (parse to array)` | array | 6 | parse JSON→array |
| `soil_texture_class` | `farms.soil_texture (value-map light/medium/heavy)` | enum:[light, medium, heavy] | 6 | value map |
| `variety` | `crop_seasons.crop_variety` | enum:variety_code | 22 |  |
| `water_source_type` | `farms.water_source_primary` | enum:[well, borewell, farm_pond, canal, mixed] | 4 |  |
| `wind_speed_ms` | `weather_station_readings.wind_speed_kmh (÷3.6)` | number | 1 | unit ÷3.6 |
| `yield_quintal_per_acre_actual` | `crop_seasons.actual_yield_qtl_per_acre` | number | 8 |  |
| `yield_target_quintal_per_acre` | `crop_seasons.target_yield_qtl_per_acre` | number | 14 |  |

## 4. Phase 2/3 — no DB home, new schema (287)

Grouped by proposed storage. New columns are named **identically** to the KB field. `kind=derived/adapter` means the value is produced by the mapper or an external adapter once its inputs exist, **not** hand-stored.

### 4.1 Per-season agronomy & field operations — 107 fields

**Proposed storage:** crop_seasons (+cols) / new farm_operations · **Source:** FO/AGRO/TECH · **Kind:** stored

| KB field | Type | Rules | Domains |
|---|---|---:|---|
| `affected_plants_removed` | boolean | 2 | D06 |
| `azospirillum_psb_done` | boolean | 5 | D04,D05,D06 |
| `basal_k_kg_per_acre` | number | 1 | D02 |
| `basal_p_kg_per_acre` | number | 2 | D02 |
| `bed_former_arranged` | boolean | 2 | D08 |
| `bed_height_cm` | number | 5 | D02,D08 |
| `bed_width_cm` | number | 4 | D02,D08 |
| `biofumigation_done` | boolean | 1 | D06 |
| `bud_orientation_instructed` | boolean | 1 | D08 |
| `calibration_date` | date | 1 | D03 |
| `calibration_done` | boolean | 4 | D03,D12 |
| `castor_bait_prepared_date` | date | 1 | D05 |
| `castor_bait_units_per_acre` | integer | 1 | D05 |
| `crop_coefficient_kc` | number | 2 | D03 |
| `deep_ploughing_done` | boolean | 6 | D02,D08 |
| `drip_efficiency_measured` | number | 1 | D03 |
| `drip_flow_lph_per_acre` | number | 2 | D03 |
| `drip_lateral_spacing_ft` | number | 3 | D03,D08 |
| `drip_runtime_min` | number | 8 | D03,D05,D06,D08 |
| `drip_shifts_per_day` | integer | 3 | D03 |
| `dripper_spacing_cm` | number | 2 | D03 |
| `drippers_per_acre` | integer | 1 | D03 |
| `drying_method` | enum:[none, simple_sun, malabar_lime_sulphur, … | 13 | D09,D10 |
| `drying_space_ready` | boolean | 3 | D09 |
| `earthing_up_2_date` | date | 1 | D08 |
| `earthing_up_date` | date | 29 | D01,D03,D04,D05,D06,D08,D09,D11,D12,D13 |
| `ec_baseline` | number | 2 | D04 |
| `ec_trend_pct` | number | 2 | D04 |
| `ethephon_spray_count` | integer | 2 | D08 |
| `fertigation_active` | boolean | 6 | D04 |
| `fertigation_last_ec_response` | number | 1 | D04 |
| `field_history_rot` | boolean | 9 | D01,D02,D05,D06,D12,D13 |
| `furrow_width_cm` | number | 4 | D02,D08 |
| `fym_fully_decomposed` | boolean | 6 | D02,D05,D08 |
| `fym_t_per_acre` | number | 11 | D02,D04,D05,D08 |
| `graded_separately` | boolean | 6 | D09,D13 |
| `harvest_route` | enum:[green_early, green_full, dry_ginger_imme… | 11 | D09,D11,D13 |
| `herbicide_post_emergent_date` | date | 3 | D08 |
| `herbicide_pre_emergent_date` | date | 1 | D08 |
| `hot_water_treatment_done` | boolean | 4 | D06,D09,D11 |
| `intercrop_selected` | string | 5 | D08,D10,D13 |
| `irrigation_applied_litres_today` | number | 7 | D03 |
| `k_applied_kg_per_acre` | number | 3 | D04 |
| `k_late_split_1_date` | date | 4 | D04,D08,D11 |
| `k_late_split_2_date` | date | 2 | D04 |
| `k_source` | enum:[MOP, SOP, mixed] | 2 | D04 |
| `k_target_kg_per_acre` | number | 5 | D04 |
| `kulav_passes` | integer | 3 | D02,D08 |
| `labour_arranged_date` | date | 4 | D08,D13 |
| `last_fungicide_date` | date | 7 | D04,D06,D09 |
| `last_fungicide_group` | string | 5 | D06,D10 |
| `last_insecticide_date` | date | 8 | D05,D09 |
| `last_insecticide_group` | string | 5 | D05,D10 |
| `leaf_wetness_hours` | number | 6 | D06,D07 |
| `limiting_nutrient` | enum:[N, P, K, S, Zn, Fe, B, Mg, none] | 1 | D04 |
| `marigold_planted` | boolean | 3 | D05,D08 |
| `metarhizium_kg_per_acre` | number | 1 | D05 |
| `micronutrient_basal_done` | boolean | 1 | D04 |
| `micronutrient_spray_1_done` | boolean | 6 | D04,D11,D12,D13 |
| `micronutrient_spray_2_done` | boolean | 2 | D04 |
| `moisture_probe_depth_cm` | number | 4 | D01,D03 |
| `mulch_stage_1_done` | boolean | 13 | D03,D06,D07,D08,D09,D11,D12,D13 |
| `mulch_stage_2_done` | boolean | 9 | D03,D04,D06,D08,D11 |
| `mulch_stage_3_done` | boolean | 5 | D03,D06,D08,D11 |
| `n_applied_kg_per_acre` | number | 2 | D04 |
| `n_split_1_date` | date | 2 | D04,D05 |
| `n_split_2_date` | date | 3 | D04,D08 |
| `n_target_kg_per_acre` | number | 6 | D04 |
| `naa_spray_count` | integer | 2 | D08 |
| `neem_cake_basal_kg_per_acre` | number | 3 | D04 |
| `neem_cake_earthing_kg_per_acre` | number | 4 | D04,D05,D08 |
| `p_applied_kg_per_acre` | number | 1 | D04 |
| `p_target_kg_per_acre` | number | 4 | D04 |
| `percolation_class` | enum:[excellent, moderate, poor, very_poor] | 6 | D02,D03,D07,D10 |
| `percolation_time_hours` | number | 3 | D02,D10 |
| `perennial_weeds_removed` | boolean | 3 | D02,D08 |
| `phi_days_remaining` | integer | 5 | D05,D06,D09,D10 |
| `planting_depth_cm` | number | 1 | D08 |
| `planting_layout` | enum:[flat_bed, ridge_furrow, broad_ridge] | 10 | D01,D02,D07,D08,D11 |
| `plants_per_acre` | integer | 3 | D08,D13 |
| `ppe_available` | boolean | 3 | D09 |
| `rows_per_bed` | integer | 2 | D08 |
| `sale_market` | string | 7 | D09,D10,D13 |
| `saturation_hours` | number | 13 | D03,D06,D07,D11,D12 |
| `season_water_plan_basis` | enum:[poor_year, average_year, good_year] | 7 | D07,D09,D13 |
| `seasonal_water_requirement_litres` | number | 1 | D03 |
| `seed_at_planting_kg` | number | 11 | D08,D09,D10,D13 |
| `seed_buds_per_piece` | integer | 1 | D08 |
| `seed_piece_weight_g` | number | 3 | D08,D13 |
| `seed_storage_method` | enum:[pit, shade_heap, cold_store, purchased_f… | 5 | D08,D09,D13 |
| `seed_stored_kg` | number | 7 | D08,D09,D13 |
| `seed_supplier_identified` | boolean | 10 | D10,D11,D13 |
| `shade_pct` | number | 2 | D08,D10 |
| `so2_treatment_used` | boolean | 4 | D09,D10 |
| `solarization_done` | boolean | 6 | D02,D05,D06,D08 |
| `solarization_weeks` | number | 1 | D02 |
| `spray_scheduled_today` | boolean — true when a foliar spray of any kind… | 1 | D07 |
| `stage_source` | enum:[calendar, marker, gdd] | 4 | D01,D07 |
| `target_product` | enum:[green_ginger, dry_ginger, seed_rhizome] | 9 | D01,D03,D04,D06,D08,D09 |
| `trichoderma_kg_per_acre` | number | 6 | D02,D04,D05,D06,D11 |
| `vafsa_state` | enum:[too_wet, workable, too_dry] | 7 | D02,D03,D05,D06,D08 |
| `vwc_field_capacity` | number | 1 | D03 |
| `vwc_saturation` | number | 4 | D03,D04 |
| `vwc_stress_threshold` | number | 1 | D03 |
| `water_available_oct_feb_litres` | number | 10 | D03,D07,D10,D13 |
| `water_stress_after_earthing_done` | boolean | 1 | D08 |
| `weeding_count` | integer | 3 | D08 |

### 4.2 Crop scouting & field observations — 48 fields

**Proposed storage:** new crop_scouting · **Source:** FO/AGRO · **Kind:** stored

| KB field | Type | Rules | Domains |
|---|---|---:|---|
| `central_shoot_dead` | boolean | 4 | D06,D12 |
| `dry_recovery_pct_actual` | number | 5 | D09 |
| `emergence_started` | boolean | 1 | D08 |
| `establishment_pct` | number | 10 | D01,D06,D08,D11,D12,D13 |
| `exposed_rhizomes_observed` | boolean | 4 | D05,D08 |
| `farmer_scout_report_days_ago` | integer — days since farmer submitted the last… | 2 | D14 |
| `field_history_wilt` | boolean | 11 | D01,D02,D05,D06,D08,D12,D13 |
| `flowering_observed` | boolean | 4 | D01,D04,D08 |
| `harvest_injury_observed` | boolean | 4 | D09 |
| `leaf_caterpillar_observed` | boolean | 1 | D05 |
| `leaf_roller_incidence_pct` | number | 3 | D05 |
| `leaf_spot_incidence_pct` | number | 2 | D06 |
| `leaf_spot_rings_visible` | boolean | 2 | D06,D07 |
| `leaf_yellowing_pattern` | enum:[uniform_old, interveinal_new, interveina… | 7 | D04,D09,D12 |
| `light_trap_count_nightly` | integer | 3 | D05,D12 |
| `light_trap_installed` | boolean | 2 | D05,D12 |
| `moisture_pct_final` | number | 4 | D09 |
| `nematode_suspected` | boolean | 9 | D05,D06,D08 |
| `ooze_test_result` | enum:[not_done, milky_thread, no_thread] | 2 | D06 |
| `pest_scouting_date` | date | 3 | D05,D07 |
| `plant_pulls_easily` | boolean | 1 | D05 |
| `produce_washed` | boolean | 6 | D09 |
| `rhizome_fly_incidence_pct` | number | 2 | D05 |
| `rhizome_smell` | enum:[normal, sour_foul, faint] | 1 | D06 |
| `rhizome_texture` | enum:[firm, mushy_wet, dry_rot] | 2 | D06 |
| `rot_incidence_pct` | number | 13 | D06,D09,D11,D12,D13 |
| `sample_dig_120_done` | boolean | 1 | D01 |
| `sample_dig_180_done` | boolean | 2 | D01,D11 |
| `scout_request_pending` | boolean — a scouting task has been dispatched … | 1 | D14 |
| `seed_sprouts_visible` | boolean | 1 | D08 |
| `seed_storage_loss_pct` | number | 5 | D08,D13 |
| `shoot_borer_incidence_pct` | number | 3 | D05 |
| `shoot_pulls_out_easily` | boolean | 1 | D06 |
| `skin_scrape_result` | enum:[not_done, peels_easily, firmly_attached] | 5 | D09 |
| `soft_rhizome_found` | boolean | 3 | D05,D08 |
| `standing_water_hours_observed` | number | 1 | D02 |
| `stem_cut_colour` | enum:[brown_black, greyish_yellow, brown_vascu… | 2 | D06 |
| `stem_hole_with_webbing` | boolean | 1 | D05 |
| `stem_ooze_type` | enum:[none, watery_foul, milky_yellowish] | 1 | D06 |
| `storage_loss_monthly_pct` | number | 4 | D09 |
| `straight_line_holes_in_whorl` | boolean | 2 | D05,D12 |
| `tillers_per_plant` | number | 5 | D01,D05,D08,D12 |
| `water_withdrawal_pct` | number | 2 | D09 |
| `water_withdrawal_start_date` | date | 1 | D09 |
| `water_withdrawal_started` | boolean | 2 | D03 |
| `white_grub_suspected` | boolean | 4 | D05,D12 |
| `wilt_incidence_pct` | number | 4 | D06,D09 |
| `wilt_while_green` | boolean | 3 | D06,D12 |

### 4.3 Economics (D13) — 31 fields

**Proposed storage:** new season_economics (+ mandi price feed) · **Source:** FO/DEALER/market · **Kind:** stored

| KB field | Type | Rules | Domains |
|---|---|---:|---|
| `breakeven_price_per_quintal` | number | 5 | D13 |
| `breakeven_yield_quintal` | number | 2 | D13 |
| `cash_flow_gap_months` | number | 3 | D13 |
| `cash_outflow_to_date` | number | 1 | D13 |
| `cost_drainage` | number | 3 | D13 |
| `cost_earthing_labour` | number | 1 | D13 |
| `cost_harvest_transport` | number | 3 | D13 |
| `cost_micronutrients` | number | 2 | D13 |
| `cost_mulch` | number | 4 | D13 |
| `cost_seed` | number | 6 | D13 |
| `cost_seed_treatment_planting` | number | 2 | D13 |
| `crop_loan_taken` | boolean | 3 | D13 |
| `drip_annual_share` | number | 2 | D13 |
| `drip_capital_cost` | number | 2 | D13 |
| `drip_life_years` | number | 1 | D13 |
| `drip_subsidy_pct_applicable` | number | 7 | D10,D13 |
| `grade_a_pct` | number | 8 | D09,D11,D13 |
| `grade_b_pct` | number | 6 | D09,D11,D13 |
| `grade_c_pct` | number | 7 | D09,D11,D13 |
| `intercrop_revenue` | number | 1 | D13 |
| `interest_cost` | number | 2 | D13 |
| `land_rent_or_opportunity` | number | 1 | D13 |
| `mulch_material_price_per_tonne` | number | 1 | D13 |
| `mulch_quantity_t_per_acre` | number | 1 | D13 |
| `net_return_per_acre` | number | 8 | D13 |
| `sale_price_per_quintal` | number | 24 | D09,D11,D13 |
| `scale_of_finance_per_acre` | number | 2 | D10,D13 |
| `seed_opportunity_cost` | number | 2 | D13 |
| `seed_retained_or_purchased` | enum:[retained, purchased, mixed] | 3 | D13 |
| `total_cost_per_acre` | number | 15 | D13 |
| `transport_cost_per_quintal` | number | 7 | D09,D10,D13 |

### 4.4 Yield-model & advisory-QA state (D11/D12) — 38 fields

**Proposed storage:** new advisory_qa / yield_predictions / consent_log · **Source:** DERIVED/SYS · **Kind:** derived/state

| KB field | Type | Rules | Domains |
|---|---|---:|---|
| `action_compliance_rate` | number | 7 | D12,D13 |
| `advisory_completed_count` | integer | 1 | D12 |
| `advisory_completed_on_time_count` | integer | 1 | D12 |
| `advisory_issued_count` | integer | 4 | D12 |
| `advisory_language` | enum:[mr, en] | 8 | D12 |
| `asr_used` | boolean | 3 | D12 |
| `bias_observation_count` | integer | 5 | D07,D12 |
| `ceiling_basis` | enum:[variety_only_94, variety_plus_broad_ridg… | 1 | D11 |
| `ceiling_quintal_per_acre` | number | 8 | D11,D13 |
| `cluster_anonymised` | boolean | 4 | D12 |
| `cluster_id` | string | 7 | D12 |
| `cluster_pest_alert_active` | boolean | 3 | D05,D06,D12 |
| `consent_advisory` | boolean | 4 | D12 |
| `consent_date` | date | 2 | D12 |
| `consent_research` | boolean | 2 | D12 |
| `cumulative_loss_pct` | number | 7 | D11 |
| `data_retention_until` | date | 2 | D12 |
| `deletion_requested` | boolean | 1 | D12 |
| `false_alarm_count` | integer | 1 | D12 |
| `gap_attributed_pct` | number | 2 | D11 |
| `gap_filling_done` | boolean | 1 | D08 |
| `gap_unexplained_pct` | number | 4 | D11,D12 |
| `interdependence_group` | string | 4 | D11 |
| `model_version` | string | 9 | D12 |
| `non_compliance_reason` | enum:[labour, time, cost, seemed_unnecessary, … | 1 | D12 |
| `photo_labelled_count` | integer | 3 | D12 |
| `photo_uploaded_count` | integer | 2 | D12 |
| `plot_ndre_gap_regional` | number — signed difference plot NDRE minus reg… | 2 | D14 |
| `plot_ndvi_gap_peer` | number — signed difference plot NDVI minus pee… | 1 | D14 |
| `predicted_yield_quintal_per_acre` | number | 7 | D11 |
| `prediction_interval_pct` | number | 8 | D11,D12 |
| `prediction_stage` | enum:[pre_season, g1_end, mid_season, pre_harv… | 5 | D11 |
| `season_record_complete` | boolean | 6 | D11,D12 |
| `third_party_share_consent_given` | boolean — DPDP purpose-limited consent for sha… | 1 | D14 |
| `true_alarm_count` | integer | 1 | D12 |
| `u_value_source_class` | enum:[SRC-Q, SRC-D, EST, FIELD] | 11 | D11,D12 |
| `u_values_applied` | array of rule_id | 17 | D11 |
| `yield_prediction_interval_pct` | number | 1 | D01 |

### 4.5 Weather & forecast (D07) — 25 fields

**Proposed storage:** weather_forecasts (adapter) / weather_station_readings · **Source:** WAPI/DERIVED · **Kind:** adapter

| KB field | Type | Rules | Domains |
|---|---|---:|---|
| `agro_climatic_zone` | enum:[marathwada_western, marathwada_central, … | 3 | D07,D10 |
| `cyclone_alert_active` | boolean | 2 | D07 |
| `drainage_levels_present` | integer 0-3 | 14 | D02,D03,D06,D07,D11,D13 |
| `drainage_outlet_present` | boolean | 1 | D02 |
| `dry_spell_days` | integer | 2 | D07,D11 |
| `effective_rainfall_mm` | number | 2 | D03,D07 |
| `fog_days_consecutive` | integer | 2 | D06,D07 |
| `fog_observed` | boolean | 3 | D07 |
| `forecast_bias_correction_mm` | number | 2 | D07 |
| `forecast_rain_48h_mm` | number | 5 | D07 |
| `forecast_source` | string | 4 | D07 |
| `heat_stress_days_count` | integer | 3 | D07 |
| `main_drain_connected` | boolean | 3 | D02,D07 |
| `pan_coefficient_kp` | number | 1 | D03 |
| `pan_evaporation_mm_day` | number | 4 | D03,D07 |
| `processing_trained_operator` | boolean | 4 | D09,D10 |
| `rain_gap_days` | integer | 4 | D03,D07 |
| `rainfall_deviation_pct` | number | 5 | D07 |
| `rainfall_last_48h_mm` | number — cumulative rainfall in the last 48 ho… | 3 | D14 |
| `rainfall_mm` | number | 14 | D02,D03,D04,D05,D06,D07 |
| `rainfall_ytd_mm` | number | 7 | D07 |
| `solar_radiation_mj_m2` | number | 3 | D07 |
| `station_data_age_hours` | number — hours since the last weather station … | 1 | D07 |
| `station_id` | string | 4 | D07 |
| `vpd_night_mean_kpa` | number — mean nighttime VPD (2200–0600 local) … | 2 | D07 |

### 4.6 Govt schemes & subsidy (D10) — 18 fields

**Proposed storage:** new farmer_schemes · **Source:** OPS/FO · **Kind:** stored

| KB field | Type | Rules | Domains |
|---|---|---:|---|
| `cgwb_block_category` | enum:[safe, semi_critical, critical, over_expl… | 1 | D10 |
| `cibrc_list_checked_date` | date | 5 | D10,D12 |
| `data_review_due` | date | 4 | D10,D12 |
| `drought_prone_listed` | enum:[yes, no, unverified] | 2 | D10 |
| `farm_pond_planned` | boolean | 5 | D10,D13 |
| `farmer_category` | enum:[small_marginal, other, unverified] | 2 | D10 |
| `geo_tagging_done` | boolean | 1 | D10 |
| `kvk_contacted` | boolean | 4 | D10 |
| `pmfby_notified_for_ginger` | enum:[yes, no, unverified] | 1 | D10 |
| `pre_sanction_date` | date | 2 | D10 |
| `pre_sanction_received` | boolean | 1 | D10 |
| `priority_category` | enum:[martyr_family, suicide_affected, bpl, wi… | 1 | D10 |
| `research_centre_contacted` | boolean | 4 | D10 |
| `soil_lab_selected` | string | 2 | D10 |
| `subsidy_applied_date` | date | 4 | D10 |
| `subsidy_documents_ready` | boolean | 2 | D10 |
| `subsidy_lottery_result` | enum:[pending, selected, not_selected, not_app… | 4 | D10,D13 |
| `subsidy_scheme_applied` | string | 8 | D10 |

### 4.7 Satellite / Domain-14 extras — 11 fields

**Proposed storage:** satellite_data (+cols) / DERIVED · **Source:** SAT/DERIVED · **Kind:** adapter/derived

| KB field | Type | Rules | Domains |
|---|---|---:|---|
| `claim_type` | text — enum tagging POS-rule dispatch: pos_001… | 7 | D14 |
| `cwsi` | number — Crop Water Stress Index in [0,1] from… | 6 | D14 |
| `lst_c` | number — Land Surface Temperature in Celsius f… | 2 | D14 |
| `monsoon_days_since_onset` | integer — days since IMD-declared monsoon onse… | 1 | D14 |
| `outgoing_message_contains_claim` | boolean — set by the outbound-message QA layer… | 7 | D14 |
| `plot_ndre_baseline_regional` | number — regional expected NDRE for the curren… | 2 | D14 |
| `plot_ndvi_baseline_peer` | number — mean peer NDVI in the cluster at the … | 2 | D14 |
| `sat_attribution_shown` | boolean — true when the required source attrib… | 1 | D14 |
| `sat_public_display_context` | text — enum: own_plot, cluster_aggregate, thir… | 1 | D14 |
| `sub_node_ec_status` | text — enum: normal, high, low, stale — resolv… | 2 | D14 |
| `sub_node_moisture_status` | text — enum: adequate, low, saturated, stale —… | 8 | D14 |

### 4.8 Soil lab test — 9 fields

**Proposed storage:** new lab_soil_tests · **Source:** lab (OPS) · **Kind:** stored

| KB field | Type | Rules | Domains |
|---|---|---:|---|
| `soil_ca_ppm` | number | 1 | D04 |
| `soil_ec` | number | 3 | D02,D04 |
| `soil_fe_ppm` | number | 5 | D02,D04,D10 |
| `soil_free_lime_pct` | number | 11 | D02,D04,D10 |
| `soil_mg_ppm` | number | 1 | D04 |
| `soil_oc_pct` | number | 5 | D02,D04 |
| `soil_s_ppm` | number | 1 | D04 |
| `soil_test_available` | boolean | 8 | D02,D04,D10,D12 |
| `soil_zn_ppm` | number | 6 | D02,D04,D10 |

## 5. Execution plan

**Phase 1 (mapper only, no schema change) — 19 fields.** Wire §2 + §3 into `build_farm_brain`; remove the inert `_set` calls whose KB counterpart is an alias (`crop_variety`, `sowing_date`, raw sensor names). Add coverage tests. Safe, immediate.

**Phase 2 (stored-fact tables) — ~213 fields.** New tables/columns for §4.1–4.4, 4.6, 4.8 (season-ops, scouting, economics, schemes, lab). One Alembic migration per group, columns named to match the KB field, then wire each in the mapper + extend the Data Entry page for entry.

**Phase 3 (adapters/derivations) — ~74 fields.** Weather-forecast adapter (§4.5), Landsat LST/CWSI + peer baselines (§4.7, peer needs ≥3 enrolled plots), and engine yield-model / QA state persistence (§4.3). Produced by code, not hand-entered.

### Not doing
- **No KB changes** — the KB is frozen.
- **No column renames** — the mapper is the name-matching contract.
- **No blind 287-column dump** — the ~74 derived/adapter fields must not become raw columns.
