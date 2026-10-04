"""Plot-run-trace repository port (downstream pipeline observability).

One row per plot per daily run, recording how the 06:30 ginger pipeline moved
through its downstream stages — farm-brain build (field coverage) → KB engine
evaluation (rules fired) → advisory write. The ingest stages live in
``pipeline_trace``; this is the daily-run companion. Observability only, written
best-effort by the daily job when ``PIPELINE_TRACE_ENABLED`` is on.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class PlotRunTrace:
    trace_id: str
    plot_id: str
    run_date: _dt.date
    overall: str  # ok | warn | fail
    created_at: _dt.datetime
    season_id: str | None = None
    tenant_id: str | None = None
    farm_id: str | None = None
    advisories_written: int = 0
    coverage: dict[str, Any] = field(default_factory=dict)
    derived: dict[str, Any] = field(default_factory=dict)
    engine: dict[str, Any] = field(default_factory=dict)
    stages: dict[str, Any] = field(default_factory=dict)
    validations: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@runtime_checkable
class PlotRunTraceRepo(Protocol):
    async def record(self, trace: PlotRunTrace) -> None:
        """Persist one daily-run trace row (best-effort caller)."""
        ...
