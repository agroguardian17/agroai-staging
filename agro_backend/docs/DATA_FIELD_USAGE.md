# Data Field Usage — what we use, where, and how

**Audience:** engineering + agronomy. **Purpose:** for every data field, say whether it drives the
Knowledge Base (KB) / another engine or is only stored, and *where* and *how* it is used — with a
correctness checklist at the end.

**Generated:** 2026-10-16 from ground truth — the KB rule JSONs
(`new-docs/AgroGuardian_Ginger_Engine_v1.0_9931/knowledge_base/Domain*_Rules_Ginger*.json`), the
mapper [`app/application/build_farm_brain.py`](../app/application/build_farm_brain.py), the ORM models
(`app/infra/persistence/models/`), the device-health rules
([`app/domain/rule_definitions.py`](../app/domain/rule_definitions.py)) and the device-metrics
([`app/domain/metrics.py`](../app/domain/metrics.py)). Where this doc and code disagree, **code wins**;
re-generate with the scripts noted in §8.

---

## 1. How a field reaches a consumer (read this first)

```
          PHYSICAL / ENTRY SOURCES                         CONSUMERS
  ┌──────────────────────────────────────┐
  │ Sub-node sensor  → node_sensor_readings│──┐
  │ Weather station  → weather_station_... │  │   build_farm_brain (the "mapper")
  │ Main node        → main_node_readings   │  │   copies/derives ~375 per-plot
  │ Weather forecast → weather_forecasts    │  ├─▶ "farm-brain" fields ───▶ Ginger KB engine (495 rules)
  │ Satellite/LST    → satellite_data       │  │                            (reads a field only if a rule's
  │ Agronomy entry   → crop_seasons, lab_…, │  │                             farm_brain_schema lists it)
  │   crop_scouting, season_economics, …    │──┘
  └──────────────────────────────────────┘
                     │  (sensor readings also go, UNmapped, straight to:)
                     ├─▶ Device-health engine (7 rules, per message)  ── app/domain/rule_definitions.py
                     ├─▶ Water-budget engine (D03-WB)                 ── app/domain/water_budget.py
                     └─▶ Device watchdog / heartbeat (main_node)      ── app/jobs/device_watchdog.py
```

**The single most important rule for reading this doc:** a column being **stored** (a table column) is
different from it being **populated into the farm-brain** (the mapper copies it) which is different
again from it being **used by the KB** (a rule's `farm_brain_schema` actually reads it). A field can be
at any of those three levels. So "soil temperature" has *two* columns that feed *two different engines*,
and most raw sensor columns are stored but not read by any rule — details below.

---

## 2. Headline numbers (current, verified)

| Metric | Value |
|---|---:|
| KB rules | **495** (D01–D14) |
| …with a machine trigger (`trigger.expr`) | 296 |
| …immutable (safety core) | 24 |
| Distinct fields **read by the KB** (union of rule `farm_brain_schema`) | **416** |
| …of those, **wired** (the mapper supplies a value) | **340** |
| …**dormant** (a rule wants it, but no source feeds it yet) | **76** |
| Fields the mapper **populates** into the farm-brain | **375** |
| …populated but **no KB rule reads them** (and not a device/water input) | **30** |

---

## 3. PART A — Fields we USE

### A1. Sub-node sensor telemetry → `node_sensor_readings` (45 columns)

This is the table you asked about: several measurements land in *parallel* columns, and they do **not**
all feed the KB. Here is every column and its real consumer.

**The multi-sensor disambiguations (the important part):**

| Measurement | Columns stored | What actually consumes it |
|---|---|---|
| **Soil temperature** | `soil_temp_c`, `soil_temp_rootzone_c` | **`soil_temp_c` → KB** (7 rules: D01-TM-001, D03-MU-001, D03-SC-003, D06-SR-001, D06-SW-001, D07-HS-001, D08-MU-001 — heat-stress, mulching, soft-rot, etc.). **`soil_temp_rootzone_c` → device-health frost rule** (`_predicate_frost` / `frost_risk` in `metrics.py:247`). *Both are used — by different engines.* The mapper also copies `soil_temp_rootzone_c` into the farm-brain, but no KB rule reads it. |
| **Soil moisture** | `soil_moisture_1_pct`, `soil_moisture_2_pct`, `soil_moisture_avg_pct` | The KB reads the **average**, via the alias **`soil_moisture_vwc`** (= `soil_moisture_avg_pct`) → **22 rules**, plus the derived **`vwc_status`** → 3 water-budget rules. `soil_moisture_avg_pct` also feeds **device-health** (`low_water`) and the **water-budget engine**. The two raw per-probe columns `soil_moisture_1_pct` / `soil_moisture_2_pct` are **stored only** (no consumer reads them individually). |
| **Soil EC / nutrients** | `soil_ec_ms_cm`, `soil_n_mg_kg`, `soil_p_mg_kg`, `soil_k_mg_kg`, `soil_{n,p,k}_bucket`, `npk_sensor_raw_hex` | The KB reads EC via the alias **`ec_current`** (= `soil_ec_ms_cm`) → 3 rules (D04-SB-001/002/003). The raw **N/P/K** sub-node values and buckets are **stored only** — KB nutrient logic uses the **lab soil test** (§A4) and `ec_current`, not the sub-node NPK probe. |
| **Irrigation flow / pump** | `water_flow_lpm`, `water_volume_liters_session/_cumulative`, `pump_running`, `pump_current_amps`, `pump_runtime_minutes_today`, `valve_status`, `dry_run_detected` | **`water_flow_lpm` → water-budget engine** (SUMmed into per-plant dose/deficit) **and device-health** (`dry_run`). `pump_running`, `pump_current_amps`, `dry_run_detected` → **device-health** `dry_run`. The `water_volume_*`, `valve_status`, `pump_runtime_minutes_today` columns are **stored only**. |
| **Battery / health** | `battery_voltage_v`, `battery_percent`, `solar_charging`, `low_battery_flag`, `tamper_detected`, `fault_flags`, `sensor_health_json`, `validation_warn`, `enclosure_temp_c`, `signal_rssi_dbm`, `firmware_version` | **Device-health engine** reads `battery_voltage_v`, `battery_percent` (battery alerts), `tamper_detected` (tamper), `fault_flags` + `sensor_health_json` + `validation_warn` (sensor_fault). `solar_charging`, `low_battery_flag`, `enclosure_temp_c`, `signal_rssi_dbm`, `firmware_version` are copied to the farm-brain but **no rule reads them** → effectively stored. |

**Directly KB-read columns:** `soil_temp_c` (7), `soil_ph` (5); plus `plot_id`/`farmer_id` (used only by the
two DPDP consent rules D12-DPDP-001/003). **KB-read via mapper alias:** `soil_moisture_avg_pct`→`soil_moisture_vwc`
(22) + `vwc_status` (3); `soil_ec_ms_cm`→`ec_current` (3).
**Device-health inputs:** `battery_voltage_v`, `battery_percent`, `soil_moisture_avg_pct`, `soil_temp_rootzone_c`,
`pump_running`, `pump_current_amps`, `water_flow_lpm`, `dry_run_detected`, `tamper_detected`, `validation_warn`,
`fault_flags`, `sensor_health_json`.
**Water-budget inputs:** `water_flow_lpm`, `soil_moisture_avg_pct`.

### A2. Weather

- **Weather station → `weather_station_readings`** (Main-Node BME280 etc., via MQTT). KB reads
  **`air_temp_max_c`** (29 rules — the most-used weather field), **`air_temp_min_c`** (4), **`dew_point_c`** (2),
  and `humidity_pct` via the alias **`rh_pct`** (10), plus derived `vpd_kpa` (2) and `wind_speed_ms` (1).
  Every other station column (pressure, wind, rain gauges, lux, UV, leaf-wetness, fog/frost/heat indices,
  station battery, fault flags) is **stored only**.
- **Weather forecast → `weather_forecasts`** (Open-Meteo nightly, live). Supplies the rainfall / dry-spell /
  evaporation / solar-radiation / VPD-night / severe-weather set the KB's D07 rules read
  (`rainfall_24h_mm`, `wind_gust_kmph`, `dry_spell_days`, `rain_gap_days`, `severe_weather_alert_active`,
  `effective_rainfall_mm`, `pan_evaporation_mm_day`, `solar_radiation_mj_m2`, `rainfall_deviation_pct`, …).
  Exact per-field list + rule counts in the Appendix.

### A3. Satellite & thermal → `satellite_data`

- **Sentinel-1/-2 (optical + SAR)** — 21 KB-read fields: `ndvi_mean`, `ndvi_delta_10d`, `ndre_mean`,
  `ndmi_mean`, `evi_mean`, `savi_mean`, `nbr_mean`, `sar_vv_db`, `sar_vh_db`, `sar_rvi`, peer/regional
  baselines (`plot_ndvi_baseline_peer`, `plot_ndre_gap_regional`, …), `scene_valid_pixel_pct`, etc.
  (D14 rules). Live on staging; a plot needs a boundary polygon.
- **Landsat LST** — `lst_c` → feeds the derived `cwsi` (crop water-stress index). Config-gated + currently
  blocked on USGS download access.

### A4. Agronomic DB inputs (entered via the dashboard pages)

These are copied into the farm-brain by name (the mapper's field tuples) and are the bulk of KB inputs.
Full per-field rule lists are in the Appendix; counts and how-used here:

| Source table | KB-read fields | Entry page | How used |
|---|---:|---|---|
| `crop_seasons` | 88 | Data Entry · AGRO | The agronomy plan: layout/beds, N-P-K plan & splits, mulch/earthing dates, drip geometry, VWC thresholds, seed & storage, target product — read across D02–D13. |
| `crop_scouting` | 37 | 🔎 Crop Scouting | Field observations: emergence, tillers, pest incidences, rot/wilt/leaf-spot, rhizome/ooze tests, dig samples — drive D05/D06 pest & disease rules. |
| `season_economics` | 32 | 📋 Season & Scheme Records | Costs, grades, prices, break-even, drip capital — drive D13 economics + D11 ceiling. |
| `season_operations` | 20 | 📋 Season & Scheme Records | Ops log: fertigation, last fungicide/insecticide group+date, herbicide dates, weeding/bait — D04/D05/D06. |
| `farmer_schemes` | 21 | 📋 Season & Scheme Records | Subsidy/scheme eligibility & status — D10. |
| `farmer_consent` | 9 | (consent flow) | DPDP consent/erasure flags — D12-DPDP. |
| `lab_soil_tests` | 5 (+`soil_test_available`) | 🧪 Lab Soil Test | Lab nutrients: `soil_oc_pct`, `soil_zn_ppm`, `soil_ca_ppm`, `soil_fe_ppm`, `soil_free_lime_pct` — D04 nutrient logic (the KB's real nutrient source, not the sub-node NPK probe). |
| `farms` | — (facts) | Data Entry | `soil_type`→derived `soil_texture_class`, `has_drip`, `dripper_lph`, `water_source_type`, `soil_depth_cm` — D02/D03/D08. |
| `farmers` | 6 | Data Entry | `district`, `taluka`, `agro_climatic_zone`, `advisory_language` — gating + delivery. |
| `plots` | 3 | seed / Data Entry | `plot_id`, `area_acre` (+ polygon for satellite). |

### A5. Derived / computed in the mapper (no table of their own)

`dap` (days-after-planting, from `sowing_date`), `current_stage`/`prediction_stage` (G0–G5), `cwsi`,
`vwc_status`, `soil_texture_class`/`soil_type`, `phi_days_remaining`, `model_version`, `vafsa_state`,
the **water-budget** ratios (`stage_water_deficit_ratio`, `per_plant_cumulative_vs_lifecycle_ratio`,
`variety_min/max_per_event_l`, `days_since_last_irrigation/flow`), the **D11 yield-model** outputs
(`predicted_yield_quintal_per_acre`, `cumulative_loss_pct`, `u_values_applied`, …), and the **D12 advisory
metrics** (`advisory_issued_count`, `action_compliance_rate`, …). See the Appendix buckets
`water_budget`, `yield_model(D11)`, `advisory_metrics`, `computed/derived(mapper)`.

### A6. Device-health engine (7 rules, evaluated per message — NOT via the mapper)

`app/domain/rule_definitions.py` + `metrics.py`. Inputs (from `node_sensor_readings`):

| Rule | Reads |
|---|---|
| `low_battery`, `battery_critical` | `battery_voltage_v`, `battery_percent` (→ battery_state) |
| `low_water` | `soil_moisture_avg_pct` (→ moisture deficit vs target) |
| `dry_run` | `dry_run_detected` OR (`pump_running` + `pump_current_amps` + `water_flow_lpm`) |
| `sensor_fault` | `validation_warn`, `fault_flags`, `sensor_health_json` |
| `frost` | `soil_temp_rootzone_c` (→ `frost_risk`) |
| `tamper` | `tamper_detected` |

### A7. Water-budget engine (D03-WB)

Reads `water_flow_lpm` (SUM → cumulative litres) + plot geometry (from `crop_seasons`) + variety targets
(`variety_stage_water_target`) → derives `vwc_status`, `stage_water_deficit_ratio`,
`per_plant_cumulative_vs_lifecycle_ratio`, `days_since_last_irrigation/flow`, which the 9 D03-WB rules read.

### A8. Advisory / delivery / DPDP

`ai_suggestions` (fired-rule outputs), `advisory_audit` (immutable record), `notification_dispatch_log`,
`farmer_actions` (replies → D12 compliance counters), `farmer_consent` (gates delivery). These are the
outputs/feedback of the pipeline rather than KB inputs.

---

## 4. PART B — Fields we JUST STORE (no consumer reads them)

Kept for completeness, audit, future rules, or debugging — but **no rule/engine reads them today**.

### B1. `node_sensor_readings` — stored, not consumed
`soil_moisture_1_pct`, `soil_moisture_2_pct` (only the average is used) · `soil_n_mg_kg`, `soil_p_mg_kg`,
`soil_k_mg_kg`, `soil_n_bucket`, `soil_p_bucket`, `soil_k_bucket`, `npk_sensor_raw_hex` (sub-node NPK probe —
KB uses the lab test instead) · `water_volume_liters_session`, `water_volume_liters_cumulative`,
`valve_status`, `pump_runtime_minutes_today` · `solar_charging`, `low_battery_flag`, `enclosure_temp_c`,
`signal_rssi_dbm`, `firmware_version`, `uptime_seconds`, `cadence_mode`, `backlog_pending` · plus routing/keys
(`reading_id`, `recorded_at`, `tenant_id`, `node_id`, `farm_id`, `received_at_master`, `transmission_type`).
*(Note: `soil_ec_ms_cm`, `soil_moisture_avg_pct`, `soil_temp_rootzone_c`, `water_flow_lpm`, battery/pump/fault
columns are NOT here — they are consumed, see Part A.)*

### B2. `weather_station_readings` — stored, not consumed
`air_temp_c`, `humidity_pct` (raw — KB uses min/max + `rh_pct` alias) · `atmospheric_pressure_hpa`, `altitude_m`,
`wind_speed_kmh`, `wind_speed_max_gust_kmh`, `wind_direction_degrees/_cardinal`, `rain_mm_current_hour`,
`rain_mm_today`, `rain_mm_last_7_days`, `rain_mm_this_season`, `light_intensity_lux`, `uv_index`,
`leaf_wetness_pct`, `fog_detected`, `fog_intensity`, `frost_risk`, `heat_stress_index`, `evapotranspiration_mm`,
`weather_station_battery_v`, `anemometer_fault`, `rain_gauge_fault` + keys.
*(Live weather for the KB comes from `weather_forecasts`; most station columns are redundant/held for when the
on-site station is fully trusted.)*

### B3. `main_node_readings` — gateway telemetry, not a KB input
No column is read by the KB/mapper. Consumers elsewhere: `sub_node_online` + `sub_node_silence_ms` +
`recorded_at` → **device watchdog** (DEVICE_OFFLINE) + the `main_node_heartbeat_total` metric. The raw
`bme280_*`, `ina219_*`, `rain_pulses_window`, `wind_pulses_window`, `wind_dir_adc` are raw master-node sensor
values (the **calibrated** weather equivalents land in `weather_station_readings`, which is what the KB reads).
`firmware_version` is copied to the farm-brain but unused.
`time_source`, `inserted_at`, keys = metadata.

### B4. Farm-brain fields the mapper POPULATES but no KB rule reads (30)
Copied into the per-plot snapshot but not read by any rule (some feed other things, noted):
`soil_moisture_1_pct`, `soil_moisture_2_pct`, `soil_temp_rootzone_c` *(→ device frost)*, `soil_ec_ms_cm`
*(→ KB via `ec_current`)*, `soil_n_mg_kg`, `soil_p_mg_kg`, `soil_k_mg_kg`, `soil_mg_ppm`, `soil_s_ppm`,
`battery_percent`/`battery_voltage_v` *(→ device)*, `enclosure_temp_c`, `signal_rssi_dbm`, `solar_charging`,
`low_battery_flag`, `tamper_detected` *(→ device)*, `firmware_version`, `humidity_pct` *(→ KB via `rh_pct`)*,
`crop_name_english`, `crop_name_marathi`, `crop_variety` *(→ water-budget targets)*, `expected_harvest_date`,
`sowing_date` *(→ `dap`)*, `days_to_harvest`, `current_month`, `sensor_pipe_position`, `plot_plants_estimated`
*(→ water-budget)*, `soil_texture_class_source`, `advisory_completed_count`, `gap_attributed_pct`, and the four
D12 claim-detection proposals (`brand_name_proposed`, `capability_claim_proposed`, `price_forecast_proposed`,
`profit_guarantee_proposed`). *Most are genuinely idle; the italicised ones feed a non-KB consumer or a
derivation.*

---

## 5. PART C — Dormant KB fields (76): a rule wants them, but no source feeds them yet

These are **not stored anywhere and not populated** — the rule stays silent (safe) until a source exists.
Grouped by what they need:

- **Farmer-app / scouting capture (doesn't exist yet):** `harvest_complete`, `emergence_observed`,
  `seed_treatment_planned`, `years_since_last_wilt`, `disease_event_recorded_in_season`, `processing_route`,
  `dry_ginger_produced/_in_storage`, `drying_in_progress`, `skin_removal_in_progress`, `photo_submitted`,
  `value_addition_being_considered`, `yield_expectation_requested`, `actual_yield_recorded`, `season_number`,
  `season_starting`, `preseason_planning`, …
- **Ops / cluster flags:** `soft_rot_confirmed_in_cluster`, `cluster_pest_alert_active`, `cibrc_verified`,
  `subsidy_application_pending`, `institutional_contact_made`, `scheduled_operation_completed/missed`,
  `basal_znso4_applied_kg_acre`, `basal_planning_active`, …
- **Engine / message-compose flags:** `chemical_option_about_to_be_shown`, `fungicide_option_about_to_be_shown`,
  `outgoing_message_contains_claim`, `differs_from_standard_marathi`, `provisional_threshold`,
  `low_confidence_decision`, `claim_type`, `local_terminology_used`, …
- **Time-series history / field test needed:** `ec_baseline`, `ec_trend_pct`, `saturation_hours`,
  `percolation_class`, `percolation_time_hours`, `leaf_wetness_hours`, `moisture_stress_period_started`,
  `saturation_event_occurred`.
- **Sub-node / weather-station derived (needs the hardware fully online):** `sub_node_ec_status`,
  `sub_node_moisture_status`, `station_id`, `station_data_age_hours`, `forecast_bias_correction_mm`,
  `monsoon_days_since_onset`, `local_hour`.
- **D12 QA workflow (not built):** `asr_used`, `bias_observation_count`.

*(The complete list is the `DORMANT(no source)` section of the Appendix.)*

---

## 6. Appendix — every KB-read field, grouped by source

The machine-generated table of all **416** KB-read fields with their rule counts and example rules follows
(§ below). It is the authoritative per-field "where used" index; the sections above interpret it.

---

## 7. Correctness checklist

Use this to verify the inventory and catch drift. Each item names the exact check.

### 7a. Schema ↔ mapper ↔ KB consistency
- [ ] **Every `r.<col>` the mapper reads is a real column.** Guarded by the generalized repo test
      `tests/infra/persistence/test_pg_repo_select_cols.py` (the k_source-class guard) — run `pytest -q tests/infra/persistence/test_pg_repo_select_cols.py`.
- [ ] **Every field a rule declares is declared in a domain `_schema`.** Guarded by the KB authoring
      **golden gate** (`pytest tests/kb/test_authoring_gates.py`). A missing declaration is a parse error.
- [ ] **Authoring `.py` expr == JSON expr** (no drift). Same gate (the **drift** check).
- [ ] **A field read by a rule but NOT populated by the mapper is intentional (dormant).** Cross-check the
      76 dormant fields (§5) against the regenerated list — a NEW dormant field usually means a rule shipped
      before its source. Decide: wire a source or confirm it should stay silent.
- [ ] **A field the mapper populates but no rule reads is intentional (alias / future / other-engine).**
      Cross-check the 30 (§B4) — a new one may be a typo'd field name (populated under the wrong key).

### 7b. Multi-sensor columns (your specific concern)
- [ ] **Soil temperature:** confirm `soil_temp_c` still feeds the KB and `soil_temp_rootzone_c` still feeds
      the device-health `frost` rule (`metrics.py` `frost_risk`). If a probe is re-wired, the two must not be swapped.
- [ ] **Soil moisture:** confirm the KB consumes the **average** via `soil_moisture_vwc` (not a single probe),
      and that `calibrate`/ingest actually writes `soil_moisture_avg_pct` (not only `_1`/`_2`).
- [ ] **EC / NPK:** confirm KB nutrient rules read the **lab test** fields + `ec_current`, and that the sub-node
      `soil_n/p/k_mg_kg` being empty does **not** silence a nutrient rule (it shouldn't — they don't read it).
- [ ] **Flow:** confirm `water_flow_lpm` is non-null when the pump runs (it feeds both `dry_run` and the
      water-budget engine); a silent flow sensor shows as `readings_fresh`/water-budget UNKNOWN, not a crash.

### 7c. Data correctness (per field, at runtime)
- [ ] **Calibration:** raw ADC → engineering units matches `device_calibration` (soil %, battery V, flow L/min,
      NPK). Spot-check on the **Pipeline Inspector** dashboard (raw↔calibrated side-by-side).
- [ ] **Units & ranges:** soil_moisture 0–100 %, battery within pack range, soil_temp plausibly 0–50 °C,
      flow ≥ 0. The ingest validators flag out-of-range (see **Stage Health**).
- [ ] **Freshness:** each live source produced a recent row — `node_sensor_readings` < 6 h, `weather_forecasts`
      covers today, `satellite_data` within revisit. The **System Diagnostics** page / `make diagnose` checks this.
- [ ] **Derivation integrity:** `dap` recomputed from `sowing_date` (not a frozen snapshot); `vwc_status` matches
      `soil_moisture_avg_pct` vs thresholds; `cwsi` present only when `lst_c` is.
- [ ] **No duplicate / stale advisories:** `no_duplicate_advisories` invariant green (diagnostics battery).
- [ ] **Coverage:** on the **Daily Run Inspector**, the per-plot farm-brain shows the expected filled vs UNKNOWN
      fields — a field that should be filled but is UNKNOWN points at a broken source or an unentered dashboard page.

### 7d. Regenerate & re-verify this doc
- [ ] After any KB reload, mapper change, or readings-schema migration, **re-run the extraction** (§8) and
      diff the headline numbers (§2) and the Appendix. A jump in "dormant" or "populated-unused" is the signal
      to investigate.

---

## 8. How this was generated (re-run to refresh)

Scripts live in the session scratchpad; the logic: parse `knowledge_base/Domain*_Rules_Ginger*.json`
(`farm_brain_schema` per rule → field→rule map), import `build_farm_brain` for the mapper field tuples
(`_SEASON_PLAN_FIELDS`, `_SCOUTING_FIELDS`, `_ECON_FIELDS`, `_OPS_FIELDS`, `_SCHEMES_FIELDS`,
`_CONSENT_FIELDS`, `SYNTHETIC_FIELDS`) + `_set(state, "…")` literals, and read the ORM models for the
readings columns. Device-health inputs come from `app/domain/metrics.py` + `rule_definitions.py`.

---

---

## Appendix — every KB-read field, grouped by source (machine-generated)

_Total distinct fields read by rule `farm_brain_schema`: **416**. A field is 'read by the KB' if it appears in any rule's `farm_brain_schema`. `#rules` = how many of the 495 rules declare it._

### sub_node_sensor — 4 fields
| field | #rules | example rules |
|---|---:|---|
| `farmer_id` | 1 | D12-DPDP-001 |
| `plot_id` | 1 | D12-DPDP-003 |
| `soil_ph` | 5 | D02-BF-002, D02-CA-001, D02-SL-001, D02-ST-001 … |
| `soil_temp_c` | 7 | D01-TM-001, D03-MU-001, D03-SC-003, D06-SR-001 … |

### sub_node_sensor(alias) — 2 fields
| field | #rules | example rules |
|---|---:|---|
| `ec_current` | 3 | D04-SB-001, D04-SB-002, D04-SB-003 |
| `soil_moisture_vwc` | 22 | D01-HV-002, D01-HW-001, D01-PH-008, D02-CA-002 … |

### weather_station — 3 fields
| field | #rules | example rules |
|---|---:|---|
| `air_temp_max_c` | 29 | D01-HV-002, D01-TM-001, D01-TM-002, D02-CA-002 … |
| `air_temp_min_c` | 4 | D01-TM-002, D07-TM-001, D07-TM-002, D07-TM-003 |
| `dew_point_c` | 2 | D07-HU-002, D07-WS-003 |

### weather_forecast — 2 fields
| field | #rules | example rules |
|---|---:|---|
| `forecast_rain_48h_mm` | 5 | D07-BC-001, D07-CY-001, D07-HS-004, D07-MO-001 … |
| `predicted_yield_quintal_per_acre` | 4 | D11-CL-002, D11-PR-001, D11-PR-002, D11-VL-001 |

### satellite(Sentinel) — 21 fields
| field | #rules | example rules |
|---|---:|---|
| `evi_mean` | 1 | D14-NV-001 |
| `nbr_delta_10d` | 1 | D14-NV-007 |
| `nbr_mean` | 1 | D14-NV-007 |
| `ndmi_delta_10d` | 6 | D14-FU-001, D14-FU-002, D14-FU-005, D14-NM-001 … |
| `ndmi_mean` | 3 | D14-NM-001, D14-NM-002, D14-NM-003 |
| `ndre_mean` | 4 | D14-FU-004, D14-NR-001, D14-NR-002, D14-NR-003 |
| `ndvi_delta_10d` | 4 | D14-AN-003, D14-NR-002, D14-NV-004, D14-PH-004 |
| `ndvi_mean` | 9 | D14-FU-005, D14-NR-002, D14-NV-001, D14-NV-003 … |
| `ndvi_std` | 2 | D14-AN-002, D14-NV-001 |
| `plot_ndre_baseline_regional` | 2 | D14-FU-004, D14-NR-003 |
| `plot_ndre_gap_regional` | 2 | D14-FU-004, D14-NR-003 |
| `plot_ndvi_baseline_peer` | 2 | D14-AN-001, D14-NV-005 |
| `plot_ndvi_gap_peer` | 1 | D14-NV-005 |
| `plot_ndvi_gap_regional` | 1 | D14-NV-003 |
| `previous_crops_3yr` | 6 | D02-SL-003, D05-IP-002, D05-TC-002, D06-BW-001 … |
| `previous_stage` | 1 | D03-SB-003 |
| `sar_coherence` | 2 | D14-SR-001, D14-SR-003 |
| `sar_vh_db` | 1 | D14-SR-001 |
| `sar_vv_db` | 2 | D14-SR-001, D14-SR-002 |
| `sar_vv_delta_db` | 4 | D14-FU-003, D14-SR-001, D14-SR-002, D14-SR-004 |
| `savi_mean` | 1 | D14-NV-001 |

### satellite_lst(Landsat) — 1 fields
| field | #rules | example rules |
|---|---:|---|
| `lst_c` | 2 | D14-LT-001, D14-LT-002 |

### crop_seasons — 88 fields
| field | #rules | example rules |
|---|---:|---|
| `affected_plants_removed` | 2 | D06-DX-002, D06-SR-002 |
| `azospirillum_psb_done` | 3 | D04-BI-001, D04-PP-002, D05-CH-007 |
| `bed_former_arranged` | 2 | D08-CA-001, D08-LY-004 |
| `bed_height_cm` | 5 | D02-DR-002, D02-DR-004, D02-LY-002, D02-ST-002 … |
| `bed_width_cm` | 4 | D02-LY-002, D02-LY-003, D08-LY-002, D08-LY-004 |
| `biofumigation_done` | 1 | D06-BW-003 |
| `bud_orientation_instructed` | 1 | D08-PL-001 |
| `calibration_date` | 1 | D03-SB-002 |
| `calibration_done` | 4 | D03-SB-002, D12-COLD-001, D12-COLD-002, D12-ROAD-001 |
| `crop_coefficient_kc` | 2 | D03-WR-002, D03-WR-003 |
| `deep_ploughing_done` | 6 | D02-CL-001, D02-TL-001, D02-TL-002, D08-CA-001 … |
| `drainage_levels_present` | 14 | D02-CL-001, D02-DR-002, D02-DR-003, D03-WL-001 … |
| `drainage_outlet_present` | 1 | D02-DR-001 |
| `drip_efficiency_measured` | 1 | D03-WS-001 |
| `drip_flow_lph_per_acre` | 2 | D03-DS-002, D03-SC-001 |
| `drip_lateral_spacing_ft` | 3 | D03-DS-001, D03-DS-002, D08-LY-002 |
| `drip_shifts_per_day` | 3 | D03-SC-002, D03-SC-003, D03-SC-004 |
| `dripper_spacing_cm` | 2 | D03-DS-001, D03-DS-002 |
| `drippers_per_acre` | 1 | D03-DS-002 |
| `dry_recovery_pct_actual` | 2 | D09-SL-001, D09-SL-002 |
| `drying_method` | 7 | D09-PR-001, D09-PR-002, D09-PR-003, D09-SF-001 … |
| `drying_space_ready` | 1 | D09-DR-004 |
| `earthing_up_2_date` | 1 | D08-EU-004 |
| `earthing_up_date` | 26 | D01-PH-004, D03-MU-002, D04-NS-002, D05-NE-003 … |
| `field_history_rot` | 7 | D01-VR-002, D01-VR-003, D02-SL-003, D06-PV-002 … |
| `field_history_wilt` | 11 | D01-VR-002, D01-VR-003, D02-SL-003, D05-TC-002 … |
| `furrow_width_cm` | 4 | D02-DR-002, D02-DR-004, D02-LY-002, D08-LY-002 |
| `fym_fully_decomposed` | 6 | D02-OM-002, D02-OM-003, D05-IP-002, D05-NE-002 … |
| `fym_t_per_acre` | 11 | D02-CA-001, D02-CL-001, D02-OM-001, D02-OM-002 … |
| `gap_filling_done` | 1 | D08-GF-001 |
| `harvest_route` | 9 | D09-DR-004, D09-MT-001, D09-MT-003, D09-MT-004 … |
| `hot_water_treatment_done` | 3 | D09-PH-002, D11-AP-003, D11-EC-004 |
| `intercrop_selected` | 5 | D08-IC-001, D08-IC-002, D08-IC-003, D10-SUB-005 … |
| `k_applied_kg_per_acre` | 3 | D04-NU-002, D04-PK-001, D04-PK-002 |
| `k_late_split_1_date` | 3 | D04-DG-004, D04-PK-001, D08-EU-004 |
| `k_late_split_2_date` | 2 | D04-DG-004, D04-PK-002 |
| `k_source` | 2 | D04-PK-003, D04-SB-003 |
| `k_target_kg_per_acre` | 5 | D04-FG-003, D04-NP-001, D04-NP-002, D04-NP-003 … |
| `limiting_nutrient` | 1 | D04-NU-001 |
| `main_drain_connected` | 3 | D02-DR-002, D02-DR-004, D07-CY-002 |
| `marigold_planted` | 3 | D05-TC-001, D05-TC-002, D08-IC-002 |
| `micronutrient_basal_done` | 1 | D04-MC-003 |
| `micronutrient_spray_1_done` | 3 | D04-MC-001, D04-MC-004, D13-MI-002 |
| `micronutrient_spray_2_done` | 2 | D04-MC-002, D04-MC-004 |
| `moisture_probe_depth_cm` | 3 | D01-HW-001, D01-PH-008, D03-SB-001 |
| `mulch_stage_1_done` | 10 | D03-MU-001, D06-LS-003, D06-MU-001, D07-HS-001 … |
| `mulch_stage_2_done` | 8 | D03-MU-002, D04-NS-002, D06-MU-001, D08-BN-001 … |
| `mulch_stage_3_done` | 4 | D03-MU-002, D06-MU-001, D08-EU-004, D08-MU-002 |
| `n_applied_kg_per_acre` | 2 | D04-NS-001, D04-NS-003 |
| `n_split_1_date` | 2 | D04-NS-001, D05-NE-001 |
| `n_split_2_date` | 3 | D04-NS-002, D08-BN-001, D08-EU-001 |
| `n_target_kg_per_acre` | 6 | D04-NP-001, D04-NP-002, D04-NP-003, D04-NU-001 … |
| `neem_cake_basal_kg_per_acre` | 3 | D04-OR-001, D04-OR-002, D04-OR-003 |
| `neem_cake_earthing_kg_per_acre` | 4 | D04-NS-002, D04-OR-001, D05-NE-003, D08-BN-002 |
| `p_applied_kg_per_acre` | 1 | D04-PP-001 |
| `p_target_kg_per_acre` | 4 | D04-NP-001, D04-NP-003, D04-PP-001, D04-PP-002 |
| `pan_coefficient_kp` | 1 | D03-WR-002 |
| `perennial_weeds_removed` | 3 | D02-WD-001, D08-TL-003, D08-WD-004 |
| `planting_depth_cm` | 1 | D08-PL-002 |
| `planting_layout` | 11 | D01-YD-001, D02-CL-001, D02-LY-001, D02-LY-002 … |
| `plants_per_acre` | 3 | D08-LY-001, D08-LY-003, D13-SD-002 |
| `ppe_available` | 3 | D09-PR-001, D09-PR-003, D09-SF-001 |
| `processing_trained_operator` | 4 | D09-PR-001, D09-PR-002, D09-SF-001, D10-INST-004 |
| `produce_washed` | 6 | D09-GD-001, D09-GD-003, D09-HV-001, D09-HV-003 … |
| `rows_per_bed` | 2 | D08-LY-002, D08-LY-003 |
| `season_water_plan_basis` | 7 | D07-CC-003, D07-MO-003, D07-RF-001, D07-RF-003 … |
| `seasonal_water_requirement_litres` | 1 | D03-WS-001 |
| `seed_at_planting_kg` | 10 | D08-LY-003, D08-PL-003, D08-SS-001, D10-INS-003 … |
| `seed_buds_per_piece` | 1 | D08-PL-003 |
| `seed_piece_weight_g` | 3 | D08-LY-003, D08-PL-003, D13-SD-002 |
| `seed_storage_loss_pct` | 5 | D08-SS-001, D08-SS-002, D13-SL-001, D13-SL-002 … |
| `seed_storage_method` | 5 | D08-SS-001, D08-SS-002, D09-PH-002, D13-SL-002 … |
| `seed_stored_kg` | 7 | D08-SS-001, D08-SS-002, D08-SS-003, D09-PH-002 … |
| `shade_pct` | 2 | D08-IC-003, D10-SUB-005 |
| `so2_treatment_used` | 4 | D09-PR-002, D09-PR-003, D09-SF-001, D10-REG-003 |
| `solarization_done` | 6 | D02-CL-001, D02-SN-001, D05-IP-002, D06-BW-003 … |
| `solarization_weeks` | 1 | D02-SN-001 |
| `storage_loss_monthly_pct` | 4 | D09-SL-001, D09-ST-001, D09-ST-002, D09-ST-003 |
| `target_product` | 9 | D01-HV-001, D01-HV-003, D01-HV-004, D01-VR-001 … |
| `trichoderma_kg_per_acre` | 4 | D02-OM-003, D05-NE-002, D06-PV-001, D11-EC-004 |
| `vwc_field_capacity` | 1 | D03-SB-002 |
| `vwc_saturation` | 4 | D03-MN-002, D03-SB-002, D03-WL-001, D04-FG-001 |
| `vwc_stress_threshold` | 1 | D03-WR-004 |
| `water_available_oct_feb_litres` | 9 | D03-WS-001, D07-CC-002, D07-RF-001, D07-RF-003 … |
| `water_stress_after_earthing_done` | 1 | D08-EU-003 |
| `water_withdrawal_pct` | 2 | D09-WW-001, D09-WW-002 |
| `water_withdrawal_start_date` | 1 | D09-WW-001 |
| `water_withdrawal_started` | 2 | D03-WW-001, D03-WW-002 |

### crop_scouting — 37 fields
| field | #rules | example rules |
|---|---:|---|
| `central_shoot_dead` | 4 | D06-DX-001, D06-DX-003, D12-CLS-001, D12-IMG-002 |
| `emergence_started` | 1 | D08-WD-001 |
| `establishment_pct` | 8 | D01-PH-002, D08-GF-001, D08-PL-001, D08-SS-003 … |
| `exposed_rhizomes_observed` | 4 | D05-RF-002, D08-EU-001, D08-EU-005, D08-PL-002 |
| `flowering_observed` | 4 | D01-PH-002, D01-PH-004, D04-NS-003, D08-EU-002 |
| `harvest_injury_observed` | 4 | D09-HV-001, D09-HV-002, D09-ST-001, D09-WW-002 |
| `leaf_caterpillar_observed` | 1 | D05-LC-001 |
| `leaf_roller_incidence_pct` | 2 | D05-LR-001, D05-SC-001 |
| `leaf_spot_incidence_pct` | 2 | D06-DX-005, D06-LS-003 |
| `leaf_spot_rings_visible` | 2 | D06-DX-005, D07-HS-002 |
| `leaf_yellowing_pattern` | 7 | D04-DG-001, D04-DG-002, D04-DG-003, D04-DG-004 … |
| `light_trap_count_nightly` | 3 | D05-SH-001, D05-SH-002, D12-LOG-004 |
| `light_trap_installed` | 2 | D05-SH-001, D12-LOG-004 |
| `moisture_pct_final` | 1 | D09-ST-003 |
| `nematode_suspected` | 8 | D05-NE-001, D05-NE-003, D05-NE-004, D05-SW-002 … |
| `ooze_test_result` | 2 | D06-CH-001, D06-DX-002 |
| `plant_pulls_easily` | 1 | D05-WG-002 |
| `rhizome_fly_incidence_pct` | 2 | D05-RF-003, D05-SC-001 |
| `rhizome_smell` | 1 | D06-DX-003 |
| `rhizome_texture` | 2 | D06-DX-003, D06-DX-004 |
| `rot_incidence_pct` | 9 | D06-DX-003, D09-GD-003, D09-HV-002, D09-HV-003 … |
| `sample_dig_120_done` | 1 | D01-PH-006 |
| `sample_dig_180_done` | 2 | D01-PH-007, D11-PR-002 |
| `seed_sprouts_visible` | 1 | D08-SS-003 |
| `shoot_borer_incidence_pct` | 2 | D05-SC-001, D05-SH-002 |
| `shoot_pulls_out_easily` | 1 | D06-DX-003 |
| `skin_scrape_result` | 5 | D09-GD-003, D09-MT-001, D09-MT-002, D09-MT-003 … |
| `soft_rhizome_found` | 3 | D05-RF-003, D05-SW-002, D08-GF-001 |
| `standing_water_hours_observed` | 1 | D02-DR-001 |
| `stem_cut_colour` | 2 | D06-DX-001, D06-DX-004 |
| `stem_hole_with_webbing` | 1 | D05-SH-002 |
| `stem_ooze_type` | 1 | D06-DX-002 |
| `straight_line_holes_in_whorl` | 2 | D05-LC-001, D12-IMG-002 |
| `tillers_per_plant` | 4 | D01-PH-002, D05-NE-001, D08-EU-003, D08-GR-002 |
| `white_grub_suspected` | 4 | D05-WG-001, D05-WG-002, D05-WG-003, D12-CLU-002 |
| `wilt_incidence_pct` | 3 | D06-CH-001, D06-DX-002, D09-YD-001 |
| `wilt_while_green` | 3 | D06-DX-001, D06-DX-002, D12-CLS-001 |

### season_economics — 32 fields
| field | #rules | example rules |
|---|---:|---|
| `breakeven_price_per_quintal` | 5 | D13-AD-001, D13-AD-004, D13-BE-001, D13-BE-002 … |
| `breakeven_yield_quintal` | 2 | D13-AD-004, D13-BE-001 |
| `cash_flow_gap_months` | 3 | D13-AD-004, D13-CF-001, D13-CF-002 |
| `cash_outflow_to_date` | 1 | D13-CF-001 |
| `ceiling_quintal_per_acre` | 7 | D11-CL-001, D11-CL-002, D11-EC-001, D11-PR-003 … |
| `cost_drainage` | 3 | D13-CS-001, D13-MI-002, D13-SN-003 |
| `cost_earthing_labour` | 1 | D13-CS-003 |
| `cost_harvest_transport` | 3 | D13-AD-003, D13-CS-002, D13-CS-003 |
| `cost_micronutrients` | 2 | D13-CS-001, D13-MI-002 |
| `cost_mulch` | 4 | D13-AD-003, D13-CS-001, D13-MI-001, D13-SN-003 |
| `cost_seed` | 6 | D13-AD-003, D13-RP-001, D13-RR-004, D13-SD-001 … |
| `cost_seed_treatment_planting` | 2 | D13-SD-003, D13-SN-003 |
| `crop_loan_taken` | 3 | D13-CF-001, D13-CF-002, D13-CF-003 |
| `drip_annual_share` | 2 | D13-BE-002, D13-CP-001 |
| `drip_capital_cost` | 2 | D13-CP-001, D13-CP-002 |
| `drip_life_years` | 1 | D13-CP-001 |
| `grade_a_pct` | 7 | D09-GD-001, D09-GD-002, D09-MK-002, D09-PH-001 … |
| `grade_b_pct` | 6 | D09-GD-001, D09-GD-002, D09-MK-002, D09-YD-001 … |
| `grade_c_pct` | 6 | D09-GD-001, D09-GD-002, D09-MK-002, D09-YD-001 … |
| `graded_separately` | 6 | D09-GD-001, D09-GD-002, D09-GD-003, D09-HV-001 … |
| `intercrop_revenue` | 1 | D13-CF-002 |
| `interest_cost` | 2 | D13-BE-002, D13-CF-003 |
| `land_rent_or_opportunity` | 1 | D13-BE-002 |
| `mulch_material_price_per_tonne` | 1 | D13-MI-001 |
| `mulch_quantity_t_per_acre` | 1 | D13-MI-001 |
| `net_return_per_acre` | 8 | D13-AD-001, D13-AD-002, D13-RV-001, D13-RV-002 … |
| `sale_market` | 7 | D09-MK-002, D09-MK-003, D09-MK-004, D10-CROP-001 … |
| `sale_price_per_quintal` | 21 | D09-DR-004, D09-GD-001, D09-GD-002, D09-MK-001 … |
| `seed_opportunity_cost` | 2 | D13-RP-001, D13-SL-001 |
| `seed_retained_or_purchased` | 3 | D13-RP-001, D13-RP-002, D13-RP-003 |
| `total_cost_per_acre` | 15 | D13-AD-003, D13-BE-001, D13-CF-001, D13-CP-002 … |
| `transport_cost_per_quintal` | 6 | D09-MK-002, D09-MK-003, D10-MKT-001, D10-MKT-002 … |

### season_operations — 20 fields
| field | #rules | example rules |
|---|---:|---|
| `basal_k_kg_per_acre` | 1 | D02-BF-001 |
| `basal_p_kg_per_acre` | 2 | D02-BF-001, D02-BF-002 |
| `castor_bait_prepared_date` | 1 | D05-RF-001 |
| `castor_bait_units_per_acre` | 1 | D05-RF-001 |
| `drip_runtime_min` | 8 | D03-SC-001, D03-SC-002, D03-SC-003, D03-SC-004 … |
| `ethephon_spray_count` | 2 | D08-GR-002, D08-GR-003 |
| `fertigation_active` | 5 | D04-FG-001, D04-FG-002, D04-FG-003, D04-SB-002 … |
| `fertigation_last_ec_response` | 1 | D04-SB-002 |
| `herbicide_post_emergent_date` | 3 | D08-WD-001, D08-WD-002, D08-WD-005 |
| `herbicide_pre_emergent_date` | 1 | D08-WD-005 |
| `irrigation_applied_litres_today` | 7 | D03-MN-001, D03-MN-002, D03-MN-003, D03-SC-001 … |
| `kulav_passes` | 3 | D02-TL-001, D08-TL-001, D08-TL-002 |
| `labour_arranged_date` | 4 | D08-BN-002, D08-CA-002, D08-LB-001, D13-CS-003 |
| `last_fungicide_date` | 4 | D06-CH-003, D06-LS-002, D06-SR-002, D09-SF-002 |
| `last_fungicide_group` | 3 | D06-DX-003, D06-LS-001, D06-LS-002 |
| `last_insecticide_date` | 6 | D05-CH-003, D05-CH-004, D05-CH-005, D05-CH-006 … |
| `last_insecticide_group` | 2 | D05-CH-001, D05-CH-004 |
| `metarhizium_kg_per_acre` | 1 | D05-WG-001 |
| `naa_spray_count` | 2 | D08-GR-001, D08-GR-003 |
| `weeding_count` | 3 | D08-CA-002, D08-WD-003, D08-WD-004 |

### farmer_schemes — 21 fields
| field | #rules | example rules |
|---|---:|---|
| `cgwb_block_category` | 1 | D10-REG-002 |
| `cibrc_list_checked_date` | 3 | D10-FRESH-001, D10-INST-001, D12-COLD-003 |
| `data_review_due` | 3 | D10-FRESH-001, D10-FRESH-002, D12-COLD-003 |
| `drip_subsidy_pct_applicable` | 7 | D10-APP-004, D10-FRESH-002, D10-GEO-001, D10-SUB-001 … |
| `drought_prone_listed` | 2 | D10-ACT-001, D10-GEO-001 |
| `farm_pond_planned` | 5 | D10-APP-002, D10-REG-002, D10-SUB-004, D10-SUB-006 … |
| `farmer_category` | 2 | D10-APP-004, D10-SUB-001 |
| `geo_tagging_done` | 1 | D10-APP-003 |
| `kvk_contacted` | 3 | D10-ACT-001, D10-INST-002, D10-INST-003 |
| `pmfby_notified_for_ginger` | 1 | D10-INS-001 |
| `pre_sanction_date` | 2 | D10-APP-003, D10-SUB-002 |
| `pre_sanction_received` | 1 | D10-SUB-002 |
| `priority_category` | 1 | D10-APP-004 |
| `research_centre_contacted` | 3 | D10-ACT-001, D10-INST-001, D10-INST-002 |
| `scale_of_finance_per_acre` | 2 | D10-INS-002, D13-CF-003 |
| `seed_supplier_identified` | 9 | D10-ACT-001, D10-CROP-001, D10-INS-003, D10-VAR-001 … |
| `soil_lab_selected` | 2 | D10-INST-003, D10-LAB-001 |
| `subsidy_applied_date` | 3 | D10-ACT-001, D10-APP-002, D10-SUB-001 |
| `subsidy_documents_ready` | 2 | D10-APP-001, D10-APP-004 |
| `subsidy_lottery_result` | 4 | D10-SUB-002, D10-SUB-003, D10-SUB-006, D13-CP-002 |
| `subsidy_scheme_applied` | 8 | D10-APP-002, D10-APP-003, D10-FRESH-001, D10-FRESH-002 … |

### farmer_consent — 9 fields
| field | #rules | example rules |
|---|---:|---|
| `cluster_anonymised` | 4 | D12-CLU-001, D12-CLU-002, D12-DPDP-002, D12-DPDP-003 |
| `consent_advisory` | 4 | D12-CLU-001, D12-DPDP-001, D12-DPDP-002, D12-ROAD-001 |
| `consent_date` | 2 | D12-DPDP-001, D12-DPDP-002 |
| `consent_research` | 2 | D12-DPDP-002, D12-DPDP-003 |
| `data_retention_until` | 2 | D12-DPDP-001, D12-DPDP-004 |
| `deletion_requested` | 1 | D12-DPDP-004 |
| `sat_attribution_shown` | 1 | D14-DP-002 |
| `sat_public_display_context` | 1 | D14-DP-001 |
| `third_party_share_consent_given` | 1 | D14-DP-001 |

### lab_soil_test — 5 fields
| field | #rules | example rules |
|---|---:|---|
| `soil_ca_ppm` | 1 | D04-SN-002 |
| `soil_ec` | 3 | D02-SL-001, D02-ST-001, D04-PK-003 |
| `soil_fe_ppm` | 4 | D02-CA-001, D02-ST-001, D04-MC-001, D10-LAB-001 |
| `soil_free_lime_pct` | 10 | D02-BF-002, D02-CA-001, D02-CA-002, D02-OM-001 … |
| `soil_zn_ppm` | 5 | D02-CA-001, D02-ST-001, D04-MC-001, D04-MC-003 … |

### farmer_facts — 6 fields
| field | #rules | example rules |
|---|---:|---|
| `advisory_language` | 7 | D12-ARCH-001, D12-LANG-001, D12-LANG-002, D12-MOD-001 … |
| `agro_climatic_zone` | 4 | D04-MC-005, D07-CL-001, D07-CL-002, D10-ACZ-001 |
| `days_since_last_flow_reading` | 1 | D03-WB-006 |
| `days_since_last_irrigation` | 2 | D03-WB-001, D03-WB-004 |
| `district` | 1 | D10-ACZ-001 |
| `taluka` | 2 | D10-ACZ-001, D10-GEO-001 |

### plot_facts — 3 fields
| field | #rules | example rules |
|---|---:|---|
| `area_acre` | 20 | D02-LY-003, D03-WS-001, D07-RF-001, D08-LY-003 … |
| `plot_area_ha` | 3 | D14-AN-001, D14-AN-002, D14-PL-001 |
| `plot_polygon_wkt` | 1 | D14-PL-001 |

### advisory_metrics — 3 fields
| field | #rules | example rules |
|---|---:|---|
| `action_compliance_rate` | 6 | D12-EVAL-001, D12-EVAL-003, D12-LANG-002, D12-POS-002 … |
| `advisory_completed_on_time_count` | 1 | D12-EVAL-001 |
| `advisory_issued_count` | 3 | D12-EVAL-001, D12-LANG-001, D12-LANG-002 |

### yield_model(D11) — 3 fields
| field | #rules | example rules |
|---|---:|---|
| `prediction_stage` | 5 | D11-PR-001, D11-PR-002, D11-PR-003, D11-PR-004 … |
| `yield_quintal_per_acre_actual` | 5 | D09-YD-001, D10-CROP-003, D11-EC-003, D12-EVAL-003 … |
| `yield_target_quintal_per_acre` | 11 | D01-YD-001, D01-YD-002, D04-FG-003, D04-NP-002 … |

### water_budget — 5 fields
| field | #rules | example rules |
|---|---:|---|
| `per_plant_cumulative_vs_lifecycle_ratio` | 1 | D03-WB-007 |
| `per_plant_water_stage_cumulative_l` | 1 | D03-WB-005 |
| `planting_geometry_incomplete` | 1 | D03-WB-008 |
| `stage_water_deficit_ratio` | 3 | D03-ST-001, D03-WB-001, D03-WB-002 |
| `vwc_status` | 3 | D03-WB-001, D03-WB-002, D03-WB-004 |

### computed(synthetic) — 1 fields
| field | #rules | example rules |
|---|---:|---|
| `days_to_planting` | 1 | D14-NV-006 |

### computed/derived(mapper) — 74 fields
| field | #rules | example rules |
|---|---:|---|
| `blocklist_reason` | 1 | D05-CH-008 |
| `blocklist_source_ref` | 1 | D05-CH-008 |
| `ceiling_basis` | 1 | D11-CL-001 |
| `cluster_id` | 7 | D12-CLU-001, D12-CLU-002, D12-DPDP-003, D12-EVAL-003 … |
| `cumulative_loss_pct` | 5 | D11-DC-001, D11-FM-001, D11-FM-004, D11-VL-001 … |
| `current_stage` | 74 | D01-HV-001, D01-HV-002, D01-HV-004, D01-PH-001 … |
| `cwsi` | 6 | D14-FU-001, D14-FU-002, D14-FU-005, D14-LT-001 … |
| `dap` | 70 | D01-HV-001, D01-HV-002, D01-HV-003, D01-HV-004 … |
| `dripper_lph` | 2 | D03-DS-001, D03-DS-002 |
| `dry_spell_days` | 1 | D07-MO-002 |
| `effective_rainfall_mm` | 2 | D03-MN-001, D07-RF-005 |
| `false_alarm_count` | 1 | D12-EVAL-002 |
| `farmer_alert_type` | 1 | D05-CH-008 |
| `flow_telemetry_field_exists` | 1 | D03-WB-006 |
| `fog_days_consecutive` | 2 | D06-LS-001, D07-HU-002 |
| `fog_observed` | 3 | D07-HU-002, D07-HU-004, D07-VP-003 |
| `forecast_source` | 4 | D07-BC-001, D07-BC-002, D07-BC-003, D07-MO-003 |
| `gap_unexplained_pct` | 1 | D11-GA-003 |
| `harvest_date` | 6 | D09-HV-001, D09-HV-002, D09-HV-003, D09-HV-004 … |
| `has_drip` | 14 | D02-CL-001, D02-CL-002, D02-LY-001, D02-LY-004 … |
| `heat_stress_days_count` | 3 | D07-HS-001, D07-HS-002, D07-HS-004 |
| `interdependence_group` | 3 | D11-DC-001, D11-DC-002, D11-FM-004 |
| `model_version` | 7 | D12-ARCH-001, D12-CLS-002, D12-MOD-001, D12-MOD-002 … |
| `ndre_slope_5d` | 2 | D14-NR-001, D14-NR-002 |
| `ndvi_freshness_days` | 4 | D14-NV-001, D14-NV-002, D14-PH-001, D14-PH-002 |
| `optical_gap_days` | 2 | D14-PL-002, D14-SR-005 |
| `pan_evaporation_mm_day` | 4 | D03-WR-002, D07-WS-001, D07-WS-003, D07-WS-004 |
| `pest_scouting_date` | 3 | D05-SC-001, D05-SW-001, D07-HU-003 |
| `phi_blocklist_hit` | 1 | D05-CH-008 |
| `phi_days_remaining` | 3 | D05-CH-003, D06-CH-003, D09-SF-002 |
| `photo_labelled_count` | 2 | D12-IMG-002, D12-ROAD-002 |
| `photo_uploaded_count` | 1 | D12-ROAD-001 |
| `planting_date` | 23 | D01-PH-001, D01-PW-002, D02-CL-001, D02-CL-002 … |
| `planting_doy` | 1 | D01-PW-001 |
| `plot_cloud_pct` | 3 | D14-NM-001, D14-NR-001, D14-NV-001 |
| `plot_ndvi_baseline_regional` | 2 | D14-AN-001, D14-NV-003 |
| `plot_status` | 2 | D04-MC-005, D06-BW-004 |
| `prediction_interval_pct` | 7 | D11-PR-001, D11-PR-002, D11-PR-003, D11-PR-004 … |
| `rain_gap_days` | 4 | D03-MN-003, D03-MN-004, D03-WR-004, D07-MO-002 |
| `rainfall_24h_mm` | 1 | D07-CY-WX-001 |
| `rainfall_deviation_pct` | 5 | D07-CC-003, D07-RF-001, D07-RF-002, D07-RF-004 … |
| `rainfall_last_48h_mm` | 3 | D14-SR-002, D14-SR-003, D14-SR-004 |
| `rainfall_mm` | 14 | D02-DR-003, D02-TL-003, D03-MN-001, D03-WL-002 … |
| `rainfall_ytd_mm` | 7 | D07-CC-001, D07-CC-003, D07-CL-003, D07-RF-002 … |
| `rh_pct` | 10 | D05-SW-001, D06-SR-001, D06-SW-001, D06-SW-002 … |
| `sar_gap_days` | 7 | D14-FU-003, D14-PL-002, D14-SR-001, D14-SR-002 … |
| `sar_rvi` | 1 | D14-SR-001 |
| `sat_advisory_confidence` | 16 | D14-FU-001, D14-FU-002, D14-FU-004, D14-FU-005 … |
| `sat_pipeline_version` | 2 | D14-NV-001, D14-PL-003 |
| `sat_source` | 7 | D14-DP-002, D14-LT-001, D14-NM-001, D14-NR-001 … |
| `scene_valid_pixel_pct` | 9 | D14-NM-001, D14-NR-001, D14-NV-001, D14-NV-003 … |
| `season_record_complete` | 4 | D11-GA-002, D11-UV-002, D12-LOG-001, D12-ROAD-001 |
| `seed_cost_per_kg` | 2 | D13-SD-001, D13-SD-004 |
| `severe_weather_alert_active` | 2 | D07-CY-001, D07-HS-003 |
| `soil_depth_cm` | 1 | D02-SL-002 |
| `soil_oc_pct` | 5 | D02-OM-001, D02-OM-004, D02-ST-001, D04-OR-002 … |
| `soil_test_available` | 8 | D02-BF-001, D02-ST-001, D04-NP-001, D04-SB-001 … |
| `soil_texture_class` | 6 | D02-TL-001, D03-DS-001, D03-SC-002, D03-WW-002 … |
| `soil_type` | 4 | D02-LY-001, D02-LY-004, D02-SL-001, D08-LY-001 |
| `solar_radiation_mj_m2` | 3 | D07-HU-003, D07-WS-001, D07-WS-002 |
| `stage_source` | 4 | D01-PH-001, D01-PH-002, D01-PH-003, D07-TM-003 |
| `true_alarm_count` | 1 | D12-EVAL-002 |
| `u_value_source_class` | 9 | D11-FM-002, D11-FM-003, D11-UV-001, D11-UV-002 … |
| `u_values_applied` | 13 | D11-AP-001, D11-AP-002, D11-DC-001, D11-DC-002 … |
| `vafsa_state` | 7 | D02-TL-002, D02-TL-003, D03-SC-005, D05-CH-005 … |
| `variety` | 20 | D01-HV-003, D01-PH-001, D01-VR-001, D01-YD-001 … |
| `variety_max_per_event_l` | 1 | D03-WB-003 |
| `variety_min_per_event_l` | 1 | D03-WB-004 |
| `vpd_kpa` | 2 | D07-VP-001, D07-VP-002 |
| `vpd_night_mean_kpa` | 2 | D07-VP-001, D07-VP-003 |
| `water_source_type` | 3 | D03-WS-001, D07-CC-002, D10-REG-002 |
| `wind_gust_kmph` | 1 | D07-CY-WX-001 |
| `wind_speed_ms` | 1 | D07-WS-001 |
| `yield_prediction_interval_pct` | 1 | D01-PH-007 |

### DORMANT(no source) — 76 fields
| field | #rules | example rules |
|---|---:|---|
| `action_not_recorded_within_3days` | 1 | D12-AL-001 |
| `actual_yield_recorded` | 2 | D09-YD-002, D11-GA-001 |
| `asr_used` | 2 | D12-VOC-001, D12-VOI-001 |
| `basal_planning_active` | 1 | D04-SN-001 |
| `basal_znso4_applied_kg_acre` | 1 | D04-MC-005 |
| `bias_observation_count` | 5 | D07-BC-001, D07-BC-002, D07-BC-003, D12-COLD-001 … |
| `biological_input_date` | 1 | D04-BI-002 |
| `biological_seed_treatment_date` | 1 | D06-ST-002 |
| `chemical_input_date` | 1 | D04-BI-002 |
| `chemical_option_about_to_be_shown` | 1 | D05-CH-002 |
| `chemical_recommendation_pending` | 1 | D10-REG-001 |
| `chemical_seed_treatment_date` | 1 | D06-ST-002 |
| `cibrc_verified` | 1 | D10-REG-001 |
| `claim_type` | 7 | D14-POS-001, D14-POS-002, D14-POS-003, D14-POS-004 … |
| `cluster_pest_alert_active` | 2 | D05-WG-003, D12-CLU-002 |
| `differs_from_standard_marathi` | 1 | D12-VOC-002 |
| `disease_event_recorded_in_season` | 1 | D11-SC-003 |
| `dry_ginger_in_storage` | 1 | D09-ST-002 |
| `dry_ginger_produced` | 1 | D09-YD-003 |
| `drying_in_progress` | 1 | D09-DR-003 |
| `durable_fact_learned_in_conversation` | 1 | D12-LOG-002 |
| `ec_baseline` | 2 | D04-SB-002, D04-SB-003 |
| `ec_trend_pct` | 2 | D04-PK-003, D04-SB-003 |
| `emergence_observed` | 1 | D01-PH-005 |
| `farmer_scout_report_days_ago` | 2 | D14-AN-004, D14-PL-002 |
| `forecast_bias_correction_mm` | 2 | D07-BC-001, D07-BC-003 |
| `fresh_price_crashed` | 1 | D09-SL-003 |
| `fresh_share_low` | 1 | D09-SL-003 |
| `fungicide_option_about_to_be_shown` | 1 | D06-CH-002 |
| `gap_attribution_complete` | 1 | D11-GA-003 |
| `hardware_upgrade_pending` | 1 | D03-SB-004 |
| `harvest_complete` | 3 | D06-FH-001, D09-YD-004, D11-GA-001 |
| `institutional_contact_made` | 1 | D10-ACT-002 |
| `leaf_wetness_hours` | 6 | D06-LS-001, D06-SW-002, D07-HU-002, D07-VP-003 … |
| `local_experience_sought` | 1 | D10-CROP-002 |
| `local_hour` | 1 | D09-DR-003 |
| `local_terminology_used` | 1 | D12-VOC-002 |
| `low_confidence_decision` | 1 | D12-AL-002 |
| `moisture_stress_period_started` | 1 | D11-RC-002 |
| `monsoon_days_since_onset` | 1 | D14-AN-003 |
| `outgoing_message_contains_claim` | 7 | D14-POS-001, D14-POS-002, D14-POS-003, D14-POS-004 … |
| `per_plant_dose_l_last_event` | 2 | D03-WB-003, D03-WB-004 |
| `percolation_class` | 6 | D02-DR-001, D02-DR-004, D02-ST-002, D03-SC-002 … |
| `percolation_time_hours` | 3 | D02-DR-001, D02-ST-002, D10-LAB-002 |
| `pest_count` | 1 | D05-SC-002 |
| `pest_planning_active` | 1 | D05-PC-001 |
| `pest_recommendation_pending` | 1 | D05-IP-001 |
| `photo_submitted` | 1 | D12-IMG-001 |
| `preseason_planning` | 1 | D11-SC-001 |
| `processing_route` | 2 | D09-DR-001, D09-PW-001 |
| `provisional_threshold` | 1 | D05-SC-002 |
| `saturation_event_occurred` | 1 | D11-RC-002 |
| `saturation_hours` | 12 | D03-WL-001, D03-WL-002, D03-WL-003, D06-SR-001 … |
| `scheduled_operation_completed` | 1 | D11-RC-003 |
| `scheduled_operation_missed` | 1 | D11-RC-003 |
| `scout_report_days_ago` | 1 | D04-DG-002 |
| `scout_request_pending` | 1 | D14-AN-004 |
| `season_number` | 1 | D12-IMG-001 |
| `season_omissions_recorded` | 1 | D11-SC-002 |
| `season_starting` | 1 | D11-GA-002 |
| `seed_treatment_planned` | 1 | D06-ST-001 |
| `skin_removal_in_progress` | 1 | D09-DR-002 |
| `soft_rot_confirmed_in_cluster` | 1 | D06-FH-002 |
| `spray_scheduled_today` | 1 | D07-VP-002 |
| `station_data_age_hours` | 1 | D07-VP-001 |
| `station_id` | 4 | D07-BC-001, D07-WS-001, D07-WS-002, D07-WS-004 |
| `sub_node_ec_status` | 2 | D14-FU-004, D14-FU-005 |
| `sub_node_moisture_status` | 8 | D14-FU-001, D14-FU-002, D14-FU-003, D14-FU-005 … |
| `subsidy_application_pending` | 1 | D10-APP-001 |
| `symptom_diagnosis_pending` | 1 | D12-AL-002 |
| `threshold_source` | 1 | D05-SC-002 |
| `unexpected_outcome` | 1 | D12-AL-002 |
| `value_addition_being_considered` | 1 | D09-PW-001 |
| `water_supply_status` | 1 | D03-WS-002 |
| `years_since_last_wilt` | 1 | D06-BW-001 |
| `yield_expectation_requested` | 1 | D11-SC-001 |

### Source summary
| source | #KB-read fields |
|---|---:|
| sub_node_sensor | 4 |
| sub_node_sensor(alias) | 2 |
| weather_station | 3 |
| weather_forecast | 2 |
| satellite(Sentinel) | 21 |
| satellite_lst(Landsat) | 1 |
| crop_seasons | 88 |
| crop_scouting | 37 |
| season_economics | 32 |
| season_operations | 20 |
| farmer_schemes | 21 |
| farmer_consent | 9 |
| lab_soil_test | 5 |
| farmer_facts | 6 |
| plot_facts | 3 |
| advisory_metrics | 3 |
| yield_model(D11) | 3 |
| water_budget | 5 |
| computed(synthetic) | 1 |
| computed/derived(mapper) | 74 |
| DORMANT(no source) | 76 |