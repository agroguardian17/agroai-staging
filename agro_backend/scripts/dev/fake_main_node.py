#!/usr/bin/env python3
"""Synthetic Main Node publisher for Day-6 of the Fast Path.


Publishes a stream of plausible telemetry JSON to the local Mosquitto
broker so the Round 7 ingest worker has something to chew on without
real hardware. Mirrors the real Sub Node cadence and field set.


Usage::


    python scripts/dev/fake_main_node.py \\
        --tenant-id 11111111-1111-1111-1111-111111111111 \\
        --farmer-id <farmer-uuid> \\
        --farm-id <farm-uuid> \\
        --plot-id PLOT_AUR_001_Z1 \\
        --node-id AGR-MH-0001 \\
        --rate 1.0 \\
        --duration 60


All identity arguments are required because the ingest pipeline writes
into ``node_sensor_readings`` which has hard FK constraints. Seed those
rows first with the same fixture helpers used in
``tests/infra/persistence/test_pg_reading_repo.py``, OR provide IDs
that already exist in your local DB.


Cadence:
* ``--rate`` is messages per second per node (default 1.0).
* The publisher walks through CadenceMode values across the run so the
  downstream metrics show all modes exercised.


Values are drawn from a stable random walk so adjacent readings look
realistic (no jumps from moisture=15 to moisture=85 in one cycle).
"""


from __future__ import annotations


import argparse
import asyncio
import contextlib
import json
import random
import signal
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


import paho.mqtt.client as mqtt


DEFAULT_BROKER_HOST = "localhost"
DEFAULT_BROKER_PORT = 1883  # the dev compose's plain listener
SCHEMA_TELEMETRY_V2 = "agro-guardian/telemetry/v2"


CADENCE_MODES = ("normal", "rapid", "low_power", "storm", "maintenance")




@dataclass
class _SensorState:
    """Random-walk state for one node so adjacent samples are correlated."""


    soil_moisture_1: float = 35.0
    soil_moisture_2: float = 36.0
    soil_temp_root: float = 24.0
    soil_ph: float = 6.7
    soil_ec: float = 0.45
    battery_v: float = 3.55
    seq: int = 0
    last_cadence_swap: int = 0
    cadence: str = "normal"
    rng: random.Random = field(default_factory=random.Random)




def _step(state: _SensorState) -> None:
    """Advance the random walk by one tick."""
    state.seq += 1
    state.soil_moisture_1 = _bounded(state.soil_moisture_1 + state.rng.gauss(0, 0.6), 5, 60)
    # Probe 2 tracks probe 1 with a small offset.
    drift = state.rng.gauss(0, 0.3)
    state.soil_moisture_2 = _bounded(state.soil_moisture_1 + drift + 0.5, 5, 60)
    state.soil_temp_root = _bounded(state.soil_temp_root + state.rng.gauss(0, 0.1), 18, 32)
    state.soil_ph = _bounded(state.soil_ph + state.rng.gauss(0, 0.02), 5.5, 8.0)
    state.soil_ec = _bounded(state.soil_ec + state.rng.gauss(0, 0.01), 0.1, 1.5)
    state.battery_v = _bounded(state.battery_v - 0.0005, 2.9, 4.2)  # slow drain
    # Switch cadence mode every ~30 ticks for visible variation in metrics.
    if state.seq - state.last_cadence_swap > 30:
        state.cadence = state.rng.choice(CADENCE_MODES)
        state.last_cadence_swap = state.seq




def _bounded(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))




def _build_payload(
    *,
    tenant_id: str,
    farmer_id: str,
    farm_id: str,
    plot_id: str,
    node_id: str,
    state: _SensorState,
) -> dict[str, object]:
    now = datetime.now(UTC)
    # Round to whole second to make idempotency tests less flaky.
    now = now.replace(microsecond=0)
    avg = round((state.soil_moisture_1 + state.soil_moisture_2) / 2, 2)
    low_batt = state.battery_v < 3.30
    return {
        "$schema": SCHEMA_TELEMETRY_V2,
        "tenant_id": tenant_id,
        "farmer_id": farmer_id,
        "farm_id": farm_id,
        "plot_id": plot_id,
        "node_id": node_id,
        "recorded_at": now.isoformat(),
        "received_at_master": now.isoformat(),
        "transmission_type": "lora",
        "signal_rssi_dbm": -60 + state.rng.randint(-15, 5),
        "battery_voltage_v": round(state.battery_v, 3),
        "battery_percent": round((state.battery_v - 2.9) / (4.2 - 2.9) * 100, 1),
        "low_battery_flag": low_batt,
        "soil_moisture_1_pct": round(state.soil_moisture_1, 2),
        "soil_moisture_2_pct": round(state.soil_moisture_2, 2),
        "soil_moisture_avg_pct": avg,
        "soil_temp_rootzone_c": round(state.soil_temp_root, 2),
        "soil_ph": round(state.soil_ph, 2),
        "soil_ec_ms_cm": round(state.soil_ec, 2),
        "soil_n_mg_kg": 100 + state.rng.randint(-20, 20),
        "soil_p_mg_kg": 50 + state.rng.randint(-15, 15),
        "soil_k_mg_kg": 80 + state.rng.randint(-15, 15),
        "cadence_mode": state.cadence,
        "firmware_version": "sub-node-1.0.0+fake",
    }




def _topic(tenant_id: str, farm_id: str, node_id: str) -> str:
    return f"agro/v2/{tenant_id}/{farm_id}/{node_id}/telemetry"




async def run(args: argparse.Namespace) -> int:
    state = _SensorState(rng=random.Random(args.seed) if args.seed else random.Random())
    client = mqtt.Client(
        client_id=f"fake-main-node-{uuid.uuid4().hex[:8]}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    if args.broker_user:
        client.username_pw_set(args.broker_user, args.broker_pass or "")
    client.connect(args.broker_host, args.broker_port, keepalive=60)
    client.loop_start()


    topic = _topic(args.tenant_id, args.farm_id, args.node_id)
    period = 1.0 / args.rate
    deadline = None if args.duration <= 0 else asyncio.get_running_loop().time() + args.duration
    sent = 0
    stop = asyncio.Event()


    def _on_signal(*_: object) -> None:
        stop.set()


    asyncio.get_running_loop().add_signal_handler(signal.SIGINT, _on_signal)
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, _on_signal)


    try:
        while not stop.is_set():
            if deadline is not None and asyncio.get_running_loop().time() >= deadline:
                break
            _step(state)
            payload = _build_payload(
                tenant_id=args.tenant_id,
                farmer_id=args.farmer_id,
                farm_id=args.farm_id,
                plot_id=args.plot_id,
                node_id=args.node_id,
                state=state,
            )
            client.publish(topic, json.dumps(payload), qos=1)
            sent += 1
            if sent % 10 == 0:
                print(
                    f"[{sent:>5}] mode={state.cadence:<11} "
                    f"moisture={payload['soil_moisture_avg_pct']:.1f} "
                    f"battery={payload['battery_voltage_v']:.2f}V"
                )
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=period)
    finally:
        client.loop_stop()
        client.disconnect()
    print(f"fake_main_node: sent {sent} messages to {topic}")
    return 0




def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Synthetic Sub Node telemetry publisher for AgroGuardian.",
    )
    p.add_argument(
        "--tenant-id",
        default="11111111-1111-1111-1111-111111111111",
        help="Pilot tenant by default; override to test multi-tenant flows.",
    )
    p.add_argument("--farmer-id", required=True, help="Existing farmer UUID")
    p.add_argument("--farm-id", required=True, help="Existing farm UUID")
    p.add_argument("--plot-id", required=True, help="Existing plot string id")
    p.add_argument("--node-id", required=True, help="Existing device id")
    p.add_argument("--rate", type=float, default=1.0, help="Messages per second")
    p.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Total seconds to run (0 = until SIGINT)",
    )
    p.add_argument("--broker-host", default=DEFAULT_BROKER_HOST)
    p.add_argument("--broker-port", type=int, default=DEFAULT_BROKER_PORT)
    p.add_argument("--broker-user", default=None)
    p.add_argument("--broker-pass", default=None)
    p.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible runs (default: time-based)",
    )
    return p.parse_args(argv)




def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    return asyncio.run(run(args))




if __name__ == "__main__":
    raise SystemExit(main())
