"""Postgres adapter for
:class:`~app.application.ports.pipeline_trace_repo.PipelineTraceRepo`.

Writes one ``pipeline_trace`` row per ingest message. Observability only — the
broker calls this best-effort, so a failure here must never surface to ingest.
"""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.pipeline_trace_repo import PipelineTrace

_INSERT = text(
    """
    INSERT INTO pipeline_trace (
        trace_id, created_at, topic, schema_id, node_id, plot_id, tenant_id,
        recorded_at, raw_payload, calibrated, stages, validations, overall, drop_reason
    ) VALUES (
        :trace_id, :created_at, :topic, :schema_id, :node_id, :plot_id, :tenant_id,
        :recorded_at, CAST(:raw_payload AS JSONB), CAST(:calibrated AS JSONB),
        CAST(:stages AS JSONB), CAST(:validations AS JSONB), :overall, :drop_reason
    )
    ON CONFLICT (trace_id) DO NOTHING
    """
)


class PgPipelineTraceRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def record(self, trace: PipelineTrace) -> None:
        params = {
            "trace_id": trace.trace_id,
            "created_at": trace.created_at,
            "topic": trace.topic,
            "schema_id": trace.schema_id,
            "node_id": trace.node_id,
            "plot_id": trace.plot_id,
            "tenant_id": trace.tenant_id,
            "recorded_at": trace.recorded_at,
            "raw_payload": json.dumps(trace.raw_payload, default=str),
            "calibrated": json.dumps(trace.calibrated, default=str),
            "stages": json.dumps(trace.stages, default=str),
            "validations": json.dumps(trace.validations, default=str),
            "overall": trace.overall,
            "drop_reason": trace.drop_reason,
        }
        async with self._sm() as session, session.begin():
            await session.execute(_INSERT, params)
