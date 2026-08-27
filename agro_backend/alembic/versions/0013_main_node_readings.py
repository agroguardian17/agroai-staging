"""0013 main_node_readings — Round 17.5 persistence for v2-master heartbeats.

The 2026-08-27 v2 Main Node firmware publishes a master-only heartbeat
every ``MASTER_HEARTBEAT_MS`` (5 min) on the wire schema
``agro-guardian/telemetry/v2-master``. It carries:

* the Main Node's own weather-station readings (BME280 + INA219 + rain +
  wind), and
* a ``sub_node_online`` liveness flag + ``sub_node_silence_ms`` counter
  measured against the last LoRa RX from the Sub Node.

This migration creates the durable landing zone. The broker already meters
the incoming heartbeat via ``agro_main_node_heartbeat_total`` (see
``app/lib/metrics.py``); Round 17.5 adds the row-level history that ops
tooling and future dashboards can query.

Design decisions recorded in ``docs/SCHEMA_DECISIONS.md`` §13.2:

* Main-Node-keyed, not plot-keyed — heartbeat is infrastructure-level.
* Composite unique on ``(main_node_id, recorded_at)`` for idempotent
  UPSERT (mirrors ``node_sensor_readings_idem`` on the Sub Node table).
* Not monthly-partitioned at pilot scale (~105 k rows/year/Main Node);
  partitioning is a follow-up round when volume warrants.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-27
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS main_node_readings (
    reading_id           BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    tenant_id            UUID        NOT NULL REFERENCES tenants(id),
    farm_id              UUID        NOT NULL REFERENCES farms(farm_id),
    main_node_id         TEXT        NOT NULL REFERENCES device_registry(device_id) ON DELETE CASCADE,

    -- Timing (both tz-aware; broker enforces this via _normalize_clock_skew
    -- before insert so we never carry naive datetimes here).
    recorded_at          TIMESTAMPTZ NOT NULL,
    received_at_master   TIMESTAMPTZ NOT NULL,

    -- Timestamp provenance emitted by firmware ("ntp"/"rtc"/"none"/NULL).
    time_source          TEXT,

    -- Sub Node liveness at the moment this heartbeat was assembled.
    -- (Even though this is a Main-Node-keyed table, the heartbeat's whole
    -- reason for existing is to expose sub_node_online independently of
    -- the Sub Node's own cadence.)
    sub_node_online      BOOLEAN     NOT NULL DEFAULT TRUE,
    sub_node_silence_ms  BIGINT      NOT NULL DEFAULT 0,

    -- BME280 weather block
    bme280_temp_c        DOUBLE PRECISION,
    bme280_humidity_pct  DOUBLE PRECISION,
    bme280_pressure_pa   DOUBLE PRECISION,

    -- INA219 power block
    ina219_bus_v         DOUBLE PRECISION,
    ina219_current_ma    DOUBLE PRECISION,

    -- Tipping-bucket rain + anemometer pulse counts over the heartbeat
    -- window (Main Node's own ISRs, reset each publish).
    rain_pulses_window   INTEGER     NOT NULL DEFAULT 0,
    wind_pulses_window   INTEGER     NOT NULL DEFAULT 0,
    wind_dir_adc         INTEGER     NOT NULL DEFAULT 0,

    -- Firmware version string carried on the payload.
    firmware_version     TEXT,

    -- Bookkeeping. `inserted_at` is server-side clock; useful for detecting
    -- ingest latency vs `received_at_master`.
    inserted_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Idempotent UPSERT: the broker retries after transient failures and
-- duplicate messages must not create duplicate rows.
CREATE UNIQUE INDEX IF NOT EXISTS main_node_readings_idem
    ON main_node_readings (main_node_id, recorded_at);

-- Recent-heartbeats lookup for the ops dashboard.
CREATE INDEX IF NOT EXISTS main_node_readings_recent
    ON main_node_readings (main_node_id, recorded_at DESC);

-- Sub-Node-down triage query: filter offline heartbeats.
CREATE INDEX IF NOT EXISTS main_node_readings_offline
    ON main_node_readings (main_node_id, recorded_at DESC)
    WHERE sub_node_online = FALSE;
"""


DOWNGRADE_SQL = r"""
DROP INDEX IF EXISTS main_node_readings_offline;
DROP INDEX IF EXISTS main_node_readings_recent;
DROP INDEX IF EXISTS main_node_readings_idem;
DROP TABLE IF EXISTS main_node_readings;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
