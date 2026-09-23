"""0038 D11 yield-model config tables: variety_potential, site_index_config, yield_actual.

Phase 1 D11 (item, PR 1 of the yield-model build). Adds the three additive
reference/truth tables the D11 spec (D11_YIELD_MODEL_v1 §6) needs, with their
seeds. These are new tables — they do not touch the existing yield_u_values /
yield_prediction_log from 0031 (those are reshaped in a later PR).

Schema reconciliation vs the spec: the spec's FKs use ``plots(id)`` /
``crop_seasons(id)``, but this DB keys plots by ``plot_id TEXT`` and crop_seasons
by ``season_id UUID`` — so ``yield_actual`` FKs are retargeted accordingly.

- variety_potential — Y_var ceiling per variety (§3.1, 5 seed rows).
- site_index_config — the SI heuristic multipliers, soil/water/climate (§3.2,
  16 seed rows). Read at every predict call until a Season-2 ML regressor
  replaces it.
- yield_actual — end-of-season truth capture (from D09-YD-002); no seed.

Seeds use ON CONFLICT DO NOTHING so the migration is idempotent. Reversible.

Revision ID: 0038
Revises: 0037
Create Date: 2026-09-23
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
CREATE TABLE IF NOT EXISTS variety_potential (
    variety             TEXT PRIMARY KEY,
    y_var_t_per_ha      NUMERIC(5,2) NOT NULL,
    y_var_q_per_acre    NUMERIC(5,1) NOT NULL,
    source_institution  TEXT NOT NULL,
    source_ref          TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS site_index_config (
    dimension  TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      NUMERIC(3,2) NOT NULL CHECK (value BETWEEN 0.3 AND 1.0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (dimension, key)
);

CREATE TABLE IF NOT EXISTS yield_actual (
    plot_id          TEXT NOT NULL REFERENCES plots(plot_id),
    season_id        UUID NOT NULL REFERENCES crop_seasons(season_id),
    fresh_q_per_acre NUMERIC(6,2),
    dry_q_per_acre   NUMERIC(6,2),
    dry_ratio        NUMERIC(4,3),
    harvest_date     DATE NOT NULL,
    reported_by      TEXT NOT NULL,
    verified         BOOLEAN NOT NULL DEFAULT false,
    verified_by      TEXT,
    captured_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (plot_id, season_id)
);

-- §3.1 variety potential (Y_var). q/acre fresh is the engine-facing figure.
INSERT INTO variety_potential
    (variety, y_var_t_per_ha, y_var_q_per_acre, source_institution, source_ref, verification_status)
VALUES
    ('IISR Mahima',     23.2, 94, 'ICAR-IISR', 'ICAR-IISR variety profile', 'CONFIRMED'),
    ('IISR Varada',     22.6, 91, 'ICAR-IISR', 'ICAR-IISR variety profile', 'CONFIRMED'),
    ('Nadia',           20.0, 81, 'VNMKV',     'VNMKV OFT indicative',       'PROVISIONAL'),
    ('Himachal',        18.0, 73, 'VNMKV',     'VNMKV OFT indicative',       'PROVISIONAL'),
    ('Rio-de-Janeiro',  24.5, 99, 'ICAR-IISR', 'ICAR-IISR variety profile', 'CONFIRMED')
ON CONFLICT (variety) DO NOTHING;

-- §3.2 site-index heuristic multipliers. SI = SI_soil * SI_water * SI_climate.
INSERT INTO site_index_config (dimension, key, value) VALUES
    ('soil', 'black_vertisol_with_drip_broad_ridge', 1.00),
    ('soil', 'black_vertisol_with_drip_flat',        0.85),
    ('soil', 'black_vertisol_flood_irrigated',       0.55),
    ('soil', 'red_loam_with_drip',                   0.90),
    ('soil', 'red_loam_without_drip',                0.70),
    ('soil', 'sandy_loam_with_drip',                 0.80),
    ('soil', 'laterite',                             0.50),
    ('soil', 'other',                                0.65),
    ('water', 'assured_source_year_round',           1.00),
    ('water', 'assured_source_seasonal_gap',         0.85),
    ('water', 'marginal_source',                     0.65),
    ('water', 'rain_dependent_only',                 0.40),
    ('climate', 'within_kannad_zone',                1.00),
    ('climate', 'marathwada_west',                   0.90),
    ('climate', 'marathwada_east',                   0.95),
    ('climate', 'outside_marathwada',                0.75)
ON CONFLICT (dimension, key) DO NOTHING;
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS yield_actual;
DROP TABLE IF EXISTS site_index_config;
DROP TABLE IF EXISTS variety_potential;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
