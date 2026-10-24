"""Isolation tests for the broker's pipeline-trace hooks.

The contract: a trace write must NEVER affect ingest. These verify the guards
hold — a repo that raises, or no repo at all, both leave the broker calls quiet.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

from app.application.evaluate_rules import EvaluateRulesDeps, EvaluateRulesResult
from app.application.ingest_telemetry import IngestDeps, IngestResult
from app.application.ports.app_event_repo import AppEvent
from app.application.ports.pipeline_trace_repo import PipelineTrace
from app.application.process_reading import ProcessReadingDeps, ProcessReadingResult
from app.infra.mqtt.broker import BrokerSettings, IngestBroker


def _deps() -> ProcessReadingDeps:
    return ProcessReadingDeps(
        ingest_deps=IngestDeps(reading_repo=MagicMock(), event_bus=MagicMock()),
        evaluate_deps=EvaluateRulesDeps(alert_repo=MagicMock(), event_bus=MagicMock()),
    )


class _FailingTraceRepo:
    async def record(self, trace: PipelineTrace) -> None:
        raise RuntimeError("trace backend down")


class _RecordingTraceRepo:
    def __init__(self) -> None:
        self.traces: list[PipelineTrace] = []

    async def record(self, trace: PipelineTrace) -> None:
        self.traces.append(trace)


def _broker(trace_repo: Any) -> IngestBroker:
    return IngestBroker(
        BrokerSettings(host="localhost", port=1883), _deps(), pipeline_trace_repo=trace_repo
    )


class _Raw:
    def model_dump(self) -> dict[str, Any]:
        return {"soil_adc": 412, "window_s": 300, "npk_ok": True}


@dataclass
class _Model:
    raw_readings: _Raw
    node_id: str
    plot_id: str
    tenant_id: uuid.UUID
    recorded_at: datetime
    schema_id: str = "agro-guardian/telemetry/v2-raw"


@dataclass
class _Reading:
    recorded_at: datetime
    soil_moisture_1_pct: Decimal


def _ingest_objs() -> tuple[_Model, _Reading, ProcessReadingResult, Any]:
    now = datetime(2026, 10, 4, 6, 0, tzinfo=UTC)
    model = _Model(_Raw(), "AGR-SN-0001", "PLOT_PILOT_001", uuid.uuid4(), now)
    reading = _Reading(recorded_at=now, soil_moisture_1_pct=Decimal("42"))
    result = ProcessReadingResult(
        ingest=IngestResult(reading_id=1, validation_warn=False, flags={}),
        rules=EvaluateRulesResult(hits=0, created=0, cooldown_suppressed=0),
    )
    return model, reading, result, MagicMock(calibration_version=7)


async def test_write_trace_swallows_repo_errors() -> None:
    # Must not raise even though the repo throws.
    await _broker(_FailingTraceRepo())._write_trace(
        PipelineTrace(trace_id="t", topic="x", overall="ok", created_at=datetime.now(UTC))
    )


async def test_write_trace_noop_without_repo() -> None:
    await _broker(None)._write_trace(
        PipelineTrace(trace_id="t", topic="x", overall="ok", created_at=datetime.now(UTC))
    )


async def test_trace_drop_never_raises() -> None:
    await _broker(_FailingTraceRepo())._trace_drop("agro/v2/x", "validation", "s2_validate")


async def test_trace_ingest_records_and_never_raises() -> None:
    model, reading, result, cal = _ingest_objs()
    rec = _RecordingTraceRepo()
    await _broker(rec)._trace_ingest("agro/v2/x", model, reading, result, cal)
    assert len(rec.traces) == 1 and rec.traces[0].node_id == "AGR-SN-0001"
    # Failing repo on the same path must stay quiet.
    await _broker(_FailingTraceRepo())._trace_ingest("agro/v2/x", model, reading, result, cal)


# --- R3.5 app_event (notable-events stream) ---------------------------------
class _RecordingAppEventRepo:
    def __init__(self) -> None:
        self.events: list[AppEvent] = []

    async def record(self, event: AppEvent) -> None:
        self.events.append(event)


class _FailingAppEventRepo:
    async def record(self, event: AppEvent) -> None:
        raise RuntimeError("app_event backend down")


def _broker_ev(app_event_repo: Any) -> IngestBroker:
    return IngestBroker(
        BrokerSettings(host="localhost", port=1883), _deps(), app_event_repo=app_event_repo
    )


async def test_record_app_event_captures_and_tags() -> None:
    rec = _RecordingAppEventRepo()
    await _broker_ev(rec)._record_app_event(
        event="unexpected_error", topic="agro/v2/x", detail={"error_type": "RuntimeError"}
    )
    assert len(rec.events) == 1
    ev = rec.events[0]
    assert ev.level == "error" and ev.source == "ingest_broker"
    assert ev.event == "unexpected_error" and ev.entity == "agro/v2/x"
    assert ev.detail["error_type"] == "RuntimeError"


async def test_record_app_event_noop_without_repo_and_swallows_errors() -> None:
    # No repo: silent no-op.
    await _broker_ev(None)._record_app_event(event="x", topic="t", detail={})
    # Failing repo: guarded, never raises.
    await _broker_ev(_FailingAppEventRepo())._record_app_event(event="x", topic="t", detail={})
