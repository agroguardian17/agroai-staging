"""0045 immutable advisory-audit log (LEGAL_COMPLIANCE_CERTIFICATE §7.3, A4.2).

The append-only record of the immutable facts of each advisory's *generation* —
rule id + version, model version, confidence, and the validation-gate results
(blocklist / PHI) — keyed to the ``ai_suggestions`` row. Delivery facts
(timestamp, channel, retries) remain on ``ai_suggestions`` (the mutable delivery
state machine, migration 0016); a join on ``suggestion_id`` gives the full §7.3
picture without making the audit row mutable.

Immutability (§65B): a BEFORE UPDATE/DELETE trigger raises, which holds even for
the table owner (a plain REVOKE does not bind the owner), plus a defensive
REVOKE. Rows are insert-only.

Revision ID: 0045
Revises: 0044
Create Date: 2026-09-24
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0045"
down_revision: str | None = "0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
CREATE TABLE IF NOT EXISTS advisory_audit (
    audit_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suggestion_id  UUID NOT NULL REFERENCES ai_suggestions(suggestion_id),
    rule_id        TEXT,
    rule_version   TEXT,
    model_version  TEXT,
    confidence     NUMERIC(3,2),
    gate_results   JSONB,        -- {blocklist_hit, phi_days_remaining, ...}
    inputs         JSONB,        -- compact generation context (dap, stage, as_of)
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS advisory_audit_suggestion_idx ON advisory_audit (suggestion_id);
CREATE INDEX IF NOT EXISTS advisory_audit_rule_idx
    ON advisory_audit (rule_id) WHERE rule_id IS NOT NULL;

CREATE OR REPLACE FUNCTION advisory_audit_no_mutate() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'advisory_audit is append-only; % is not permitted', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS advisory_audit_immutable ON advisory_audit;
CREATE TRIGGER advisory_audit_immutable
    BEFORE UPDATE OR DELETE ON advisory_audit
    FOR EACH ROW EXECUTE FUNCTION advisory_audit_no_mutate();
"""

DOWNGRADE_SQL = """
DROP TRIGGER IF EXISTS advisory_audit_immutable ON advisory_audit;
DROP FUNCTION IF EXISTS advisory_audit_no_mutate();
DROP TABLE IF EXISTS advisory_audit;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
