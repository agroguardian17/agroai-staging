"""0039 D11 U-value register: full metadata + factors 13-15 (D11 spec §3.3/§6.2).

D11 yield-model build, PR 2 of N. Completes the 15-factor U-value register that
0031 scaffolded with 12 factors. Additive and non-breaking: ``factor_key`` stays
the primary key (existing reads via YieldModelRepo.list_u_values keep working);
new spec columns are added and back-filled, and factors 13-15 are inserted.

New columns (D11_YIELD_MODEL_v1 §6.2): factor_id (1..15, UNIQUE),
intensity_definition (the computable I_i expression), recoverable (yes/no/
partial), interdependence_group, confidence, calibration_status, signal_rules.

Interdependence groups (§3.3) OVERLAP — factor 2 (waterlogging) belongs to both
the soft-rot cluster {1,2,11} and the drip-drainage cluster {14,2}. A single TEXT
column (as the spec's §6.2 sketch shows) cannot express that, so
``interdependence_group`` is ``TEXT[]`` here; the "apply the group's max, not the
sum" logic (built in a later PR) groups by each membership. Groups:
  soft_rot_cluster      = {1 soft_rot, 2 waterlogging, 11 micronutrient}
  n_k_antagonism        = {4 k_deficiency, 8 excess_n_late}
  drip_drainage_cluster = {2 waterlogging, 14 wrong_drip_design}

All factors stay source_tier L4 / calibration_status EST_phase_1; confidence is a
uniform 0.50 Phase-1 placeholder (the spec gives no per-factor confidence, only
"SRC-EST L4"), replaced by empirical values after Season 1.

Reversible (drops the added columns + the 3 new factors).

Revision ID: 0039
Revises: 0038
Create Date: 2026-09-23
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = r"""
ALTER TABLE yield_u_values
    ADD COLUMN IF NOT EXISTS factor_id            SMALLINT,
    ADD COLUMN IF NOT EXISTS intensity_definition TEXT,
    ADD COLUMN IF NOT EXISTS recoverable          TEXT,
    ADD COLUMN IF NOT EXISTS interdependence_group TEXT[],
    ADD COLUMN IF NOT EXISTS confidence           NUMERIC(3,2),
    ADD COLUMN IF NOT EXISTS calibration_status   TEXT,
    ADD COLUMN IF NOT EXISTS signal_rules         TEXT[];

-- Back-fill the 12 existing factors (factor_id 1..12) with §3.3 metadata.
UPDATE yield_u_values SET factor_id=1,  intensity_definition='fraction of plot with confirmed rot symptoms',            recoverable='no',      interdependence_group='{soft_rot_cluster}',                       signal_rules='{D06-ROT-001}'  WHERE factor_key='soft_rot';
UPDATE yield_u_values SET factor_id=2,  intensity_definition='(waterlog_events * avg_duration) / 96h, normalised',      recoverable='partial', interdependence_group='{soft_rot_cluster,drip_drainage_cluster}',  signal_rules='{D03-DR-001}'   WHERE factor_key='waterlogging';
UPDATE yield_u_values SET factor_id=3,  intensity_definition='fraction of plot with confirmed wilt',                    recoverable='no',      interdependence_group=NULL,                                       signal_rules='{D06-WILT-001}' WHERE factor_key='bacterial_wilt';
UPDATE yield_u_values SET factor_id=4,  intensity_definition='(budget_gap / budget_target) capped at 1.0',             recoverable='partial', interdependence_group='{n_k_antagonism}',                         signal_rules='{D04-K-001}'    WHERE factor_key='k_deficiency';
UPDATE yield_u_values SET factor_id=5,  intensity_definition='scouting_damage_pct / 100',                              recoverable='no',      interdependence_group=NULL,                                       signal_rules='{D05-RF-001}'   WHERE factor_key='rhizome_fly';
UPDATE yield_u_values SET factor_id=6,  intensity_definition='1 - (emergence_pct / 90)',                               recoverable='no',      interdependence_group=NULL,                                       signal_rules='{D01-EM-001}'   WHERE factor_key='seed_vigour';
UPDATE yield_u_values SET factor_id=7,  intensity_definition='stress_days / 30',                                       recoverable='partial', interdependence_group=NULL,                                       signal_rules='{D03-ST-001}'   WHERE factor_key='drought_fill';
UPDATE yield_u_values SET factor_id=8,  intensity_definition='max(0, actual_N_after_120DAP / 30)',                     recoverable='no',      interdependence_group='{n_k_antagonism}',                         signal_rules='{D04-N-001}'    WHERE factor_key='excess_n_late';
UPDATE yield_u_values SET factor_id=9,  intensity_definition='heat_day_count / 15',                                    recoverable='no',      interdependence_group=NULL,                                       signal_rules='{D07-HT-001}'   WHERE factor_key='heat_stress';
UPDATE yield_u_values SET factor_id=10, intensity_definition='1 - weeding_compliance_pct',                             recoverable='partial', interdependence_group=NULL,                                       signal_rules='{D08-WD-001}'   WHERE factor_key='weed_pressure';
UPDATE yield_u_values SET factor_id=11, intensity_definition='deficiency_severity (0 / 0.5 / 1)',                      recoverable='yes',     interdependence_group='{soft_rot_cluster}',                       signal_rules='{D04-MN-001}'   WHERE factor_key='micronutrient';
UPDATE yield_u_values SET factor_id=12, intensity_definition='1 if confirmed else 0.3 if suspected',                   recoverable='no',      interdependence_group=NULL,                                       signal_rules='{D06-NEM-001}'  WHERE factor_key='nematode';

UPDATE yield_u_values SET confidence=0.50, calibration_status='EST_phase_1' WHERE confidence IS NULL;

-- Factors 13-15 (new in §3.3).
INSERT INTO yield_u_values
    (factor_key, rank, factor_label, u_value, signal_field, signal_domain, representative_rule_id,
     source_tier, source_ref, factor_id, intensity_definition, recoverable, interdependence_group,
     confidence, calibration_status, signal_rules)
VALUES
    ('late_planting',     13, 'Late planting (> 15 June)',            0.20, 'planting_date',            'D01', 'D01-PW-001', 'L4',
     'D11_YIELD_MODEL_v1 §3.3 EST', 13, 'days_late / 30 capped at 1.0',                        'no', NULL,                     0.50, 'EST_phase_1', '{D01-PW-001}'),
    ('wrong_drip_design', 14, 'Wrong drip design (heavy soil + close dripper)', 0.15, 'drip_lateral_spacing_ft', 'D03', 'D03-DS-001', 'L4',
     'D11_YIELD_MODEL_v1 §3.3 EST', 14, '1 if heavy-soil/close-dripper mismatch else 0',       'no', '{drip_drainage_cluster}', 0.50, 'EST_phase_1', '{D03-DS-001}'),
    ('herbicide_damage',  15, 'Herbicide damage after emergence',     0.40, 'herbicide_post_emergent_date', 'D08', 'D08-WD-001', 'L4',
     'D11_YIELD_MODEL_v1 §3.3 EST', 15, '1 if herbicide applied post-emergence else 0',        'no', NULL,                     0.50, 'EST_phase_1', '{D08-WD-001}')
ON CONFLICT (factor_key) DO NOTHING;

ALTER TABLE yield_u_values
    ADD CONSTRAINT yield_u_values_factor_id_key UNIQUE (factor_id);
ALTER TABLE yield_u_values
    ADD CONSTRAINT yield_u_values_recoverable_check
    CHECK (recoverable IS NULL OR recoverable IN ('yes', 'no', 'partial'));
"""

DOWNGRADE_SQL = r"""
DELETE FROM yield_u_values WHERE factor_key IN ('late_planting', 'wrong_drip_design', 'herbicide_damage');
ALTER TABLE yield_u_values DROP CONSTRAINT IF EXISTS yield_u_values_recoverable_check;
ALTER TABLE yield_u_values DROP CONSTRAINT IF EXISTS yield_u_values_factor_id_key;
ALTER TABLE yield_u_values
    DROP COLUMN IF EXISTS factor_id,
    DROP COLUMN IF EXISTS intensity_definition,
    DROP COLUMN IF EXISTS recoverable,
    DROP COLUMN IF EXISTS interdependence_group,
    DROP COLUMN IF EXISTS confidence,
    DROP COLUMN IF EXISTS calibration_status,
    DROP COLUMN IF EXISTS signal_rules;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
