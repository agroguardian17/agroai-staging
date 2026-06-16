"""Reading repository port.


Application-layer Protocol that any reading-persistence adapter must satisfy.
The concrete Postgres implementation lands in Round 6 as
``app.infra.persistence.pg_reading_repo.PgReadingRepo``; this file is the
contract.


The methods here are exactly what the ingest use case (Round 7) and the
Phase 2.3 validation gates (Round 5) need - nothing more. Adding a new
method requires a use case to justify it.


Per ``.cursorrules`` #14 the application layer calls *this Protocol*, never
the concrete repo. Tests substitute a fake implementation; production
substitutes Postgres.
"""


from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from app.domain.sensor import Reading

# ---------------------------------------------------------------------------
# Fields allowed in the parameterised history queries.
#
# The implementation in Round 6 builds SQL against ``node_sensor_readings``;
# a string field name passed in from the validation gate is interpolated
# into a column reference. To prevent SQL injection on the column name we
# whitelist exactly the columns the gates need. The repo MUST reject any
# field not in this set with a ``ValueError`` - tested at the integration
# boundary in Round 5.
# ---------------------------------------------------------------------------
ALLOWED_HISTORY_FIELDS: frozenset[str] = frozenset(
    {
        "soil_moisture_1_pct",
        "soil_moisture_2_pct",
        "soil_moisture_avg_pct",
        "soil_temp_c",
        "soil_temp_rootzone_c",
        "soil_ph",
        "soil_ec_ms_cm",
        "soil_n_mg_kg",
        "soil_p_mg_kg",
        "soil_k_mg_kg",
        "battery_voltage_v",
    }
)




@runtime_checkable
class ReadingRepo(Protocol):
    """Operations the ingest pipeline + validation gates need against ``node_sensor_readings``.


    Every method is async. Implementations MUST be idempotent on
    ``(node_id, recorded_at)`` per the schema's UNIQUE constraint
    (``node_sensor_readings_idem`` from migration 0005).
    """


    async def save(self, reading: Reading) -> int | None:
        """Insert one row; return the new ``reading_id``.


        Returns ``None`` if the ``(node_id, recorded_at)`` pair was already
        present (duplicate from QoS-1 retry, SD-card replay, etc.). The
        Phase 4 ingest use case treats ``None`` as "drop silently, increment
        metrics.ingest.duplicate" (Phase 9 #20).
        """
        ...


    async def latest_for_plot(self, plot_id: str, limit: int) -> list[Reading]:
        """Most recent ``limit`` readings for a plot, newest first.


        Used by the read API (Round 8, ``GET /plots/{id}/sensor_history``)
        and by the live dashboard.
        """
        ...


    async def recent_for_node(self, node_id: str, since: datetime) -> list[Reading]:
        """All readings from one node since ``since`` (UTC, tz-aware).


        Used by the cross-sensor validation gate (Round 5) when it needs
        multiple recent rows from the same device.
        """
        ...


    async def history_for_stuck_check(
        self, node_id: str, field: str, minutes: int
    ) -> list[Decimal | None]:
        """Trailing window of values for the *stuck* validation gate.


        The implementation:


        * MUST validate ``field`` against :data:`ALLOWED_HISTORY_FIELDS`
          and raise ``ValueError`` otherwise (SQL-injection guard).
        * Returns up to ~6 most-recent values in arrival order
          (oldest -> newest). ``None`` entries mean the column was null
          on that row.


        The stuck gate considers a sensor "stuck" when 4+ of the last 6
        values are identical and non-null (Round 5).
        """
        ...


    async def history_for_mad_check(self, node_id: str, field: str, hours: int) -> list[Decimal]:
        """Trailing 24-h window for Median Absolute Deviation outlier check.


        Same field whitelist as :meth:`history_for_stuck_check`. Returns
        only non-null values (MAD over nulls is meaningless). Empty list
        is a valid return (e.g. brand-new node) - the gate falls back to
        "pass" until enough history exists.
        """
        ...




__all__ = ["ALLOWED_HISTORY_FIELDS", "ReadingRepo"]
