"""Integration test for PgPipelineTraceRepo against the pipeline_trace table."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.pipeline_trace_repo import PipelineTrace
from app.infra.persistence.pg_pipeline_trace_repo import PgPipelineTraceRepo

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]


async def test_record_round_trips(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    repo = PgPipelineTraceRepo(sessionmaker)
    tid = str(uuid.uuid4())
    trace = PipelineTrace(
        trace_id=tid,
        topic="agro/v2/t/f/AGR-SN-0001/telemetry",
        overall="warn",
        created_at=datetime.now(UTC),
        schema_id="agro-guardian/telemetry/v2-raw",
        node_id="AGR-SN-0001",
        plot_id="PLOT_PILOT_001",
        recorded_at=datetime(2026, 10, 4, 6, 0, tzinfo=UTC),
        raw_payload={"soil_adc": 412},
        calibrated={"soil_moisture_1_pct": 42.0},
        stages={"s6_persist": {"status": "inserted"}},
        validations=[{"field": "window_s", "level": "warn"}],
    )
    await repo.record(trace)
    try:
        async with sessionmaker() as s:
            row = (
                await s.execute(
                    text(
                        "SELECT overall, node_id, raw_payload->>'soil_adc' AS adc, "
                        "calibrated->>'soil_moisture_1_pct' AS moist "
                        "FROM pipeline_trace WHERE trace_id = :t"
                    ),
                    {"t": tid},
                )
            ).one()
        assert row.overall == "warn"
        assert row.node_id == "AGR-SN-0001"
        assert row.adc == "412"
        assert row.moist == "42.0"
        # idempotent on trace_id
        await repo.record(trace)
    finally:
        async with sessionmaker() as s, s.begin():
            await s.execute(text("DELETE FROM pipeline_trace WHERE trace_id = :t"), {"t": tid})


async def test_purge_older_than(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    repo = PgPipelineTraceRepo(sessionmaker)
    old_id, new_id = str(uuid.uuid4()), str(uuid.uuid4())
    now = datetime.now(UTC)

    def _trace(tid: str, created: datetime) -> PipelineTrace:
        return PipelineTrace(
            trace_id=tid, topic="t", overall="ok", created_at=created, node_id="PURGE_TEST"
        )

    await repo.record(_trace(old_id, now - timedelta(days=40)))
    await repo.record(_trace(new_id, now))
    try:
        removed = await repo.purge_older_than(now - timedelta(days=30))
        assert removed >= 1
        async with sessionmaker() as s:
            remaining = {
                str(x)
                for x in (
                    await s.execute(
                        text("SELECT trace_id FROM pipeline_trace WHERE node_id = 'PURGE_TEST'")
                    )
                )
                .scalars()
                .all()
            }
        assert old_id not in remaining
        assert new_id in remaining
    finally:
        async with sessionmaker() as s, s.begin():
            await s.execute(text("DELETE FROM pipeline_trace WHERE node_id = 'PURGE_TEST'"))
