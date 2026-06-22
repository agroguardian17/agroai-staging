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


import paho.mqtt.client as mqtt
import structlog
from pydantic import ValidationError


from app.application.process_reading import ProcessReadingDeps
from app.application.process_reading import execute as process_execute
from app.infra.mqtt.schemas import (
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


        client.connect(self._settings.host, self._settings.port, self._settings.keepalive_seconds)
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
                reading = model.to_domain()  # type: ignore[attr-defined]
                result = await self._ingest_fn(reading, self._deps)
                if result.reading_id is None:  # type: ignore[attr-defined]
                    metrics.ingest_dropped_total.labels(reason="duplicate").inc()
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
            except Exception:
                # Catch-all so the drain loop never dies. Re-raise inside
                # CancelledError so :meth:`stop` can still cancel us.
                metrics.ingest_dropped_total.labels(reason="unexpected").inc()
                log.exception("ingest_broker.unexpected_error", topic=topic)




def _topic_template(topic: str) -> str:
    """Reduce a concrete topic to its template for low-cardinality metrics.


    ``agro/v2/pilot/F_001/N_001/telemetry`` -> ``agro/v2/+/+/+/telemetry``.
    Prevents the Prometheus label explosion at >100 farms.
    """
    parts = topic.split("/")
    if len(parts) == 6 and parts[0] == "agro" and parts[1] == "v2":
        return f"{parts[0]}/{parts[1]}/+/+/+/{parts[5]}"
    return "other"




__all__ = [
    "MAX_QUEUE",
    "QOS_AT_LEAST_ONCE",
    "TELEMETRY_TOPIC_FILTER",
    "BrokerSettings",
    "IngestBroker",
]
