# AgroGuardian V2 — Data Inventory & Flow

**Purpose:** exhaustive reference of every table and every field in the backend, with a **source label** on each field so anyone can answer the question "where does this value come from and who's responsible for it?"

Ground truth: the migration files in `alembic/versions/`. This document is a human-readable projection. When the two disagree, the migrations win — update this doc.

**Latest changes (2026-09-05, v2.1 firmware + Round 17):**

- `node_sensor_readings.uptime_seconds` — now actually populated (was schema-only). Sub Node emits `UP=<seconds>` in the CSV.
- `node_sensor_readings.fault_flags` — now populated when the Sub Node hits a recoverable sensor failure. Tags today: `npk_short`, `npk_hdr`, `npk_crc`, `ds18_disc`.
- `node_sensor_readings.backlog_pending` — now populated. Main Node SD outbox drainer flips this to `true` on replayed packets.
- `weather_station_readings` — now actually populated. Round 17 promoted the Main Node's `master_readings` block out of `Reading.sensor_health_json` into this table, keyed on `(master_node_id, recorded_at)`. Both v2-raw (bundled) and v2-master (heartbeat) paths write. See §3.13 below.
- `weather_station_readings.wind_speed_max_gust_kmh` — the underlying `wind_gust_pulses_max` is now emitted by the Main Node; backend calibration to km/h is a rollup pending Round 18.

---

## Part 1 — Data source glossary

Every field in the schema comes from exactly one of these sources. The abbreviation appears in the "Source" column of every table below.

| Code | Source | Who / what produces it | When |
|---|---|---|---|
| **SN** | Sub Node sensor | ATmega328P + capacitive soil probe + NPK Modbus probe + DS18B20 + flow sensor + battery + pressure transducer | Every 5 min while device is powered |
| **MN** | Main Node sensor | ESP32 + BME280 (air temp/humidity/pressure) + INA219 (bus V, current) + tipping-bucket rain gauge + anemometer + wind vane | Every 5 min (heartbeat) or bundled onto Sub Node telemetry |
| **WSS** | Water-source sensor | Ultrasonic level sensor in well/borewell/farm pond + optional turbidity/pH/EC probe | Every 10–15 min (planned; not yet deployed) |
| **SAT** | Satellite | Sentinel-2, Sentinel-1, Landsat-8, MODIS, SMAP, Planet | Cadence depends on constellation (5–16 days typical); backend polls |
| **WAPI** | Weather forecast API | Open-Meteo / IMD (planned) | Every 3–6 hours; backend polls |
| **FI** | Farmer at install | Farmer answers during onboarding, one-time | Once, at signup |
| **FO** | Farmer ongoing | Farmer via WhatsApp reply, app entry, or SMS | Whenever; opportunistic |
| **TECH** | Technician at install | Field engineer completing the installation form | Once per hardware install |
| **OPS** | Ops team (staff) | Agronomist / admin / service / technician via internal tools | On demand |
| **DEALER** | Dealer / partner | Reseller entering account creation for a farmer | Signup only |
| **SYS** | System (auto-generated) | Backend code — UUIDs, timestamps, counters, hashes | Every write |
| **DERIVED** | Derived by backend | Backend computes from other stored data (aggregations, rule outputs, deltas) | On write or on batch schedule |
| **LLM** | Claude LLM | Sonnet or Haiku, invoked by `compose_advisory` or the Ginger Engine | Per-alert or daily 06:30 IST |
| **CAL** | Device calibration row | Field team's `UPDATE device_calibration SET …` after physical measurement | Once during commissioning; updated rarely |
| **FW** | Firmware constant | Compiled into the firmware image and reported over MQTT | On device flash |
| **AUTH** | Auth flow output | Argon2id hash, JWT claim, OTP generation | On login/verify |
| **AUDIT** | Audit trigger | Postgres trigger writing to `audit_log` on any INSERT/UPDATE/DELETE of watched tables | Every mutation |
| **AGRO** | Agronomy team, curated | Ginger Engine KB content — 431 rules + stage catalogue + Farm Brain schema hand-authored by the agronomy team, imported via a single 1.16 MB SQL blob per KB release | Once per KB release; versioned via `kb_domains.version` |

---

## Part 2 — Data flow at a glance

```
                       ┌───── Sub Node (buried) ─────┐
                       │ Soil / battery / pressure    │  Every 5 min:
                       │ NPK Modbus / flow / DS18B20  │  ── CSV over LoRa 433 MHz ──►
                       └──────────────────────────────┘
                                                              │
                                                              ▼
                       ┌───── Main Node (mast) ──────┐
                       │ BME280 / INA219 / rain /    │
                       │ wind — its own weather      │  Every 5 min: master heartbeat
                       │ station.                    │──JSON via MQTT-TLS over 4G──►
                       │ SD card outbox on outage.   │  ("v2-raw" or "v2-master")
                       └─────────────────────────────┘
                                                              │
                                                              ▼
                                            Caddy L4 TLS → Mosquitto
                                                              │
                                                              ▼
                                            IngestBroker (paho → asyncio)
                                            • parse $schema
                                            • fetch device_calibration
                                            • apply calibration formulas
                                            • normalise clock skew
                                            • save Reading (Sub Node) or
                                              MainNodeReading (heartbeat)
                                            • evaluate 7 device-health rules
                                            • NOTIFY agro_events
                                                              │
       ┌──────────────────────────────────────────────────────┼──────────────────────────┐
       ▼                                                      ▼                          ▼
node_sensor_readings                                 main_node_readings           alerts_notifications
weather_station_readings (Round 17)                                                       │
water_source_status (planned)                                                             │
                                                                                          ▼
       ▲                                                                     compose_advisory (Claude)
       │                                                                     → ai_suggestions
       │                                                                     → WhatsApp (Round 14)
       │                                                                                  │
       │                                                                                  ▼
       │                                                                          farmer_actions
       │                                                                          (WhatsApp replies)
       │
       │  Daily 06:30 IST batch:
       │  • Ginger Engine reads 431 rules over the day's data
       │  • satellite_data (Sentinel-2 NDVI, SMAP moisture) refresh
       │  • weather_forecasts (Open-Meteo) refresh
       │  • product_performance_bi aggregate
       │  • ai_learning_log records outcome vs suggestion
```

**Key principle:** data always flows *into* the DB from a *single* source of truth for each field. Derived fields are recomputed, never entered by hand. Farmer-entered fields never overwrite sensor readings.

---

## Part 3 — Tables by domain

### Legend

- **PK** column ends with `PK`.
- **FK** column ends with `FK`.
- **Source** column uses the codes from Part 1.
- Fields marked with **`*`** are Round 16+ additions; marked with **`†`** are Round 17.5 (this session).

---

## Group A — Farmer & farm identity

Established during onboarding, updated rarely.

### 3.1 `tenants` (1 row per organisation / pilot)

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` PK | UUID | SYS | Auto `gen_random_uuid()`. Pilot = `11111111-1111-1111-1111-111111111111`. |
| `name` | TEXT | OPS | Business name of the org. |
| `slug` | TEXT UNIQUE | OPS | URL-safe identifier. |
| `tier` | TEXT | OPS | `pilot_internal` / `basic` / `standard` / `pro`. |
| `features` | JSONB | OPS | Feature-flag blob. |
| `created_at` | TIMESTAMPTZ | SYS | Auto `now()`. |

### 3.2 `farmers` (1 row per human farmer)

| Field | Type | Source | Notes |
|---|---|---|---|
| `farmer_id` PK | UUID | SYS | Auto. |
| `tenant_id` FK | UUID | SYS | From auth context. |
| `full_name` | TEXT | FI | English/roman. |
| `marathi_name` | TEXT | FI | Devanagari. |
| `phone_primary` | TEXT | FI | E.164. |
| `phone_secondary` | TEXT | FI | Optional. |
| `whatsapp_number` | TEXT | FI | May equal `phone_primary`. |
| `phone_hash` | BYTEA | DERIVED | HMAC-SHA256 for lookup; unique index. |
| `phone_encrypted` | BYTEA | DERIVED | AES-GCM ciphertext (planned). |
| `language_preference` | TEXT | FI | `marathi` / `hindi` / `english`. |
| `village`, `taluka`, `district`, `state`, `pin_code` | TEXT | FI | Address block. |
| `aadhar_number`, `farmer_id_govt` | TEXT | FI | Government IDs. |
| `education_level` | TEXT | FI | `primary`/`secondary`/`graduate`/`illiterate`. |
| `age_years` | INT | FI | |
| `gender` | TEXT | FI | `male`/`female`/`other`. |
| `account_created_at` | TIMESTAMPTZ | SYS | Auto. |
| `account_status` | TEXT | OPS | `active`/`inactive`/`suspended`. |
| `subscription_tier` | TEXT | DEALER | `basic`/`standard`/`pro`/`custom`. |
| `subscription_start`, `subscription_end` | DATE | DEALER | Billing dates. |
| `payment_status` | TEXT | SYS | Updated by billing job. |
| `referred_by` | TEXT | FI | Word-of-mouth referrer name. |
| `dealer_id` | TEXT | DEALER | Reseller code. |
| `notes` | TEXT | OPS | Free-form. |

### 3.3 `farms` (1 row per farm — a farmer may have several)

| Field | Type | Source | Notes |
|---|---|---|---|
| `farm_id` PK | UUID | SYS | Auto. |
| `tenant_id`, `farmer_id` FK | UUID | SYS | Context. |
| `farm_name`, `survey_number` | TEXT | FI | Farmer / land record identifiers. |
| `total_area_acre` | NUMERIC | FI | |
| `gps_lat_center`, `gps_lng_center` | FLOAT | TECH | Recorded by technician at install; falls back to farmer's phone GPS. |
| `gps_boundary_geojson` | JSONB | TECH | Polygon walked by the technician's tool. |
| `soil_type` | TEXT | FI | `black`/`red`/`sandy`/`loamy`/`mixed` — farmer knowledge. |
| `soil_texture`, `soil_depth_cm`, `soil_organic_carbon_pct` | mixed | OPS | From optional lab test. |
| `water_holding_capacity` | TEXT | DERIVED | Inferred from soil_type + organic carbon. |
| `terrain_type`, `elevation_m` | TEXT / FLOAT | TECH | Observed on-site. |
| `water_source_primary`, `water_source_secondary` | TEXT | FI | Well / borewell / pond / canal / tanker / rain. |
| `well_depth_ft`, `borewell_depth_ft` | INT | FI | Farmer knowledge. |
| `borewell_yield_lpm` | FLOAT | TECH | Measured during install (yield test). |
| `farm_pond_capacity_liters` | FLOAT | FI | |
| `irrigation_type` | TEXT | FI | `drip`/`sprinkler`/`flood`/`furrow`/`mixed`. |
| `drip_emitter_lph` | FLOAT | FI | Nominal emitter flow. |
| `irrigation_area_acre` | NUMERIC | FI | |
| `electricity_source` | TEXT | FI | `grid`/`solar_pump`/`generator`/`mixed`. |
| `solar_pump_hp`, `generator_fuel` | FLOAT / TEXT | FI | |
| `electricity_feeder_name`, `electricity_schedule_known` | TEXT / BOOL | FI | |
| `electricity_schedule_json` | JSONB | FI or DERIVED | Farmer-declared schedule; overridden by learned schedule (see `electricity_schedule_log`). |
| `road_access`, `nearest_town_km` | BOOL / FLOAT | TECH | |
| `mobile_network_quality` | TEXT | TECH | Observed at install. |
| `previous_crops_json` | JSONB | FI | History disclosed at signup. |
| `created_at`, `updated_at` | TIMESTAMPTZ | SYS | Auto. |

### 3.4 `plots` (1 row per irrigable plot within a farm — pilot has 2)

| Field | Type | Source | Notes |
|---|---|---|---|
| `plot_id` PK | TEXT | OPS or SYS | Deterministic: `PLOT_PILOT_001`, `PLOT_PILOT_002`. |
| `tenant_id`, `farm_id` FK | UUID | SYS | Context. |
| `plot_number` | INT | OPS | 1, 2, 3… per farm. |
| `plot_name` | TEXT | FI | Farmer's own name for the plot. |
| `area_acre` | NUMERIC | FI | |
| `gps_lat`, `gps_lng` | FLOAT | TECH | Centre of plot. |
| `gps_boundary_geojson` | JSONB | TECH | Polygon. |
| `node_id` FK | TEXT | SYS | Sub Node covering this plot; nullable for satellite-only plots (Round 4). |
| `soil_type_override` | TEXT | OPS | Optional plot-specific soil type (rare). |
| `crop_current_season_id` FK | UUID | SYS | Points to active `crop_seasons` row. |
| `irrigation_valve_id` | TEXT | TECH | Physical valve identifier. |
| `drip_line_count` | INT | TECH | |
| `plot_status` | TEXT | OPS or FO | `active`/`fallow`/`harvested`. |
| `created_at` | TIMESTAMPTZ | SYS | Auto. |

The **`data_tier`** column (0004) records `hardware` vs `satellite_only` for each plot. Trigger keeps it consistent with `node_id IS NULL`.

### 3.5 `crop_seasons` (1 row per crop per plot per season)

| Field | Type | Source | Notes |
|---|---|---|---|
| `season_id` PK | UUID | SYS | Auto. |
| `tenant_id`, `farm_id`, `plot_id` FK | mixed | SYS | Context. |
| `season_name` | TEXT | OPS | E.g. "Kharif 2026 — Ginger Mahima". |
| `season_type` | TEXT | OPS | `kharif`/`rabi`/`summer`/`perennial`. |
| `year` | INT | OPS | Calendar year of sowing. |
| `crop_name_marathi`, `crop_name_english`, `crop_variety` | TEXT | FI or OPS | Pilot: Ginger, variety Mahima. |
| `crop_category` | TEXT | OPS | `cereal`/`pulse`/`oilseed`/`vegetable`/`fruit`/`cash_crop`/`fodder`. |
| `sowing_date`, `transplanting_date`, `expected_harvest_date`, `actual_harvest_date` | DATE | FI | Farmer-declared. Actual back-filled. |
| `sowing_date_inferred` | BOOL | DERIVED | TRUE if backend guessed from NDVI onset. |
| `seed_rate_kg_per_acre`, `seed_cost_per_kg` | FLOAT/NUMERIC | FI | |
| `base_fertilizer_at_sowing` | TEXT | FI | Free-form. |
| `crop_age_days_today` | INT | DERIVED | `now() - sowing_date`, refreshed daily. |
| `current_growth_stage` | TEXT | DERIVED | Ginger Engine's stage classifier. |
| `days_to_harvest` | INT | DERIVED | `expected_harvest_date - now()`. |
| `target_yield_qtl_per_acre`, `actual_yield_qtl_per_acre` | FLOAT | FI or DERIVED | Target from farmer expectation; actual from post-harvest weigh-in. |
| `total_water_used_liters` | FLOAT | DERIVED | Sum of `irrigation_events.water_liters`. |
| `total_fertilizer_cost_rs`, `total_pesticide_cost_rs` | NUMERIC | DERIVED | Sum of `farmer_actions.*_cost_rs`. |
| `season_status` | TEXT | OPS or DERIVED | `active`/`completed`/`abandoned`. |
| `notes` | TEXT | OPS | |
| `created_at` | TIMESTAMPTZ | SYS | |

---

## Group B — Hardware & devices

Set at install time, updated during service visits.

### 3.6 `device_registry` (1 row per physical device — Main Node, Sub Node, weather station)

| Field | Type | Source | Notes |
|---|---|---|---|
| `device_id` PK | TEXT | OPS | Deterministic: `AGR-MN-0001`, `AGR-SN-0001`. |
| `tenant_id`, `farm_id`, `plot_id` FK | mixed | SYS | Deployment context. |
| `device_type` | TEXT | OPS | `master_node`/`sub_node`/`weather_station`. |
| `serial_number`, `mac_address`, `qr_code_data` | TEXT | TECH | Read from hardware label at install. |
| `device_tier` | TEXT | OPS | `basic`/`standard`/`pro`. |
| `manufacture_date`, `batch_number`, `pcb_version` | mixed | OPS | Traceability. |
| `firmware_version_installed` | TEXT | FW | Reported by every MQTT payload; `viraai-mn-1.0.0-raw` etc. |
| `firmware_version_latest` | TEXT | OPS | Latest available from OTA. |
| `ota_pending`, `last_ota_update`, `last_ota_result` | mixed | SYS | OTA pipeline (Phase 8, not built). |
| `installation_date`, `installation_technician_id` | DATE / TEXT | TECH | |
| `gps_installed_lat`, `gps_installed_lng` | FLOAT | TECH | Where the device physically sits. |
| `pole_height_ft`, `enclosure_type` | mixed | TECH | |
| `sim_number`, `sim_provider` | TEXT | TECH | Pilot uses `airtel`. |
| `signal_4g_strength` | TEXT | TECH or DERIVED | Observed at install; refreshed from `master_readings.ina219_bus_v` history? no — from RSSI reports (planned). |
| `last_heartbeat_at` | TIMESTAMPTZ | DERIVED † | `MAX(main_node_readings.recorded_at)` — refreshed by trigger or read query. |
| `heartbeat_interval_min` | INT | FW | 5 for the current firmware. |
| `device_status` | TEXT | DERIVED | `online`/`offline`/`fault`/`maintenance` — updated by ops-alert rules. |
| `warranty_expiry` | DATE | OPS | |
| `total_uptime_hours`, `total_downtime_hours`, `fault_count` | mixed | DERIVED | Aggregated periodically. |
| `replacement_flag` | BOOL | OPS | Flagged for RMA. |
| `notes` | TEXT | OPS | |
| `broker_secret_hash` | TEXT | SYS | Argon2id hash of the device's MQTT password. |
| `calibration_json` | JSONB | OPS | Legacy — replaced by `device_calibration` (Round 16). |

### 3.7 `device_calibration` (Round 16 — 1 row per Sub Node)

Set once during commissioning, updated when the field team dials in a probe.

| Field | Type | Source | Notes |
|---|---|---|---|
| `tenant_id` + `device_id` PK | mixed | SYS + OPS | Composite primary key. |
| `soil_dry_adc`, `soil_wet_adc` | INT | CAL | Measured during calibration day. |
| `battery_vref_v` | NUMERIC | CAL | ADC reference (~3.3 V). |
| `battery_divider_ratio` | NUMERIC | CAL | ~3.2 for 220 k + 100 k. |
| `pressure_offset_v`, `pressure_scale_bar_per_v` | NUMERIC | CAL | From manometer test. |
| `flow_pulses_per_litre` | NUMERIC | CAL | From bucket test (typ. 450). |
| `flow_window_seconds` | NUMERIC | CAL | Cadence fallback; **overridden at runtime** by `raw_readings.window_s` when v2 firmware sends it. |
| `npk_temp_divisor`, `npk_moisture_divisor`, `npk_ph_divisor` | NUMERIC | CAL | Register divisors (10/10/100 typical for JXCT). |
| `calibration_version` | INT | SYS | Bumped by trigger on every UPDATE. |
| `updated_at` | TIMESTAMPTZ | SYS | Trigger. |
| `updated_by` | TEXT | OPS | Free-form. |
| `notes` | TEXT | OPS | E.g. "Calibrated after monsoon 2027 recalibration". |

### 3.8 `component_inventory` (1 row per replaceable part — sensor, battery, MOSFET, etc.)

| Field | Type | Source | Notes |
|---|---|---|---|
| `component_id` PK | UUID | SYS | |
| `device_id` FK | TEXT | SYS | Parent device. |
| `component_name`, `component_category` | TEXT | OPS | `sensor`/`power`/`communication`/`protection`/`valve`/`camera`/`other`. |
| `manufacturer`, `model_number`, `serial_number` | TEXT | OPS | Traceability. |
| `purchase_date`, `purchase_cost_rs`, `supplier`, `warranty_months` | mixed | OPS | Sourcing metadata. |
| `installation_date` | DATE | TECH | |
| `status` | TEXT | OPS | `active`/`faulty`/`replaced`/`removed`. |
| `last_calibration_date`, `next_calibration_due` | DATE | OPS | For probes needing periodic recalibration. |
| `calibration_values_json` | JSONB | OPS | Free-form; distinct from Round-16 `device_calibration`. |
| `fault_history_json` | JSONB | DERIVED | Filled from `service_maintenance` records. |
| `replacement_component_id` | UUID | OPS | Chain to successor when replaced. |
| `notes` | TEXT | OPS | |

### 3.9 `calibration_history` (append-only log; per device × sensor)

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` PK | UUID | SYS | |
| `device_id` FK | TEXT | SYS | |
| `sensor` | TEXT | OPS | e.g. `soil_moisture`, `ph`, `pressure`. |
| `slope`, `intercept` | NUMERIC | CAL | Two-point calibration curve. |
| `lab_id` | TEXT | OPS | Which lab certified the values. |
| `calibrated_at` | TIMESTAMPTZ | OPS | When the lab performed the test. |
| `recorded_at` | TIMESTAMPTZ | SYS | When we ingested the record. |

### 3.10 `technician_installations` (1 row per site visit)

| Field | Type | Source | Notes |
|---|---|---|---|
| `installation_id` PK | UUID | SYS | |
| `technician_id`, `technician_name`, `technician_phone` | TEXT | OPS | Staff master data. |
| `farm_id`, `farmer_id` FK | UUID | SYS | Context. |
| `visit_type` | TEXT | TECH | `installation`/`service`/`upgrade`/`inspection`/`replacement`. |
| `visit_date`, `arrival_time`, `departure_time`, `duration_hours` | mixed | TECH | Timesheet. |
| `devices_installed_json` | JSONB | TECH | Which devices were mounted. |
| `nodes_installed_count`, `solar_panels_installed`, `poles_installed`, `cable_meters_laid` | INT / FLOAT | TECH | Physical bill of work. |
| `soil_type_observed`, `moisture_at_install` | TEXT / FLOAT | TECH | Hand-observations. |
| `well_depth_measured_ft`, `borewell_yield_tested_lpm`, `farm_pond_level_pct` | mixed | TECH | Physical measurements. |
| `water_quality_check` | TEXT | TECH | Free-form. |
| `electricity_tested`, `signal_4g_tested`, `signal_4g_result` | BOOL / TEXT | TECH | Bring-up tests. |
| `whatsapp_test_sent`, `sensors_calibrated`, `farmer_training_done` | BOOL | TECH | Checklist. |
| `farmer_training_topics` | TEXT | TECH | What was covered. |
| `installation_photos_urls` | JSONB | TECH | R2/B2 URLs. |
| `issues_found`, `issues_resolved`, `pending_work` | TEXT | TECH | Narrative. |
| `farmer_signature_collected` | BOOL | TECH | |
| `installation_quality_score` | INT (1–10) | TECH | Self-assessed. |
| `next_service_due` | DATE | OPS | |
| `notes` | TEXT | TECH | |

### 3.11 `service_maintenance` (1 row per repair / preventive service)

| Field | Type | Source | Notes |
|---|---|---|---|
| `service_id` PK | UUID | SYS | |
| `device_id`, `farm_id` FK | mixed | SYS | Context. |
| `technician_id` | TEXT | OPS | |
| `service_date` | DATE | TECH | |
| `service_type` | TEXT | OPS | `preventive`/`corrective`/`emergency`/`upgrade`/`calibration`. |
| `complaint_description`, `root_cause`, `action_taken` | TEXT | TECH | Post-visit narrative. |
| `components_replaced_json` | JSONB | TECH | Links to component_inventory entries. |
| `spare_parts_cost_rs`, `labour_cost_rs` | NUMERIC | TECH | |
| `downtime_hours`, `resolution_time_hours` | FLOAT | DERIVED | From timestamps. |
| `firmware_updated`, `new_firmware_version` | BOOL / TEXT | SYS | |
| `service_status` | TEXT | OPS | `completed`/`pending`/`escalated`. |
| `farmer_satisfaction` | INT (1–5) | FO | Post-service survey. |
| `warranty_claim` | BOOL | OPS | |
| `notes` | TEXT | TECH | |

---

## Group C — Live telemetry (streaming)

Highest volume. All rows are idempotent by `(device_id, recorded_at)`.

### 3.12 `node_sensor_readings` (Sub Node telemetry — one row every 5 min per Sub Node)

Post-Round-16 the row is derived from a **v2-raw payload + `device_calibration`**. Pre-Round-16 the row was populated directly from a **v2** (calibrated) payload.

| Field | Type | Source | Notes |
|---|---|---|---|
| `reading_id` PK | BIGINT | SYS | Auto. |
| `tenant_id`, `node_id`, `farm_id`, `plot_id`, `farmer_id` FK | mixed | SYS | Context, derived from `NODE_ID → PLOT_ID → farm/farmer`. |
| `recorded_at` | TIMESTAMPTZ | MN | Main Node stamps time from NTP/RTC; broker's `_normalize_clock_skew` corrects impossible values. |
| `received_at_master` | TIMESTAMPTZ | MN | When the Main Node saw the LoRa frame. |
| `transmission_type` | TEXT | FW | `lora` for the pilot. |
| `signal_rssi_dbm` | INT | MN | `LoRa.packetRssi()` at RX. |
| `battery_voltage_v` | FLOAT | SN + CAL | Raw ADC × cal.battery_vref_v / 1023 × divider_ratio. |
| `battery_percent`, `solar_charging`, `low_battery_flag` | mixed | DERIVED | Threshold-based; not always populated. |
| `soil_moisture_1_pct` | FLOAT | SN + CAL | Capacitive probe: `(DRY-raw)/(DRY-WET) × 100`, clamped 0–100. |
| `soil_moisture_2_pct` | FLOAT | SN + CAL | NPK-probe's own moisture register (raw/10). Null when `npk_ok=false`. |
| `soil_moisture_avg_pct` | FLOAT | DERIVED | Currently = `soil_moisture_1_pct`; averaging planned. |
| `soil_temp_c` | FLOAT | SN | DS18B20 native °C. |
| `soil_temp_rootzone_c` | FLOAT | SN + CAL | NPK temp register (raw/10). |
| `soil_ph` | FLOAT | SN + CAL | NPK pH register (raw/100). |
| `soil_ec_ms_cm` | FLOAT | SN | NPK EC register (µS/cm) / 1000. |
| `soil_n_mg_kg`, `soil_p_mg_kg`, `soil_k_mg_kg` | FLOAT | SN | NPK N/P/K registers, sensor-native mg/kg. |
| `soil_n_bucket`, `soil_p_bucket`, `soil_k_bucket` | INT (0–63) | DERIVED | Bucketed for compactness (planned). |
| `npk_sensor_raw_hex` | TEXT | SN | Full raw Modbus response for debugging. |
| `tamper_detected` | BOOL | SN | Micro-switch / accelerometer flag (planned). |
| `enclosure_temp_c` | FLOAT | MN | BME280 doubles as enclosure temp on the Main Node. |
| `fault_flags` | TEXT | SN | Comma-separated firmware error tags. |
| `sensor_health_json` | JSONB | SYS + MN | Carries `calibration_version`, `seq`, `main_node_id`, `master_readings` (v2-raw path), `window_s`, `time_source`, plus clock-skew audit if the broker rewrote timestamps. |
| `firmware_version` | TEXT | FW | Sub Node's own string (`viraai-sn-1.0.0-raw`), fallback to Main Node's. |
| `uptime_seconds` | INT | SN | Sub Node's `millis()/1000` at TX. |
| `cadence_mode` | TEXT | SN | `normal`/`rapid`/`low_power`/`storm`/`maintenance` (planned; today always effectively `normal`). |
| `backlog_pending` | BOOL | MN | True if Main Node drained this row from SD outbox after an outage. |
| `validation_warn` | BOOL | SYS | Set by `_normalize_clock_skew` when timestamp was rewritten. |
| `valve_status`, `pump_running`, `pump_current_amps`, `pump_runtime_minutes_today`, `dry_run_detected` | mixed | SN | Pump/valve telemetry (present in schema, populated when the hardware supports it — pilot Sub Node has no valve, so these stay null). |
| `water_flow_lpm` | FLOAT | SN + CAL | `pulses × 60 / (window_s × pulses_per_L)`. Null when `window_s=0` (first cycle). |
| `water_volume_liters_session` | FLOAT | DERIVED | Delta of `flow_pulses_total` between adjacent rows / pulses_per_L. |
| `water_volume_liters_cumulative` | FLOAT | SN | Sub Node's own totalizer since boot. |
| `water_pressure_bar` | FLOAT | SN + CAL | 0011 migration; pressure transducer. |

### 3.13 `weather_station_readings` (Main Node — one row per weather cycle; Round 17 destination)

Populated by a separate producer today, but from Round 17 onwards will be written from the v2-raw path's `master_readings` block. Currently, the same data is duplicated into `Reading.sensor_health_json["master_readings"]`.

| Field | Type | Source | Notes |
|---|---|---|---|
| `weather_id` PK | BIGINT | SYS | |
| `tenant_id`, `master_node_id`, `farm_id` FK | mixed | SYS | Context. |
| `recorded_at` | TIMESTAMPTZ | MN | |
| `air_temp_c`, `air_temp_min_c`, `air_temp_max_c` | FLOAT | MN | BME280. Min/max over aggregation window. |
| `humidity_pct` | FLOAT | MN | BME280. |
| `dew_point_c` | FLOAT | DERIVED | Magnus formula from temp + humidity. |
| `atmospheric_pressure_hpa` | FLOAT | MN | BME280 (Pa/100). |
| `wind_speed_kmh`, `wind_speed_max_gust_kmh` | FLOAT | MN | Anemometer pulses ÷ window × calibration constant. |
| `wind_direction_degrees`, `wind_direction_cardinal` | mixed | MN + DERIVED | Wind vane ADC → degrees, mapped to N/NE/E… |
| `rain_mm_current_hour`, `rain_mm_today`, `rain_mm_last_7_days`, `rain_mm_this_season` | FLOAT | MN + DERIVED | Tipping-bucket pulses × mm/tick; rolling windows computed by aggregation. |
| `light_intensity_lux`, `uv_index` | FLOAT | MN | If lux/UV sensor present (not in pilot Main Node). |
| `leaf_wetness_pct`, `fog_detected`, `fog_intensity` | mixed | MN or DERIVED | Optional sensor + Ginger Engine inference. |
| `frost_risk`, `heat_stress_index`, `evapotranspiration_mm` | mixed | DERIVED | Formulas over temperature + humidity + wind. |
| `weather_station_battery_v` | FLOAT | MN | INA219 bus voltage. |
| `anemometer_fault`, `rain_gauge_fault` | BOOL | DERIVED | Long-run zero-count check. |

### 3.14 † `main_node_readings` (Round 17.5 — Main Node master-only heartbeat)

Row per v2-master heartbeat (every 5 min). Independent of Sub Node cadence — proves Main Node liveness even when Sub Node is silent.

| Field | Type | Source | Notes |
|---|---|---|---|
| `reading_id` PK | BIGINT | SYS | |
| `tenant_id`, `farm_id`, `main_node_id` FK | mixed | SYS | Context (no `plot_id` / `farmer_id`). |
| `recorded_at` | TIMESTAMPTZ | MN | Broker `_normalize_clock_skew` corrects impossible values. |
| `received_at_master` | TIMESTAMPTZ | MN | |
| `time_source` | TEXT | MN | `ntp`/`rtc`/`none` — provenance of the timestamp. |
| `sub_node_online` | BOOL | MN | Main Node's inference: `age(last LoRa RX) < 15 min`. |
| `sub_node_silence_ms` | BIGINT | MN | Milliseconds since last Sub Node RX. |
| `bme280_temp_c`, `bme280_humidity_pct`, `bme280_pressure_pa` | FLOAT | MN | Main Node BME280. |
| `ina219_bus_v`, `ina219_current_ma` | FLOAT | MN | Main Node power monitor. |
| `rain_pulses_window`, `wind_pulses_window`, `wind_dir_adc` | INT | MN | Raw counts over the 5-min window. |
| `firmware_version` | TEXT | FW | `viraai-mn-1.0.0-raw` etc. |
| `inserted_at` | TIMESTAMPTZ | SYS | Server clock; useful for ingest-latency diagnostics. |

### 3.15 `water_source_status` (planned — Phase 6)

Level/quality readings from a dedicated well/borewell/pond probe. Not yet deployed on the pilot.

| Field | Type | Source | Notes |
|---|---|---|---|
| `source_id` PK | BIGINT | SYS | |
| `tenant_id`, `farm_id` FK | UUID | SYS | |
| `source_type` | TEXT | FI | `well`/`borewell`/`farm_pond`/`canal`. |
| `recorded_at` | TIMESTAMPTZ | WSS | |
| `water_level_cm`, `water_level_pct`, `water_level_liters_estimate` | FLOAT | WSS + DERIVED | Ultrasonic distance → level → volume via source geometry. |
| `level_status` | TEXT | DERIVED | `full`/`adequate`/`low`/`critical`/`empty`. |
| `turbidity_ntu`, `water_temp_c`, `water_ph`, `water_ec_ms_cm` | FLOAT | WSS | Optional probe. |
| `pump_drawdown_cm`, `recovery_rate_cm_per_hour` | FLOAT | DERIVED | From level history + pump running windows. |
| `recharge_status` | TEXT | DERIVED | `recharging`/`stable`/`depleting`. |
| `alert_sent` | BOOL | SYS | |
| `sensor_id` | TEXT | SYS | |

### 3.16 `electricity_schedule_log` (learns the daily power-on window)

| Field | Type | Source | Notes |
|---|---|---|---|
| `elec_id` PK | BIGINT | SYS | |
| `tenant_id`, `farm_id` FK | mixed | SYS | |
| `recorded_at`, `electricity_on_at`, `electricity_off_at` | TIMESTAMPTZ | DERIVED | From `pump_current_amps > 0` transitions in `node_sensor_readings`. |
| `duration_minutes` | INT | DERIVED | |
| `detection_method` | TEXT | SYS | `current_sensor`/`pump_runtime`/`manual_input`. |
| `pump_used_during` | BOOL | DERIVED | |
| `pattern_confidence_pct` | FLOAT | DERIVED | Score from the pattern detector. |
| `detected_schedule_json` | JSONB | DERIVED | Learned daily on/off windows. |
| `schedule_changed_flag`, `last_schedule_change_at` | mixed | DERIVED | Change detection. |
| `ai_irrigation_adapted` | BOOL | DERIVED | True after `compose_advisory` used the learned schedule. |
| `notes` | TEXT | OPS | |

---

## Group D — External data

Backend polls; no user input.

### 3.17 `satellite_data` (1 row per satellite pass per plot)

| Field | Type | Source | Notes |
|---|---|---|---|
| `sat_id` PK | BIGINT | SYS | |
| `tenant_id`, `farm_id`, `plot_id` FK | mixed | SYS | Context. |
| `satellite_source` | TEXT | SAT | `sentinel2`/`sentinel1`/`landsat8`/`modis`/`smap`/`planet`. |
| `image_date` | DATE | SAT | Acquisition date. |
| `cloud_cover_pct`, `resolution_m` | FLOAT | SAT | Metadata. |
| `ndvi_value`, `ndvi_min`, `ndvi_max` | FLOAT | SAT + DERIVED | NDVI = (NIR-RED)/(NIR+RED) computed on the tile. |
| `ndvi_status` | TEXT | DERIVED | Bucketed `healthy`/`moderate`/`stressed`/`critical`. |
| `ndre_value`, `evi_value`, `savi_value`, `ndwi_value`, `ndmi_value` | FLOAT | DERIVED | Other vegetation indices. |
| `ndwi_status` | TEXT | DERIVED | Water-content bucket. |
| `soil_moisture_index`, `soil_moisture_source` | mixed | SAT | SMAP or Sentinel-1 backscatter. |
| `chlorophyll_index`, `lai_value`, `crop_health_score` | FLOAT | DERIVED | Model outputs. |
| `stressed_area_pct`, `stressed_zone_geojson` | mixed | DERIVED | Zonal statistics + polygon. |
| `pest_risk_index`, `disease_risk_index` | FLOAT | DERIVED | From spectral + weather. |
| `yield_prediction_qtl` | FLOAT | DERIVED | Regression on NDVI × phenological stage. |
| `raw_image_url` | TEXT | SAT | Object storage URL. |
| `processed_at` | TIMESTAMPTZ | SYS | |
| `gee_task_id` | TEXT | SAT | Google Earth Engine handle if applicable. |

### 3.18 `weather_forecasts` (external forecast API)

| Field | Type | Source | Notes |
|---|---|---|---|
| `forecast_id` PK | BIGINT | SYS | |
| `tenant_id`, `farm_id` FK | mixed | SYS | |
| `fetched_at`, `forecast_for_date`, `forecast_hour` | mixed | WAPI | Fetch time + horizon. |
| `source_api` | TEXT | WAPI | `open-meteo`/`imd` etc. |
| `temp_c`, `temp_min_c`, `temp_max_c` | FLOAT | WAPI | |
| `humidity_pct`, `rain_probability_pct`, `rain_mm_expected` | FLOAT | WAPI | |
| `wind_speed_kmh`, `wind_direction`, `fog_probability_pct`, `cloud_cover_pct` | mixed | WAPI | |
| `spray_suitability` | TEXT | DERIVED | `good`/`moderate`/`poor`/`not_recommended` — combined weather rule. |
| `irrigation_recommendation` | TEXT | DERIVED | `irrigate`/`skip_rain`/`reduce`/`normal`. |
| `frost_risk`, `heat_wave_risk` | BOOL | DERIVED | |

---

## Group E — Advisory pipeline (derived + LLM)

Where sensor data meets crop science and Claude.

### 3.19 `ai_suggestions` (1 row per advisory)

| Field | Type | Source | Notes |
|---|---|---|---|
| `suggestion_id` PK | UUID | SYS | |
| `tenant_id`, `farmer_id`, `farm_id`, `plot_id`, `season_id` FK | mixed | SYS | Context. |
| `generated_at` | TIMESTAMPTZ | SYS | |
| `suggestion_type` | TEXT | SYS | `daily`/`alert`/`weekly`/`monthly`/`end_of_season`. |
| `crop_age_days`, `crop_stage` | mixed | DERIVED | Snapshot at generation. |
| `soil_moisture_at_time`, `ndvi_at_time` | FLOAT | DERIVED | Snapshot. |
| `weather_summary_json`, `electricity_window_json` | JSONB | DERIVED | Digested inputs. |
| `water_source_status` | TEXT | DERIVED | |
| `water_action`, `water_liters_suggested`, `water_time_suggested`, `water_reason` | mixed | LLM | |
| `fertilizer_needed`, `fertilizer_product`, `fertilizer_qty_kg_per_acre`, `fertilizer_timing`, `fertilizer_reason` | mixed | LLM | |
| `micronutrient_deficiency`, `micronutrient_product`, `micronutrient_qty`, `micronutrient_reason` | mixed | LLM | |
| `pesticide_spray_today`, `pesticide_product`, `pesticide_dose`, `pesticide_reason` | mixed | LLM | |
| `tomorrow_plan`, `weekly_tip` | TEXT | LLM | |
| `full_message_marathi` | TEXT | LLM | The message that goes to the farmer. |
| `whatsapp_sent`, `whatsapp_sent_at` | BOOL / TIMESTAMPTZ | SYS | Set by dispatcher. |
| `ai_model_version`, `tokens_used`, `generation_time_ms` | mixed | SYS | Cost accounting. |
| `prompt_template_version` | TEXT | SYS | Which prompt file. |
| `llm_cost_inr` | NUMERIC | DERIVED | tokens × rate → INR. |
| `confidence_score`, `confidence_band` | mixed | DERIVED | LLM self-report + calibration. |
| `review_status` | TEXT | OPS | `none`/`pending`/`approved`/`rejected`/`edited`. |
| `reviewed_by`, `reviewed_at`, `review_notes` | mixed | OPS | Agronomist review. |

### 3.20 `irrigation_events` (1 row per pump-on window)

| Field | Type | Source | Notes |
|---|---|---|---|
| `irrigation_id` PK | BIGINT | SYS | |
| `tenant_id`, `farm_id`, `plot_id`, `farmer_id`, `season_id` FK | mixed | SYS | |
| `started_at`, `ended_at`, `duration_minutes` | mixed | DERIVED | From `pump_running` transitions in `node_sensor_readings`. |
| `water_liters`, `flow_rate_lpm_avg` | FLOAT | DERIVED | Integral of `water_flow_lpm` over the window. |
| `trigger_type` | TEXT | DERIVED or FO | `ai_auto`/`ai_suggested`/`manual`/`scheduled`/`emergency`. |
| `ai_suggestion_id` FK | UUID | SYS | If triggered by an advisory. |
| `soil_moisture_before`, `soil_moisture_after` | FLOAT | DERIVED | Sampled from `node_sensor_readings` at event boundaries. |
| `valve_id`, `pump_id` | TEXT | SYS | Physical identifiers. |
| `water_source_used` | TEXT | FO or DERIVED | Farmer or inferred from source-status delta. |
| `electricity_available` | BOOL | DERIVED | From `electricity_schedule_log`. |
| `weather_at_irrigation` | JSONB | DERIVED | Snapshot. |
| `crop_stage_at_time` | TEXT | DERIVED | |
| `ai_recommended_liters`, `variance_liters` | FLOAT | DERIVED | Compare AI vs actual. |
| `dry_run_event` | BOOL | DERIVED | If `dry_run_detected` was true during window. |
| `notes` | TEXT | FO | |

### 3.21 `farmer_actions` (1 row per farmer-reported activity)

| Field | Type | Source | Notes |
|---|---|---|---|
| `action_id` PK | BIGINT | SYS | |
| `tenant_id`, `farmer_id`, `farm_id`, `plot_id`, `season_id` FK | mixed | SYS | |
| `action_date`, `action_time` | mixed | FO | Farmer states when. |
| `action_type` | TEXT | FO | `watering`/`fertilizer`/`pesticide_spray`/`harvesting`/`weeding`/`ploughing`/`other`. |
| `ai_suggestion_id` FK | UUID | SYS | Which advisory this responds to. |
| `ai_suggested`, `farmer_followed_ai` | BOOL | DERIVED | Signal quality metric. |
| `water_liters` | FLOAT | FO | Farmer's estimate. |
| `fertilizer_name`, `fertilizer_qty_kg`, `fertilizer_cost_rs` | mixed | FO | |
| `pesticide_name`, `pesticide_qty_ml_or_g`, `pesticide_area_acre`, `pesticide_cost_rs` | mixed | FO | |
| `labour_cost_rs` | NUMERIC | FO | |
| `equipment_used` | TEXT | FO | Free-form. |
| `weather_at_action` | JSONB | DERIVED | Snapshot. |
| `farmer_note` | TEXT | FO | Free-form. |
| `source` | TEXT | SYS | `whatsapp_reply`/`app`/`manual_entry`/`auto_sensor`. |
| `recorded_at` | TIMESTAMPTZ | SYS | |

### 3.22 `ai_learning_log` (feedback for the AI — what worked, what didn't)

| Field | Type | Source | Notes |
|---|---|---|---|
| `learning_id` PK | BIGINT | SYS | |
| `tenant_id`, `farmer_id`, `season_id`, `suggestion_id`, `action_id` FK | mixed | SYS | |
| `learning_date` | DATE | SYS | |
| `suggestion_type` | TEXT | DERIVED | Copied from suggestion. |
| `ai_suggested_liters`, `farmer_gave_liters`, `water_variance_liters` | FLOAT | DERIVED | |
| `ndvi_before`, `ndvi_7days_after`, `ndvi_change` | FLOAT | DERIVED | Satellite response. |
| `moisture_before`, `moisture_3days_after` | FLOAT | DERIVED | Sensor response. |
| `crop_health_improved` | BOOL | DERIVED | |
| `suggestion_accuracy` | TEXT | DERIVED | `good`/`slight_over`/`slight_under`/`poor`. |
| `soil_type`, `crop_stage`, `weather_pattern` | mixed | DERIVED | Feature snapshot. |
| `water_coefficient_adjusted` | FLOAT | DERIVED | Learning update to the model. |
| `notes`, `learning_applied_at` | mixed | SYS | |

---

## Group F — Alerts & notifications

### 3.23 `alerts_notifications` (1 row per fired rule)

| Field | Type | Source | Notes |
|---|---|---|---|
| `alert_id` PK | BIGINT | SYS | |
| `tenant_id`, `farm_id`, `farmer_id`, `device_id` FK | mixed | SYS | Context. |
| `alert_type` | TEXT | DERIVED | `dry_run`/`low_water`/`power_off`/`pump_fault`/`sensor_fault`/`rain_heavy`/`frost`/`pest_risk`/`disease_risk`/`low_battery`/`device_offline`/`tamper`. |
| `severity` | TEXT | DERIVED | `info`/`warning`/`critical`. |
| `alert_message_marathi` | TEXT | DERIVED | Rendered from `PILOT_RULESET` templates. |
| `alert_value`, `alert_threshold` | FLOAT | DERIVED | What tripped, what the limit was. |
| `triggered_at` | TIMESTAMPTZ | SYS | |
| `whatsapp_sent`, `whatsapp_sent_at`, `sms_sent` | mixed | SYS | Dispatcher outputs. |
| `dispatch_status` | TEXT | SYS | `pending`/`sent`/`failed`/`dlq`. |
| `auto_action_taken` | TEXT | DERIVED | E.g. "closed valve on plot X" — actuation isn't in pilot. |
| `farmer_acknowledged`, `acknowledged_at` | mixed | FO | Farmer WhatsApp reply. |
| `resolved`, `resolved_at`, `resolution_note` | mixed | OPS or FO | |

### 3.24 `notification_dispatch_log` (delivery receipts per channel)

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` PK | BIGINT | SYS | |
| `alert_id` FK | BIGINT | SYS | |
| `channel` | TEXT | SYS | `whatsapp`/`sms`/`fcm`/`email`. |
| `provider_message_id` | TEXT | SYS | Meta/MSG91 handle. |
| `status` | TEXT | SYS | `queued`/`sent`/`delivered`/`failed`. |
| `error_code`, `error_message` | TEXT | SYS | |
| `dispatched_at` | TIMESTAMPTZ | SYS | |

### 3.25 `notification_dlq` (dead-letter queue)

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` PK | BIGINT | SYS | |
| `alert_id` FK | BIGINT | SYS | |
| `channels` | TEXT[] | SYS | Which channels failed. |
| `last_error`, `retry_count`, `moved_to_dlq_at` | mixed | SYS | |

---

## Group G — Business & billing

### 3.26 `subscriptions_billing` (1 row per farmer plan)

| Field | Type | Source | Notes |
|---|---|---|---|
| `subscription_id` PK | UUID | SYS | |
| `farmer_id` FK | UUID | SYS | |
| `plan_type` | TEXT | DEALER | `basic`/`standard`/`pro`/`custom`/`lease`. |
| `plan_start_date`, `plan_end_date` | DATE | DEALER | |
| `hardware_price_rs`, `monthly_fee_rs`, `emi_amount_rs`, `emi_months` | NUMERIC | DEALER | Pricing. |
| `payment_mode` | TEXT | DEALER | `full`/`emi`/`lease`/`subsidized`. |
| `govt_subsidy_scheme`, `subsidy_amount_rs` | mixed | DEALER | |
| `payment_gateway` | TEXT | SYS | Which PSP integration. |
| `last_payment_date`, `last_payment_amount_rs` | mixed | SYS | Recorded by webhook. |
| `next_payment_due` | DATE | DERIVED | |
| `total_paid_rs`, `outstanding_rs` | NUMERIC | DERIVED | |
| `payment_status` | TEXT | DERIVED | `paid`/`due`/`overdue`/`cancelled`. |
| `auto_renewal` | BOOL | FI | |
| `dealer_id`, `dealer_commission_pct` | mixed | OPS | |
| `churn_risk` | TEXT | DERIVED | `low`/`medium`/`high` — ML score. |

### 3.27 `product_performance_bi` (monthly rollup for reporting)

Populated by a nightly aggregation job.

| Field | Type | Source | Notes |
|---|---|---|---|
| `perf_id` PK | BIGINT | SYS | |
| `farmer_id`, `farm_id`, `season_id` FK | mixed | SYS | |
| `district`, `period_month` | mixed | DERIVED | Time bucket. |
| `water_saved_liters`, `water_saved_pct` | FLOAT | DERIVED | AI-recommended vs actual. |
| `fertilizer_saved_kg`, `fertilizer_saved_rs` | mixed | DERIVED | |
| `pesticide_sprays_ai_recommended`, `pesticide_sprays_done`, `spray_saved_count`, `spray_saved_rs` | mixed | DERIVED | |
| `ndvi_avg_this_season`, `ndvi_improvement_vs_last_season` | FLOAT | DERIVED | |
| `yield_actual_qtl`, `yield_last_season_qtl`, `yield_improvement_pct` | FLOAT | DERIVED | |
| `ai_suggestions_sent`, `ai_suggestions_followed`, `ai_follow_rate_pct` | mixed | DERIVED | |
| `device_uptime_pct`, `alerts_sent`, `alerts_critical` | mixed | DERIVED | |
| `farmer_satisfaction_score` | FLOAT | DERIVED | Rolling average of `service_maintenance.farmer_satisfaction`. |
| `roi_estimate_rs` | NUMERIC | DERIVED | |
| `product_effective` | BOOL | DERIVED | Threshold on ROI + NDVI improvement. |

---

## Group H — Auth & security (system)

### 3.28 `users` (staff, not tenant-scoped)

| Field | Type | Source | Notes |
|---|---|---|---|
| `user_id` PK | UUID | SYS | |
| `email` | TEXT | OPS | Unique lower-cased. |
| `password_hash` | TEXT | AUTH | Argon2id PHC string. |
| `full_name`, `phone` | TEXT | OPS | |
| `role` | TEXT | OPS | `admin`/`agronomist`/`service`/`technician`. |
| `is_active` | BOOL | OPS | |
| `created_at`, `last_login_at` | mixed | SYS | |

### 3.29 `otp_codes` (phone OTP store)

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` PK | UUID | SYS | |
| `tenant_id` FK | UUID | SYS | |
| `phone_e164` | TEXT | FO | |
| `code_hash` | TEXT | AUTH | Hashed OTP. |
| `transport` | TEXT | SYS | `whatsapp`/`sms`. |
| `wa_message_id` | TEXT | SYS | Meta provider ID. |
| `attempts`, `expires_at`, `verified_at`, `created_at` | mixed | SYS | |

### 3.30 `refresh_tokens`

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` PK | UUID | SYS | |
| `token_hash` | BYTEA | AUTH | Hashed. |
| `user_or_farmer_id`, `role`, `tenant_id` | mixed | SYS | Subject binding. |
| `expires_at`, `revoked_at`, `created_at` | mixed | SYS | |

### 3.31 `auth_sessions` (0009)

Session state per JWT — not shown here in full; standard shape (session_id, refresh_id, issued_at, last_seen_at, ip, user_agent).

---

## Group I — Ops plumbing (system)

### 3.32 `audit_log`

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` PK | BIGINT | SYS | |
| `actor_type`, `actor_id` | TEXT | SYS | Who did the mutation. |
| `table_name`, `row_pk`, `operation` | mixed | AUDIT | Where + what. |
| `old_data`, `new_data` | JSONB | AUDIT | Before/after snapshots. |
| `at` | TIMESTAMPTZ | SYS | |

### 3.33 `ingest_unmatched` (quarantine for unknown tenant/farm/device)

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` PK | BIGINT | SYS | |
| `tenant_id`, `topic`, `payload`, `reason` | mixed | SYS | Rejected message body. |
| `first_seen`, `last_seen`, `count` | mixed | SYS | Coalesced. |

### 3.34 `event_outbox` (transactional outbox — planned Round 13)

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` PK | BIGINT | SYS | |
| `tenant_id`, `event_name`, `payload` | mixed | SYS | |
| `published`, `published_at`, `created_at` | mixed | SYS | Subscriber advances the `published` flag. |

### 3.35 `feature_flags`

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` PK | UUID | SYS | |
| `tenant_id`, `flag_name`, `enabled`, `payload` | mixed | OPS | |

### 3.36 `system_config` (hot-reloadable key/value)

| Field | Type | Source | Notes |
|---|---|---|---|
| `key` PK | TEXT | OPS | |
| `value` | JSONB | OPS | |
| `updated_at` | TIMESTAMPTZ | SYS | |

### 3.37 `chat_messages` (Tier-3 farmer chat, 90-day rolling)

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` PK | UUID | SYS | |
| `farmer_id` FK | UUID | SYS | |
| `role` | TEXT | SYS | `user`/`assistant`/`system`. |
| `content` | TEXT | FO or LLM | |
| `tokens_used`, `llm_cost_inr` | mixed | DERIVED | |
| `context` | JSONB | SYS | Included Farm Brain fields. |
| `created_at` | TIMESTAMPTZ | SYS | |

### 3.38 `wa_inbound_log` (WhatsApp inbound raw)

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` PK | UUID | SYS | |
| `farmer_id` FK | UUID | SYS | Resolved from phone. |
| `wa_message_id`, `phone_e164`, `body` | mixed | FO | |
| `received_at` | TIMESTAMPTZ | SYS | |
| `processed` | BOOL | SYS | Set by the classifier. |

---

## Group J — Ginger Engine KB (19 tables + 16 views, teammate-owned)

Created by migration 0010 from a 1.16 MB SQL blob (`ginger/generated/agroguardian_ginger_kb.sql`). 17 tables are the *knowledge base* proper (all prefixed `kb_*`, all sourced from the agronomy team), 2 are *runtime state* the engine writes as it runs (`engine_state`, `advisory_log`). Plus 16 read-only diagnostic views (`v_*`) computed from the tables.

**Do not modify the `kb_*` tables by hand.** They're regenerated wholesale from the upstream authoring artefacts on every KB release. If you need to change a rule, patch the source doc, re-emit the SQL blob, ship a new migration. The `kb_overrides` table (below) is the sanctioned way to override individual rules at runtime without touching the KB itself.

### J.1 Reference / catalogue tables

Small, static lookups.

#### `kb_source_tiers` (evidence-quality tiers used by rules)

| Field | Type | Source | Notes |
|---|---|---|---|
| `tier` PK | CHAR(1) | AGRO | e.g. `A` = peer-reviewed, `B` = agronomist consensus, `C` = anecdotal. |
| `description` | TEXT | AGRO | Human-readable meaning. |

#### `kb_source_classes` (broader categorisation of evidence sources)

| Field | Type | Source | Notes |
|---|---|---|---|
| `source_class` PK | TEXT | AGRO | e.g. `peer_reviewed`, `field_trial`, `extension_service`. |
| `description` | TEXT | AGRO | |
| `production_allowed` | BOOL | AGRO | If `false`, rules from this class are draft-only — the engine won't act on them. |

#### `kb_stages` (crop phenological stages)

| Field | Type | Source | Notes |
|---|---|---|---|
| `stage_code` PK | TEXT | AGRO | e.g. `sowing`, `sprouting`, `vegetative`, `rhizome_bulking`, `maturity`. |
| `name_en`, `name_mr` | TEXT | AGRO | Bilingual labels. |
| `dap_start`, `dap_end` | INT | AGRO | "Days after planting" bounds for ginger. |
| `criticality` | TEXT | AGRO | `low`/`medium`/`medium_high`/`high`/`highest`. |
| `critical_irrigation` | BOOL | AGRO | Missing water in this stage is unrecoverable. |
| `recoverable` | TEXT | AGRO | `none`/`partial`/`full` — how much a mistake in this stage costs. |

#### `kb_domains` (functional domains — 1 per rule bundle)

| Field | Type | Source | Notes |
|---|---|---|---|
| `domain_id` PK | INT | AGRO | 1-based; used as prefix in `rule_id` (`D01-…`). |
| `name_en`, `name_mr` | TEXT | AGRO | e.g. "Irrigation", "Nutrition", "Pest & Disease". |
| `crop` | TEXT | AGRO | Currently always `ginger`. |
| `source_document` | TEXT | AGRO | Which upstream doc this domain was authored from. |
| `version` | TEXT | AGRO | KB release version. |
| `status` | TEXT | AGRO | `PHASE_1_RAW_UNVALIDATED`/`AGRONOMIST_REVIEWED`/`FIELD_VALIDATED`/`PRODUCTION`. |
| `agronomist_validated` | BOOL | AGRO | Sign-off flag. |
| `total_rules` | INT | AGRO | Count for reconciliation. |
| `review_by` | DATE | AGRO | Deadline for next agronomist review. |
| `purpose`, `central_finding`, `author_note` | TEXT | AGRO | Editorial metadata. |
| `created_at` | TIMESTAMPTZ | SYS | KB import timestamp. |

#### `kb_rule_categories` (subdivisions of a domain)

| Field | Type | Source | Notes |
|---|---|---|---|
| `domain_id` FK + `category` — composite PK | INT + TEXT | AGRO | e.g. domain=Irrigation, category=`under-watering`. |
| `description` | TEXT | AGRO | |

#### `kb_farm_brain_fields` (declared inputs a rule may reference)

Contract table — every field the engine will read on any given plot **must** appear here. Prevents typos and silent bugs.

| Field | Type | Source | Notes |
|---|---|---|---|
| `field_name` PK | TEXT | AGRO | e.g. `soil_moisture_avg_pct`, `days_since_last_irrigation`. |
| `spec` | TEXT | AGRO | Type + unit + expected range. |
| `declared_in_domain` FK | INT | AGRO | Which domain introduced this field. |

### J.2 Rules and their metadata (the 431 rules live here)

#### `kb_rules` (the heart of the KB — 1 row per rule)

| Field | Type | Source | Notes |
|---|---|---|---|
| `rule_id` PK | TEXT | AGRO | Format `D<domain2>-<seq>`, e.g. `D01-042`. Enforced by CHECK. |
| `domain_id`, `category` FK | INT + TEXT | AGRO | Composite FK into `kb_rule_categories`. |
| `priority` | INT (1–5) | AGRO | 1 = highest. |
| `severity` | TEXT | AGRO | `info`/`yellow`/`red`/`blocking`. Blocking rules stop the engine's daily run for that plot. |
| `stage_code` FK | TEXT | AGRO | Which crop stage this rule fires in (nullable = all stages). |
| `trigger_en`, `trigger_mr` | TEXT | AGRO | Human-readable trigger, bilingual. |
| `trigger_expr` | TEXT | AGRO | Formal expression evaluated by the engine (mini-DSL). |
| `trigger_expr_version` | TEXT | AGRO | DSL version for backwards compat. |
| `delivery` | TEXT | AGRO | `ONCE_UNTIL_RESOLVED` / `EVENT` / `WINDOW` / `SILENT_GUARD`. |
| `immutable` | BOOL | AGRO | If TRUE, `kb_overrides` cannot modify this rule. |
| `immutable_reason` | TEXT | AGRO | Free-form. |
| `action_en`, `action_mr` | TEXT | AGRO | Recommended action; the `_mr` variant lands in `ai_suggestions.full_message_marathi`. |
| `agronomic_basis` | TEXT | AGRO | 40+ char justification (CHECK-enforced). |
| `yield_impact` | TEXT | AGRO | Expected yield delta if this action is/isn't taken. |
| `confidence_score` | NUMERIC(3,2) | AGRO | 0–1 self-scored confidence. |
| `source_tier` FK | CHAR(1) | AGRO | Points to `kb_source_tiers`. |
| `source_class` FK | TEXT | AGRO | Points to `kb_source_classes`. |
| `u_value` | NUMERIC(4,3) | AGRO | Utility weight used by de-duplication (see J.3). |
| `recoverability` | TEXT | AGRO | `none`/`partial`/`full` — inherits stage semantics. |
| `kannad_note` | TEXT | AGRO | 20+ char field-team note in Kannada or another local dialect (CHECK-enforced). |
| `created_at` | TIMESTAMPTZ | SYS | |

#### `kb_golden_tests` (per-rule test cases)

Ensures no rule ships without a passing test.

| Field | Type | Source | Notes |
|---|---|---|---|
| `rule_id` FK + `seq` PK | TEXT + INT | AGRO | |
| `context` | JSONB | AGRO | Farm Brain fixture. |
| `expect` | TEXT | AGRO | `TRUE`/`FALSE`/`UNKNOWN` — expected trigger outcome. |
| `label` | TEXT | AGRO | Human-readable case name. |

#### `kb_rule_fields` (which Farm Brain fields a rule reads)

Populated at KB import by parsing `trigger_expr`. Enables impact analysis when a field is renamed.

| Field | Type | Source | Notes |
|---|---|---|---|
| `rule_id` FK + `field_name` FK — composite PK | TEXT + TEXT | AGRO | |

#### `kb_rule_references` (citations for the rule's agronomic basis)

| Field | Type | Source | Notes |
|---|---|---|---|
| `rule_id` FK + `reference` PK | TEXT | AGRO | Free-form citation (paper, report, extension bulletin, etc.). |

#### `kb_rule_dependencies` (inter-domain wiring)

| Field | Type | Source | Notes |
|---|---|---|---|
| `rule_id` FK + `direction` + `target_domain_id` FK — composite PK | mixed | AGRO | |
| `direction` | TEXT | AGRO | `feeds_into` (this rule produces state consumed elsewhere) or `depends_on` (this rule reads state produced elsewhere). |

### J.3 Deduplication + precedence

Prevents the engine from bombarding a farmer with 12 near-identical Marathi messages when 12 related rules all fire on the same day.

#### `kb_duplication_groups`

| Field | Type | Source | Notes |
|---|---|---|---|
| `group_name` PK | TEXT | AGRO | e.g. `low_moisture_family`. |
| `u_value` | NUMERIC(4,3) | AGRO | Group-level utility weight. |
| `count_once` | BOOL | AGRO | If TRUE, the group counts as one action toward the daily budget. |
| `note` | TEXT | AGRO | |

#### `kb_duplication_members`

| Field | Type | Source | Notes |
|---|---|---|---|
| `group_name` FK + `rule_id` FK — composite PK | TEXT | AGRO | Membership. |

#### `kb_precedence` (directed relationships between rules)

Says "if A fires, don't fire B" or "A escalates B into a stronger alert".

| Field | Type | Source | Notes |
|---|---|---|---|
| `subject_rule` FK + `relation` + `object_rule` FK — composite PK | mixed | AGRO | |
| `relation` | TEXT | AGRO | `SUPPRESSES`/`SUPERSEDES`/`ESCALATES`/`BUNDLES`/`SEQUENCES`. |
| `reason_en`, `reason_mr` | TEXT | AGRO | Bilingual justification. |
| CHECK constraint | — | AGRO | `subject_rule <> object_rule` (no self-references). |

### J.4 Runtime overrides

The one part of the KB that's meant to change without a KB release. Field agronomists can adjust thresholds or disable a rule for a specific plot without touching the source blob.

#### `kb_overrides`

| Field | Type | Source | Notes |
|---|---|---|---|
| `override_id` PK | TEXT | OPS | Deterministic slug written by the agronomist. |
| `rule_id` FK | TEXT | OPS | Which rule to override (must not be `immutable=true`). |
| `kind` | TEXT | OPS | `THRESHOLD`/`DELIVERY`/`SEVERITY`/`DISABLE`/`PARAMETER`. |
| `scope` | TEXT | OPS | `plot`/`cluster`/`global`. |
| `scope_id` | TEXT | OPS | Required unless `scope = 'global'` (CHECK-enforced). |
| `expert_id`, `expert_name` | TEXT | OPS | Which agronomist entered this. |
| `rationale_mr` | TEXT | OPS | 15+ char Marathi rationale (CHECK-enforced) — appears in `advisory_log` audit trail. |
| `created`, `expires` | DATE | OPS | `expires > created` and `expires <= created + 400 days` (CHECK-enforced). |
| `payload` | JSONB | OPS | Kind-specific data (new threshold value, new severity, etc.). |
| `revoked`, `revoked_by` | mixed | OPS | Set on manual revocation. |
| `applied_count` | INT | DERIVED | Bumped by the engine each time the override was actually applied. |

#### `kb_override_audit` (append-only trail of override lifecycle)

| Field | Type | Source | Notes |
|---|---|---|---|
| `audit_id` PK | BIGSERIAL | SYS | |
| `action` | TEXT | AUDIT | `CREATED`/`REVOKED`/`REFUSED`/`APPLIED`. |
| `rule_id` | TEXT | SYS | (Not a FK — audit outlives rules.) |
| `override_id` | TEXT | SYS | |
| `expert_id` | TEXT | SYS | |
| `detail` | TEXT | SYS | Free-form. |
| `at` | TIMESTAMPTZ | SYS | |

### J.5 Runtime state (the engine writes these; not KB)

#### `engine_state` (1 row per plot — persistent memory across daily runs)

| Field | Type | Source | Notes |
|---|---|---|---|
| `plot_id` PK | TEXT | SYS | |
| `version` | INT | DERIVED | Bumped on each write. |
| `last_run` | DATE | DERIVED | Last day the engine successfully processed this plot. |
| `saved_at` | TIMESTAMPTZ | SYS | |
| `payload` | JSONB | DERIVED | Fires-since-resolved counters, cool-down markers, memoised interim values. |

#### `advisory_log` (1 row per (plot, day, rule) advisory issued)

| Field | Type | Source | Notes |
|---|---|---|---|
| `plot_id` + `day` + `rule_id` — composite PK | mixed | DERIVED | Idempotent — one entry per day per rule per plot. |
| `severity` | TEXT | DERIVED | Copied from the rule (post-override). |
| `message` | TEXT | DERIVED | Rendered Marathi text (from `kb_rules.action_mr`, template-expanded). |
| `delivered_at` | TIMESTAMPTZ | SYS | |
| `acted_on` | BOOL | FO | Farmer WhatsApp reply flips this. |
| `acted_at` | DATE | FO | |

### J.6 Open items (KB planning tracker)

Where the agronomy team parks "we should build a rule for X but the data isn't good enough yet".

#### `kb_open_items`

| Field | Type | Source | Notes |
|---|---|---|---|
| `open_item_id` PK | TEXT | AGRO | |
| `domain_id` FK | INT | AGRO | |
| `item` | TEXT | AGRO | Description. |
| `owner` | TEXT | AGRO | Person accountable. |
| `source_class` FK | TEXT | AGRO | Kind of evidence needed. |
| `blocking` | BOOL | AGRO | If TRUE, some downstream domain can't ship until this is resolved. |
| `time_sensitive` | BOOL | AGRO | Missing this by a season loses a year of data. |
| `note` | TEXT | AGRO | |
| `resolved_at` | TIMESTAMPTZ | SYS | Nullable — set on close. |

### J.7 Diagnostic views (16, read-only)

The KB migration ships 16 views over the tables above. They are read-only and their content is entirely a projection of the tables — no independent source label needed. Purpose in one line each:

| View | Purpose |
|---|---|
| `v_u_values_deduplicated` | Rule utility scores after applying `kb_duplication_groups`. |
| `v_unintended_duplicate_actions` | Pairs of rules that would produce nearly identical Marathi text — flags authoring drift. |
| `v_rules_by_stage` | Roll-up: rule count per crop stage. |
| `v_executable_rules` | Rules whose `source_class.production_allowed` is TRUE **and** which have passing golden tests. |
| `v_pending_triggers` | Rules that fired today per plot but aren't yet acted on (from `advisory_log`). |
| `v_rule_precedence` | Materialised transitive closure of `kb_precedence`. |
| `v_unguarded_instructions` | Rules whose action tells the farmer to apply something (fertilizer, pesticide) with no guard on rainfall or spray window — audit target. |
| `v_active_overrides` | `kb_overrides` filtered to `now() BETWEEN created AND expires AND revoked IS NULL`. |
| `v_override_review` | Overrides expiring within 30 days — agronomist review queue. |
| `v_immutable_rules` | The subset of rules the engine will refuse to override. |
| `v_compliance` | Rules missing required metadata (empty `agronomic_basis`, no golden test, etc.). |
| `v_stale_plots` | Plots whose `engine_state.last_run` is > 2 days old. |
| `v_rule_effectiveness` | Per rule: fired-count / acted-on-count over 30 days. |
| `v_blocking` | Rules with severity `blocking` — should be a very short list. |
| `v_high_value_free` | Rules with `u_value > 0.7` and low `applied_count` — under-fired rules that agronomists should investigate. |
| `v_expiring` | Overrides + open items expiring in the next 14 days. |

### J.8 How the pilot Ginger Engine reads this KB

1. **Daily 06:30 IST**, `ginger_daily.py` iterates every active plot.
2. For each plot it builds a "Farm Brain" dict — 305 fields, currently ~85 populated from the tables in Groups A–E above. Only fields declared in `kb_farm_brain_fields` are readable by rules.
3. It walks `kb_rules` in priority order, filtered by `stage_code` matching the plot's current growth stage.
4. Each rule's `trigger_expr` is evaluated against the Farm Brain. Passing triggers become candidate advisories.
5. `kb_precedence` prunes candidates (SUPPRESSES / SUPERSEDES). `kb_duplication_groups` collapses near-duplicates.
6. `kb_overrides` (via `v_active_overrides`) may adjust thresholds or disable specific rules for this plot.
7. Surviving advisories are appended to `advisory_log` and turned into `ai_suggestions` rows for delivery.
8. `engine_state.payload` is updated so tomorrow's run knows which advisories fired without repeating them (`ONCE_UNTIL_RESOLVED` semantics).

The 431 rules currently live in domains 1 through N (see `SELECT domain_id, name_en, total_rules FROM kb_domains ORDER BY domain_id`).

**Do not modify by hand.** The `ginger/` Python package is upstream-owned; the tables are its persistent memory. `kb_overrides` is the sanctioned adjustment surface.

---

## Part 4 — Data lifecycle rules

1. **Sensor data is append-only.** `node_sensor_readings`, `weather_station_readings`, `main_node_readings`, `water_source_status` — never UPDATE, never DELETE except by retention policy. Idempotency guaranteed by unique index on `(device_id, recorded_at)`.

2. **Farmer identity is farmer-owned but staff-editable.** Fields on `farmers` / `farms` are updated by the farmer (via WhatsApp / app) or by ops staff correcting mistakes. Every change is captured by the audit trigger.

3. **Advisories are LLM-owned but reviewable.** `ai_suggestions` are written by the compose loop and can be gated by an agronomist via `review_status`. The `ai_suggestions_review_guard` trigger prevents any column change other than the review fields, protecting the LLM's original output as an evidentiary record.

4. **Derived fields recompute deterministically.** Anything sourced `DERIVED` should be reproducible from its inputs. If a bug is found, the fix should be a batch job, not a manual UPDATE. `calibration_version` on every reading makes retroactive recalibration possible.

5. **Farmer edits never overwrite sensor readings.** If a farmer says "no, the moisture was 60% not 45%", that becomes a `farmer_actions.farmer_note` — the sensor row stays untouched.

6. **Every telemetry-writing path passes through `_normalize_clock_skew`.** Bad device clocks are corrected + flagged, never dropped, never trusted.

---

## Part 5 — Retention & privacy

- **Sensor + telemetry tables** (`*_readings`, `*_status`) — retained indefinitely for the pilot; production plan is 3 years online then object-storage archive.
- **`chat_messages`** — 90-day rolling per system_config; older rows are purged nightly.
- **`otp_codes`, `refresh_tokens`** — expiry-based; purged 30 days after `expires_at`.
- **`wa_inbound_log`, `ingest_unmatched`** — 90 days.
- **`audit_log`** — 7 years (compliance).
- **`farmers.phone_primary` etc.** — encrypted-at-rest column (`phone_encrypted`) planned; lookup via `phone_hash`. Aadhaar and government IDs are never returned by any API — they are internal-only.

---

*End of document. When the schema changes, update this doc in the same PR as the migration. When the two disagree, the migration wins.*
