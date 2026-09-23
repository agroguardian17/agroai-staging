"""0041 D12 advisory-QA workflow tables (D12_QA_WORKFLOW §3).

D12 build, PR 1 of N. Adds the QA-review subsystem's tables so the 8 QA
farm-brain fields (true/false-alarm counts, non-compliance reason, bias, photo
counts, cluster_id) can start being populated. Additive; no existing table is
touched.

Schema reconciliation vs the spec (its FKs assume `advisory_log(id BIGINT)`,
`plots(id UUID)`, `farmers(id)`, a `farmer_photos` table):
- the QA-reviewed advisory is the delivered farmer advisory, `ai_suggestions`
  (PK `suggestion_id UUID`, carries `farmer_id`), NOT the KB-engine `advisory_log`
  (composite PK, no id/farmer_id) - so every `advisory_id` retargets to
  `ai_suggestions(suggestion_id)` as UUID.
- `plots` keys on `plot_id TEXT`; `farmers` on `farmer_id UUID`.
- `farmer_photos` does not exist, so a minimal ingestion table is created here
  (the photo-intake pipeline - WhatsApp media / app upload - is separate).

Tables: farmer_photos, advisory_classification, non_compliance_reason,
bias_observation, photo_label, cluster_config (+ seed). Reversible.

Revision ID: 0041
Revises: 0040
Create Date: 2026-09-23
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
CREATE TABLE IF NOT EXISTS farmer_photos (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plot_id       TEXT REFERENCES plots(plot_id),
    farmer_id     UUID NOT NULL REFERENCES farmers(farmer_id),
    submitted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    storage_ref   TEXT,                       -- object-store key / URL (intake is a separate pipeline)
    gps_lat       NUMERIC(9,6),
    gps_lng       NUMERIC(9,6),
    source        TEXT,                        -- 'whatsapp' | 'farmer_app' | ...
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS farmer_photos_farmer_idx ON farmer_photos (farmer_id, submitted_at DESC);

CREATE TABLE IF NOT EXISTS advisory_classification (
    id                   BIGSERIAL PRIMARY KEY,
    advisory_id          UUID NOT NULL REFERENCES ai_suggestions(suggestion_id),
    plot_id              TEXT NOT NULL REFERENCES plots(plot_id),
    farmer_id            UUID NOT NULL REFERENCES farmers(farmer_id),
    rule_id              TEXT NOT NULL,
    fired_at             TIMESTAMPTZ NOT NULL,
    review_week          DATE NOT NULL,
    classification       TEXT NOT NULL CHECK (classification IN (
                           'confirmed_true_positive', 'false_positive', 'unresolved')),
    evidence_source      TEXT CHECK (evidence_source IN (
                           'farmer_report', 'agronomist_visit', 'photo', 'sensor', 'no_evidence')),
    classification_note  TEXT,
    reviewer             TEXT NOT NULL,
    reviewed_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (advisory_id, review_week)
);
CREATE INDEX IF NOT EXISTS advisory_classification_rule_class_idx
    ON advisory_classification (rule_id, classification);
CREATE INDEX IF NOT EXISTS advisory_classification_week_idx
    ON advisory_classification (review_week);

CREATE TABLE IF NOT EXISTS non_compliance_reason (
    id               BIGSERIAL PRIMARY KEY,
    advisory_id      UUID NOT NULL REFERENCES ai_suggestions(suggestion_id),
    plot_id          TEXT NOT NULL REFERENCES plots(plot_id),
    farmer_id        UUID NOT NULL REFERENCES farmers(farmer_id),
    action_state     TEXT NOT NULL CHECK (action_state IN ('not_acted', 'partially_acted')),
    reason           TEXT NOT NULL CHECK (reason IN (
                       'already_done', 'cost_barrier', 'unavailable_input',
                       'disagreed', 'forgot', 'other')),
    reason_detail_mr TEXT,
    captured_via     TEXT NOT NULL CHECK (captured_via IN (
                       'whatsapp_reply', 'agronomist_call', 'farmer_app', 'field_visit')),
    captured_by      TEXT NOT NULL,
    captured_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (advisory_id)
);
CREATE INDEX IF NOT EXISTS non_compliance_reason_reason_idx ON non_compliance_reason (reason);
CREATE INDEX IF NOT EXISTS non_compliance_reason_farmer_idx ON non_compliance_reason (farmer_id);

CREATE TABLE IF NOT EXISTS bias_observation (
    id                  BIGSERIAL PRIMARY KEY,
    observed_week       DATE NOT NULL,
    bias_type           TEXT NOT NULL CHECK (bias_type IN (
                          'over_issuing', 'under_issuing', 'wrong_timing', 'wrong_target_group',
                          'wrong_wording', 'confidence_miscalibrated', 'other')),
    scope_domain        TEXT,
    scope_rule_id       TEXT,
    scope_plot_ids      TEXT[],
    observation_mr      TEXT NOT NULL,
    suggested_change_mr TEXT,
    observed_by         TEXT NOT NULL,
    observed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    kb_author_read      BOOLEAN NOT NULL DEFAULT false,
    kb_author_action    TEXT
);
CREATE INDEX IF NOT EXISTS bias_observation_week_idx ON bias_observation (observed_week);
CREATE INDEX IF NOT EXISTS bias_observation_rule_idx
    ON bias_observation (scope_rule_id) WHERE scope_rule_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS bias_observation_unread_idx
    ON bias_observation (kb_author_read) WHERE kb_author_read = false;

CREATE TABLE IF NOT EXISTS photo_label (
    id                 BIGSERIAL PRIMARY KEY,
    photo_id           UUID NOT NULL REFERENCES farmer_photos(id),
    plot_id            TEXT NOT NULL REFERENCES plots(plot_id),
    farmer_id          UUID NOT NULL REFERENCES farmers(farmer_id),
    submitted_at       TIMESTAMPTZ NOT NULL,
    label              TEXT NOT NULL CHECK (label IN (
                         'soft_rot', 'bacterial_wilt', 'rhizome_fly', 'thrips', 'mite', 'leaf_spot',
                         'heat_scorch', 'zn_deficiency', 'fe_deficiency', 'k_deficiency',
                         'n_deficiency', 'waterlogging_damage', 'herbicide_damage', 'healthy',
                         'other', 'cannot_tell_from_photo')),
    label_confidence   NUMERIC(3,2) CHECK (label_confidence BETWEEN 0 AND 1),
    label_note_mr      TEXT,
    labelled_by        TEXT NOT NULL,
    labelled_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    routed_to_advisory UUID REFERENCES ai_suggestions(suggestion_id),
    UNIQUE (photo_id)
);
CREATE INDEX IF NOT EXISTS photo_label_label_idx ON photo_label (label);
CREATE INDEX IF NOT EXISTS photo_label_labelled_idx ON photo_label (labelled_at);

CREATE TABLE IF NOT EXISTS cluster_config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO cluster_config (key, value) VALUES
    ('min_plots_per_cluster', '8'),
    ('max_plots_per_cluster', '12'),
    ('proximity_km', '3'),
    ('planting_week_bucket_days', '7'),
    ('variety_gate', 'strict')
ON CONFLICT (key) DO NOTHING;
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS photo_label;
DROP TABLE IF EXISTS bias_observation;
DROP TABLE IF EXISTS non_compliance_reason;
DROP TABLE IF EXISTS advisory_classification;
DROP TABLE IF EXISTS cluster_config;
DROP TABLE IF EXISTS farmer_photos;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
