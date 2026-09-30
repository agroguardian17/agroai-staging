"""Water-budget repository port.

Read-side contract the water-budget engine (``build_farm_brain`` +
``app.domain.water_budget``) needs:

* per-variety, per-stage water targets, looked up by DAP window
  (``variety_stage_water_target``);
* the variety's full-season (LIFECYCLE) high-end target;
* cumulative drip flow (litres) delivered to a plot since a timestamp
  (aggregated from ``node_sensor_readings.water_flow_lpm``).

Kept as a single optional port so tests/fakes that don't exercise the water
budget need not implement it — production wires the Postgres adapter, everything
else leaves it unset and the derived water-budget fields stay UNKNOWN.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

from app.domain.water_budget import VarietyStageTargets


@runtime_checkable
class WaterBudgetRepo(Protocol):
    async def targets_for_dap(self, variety: str, dap: int) -> VarietyStageTargets | None:
        """Water targets for the stage whose DAP window contains ``dap``.

        Matches the plot's variety loosely (season stores "Mahima", the table
        keys "IISR-Mahima"). Returns ``None`` if the variety or a covering stage
        row is absent.
        """
        ...

    async def lifecycle_high(self, variety: str) -> Decimal | None:
        """The variety's LIFECYCLE-row ``stage_target_l_high`` (full-season per-plant high-end)."""
        ...

    async def flow_litres_since(self, plot_id: str, since: datetime) -> Decimal | None:
        """Total drip litres delivered to the plot at/after ``since``.

        Aggregated from ``node_sensor_readings.water_flow_lpm`` (L/min) over the
        reading cadence. Returns ``None`` if no flow rows exist in the window.
        """
        ...

    async def last_irrigation_at(self, plot_id: str) -> datetime | None:
        """Timestamp of the most recent positive-flow reading (last irrigation event).

        ``MAX(recorded_at) WHERE water_flow_lpm > 0``; ``None`` if the plot has
        never recorded flow.
        """
        ...
