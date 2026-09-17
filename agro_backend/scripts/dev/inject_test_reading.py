#!/usr/bin/env python3
"""Inject ONE guaranteed-alert telemetry reading — end-to-end test without hardware.

Publishes a single Sub Node telemetry frame with a deliberately low soil-moisture
value (default 8%, well under the pilot target) to the MQTT broker. That drives the
whole live pipeline exactly as real hardware would:

    this publish
      -> ingest worker writes node_sensor_readings
      -> evaluate_rules fires a LOW_WATER alert + NOTIFY agro_events
      -> advisory_subscriber composes a Marathi advisory via Claude -> ai_suggestions
      -> delivery_subscriber sends the WhatsApp template (if Meta creds are set)

Unlike ``fake_main_node.py`` (a random-walk stream that only *sometimes* breaches a
threshold), this fires a specific alert on demand, once.

The broker has no host port on the prod/staging compose, so run this INSIDE the
docker network — from the ``app`` container, which already has paho + the broker
credentials in its environment::

    # from the compose dir on the VPS, after seeding pilot data:
    docker compose -f docker-compose.prod.yml cp \\
        scripts/dev/inject_test_reading.py app:/tmp/inject_test_reading.py
    docker compose -f docker-compose.prod.yml exec app python /tmp/inject_test_reading.py

Broker host/user/password default to the app container's MQTT_BROKER_* env vars.
Identity args default to the fixed UUIDs that scripts/dev/seed_pilot.py creates, so
with a default seed you can run it with no arguments.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import UTC, datetime

import paho.mqtt.client as mqtt

SCHEMA_TELEMETRY_V2 = "agro-guardian/telemetry/v2"

# Defaults match scripts/dev/seed_pilot.py so a default seed needs no args.
DEFAULT_TENANT = "11111111-1111-1111-1111-111111111111"
DEFAULT_FARMER = "aaaaaaaa-1111-1111-1111-111111111111"
DEFAULT_FARM = "bbbbbbbb-2222-2222-2222-222222222222"
DEFAULT_PLOT = "PLOT_PILOT_001"
DEFAULT_NODE = "AGR-SN-0001"


def _build_payload(args: argparse.Namespace) -> dict[str, object]:
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    moisture = round(args.moisture, 2)
    # Only fields that exist on SubNodeTelemetryV2 (the schema forbids extras).
    # soil_moisture_avg_pct is the field the LOW_WATER rule reads.
    return {
        "$schema": SCHEMA_TELEMETRY_V2,
        "tenant_id": args.tenant_id,
        "farmer_id": args.farmer_id,
        "farm_id": args.farm_id,
        "plot_id": args.plot_id,
        "node_id": args.node_id,
        "recorded_at": now,
        "received_at_master": now,
        "transmission_type": "lora",
        "battery_voltage_v": round(args.battery, 3),
        "soil_moisture_1_pct": moisture,
        "soil_moisture_2_pct": moisture,
        "soil_moisture_avg_pct": moisture,
        "soil_temp_rootzone_c": 24.0,
        "soil_ph": 6.7,
        "soil_ec_ms_cm": 0.45,
    }


def _topic(tenant_id: str, farm_id: str, node_id: str) -> str:
    return f"agro/v2/{tenant_id}/{farm_id}/{node_id}/telemetry"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--moisture",
        type=float,
        default=8.0,
        help="soil_moisture_avg_pct (default 8.0 → LOW_WATER)",
    )
    p.add_argument(
        "--battery",
        type=float,
        default=3.90,
        help="battery_voltage_v (default 3.90, above low threshold)",
    )
    p.add_argument("--tenant-id", default=DEFAULT_TENANT)
    p.add_argument("--farmer-id", default=DEFAULT_FARMER)
    p.add_argument("--farm-id", default=DEFAULT_FARM)
    p.add_argument("--plot-id", default=DEFAULT_PLOT)
    p.add_argument("--node-id", default=DEFAULT_NODE)
    p.add_argument("--broker-host", default=os.environ.get("MQTT_BROKER_HOST", "mosquitto"))
    p.add_argument(
        "--broker-port", type=int, default=int(os.environ.get("MQTT_BROKER_PORT", "1883"))
    )
    p.add_argument("--broker-user", default=os.environ.get("MQTT_BROKER_USER", "service"))
    p.add_argument("--broker-pass", default=os.environ.get("MQTT_BROKER_PASSWORD", ""))
    args = p.parse_args(sys.argv[1:] if argv is None else argv)

    payload = _build_payload(args)
    topic = _topic(args.tenant_id, args.farm_id, args.node_id)

    client = mqtt.Client(
        client_id=f"inject-test-{uuid.uuid4().hex[:8]}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )
    if args.broker_user:
        client.username_pw_set(args.broker_user, args.broker_pass or "")
    client.connect(args.broker_host, args.broker_port, keepalive=30)
    client.loop_start()
    info = client.publish(topic, json.dumps(payload), qos=1)
    info.wait_for_publish(timeout=10)
    client.loop_stop()
    client.disconnect()

    print(f"published to {topic}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(
        f"\nOK — moisture={args.moisture}% should fire a LOW_WATER alert on {args.plot_id}. "
        "Watch: docker compose -f docker-compose.prod.yml logs -f app | "
        "grep -E 'ingest|alert|advisory|delivery'"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
