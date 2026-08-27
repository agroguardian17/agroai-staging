"""0012 device_calibration — per-device calibration constants for raw-payload
firmware.

Firmware (`viraai-sn-1.0.0-raw` + `viraai-mn-1.0.0-raw`) emits payloads with
`$schema=agro-guardian/telemetry/v2-raw`. Values arrive as raw ADC counts,
pulse counts, or Modbus register integers. Server-side calibration converts
them to engineering units (VWC%, volts, bar, L/min, °C, pH, µS/cm) before
the domain `Reading` object is constructed.

This migration:

1. Creates `device_calibration` — one row per Sub Node, PK
   `(tenant_id, device_id)`. Every column is nullable-with-default so the
   Round 16 code path can operate on partial rows during field calibration.
2. Adds a BEFORE INSERT/UPDATE trigger that stamps `updated_at`.
3. Seeds default calibration for **AGR-SN-0001** using the constants the
   VIRAAI hardware team's firmware previously baked in — pilot works
   out-of-the-box with no manual entry, and the field team overrides
   individual values later via SQL.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-26
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS device_calibration (
    tenant_id                UUID        NOT NULL REFERENCES tenants(id),
    device_id                TEXT        NOT NULL REFERENCES device_registry(device_id) ON DELETE CASCADE,

    -- Soil moisture (capacitive probe)
    -- VWC% = (WET_ADC - raw) / (WET_ADC - DRY_ADC) * 100, clamped [0, 100]
    soil_dry_adc             INTEGER     NOT NULL DEFAULT 750,
    soil_wet_adc             INTEGER     NOT NULL DEFAULT 350,

    -- Battery (divider on A1, 220k + 100k)
    -- volts = raw * VREF/1023 * divider_ratio
    battery_vref_v           NUMERIC(6, 3) NOT NULL DEFAULT 3.300,
    battery_divider_ratio    NUMERIC(6, 3) NOT NULL DEFAULT 3.200,

    -- Pressure transducer (0.5-4.5 V for 0-10 bar typical)
    -- bar = ((raw * VREF/1023) - offset) * scale, clamped >= 0
    pressure_offset_v        NUMERIC(6, 3) NOT NULL DEFAULT 0.500,
    pressure_scale_bar_per_v NUMERIC(6, 3) NOT NULL DEFAULT 2.500,

    -- Flow sensor (hall-effect pulse)
    -- L/min = pulses * 60 / (window_seconds * pulses_per_L)
    flow_pulses_per_litre    NUMERIC(8, 3) NOT NULL DEFAULT 450.000,
    flow_window_seconds      NUMERIC(6, 2) NOT NULL DEFAULT 16.00,

    -- NPK Modbus register scaling (raw / divisor -> engineering unit)
    npk_temp_divisor         NUMERIC(6, 3) NOT NULL DEFAULT 10.000,
    npk_moisture_divisor     NUMERIC(6, 3) NOT NULL DEFAULT 10.000,
    npk_ph_divisor           NUMERIC(6, 3) NOT NULL DEFAULT 100.000,

    -- Audit
    calibration_version      INTEGER     NOT NULL DEFAULT 1,
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by               TEXT,
    notes                    TEXT,

    PRIMARY KEY (tenant_id, device_id)
);

CREATE OR REPLACE FUNCTION device_calibration_bump_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    IF TG_OP = 'UPDATE' THEN
        NEW.calibration_version := OLD.calibration_version + 1;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS device_calibration_bump_updated_at_trg ON device_calibration;
CREATE TRIGGER device_calibration_bump_updated_at_trg
    BEFORE INSERT OR UPDATE ON device_calibration
    FOR EACH ROW
    EXECUTE FUNCTION device_calibration_bump_updated_at();

-- Seed AGR-SN-0001 with the firmware team's tested defaults so the pilot's
-- one hardware Sub Node works end-to-end the moment the migration runs.
-- ON CONFLICT DO NOTHING keeps re-runs idempotent.
INSERT INTO device_calibration (
    tenant_id, device_id,
    soil_dry_adc, soil_wet_adc,
    battery_vref_v, battery_divider_ratio,
    pressure_offset_v, pressure_scale_bar_per_v,
    flow_pulses_per_litre, flow_window_seconds,
    npk_temp_divisor, npk_moisture_divisor, npk_ph_divisor,
    updated_by, notes
)
SELECT
    d.tenant_id, d.device_id,
    750, 350,
    3.300, 3.200,
    0.500, 2.500,
    450.000, 16.00,
    10.000, 10.000, 100.000,
    'migration-0012',
    'Firmware-baked defaults from viraai-sn-1.0.0-raw. Field team must ' ||
    'measure DRY_ADC + WET_ADC on the actual probe during commissioning.'
FROM device_registry d
WHERE d.device_id = 'AGR-SN-0001'
ON CONFLICT (tenant_id, device_id) DO NOTHING;
"""


DOWNGRADE_SQL = r"""
DROP TRIGGER IF EXISTS device_calibration_bump_updated_at_trg ON device_calibration;
DROP FUNCTION IF EXISTS device_calibration_bump_updated_at();
DROP TABLE IF EXISTS device_calibration;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
