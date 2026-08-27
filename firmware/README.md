# AgroGuardian V2 — Firmware

Full firmware for the pilot's two field devices. Together they take a
sensor reading in the ground and land it as a JSON row in Postgres.

```
[Sub Node]  raw sensors → LoRa 433 MHz CSV
       │
       ▼
[Main Node] parses CSV → adds own weather-station readings → JSON
       │  MQTT-TLS via A7672S 4G modem (Airtel)
       ▼
mqtts-13-207-20-67.sslip.io:8883
       │
       ▼
[Caddy caddy-l4] TLS terminate → Mosquitto :1883
       │
       ▼
[FastAPI IngestBroker] validates + writes node_sensor_readings
```

**Design principle:** all calibration happens server-side. Firmware sends
raw sensor outputs — raw ADC counts, pulse counts, Modbus register
values. This keeps firmware simple, keeps calibration data centralised,
and lets us tune per-device offsets without reflashing hardware.

## Pilot device roster (as of 2026-08-26)

| Device | ID | Notes |
|---|---|---|
| Main Node | `AGR-MN-0001` | ESP32 + A7672S 4G + LoRa RX + weather station |
| Sub Node | `AGR-SN-0001` | ATmega328P, buried near `PLOT_PILOT_001` |
| (satellite plot) | `PLOT_PILOT_002` | No hardware; ingested via satellite pipeline later |

## Folder layout

```
firmware/
├─ README.md                    ← you are here
├─ sub_node/
│  ├─ sub_node.ino              Full Arduino sketch
│  ├─ sub_node_config.h         Per-board NODE_ID + timings
│  └─ README.md                 Build + flash instructions (Arduino IDE + USBasp)
└─ main_node/
   ├─ platformio.ini            PlatformIO env for ESP32
   ├─ include/
   │  └─ pilot_config.h         MQTT creds, tenant/farm UUIDs, NODE_MAP
   ├─ src/
   │  └─ main.cpp               Full firmware — sensors, modem, MQTT, LoRa
   └─ README.md                 Build + flash instructions (PlatformIO)
```

## End-to-end deployment sequence

Follow this order strictly the first time. Each step's own README has the
detailed commands.

### 1. Verify backend + broker are up

On the Lightsail VPS:

```
docker compose -f docker-compose.prod.yml ps    # all services healthy
mosquitto_sub -h mqtts-13-207-20-67.sslip.io -p 8883 \
    --cafile /etc/ssl/certs/ca-certificates.crt \
    -u main-node-001 -P <password> \
    -t 'agro/v2/#' -v
```

You should see the subscription hang open with no errors. This proves the
Caddy → Mosquitto path works before any device is flashed.

### 2. Provision the MQTT credential

Only needed once per Main Node. On the VPS:

```
bash agro_backend/scripts/dev/provision_mqtt_credential.sh AGR-MN-0001
```

Copy the printed username / password into
`firmware/main_node/include/pilot_config.h`:

```c
#define MQTT_USERNAME "main-node-001"
#define MQTT_PASSWORD "<paste-here>"
```

### 3. Seed the pilot data in Postgres

Only needed once per environment. On the VPS:

```
docker compose -f docker-compose.prod.yml exec app \
    python scripts/dev/seed_pilot.py
```

This creates the tenant, farmer, farm, both plots (`PLOT_PILOT_001`
hardware + `PLOT_PILOT_002` satellite), the Main Node, the Sub Node, and
two Ginger crop seasons. Verify at the end that the printed
`Sub Node 1: AGR-SN-0001 -> PLOT_PILOT_001 (hardware)` line matches
the `NODE_MAP` in `firmware/main_node/include/pilot_config.h`.

### 4. Flash the Sub Node (bench, not in the field yet)

See `firmware/sub_node/README.md` for the detailed Arduino IDE + USBasp
walkthrough. Summary:

1. First time only: **Tools → Burn Bootloader** with MiniCore ATmega328,
   external 8 MHz, BOD 2.7 V, No bootloader, USBasp (slow). This just
   sets the fuses.
2. Edit `sub_node_config.h::NODE_ID` to the string this board will carry
   (`"AGR-SN-0001"` for the pilot).
3. **Sketch → Upload Using Programmer** (Ctrl+Shift+U).
4. Open Serial Monitor @ **9600 baud**. Confirm the startup banner and
   the first cycle prints within ~15 seconds.

### 5. IRLZ44N gate polarity multimeter check

The one open hardware question. Do this before burying the Sub Node:

- Connect the multimeter across the NPK 12 V rail (MT3608 output).
- Watch serial for `NPK: powered ON`.
- Multimeter should read ~12 V during the 10 s stabilization window and
  drop back to ~0 V after `NPK: powered OFF`.

If the multimeter shows the opposite polarity (12 V when firmware reports
"OFF"), the IRLZ44N is wired backwards — swap the source/drain terminals
and re-run.

### 6. Flash the Main Node (bench, next to Sub Node)

See `firmware/main_node/README.md` for the PlatformIO walkthrough.
Summary:

1. `cd firmware/main_node`.
2. Confirm `include/pilot_config.h` has the correct `MQTT_HOST`, credentials,
   `PILOT_TENANT_ID` / `FARM_ID` / `FARMER_ID`, `MODEM_APN`, and
   `NODE_MAP`.
3. `pio run -t upload && pio device monitor -b 115200`.
4. Confirm the boot log:
   - I2C scan finds 0x40 (INA219), 0x68 (DS3231), 0x76 or 0x77 (BME280).
   - `[bme]`, `[ina]`, `[rtc]`, `[sd]`, `[lora]` all say OK.
   - Modem sequence prints `+CMQTTCONNECT: 0,0`.
   - Final `SETUP COMPLETE — waiting for LoRa packets` banner.

### 7. Bench end-to-end verification

With both boards powered and physically near each other:

- Every ~5 minutes the Sub Node serial shows a new cycle and `LoRa TX: OK`.
- Within a second the Main Node serial shows `[lora] RX (…): NODE=AGR-SN-0001,…`
  followed by `[mqtt] publish OK`.
- On the VPS, `python agro_backend/scripts/dev/tail_ingest.py` shows the
  incoming reading being validated and either accepted (once the backend
  raw-schema is live) or logged as an unknown-schema message (until then).
- Query Postgres to see the row land:

```sql
SELECT recorded_at, node_id, plot_id, raw_readings, master_readings
FROM node_sensor_readings
WHERE plot_id = 'PLOT_PILOT_001'
ORDER BY recorded_at DESC
LIMIT 5;
```

(Column names above assume the backend has been extended for the raw
schema — see §Backend follow-up below.)

### 8. Bury the Sub Node + field-mount the Main Node

Same firmware, no changes needed. Confirm again after installation that
Main Node serial shows steady `[lora] RX` and `[mqtt] publish OK` at the
expected cadence.

## Backend follow-up (required before this firmware is fully useful)

The current backend `TelemetryIn` schema
(`agro_backend/app/infra/mqtt/schemas.py`) uses `extra="forbid"` and
expects pre-calibrated fields (`soil_moisture_avg_pct`,
`water_flow_lpm`, `water_pressure_bar`). This firmware sends the **raw
variant** instead — `$schema = "agro-guardian/telemetry/v2-raw"`, with
`raw_readings` and `master_readings` sub-objects.

The backend needs a small extension before it can consume these:

1. New pydantic schema `TelemetryInRaw` accepting the raw-values payload.
2. Router in `IngestBroker` — pick the schema based on the incoming
   `$schema` value (`v2` → old path, `v2-raw` → new path).
3. Calibration step converting raw ADC → engineering units, stored per
   device in a new table (`device_calibration` — one row per Sub Node
   with `DRY_ADC`, `WET_ADC`, pressure-transducer curve, battery divider
   ratio, NPK register divisors).
4. `weather_station_readings` writes for the `master_readings` block,
   keyed on `main_node_id`.

That work is roughly one-day scope; file as **Round 16 — Raw-payload
ingestion + calibration table**.

Until Round 16 lands, you can:
- Deploy this firmware anyway; Mosquitto will accept + queue the messages.
- Watch them on the VPS with `mosquitto_sub -t 'agro/v2/#' -v` and hand-verify.
- Compare against the Sub Node's serial log to check the LoRa hop is
  lossless.

## Common questions

**Q: Where does `plot_id` come from? The Sub Node doesn't know its plot.**
A: The Main Node keeps a `NODE_MAP` (in `pilot_config.h`) that translates
`NODE_ID → PLOT_ID`. For scale-out to more plots, just add rows there and
reflash the Main Node.

**Q: Why doesn't the Sub Node send its own timestamp?**
A: ATmega328P has no accurate real-time clock and no NTP link. Timestamp
is added at the Main Node (which has DS3231 + modem NTP). The LoRa hop
is well under a second, so this loses no meaningful precision.

**Q: Why raw values instead of engineering units?**
A: So we can update calibration constants (soil dry/wet ADC baselines,
pressure transducer curve, battery divider ratio) from the backend
without reflashing hardware. See "Backend follow-up" above.

**Q: What if I add a second Sub Node later?**
A: Two changes: (1) extend `NODE_MAP` in `firmware/main_node/include/pilot_config.h`
and reflash the Main Node; (2) add a `NODE=<id>,` line to the Sub Node
LoRa payload — the current sketch already does this from
`sub_node_config.h::NODE_ID`, so just flash each board with a unique
value.

**Q: Does the Main Node buffer to SD when offline?**
A: Not yet. The `SD.begin()` is called and verified at boot, but no
offline queue is implemented. If the modem drops the MQTT link, Sub Node
frames received during the outage are lost. This is a Round 17-ish
future improvement.

## References

- Backend project skill: `agroguardian-context` (single source of truth for
  the whole platform).
- MQTT wire contract: `agro_backend/docs/HARDWARE_WIRE_CONTRACT.md`.
- Server-side TLS fix: `agro_backend/deploy/caddy/Caddyfile.prod` +
  agroguardian-context skill §17.
- Provisioning script: `agro_backend/scripts/dev/provision_mqtt_credential.sh`.
- Seed data: `agro_backend/scripts/dev/seed_pilot.py`.
