"""0030 farmer_consent — DPDP consent / display governance (Phase 3, D12/D14).

1:1 per farmer (``farmer_id`` UNIQUE) upsert table holding the consent and
public-display governance flags the KB's D12 (privacy) and D14 (satellite
display) rules read. Columns named to match kb_farm_brain_fields. Reversible.

Revision ID: 0030
Revises: 0029
Create Date: 2026-09-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS farmer_consent (
    id                             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                      UUID        NOT NULL REFERENCES tenants(id),
    farmer_id                      UUID        NOT NULL UNIQUE REFERENCES farmers(farmer_id)
                                                 ON DELETE CASCADE,
    consent_advisory               BOOLEAN,
    consent_research               BOOLEAN,
    consent_date                   DATE,
    third_party_share_consent_given BOOLEAN,
    data_retention_until           DATE,
    deletion_requested             BOOLEAN,
    cluster_anonymised             BOOLEAN,
    sat_attribution_shown          BOOLEAN,
    sat_public_display_context     TEXT
        CHECK (sat_public_display_context IN ('own_plot', 'cluster_aggregate', 'third_party')),
    notes                          TEXT,
    updated_at                     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

DOWNGRADE_SQL = "DROP TABLE IF EXISTS farmer_consent;"


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
