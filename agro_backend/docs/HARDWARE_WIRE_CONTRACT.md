# AgroGuardian Hardware Wire Contract


> **Audience:** Main Node firmware engineers.
> **Truth source:** `app/infra/mqtt/schemas.py::TelemetryIn`.
> If this doc and the code disagree, the code wins — update the doc.


## 0. Hardware revision notes


- **2026-08-05 — NPK power switch:** the Sub Node's RS485/NPK 12 V rail is switched by an **IRLZ44N** N-channel MOSFET. This replaced an earlier AO3401A + 2N7000 arrangement that was cancelled after ~2.5 days of unstable-switching tests. Firmware behaviour is unchanged (A2 HIGH → NPK powered, ~1 s warm-up, then Modbus request, then A2 LOW). Any doc, schematic, or PCB reference to `AO3401A + 2N7000` is **obsolete**.
- **2026-08-26 — Pilot scope reduced to 2 plots:** `AGR-SN-0001 → PLOT_PILOT_001` (hardware). `PLOT_PILOT_002` is satellite-only (`plots.node_id = NULL`, `data_tier='satellite_only'`). `AGR-SN-0002`, `PLOT_PILOT_003`, and `PLOT_PILOT_004` are removed from the pilot for now; they can be re-added by extending `scripts/dev/seed_pilot.py::PLOTS`. Identification remains sub-node-based in the MQTT payload, so scale-out to more plots requires no wire-contract changes.


## 1. Topology (aggregate mode)


```
Sub Node 1  ──LoRa──┐
Sub Node 2  ──LoRa──┴──> Main Node ──MQTTS/8883──> AgroGuardian backend
```


Only the **Main Node** speaks MQTT. It aggregates LoRa frames from each Sub Node, unpacks the sensor readings, and publishes **one MQTT message per Sub-Node reading** with that Sub Node's `node_id` in the payload.


The Main Node holds the only MQTT credential. Sub Nodes never authenticate to MQTT directly.


## 2. Transport


| Field | Value |
| :--- | :--- |
| Broker host | `mqtts-<STATIC_IP_WITH_DASHES>.sslip.io` for the public prototype endpoint |
| Broker port | `8883` (public TLS) — local bench-test may use `1883` on localhost |
| Protocol | MQTT v5 (`mqtt.MQTTv5`) |
| QoS | **1** (at-least-once); the backend deduplicates on `(node_id, recorded_at)` |
| Auth | username + password from `provision_mqtt_credential.sh` |
| TLS | Let's Encrypt cert on port 8883; use the system CA bundle |
| Keepalive | 60 s |
| Reconnect | firmware must auto-reconnect on disconnect |


The external and internal hops are different. Firmware/laptop clients connect
to Caddy over TLS on `8883`; Caddy forwards the decrypted stream to Mosquitto
on private Docker port `1883`. The FastAPI backend also connects directly to
`mosquitto:1883` with `MQTT_USE_TLS=false`. Do not point the backend at the
public hostname from inside the Compose network.


## 3. Topic pattern


Exactly six slash-separated segments:


```
agro/v2/<tenant_id>/<farm_id>/<node_id>/telemetry
```


- `agro` and `v2` are literal.
- `<tenant_id>` — UUID from `seed_pilot.py` output. For the pilot: `11111111-1111-1111-1111-111111111111`.
- `<farm_id>` — UUID from `seed_pilot.py` output. For the pilot: `bbbbbbbb-2222-2222-2222-222222222222`.
- `<node_id>` — the **originating Sub Node** identifier, not the Main Node. Example: `AGR-SN-0001`.
- `<kind>` — currently only `telemetry` is accepted. Other kinds (`weather`, `heartbeat`, `alert`, `health`) will be added in later rounds; the backend rejects them today with `UnknownTopicKindError`.


**Backend behavior on malformed topic:** log + drop, metric `ingest_dropped_total{reason="topic_parse"}` increments.


## 4. Payload — JSON


`Content-Type` is implicit JSON. UTF-8. No BOM. **Unknown fields are rejected** (`extra="forbid"` in the pydantic model), so don't add exploratory fields to the payload — the whole message will be dropped with a validation error.


### 4.1 Required fields


| Field | Type | Notes |
| :--- | :--- | :--- |
| `$schema` | string literal | Must be exactly `"agro-guardian/telemetry/v2"`. |
| `tenant_id` | UUID string | Same as topic's `<tenant_id>`. |
| `farmer_id` | UUID string | From `seed_pilot.py`. Pilot: `aaaaaaaa-1111-1111-1111-111111111111`. |
| `farm_id` | UUID string | Same as topic's `<farm_id>`. |
| `plot_id` | string (1–64 chars) | Which plot this reading covers. Current pilot value: `PLOT_PILOT_001` (hardware). `PLOT_PILOT_002` also exists as a satellite-only plot but does not appear in MQTT telemetry. |
| `node_id` | string (1–64 chars) | Same as topic's `<node_id>` — the originating Sub Node. |
| `recorded_at` | RFC 3339 timestamp **with offset** | e.g. `"2026-07-21T13:12:00+00:00"`. Naive timestamps (no `Z`/offset) are rejected. |
| `received_at_master` | RFC 3339 timestamp with offset | When the Main Node received the LoRa frame from the Sub Node. Usually same as `recorded_at` if the Sub Node has an RTC. |
| `transmission_type` | enum string | One of: `"esp_now"`, `"lora"`, `"rs485"`, `"wifi"`. Aggregate mode almost always sends `"lora"`. |


### 4.2 Optional numeric fields (all `null` if unavailable)


Signal / diagnostics:


| Field | Type | Range / units |
| :--- | :--- | :--- |
| `signal_rssi_dbm` | integer | −150 to 20 dBm (LoRa RSSI at Main Node) |
| `firmware_version` | string | e.g. `"sub-node-1.0.0"` |
| `uptime_seconds` | integer ≥ 0 | Sub Node uptime |


Battery:


| Field | Type | Notes |
| :--- | :--- | :--- |
| `battery_voltage_v` | decimal (string or number) | e.g. `3.62` |
| `battery_percent` | decimal | 0–100 |
| `solar_charging` | boolean | true when panel is actively charging |
| `low_battery_flag` | boolean | firmware's own low-battery signal |


Soil:


| Field | Type | Units |
| :--- | :--- | :--- |
| `soil_moisture_1_pct` | decimal | 0–100 % VWC |
| `soil_moisture_2_pct` | decimal | 0–100 % VWC (second probe) |
| `soil_moisture_avg_pct` | decimal | mean of the two probes |
| `soil_temp_c` | decimal | °C |
| `soil_temp_rootzone_c` | decimal | °C at root depth |
| `soil_ph` | decimal | 0–14 |
| `soil_ec_ms_cm` | decimal | mS/cm |
| `soil_n_mg_kg` | decimal | mg N per kg soil |
| `soil_p_mg_kg` | decimal | mg P per kg soil |
| `soil_k_mg_kg` | decimal | mg K per kg soil |
| `soil_n_bucket` | integer 0–63 | if the probe returns bucketed values |
| `soil_p_bucket` | integer 0–63 | ″ |
| `soil_k_bucket` | integer 0–63 | ″ |
| `npk_sensor_raw_hex` | string | raw Modbus frame if useful for diagnostics |


Water / pump (VIRAAI v1.0 Sub Node emits flow and pressure):


| Field | Type | Notes |
| :--- | :--- | :--- |
| `water_flow_lpm` | decimal | Litres per minute measured by the pulse-counting flow sensor on the Sub Node (pin D9 of the ATmega328P). |
| `water_pressure_bar` | decimal | Line pressure in bar from the analog pressure sensor on pin A3. Range 0..~10. |


Environment / diagnostics:


| Field | Type | Notes |
| :--- | :--- | :--- |
| `tamper_detected` | boolean | tilt/tamper switch |
| `enclosure_temp_c` | decimal | °C inside the Sub Node enclosure |
| `fault_flags` | string | firmware-defined bitfield encoded as hex or CSV |
| `sensor_health_json` | object | free-form; backend stores as JSONB |
| `cadence_mode` | enum string | `"normal"`, `"rapid"`, `"low_power"`, `"storm"`, `"maintenance"` — how often this Sub Node samples |
| `backlog_pending` | boolean | true if the Sub Node has unsent readings queued |
| `validation_warn` | boolean | firmware-side pre-flight check flagged the reading |


The current MQTT Pydantic model accepts exactly the fields listed above. The
domain `Reading` and database contain additional reserved fields
(`water_volume_liters_session`, `water_volume_liters_cumulative`,
`valve_status`, `pump_running`, `pump_current_amps`,
`pump_runtime_minutes_today`, `dry_run_detected`) that are not currently
accepted by `TelemetryIn`; sending them today is an unknown-field validation
failure. Enabling any of them requires a deliberate wire-schema change,
tests, and a documentation update.


## 4.3 LoRa packet — Sub Node → Main Node (CSV over the air)


The Sub Node firmware does NOT send JSON over LoRa. It sends a compact
plain-text CSV frame because:


- ATmega328P has 32 KB flash / 2 KB SRAM — an ArduinoJson serializer at
  this scale would fit but eat working memory the sensor read loop needs.
- The frame is human-readable on the serial monitor during bench testing
  without a decoder.


The Main Node is responsible for parsing this CSV into the JSON payload
above. LoRa itself does the CRC at the radio layer (SX1278 hardware CRC),
so the packet carries no app-level checksum.


### Packet format


```
NODE=<sub_node_id>,BAT=<v>,BATP=<pct>,DST=<temp_c>,SOIL=<pct_vwc>,PRESS=<bar>,FLOW=<lpm>,NTEMP=<temp_c>,NMOIST=<pct>,EC=<ms_cm>,PH=<val>,N=<mg_kg>,P=<mg_kg>,K=<mg_kg>
```


- All fields are `KEY=VALUE`, comma-separated. No spaces.
- Missing / unavailable readings are transmitted as `KEY=NAN`.
- Numeric precision is 1 decimal place for temperatures and moistures, 2
  decimals for battery/pressure/pH, integers for counts.
- **`NODE` is required.** With more than one Sub Node on the same LoRa
  channel, this is the only way the Main Node can identify the sender.
  The Sub Node reads its own ID from EEPROM at boot (see
  `docs/SUB_NODE_FIRMWARE_CHANGES.md`).


### Example frame (real serial output from the teammate's firmware, 2026-08-03)


```
NODE=AGR-SN-0001,BAT=9.38,BATP=100,DST=27.4,SOIL=41.9,PRESS=5.31,FLOW=8.00,NTEMP=29.1,NMOIST=35.7,EC=1.045,PH=6.45,N=58,P=79,K=197
```


### Unit conversions the Main Node performs before publishing MQTT


| CSV field | Wire value | JSON field | Wire → JSON conversion |
| :--- | :--- | :--- | :--- |
| `BAT` | 9.38 (V) | `battery_voltage_v` | copy |
| `BATP` | 100 (%) | `battery_percent` | copy |
| `DST` | 27.4 (°C, DS18B20 surface) | `soil_temp_c` | copy |
| `SOIL` | 41.9 (% VWC, after Sub-Node calibration) | `soil_moisture_avg_pct` | copy |
| `PRESS` | 5.31 (bar) | `water_pressure_bar` | copy |
| `FLOW` | 8.00 (L/min) | `water_flow_lpm` | copy |
| `NTEMP` | 29.1 (°C, NPK probe at root depth) | `soil_temp_rootzone_c` | copy |
| `NMOIST` | 35.7 (%, NPK probe) | (not published — DS18B20 is our primary) | drop |
| `EC` | 1.045 (mS/cm, **already divided by 1000 on the Sub Node**) | `soil_ec_ms_cm` | copy |
| `PH` | 6.45 | `soil_ph` | copy |
| `N`, `P`, `K` | mg/kg | `soil_n_mg_kg`, `soil_p_mg_kg`, `soil_k_mg_kg` | copy |
| `NAN` (any field) | — | `null` in JSON | never emit the string `"NAN"` |


## 5. Number format — Decimal safety


Every numeric field goes through a **Decimal coercion** at the backend boundary (`Decimal(str(v))`). This dodges float-precision drift like `7.2 → 7.199999…`. Firmware can send numbers as either JSON numbers (`3.62`) or JSON strings (`"3.62"`) — both work. Sending as string avoids any risk of the JSON encoder losing a trailing digit.


**Booleans are strictly booleans.** The backend rejects `0` / `1` in a boolean field with `ValidationError`.


## 6. Timestamp format


RFC 3339, timezone-aware. Both of these are valid:


```
2026-07-21T13:12:00+00:00
2026-07-21T13:12:00.500+05:30
```


**These are all rejected:**


```
2026-07-21T13:12:00        # no timezone
2026-07-21 13:12:00Z       # space instead of T
1721560320                 # unix seconds
```


Recommendation for the Main Node: keep clock in UTC, format with `strftime("%Y-%m-%dT%H:%M:%S+00:00", ...)`. Sub Nodes without an RTC should send their reading time as `received_at_master` (i.e. the time the Main Node saw the frame).


## 7. Two example payloads


### 7.1 Minimal — just the required fields + one sensor


```json
{
  "$schema": "agro-guardian/telemetry/v2",
  "tenant_id": "11111111-1111-1111-1111-111111111111",
  "farmer_id": "aaaaaaaa-1111-1111-1111-111111111111",
  "farm_id":   "bbbbbbbb-2222-2222-2222-222222222222",
  "plot_id":   "PLOT_PILOT_001",
  "node_id":   "AGR-SN-0001",
  "recorded_at":        "2026-07-21T13:12:00+00:00",
  "received_at_master": "2026-07-21T13:12:00+00:00",
  "transmission_type":  "lora",
  "soil_moisture_avg_pct": 42.15
}
```


Published on topic:
```
agro/v2/11111111-1111-1111-1111-111111111111/bbbbbbbb-2222-2222-2222-222222222222/AGR-SN-0001/telemetry
```


### 7.2 Full — typical rich Sub-Node reading


```json
{
  "$schema": "agro-guardian/telemetry/v2",
  "tenant_id": "11111111-1111-1111-1111-111111111111",
  "farmer_id": "aaaaaaaa-1111-1111-1111-111111111111",
  "farm_id":   "bbbbbbbb-2222-2222-2222-222222222222",
  "plot_id":   "PLOT_PILOT_001",
  "node_id":   "AGR-SN-0001",
  "recorded_at":        "2026-07-21T13:12:00+00:00",
  "received_at_master": "2026-07-21T13:12:01+00:00",
  "transmission_type":  "lora",
  "signal_rssi_dbm":    -72,
  "firmware_version":   "sub-node-1.0.0",
  "uptime_seconds":     864230,
  "battery_voltage_v":  3.62,
  "battery_percent":    58.4,
  "solar_charging":     true,
  "low_battery_flag":   false,
  "soil_moisture_1_pct":  41.9,
  "soil_moisture_2_pct":  42.4,
  "soil_moisture_avg_pct": 42.15,
  "soil_temp_rootzone_c": 24.7,
  "soil_ph":            6.9,
  "soil_ec_ms_cm":      0.42,
  "soil_n_mg_kg":       95,
  "soil_p_mg_kg":       48,
  "soil_k_mg_kg":       82,
  "tamper_detected":    false,
  "enclosure_temp_c":   31.2,
  "cadence_mode":       "normal",
  "backlog_pending":    false,
  "validation_warn":    false
}
```


## 8. Backend behavior at a glance


| What happens | Backend response |
| :--- | :--- |
| Topic doesn't match `agro/v2/…/telemetry` | log + drop, metric `ingest_dropped_total{reason="topic_parse"}` |
| Topic kind is not `telemetry` (e.g. `heartbeat`) | log + drop, metric `ingest_dropped_total{reason="unknown_topic_kind"}` |
| Payload isn't JSON | log + drop, metric `ingest_dropped_total{reason="parse_error"}` |
| Extra/unknown field in payload | log + drop, metric `ingest_dropped_total{reason="validation"}` |
| Required field missing | ″ |
| Timestamp is naive (no offset) | ″ |
| Everything valid | Insert into `node_sensor_readings`; an existing `(node_id, recorded_at)` is treated as a duplicate, and rules evaluate only for a fresh insert unless `CALIBRATION_MODE=true` |


## 9. Bench test checklist for firmware


1. Backend up on the target host. Run `scripts/dev/tail_ingest.py` in a second terminal to watch.
2. `seed_pilot.py` has been run — Sub Node IDs and plot IDs exist in the DB.
3. MQTT credential provisioned via `provision_mqtt_credential.sh`.
4. `CALIBRATION_MODE=true` in the backend `.env` so early wonky readings don't fire alerts.
5. Provision `main-node-001` in the host-side Mosquitto password/ACL files. Production mounts are read-only inside the broker; use the one-off utility-container procedure in `deploy/staging/README.md`.
6. First test: `mosquitto_pub` from your laptop with the minimal payload from §7.1. If that lands, the Main Node firmware is doing the same job, just with real sensor values.
7. Only flip `CALIBRATION_MODE=false` once the sensors are producing plausible values.


## 10. Change control


Fields can be **added** to the schema in a later round; existing fields cannot be removed or renamed without a migration + a version bump on the `$schema` literal (`agro-guardian/telemetry/v3`). The backend will reject `v3` until it explicitly supports it, so firmware and backend need to move together.
