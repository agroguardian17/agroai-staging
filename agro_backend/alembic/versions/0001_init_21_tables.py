"""0001 init: tenants + 21 source tables (from Database Schema PDF).

Faithful to ``Agro_Guardian_AI_Database_Schema 1.pdf`` (21 tables / 400+ cols),
with the roadmap v3 overlay applied per ``docs/SCHEMA_DECISIONS.md``:

* ``tenants`` created first; every business table carries
  ``tenant_id UUID NOT NULL REFERENCES tenants(id)``.
* PDF ``ENUM`` columns are ``TEXT`` + ``CHECK`` (no native enum types).
* PKs: UUID for entity tables, TEXT for ``plot_id`` / ``device_id`` / ``node_id``,
  BIGINT IDENTITY for high-volume reading/log tables (PDF ``BIGSERIAL``).
* UUID defaults use ``gen_random_uuid()`` (Postgres 13+ core; no extension dep).
* PDF identifiers that begin with a digit (``4g_signal_*``) are renamed to
  ``signal_4g_*`` (illegal SQL identifiers otherwise).
* Time-series tables are created as plain tables here and converted to
  range-partitioned tables in 0005.
* Circular FKs (plots<->device_registry, plots<->crop_seasons) are added as
  trailing ALTERs once both sides exist.

Hand-written raw SQL (op.execute), not ``op.create_table`` -- per roadmap 1.1.

Revision ID: 0001
Revises:
Create Date: Phase 1
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
-- ---------------------------------------------------------------------------
-- tenants (v3 multi-tenancy root). tier/features added in 0002.
-- ---------------------------------------------------------------------------
CREATE TABLE tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    slug        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- TABLE 1: farmers
-- ---------------------------------------------------------------------------
CREATE TABLE farmers (
    farmer_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    full_name           TEXT NOT NULL,
    marathi_name        TEXT NOT NULL,
    phone_primary       TEXT NOT NULL,
    phone_secondary     TEXT,
    whatsapp_number     TEXT NOT NULL,
    language_preference TEXT NOT NULL CHECK (language_preference IN ('marathi','hindi','english')),
    village             TEXT NOT NULL,
    taluka              TEXT NOT NULL,
    district            TEXT NOT NULL,
    state               TEXT NOT NULL,
    pin_code            TEXT,
    aadhar_number       TEXT,
    farmer_id_govt      TEXT,
    education_level     TEXT CHECK (education_level IN ('primary','secondary','graduate','illiterate')),
    age_years           INT,
    gender              TEXT CHECK (gender IN ('male','female','other')),
    account_created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    account_status      TEXT NOT NULL DEFAULT 'active' CHECK (account_status IN ('active','inactive','suspended')),
    subscription_tier   TEXT NOT NULL CHECK (subscription_tier IN ('basic','standard','pro','custom')),
    subscription_start  DATE NOT NULL,
    subscription_end    DATE NOT NULL,
    payment_status      TEXT NOT NULL CHECK (payment_status IN ('paid','due','overdue')),
    referred_by         TEXT,
    dealer_id           TEXT,
    notes               TEXT
);
CREATE INDEX farmers_tenant_idx ON farmers (tenant_id);

-- ---------------------------------------------------------------------------
-- TABLE 2: farms
-- ---------------------------------------------------------------------------
CREATE TABLE farms (
    farm_id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                UUID NOT NULL REFERENCES tenants(id),
    farmer_id                UUID NOT NULL REFERENCES farmers(farmer_id),
    farm_name                TEXT,
    survey_number            TEXT,
    total_area_acre          NUMERIC(10,2) NOT NULL,
    gps_lat_center           DOUBLE PRECISION NOT NULL,
    gps_lng_center           DOUBLE PRECISION NOT NULL,
    gps_boundary_geojson     JSONB,
    soil_type                TEXT NOT NULL CHECK (soil_type IN ('black','red','sandy','loamy','mixed')),
    soil_texture             TEXT,
    soil_depth_cm            INT,
    soil_organic_carbon_pct  DOUBLE PRECISION,
    water_holding_capacity   TEXT CHECK (water_holding_capacity IN ('low','medium','high')),
    terrain_type             TEXT CHECK (terrain_type IN ('flat','mild_slope','steep')),
    elevation_m              DOUBLE PRECISION,
    water_source_primary     TEXT NOT NULL CHECK (water_source_primary IN ('well','borewell','farm_pond','canal','tanker','rain')),
    water_source_secondary   TEXT CHECK (water_source_secondary IN ('well','borewell','farm_pond','none')),
    well_depth_ft            INT,
    borewell_depth_ft        INT,
    borewell_yield_lpm       DOUBLE PRECISION,
    farm_pond_capacity_liters DOUBLE PRECISION,
    irrigation_type          TEXT NOT NULL CHECK (irrigation_type IN ('drip','sprinkler','flood','furrow','mixed')),
    drip_emitter_lph         DOUBLE PRECISION,
    irrigation_area_acre     NUMERIC(10,2),
    electricity_source       TEXT NOT NULL CHECK (electricity_source IN ('grid','solar_pump','generator','mixed')),
    solar_pump_hp            DOUBLE PRECISION,
    generator_fuel           TEXT CHECK (generator_fuel IN ('diesel','petrol','none')),
    electricity_feeder_name  TEXT,
    electricity_schedule_known BOOLEAN,
    electricity_schedule_json  JSONB,
    road_access              BOOLEAN,
    mobile_network_quality   TEXT CHECK (mobile_network_quality IN ('4G','3G','2G','poor')),
    nearest_town_km          DOUBLE PRECISION,
    previous_crops_json      JSONB,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX farms_tenant_idx ON farms (tenant_id);
CREATE INDEX farms_farmer_idx ON farms (farmer_id);

-- ---------------------------------------------------------------------------
-- TABLE 3: plots  (node_id & crop_current_season_id FKs added at end)
-- ---------------------------------------------------------------------------
CREATE TABLE plots (
    plot_id                 TEXT PRIMARY KEY,
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    farm_id                 UUID NOT NULL REFERENCES farms(farm_id),
    plot_number             INT NOT NULL,
    plot_name               TEXT,
    area_acre               NUMERIC(10,2) NOT NULL,
    gps_lat                 DOUBLE PRECISION NOT NULL,
    gps_lng                 DOUBLE PRECISION NOT NULL,
    gps_boundary_geojson    JSONB,
    node_id                 TEXT NOT NULL,
    soil_type_override      TEXT CHECK (soil_type_override IN ('black','red')),
    crop_current_season_id  UUID,
    irrigation_valve_id     TEXT NOT NULL,
    drip_line_count         INT,
    plot_status             TEXT NOT NULL DEFAULT 'active' CHECK (plot_status IN ('active','fallow','harvested')),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX plots_tenant_idx ON plots (tenant_id);
CREATE INDEX plots_farm_idx ON plots (farm_id);

-- ---------------------------------------------------------------------------
-- TABLE 4: crop_seasons
-- ---------------------------------------------------------------------------
CREATE TABLE crop_seasons (
    season_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    farm_id                 UUID NOT NULL REFERENCES farms(farm_id),
    plot_id                 TEXT NOT NULL REFERENCES plots(plot_id),
    season_name             TEXT NOT NULL,
    season_type             TEXT NOT NULL CHECK (season_type IN ('kharif','rabi','summer','perennial')),
    year                    INT NOT NULL,
    crop_name_marathi       TEXT NOT NULL,
    crop_name_english       TEXT NOT NULL,
    crop_variety            TEXT NOT NULL,
    crop_category           TEXT NOT NULL CHECK (crop_category IN ('cereal','pulse','oilseed','vegetable','fruit','cash_crop','fodder')),
    sowing_date             DATE NOT NULL,
    transplanting_date      DATE,
    expected_harvest_date   DATE NOT NULL,
    actual_harvest_date     DATE,
    seed_rate_kg_per_acre   DOUBLE PRECISION,
    seed_cost_per_kg        NUMERIC(10,2),
    base_fertilizer_at_sowing TEXT,
    crop_age_days_today     INT,
    current_growth_stage    TEXT,
    days_to_harvest         INT,
    target_yield_qtl_per_acre DOUBLE PRECISION,
    actual_yield_qtl_per_acre DOUBLE PRECISION,
    total_water_used_liters DOUBLE PRECISION,
    total_fertilizer_cost_rs NUMERIC(12,2),
    total_pesticide_cost_rs  NUMERIC(12,2),
    season_status           TEXT NOT NULL DEFAULT 'active' CHECK (season_status IN ('active','completed','abandoned')),
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX crop_seasons_tenant_idx ON crop_seasons (tenant_id);
CREATE INDEX crop_seasons_plot_idx ON crop_seasons (plot_id);

-- ---------------------------------------------------------------------------
-- TABLE 15: device_registry  (created before reading tables for FK targets)
-- broker_secret_hash / calibration_json added in 0002.
-- ---------------------------------------------------------------------------
CREATE TABLE device_registry (
    device_id                  TEXT PRIMARY KEY,
    tenant_id                  UUID NOT NULL REFERENCES tenants(id),
    device_type                TEXT NOT NULL CHECK (device_type IN ('master_node','sub_node','weather_station')),
    serial_number              TEXT NOT NULL,
    mac_address                TEXT NOT NULL,
    qr_code_data               TEXT NOT NULL,
    farm_id                    UUID NOT NULL REFERENCES farms(farm_id),
    plot_id                    TEXT REFERENCES plots(plot_id),
    device_tier                TEXT NOT NULL CHECK (device_tier IN ('basic','standard','pro')),
    manufacture_date           DATE,
    batch_number               TEXT,
    pcb_version                TEXT,
    firmware_version_installed TEXT,
    firmware_version_latest    TEXT,
    ota_pending                BOOLEAN,
    last_ota_update            TIMESTAMPTZ,
    last_ota_result            TEXT CHECK (last_ota_result IN ('success','failed','rolled_back')),
    installation_date          DATE,
    installation_technician_id TEXT,
    gps_installed_lat          DOUBLE PRECISION,
    gps_installed_lng          DOUBLE PRECISION,
    pole_height_ft             DOUBLE PRECISION,
    enclosure_type             TEXT,
    sim_number                 TEXT,
    sim_provider               TEXT CHECK (sim_provider IN ('jio','airtel','bsnl')),
    signal_4g_strength         TEXT CHECK (signal_4g_strength IN ('excellent','good','fair','poor')),
    last_heartbeat_at          TIMESTAMPTZ,
    heartbeat_interval_min     INT,
    device_status              TEXT NOT NULL DEFAULT 'offline' CHECK (device_status IN ('online','offline','fault','maintenance')),
    warranty_expiry            DATE,
    total_uptime_hours         DOUBLE PRECISION,
    total_downtime_hours       DOUBLE PRECISION,
    fault_count                INT,
    replacement_flag           BOOLEAN,
    notes                      TEXT
);
CREATE INDEX device_registry_tenant_idx ON device_registry (tenant_id);
CREATE INDEX device_registry_farm_idx ON device_registry (farm_id);

-- ---------------------------------------------------------------------------
-- TABLE 5: node_sensor_readings  (plain here; partitioned in 0005)
-- ---------------------------------------------------------------------------
CREATE TABLE node_sensor_readings (
    reading_id                     BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tenant_id                      UUID NOT NULL REFERENCES tenants(id),
    node_id                        TEXT NOT NULL REFERENCES device_registry(device_id),
    farm_id                        UUID NOT NULL REFERENCES farms(farm_id),
    plot_id                        TEXT NOT NULL REFERENCES plots(plot_id),
    farmer_id                      UUID NOT NULL REFERENCES farmers(farmer_id),
    recorded_at                    TIMESTAMPTZ NOT NULL,
    received_at_master             TIMESTAMPTZ NOT NULL,
    transmission_type              TEXT NOT NULL CHECK (transmission_type IN ('esp_now','lora','rs485','wifi')),
    signal_rssi_dbm                INT,
    battery_voltage_v              DOUBLE PRECISION,
    battery_percent                DOUBLE PRECISION,
    solar_charging                 BOOLEAN,
    soil_moisture_1_pct            DOUBLE PRECISION,
    soil_moisture_2_pct            DOUBLE PRECISION,
    soil_moisture_avg_pct          DOUBLE PRECISION,
    soil_temp_c                    DOUBLE PRECISION,
    soil_ph                        DOUBLE PRECISION,
    soil_ec_ms_cm                  DOUBLE PRECISION,
    soil_n_mg_kg                   DOUBLE PRECISION,
    soil_p_mg_kg                   DOUBLE PRECISION,
    soil_k_mg_kg                   DOUBLE PRECISION,
    npk_sensor_raw_hex             TEXT,
    water_flow_lpm                 DOUBLE PRECISION,
    water_volume_liters_session    DOUBLE PRECISION,
    water_volume_liters_cumulative DOUBLE PRECISION,
    valve_status                   TEXT CHECK (valve_status IN ('open','closed','fault')),
    pump_running                   BOOLEAN,
    pump_current_amps              DOUBLE PRECISION,
    pump_runtime_minutes_today     INT,
    dry_run_detected               BOOLEAN,
    tamper_detected                BOOLEAN,
    enclosure_temp_c               DOUBLE PRECISION,
    fault_flags                    TEXT,
    sensor_health_json             JSONB,
    firmware_version               TEXT,
    uptime_seconds                 INT,
    CONSTRAINT node_sensor_readings_idem UNIQUE (node_id, recorded_at)
);
CREATE INDEX node_sensor_readings_farm_time_idx ON node_sensor_readings (farm_id, recorded_at);
CREATE INDEX node_sensor_readings_plot_time_idx ON node_sensor_readings (plot_id, recorded_at);
CREATE INDEX node_sensor_readings_tenant_idx ON node_sensor_readings (tenant_id);

-- ---------------------------------------------------------------------------
-- TABLE 6: weather_station_readings  (plain here; partitioned in 0005)
-- ---------------------------------------------------------------------------
CREATE TABLE weather_station_readings (
    weather_id                BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tenant_id                 UUID NOT NULL REFERENCES tenants(id),
    master_node_id            TEXT NOT NULL REFERENCES device_registry(device_id),
    farm_id                   UUID NOT NULL REFERENCES farms(farm_id),
    recorded_at               TIMESTAMPTZ NOT NULL,
    air_temp_c                DOUBLE PRECISION,
    air_temp_min_c            DOUBLE PRECISION,
    air_temp_max_c            DOUBLE PRECISION,
    humidity_pct              DOUBLE PRECISION,
    dew_point_c               DOUBLE PRECISION,
    atmospheric_pressure_hpa  DOUBLE PRECISION,
    wind_speed_kmh            DOUBLE PRECISION,
    wind_speed_max_gust_kmh   DOUBLE PRECISION,
    wind_direction_degrees    DOUBLE PRECISION,
    wind_direction_cardinal   TEXT,
    rain_mm_current_hour      DOUBLE PRECISION,
    rain_mm_today             DOUBLE PRECISION,
    rain_mm_last_7_days       DOUBLE PRECISION,
    rain_mm_this_season       DOUBLE PRECISION,
    light_intensity_lux       DOUBLE PRECISION,
    uv_index                  DOUBLE PRECISION,
    leaf_wetness_pct          DOUBLE PRECISION,
    fog_detected              BOOLEAN,
    fog_intensity             TEXT CHECK (fog_intensity IN ('none','light','moderate','dense')),
    frost_risk                BOOLEAN,
    heat_stress_index         DOUBLE PRECISION,
    evapotranspiration_mm     DOUBLE PRECISION,
    weather_station_battery_v DOUBLE PRECISION,
    anemometer_fault          BOOLEAN,
    rain_gauge_fault          BOOLEAN,
    CONSTRAINT weather_station_readings_idem UNIQUE (master_node_id, recorded_at)
);
CREATE INDEX weather_station_readings_farm_time_idx ON weather_station_readings (farm_id, recorded_at);
CREATE INDEX weather_station_readings_tenant_idx ON weather_station_readings (tenant_id);

-- ---------------------------------------------------------------------------
-- TABLE 7: satellite_data  (not partitioned)
-- ---------------------------------------------------------------------------
CREATE TABLE satellite_data (
    sat_id                BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tenant_id             UUID NOT NULL REFERENCES tenants(id),
    farm_id               UUID NOT NULL REFERENCES farms(farm_id),
    plot_id               TEXT REFERENCES plots(plot_id),
    satellite_source      TEXT NOT NULL CHECK (satellite_source IN ('sentinel2','sentinel1','landsat8','modis','smap','planet')),
    image_date            DATE NOT NULL,
    cloud_cover_pct       DOUBLE PRECISION,
    resolution_m          DOUBLE PRECISION,
    ndvi_value            DOUBLE PRECISION,
    ndvi_min              DOUBLE PRECISION,
    ndvi_max              DOUBLE PRECISION,
    ndvi_status           TEXT CHECK (ndvi_status IN ('healthy','moderate','stressed','critical')),
    ndre_value            DOUBLE PRECISION,
    evi_value             DOUBLE PRECISION,
    savi_value            DOUBLE PRECISION,
    ndwi_value            DOUBLE PRECISION,
    ndwi_status           TEXT CHECK (ndwi_status IN ('well_watered','adequate','stressed','severe')),
    ndmi_value            DOUBLE PRECISION,
    soil_moisture_index   DOUBLE PRECISION,
    soil_moisture_source  TEXT CHECK (soil_moisture_source IN ('smap','sentinel1','modis')),
    chlorophyll_index     DOUBLE PRECISION,
    lai_value             DOUBLE PRECISION,
    crop_health_score     DOUBLE PRECISION,
    stressed_area_pct     DOUBLE PRECISION,
    stressed_zone_geojson JSONB,
    pest_risk_index       DOUBLE PRECISION,
    disease_risk_index    DOUBLE PRECISION,
    yield_prediction_qtl  DOUBLE PRECISION,
    raw_image_url         TEXT,
    processed_at          TIMESTAMPTZ,
    gee_task_id           TEXT
);
CREATE INDEX satellite_data_tenant_idx ON satellite_data (tenant_id);
CREATE INDEX satellite_data_farm_date_idx ON satellite_data (farm_id, image_date);
CREATE INDEX satellite_data_plot_date_idx ON satellite_data (plot_id, image_date);

-- ---------------------------------------------------------------------------
-- TABLE 8: weather_forecasts  (plain here; partitioned by fetched_at in 0005)
-- ---------------------------------------------------------------------------
CREATE TABLE weather_forecasts (
    forecast_id               BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tenant_id                 UUID NOT NULL REFERENCES tenants(id),
    farm_id                   UUID NOT NULL REFERENCES farms(farm_id),
    fetched_at                TIMESTAMPTZ NOT NULL,
    forecast_for_date         DATE NOT NULL,
    forecast_hour             INT,
    source_api                TEXT NOT NULL,
    temp_c                    DOUBLE PRECISION,
    temp_min_c                DOUBLE PRECISION,
    temp_max_c                DOUBLE PRECISION,
    humidity_pct              DOUBLE PRECISION,
    rain_probability_pct      DOUBLE PRECISION,
    rain_mm_expected          DOUBLE PRECISION,
    wind_speed_kmh            DOUBLE PRECISION,
    wind_direction            TEXT,
    fog_probability_pct       DOUBLE PRECISION,
    cloud_cover_pct           DOUBLE PRECISION,
    spray_suitability         TEXT CHECK (spray_suitability IN ('good','moderate','poor','not_recommended')),
    irrigation_recommendation TEXT CHECK (irrigation_recommendation IN ('irrigate','skip_rain','reduce','normal')),
    frost_risk                BOOLEAN,
    heat_wave_risk            BOOLEAN
);
CREATE INDEX weather_forecasts_tenant_idx ON weather_forecasts (tenant_id);
CREATE INDEX weather_forecasts_lookup_idx ON weather_forecasts (farm_id, forecast_for_date, forecast_hour);

-- ---------------------------------------------------------------------------
-- TABLE 9: electricity_schedule_log
-- ---------------------------------------------------------------------------
CREATE TABLE electricity_schedule_log (
    elec_id                 BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    farm_id                 UUID NOT NULL REFERENCES farms(farm_id),
    recorded_at             TIMESTAMPTZ NOT NULL,
    electricity_on_at       TIMESTAMPTZ,
    electricity_off_at      TIMESTAMPTZ,
    duration_minutes        INT,
    detection_method        TEXT CHECK (detection_method IN ('current_sensor','pump_runtime','manual_input')),
    pump_used_during        BOOLEAN,
    pattern_confidence_pct  DOUBLE PRECISION,
    detected_schedule_json  JSONB,
    schedule_changed_flag   BOOLEAN,
    last_schedule_change_at  TIMESTAMPTZ,
    ai_irrigation_adapted   BOOLEAN,
    notes                   TEXT
);
CREATE INDEX electricity_schedule_log_tenant_idx ON electricity_schedule_log (tenant_id);
CREATE INDEX electricity_schedule_log_farm_time_idx ON electricity_schedule_log (farm_id, recorded_at);

-- ---------------------------------------------------------------------------
-- TABLE 12: ai_suggestions  (before irrigation_events / farmer_actions for FK)
-- v3 columns (prompt_template_version, llm_cost_inr, review_*) added in 0002.
-- ---------------------------------------------------------------------------
CREATE TABLE ai_suggestions (
    suggestion_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                UUID NOT NULL REFERENCES tenants(id),
    farmer_id                UUID NOT NULL REFERENCES farmers(farmer_id),
    farm_id                  UUID NOT NULL REFERENCES farms(farm_id),
    plot_id                  TEXT REFERENCES plots(plot_id),
    season_id                UUID NOT NULL REFERENCES crop_seasons(season_id),
    generated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    suggestion_type          TEXT NOT NULL CHECK (suggestion_type IN ('daily','alert','weekly','monthly','end_of_season')),
    crop_age_days            INT,
    crop_stage               TEXT,
    soil_moisture_at_time    DOUBLE PRECISION,
    ndvi_at_time             DOUBLE PRECISION,
    weather_summary_json     JSONB,
    electricity_window_json  JSONB,
    water_source_status      TEXT,
    water_action             TEXT,
    water_liters_suggested   DOUBLE PRECISION,
    water_time_suggested     TEXT,
    water_reason             TEXT,
    fertilizer_needed        BOOLEAN,
    fertilizer_product       TEXT,
    fertilizer_qty_kg_per_acre DOUBLE PRECISION,
    fertilizer_timing        TEXT,
    fertilizer_reason        TEXT,
    micronutrient_deficiency TEXT,
    micronutrient_product    TEXT,
    micronutrient_qty        TEXT,
    micronutrient_reason     TEXT,
    pesticide_spray_today    BOOLEAN,
    pesticide_product        TEXT,
    pesticide_dose           TEXT,
    pesticide_reason         TEXT,
    tomorrow_plan            TEXT,
    weekly_tip               TEXT,
    full_message_marathi     TEXT,
    whatsapp_sent            BOOLEAN,
    whatsapp_sent_at         TIMESTAMPTZ,
    ai_model_version         TEXT,
    tokens_used              INT,
    generation_time_ms       INT
);
CREATE INDEX ai_suggestions_tenant_idx ON ai_suggestions (tenant_id);
CREATE INDEX ai_suggestions_farmer_time_idx ON ai_suggestions (farmer_id, generated_at);

-- ---------------------------------------------------------------------------
-- TABLE 10: irrigation_events
-- ---------------------------------------------------------------------------
CREATE TABLE irrigation_events (
    irrigation_id          BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tenant_id              UUID NOT NULL REFERENCES tenants(id),
    farm_id                UUID NOT NULL REFERENCES farms(farm_id),
    plot_id                TEXT NOT NULL REFERENCES plots(plot_id),
    farmer_id              UUID NOT NULL REFERENCES farmers(farmer_id),
    season_id              UUID NOT NULL REFERENCES crop_seasons(season_id),
    started_at             TIMESTAMPTZ NOT NULL,
    ended_at               TIMESTAMPTZ,
    duration_minutes       INT,
    water_liters           DOUBLE PRECISION,
    flow_rate_lpm_avg      DOUBLE PRECISION,
    trigger_type           TEXT NOT NULL CHECK (trigger_type IN ('ai_auto','ai_suggested','manual','scheduled','emergency')),
    ai_suggestion_id       UUID REFERENCES ai_suggestions(suggestion_id),
    soil_moisture_before   DOUBLE PRECISION,
    soil_moisture_after    DOUBLE PRECISION,
    valve_id               TEXT,
    pump_id                TEXT,
    water_source_used      TEXT CHECK (water_source_used IN ('well','borewell','farm_pond','canal')),
    electricity_available  BOOLEAN,
    weather_at_irrigation  JSONB,
    crop_stage_at_time     TEXT,
    ai_recommended_liters  DOUBLE PRECISION,
    variance_liters        DOUBLE PRECISION,
    dry_run_event          BOOLEAN,
    notes                  TEXT
);
CREATE INDEX irrigation_events_tenant_idx ON irrigation_events (tenant_id);
CREATE INDEX irrigation_events_plot_time_idx ON irrigation_events (plot_id, started_at);

-- ---------------------------------------------------------------------------
-- TABLE 11: water_source_status
-- ---------------------------------------------------------------------------
CREATE TABLE water_source_status (
    source_id                  BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tenant_id                  UUID NOT NULL REFERENCES tenants(id),
    farm_id                    UUID NOT NULL REFERENCES farms(farm_id),
    source_type                TEXT NOT NULL CHECK (source_type IN ('well','borewell','farm_pond','canal')),
    recorded_at                TIMESTAMPTZ NOT NULL,
    water_level_cm             DOUBLE PRECISION,
    water_level_pct            DOUBLE PRECISION,
    water_level_liters_estimate DOUBLE PRECISION,
    level_status               TEXT CHECK (level_status IN ('full','adequate','low','critical','empty')),
    turbidity_ntu              DOUBLE PRECISION,
    water_temp_c               DOUBLE PRECISION,
    water_ph                   DOUBLE PRECISION,
    water_ec_ms_cm             DOUBLE PRECISION,
    pump_drawdown_cm           DOUBLE PRECISION,
    recovery_rate_cm_per_hour  DOUBLE PRECISION,
    recharge_status            TEXT CHECK (recharge_status IN ('recharging','stable','depleting')),
    alert_sent                 BOOLEAN,
    sensor_id                  TEXT
);
CREATE INDEX water_source_status_tenant_idx ON water_source_status (tenant_id);
CREATE INDEX water_source_status_farm_time_idx ON water_source_status (farm_id, recorded_at);

-- ---------------------------------------------------------------------------
-- TABLE 13: farmer_actions
-- ---------------------------------------------------------------------------
CREATE TABLE farmer_actions (
    action_id              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tenant_id              UUID NOT NULL REFERENCES tenants(id),
    farmer_id              UUID NOT NULL REFERENCES farmers(farmer_id),
    farm_id                UUID NOT NULL REFERENCES farms(farm_id),
    plot_id                TEXT REFERENCES plots(plot_id),
    season_id              UUID NOT NULL REFERENCES crop_seasons(season_id),
    action_date            DATE NOT NULL,
    action_time            TIME,
    action_type            TEXT NOT NULL CHECK (action_type IN ('watering','fertilizer','pesticide_spray','harvesting','weeding','ploughing','other')),
    ai_suggestion_id       UUID REFERENCES ai_suggestions(suggestion_id),
    ai_suggested           BOOLEAN,
    farmer_followed_ai     BOOLEAN,
    water_liters           DOUBLE PRECISION,
    fertilizer_name        TEXT,
    fertilizer_qty_kg      DOUBLE PRECISION,
    fertilizer_cost_rs     NUMERIC(10,2),
    pesticide_name         TEXT,
    pesticide_qty_ml_or_g  DOUBLE PRECISION,
    pesticide_area_acre    NUMERIC(10,2),
    pesticide_cost_rs      NUMERIC(10,2),
    labour_cost_rs         NUMERIC(10,2),
    equipment_used         TEXT,
    weather_at_action      JSONB,
    farmer_note            TEXT,
    source                 TEXT NOT NULL CHECK (source IN ('whatsapp_reply','app','manual_entry','auto_sensor')),
    recorded_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX farmer_actions_tenant_idx ON farmer_actions (tenant_id);
CREATE INDEX farmer_actions_farmer_date_idx ON farmer_actions (farmer_id, action_date);

-- ---------------------------------------------------------------------------
-- TABLE 14: ai_learning_log
-- ---------------------------------------------------------------------------
CREATE TABLE ai_learning_log (
    learning_id             BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    farmer_id               UUID NOT NULL REFERENCES farmers(farmer_id),
    season_id               UUID NOT NULL REFERENCES crop_seasons(season_id),
    suggestion_id           UUID NOT NULL REFERENCES ai_suggestions(suggestion_id),
    action_id               BIGINT REFERENCES farmer_actions(action_id),
    learning_date           DATE NOT NULL,
    suggestion_type         TEXT,
    ai_suggested_liters     DOUBLE PRECISION,
    farmer_gave_liters      DOUBLE PRECISION,
    water_variance_liters   DOUBLE PRECISION,
    ndvi_before             DOUBLE PRECISION,
    ndvi_7days_after        DOUBLE PRECISION,
    ndvi_change             DOUBLE PRECISION,
    moisture_before         DOUBLE PRECISION,
    moisture_3days_after    DOUBLE PRECISION,
    crop_health_improved    BOOLEAN,
    suggestion_accuracy     TEXT CHECK (suggestion_accuracy IN ('good','slight_over','slight_under','poor')),
    soil_type               TEXT,
    crop_stage              TEXT,
    weather_pattern         TEXT,
    water_coefficient_adjusted DOUBLE PRECISION,
    notes                   TEXT,
    learning_applied_at     TIMESTAMPTZ
);
CREATE INDEX ai_learning_log_tenant_idx ON ai_learning_log (tenant_id);
CREATE INDEX ai_learning_log_season_idx ON ai_learning_log (season_id);

-- ---------------------------------------------------------------------------
-- TABLE 16: component_inventory
-- ---------------------------------------------------------------------------
CREATE TABLE component_inventory (
    component_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    device_id               TEXT NOT NULL REFERENCES device_registry(device_id),
    component_name          TEXT NOT NULL,
    component_category      TEXT NOT NULL CHECK (component_category IN ('sensor','power','communication','protection','valve','camera','other')),
    manufacturer            TEXT,
    model_number            TEXT,
    serial_number           TEXT,
    purchase_date           DATE,
    purchase_cost_rs        NUMERIC(10,2),
    supplier                TEXT,
    warranty_months         INT,
    installation_date       DATE,
    status                  TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','faulty','replaced','removed')),
    last_calibration_date   DATE,
    next_calibration_due    DATE,
    calibration_values_json JSONB,
    fault_history_json      JSONB,
    replacement_component_id UUID,
    notes                   TEXT
);
CREATE INDEX component_inventory_tenant_idx ON component_inventory (tenant_id);
CREATE INDEX component_inventory_device_idx ON component_inventory (device_id);

-- ---------------------------------------------------------------------------
-- TABLE 17: technician_installations
-- ---------------------------------------------------------------------------
CREATE TABLE technician_installations (
    installation_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                  UUID NOT NULL REFERENCES tenants(id),
    technician_id              TEXT NOT NULL,
    technician_name            TEXT NOT NULL,
    technician_phone           TEXT NOT NULL,
    farm_id                    UUID NOT NULL REFERENCES farms(farm_id),
    farmer_id                  UUID NOT NULL REFERENCES farmers(farmer_id),
    visit_type                 TEXT NOT NULL CHECK (visit_type IN ('installation','service','upgrade','inspection','replacement')),
    visit_date                 DATE NOT NULL,
    arrival_time               TIME,
    departure_time             TIME,
    duration_hours             DOUBLE PRECISION,
    devices_installed_json     JSONB,
    nodes_installed_count      INT,
    solar_panels_installed     INT,
    poles_installed            INT,
    cable_meters_laid          DOUBLE PRECISION,
    soil_type_observed         TEXT,
    moisture_at_install        DOUBLE PRECISION,
    well_depth_measured_ft     INT,
    borewell_yield_tested_lpm  DOUBLE PRECISION,
    farm_pond_level_pct        DOUBLE PRECISION,
    water_quality_check        TEXT,
    electricity_tested         BOOLEAN,
    signal_4g_tested           BOOLEAN,
    signal_4g_result           TEXT CHECK (signal_4g_result IN ('excellent','good','fair','poor')),
    whatsapp_test_sent         BOOLEAN,
    sensors_calibrated         BOOLEAN,
    farmer_training_done       BOOLEAN,
    farmer_training_topics     TEXT,
    installation_photos_urls   JSONB,
    issues_found               TEXT,
    issues_resolved            TEXT,
    pending_work               TEXT,
    farmer_signature_collected BOOLEAN,
    installation_quality_score INT CHECK (installation_quality_score BETWEEN 1 AND 10),
    notes                      TEXT,
    next_service_due           DATE
);
CREATE INDEX technician_installations_tenant_idx ON technician_installations (tenant_id);
CREATE INDEX technician_installations_farm_idx ON technician_installations (farm_id);

-- ---------------------------------------------------------------------------
-- TABLE 18: service_maintenance
-- ---------------------------------------------------------------------------
CREATE TABLE service_maintenance (
    service_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    device_id               TEXT NOT NULL REFERENCES device_registry(device_id),
    farm_id                 UUID NOT NULL REFERENCES farms(farm_id),
    technician_id           TEXT,
    service_date            DATE NOT NULL,
    service_type            TEXT NOT NULL CHECK (service_type IN ('preventive','corrective','emergency','upgrade','calibration')),
    complaint_description   TEXT,
    root_cause              TEXT,
    action_taken            TEXT,
    components_replaced_json JSONB,
    spare_parts_cost_rs     NUMERIC(10,2),
    labour_cost_rs          NUMERIC(10,2),
    downtime_hours          DOUBLE PRECISION,
    resolution_time_hours   DOUBLE PRECISION,
    firmware_updated        BOOLEAN,
    new_firmware_version    TEXT,
    service_status          TEXT NOT NULL DEFAULT 'pending' CHECK (service_status IN ('completed','pending','escalated')),
    farmer_satisfaction     INT CHECK (farmer_satisfaction BETWEEN 1 AND 5),
    warranty_claim          BOOLEAN,
    notes                   TEXT
);
CREATE INDEX service_maintenance_tenant_idx ON service_maintenance (tenant_id);
CREATE INDEX service_maintenance_device_idx ON service_maintenance (device_id);

-- ---------------------------------------------------------------------------
-- TABLE 19: alerts_notifications
-- ---------------------------------------------------------------------------
CREATE TABLE alerts_notifications (
    alert_id               BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tenant_id              UUID NOT NULL REFERENCES tenants(id),
    farm_id                UUID NOT NULL REFERENCES farms(farm_id),
    farmer_id              UUID NOT NULL REFERENCES farmers(farmer_id),
    device_id              TEXT REFERENCES device_registry(device_id),
    alert_type             TEXT NOT NULL CHECK (alert_type IN ('dry_run','low_water','power_off','pump_fault','sensor_fault','rain_heavy','frost','pest_risk','disease_risk','low_battery','device_offline','tamper')),
    severity               TEXT NOT NULL CHECK (severity IN ('info','warning','critical')),
    alert_message_marathi  TEXT NOT NULL,
    alert_value            DOUBLE PRECISION,
    alert_threshold        DOUBLE PRECISION,
    triggered_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    whatsapp_sent          BOOLEAN,
    whatsapp_sent_at       TIMESTAMPTZ,
    sms_sent               BOOLEAN,
    auto_action_taken      TEXT,
    farmer_acknowledged    BOOLEAN,
    acknowledged_at        TIMESTAMPTZ,
    resolved               BOOLEAN,
    resolved_at            TIMESTAMPTZ,
    resolution_note        TEXT
);
CREATE INDEX alerts_notifications_tenant_idx ON alerts_notifications (tenant_id);
CREATE INDEX alerts_notifications_farm_time_idx ON alerts_notifications (farm_id, triggered_at);

-- ---------------------------------------------------------------------------
-- TABLE 20: subscriptions_billing
-- ---------------------------------------------------------------------------
CREATE TABLE subscriptions_billing (
    subscription_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id              UUID NOT NULL REFERENCES tenants(id),
    farmer_id              UUID NOT NULL REFERENCES farmers(farmer_id),
    plan_type              TEXT NOT NULL CHECK (plan_type IN ('basic','standard','pro','custom','lease')),
    plan_start_date        DATE NOT NULL,
    plan_end_date          DATE NOT NULL,
    hardware_price_rs      NUMERIC(12,2),
    monthly_fee_rs         NUMERIC(10,2),
    emi_amount_rs          NUMERIC(10,2),
    emi_months             INT,
    payment_mode           TEXT CHECK (payment_mode IN ('full','emi','lease','subsidized')),
    govt_subsidy_scheme    TEXT,
    subsidy_amount_rs      NUMERIC(10,2),
    payment_gateway        TEXT,
    last_payment_date      DATE,
    last_payment_amount_rs NUMERIC(10,2),
    next_payment_due       DATE,
    total_paid_rs          NUMERIC(12,2),
    outstanding_rs         NUMERIC(12,2),
    payment_status         TEXT NOT NULL CHECK (payment_status IN ('paid','due','overdue','cancelled')),
    auto_renewal           BOOLEAN,
    dealer_id              TEXT,
    dealer_commission_pct  DOUBLE PRECISION,
    churn_risk             TEXT CHECK (churn_risk IN ('low','medium','high')),
    notes                  TEXT
);
CREATE INDEX subscriptions_billing_tenant_idx ON subscriptions_billing (tenant_id);
CREATE INDEX subscriptions_billing_farmer_idx ON subscriptions_billing (farmer_id);

-- ---------------------------------------------------------------------------
-- TABLE 21: product_performance_bi
-- ---------------------------------------------------------------------------
CREATE TABLE product_performance_bi (
    perf_id                       BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tenant_id                     UUID NOT NULL REFERENCES tenants(id),
    farm_id                       UUID NOT NULL REFERENCES farms(farm_id),
    farmer_id                     UUID NOT NULL REFERENCES farmers(farmer_id),
    season_id                     UUID NOT NULL REFERENCES crop_seasons(season_id),
    district                      TEXT NOT NULL,
    period_month                  DATE NOT NULL,
    water_saved_liters            DOUBLE PRECISION,
    water_saved_pct               DOUBLE PRECISION,
    fertilizer_saved_kg           DOUBLE PRECISION,
    fertilizer_saved_rs           NUMERIC(10,2),
    pesticide_sprays_ai_recommended INT,
    pesticide_sprays_done         INT,
    spray_saved_count             INT,
    spray_saved_rs                NUMERIC(10,2),
    ndvi_avg_this_season          DOUBLE PRECISION,
    ndvi_improvement_vs_last_season DOUBLE PRECISION,
    yield_actual_qtl              DOUBLE PRECISION,
    yield_last_season_qtl         DOUBLE PRECISION,
    yield_improvement_pct         DOUBLE PRECISION,
    ai_suggestions_sent           INT,
    ai_suggestions_followed       INT,
    ai_follow_rate_pct            DOUBLE PRECISION,
    device_uptime_pct             DOUBLE PRECISION,
    alerts_sent                   INT,
    alerts_critical               INT,
    farmer_satisfaction_score     DOUBLE PRECISION,
    roi_estimate_rs               NUMERIC(12,2),
    product_effective             BOOLEAN
);
CREATE INDEX product_performance_bi_tenant_idx ON product_performance_bi (tenant_id);
CREATE INDEX product_performance_bi_district_month_idx ON product_performance_bi (district, period_month);

-- ---------------------------------------------------------------------------
-- Deferred circular FKs (both sides now exist)
-- ---------------------------------------------------------------------------
ALTER TABLE plots
    ADD CONSTRAINT plots_node_fk
        FOREIGN KEY (node_id) REFERENCES device_registry(device_id),
    ADD CONSTRAINT plots_current_season_fk
        FOREIGN KEY (crop_current_season_id) REFERENCES crop_seasons(season_id);
"""


DOWNGRADE_SQL = r"""
ALTER TABLE plots
    DROP CONSTRAINT IF EXISTS plots_node_fk,
    DROP CONSTRAINT IF EXISTS plots_current_season_fk;

DROP TABLE IF EXISTS product_performance_bi CASCADE;
DROP TABLE IF EXISTS subscriptions_billing CASCADE;
DROP TABLE IF EXISTS alerts_notifications CASCADE;
DROP TABLE IF EXISTS service_maintenance CASCADE;
DROP TABLE IF EXISTS technician_installations CASCADE;
DROP TABLE IF EXISTS component_inventory CASCADE;
DROP TABLE IF EXISTS ai_learning_log CASCADE;
DROP TABLE IF EXISTS farmer_actions CASCADE;
DROP TABLE IF EXISTS water_source_status CASCADE;
DROP TABLE IF EXISTS irrigation_events CASCADE;
DROP TABLE IF EXISTS ai_suggestions CASCADE;
DROP TABLE IF EXISTS electricity_schedule_log CASCADE;
DROP TABLE IF EXISTS weather_forecasts CASCADE;
DROP TABLE IF EXISTS satellite_data CASCADE;
DROP TABLE IF EXISTS weather_station_readings CASCADE;
DROP TABLE IF EXISTS node_sensor_readings CASCADE;
DROP TABLE IF EXISTS device_registry CASCADE;
DROP TABLE IF EXISTS crop_seasons CASCADE;
DROP TABLE IF EXISTS plots CASCADE;
DROP TABLE IF EXISTS farms CASCADE;
DROP TABLE IF EXISTS farmers CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
