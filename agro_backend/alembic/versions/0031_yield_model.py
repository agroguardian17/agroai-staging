"""0031 yield model (D11) - U-value register + prediction log.

Scaffold for the Domain 11 yield model (AGRONOMY_SIGNOFF / VJH-V1.0 §2, §9.7):
a process-baseline predictor ``Y = ceiling * prod(1 - u_i*I_i)`` seeded with
the 12-factor U-value register (all ``source_tier='L4'`` estimates for Phase 1,
replaced by empirical means after Season 1). ``yield_prediction_log`` captures
every prediction with provenance. The 11 D11 farm-brain fields fill from these.

Reversible, no backfill.

Revision ID: 0031
Revises: 0030
Create Date: 2026-09-21
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS yield_u_values (
    factor_key      TEXT        PRIMARY KEY,
    crop            TEXT        NOT NULL DEFAULT 'Ginger',
    rank            INTEGER     NOT NULL,
    factor_label    TEXT        NOT NULL,
    u_value         NUMERIC     NOT NULL CHECK (u_value >= 0 AND u_value <= 1),
    signal_field    TEXT,                              -- farm-brain field driving intensity, if any
    signal_domain   TEXT,                              -- KB domain the signal comes from
    representative_rule_id TEXT,                        -- for u_values_applied (array of rule_id)
    source_tier     TEXT        NOT NULL DEFAULT 'L4',
    source_ref      TEXT,
    active          BOOLEAN     NOT NULL DEFAULT TRUE,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO yield_u_values
    (factor_key, rank, factor_label, u_value, signal_field, signal_domain, representative_rule_id, source_ref)
VALUES
    ('soft_rot',        1, 'Soft rot (Pythium)',                 0.60, 'rot_incidence_pct',              'D06', 'D06-ROT-001', 'AGRONOMY_SIGNOFF 2026-09-21 EST'),
    ('waterlogging',    2, 'Drainage failure / waterlogging',    0.35, 'standing_water_hours_observed',  'D03', 'D03-DR-001',  'AGRONOMY_SIGNOFF 2026-09-21 EST'),
    ('bacterial_wilt',  3, 'Bacterial wilt (once present)',      0.50, 'wilt_incidence_pct',             'D06', 'D06-WILT-001','AGRONOMY_SIGNOFF 2026-09-21 EST'),
    ('k_deficiency',    4, 'K deficiency uncorrected',           0.20, NULL,                             'D04', 'D04-K-001',   'AGRONOMY_SIGNOFF 2026-09-21 EST'),
    ('rhizome_fly',     5, 'Rhizome fly damage',                 0.15, 'rhizome_fly_incidence_pct',      'D05', 'D05-RF-001',  'AGRONOMY_SIGNOFF 2026-09-21 EST'),
    ('seed_vigour',     6, 'Seed rhizome vigour poor',           0.15, 'establishment_pct',              'D01', 'D01-EM-001',  'AGRONOMY_SIGNOFF 2026-09-21 EST'),
    ('drought_fill',    7, 'Drought during rhizome fill (G3-G4)',0.20, 'dry_spell_days',                 'D03', 'D03-ST-001',  'AGRONOMY_SIGNOFF 2026-09-21 EST'),
    ('excess_n_late',   8, 'Excess N late (> 80 DAP)',           0.08, NULL,                             'D04', 'D04-N-001',   'AGRONOMY_SIGNOFF 2026-09-21 EST'),
    ('heat_stress',     9, 'Heat stress > 35C sustained',        0.10, 'heat_stress_days_count',         'D07', 'D07-HT-001',  'AGRONOMY_SIGNOFF 2026-09-21 EST'),
    ('weed_pressure',  10, 'Weed pressure uncontrolled',         0.10, NULL,                             'D08', 'D08-WD-001',  'AGRONOMY_SIGNOFF 2026-09-21 EST'),
    ('micronutrient',  11, 'Micronutrient (Zn/Fe) lock-out',     0.08, NULL,                             'D04', 'D04-MN-001',  'AGRONOMY_SIGNOFF 2026-09-21 EST'),
    ('nematode',       12, 'Nematode pressure',                  0.12, 'nematode_suspected',             'D06', 'D06-NEM-001', 'AGRONOMY_SIGNOFF 2026-09-21 EST')
ON CONFLICT (factor_key) DO NOTHING;

CREATE TABLE IF NOT EXISTS yield_prediction_log (
    id                              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                       UUID        NOT NULL REFERENCES tenants(id),
    season_id                       UUID        NOT NULL REFERENCES crop_seasons(season_id) ON DELETE CASCADE,
    plot_id                         TEXT        REFERENCES plots(plot_id),
    prediction_date                 DATE        NOT NULL,
    dap                             INTEGER,
    prediction_stage               TEXT,
    ceiling_quintal_per_acre        NUMERIC,
    ceiling_basis                   TEXT,
    predicted_yield_quintal_per_acre NUMERIC,
    ci_low_quintal_per_acre         NUMERIC,
    ci_high_quintal_per_acre        NUMERIC,
    prediction_interval_pct         NUMERIC,
    cumulative_loss_pct             NUMERIC,
    gap_attributed_pct              NUMERIC,
    gap_unexplained_pct             NUMERIC,
    u_values_applied                JSONB,       -- array of rule_id
    attribution                     JSONB,       -- [{factor_key, u_value, intensity, loss_pct}]
    u_value_source_class            TEXT,
    model_version                   TEXT        NOT NULL,
    data_quality                    NUMERIC,
    confidence                      NUMERIC,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS yield_prediction_log_season_idx
    ON yield_prediction_log (season_id, prediction_date DESC);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS yield_prediction_log;
DROP TABLE IF EXISTS yield_u_values;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
