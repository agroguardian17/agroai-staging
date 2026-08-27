"""Unit tests for :class:`~app.infra.mqtt.broker.IngestBroker`.


Replaces paho-mqtt connection + the parse/ingest functions with fakes so
the tests run without a real broker. Verifies:


* Lifecycle: start/stop is idempotent; can be called from asyncio.
* Drain loop classifies exceptions into the right metric labels.
* Queue full drops with the right reason.
* Topic-template helper folds concrete topics to the metric template.
"""


from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.application.evaluate_rules import EvaluateRulesDeps, EvaluateRulesResult
from app.application.ingest_telemetry import IngestDeps, IngestResult
from app.application.process_reading import ProcessReadingDeps, ProcessReadingResult
from app.domain.sensor import Reading, TransmissionType
from app.infra.mqtt import broker as broker_module
from app.infra.mqtt.broker import (
    MAX_QUEUE,
    QOS_AT_LEAST_ONCE,
    TELEMETRY_TOPIC_FILTER,
    BrokerSettings,
    IngestBroker,
    _normalize_clock_skew,
    _topic_template,
)
from app.infra.mqtt.schemas import (
    SCHEMA_TELEMETRY_V2_MASTER,
    TelemetryIn,
    TelemetryMaster,
    TopicParseError,
    UnknownTopicKindError,
)
from app.lib import metrics


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
def _reading() -> Reading:
    return Reading(
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        farmer_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        farm_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        plot_id="P1",
        node_id="N1",
        recorded_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        received_at_master=datetime(2026, 5, 1, 12, 0, 5, tzinfo=UTC),
        transmission_type=TransmissionType.LORA,
    )




class _StubModel:
    """Stand-in for TelemetryIn whose to_domain returns our fixture Reading."""


    def to_domain(self) -> Reading:
        return _reading()




def _ok_parse(topic: str, raw: bytes) -> _StubModel:
    return _StubModel()




async def _ok_ingest(reading: Reading, deps: ProcessReadingDeps) -> ProcessReadingResult:
    return ProcessReadingResult(
        ingest=IngestResult(reading_id=1, validation_warn=False, flags={}),
        rules=EvaluateRulesResult(hits=0, created=0, cooldown_suppressed=0),
    )




async def _duplicate_ingest(reading: Reading, deps: ProcessReadingDeps) -> ProcessReadingResult:
    return ProcessReadingResult(
        ingest=IngestResult(reading_id=None, validation_warn=False, flags={}),
        rules=None,
    )




# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _empty_deps() -> ProcessReadingDeps:
    # We never actually exercise these in unit tests - the parse/ingest
    # fakes short-circuit before any port is called.
    return ProcessReadingDeps(
        ingest_deps=IngestDeps(reading_repo=MagicMock(), event_bus=MagicMock()),
        evaluate_deps=EvaluateRulesDeps(alert_repo=MagicMock(), event_bus=MagicMock()),
    )




def _settings() -> BrokerSettings:
    return BrokerSettings(host="localhost", port=1883)




@pytest.fixture(autouse=True)
def _reset_metrics() -> None:
    # Prometheus counters accumulate across tests in the same process.
    # We can't truly reset them but each test asserts on a *delta* below.
    pass




def _dropped_count(reason: str) -> float:
    # prometheus_client exposes ._value.get() on Counters; for a labeled
    # counter we grab the child first.
    return metrics.ingest_dropped_total.labels(reason=reason)._value.get()




def _received_count(topic_template: str) -> float:
    return metrics.ingest_received_total.labels(topic=topic_template)._value.get()




def _rule_eval_count() -> float:
    return metrics.rule_evaluations_total._value.get()




def _alerts_created_count() -> float:
    return metrics.alerts_created_total._value.get()




def _cooldown_count() -> float:
    return metrics.alerts_cooldown_suppressed_total._value.get()




# ===========================================================================
# Topic template helper
# ===========================================================================
def test_topic_template_folds_telemetry_topics() -> None:
    assert _topic_template("agro/v2/pilot/F_001/N_001/telemetry") == "agro/v2/+/+/+/telemetry"




def test_topic_template_handles_other_shapes() -> None:
    assert _topic_template("garbage") == "other"
    assert _topic_template("agro/v1/pilot/x/y/telemetry") == "other"




# ===========================================================================
# Drain loop - happy path
# ===========================================================================
async def test_drain_loop_dispatches_to_ingest_fn() -> None:
    ingested: list[Reading] = []


    async def capture_ingest(reading: Reading, _deps: ProcessReadingDeps) -> ProcessReadingResult:
        ingested.append(reading)
        return ProcessReadingResult(
            ingest=IngestResult(reading_id=1, validation_warn=False, flags={}),
            rules=EvaluateRulesResult(hits=0, created=0, cooldown_suppressed=0),
        )


    broker = IngestBroker(
        _settings(),
        _empty_deps(),
        parse_fn=_ok_parse,
        ingest_fn=capture_ingest,
        max_queue=4,
    )


    # Bypass paho - directly set up the asyncio plumbing.
    broker._loop = asyncio.get_running_loop()
    broker._queue = asyncio.Queue(maxsize=4)
    task = asyncio.create_task(broker._drain())


    received_before = _received_count("agro/v2/+/+/+/telemetry")
    broker._enqueue("agro/v2/pilot/F/N/telemetry", b"{}")
    await asyncio.sleep(0.1)


    assert len(ingested) == 1
    received_after = _received_count("agro/v2/+/+/+/telemetry")
    assert received_after == pytest.approx(received_before + 1)


    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task




# ===========================================================================
# Drain loop - duplicate handling
# ===========================================================================
async def test_drain_loop_marks_duplicate_drops() -> None:
    broker = IngestBroker(
        _settings(),
        _empty_deps(),
        parse_fn=_ok_parse,
        ingest_fn=_duplicate_ingest,
        max_queue=4,
    )
    broker._loop = asyncio.get_running_loop()
    broker._queue = asyncio.Queue(maxsize=4)
    task = asyncio.create_task(broker._drain())


    before = _dropped_count("duplicate")
    broker._enqueue("agro/v2/pilot/F/N/telemetry", b"{}")
    await asyncio.sleep(0.1)
    after = _dropped_count("duplicate")
    assert after == pytest.approx(before + 1)


    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task




# ===========================================================================
# Drain loop - exception classification
# ===========================================================================
async def _run_one_message_through_drain(parse_fn: Any, ingest_fn: Any = _ok_ingest) -> None:
    broker = IngestBroker(
        _settings(),
        _empty_deps(),
        parse_fn=parse_fn,
        ingest_fn=ingest_fn,
        max_queue=4,
    )
    broker._loop = asyncio.get_running_loop()
    broker._queue = asyncio.Queue(maxsize=4)
    task = asyncio.create_task(broker._drain())
    broker._enqueue("agro/v2/pilot/F/N/telemetry", b"{}")
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task




async def test_topic_parse_error_increments_topic_parse_label() -> None:
    def bad_topic(_t: str, _r: bytes) -> _StubModel:
        raise TopicParseError("bad topic")


    before = _dropped_count("topic_parse")
    await _run_one_message_through_drain(bad_topic)
    after = _dropped_count("topic_parse")
    assert after == pytest.approx(before + 1)




async def test_unknown_kind_error_increments_unknown_topic_kind_label() -> None:
    def unknown(_t: str, _r: bytes) -> _StubModel:
        raise UnknownTopicKindError("weather not yet supported")


    before = _dropped_count("unknown_topic_kind")
    await _run_one_message_through_drain(unknown)
    after = _dropped_count("unknown_topic_kind")
    assert after == pytest.approx(before + 1)




async def test_validation_error_increments_validation_label() -> None:
    def invalid(_t: str, _r: bytes) -> _StubModel:
        # Provoke a real ValidationError by passing junk into TelemetryIn.
        # (Easier than building a fake ValidationError, which pydantic guards.)
        TelemetryIn.model_validate({"$schema": "agro-guardian/telemetry/v2"})
        raise AssertionError  # unreachable


    before = _dropped_count("validation")
    await _run_one_message_through_drain(invalid)
    after = _dropped_count("validation")
    assert after == pytest.approx(before + 1)




async def test_parse_error_via_value_error_increments_parse_error_label() -> None:
    def value_err(_t: str, _r: bytes) -> _StubModel:
        raise ValueError("garbage payload")


    before = _dropped_count("parse_error")
    await _run_one_message_through_drain(value_err)
    after = _dropped_count("parse_error")
    assert after == pytest.approx(before + 1)




async def test_drain_loop_increments_rule_metrics_for_fresh_insert() -> None:
    async def fired_ingest(_r: Reading, _d: ProcessReadingDeps) -> ProcessReadingResult:
        return ProcessReadingResult(
            ingest=IngestResult(reading_id=42, validation_warn=False, flags={}),
            rules=EvaluateRulesResult(hits=2, created=1, cooldown_suppressed=1),
        )


    broker = IngestBroker(
        _settings(),
        _empty_deps(),
        parse_fn=_ok_parse,
        ingest_fn=fired_ingest,
        max_queue=4,
    )
    broker._loop = asyncio.get_running_loop()
    broker._queue = asyncio.Queue(maxsize=4)
    task = asyncio.create_task(broker._drain())


    eval_before = _rule_eval_count()
    created_before = _alerts_created_count()
    cooldown_before = _cooldown_count()
    broker._enqueue("agro/v2/pilot/F/N/telemetry", b"{}")
    await asyncio.sleep(0.1)


    assert _rule_eval_count() == pytest.approx(eval_before + 1)
    assert _alerts_created_count() == pytest.approx(created_before + 1)
    assert _cooldown_count() == pytest.approx(cooldown_before + 1)


    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task




async def test_unexpected_error_increments_unexpected_label() -> None:
    def boom(_t: str, _r: bytes) -> _StubModel:
        raise RuntimeError("infra meltdown")


    before = _dropped_count("unexpected")
    await _run_one_message_through_drain(boom)
    after = _dropped_count("unexpected")
    assert after == pytest.approx(before + 1)




# ===========================================================================
# 2026-08-27 v2 firmware — v2-master heartbeat dispatch
# ===========================================================================
def _make_heartbeat_model(sub_node_online: bool = True) -> TelemetryMaster:
    return TelemetryMaster.model_validate(
        {
            "$schema": SCHEMA_TELEMETRY_V2_MASTER,
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "farm_id":   "bbbbbbbb-2222-2222-2222-222222222222",
            "main_node_id": "AGR-MN-0001",
            "recorded_at":        "2026-08-27T05:00:00+00:00",
            "received_at_master": "2026-08-27T05:00:00+00:00",
            "transmission_type":  "heartbeat",
            "master_readings": {
                "bme280_temp_c": 32.4,
                "bme280_humidity_pct": 65.1,
                "bme280_pressure_pa": 95000.0,
                "ina219_bus_v": 12.1,
                "ina219_current_ma": 250.0,
                "rain_pulses_window": 0,
                "wind_pulses_window": 0,
                "wind_dir_adc": 976,
                "time_source": "ntp",
                "sub_node_online": sub_node_online,
                "sub_node_silence_ms": 42_000 if sub_node_online else 900_001,
            },
            "firmware_version": "viraai-mn-1.0.0-raw",
        }
    )


async def test_v2_master_heartbeat_meters_and_does_not_ingest() -> None:
    """Drain loop dispatches TelemetryMaster to the meter path, not to ingest."""
    ingested: list[Reading] = []

    async def capture_ingest(reading: Reading, _deps: ProcessReadingDeps) -> ProcessReadingResult:
        ingested.append(reading)
        return ProcessReadingResult(
            ingest=IngestResult(reading_id=1, validation_warn=False, flags={}),
            rules=None,
        )

    def parse_heartbeat(_t: str, _r: bytes) -> TelemetryMaster:
        return _make_heartbeat_model(sub_node_online=True)

    before_online = metrics.main_node_heartbeat_total.labels(
        sub_node_online="true"
    )._value.get()

    await _run_one_message_through_drain(parse_heartbeat, capture_ingest)

    # No ingest — heartbeats are metered + logged, not persisted.
    assert ingested == []

    after_online = metrics.main_node_heartbeat_total.labels(
        sub_node_online="true"
    )._value.get()
    assert after_online == pytest.approx(before_online + 1)


async def test_v2_master_heartbeat_labels_sub_node_offline() -> None:
    def parse_heartbeat(_t: str, _r: bytes) -> TelemetryMaster:
        return _make_heartbeat_model(sub_node_online=False)

    before_offline = metrics.main_node_heartbeat_total.labels(
        sub_node_online="false"
    )._value.get()
    await _run_one_message_through_drain(parse_heartbeat)
    after_offline = metrics.main_node_heartbeat_total.labels(
        sub_node_online="false"
    )._value.get()
    assert after_offline == pytest.approx(before_offline + 1)


# ---------------------------------------------------------------------------
# Round 17.5 persistence — main_node_reading_repo is injected
# ---------------------------------------------------------------------------
class _FakeMainNodeRepo:
    """Records every save() call. Round-17.5 broker wiring test hook."""

    def __init__(self, return_id: int | None = 42) -> None:
        self.saved: list[Any] = []
        self._return_id = return_id

    async def save(self, reading: Any) -> int | None:
        self.saved.append(reading)
        return self._return_id

    async def latest_for_node(self, main_node_id: str, limit: int) -> list[Any]:
        return []

    async def most_recent(self, main_node_id: str) -> Any | None:
        return None


async def test_v2_master_heartbeat_persists_when_repo_injected() -> None:
    """When Round 17.5's PgMainNodeReadingRepo is wired the heartbeat lands."""
    fake_repo = _FakeMainNodeRepo(return_id=99)

    def parse_heartbeat(_t: str, _r: bytes) -> TelemetryMaster:
        return _make_heartbeat_model(sub_node_online=True)

    broker = IngestBroker(
        _settings(),
        _empty_deps(),
        main_node_reading_repo=fake_repo,
        parse_fn=parse_heartbeat,
        ingest_fn=_ok_ingest,
        max_queue=4,
    )
    broker._loop = asyncio.get_running_loop()
    broker._queue = asyncio.Queue(maxsize=4)
    task = asyncio.create_task(broker._drain())
    broker._enqueue("agro/v2/T/F/AGR-MN-0001/telemetry", b"{}")
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert len(fake_repo.saved) == 1
    row = fake_repo.saved[0]
    assert row.main_node_id == "AGR-MN-0001"
    assert row.sub_node_online is True
    assert row.sub_node_silence_ms == 42_000
    assert row.time_source == "ntp"


async def test_v2_master_heartbeat_duplicate_repo_counts_as_dropped() -> None:
    """Repo returning None (ON CONFLICT) increments the `duplicate` counter."""
    fake_repo = _FakeMainNodeRepo(return_id=None)

    def parse_heartbeat(_t: str, _r: bytes) -> TelemetryMaster:
        return _make_heartbeat_model(sub_node_online=True)

    before = _dropped_count("duplicate")
    broker = IngestBroker(
        _settings(),
        _empty_deps(),
        main_node_reading_repo=fake_repo,
        parse_fn=parse_heartbeat,
        ingest_fn=_ok_ingest,
        max_queue=4,
    )
    broker._loop = asyncio.get_running_loop()
    broker._queue = asyncio.Queue(maxsize=4)
    task = asyncio.create_task(broker._drain())
    broker._enqueue("agro/v2/T/F/AGR-MN-0001/telemetry", b"{}")
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    after = _dropped_count("duplicate")
    assert after == pytest.approx(before + 1)


def test_normalize_clock_skew_replaces_impossible_future_timestamp() -> None:
    reading = _reading().with_(
        recorded_at=datetime(2070, 1, 1, 1, 3, 6, tzinfo=UTC),
        received_at_master=datetime(2070, 1, 1, 1, 3, 6, tzinfo=UTC),
    )
    now = datetime(2026, 8, 27, 4, 10, tzinfo=UTC)

    normalized = _normalize_clock_skew(reading, now=now)

    assert normalized.recorded_at == now
    assert normalized.received_at_master == now
    assert normalized.validation_warn is True
    assert normalized.sensor_health_json["timestamp_corrected"] is True
    assert normalized.sensor_health_json["timestamp_correction_reason"] == "future_clock_skew"
    assert normalized.sensor_health_json["original_recorded_at"] == "2070-01-01T01:03:06+00:00"


def test_normalize_clock_skew_replaces_impossible_past_timestamp() -> None:
    """Uninitialised RTCs commonly boot to year 2000 or the 1970 epoch.

    ``MAX_CLOCK_SKEW_PAST`` = 365 days: anything older is treated as clock
    skew and rewritten to server UTC. The audit trail records
    ``past_clock_skew`` so ops can distinguish this from a firmware future
    clock like 2070.
    """
    reading = _reading().with_(
        recorded_at=datetime(2000, 1, 1, 0, 0, 0, tzinfo=UTC),
        received_at_master=datetime(2000, 1, 1, 0, 0, 0, tzinfo=UTC),
    )
    now = datetime(2026, 8, 27, 4, 10, tzinfo=UTC)

    normalized = _normalize_clock_skew(reading, now=now)

    assert normalized.recorded_at == now
    assert normalized.received_at_master == now
    assert normalized.validation_warn is True
    assert normalized.sensor_health_json["timestamp_corrected"] is True
    assert normalized.sensor_health_json["timestamp_correction_reason"] == "past_clock_skew"
    assert normalized.sensor_health_json["original_recorded_at"] == "2000-01-01T00:00:00+00:00"


def test_normalize_clock_skew_leaves_valid_timestamps_untouched() -> None:
    """Happy path: a fresh reading within the skew window passes through unchanged.

    Guards against a regression that inverts the ``too_future or too_old``
    branch and starts rewriting every timestamp.
    """
    original_recorded_at = datetime(2026, 8, 27, 4, 5, 0, tzinfo=UTC)
    original_received_at = datetime(2026, 8, 27, 4, 5, 1, tzinfo=UTC)
    reading = _reading().with_(
        recorded_at=original_recorded_at,
        received_at_master=original_received_at,
    )
    now = datetime(2026, 8, 27, 4, 10, tzinfo=UTC)

    normalized = _normalize_clock_skew(reading, now=now)

    assert normalized is reading   # frozen dataclass; no copy needed
    assert normalized.recorded_at == original_recorded_at
    assert normalized.received_at_master == original_received_at
    assert normalized.validation_warn is False
    assert "timestamp_corrected" not in normalized.sensor_health_json


# ===========================================================================
# Queue-full handling
# ===========================================================================
async def test_enqueue_drops_when_queue_full() -> None:
    broker = IngestBroker(
        _settings(),
        _empty_deps(),
        parse_fn=_ok_parse,
        ingest_fn=_ok_ingest,
        max_queue=1,
    )
    broker._loop = asyncio.get_running_loop()
    broker._queue = asyncio.Queue(maxsize=1)


    before = _dropped_count("queue_full")
    broker._enqueue("agro/v2/p/f/n/telemetry", b"a")
    # Queue is now full; second enqueue without a drain in between must drop.
    broker._enqueue("agro/v2/p/f/n/telemetry", b"b")
    after = _dropped_count("queue_full")
    assert after == pytest.approx(before + 1)




# ===========================================================================
# Lifecycle guards
# ===========================================================================
async def test_start_schedules_nonblocking_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.connect_async_args: tuple[str, int, int] | None = None
            self.loop_started = False
            self.loop_stopped = False
            self.disconnected = False

        def username_pw_set(self, username: str, password: str | None) -> None:
            self.username = username
            self.password = password

        def tls_set_context(self, ctx: object) -> None:
            self.tls_context = ctx

        def connect(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("start() must not block on client.connect()")

        def connect_async(self, host: str, port: int, keepalive: int) -> None:
            self.connect_async_args = (host, port, keepalive)

        def loop_start(self) -> None:
            self.loop_started = True

        def loop_stop(self) -> None:
            self.loop_stopped = True

        def disconnect(self) -> None:
            self.disconnected = True

    monkeypatch.setattr(broker_module.mqtt, "Client", FakeClient)

    broker = IngestBroker(BrokerSettings(host="mosquitto", port=1883), _empty_deps())
    await broker.start()

    client = broker._client
    assert isinstance(client, FakeClient)
    assert client.connect_async_args == ("mosquitto", 1883, 60)
    assert client.loop_started is True

    await broker.stop()
    assert client.loop_stopped is True
    assert client.disconnected is True


async def test_start_raises_when_already_started() -> None:
    broker = IngestBroker(_settings(), _empty_deps())
    # We can't actually .start() without a real broker, but the duplicate-
    # start check fires on the second call's first line ("if self._client
    # is not None"). Simulate the "already started" state by injecting.
    broker._client = MagicMock()  # type: ignore[assignment]
    with pytest.raises(RuntimeError, match="already started"):
        await broker.start()




async def test_stop_is_idempotent() -> None:
    broker = IngestBroker(_settings(), _empty_deps())
    # Fresh broker; stop() should be a no-op (everything is None).
    await broker.stop()
    await broker.stop()




# ===========================================================================
# Constants - protect against accidental edits
# ===========================================================================
def test_telemetry_topic_filter_uses_multilevel_wildcards() -> None:
    assert TELEMETRY_TOPIC_FILTER == "agro/v2/+/+/+/telemetry"




def test_qos_default_is_at_least_once() -> None:
    assert QOS_AT_LEAST_ONCE == 1




def test_max_queue_is_a_reasonable_size() -> None:
    # Floor: 1000 messages of buffer. Ceiling: 100k would mean we're
    # papering over a real slow-consumer problem. Sanity-check the
    # constant doesn't drift wildly.
    assert 1000 <= MAX_QUEUE <= 100_000
