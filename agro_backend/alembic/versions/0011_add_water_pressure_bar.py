"""0011 add water_pressure_bar column to node_sensor_readings.

The VIRAAI v1.0 Sub Node hardware includes an analog pressure sensor on
pin A3 (see the teammate's ``Final Code`` doc, 2026-08-03). The reading
is meaningful for irrigation-line diagnostics and complements the flow
sensor (already stored in ``water_flow_lpm``).

Round G brought us the ginger engine; this migration is the small
follow-up to make the pressure reading first-class in the wire schema
and the persistence layer. Nothing else moves — one column added, no
FK impact, no data migration required.

Column semantics:
* Range 0..~10 bar (typical drip-irrigation pressures).
* Nullable — a Sub Node without the sensor still ingests cleanly.
* Stored as ``DOUBLE PRECISION`` to match every other sensor column
  (the Reading domain wraps it as ``Decimal | None`` at the boundary
  for float-precision safety, per .cursorrules #3).

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-04
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ``node_sensor_readings`` is partitioned by month. Adding a column to
    # the parent table automatically propagates to every child partition
    # in Postgres 15+ (declarative partitioning). No per-partition DDL
    # needed.
    op.execute(
        "ALTER TABLE node_sensor_readings "
        "ADD COLUMN IF NOT EXISTS water_pressure_bar DOUBLE PRECISION"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE node_sensor_readings "
        "DROP COLUMN IF EXISTS water_pressure_bar"
    )
