"""0053 registered_herbicide_registry — positive-list herbicide gate data (VIRAAI deliverables 25 Sep 2026).

Positive-list registry backing rule D08-WD-001 (registered-herbicide gate,
Track A5.1). The gate's default is BLOCK; a product PERMITs only per its
``compliance_tier`` (recommended practice, or off-label after agronomist
verification). Season 1 Kannad default = hand-weeding + mulching.

Seeded from ``VIRAAI_Agronomy_Deliverables_25Sep2026/02_HERBICIDE_GATE/
registered_herbicide_registry_ginger_v1.0.csv`` (13 entries). ``NA`` sentinels
in the CSV are stored as NULL; dose/PHI kept numeric (NULL where not applicable).
Long free-text citations/notes are condensed to ASCII provenance summaries; the
authoritative wording lives in the CSV.

Compliance tiers: L1_recommended_practice (permit), L1_crop_damage_block /
L1_nonselective_block / L1_not_for_ginger_block (hard block),
L3_off_label_icar_recommended / L4_off_label_needs_verification (block until
agronomist CIB&RC verification).

Additive; reversible (drops the table).

Revision ID: 0053
Revises: 0052
Create Date: 2026-09-25
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0053"
down_revision: str | None = "0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
CREATE TABLE IF NOT EXISTS registered_herbicide_registry (
    product_name                 TEXT NOT NULL,
    active_ingredient            TEXT,
    formulation                  TEXT,
    cib_rc_registered_for_ginger TEXT,     -- unverified | no | NULL(NA)
    icar_iisr_recommended        TEXT,     -- yes | no | not_recommended | not_recommended_specifically
    selective_or_nonselective    TEXT,
    ginger_specific_label        TEXT,
    label_timing_stage           TEXT,
    label_timing_dap_window      TEXT,     -- e.g. 0_to_3, -30_to_-7 (NULL where NA)
    dose_per_acre_low            NUMERIC(8,2),
    dose_per_acre_high           NUMERIC(8,2),
    dose_unit                    TEXT,
    phi_days                     INTEGER,
    source_citation              TEXT,
    compliance_tier              TEXT NOT NULL,
    notes                        TEXT,
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (product_name)
);

INSERT INTO registered_herbicide_registry (
    product_name, active_ingredient, formulation, cib_rc_registered_for_ginger,
    icar_iisr_recommended, selective_or_nonselective, ginger_specific_label,
    label_timing_stage, label_timing_dap_window,
    dose_per_acre_low, dose_per_acre_high, dose_unit, phi_days,
    source_citation, compliance_tier, notes
) VALUES
    ('Stomp', 'Pendimethalin 30 EC', 'EC', 'unverified', 'not_recommended_specifically',
        'selective_pre_emergent', 'no_ginger_specific_label', 'pre_emergent', '0_to_3',
        1.0, 1.3, 'L/acre', NULL,
        'CIB&RC ginger label check pending; commonly used off-label in India',
        'L4_off_label_needs_verification',
        'Registered for many crops; ginger-specific label needs CIB&RC verification. Season 1 default BLOCK.'),
    ('Goal', 'Oxyfluorfen 23.5 EC', 'EC', 'unverified', 'yes',
        'selective_pre_emergent', 'off_label_icar_recommended', 'pre_emergent', '1_to_3',
        180, 200, 'ml/acre', NULL,
        'ICAR-IISR recommends ~500 ml/ha (~200 ml/acre) at day 2 after sowing; warns may not be CIB&RC-approved for ginger',
        'L3_off_label_icar_recommended',
        'Off-label ICAR-recommended. BLOCK by default until label verified.'),
    ('Targa Super', 'Quizalofop ethyl 5 EC', 'EC', 'unverified', 'yes',
        'selective_post_emergent_grass', 'off_label_icar_recommended', 'post_emergent', '25_to_35',
        400, 400, 'ml/acre', NULL,
        'ICAR-IISR recommends ~1 L/ha (~400 ml/acre) at 30 DAP; warns not CIB&RC-verified for ginger',
        'L3_off_label_icar_recommended',
        'Off-label ICAR-recommended. BLOCK by default.'),
    ('Roundup', 'Glyphosate 41 SL', 'SL', 'no', 'not_recommended',
        'nonselective_systemic', 'no', 'pre_planting_only', '-30_to_-7',
        NULL, NULL, 'ml/acre', NULL,
        'Non-selective; will kill ginger. Registered for pre-plant knock-down in other crops.',
        'L1_nonselective_block',
        'ALWAYS BLOCK in-season. Only pre-plant fallow knockdown with explicit farmer consent + agronomist signoff.'),
    ('Gramoxone', 'Paraquat 24 SL', 'SL', 'no', 'not_recommended',
        'nonselective_contact', 'no', 'pre_planting_only', '-30_to_-7',
        NULL, NULL, 'ml/acre', NULL,
        'Non-selective + acutely toxic; several state bans (Kerala, Punjab); WHO Class II hazard.',
        'L1_nonselective_block',
        'ALWAYS BLOCK. Do not include in any recommendation even off-label.'),
    ('2,4-D', '2,4-D Amine Salt 58 SL', 'SL', 'no', 'not_recommended',
        'selective_broadleaf_but_ginger_sensitive', 'no', 'not_applicable', NULL,
        NULL, NULL, 'ml/acre', NULL,
        'Ginger is broadleaf-sensitive to 2,4-D; will damage crop.',
        'L1_crop_damage_block',
        'ALWAYS BLOCK. Farmer confusion with maize/sugarcane recommendations.'),
    ('Atrataf', 'Atrazine 50 WP', 'WP', 'no', 'not_recommended',
        'selective_pre_emergent_maize', 'no', 'not_applicable', NULL,
        NULL, NULL, 'g/acre', NULL,
        'Registered for maize and sugarcane only; not for ginger; groundwater risk on vertisol.',
        'L1_not_for_ginger_block',
        'ALWAYS BLOCK. Common farmer error to apply from maize kit.'),
    ('Sencor', 'Metribuzin 70 WP', 'WP', 'no', 'not_recommended',
        'selective_pre_and_post_emergent', 'no', 'not_applicable', NULL,
        NULL, NULL, 'g/acre', NULL,
        'Not registered for ginger; potato/soybean crop.',
        'L1_not_for_ginger_block',
        'ALWAYS BLOCK for ginger.'),
    ('Sunstar', 'Ethoxysulfuron 15 WDG', 'WDG', 'no', 'not_recommended',
        'selective_broadleaf', 'no', 'not_applicable', NULL,
        NULL, NULL, 'g/acre', NULL,
        'Rice-crop registered; not for ginger.',
        'L1_not_for_ginger_block',
        'ALWAYS BLOCK.'),
    ('Basagran', 'Bentazon 48 SL', 'SL', 'unverified', 'no',
        'selective_broadleaf', 'no', 'unknown', NULL,
        NULL, NULL, 'ml/acre', NULL,
        'Rice/soybean crop registration; ginger label absent.',
        'L4_off_label_needs_verification',
        'BLOCK by default until CIB&RC verification confirmed.'),
    ('Manual/Mechanical', NULL, NULL, NULL, 'yes',
        NULL, 'yes', 'pre_and_post_emergent', '0_to_150',
        NULL, NULL, NULL, NULL,
        'ICAR-IISR + AICRP-Spices + VNMKV standard: hand weeding + earthing + mulching; no chemical needed',
        'L1_recommended_practice',
        'DEFAULT Season 1 recommendation. 5-6 hand weedings; earthing at 45 and 90 DAP; mulching 15 t/ha at planting.'),
    ('Green Mulch Coir/Leaves', NULL, NULL, NULL, 'yes',
        NULL, 'yes', 'post_emergent_suppressor', '0_to_90',
        15, 15, 'tonnes/acre', NULL,
        'AICRP-Spices PoP: 15 t/ha green mulch at planting suppresses weed emergence for 60-90 days',
        'L1_recommended_practice',
        'Non-chemical alternative; strongly recommended for Kannad (also conserves soil moisture).'),
    ('Green Manure Intercrop', 'Daincha/Sunhemp', 'live_crop', NULL, 'yes',
        NULL, 'yes', 'inter_row_alleys', '0_to_45',
        NULL, NULL, NULL, NULL,
        'AICRP-Spices: green manure in interspaces suppresses weeds + adds N via legume fixation',
        'L1_recommended_practice',
        'Non-chemical alternative; sow in bed alleys, incorporate at 45 DAP.')
ON CONFLICT (product_name) DO NOTHING;
"""

DOWNGRADE_SQL = "DROP TABLE IF EXISTS registered_herbicide_registry;"


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
