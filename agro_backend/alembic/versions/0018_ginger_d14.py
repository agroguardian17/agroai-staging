"""0018 ginger Domain 14 (satellite/remote sensing) + D07 VPD retrofit.

Loads the additive knowledge-base delta produced by the agronomist team's
Domain 14 build on top of the D01-D13 KB that migration 0010 installed:

- 47 Domain 14 rules (satellite / remote-sensing intelligence) + 1 new domain
- 3 Domain 7 VPD-retrofit rules (D07-VP-001..003) + the ``VP`` category
- 6 precedence relations (3 BUNDLES + 2 SEQUENCES for D14, 1 BUNDLES for VPD)
- 52 new farm_brain fields (49 declared in D14, 3 VPD fields in D07)
- 11 open items (D14-OI-01..10, D07-OI-09)
- D07 ``total_rules`` counter 35 -> 38 (post-VPD)

The delta SQL at ``agro_backend/ginger/generated/agroguardian_ginger_kb_d14.sql``
is a data-only extract of the compiled full build ``kb_ginger_d14_v1.0.sql``.
It was verified by set-equality: applying it on top of the 0010 build yields a
kb_* row set byte-identical to the full 14-domain build (481 rules, 45
precedence, 24 immutable, 358 farm_brain fields, 120 open items). Every INSERT
carries ``ON CONFLICT DO NOTHING`` so the migration is idempotent; the schema,
indexes and immutable-override trigger already exist from 0010, so no DDL runs.

The runtime engine (``ginger.engine.runtime_loader.PostgresSource``) reads all
rules, triggers, delivery classes, precedence and immutable flags directly from
these tables, so loading these rows is what makes Domain 14 live at runtime.

Downgrade removes exactly the rows this migration adds, in FK-safe order, and
restores the D07 counter. No pre-existing D01-D13 row is touched either way.

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-18
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# This migration lives at agro_backend/alembic/versions/0018_ginger_d14.py, so
# the compiled delta is two directories up and then ginger/generated/.
_SQL_PATH = (
    Path(__file__).resolve().parents[2] / "ginger" / "generated" / "agroguardian_ginger_kb_d14.sql"
)

# The three farm_brain fields the VPD retrofit declares under domain 7 (the
# rest of the delta's new fields are declared under domain 14). Named
# explicitly so downgrade removes precisely what upgrade added.
_VPD_FARM_BRAIN_FIELDS = ("vpd_kpa", "vpd_night_mean_kpa", "spray_scheduled_today")


# The D14/VPD rules use recoverability='same_season', a class the 0010 CHECK
# (none/partial/full) omits. Widen it before loading the delta. The DO block
# discovers the existing CHECK by name (it is an inline, auto-named constraint)
# so the swap works regardless of the exact generated name.
_WIDEN_RECOVERABILITY_CHECK = """
DO $$
DECLARE cname text;
BEGIN
    SELECT conname INTO cname FROM pg_constraint
     WHERE conrelid = 'kb_rules'::regclass AND contype = 'c'
       AND pg_get_constraintdef(oid) ILIKE '%recoverability%';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE kb_rules DROP CONSTRAINT %I', cname);
    END IF;
    ALTER TABLE kb_rules ADD CONSTRAINT kb_rules_recoverability_check
        CHECK (recoverability IN ('none', 'partial', 'full', 'same_season'));
END $$;
"""

_NARROW_RECOVERABILITY_CHECK = """
DO $$
DECLARE cname text;
BEGIN
    SELECT conname INTO cname FROM pg_constraint
     WHERE conrelid = 'kb_rules'::regclass AND contype = 'c'
       AND pg_get_constraintdef(oid) ILIKE '%recoverability%';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE kb_rules DROP CONSTRAINT %I', cname);
    END IF;
    ALTER TABLE kb_rules ADD CONSTRAINT kb_rules_recoverability_check
        CHECK (recoverability IN ('none', 'partial', 'full'));
END $$;
"""


def upgrade() -> None:
    """Load the Domain 14 + VPD knowledge-base delta."""
    if not _SQL_PATH.exists():
        raise RuntimeError(
            f"Ginger D14 delta SQL not found at {_SQL_PATH}. "
            "Ensure agro_backend/ginger/generated/agroguardian_ginger_kb_d14.sql "
            "is present."
        )
    # Schema prep: admit the 'same_season' recoverability class the delta uses.
    # (The delta itself adds the 'ALL' meta-stage row before its kb_rules INSERTs.)
    op.execute(_WIDEN_RECOVERABILITY_CHECK)
    sql = _SQL_PATH.read_text(encoding="utf-8")
    op.execute(sql)


def downgrade() -> None:
    """Remove every row this migration added, in FK-safe (child-first) order."""
    like = "rule_id LIKE 'D14-%' OR rule_id LIKE 'D07-VP-%'"
    # Children of kb_rules first.
    op.execute(
        "DELETE FROM kb_precedence WHERE subject_rule LIKE 'D14-%' OR subject_rule LIKE 'D07-VP-%'"
    )
    op.execute(f"DELETE FROM kb_rule_dependencies WHERE {like}")
    op.execute(f"DELETE FROM kb_rule_references WHERE {like}")
    op.execute(f"DELETE FROM kb_golden_tests WHERE {like}")
    op.execute(f"DELETE FROM kb_rule_fields WHERE {like}")
    op.execute(f"DELETE FROM kb_rules WHERE {like}")
    # Categories referenced by the rules above.
    op.execute(
        "DELETE FROM kb_rule_categories WHERE domain_id = 14 OR (domain_id = 7 AND category = 'VP')"
    )
    # Farm-brain fields (D14 ones by domain; the 3 VPD ones by explicit name).
    vpd_names = ", ".join(f"'{f}'" for f in _VPD_FARM_BRAIN_FIELDS)
    op.execute(
        "DELETE FROM kb_farm_brain_fields "
        f"WHERE declared_in_domain = 14 OR field_name IN ({vpd_names})"
    )
    # Open items.
    op.execute("DELETE FROM kb_open_items WHERE domain_id = 14 OR open_item_id = 'D07-OI-09'")
    # The domain row last (parent of the above).
    op.execute("DELETE FROM kb_domains WHERE domain_id = 14")
    # Restore the D07 counter to its pre-VPD value.
    op.execute("UPDATE kb_domains SET total_rules = 35 WHERE domain_id = 7 AND total_rules = 38")
    # Remove the 'ALL' meta-stage the delta added (no rule references it now).
    op.execute("DELETE FROM kb_stages WHERE stage_code = 'ALL'")
    # Restore the narrower recoverability CHECK (no 'same_season' rows remain).
    op.execute(_NARROW_RECOVERABILITY_CHECK)
