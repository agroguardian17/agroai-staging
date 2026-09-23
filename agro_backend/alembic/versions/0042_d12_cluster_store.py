"""0042 D12 peer-cluster store (D12_QA_WORKFLOW §4.6, §5.3).

D12 build, PR 3. Backs the ``assign_cluster`` use-case: ``clusters`` holds one
row per peer cluster with the aggregate the gating algorithm reads
(variety, planting-week median, centroid, member count, baseline-active flag);
``plot_cluster`` maps each plot to its cluster and records the fit outcome.

The cluster aggregate is recomputed from ``plot_cluster`` members on every
assignment (see :mod:`app.infra.persistence.pg_cluster_repo`), so the two tables
never drift. ``baseline_active`` flips true at ``min_plots_per_cluster`` (8),
the point where a peer NDVI/NDRE baseline becomes meaningful for the D14
satellite rules. An emptied cluster is deleted by the repo.

Schema reconciliation: ``plots`` keys on ``plot_id TEXT``; the cluster id is a
minted TEXT key (``CL-<short>``), not a UUID, so it reads cleanly in the farm
brain's ``cluster_id`` field and in agronomist digests.

Additive; no existing table is touched. Reversible.

Revision ID: 0042
Revises: 0041
Create Date: 2026-09-23
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
CREATE TABLE IF NOT EXISTS clusters (
    cluster_id            TEXT PRIMARY KEY,
    tenant_id             UUID NOT NULL,
    variety               TEXT NOT NULL,
    planting_week_median  DATE NOT NULL,
    centroid_lat          NUMERIC(9,6) NOT NULL,
    centroid_lng          NUMERIC(9,6) NOT NULL,
    plot_count            INTEGER NOT NULL DEFAULT 0,
    baseline_active       BOOLEAN NOT NULL DEFAULT false,  -- peer baseline live at >= min_plots
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS clusters_tenant_variety_idx
    ON clusters (tenant_id, variety, planting_week_median);

CREATE TABLE IF NOT EXISTS plot_cluster (
    plot_id            TEXT PRIMARY KEY REFERENCES plots(plot_id),
    cluster_id         TEXT NOT NULL REFERENCES clusters(cluster_id),
    tenant_id          UUID NOT NULL,
    variety            TEXT NOT NULL,
    planting_week      DATE NOT NULL,
    centroid_lat       NUMERIC(9,6) NOT NULL,
    centroid_lng       NUMERIC(9,6) NOT NULL,
    distance_km        NUMERIC(7,3),                 -- to the cluster centroid at assignment; NULL on spawn
    fit_score          NUMERIC(4,3) NOT NULL,        -- [0,1]; < 0.6 -> informational_only for D14
    informational_only BOOLEAN NOT NULL DEFAULT false,
    assigned_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS plot_cluster_cluster_idx ON plot_cluster (cluster_id);
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS plot_cluster;
DROP TABLE IF EXISTS clusters;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
