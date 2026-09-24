"""0049 VNMKV B1.7 — Kannad (Western Scarcity) D11 site-index baseline.

VNMKV compliance certificate §4.2: the site-index (SI) multiplier for Kannad
plots is certified at 0.75–0.85 in the D11 yield model (Western Marathwada
Scarcity zone). Kannad plots (district Chhatrapati Sambhajinagar) resolve the
``climate`` dimension key ``within_kannad_zone`` (app/domain/yield_forecast.py),
seeded at 1.00 in migration 0038. This lowers that climate baseline to 0.80
(the midpoint of the certified band); the final SI stays a product of the
soil/water/climate dimensions.

Interpretation note: the cert's "SI multiplier 0.75–0.85" is applied here as the
zone's *climate-dimension* baseline (the axis that encodes agro-climatic zone),
not a clamp on the overall SI product. 0.80 satisfies the 0.3–1.0 CHECK.

Additive/idempotent UPDATE; reversible.

Revision ID: 0049
Revises: 0048
Create Date: 2026-09-24
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0049"
down_revision: str | None = "0048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE site_index_config SET value = 0.80, updated_at = now() "
        "WHERE dimension = 'climate' AND key = 'within_kannad_zone'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE site_index_config SET value = 1.00, updated_at = now() "
        "WHERE dimension = 'climate' AND key = 'within_kannad_zone'"
    )
