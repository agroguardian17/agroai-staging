"""0034 reload KB for step-2 additions (rule D07-CY-WX-001 + 2 fields).

Step 2 is purely ADDITIVE to the knowledge base: one new rule
(D07-CY-WX-001) plus two new farm-brain fields (rainfall_24h_mm,
wind_gust_kmph). Re-executing the regenerated unified SQL is therefore
sufficient - its ``INSERT ... ON CONFLICT DO NOTHING`` no-ops every existing
row and inserts only the new rule, its rule_fields / golden_tests, and the two
new field declarations. No truncate / FK dance is needed (nothing is renamed or
removed, unlike 0032).

Forward-only (the KB is derived data); downgrade is a no-op.

Revision ID: 0034
Revises: 0033
Create Date: 2026-09-22
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SQL_PATH = (
    Path(__file__).resolve().parents[2] / "ginger" / "generated" / "agroguardian_ginger_kb.sql"
)


def upgrade() -> None:
    if not _SQL_PATH.exists():
        raise RuntimeError(f"Unified ginger KB SQL not found at {_SQL_PATH}.")
    sql = _SQL_PATH.read_text(encoding="utf-8")
    # Strip the file's own transaction wrapper so it runs in the migration tx.
    sql = re.sub(r"(?m)^\s*BEGIN;\s*$", "", sql, count=1)
    sql = re.sub(r"(?m)^\s*COMMIT;\s*$", "", sql, count=1)
    op.execute(sql)


def downgrade() -> None:
    """No-op: the KB is derived data and the reload is forward-only."""
