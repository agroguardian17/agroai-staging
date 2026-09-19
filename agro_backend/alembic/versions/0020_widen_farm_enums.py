"""0020 widen over-narrow farms enums for real pilot data.

The pilot intake sheet surfaced real-world values the migration-0001 CHECKs
rejected:

- ``water_source_secondary`` — add ``canal, tanker, rain, dam`` (was only
  well/borewell/farm_pond/none). "Dam" is a legitimate secondary source.
- ``mobile_network_quality`` — realign the odd tech-mixed set (4G/3G/2G/poor)
  to a quality scale ``excellent/good/moderate/poor``; existing tech values are
  mapped first so the new CHECK validates.
- ``electricity_source`` — allow **multiple** sources: a farm can be on grid
  AND solar. Store a comma-separated list of ``grid/solar_pump/generator``
  (legacy scalar ``mixed`` still accepted). The data-entry form renders this as
  a multi-select.

Each CHECK is swapped by discovering its (auto-named) constraint so the swap is
robust to the exact name. Nothing in app logic branches on these columns
(descriptive metadata), so widening is behaviour-neutral. Reversible.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _drop_col_check(col: str) -> str:
    """SQL to drop whichever CHECK constraint on farms mentions ``col``."""
    return f"""
DO $$
DECLARE cname text;
BEGIN
    SELECT conname INTO cname FROM pg_constraint
     WHERE conrelid = 'farms'::regclass AND contype = 'c'
       AND pg_get_constraintdef(oid) ILIKE '%{col}%';
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE farms DROP CONSTRAINT %I', cname);
    END IF;
END $$;
"""


_WATER_NEW = (
    "water_source_secondary IN ('well','borewell','farm_pond','canal','tanker','rain','dam','none')"
)
_WATER_OLD = "water_source_secondary IN ('well','borewell','farm_pond','none')"
_MOBILE_NEW = "mobile_network_quality IN ('excellent','good','moderate','poor')"
_MOBILE_OLD = "mobile_network_quality IN ('4G','3G','2G','poor')"
# Legacy scalar 'mixed' OR a comma-list of the base sources.
_ELEC_NEW = (
    r"electricity_source ~ "
    r"'^(mixed|(grid|solar_pump|generator)(,(grid|solar_pump|generator))*)$'"
)
_ELEC_OLD = "electricity_source IN ('grid','solar_pump','generator','mixed')"


def upgrade() -> None:
    # water_source_secondary — pure widen.
    op.execute(_drop_col_check("water_source_secondary"))
    op.execute(
        f"ALTER TABLE farms ADD CONSTRAINT farms_water_source_secondary_check CHECK ({_WATER_NEW})"
    )

    # mobile_network_quality — drop old, map any existing tech values, add new.
    op.execute(_drop_col_check("mobile_network_quality"))
    op.execute(
        "UPDATE farms SET mobile_network_quality = CASE mobile_network_quality "
        "WHEN '4G' THEN 'excellent' WHEN '3G' THEN 'good' WHEN '2G' THEN 'moderate' "
        "ELSE mobile_network_quality END "
        "WHERE mobile_network_quality IN ('4G','3G','2G')"
    )
    op.execute(
        f"ALTER TABLE farms ADD CONSTRAINT farms_mobile_network_quality_check CHECK ({_MOBILE_NEW})"
    )

    # electricity_source — allow a comma-list; keep legacy 'mixed' valid.
    op.execute(_drop_col_check("electricity_source"))
    op.execute(
        f"ALTER TABLE farms ADD CONSTRAINT farms_electricity_source_check CHECK ({_ELEC_NEW})"
    )


def downgrade() -> None:
    # Coerce widened values back into the old domains so the old CHECKs validate.
    op.execute(
        "UPDATE farms SET water_source_secondary = 'none' "
        "WHERE water_source_secondary IN ('canal','tanker','rain','dam')"
    )
    op.execute(_drop_col_check("water_source_secondary"))
    op.execute(
        f"ALTER TABLE farms ADD CONSTRAINT farms_water_source_secondary_check CHECK ({_WATER_OLD})"
    )

    op.execute(
        "UPDATE farms SET mobile_network_quality = CASE mobile_network_quality "
        "WHEN 'excellent' THEN '4G' WHEN 'good' THEN '3G' WHEN 'moderate' THEN '2G' "
        "ELSE mobile_network_quality END "
        "WHERE mobile_network_quality IN ('excellent','good','moderate')"
    )
    op.execute(_drop_col_check("mobile_network_quality"))
    op.execute(
        f"ALTER TABLE farms ADD CONSTRAINT farms_mobile_network_quality_check CHECK ({_MOBILE_OLD})"
    )

    op.execute("UPDATE farms SET electricity_source = 'mixed' WHERE electricity_source LIKE '%,%'")
    op.execute(_drop_col_check("electricity_source"))
    op.execute(
        f"ALTER TABLE farms ADD CONSTRAINT farms_electricity_source_check CHECK ({_ELEC_OLD})"
    )
