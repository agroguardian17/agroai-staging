"""Pipeline-trace repository port.

The tracer records one row per ingest message describing how it moved through
the server-side stages (receive → validate → raw snapshot → calibrate →
clock-skew → persist → device-rules), the raw-vs-calibrated values, and the
validation checklist. It is **observability only**: a trace write must never
affect ingest, so the broker calls ``record`` best-effort (guarded) and only
when a repo is injected (the ``PIPELINE_TRACE_ENABLED`` flag).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class PipelineTrace:
    """One ingest message's journey through the pipeline. JSON-friendly."""

    trace_id: str
    topic: str
    overall: str  # ok | warn | fail
    created_at: _dt.datetime
    schema_id: str | None = None
    node_id: str | None = None
    plot_id: str | None = None
    tenant_id: str | None = None
    recorded_at: _dt.datetime | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    calibrated: dict[str, Any] = field(default_factory=dict)
    stages: dict[str, Any] = field(default_factory=dict)
    validations: list[dict[str, Any]] = field(default_factory=list)
    drop_reason: str | None = None


@runtime_checkable
class PipelineTraceRepo(Protocol):
    async def record(self, trace: PipelineTrace) -> None:
        """Persist one trace row. Implementations must be best-effort callers'
        friendly — raising is tolerated (the broker guards the call), but the
        adapter should keep its own write in a single short transaction."""
        ...
