# AgroGuardian Main Node firmware — v0.1

PlatformIO project for the ESP32-WROOM-32 (38-pin dev module) that acts as the LoRa-to-MQTT bridge for the Aurangabad pilot.

## What this firmware does

Boot sequence, in order:

1. Powers up the SIMCom A7672S 4G modem, opens UART2.
2. Registers on LTE, opens a PDP context using the BSNL APN.
3. NTP-syncs the clock (falls back to the modem's built-in NTP if the OS-level `configTime` stalls).
4. Initializes the LoRa RA-02 radio on 433 MHz.
5. Connects MQTT over TLS to Caddy at `mqtts-<ip>.sslip.io:8883`, authenticating as `main-node-001`.

Main loop:

- Blocks briefly on `LoRa.parsePacket()`.
- On any packet: reads the CSV payload, parses `KEY=VALUE` pairs, extracts the Sub Node ID.
- Looks up which plot that Sub Node covers (`SUB_NODE_MAP` in `include/pilot_config.h`).
- Builds a JSON payload matching `docs/HARDWARE_WIRE_CONTRACT.md` §4.
- Publishes to `agro/v2/<tenant>/<farm>/<node>/telemetry` with QoS 0 (raise to QoS 1 once you're happy).
- Keeps MQTT and the modem session alive; auto-reconnects on drop.

## Prerequisites

- PlatformIO Core (`brew install platformio` or the VS Code extension).
- ESP32-WROOM-32 dev board wired per the VIRAAI hardware spec:
  - LoRa RA-02: SCK=18, MISO=19, MOSI=23, NSS=5, RESET=14, DIO0=26.
  - A7672S UART2: TX=17, RX=16, power-key GPIO 4 (verify against the actual PCB before flashing).
- A working USB cable and driver for your board (CP2102 or CH340).
- The backend running at Lightsail so there's something for MQTT to reach. See `agro_backend/deploy/staging/README.md`.

## First-time setup

1. Edit `include/pilot_config.h`:
   - `MQTT_HOST` — replace `<STATIC_IP_DASHES>` with your VPS static IP (dots → dashes).
   - `MQTT_PASSWORD` — replace with the value from `provision_mqtt_credential.sh main-node-001 …`.
   - Confirm `GSM_APN`, `GSM_TX_PIN`, `GSM_RX_PIN`, `GSM_PWR_PIN` match your PCB.
   - Confirm `SUB_NODE_MAP` maps every Sub Node ID you flashed via `docs/SUB_NODE_FIRMWARE_CHANGES.md`.
2. Build + flash:

   ```bash
   pio run -t upload
   pio device monitor -b 115200
   ```

3. On the serial monitor you should see:

   ```
   [boot] AgroGuardian Main Node v0.1
   [modem] power-cycling A7672S
   [modem] init
   [gsm] waiting for LTE registration
   [gsm] network OK, opening PDP context
   [gsm] IP: 10.x.y.z
   [ntp] time = 2026-08-04T05:30:00Z
   [lora] listening on 433000000 Hz
   [mqtt] connecting as AGR-MN-0001-xxxxxxxx
   [mqtt] connected
   [boot] ready
   ```

4. Power on a Sub Node. Watch for:

   ```
   [lora] RX 132 bytes rssi=-72 snr=8.5
   [lora] payload: NODE=AGR-SN-0001,BAT=9.38,BATP=100,...
   [mqtt] publish OK -> agro/v2/.../AGR-SN-0001/telemetry (412 bytes)
   ```

5. On the VPS, confirm the row landed:

   ```bash
   docker compose -f docker-compose.prod.yml exec postgres \
     psql -U agro -d agro -c \
     "SELECT node_id, plot_id, recorded_at, soil_moisture_avg_pct, water_flow_lpm, water_pressure_bar \
      FROM node_sensor_readings ORDER BY recorded_at DESC LIMIT 3;"
   ```

## Known limitations

- **TLS in the modem, not in mbedtls on the ESP32.** The A7672S handles TLS termination; you rely on the modem firmware. If the LTE carrier does DPI on 8883 you may need to switch to port 443 + a HTTPS-tunnelled MQTT (out of scope).
- **QoS 0 publish today.** Raise to QoS 1 once you observe zero dropped messages during a bench test — QoS 1 needs a larger `MQTT_MAX_PACKET_SIZE` and a longer session state, both of which the ESP32-WROOM handles fine.
- **No offline buffering yet.** If MQTT connect fails when a LoRa packet arrives, the reading is dropped. A follow-up should write the JSON to the MicroSD card (`SD.h`) and replay on next connect. The VIRAAI spec calls out MicroSD explicitly for exactly this reason.
- **No OTA yet.** Firmware updates today require a physical USB flash. Round-18 territory: ESP32 supports dual-partition A/B OTA, and pulling the firmware from the same backend server closes that loop.
- **Sub Node → plot mapping is one-to-one.** Each Sub Node covers exactly one plot in `SUB_NODE_MAP`. The physical pilot has one Sub Node per two plots; extend the mapping (or ship a per-probe plot_id inside the LoRa payload) when that matters.
- **No heartbeat topic.** The backend's `agro/v2/+/+/+/heartbeat` route rejects heartbeats today (`UnknownTopicKindError`). Send only `telemetry` for now.

## Where to change what

| Change | File |
| :--- | :--- |
| Backend endpoint / credentials | `include/pilot_config.h` |
| GPIO pinouts (LoRa or GSM) | `include/pilot_config.h` |
| Add another Sub Node → plot mapping | `include/pilot_config.h` — extend `SUB_NODE_MAP` and bump `NUM_SUB_NODES` |
| Change JSON payload shape | `src/main.cpp::buildJson` |
| CSV parsing | `src/main.cpp::parseCsv` |
| Library versions | `platformio.ini` — pin to majors, not `latest` |

## Troubleshooting

- **SIMCom `+CMQTTCONNECT: 0,32`**: TCP reached the server but TLS failed.
  First check modem time with `AT+CCLK?`, upload ISRG Root X1 as the CA,
  set `AT+CSSLCFG="enableSNI",0,1`, and bind SSL context 0 with
  `AT+CMQTTSSLCFG=0,0` before `AT+CMQTTCONNECT`. The server-side Caddy
  template forces RSA certificates for A7672S compatibility.
- **`[modem] init FAILED`**: check `GSM_TX_PIN`/`GSM_RX_PIN` orientation; ESP32 TX must go to modem RX. Also verify the modem is powered (LED on the A7672S board).
- **`[gsm] network timeout`**: often SIM PIN. Set `GSM_PIN` in the config if the SIM is locked. Otherwise confirm carrier coverage and antenna.
- **`[mqtt] connect FAILED, state=-2`**: TLS handshake failure. Double-check `MQTT_HOST` matches your sslip.io hostname exactly (dashes, not dots). Also check the Caddy log on the VPS.
- **`[mqtt] connect FAILED, state=5`**: bad credentials. Confirm `MQTT_PASSWORD` matches what `provision_mqtt_credential.sh` set.
- **`[lora] payload: ...` but no MQTT publish**: `SUB_NODE_MAP` doesn't recognize that node ID. Update the map and reflash.

## Handoff to the field

Before deploying:

1. Bench-test one Sub Node → Main Node → cloud pipeline end-to-end.
2. Confirm you can see the row in `node_sensor_readings` on the VPS.
3. Set `MQTT_PASSWORD` and any other secrets in the config; commit an example without the secrets.
4. Enclosure: IP66 minimum for the Main Node. Solar panel wire routing.
5. On the VPS, flip `CALIBRATION_MODE=false` in `.env` and restart the app once the sensor values look plausible.
