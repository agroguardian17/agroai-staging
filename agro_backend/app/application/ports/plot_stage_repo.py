"""Port for per-plot growth-stage history.

The KB rule **D03-SB-003** fires on a phenological transition
(``current_stage != previous_stage AND previous_stage IS NOT NULL``). The
mapper knows the *current* stage from the active season, but "the stage this
plot was in on the previous run" is history we have to keep ourselves — the
ginger engine's own ``engine_state`` store only persists notifier/override
bookkeeping, not the farm-brain stage.

This port is that history: the daily job **records** the stage each run, and
the mapper **reads** the most recent stage from a prior run to fill
``previous_stage``. Until a plot has been seen on two distinct days,
``previous_stage`` stays ``None`` and the rule stays dormant (correct — there
is no transition to detect yet).
"""

from __future__ import annotations

import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class PlotStageRepo(Protocol):
    """Read/write a plot's growth-stage-by-run-date log."""

    async def previous_stage(self, plot_id: str, before: datetime.date) -> str | None:
        """The stage recorded on the most recent run strictly before ``before``.

        Returns ``None`` when the plot has no earlier recorded run.
        """
        ...

    async def record_stage(self, plot_id: str, run_date: datetime.date, stage: str) -> None:
        """Upsert this run's stage for the plot (idempotent on plot + date)."""
        ...
