"""0046 DPDP consent capture + versioning + age gate (A3.1, A3.3).

Turns ``farmer_consent`` from a read-only row into a captured, versioned,
evidenced consent (LEGAL_COMPLIANCE_CERTIFICATE §3.1, D12-DPDP-001):

- ``farmer_consent`` gains the evidence columns: which notice version the farmer
  saw (``consent_version`` + ``consent_notice_hash``), when it was shown
  (``notice_shown_at``), the ``consent_channel``, and the age/parental-consent
  fields (§3.1 requires verifiable parental consent under 18, DPDP §9).
- ``farmers`` gains ``date_of_birth`` (age was only self-reported as
  ``age_years``); the age gate uses it when present.
- ``consent_event`` — an append-only history (given / withdrawn / updated per
  scope), because the single 1:1 consent row cannot evidence consent-over-time
  for §12. Immutability via a BEFORE UPDATE/DELETE trigger.

Additive; existing rows keep NULLs.

Revision ID: 0046
Revises: 0045
Create Date: 2026-09-24
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0046"
down_revision: str | None = "0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
ALTER TABLE farmer_consent ADD COLUMN IF NOT EXISTS consent_version TEXT;
ALTER TABLE farmer_consent ADD COLUMN IF NOT EXISTS consent_notice_hash TEXT;
ALTER TABLE farmer_consent ADD COLUMN IF NOT EXISTS notice_shown_at TIMESTAMPTZ;
ALTER TABLE farmer_consent ADD COLUMN IF NOT EXISTS consent_channel TEXT;
ALTER TABLE farmer_consent ADD COLUMN IF NOT EXISTS parental_consent_by TEXT;
ALTER TABLE farmer_consent ADD COLUMN IF NOT EXISTS parental_consent_verified BOOLEAN;

ALTER TABLE farmers ADD COLUMN IF NOT EXISTS date_of_birth DATE;

CREATE TABLE IF NOT EXISTS consent_event (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_id       UUID NOT NULL REFERENCES farmers(farmer_id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL CHECK (event_type IN ('given', 'withdrawn', 'updated')),
    scope           TEXT NOT NULL CHECK (scope IN ('advisory', 'research', 'third_party')),
    consent_version TEXT,
    channel         TEXT,
    actor           TEXT,
    at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS consent_event_farmer_idx ON consent_event (farmer_id, at DESC);

CREATE OR REPLACE FUNCTION consent_event_no_mutate() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'consent_event is append-only; % is not permitted', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS consent_event_immutable ON consent_event;
CREATE TRIGGER consent_event_immutable
    BEFORE UPDATE OR DELETE ON consent_event
    FOR EACH ROW EXECUTE FUNCTION consent_event_no_mutate();
"""

DOWNGRADE_SQL = """
DROP TRIGGER IF EXISTS consent_event_immutable ON consent_event;
DROP FUNCTION IF EXISTS consent_event_no_mutate();
DROP TABLE IF EXISTS consent_event;

ALTER TABLE farmers DROP COLUMN IF EXISTS date_of_birth;

ALTER TABLE farmer_consent DROP COLUMN IF EXISTS parental_consent_verified;
ALTER TABLE farmer_consent DROP COLUMN IF EXISTS parental_consent_by;
ALTER TABLE farmer_consent DROP COLUMN IF EXISTS consent_channel;
ALTER TABLE farmer_consent DROP COLUMN IF EXISTS notice_shown_at;
ALTER TABLE farmer_consent DROP COLUMN IF EXISTS consent_notice_hash;
ALTER TABLE farmer_consent DROP COLUMN IF EXISTS consent_version;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
