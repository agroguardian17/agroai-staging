# KB ↔ DB Field Mapping Specification

**Regenerated:** 2026-09-22 · **Status:** current (post KB step-2: rule D07-CY-WX-001) · **Owner:** backend

Single source of truth for how every Ginger-KB input field reaches the engine. The KB is authored in `new-docs/AgroGuardian_Ginger_Engine_v1.0_9931/` (JSON → `json_to_sql.py` → unified SQL); the backend loads that unified build (migration 0032) and reconciles via the mapper [`app/application/build_farm_brain.py`](../app/application/build_farm_brain.py). A field is *wired* when the mapper copies it into the per-plot farm-brain the engine reads.

## Summary

| | Count |
|---|---:|
| KB rules | **483** |
| Distinct fields the rules read | **352** |
| Fields wired (DB home + mapper) | **325** |
| Fields not yet wired | **27** |
| Rules fully-wireable | **408** |
| Rules partially wireable | 66 |
| Rules fully blocked (all fields not yet wired) | 9 |

*Wireable ≠ firing:* a rule fires only when its fields also hold **data** and its trigger is true. Most tables/columns below are populated on demand via the dashboard entry pages; sensor & weather fields depend on field hardware.

## Rule readiness by domain

| Domain | Fully-wireable | Partial | Blocked | Total |
|---|---:|---:|---:|---:|
| D01 nursery/stage | 22 | 0 | 0 | 22 |
| D02 land prep | 24 | 3 | 0 | 27 |
| D03 irrigation | 27 | 4 | 0 | 31 |
| D04 nutrients | 31 | 3 | 0 | 34 |
| D05 pests | 33 | 1 | 0 | 34 |
| D06 disease | 22 | 6 | 0 | 28 |
| D07 weather | 24 | 15 | 0 | 39 |
| D08 planting | 38 | 0 | 0 | 38 |
| D09 harvest | 39 | 0 | 0 | 39 |
| D10 schemes | 34 | 1 | 0 | 35 |
| D11 yield model | 28 | 6 | 0 | 34 |
| D12 advisory QA | 19 | 16 | 1 | 36 |
| D13 economics | 39 | 0 | 0 | 39 |
| D14 satellite | 28 | 11 | 8 | 47 |
| **Total** | **408** | **66** | **9** | **483** |

## Wired fields by source

Each source is a DB table (with its entry path) or a computed value.

### crop_seasons — 98 fields
*Entry: Data Entry page · AGRO tab*

`affected_plants_removed`, `azospirillum_psb_done`, `bed_former_arranged`, `bed_height_cm`, `bed_width_cm`, `biofumigation_done`, `bud_orientation_instructed`, `calibration_date`, `calibration_done`, `crop_coefficient_kc`, `current_stage`, `dap`, `days_to_planting`, `deep_ploughing_done`, `drainage_levels_present`, `drainage_outlet_present`, `drip_efficiency_measured`, `drip_flow_lph_per_acre`, `drip_lateral_spacing_ft`, `drip_shifts_per_day`, `dripper_spacing_cm`, `drippers_per_acre`, `dry_recovery_pct_actual`, `drying_method`, `drying_space_ready`, `earthing_up_2_date`, `earthing_up_date`, `field_history_rot`, `field_history_wilt`, `furrow_width_cm`, `fym_fully_decomposed`, `fym_t_per_acre`, `gap_filling_done`, `harvest_date`, `harvest_route`, `hot_water_treatment_done`, `intercrop_selected`, `k_applied_kg_per_acre`, `k_late_split_1_date`, `k_late_split_2_date`, `k_source`, `k_target_kg_per_acre`, `limiting_nutrient`, `main_drain_connected`, `marigold_planted`, `micronutrient_basal_done`, `micronutrient_spray_1_done`, `micronutrient_spray_2_done`, `moisture_probe_depth_cm`, `mulch_stage_1_done`, `mulch_stage_2_done`, `mulch_stage_3_done`, `n_applied_kg_per_acre`, `n_split_1_date`, `n_split_2_date`, `n_target_kg_per_acre`, `neem_cake_basal_kg_per_acre`, `neem_cake_earthing_kg_per_acre`, `p_applied_kg_per_acre`, `p_target_kg_per_acre`, `pan_coefficient_kp`, `perennial_weeds_removed`, `planting_date`, `planting_depth_cm`, `planting_layout`, `plants_per_acre`, `ppe_available`, `processing_trained_operator`, `produce_washed`, `rows_per_bed`, `season_water_plan_basis`, `seasonal_water_requirement_litres`, `seed_at_planting_kg`, `seed_buds_per_piece`, `seed_cost_per_kg`, `seed_piece_weight_g`, `seed_storage_loss_pct`, `seed_storage_method`, `seed_stored_kg`, `shade_pct`, `so2_treatment_used`, `solarization_done`, `solarization_weeks`, `stage_source`, `storage_loss_monthly_pct`, `target_product`, `trichoderma_kg_per_acre`, `variety`, `vwc_field_capacity`, `vwc_saturation`, `vwc_stress_threshold`, `water_available_oct_feb_litres`, `water_stress_after_earthing_done`, `water_withdrawal_pct`, `water_withdrawal_start_date`, `water_withdrawal_started`, `yield_quintal_per_acre_actual`, `yield_target_quintal_per_acre`

### crop_scouting — 38 fields
*Entry: 🔎 Crop Scouting page*

`central_shoot_dead`, `emergence_started`, `establishment_pct`, `exposed_rhizomes_observed`, `flowering_observed`, `harvest_injury_observed`, `leaf_caterpillar_observed`, `leaf_roller_incidence_pct`, `leaf_spot_incidence_pct`, `leaf_spot_rings_visible`, `leaf_yellowing_pattern`, `light_trap_count_nightly`, `light_trap_installed`, `moisture_pct_final`, `nematode_suspected`, `ooze_test_result`, `pest_scouting_date`, `plant_pulls_easily`, `rhizome_fly_incidence_pct`, `rhizome_smell`, `rhizome_texture`, `rot_incidence_pct`, `sample_dig_120_done`, `sample_dig_180_done`, `seed_sprouts_visible`, `shoot_borer_incidence_pct`, `shoot_pulls_out_easily`, `skin_scrape_result`, `soft_rhizome_found`, `standing_water_hours_observed`, `stem_cut_colour`, `stem_hole_with_webbing`, `stem_ooze_type`, `straight_line_holes_in_whorl`, `tillers_per_plant`, `white_grub_suspected`, `wilt_incidence_pct`, `wilt_while_green`

### season_economics — 32 fields
*Entry: 📋 Season & Scheme Records page*

`breakeven_price_per_quintal`, `breakeven_yield_quintal`, `cash_flow_gap_months`, `cash_outflow_to_date`, `ceiling_quintal_per_acre`, `cost_drainage`, `cost_earthing_labour`, `cost_harvest_transport`, `cost_micronutrients`, `cost_mulch`, `cost_seed`, `cost_seed_treatment_planting`, `crop_loan_taken`, `drip_annual_share`, `drip_capital_cost`, `drip_life_years`, `grade_a_pct`, `grade_b_pct`, `grade_c_pct`, `graded_separately`, `intercrop_revenue`, `interest_cost`, `land_rent_or_opportunity`, `mulch_material_price_per_tonne`, `mulch_quantity_t_per_acre`, `net_return_per_acre`, `sale_market`, `sale_price_per_quintal`, `seed_opportunity_cost`, `seed_retained_or_purchased`, `total_cost_per_acre`, `transport_cost_per_quintal`

### satellite_data (Sentinel-1/2) — 32 fields
*Entry: daily CDSE sweep (automated). Peer/regional baselines light up once ≥3 cluster plots are enrolled (item #1, PR #46).*

`evi_mean`, `nbr_delta_10d`, `nbr_mean`, `ndmi_delta_10d`, `ndmi_mean`, `ndre_mean`, `ndre_slope_5d`, `ndvi_delta_10d`, `ndvi_freshness_days`, `ndvi_mean`, `ndvi_std`, `optical_gap_days`, `plot_area_ha`, `plot_cloud_pct`, `plot_ndre_baseline_regional`, `plot_ndre_gap_regional`, `plot_ndvi_baseline_peer`, `plot_ndvi_baseline_regional`, `plot_ndvi_gap_peer`, `plot_ndvi_gap_regional`, `plot_polygon_wkt`, `sar_coherence`, `sar_gap_days`, `sar_rvi`, `sar_vh_db`, `sar_vv_db`, `sar_vv_delta_db`, `sat_advisory_confidence`, `sat_pipeline_version`, `sat_source`, `savi_mean`, `scene_valid_pixel_pct`

### satellite_data (Landsat LST) — 1 field
*Entry: daily USGS M2M sweep (automated, PR #48). Needs `LANDSAT_JOB_ENABLED` + USGS creds. Feeds the derived `cwsi`.*

`lst_c`

### farmer_schemes — 21 fields
*Entry: 📋 Season & Scheme Records page*

`cgwb_block_category`, `cibrc_list_checked_date`, `data_review_due`, `drip_subsidy_pct_applicable`, `drought_prone_listed`, `farm_pond_planned`, `farmer_category`, `geo_tagging_done`, `kvk_contacted`, `pmfby_notified_for_ginger`, `pre_sanction_date`, `pre_sanction_received`, `priority_category`, `research_centre_contacted`, `scale_of_finance_per_acre`, `seed_supplier_identified`, `soil_lab_selected`, `subsidy_applied_date`, `subsidy_documents_ready`, `subsidy_lottery_result`, `subsidy_scheme_applied`

### season_operations — 20 fields
*Entry: 📋 Season & Scheme Records page*

`basal_k_kg_per_acre`, `basal_p_kg_per_acre`, `castor_bait_prepared_date`, `castor_bait_units_per_acre`, `drip_runtime_min`, `ethephon_spray_count`, `fertigation_active`, `fertigation_last_ec_response`, `herbicide_post_emergent_date`, `herbicide_pre_emergent_date`, `irrigation_applied_litres_today`, `kulav_passes`, `labour_arranged_date`, `last_fungicide_date`, `last_fungicide_group`, `last_insecticide_date`, `last_insecticide_group`, `metarhizium_kg_per_acre`, `naa_spray_count`, `weeding_count`

### weather_forecasts (Open-Meteo) — 18 fields
*Entry: daily forecast fetch (automated). `rainfall_deviation_pct` uses IMD station monthly normals; `severe_weather_alert_active` (renamed from `cyclone_alert_active`, VJH §7) and the new rule `D07-CY-WX-001` both trip on rain ≥ 75 mm OR wind ≥ 40 km/h — the latter reads the raw `rainfall_24h_mm` / `wind_gust_kmph` (wind gust now fetched from Open-Meteo).*

`dry_spell_days`, `effective_rainfall_mm`, `fog_days_consecutive`, `fog_observed`, `forecast_rain_48h_mm`, `forecast_source`, `heat_stress_days_count`, `pan_evaporation_mm_day`, `rain_gap_days`, `rainfall_24h_mm`, `rainfall_deviation_pct`, `rainfall_last_48h_mm`, `rainfall_mm`, `rainfall_ytd_mm`, `severe_weather_alert_active`, `solar_radiation_mj_m2`, `vpd_night_mean_kpa`, `wind_gust_kmph`

### farmer_consent — 9 fields
*Entry: —*

`cluster_anonymised`, `consent_advisory`, `consent_date`, `consent_research`, `data_retention_until`, `deletion_requested`, `sat_attribution_shown`, `sat_public_display_context`, `third_party_share_consent_given`

### farms — 8 fields
*Entry: Data Entry page (farm facts). `soil_type` now maps `red → red_loam` (VJH §3).*

`dripper_lph`, `has_drip`, `previous_crops_3yr`, `soil_depth_cm`, `soil_oc_pct`, `soil_texture_class`, `soil_type`, `water_source_type`

### lab_soil_tests — 8 fields
*Entry: 🧪 Lab Soil Test page*

`soil_ca_ppm`, `soil_ec`, `soil_fe_ppm`, `soil_free_lime_pct`, `soil_mg_ppm`, `soil_s_ppm`, `soil_test_available`, `soil_zn_ppm`

### weather_station_readings (Main Node) — 6 fields
*Entry: MQTT telemetry (hardware)*

`air_temp_max_c`, `air_temp_min_c`, `dew_point_c`, `rh_pct`, `vpd_kpa`, `wind_speed_ms`

### farmers — 4 fields
*Entry: Data Entry page (identity)*

`advisory_language`, `agro_climatic_zone`, `district`, `taluka`

### advisory metrics (ai_suggestions + farmer_actions) — 4 fields
*Entry: derived from the engine's own history (D12 compliance counters, PR #49). Populate as advisories are sent and farmers reply.*

`action_compliance_rate`, `advisory_completed_count`, `advisory_completed_on_time_count`, `advisory_issued_count`

### yield model (D11 process baseline) — 10 fields
*Entry: computed each run by the yield-model scaffold (`yield_u_values` register + `predict_yield`), logged to `yield_prediction_log`. `ceiling_quintal_per_acre` comes from `season_economics` (above).*

`ceiling_basis`, `cumulative_loss_pct`, `gap_attributed_pct`, `gap_unexplained_pct`, `predicted_yield_quintal_per_acre`, `prediction_interval_pct`, `season_record_complete`, `u_value_source_class`, `u_values_applied`, `yield_prediction_interval_pct`

### computed in mapper — 5 fields
*Entry: derived each run from other filled fields.*

`cwsi`, `model_version`, `phi_days_remaining`, `prediction_stage`, `vafsa_state`

### node_sensor_readings (Sub Node sensor) — 4 fields
*Entry: MQTT telemetry (hardware)*

`ec_current`, `soil_moisture_vwc`, `soil_ph`, `soil_temp_c`

### plots — 2 fields
*Entry: seed / Data Entry*

`area_acre`, `plot_id`

### derived in mapper (satellite/season) — 1 fields
*Entry: —*

`farmer_id`

### Declared + mapper-set, awaiting a consuming rule — 1 field
Newly declared in the KB (step-1 edits) and set by the mapper, but no rule reads it yet, so it is not counted in the read/wired totals above. `soil_texture_class_source` stands ready for the agronomy team to author the consuming rule.
`soil_texture_class_source`

The four D05 blocklist trace fields (`phi_blocklist_hit`, `blocklist_reason`, `blocklist_source_ref`, `farmer_alert_type`) are now consumed by **`D05-CH-008`** — the runtime blocklist-detection alert (severity red, `ONCE_UNTIL_RESOLVED`) that fires on `phi_blocklist_hit IS TRUE` and warns the farmer that a blocklisted input has no certifiable pre-harvest interval. They are therefore counted in the read/wired totals above.

## Not yet wired (27 fields)

None of these is a farm *input* the mapper can copy. Each is either an engine
output, a value that needs a subsystem/workflow we have not built, or a value
that depends on hardware/history that is not present yet.

### Engine yield-model output (D11) — 1 field
The 10 other D11 fields are now produced by the yield-model scaffold (above). `interdependence_group` remains UNKNOWN pending the KB's duplication-group map. *See item #8 / `D11_YIELD_MODEL_v1.md`.*
`interdependence_group`

### Advisory-QA workflow (D12) — 8 fields
Need a human QA-review / labelling workflow that does not exist yet (alarm classification, bias review, photo labelling, cluster assignment, non-compliance reason capture). The four *computable* D12 counters are now wired (above). *See item #8.*
`asr_used`, `bias_observation_count`, `cluster_id`, `false_alarm_count`, `non_compliance_reason`, `photo_labelled_count`, `photo_uploaded_count`, `true_alarm_count`

### Hardware / runtime message-pipeline — 9 fields
Set at message-compose time or derived from the Sub Node / cluster once those exist — not part of the per-plot farm-brain snapshot.
`claim_type`, `cluster_pest_alert_active`, `farmer_scout_report_days_ago`, `monsoon_days_since_onset`, `outgoing_message_contains_claim`, `scout_request_pending`, `spray_scheduled_today`, `sub_node_ec_status`, `sub_node_moisture_status`

### Derived — needs time-series history or a field test — 6 fields
Computable once we retain enough history (EC baseline/trend, saturation & leaf-wetness durations) or capture a one-off percolation test.
`ec_baseline`, `ec_trend_pct`, `leaf_wetness_hours`, `percolation_class`, `percolation_time_hours`, `saturation_hours`

### Weather-station hardware / forecast bias — 3 fields
Depend on the physical Main Node weather station being installed, or on observed-vs-forecast history to compute a bias correction.
`forecast_bias_correction_mm`, `station_data_age_hours`, `station_id`

## Build history

- **Phase 1** (#36): 19 mapper-only fields (variety, planting_date, area, soil, water…).
- **Phase 2.1** (#37/#38): `lab_soil_tests` + entry page.
- **Phase 2.2** (#39): `crop_seasons` agronomy-plan part 1 (37 cols).
- **Phase 2.3** (#40): `crop_scouting` + entry page.
- **Phase 2.4** (#41): `crop_seasons` part 2 (50 cols) + `season_economics` + `season_operations` + `farmer_schemes` + records page.
- **Fix** (#42): wire the part-2 season columns into the mapper (+ guard test).
- **Phase 3 weather** (#44/#45): Open-Meteo forecast adapter (D07 rain/evaporation/radiation window).
- **Phase 3 peer** (#46): peer/regional NDVI+NDRE baselines across cluster plots (item #1).
- **Phase 3 agronomy** (#47): soil/zone/PHI defaults, `rainfall_deviation_pct`, `cyclone_alert_active`, `phi_days_remaining`, `prediction_stage`, `model_version` (items #3, #7).
- **Phase 3 Landsat** (#48): USGS M2M LST adapter → `lst_c` → derived `cwsi` (item #6).
- **D12 counters** (#49): advisory compliance counters from `ai_suggestions` + `farmer_actions` (`advisory_issued/completed/on_time_count`, `action_compliance_rate`) — the code-doable slice of item #8.
- **D11 scaffold** (#51): process-baseline yield model (`yield_u_values` + `predict_yield` + `yield_prediction_log`) → 10 D11 fields.
- **KB step-1** (PR #52): switched the backend onto the unified 14-domain KB build (migration 0032, state-preserving reload). Applied AGRONOMY_SIGNOFF / VJH-V1.0 edits in the JSON source + regenerated: `cyclone_alert_active`→`severe_weather_alert_active` (rain≥75 OR wind≥40), `prediction_stage`→G0–G5, `soil_type` +`red_loam`, new declared fields (`soil_texture_class_source` + D05 blocklist trace).
- **KB step-2** (PR #54): new rule **`D07-CY-WX-001`** (VJH §8) authored in the JSON + authoring `.py` with 9 boundary golden tests, regenerated (482 rules). Added `rainfall_24h_mm` / `wind_gust_kmph` fields end-to-end (Open-Meteo `wind_gusts_10m_max` → `weather_forecasts.wind_gust_kmph` col via migration 0033 → mapper), and an additive KB reload (migration 0034).
- **KB step-3 / structured references** (PR #58): split the free-text `kb_rule_references.reference` into an evidence hierarchy — `ref_kind` (external/internal), `institution` (curated recogniser), `source_tier` (A/B/C on external refs) — derived in `json_to_sql.py`; migration 0035 reshaped `kb_rule_references`.
- **D05 blocklist branch** (this PR): new rule **`D05-CH-008`** (severity red, `ONCE_UNTIL_RESOLVED`) authored in the JSON + authoring `.py` with 3 golden tests, regenerated (483 rules). It consumes the four blocklist trace fields the mapper already set (`phi_blocklist_hit` / `blocklist_reason` / `blocklist_source_ref` / `farmer_alert_type`) — the runtime counterpart to the `D05-CH-001` emission guard — and lands via an additive KB reload (migration 0036).
- **Remaining (27 fields):** `interdependence_group` (D11 duplication-group map) + the D12 advisory-QA workflow (item #8) need agronomy/QA subsystems; the rest need field hardware, time-series history, or external feeds.
