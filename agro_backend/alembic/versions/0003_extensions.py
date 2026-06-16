"""0003 extensions: uuid-ossp, postgis, pgcrypto (+ optional vector).

Created after the tables (0001/0002) because no table DDL depends on these
extensions -- UUID defaults use core ``gen_random_uuid()`` and boundaries are
JSONB, not PostGIS geometry (see docs/SCHEMA_DECISIONS.md).

``vector`` (pgvector) is created best-effort: the pilot's ``postgis/postgis``
image does not bundle it, and the pilot uses ChromaDB (not pgvector) for RAG.
The DO block swallows the "could not open extension control file" error so the
migration stays green on images without pgvector. Swap in a pgvector-bundled
image and re-run to enable it.

Revision ID: 0003
Revises: 0002
Create Date: Phase 1
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION
    WHEN undefined_file OR insufficient_privilege OR feature_not_supported THEN
        RAISE NOTICE 'pgvector not available in this image; skipping (pilot uses ChromaDB).';
END
$$;
"""


DOWNGRADE_SQL = r"""
DROP EXTENSION IF EXISTS vector;
DROP EXTENSION IF EXISTS pgcrypto;
DROP EXTENSION IF EXISTS postgis;
DROP EXTENSION IF EXISTS "uuid-ossp";
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
