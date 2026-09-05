"""MQTT subscriber that drives the ingest use case.


Bridges paho-mqtt (thread-based callback model) to asyncio (the use case
is async). The bridge is intentionally small:


1. paho's ``on_message`` callback (running on paho's I/O thread) drops
   the (topic, payload) tuple into an :class:`asyncio.Queue` via
   ``loop.call_soon_threadsafe``.
2. A long-lived asyncio task (the "drain loop") pulls from the queue,
   parses the payload, builds a Reading, and calls
   :func:`app.application.ingest_telemetry.execute`.
3. Every drop is metered with a reason label
   (``parse_error|unknown_topic|validation|duplicate|unexpected``).


Why this shape rather than a fully-async MQTT client (aiomqtt etc.):


* paho-mqtt is the most battle-tested MQTT client in the Python ecosystem.
* The thread-to-asyncio bridge is ~30 lines, well-isolated here in infra.
* aiomqtt has had multiple breaking changes; pinning paho is calmer.
* The Round-7 ingest worker is the ONLY place this thread/event-loop
  bridge exists in the codebase.


Queue full handling: the bounded asyncio.Queue rejects new messages once
``MAX_QUEUE`` is reached. We drop with metric rather than block paho's
thread - blocking would back-pressure into MQTT broker disk eventually,
which is the broker's job to surface (its own queue overflow alarms),
not ours to silently retry.
"""


from __future__ import annotations

import asyncio
import contextlib
import logging
import ssl
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import paho.mqtt.client as mqtt
import structlog
from pydantic import ValidationError

from app.application.ports.device_calibration_repo import DeviceCalibrationRepo
from app.application.ports.main_node_reading_repo import MainNodeReadingRepo
from app.application.process_reading import ProcessReadingDeps
from app.application.process_reading import execute as process_execute
from app.domain.main_node_reading import MainNodeReading
from app.infra.mqtt.schemas import (
    TelemetryInRaw,
    TelemetryMaster,
    TopicParseError,
    UnknownTopicKindError,
    parse_inbound,
)
from app.lib import metrics

log = structlog.get_logger(__name__)




# Asyncio queue depth. ~10k msg/min sustained throughput would still
# leave us with 30 seconds of cushion at this depth; if we hit the cap
# we're falling behind and need to scale (Roadmap Part 12.4).
MAX_QUEUE: int = 5000


# Topic filter the broker subscribes to. Multi-level wildcards keep the
# subscription unchanged when we add tenants / farms / nodes.
TELEMETRY_TOPIC_FILTER: str = "agro/v2/+/+/+/telemetry"


QOS_AT_LEAST_ONCE: int = 1
MAX_CLOCK_SKEW_FUTURE: timedelta = timedelta(days=1)
MAX_CLOCK_SKEW_PAST: timedelta = timedelta(days=365)




@dataclass(frozen=True, slots=True)
class BrokerSettings:
    """Connection parameters for the MQTT broker.


    Constructed from ``app.config.Settings`` at startup. Frozen so a
    badly-behaved caller can't mutate the broker mid-flight.
    """


    host: str
    port: int
    username: str | None = None
    password: str | None = None
    client_id: str = "agro-backend-ingest"
    use_tls: bool = False
    tls_ca_path: str | None = None
    keepalive_seconds: int = 60




class IngestBroker:
    """Subscribe to MQTT telemetry, drive the ingest use case.


    Lifecycle:


    * :meth:`start` connects, subscribes, starts paho's network loop in
      a thread, and launches the asyncio drain task. Must be called from
      an asyncio context (FastAPI's lifespan hook supplies one).
    * :meth:`stop` cancels the drain task, calls ``loop_stop``, and
      disconnects. Idempotent.


    Errors during ingest are caught and metered; the drain loop never
    dies on a bad message (broker would block, broker disk would fill,
    pager goes off). Only an asyncio.CancelledError stops the loop -
    which is exactly what :meth:`stop` raises by cancelling the task.
    """


    def __init__(
        self,
        broker_settings: BrokerSettings,
        deps: ProcessReadingDeps,
        *,
        # Round 16: when a `$schema=agro-guardian/telemetry/v2-raw` payload
        # arrives, the broker fetches per-device calibration constants from
        # this repo and applies them via TelemetryInRaw.to_domain(cal).
        # Injecting via keyword keeps back-compat with Round 7 tests that
        # don't need the raw path.
        calibration_repo: DeviceCalibrationRepo | None = None,
        # Round 17.5 (2026-08-27 v2 firmware): when a `$schema=agro-guardian/
        # telemetry/v2-master` heartbeat arrives, the broker persists it via
        # this repo. Optional — if None, the heartbeat is still metered +
        # logged (the pre-17.5 behaviour), just not persisted. Keeps every
        # existing test working without touching their broker construction.
        main_node_reading_repo: MainNodeReadingRepo | None = None,
        # Test seam: allow callers to inject a fake parser/processor for
        # unit tests. Production callers always use the module defaults.
        # ``ingest_fn`` keeps its historical name (Round 7) for backward
        # compatibility but now defaults to ``process_reading.execute`` —
        # which calls ``ingest_telemetry`` then ``evaluate_rules``.
        parse_fn: Callable[[str, bytes], object] = parse_inbound,
        ingest_fn: Callable[[object, ProcessReadingDeps], Awaitable[object]] = process_execute,
        max_queue: int = MAX_QUEUE,
    ) -> None:
        self._settings = broker_settings
        self._deps = deps
        self._calibration_repo = calibration_repo
        self._main_node_reading_repo = main_node_reading_repo
        self._parse_fn = parse_fn
        self._ingest_fn = ingest_fn
        self._max_queue = max_queue


        self._client: mqtt.Client | None = None
        self._queue: asyncio.Queue[tuple[str, bytes]] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._drain_task: asyncio.Task[None] | None = None


    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self) -> None:
        """Connect, subscribe, kick off the network + drain loops."""
        if self._client is not None:
            raise RuntimeError("IngestBroker already started")
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=self._max_queue)


        client = mqtt.Client(
            client_id=self._settings.client_id,
            protocol=mqtt.MQTTv5,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        if self._settings.username:
            client.username_pw_set(self._settings.username, self._settings.password)
        if self._settings.use_tls:
            ctx = ssl.create_default_context(cafile=self._settings.tls_ca_path)
            client.tls_set_context(ctx)


        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect


        # Silence paho-mqtt's noisy "INFO" log; we route everything through
        # structlog so a double log is just noise.
        mqtt_paho_logger = logging.getLogger("paho.mqtt.client")
        mqtt_paho_logger.setLevel(logging.WARNING)


        # Schedule the first connection without resolving the broker hostname on
        # the FastAPI startup path. The paho network thread will keep retrying
        # if Mosquitto is temporarily absent during local development.
        client.connect_async(
            self._settings.host,
            self._settings.port,
            self._settings.keepalive_seconds,
        )
        # Background thread runs the network loop; on_message fires from there.
        client.loop_start()
        self._client = client


        # Drain task pulls from the queue and ingests on the asyncio loop.
        self._drain_task = asyncio.create_task(self._drain(), name="ingest-drain")
        log.info("ingest_broker.started", host=self._settings.host, port=self._settings.port)


    async def stop(self) -> None:
        """Disconnect cleanly. Idempotent."""
        if self._drain_task is not None:
            self._drain_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._drain_task
            self._drain_task = None
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
        log.info("ingest_broker.stopped")


    # ------------------------------------------------------------------
    # paho callbacks (run on paho's I/O thread - NOT the asyncio thread)
    # ------------------------------------------------------------------
    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: object,
        _flags: object,
        reason_code: object,
        _properties: object = None,
    ) -> None:
        if getattr(reason_code, "is_failure", False) or (
            isinstance(reason_code, int) and reason_code != 0
        ):
            log.error("ingest_broker.connect_failed", reason=str(reason_code))
            return
        # Re-subscribe on every connect (covers reconnects too).
        client.subscribe(TELEMETRY_TOPIC_FILTER, qos=QOS_AT_LEAST_ONCE)
        log.info("ingest_broker.subscribed", topic=TELEMETRY_TOPIC_FILTER, qos=QOS_AT_LEAST_ONCE)


    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: object,
        _disconnect_flags: object,
        reason_code: object,
        _properties: object = None,
    ) -> None:
        # paho's loop will auto-reconnect; we just log.
        log.warning("ingest_broker.disconnected", reason=str(reason_code))


    def _on_message(self, _client: mqtt.Client, _userdata: object, msg: mqtt.MQTTMessage) -> None:
        """Push to the asyncio queue from the paho thread.


        Uses ``call_soon_threadsafe`` because we're crossing thread
        boundaries: paho's I/O thread -> asyncio's loop thread. Anything
        else risks data races on the Queue's internal state.


        On queue full: drop + meter. Backpressure to the broker would
        come from refusing to ACK QoS-1, which paho only does if it
        runs out of in-flight slots; that's the broker's responsibility
        to surface via its own metrics.
        """
        if self._loop is None or self._queue is None:
            return  # not started; shouldn't happen
        try:
            self._loop.call_soon_threadsafe(self._enqueue, msg.topic, msg.payload)
        except RuntimeError:
            # Loop already closed during shutdown - drop quietly.
            metrics.ingest_dropped_total.labels(reason="loop_closed").inc()


    def _enqueue(self, topic: str, raw: bytes) -> None:
        """Inner method invoked on the asyncio loop thread."""
        if self._queue is None:
            return
        try:
            self._queue.put_nowait((topic, raw))
            metrics.ingest_queue_depth.set(self._queue.qsize())
        except asyncio.QueueFull:
            metrics.ingest_dropped_total.labels(reason="queue_full").inc()
            log.warning("ingest_broker.queue_full", topic=topic)


    # ------------------------------------------------------------------
    # Drain loop
    # ------------------------------------------------------------------
    async def _drain(self) -> None:
        """Pull messages off the queue and run them through the ingest pipeline.


        Each iteration is in its own try/except so a bad message can never
        kill the loop. Drops are metered with a label that maps 1:1 to the
        exception type (parse_error, unknown_topic, validation, duplicate,
        unexpected).
        """
        assert self._queue is not None
        while True:
            topic, raw = await self._queue.get()
            metrics.ingest_queue_depth.set(self._queue.qsize())
            metrics.ingest_received_total.labels(topic=_topic_template(topic)).inc()
            try:
                model = self._parse_fn(topic, raw)
                if isinstance(model, TelemetryMaster):
                    # 2026-08-27 v2 Main Node master-only heartbeat.
                    # Meter + log always. Persist when the Round 17.5 repo
                    # is wired (migration 0013 landed and ingest_startup
                    # constructs a PgMainNodeReadingRepo). Tests that don't
                    # inject the repo still see identical behaviour to the
                    # pre-17.5 log-only path.
                    online_label = (
                        "true" if model.master_readings.sub_node_online else "false"
                    )
                    metrics.main_node_heartbeat_total.labels(
                        sub_node_online=online_label
                    ).inc()
                    log.info(
                        "ingest_broker.master_heartbeat",
                        topic=topic,
                        main_node_id=model.main_node_id,
                        sub_node_online=model.master_readings.sub_node_online,
                        sub_node_silence_ms=model.master_readings.sub_node_silence_ms,
                        time_source=model.master_readings.time_source,
                    )
                    if self._main_node_reading_repo is not None:
                        mr = model.master_readings
                        heartbeat = MainNodeReading(
                            tenant_id=model.tenant_id,
                            farm_id=model.farm_id,
                            main_node_id=model.main_node_id,
                            recorded_at=model.recorded_at,
                            received_at_master=model.received_at_master,
                            time_source=mr.time_source,
                            sub_node_online=mr.sub_node_online,
                            sub_node_silence_ms=mr.sub_node_silence_ms,
                            bme280_temp_c=mr.bme280_temp_c,
                            bme280_humidity_pct=mr.bme280_humidity_pct,
                            bme280_pressure_pa=mr.bme280_pressure_pa,
                            ina219_bus_v=mr.ina219_bus_v,
                            ina219_current_ma=mr.ina219_current_ma,
                            rain_pulses_window=mr.rain_pulses_window,
                            wind_pulses_window=mr.wind_pulses_window,
                            wind_dir_adc=mr.wind_dir_adc,
                            firmware_version=model.firmware_version,
                        )
                        # Same broker-side safety net as the Sub Node path:
                        # rewrite impossible device timestamps to server UTC
                        # before the row lands. MainNodeReading has the same
                        # (recorded_at, received_at_master, with_,
                        # sensor_health_json, validation_warn) shape as
                        # Reading, so _normalize_clock_skew works duck-typed.
                        heartbeat = _normalize_clock_skew(heartbeat)  # type: ignore[assignment]
                        reading_id = await self._main_node_reading_repo.save(
                            heartbeat
                        )
                        if reading_id is None:
                            metrics.ingest_dropped_total.labels(
                                reason="duplicate"
                            ).inc()
                            log.info(
                                "ingest_broker.master_heartbeat_duplicate",
                                topic=topic,
                                main_node_id=heartbeat.main_node_id,
                                recorded_at=heartbeat.recorded_at.isoformat(),
                            )
                        else:
                            log.info(
                                "ingest_broker.master_heartbeat_saved",
                                topic=topic,
                                main_node_id=heartbeat.main_node_id,
                                reading_id=reading_id,
                                recorded_at=heartbeat.recorded_at.isoformat(),
                            )
                    continue
                if isinstance(model, TelemetryInRaw):
                    # Round 16: raw-values payload — apply per-device
                    # calibration before building the Reading.
                    if self._calibration_repo is None:
                        metrics.ingest_dropped_total.labels(
                            reason="raw_no_calibration_repo"
                        ).inc()
                        log.error(
                            "ingest_broker.raw_payload_without_calibration_repo",
                            topic=topic,
                            node_id=model.node_id,
                        )
                        continue
                    calibration = await self._calibration_repo.get_by_device(
                        str(model.tenant_id), model.node_id
                    )
                    if calibration is None:
                        metrics.ingest_dropped_total.labels(
                            reason="missing_calibration"
                        ).inc()
                        log.warning(
                            "ingest_broker.missing_calibration",
                            topic=topic,
                            node_id=model.node_id,
                            tenant_id=str(model.tenant_id),
                        )
                        continue
                    reading = model.to_domain(calibration)
                else:
                    reading = model.to_domain()  # type: ignore[attr-defined]
                reading = _normalize_clock_skew(reading)
                result = await self._ingest_fn(reading, self._deps)
                if result.reading_id is None:  # type: ignore[attr-defined]
                    metrics.ingest_dropped_total.labels(reason="duplicate").inc()
                    log.info(
                        "ingest_broker.reading_duplicate",
                        topic=topic,
                        node_id=reading.node_id,
                        recorded_at=reading.recorded_at.isoformat(),
                    )
                else:
                    # Rule-engine accounting. Only fires when the use case
                    # actually ran rule evaluation (ProcessReadingResult);
                    # tests injecting an IngestResult-shaped stub don't
                    # have a ``.rules`` attribute and are skipped here.
                    rules = getattr(result, "rules", None)
                    if rules is not None:
                        metrics.rule_evaluations_total.inc()
                        if rules.hits:
                            metrics.rule_hits_total.inc(rules.hits)
                        if rules.created:
                            metrics.alerts_created_total.inc(rules.created)
                        if rules.cooldown_suppressed:
                            metrics.alerts_cooldown_suppressed_total.inc(rules.cooldown_suppressed)
            except TopicParseError:
                metrics.ingest_dropped_total.labels(reason="topic_parse").inc()
                log.warning("ingest_broker.topic_parse_error", topic=topic)
            except UnknownTopicKindError:
                metrics.ingest_dropped_total.labels(reason="unknown_topic_kind").inc()
                log.info("ingest_broker.unknown_topic_kind", topic=topic)
            except ValidationError as exc:
                metrics.ingest_dropped_total.labels(reason="validation").inc()
                log.warning(
                    "ingest_broker.validation_error",
                    topic=topic,
                    errors=exc.error_count(),
                )
            except (ValueError, KeyError) as exc:
                # parse_inbound -> json.JSONDecodeError (a ValueError subclass)
                # or our own ValueErrors from the SafeDecimal coercer.
                metrics.ingest_dropped_total.labels(reason="parse_error").inc()
                log.warning("ingest_broker.parse_error", topic=topic, exc=str(exc))
            except Exception as exc:
                # Catch-all so the drain loop never dies. Re-raise inside
                # CancelledError so :meth:`stop` can still cancel us.
                metrics.ingest_dropped_total.labels(reason="unexpected").inc()
                log.exception("ingest_broker.unexpected_error", topic=topic, exc=str(exc))




def _topic_template(topic: str) -> str:
    """Reduce a concrete topic to its template for low-cardinality metrics.


    ``agro/v2/pilot/F_001/N_001/telemetry`` -> ``agro/v2/+/+/+/telemetry``.
    Prevents the Prometheus label explosion at >100 farms.
    """
    parts = topic.split("/")
    if len(parts) == 6 and parts[0] == "agro" and parts[1] == "v2":
        return f"{parts[0]}/{parts[1]}/+/+/+/{parts[5]}"
    return "other"


def _normalize_clock_skew(reading: object, *, now: datetime | None = None) -> object:
    """Replace impossible device timestamps with server time.

    Field hardware can briefly boot with a bad RTC/modem time (for example
    2070-01-01). ``node_sensor_readings`` is monthly-partitioned, so such a
    timestamp can miss all existing partitions and make Postgres reject the
    insert. For ingest we prefer a usable row with a validation warning over
    dropping the packet: store the original timestamps in ``sensor_health_json``
    and stamp the row with server UTC time.
    """
    if not hasattr(reading, "recorded_at") or not hasattr(reading, "with_"):
        return reading

    current = now or datetime.now(UTC)
    recorded_at = reading.recorded_at
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=UTC)
    else:
        recorded_at = recorded_at.astimezone(UTC)

    too_future = recorded_at > current + MAX_CLOCK_SKEW_FUTURE
    too_old = recorded_at < current - MAX_CLOCK_SKEW_PAST
    if not (too_future or too_old):
        return reading

    received_at_master = reading.received_at_master
    if received_at_master.tzinfo is None:
        received_at_master = received_at_master.replace(tzinfo=UTC)
    else:
        received_at_master = received_at_master.astimezone(UTC)

    health = dict(getattr(reading, "sensor_health_json", {}))
    health.update(
        {
            "timestamp_corrected": True,
            "timestamp_correction_reason": "future_clock_skew" if too_future else "past_clock_skew",
            "original_recorded_at": recorded_at.isoformat(),
            "original_received_at_master": received_at_master.isoformat(),
        }
    )
    log.warning(
        "ingest_broker.timestamp_corrected",
        device_id=getattr(reading, "node_id", getattr(reading, "main_node_id", "unknown")),
        original_recorded_at=recorded_at.isoformat(),
        corrected_recorded_at=current.isoformat(),
    )
    return reading.with_(
        recorded_at=current,
        received_at_master=current,
        sensor_health_json=health,
        validation_warn=True,
    )




__all__ = [
    "MAX_CLOCK_SKEW_FUTURE",
    "MAX_CLOCK_SKEW_PAST",
    "MAX_QUEUE",
    "QOS_AT_LEAST_ONCE",
    "TELEMETRY_TOPIC_FILTER",
    "BrokerSettings",
    "IngestBroker",
    "_normalize_clock_skew",
]
