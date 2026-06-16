"""0006 aggregate materialized views + dashboard view.

Four materialized views (hourly/daily for node + weather) per roadmap §2.5,
each with a UNIQUE index so ``REFRESH MATERIALIZED VIEW CONCURRENTLY`` works,
plus the non-materialized ``v_plot_latest_state`` dashboard view.

Column sets are derived from the source reading tables (the technical-ref
§2.5.2 definitions were not available verbatim -- see docs/SCHEMA_DECISIONS.md).

Revision ID: 0006
Revises: 0005
Create Date: Phase 1
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
-- node_readings_hourly ------------------------------------------------------
CREATE MATERIALIZED VIEW node_readings_hourly AS
SELECT
    tenant_id,
    node_id,
    plot_id,
    farm_id,
    date_trunc('hour', recorded_at)        AS bucket_hour,
    count(*)                               AS sample_count,
    avg(soil_moisture_avg_pct)             AS soil_moisture_avg_pct,
    min(soil_moisture_avg_pct)             AS soil_moisture_min_pct,
    max(soil_moisture_avg_pct)             AS soil_moisture_max_pct,
    avg(soil_temp_c)                       AS soil_temp_c,
    avg(soil_ph)                           AS soil_ph,
    avg(soil_ec_ms_cm)                     AS soil_ec_ms_cm,
    avg(soil_n_mg_kg)                      AS soil_n_mg_kg,
    avg(soil_p_mg_kg)                      AS soil_p_mg_kg,
    avg(soil_k_mg_kg)                      AS soil_k_mg_kg,
    avg(battery_percent)                   AS battery_percent,
    max(water_volume_liters_cumulative)    AS water_volume_liters_cumulative
FROM node_sensor_readings
GROUP BY tenant_id, node_id, plot_id, farm_id, date_trunc('hour', recorded_at)
WITH DATA;
CREATE UNIQUE INDEX node_readings_hourly_uq
    ON node_readings_hourly (tenant_id, node_id, plot_id, farm_id, bucket_hour);

-- node_readings_daily -------------------------------------------------------
CREATE MATERIALIZED VIEW node_readings_daily AS
SELECT
    tenant_id,
    node_id,
    plot_id,
    farm_id,
    date_trunc('day', recorded_at)         AS bucket_day,
    count(*)                               AS sample_count,
    avg(soil_moisture_avg_pct)             AS soil_moisture_avg_pct,
    min(soil_moisture_avg_pct)             AS soil_moisture_min_pct,
    max(soil_moisture_avg_pct)             AS soil_moisture_max_pct,
    avg(soil_temp_c)                       AS soil_temp_c,
    avg(soil_ph)                           AS soil_ph,
    avg(soil_ec_ms_cm)                     AS soil_ec_ms_cm,
    avg(soil_n_mg_kg)                      AS soil_n_mg_kg,
    avg(soil_p_mg_kg)                      AS soil_p_mg_kg,
    avg(soil_k_mg_kg)                      AS soil_k_mg_kg,
    avg(battery_percent)                   AS battery_percent,
    max(water_volume_liters_cumulative)    AS water_volume_liters_cumulative
FROM node_sensor_readings
GROUP BY tenant_id, node_id, plot_id, farm_id, date_trunc('day', recorded_at)
WITH DATA;
CREATE UNIQUE INDEX node_readings_daily_uq
    ON node_readings_daily (tenant_id, node_id, plot_id, farm_id, bucket_day);

-- weather_hourly ------------------------------------------------------------
CREATE MATERIALIZED VIEW weather_hourly AS
SELECT
    tenant_id,
    farm_id,
    master_node_id,
    date_trunc('hour', recorded_at)        AS bucket_hour,
    count(*)                               AS sample_count,
    avg(air_temp_c)                        AS air_temp_c,
    min(air_temp_c)                        AS air_temp_min_c,
    max(air_temp_c)                        AS air_temp_max_c,
    avg(humidity_pct)                      AS humidity_pct,
    max(rain_mm_today)                     AS rain_mm_today,
    avg(wind_speed_kmh)                    AS wind_speed_kmh,
    max(wind_speed_max_gust_kmh)           AS wind_speed_max_gust_kmh,
    avg(evapotranspiration_mm)             AS evapotranspiration_mm,
    avg(leaf_wetness_pct)                  AS leaf_wetness_pct
FROM weather_station_readings
GROUP BY tenant_id, farm_id, master_node_id, date_trunc('hour', recorded_at)
WITH DATA;
CREATE UNIQUE INDEX weather_hourly_uq
    ON weather_hourly (tenant_id, farm_id, master_node_id, bucket_hour);

-- weather_daily -------------------------------------------------------------
CREATE MATERIALIZED VIEW weather_daily AS
SELECT
    tenant_id,
    farm_id,
    master_node_id,
    date_trunc('day', recorded_at)         AS bucket_day,
    count(*)                               AS sample_count,
    avg(air_temp_c)                        AS air_temp_c,
    min(air_temp_c)                        AS air_temp_min_c,
    max(air_temp_c)                        AS air_temp_max_c,
    avg(humidity_pct)                      AS humidity_pct,
    max(rain_mm_today)                     AS rain_mm_today,
    avg(wind_speed_kmh)                    AS wind_speed_kmh,
    max(wind_speed_max_gust_kmh)           AS wind_speed_max_gust_kmh,
    avg(evapotranspiration_mm)             AS evapotranspiration_mm,
    avg(leaf_wetness_pct)                  AS leaf_wetness_pct
FROM weather_station_readings
GROUP BY tenant_id, farm_id, master_node_id, date_trunc('day', recorded_at)
WITH DATA;
CREATE UNIQUE INDEX weather_daily_uq
    ON weather_daily (tenant_id, farm_id, master_node_id, bucket_day);

-- v_plot_latest_state (computed at query time) ------------------------------
CREATE VIEW v_plot_latest_state AS
SELECT DISTINCT ON (p.plot_id)
    p.plot_id,
    p.tenant_id,
    p.farm_id,
    p.plot_name,
    p.data_tier,
    p.plot_status,
    r.recorded_at          AS last_reading_at,
    r.soil_moisture_avg_pct,
    r.soil_temp_c,
    r.soil_ph,
    r.soil_ec_ms_cm,
    r.soil_n_mg_kg,
    r.soil_p_mg_kg,
    r.soil_k_mg_kg,
    r.battery_percent,
    r.valve_status,
    r.pump_running
FROM plots p
LEFT JOIN node_sensor_readings r ON r.plot_id = p.plot_id
ORDER BY p.plot_id, r.recorded_at DESC NULLS LAST;
"""


DOWNGRADE_SQL = r"""
DROP VIEW IF EXISTS v_plot_latest_state;
DROP MATERIALIZED VIEW IF EXISTS weather_daily;
DROP MATERIALIZED VIEW IF EXISTS weather_hourly;
DROP MATERIALIZED VIEW IF EXISTS node_readings_daily;
DROP MATERIALIZED VIEW IF EXISTS node_readings_hourly;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
