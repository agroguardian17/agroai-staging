"""0004 plots satellite-only support.

* ``plots.node_id`` becomes nullable (satellite-only plots have no sub-node).
* ``plots.data_tier`` added: ``'satellite_only' | 'sub_node'``.
* ``plots_set_data_tier`` BEFORE INSERT/UPDATE trigger keeps ``data_tier``
  consistent with ``node_id`` (NULL node => satellite_only, else sub_node).

The technical-ref ``§2.2.2 patch 2`` text was not available verbatim; this is
the faithful implementation of the roadmap's stated intent
("BEFORE trigger that keeps data_tier consistent with node_id"). See
docs/SCHEMA_DECISIONS.md.

Revision ID: 0004
Revises: 0003
Create Date: Phase 1
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
ALTER TABLE plots ALTER COLUMN node_id DROP NOT NULL;

ALTER TABLE plots
    ADD COLUMN data_tier TEXT NOT NULL DEFAULT 'satellite_only'
        CHECK (data_tier IN ('satellite_only','sub_node'));

CREATE OR REPLACE FUNCTION plots_set_data_tier() RETURNS TRIGGER AS $$
BEGIN
    -- A plot with no sub-node is satellite-only; otherwise it has node data.
    IF NEW.node_id IS NULL THEN
        NEW.data_tier := 'satellite_only';
    ELSE
        NEW.data_tier := 'sub_node';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER plots_set_data_tier_trg
    BEFORE INSERT OR UPDATE OF node_id ON plots
    FOR EACH ROW
    EXECUTE FUNCTION plots_set_data_tier();
"""


DOWNGRADE_SQL = r"""
DROP TRIGGER IF EXISTS plots_set_data_tier_trg ON plots;
DROP FUNCTION IF EXISTS plots_set_data_tier();
ALTER TABLE plots DROP COLUMN IF EXISTS data_tier;
ALTER TABLE plots ALTER COLUMN node_id SET NOT NULL;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
