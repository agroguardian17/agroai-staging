"""Port: advisory-performance metrics (Domain 12 evaluation counters).

The KB's Domain 12 (system governance / evaluation) reads a small set of
history-derived counters that describe how well the advisory loop is working:

- ``advisory_issued_count`` - recommended actions issued to the farmer.
- ``advisory_completed_count`` - of those, how many the farmer acted on.
- ``advisory_completed_on_time_count`` - completed within the compliance window.
- ``action_compliance_rate`` - the KB's primary success metric (D12-EVAL-001),
  ``advisory_completed_on_time_count / advisory_issued_count`` as a percent.

Unlike every other farm-brain field these are not farm *inputs*: they are
computed from the engine's own history - ``ai_suggestions`` (what was issued)
joined against ``farmer_actions`` (what the farmer did). They are scoped to one
crop season so the counters describe the season the daily job is advising on.

The remaining D12 fields (true/false alarm counts, bias observations, photo
review counts, clustering) need a human QA-review workflow that does not exist
yet, and stay UNKNOWN until that subsystem is built.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class AdvisoryPerformance:
    """Per-season advisory-compliance counters.

    ``action_compliance_rate`` is a percent in ``[0, 100]``, or ``None`` when
    no advisory was issued (division would be undefined - the KB then reports
    the dependent rules as UNKNOWN rather than firing on a fabricated zero).
    """

    advisory_issued_count: int
    advisory_completed_count: int
    advisory_completed_on_time_count: int
    action_compliance_rate: Decimal | None


@runtime_checkable
class AdvisoryMetricsRepo(Protocol):
    """Read-only aggregation over ``ai_suggestions`` + ``farmer_actions``."""

    async def performance_for_season(
        self, season_id: uuid.UUID, *, on_time_days: int = 3
    ) -> AdvisoryPerformance:
        """Compliance counters for one season.

        ``on_time_days`` is the compliance window: an advisory is "on time"
        when the farmer's first following action is recorded no later than
        ``on_time_days`` after the advisory was issued (D12-AL-001 flags an
        action not recorded within 3 days of its deadline).
        """
        ...


__all__ = ["AdvisoryMetricsRepo", "AdvisoryPerformance"]
