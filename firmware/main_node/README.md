# VIRAAI Main Node — Firmware

Full production firmware for the ESP32-based Main Node. Receives LoRa CSV
frames from the Sub Node, reads the Main Node's own weather-station
sensors, assembles a raw-values JSON payload, and publishes to the pilot
MQTT broker over TLS via the SIMCom A7672S 4G modem.

All calibration is done **server-side**. Firmware transmits raw sensor
outputs (raw ADC counts, pulse counts, Modbus register values).

## Hardware assumptions

- **MCU:** ESP32-WROOM-32 dual-core @ 240 MHz.
- **Modem:** SIMCom A7672S LTE Cat-1 on UART2 (RX=GPIO 14, TX=GPIO 33).
- **LoRa:** RA-02 (SX1278) 433 MHz on HSPI (CS=5, RST=32, DIO0=27).
- **I2C:** BME280 (0x76/0x77), INA219 (0x40), DS3231 (0x68) on SDA=21 / SCL=22.
- **Weather I/O:** tipping-bucket rain gauge (GPIO 16, FALLING, INPUT_PULLUP),
  anemometer (GPIO 17, FALLING, INPUT_PULLUP), wind vane (GPIO 34, ADC).
- **SD:** MicroSD on SPI, CS=13. Currently init-verify only; offline
  buffering is a follow-up.
- **SIM:** Airtel (`airtelgprs.com`). Change `MODEM_APN` in `pilot_config.h`
  if the SIM operator changes.

## Prerequisites

1. **PlatformIO Core** (`pip install platformio` or install VSCode extension).
2. USB-serial driver for the ESP32 board's USB bridge (CP210x / CH340 —
   depends on the specific dev board).
3. Antenna + SIM installed on the A7672S module before power-on.
4. Backend already reachable at `mqtts-13-207-20-67.sslip.io:8883` with a
   valid MQTT credential provisioned via
   `agro_backend/scripts/dev/provision_mqtt_credential.sh AGR-MN-0001`.

## Configure

Edit `include/pilot_config.h` and confirm:

- `MAIN_NODE_ID` — string identity of this Main Node.
- `PILOT_TENANT_ID`, `PILOT_FARM_ID`, `PILOT_FARMER_ID` — must match the
  UUIDs seeded by `agro_backend/scripts/dev/seed_pilot.py`.
- `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD` — from the
  provisioning script's output.
- `MODEM_APN` — `airtelgprs.com` for the pilot SIM.
- `NODE_MAP` — every `Sub Node ID → PLOT_ID` pair the Main Node should
  route. For the current 2-plot pilot only `AGR-SN-0001 → PLOT_PILOT_001`
  is populated.

**Do not commit real credentials to git.** For any environment past the
pilot smoke test, move `MQTT_PASSWORD` to ESP32 NVS (Preferences library)
and rotate the value in `pilot_config.h` back to a placeholder.

## Build and flash

From this folder:

```
pio run                       # compile
pio run -t upload             # compile + flash over USB
pio device monitor -b 115200  # open serial monitor
```

Or in one shot:

```
pio run -t upload && pio device monitor -b 115200
```

## What you should see on boot (typical timings)

```
==================================================
 VIRAAI Main Node — RAW variant
  main_node_id = AGR-MN-0001
  firmware     = viraai-mn-1.0.0-raw
==================================================
I2C scan:
  0x40
  0x68
  0x76
  (3 device(s) found)
[bme]  init OK
[ina]  init OK
[rtc]  DS3231 present
[sd]   OK, 15230 MB
[lora] listening on 433 MHz SF7 BW125k CR4/5
[modem] wake…
AT
OK
AT+CPIN?
+CPIN: READY
...
+CMQTTSTART: 0
...
+CMQTTCONNECT: 0,0
[mqtt] CONNECTED
==================================================
 SETUP COMPLETE — waiting for LoRa packets
==================================================
```

Once the Sub Node powers on nearby, each cycle prints:

```
[lora] RX (168 B, rssi=-71, snr=8.50): NODE=AGR-SN-0001,SEQ=3,SOIL=412,...
[mqtt] publish → agro/v2/1111.../bbbb.../AGR-SN-0001/telemetry
[mqtt] publish OK
```

## Wire format published to MQTT

Topic: `agro/v2/<tenant_id>/<farm_id>/<sub_node_id>/telemetry`

Payload (raw variant — server does calibration):

```json
{
  "$schema": "agro-guardian/telemetry/v2-raw",
  "tenant_id": "11111111-1111-1111-1111-111111111111",
  "farmer_id": "aaaaaaaa-1111-1111-1111-111111111111",
  "farm_id":   "bbbbbbbb-2222-2222-2222-222222222222",
  "plot_id":   "PLOT_PILOT_001",
  "node_id":   "AGR-SN-0001",
  "seq": 42,
  "recorded_at":       "2026-08-26T10:45:00+00:00",
  "received_at_master":"2026-08-26T10:45:03+00:00",
  "transmission_type": "lora",
  "raw_readings": {
    "soil_adc": 412,
    "battery_adc": 780,
    "pressure_adc": 340,
    "flow_pulses_window": 12,
    "flow_pulses_total": 145,
    "ds18b20_temp_c": 27.5,
    "npk_ok": true,
    "npk_temp_raw": 291,
    "npk_moisture_raw": 357,
    "npk_ec_us_cm": 1045,
    "npk_ph_raw": 645,
    "npk_nitrogen_mg_kg": 58,
    "npk_phosphorus_mg_kg": 79,
    "npk_potassium_mg_kg": 197,
    "sub_node_fw": "viraai-sn-1.0.0-raw"
  },
  "master_readings": {
    "bme280_temp_c": 32.4,
    "bme280_humidity_pct": 65.1,
    "bme280_pressure_pa": 95000.0,
    "ina219_bus_v": 12.1,
    "ina219_current_ma": 250.0,
    "rain_pulses_window": 3,
    "wind_pulses_window": 12,
    "wind_dir_adc": 976,
    "lora_rssi_dbm": -71,
    "lora_snr_db": 8.5
  },
  "firmware_version": "viraai-mn-1.0.0-raw",
  "main_node_id": "AGR-MN-0001"
}
```

**Backend implication:** the current backend `TelemetryIn` schema
(`app/infra/mqtt/schemas.py`) uses `extra="forbid"` and expects
calibrated fields (`soil_moisture_avg_pct`, `water_flow_lpm`,
`water_pressure_bar`). This firmware sends the raw variant instead. The
backend must be extended with a matching `TelemetryInRaw` schema
(`$schema=agro-guardian/telemetry/v2-raw`) plus a calibration step that
converts raw values into the existing `Reading` domain model. That
schema change is a separate backend task — file a follow-up when you're
ready to consume these payloads live.

## Boot-time A7672S sequence

`main.cpp::modemDataAttach()` and `mqttStartAndAcquire()` reproduce the
exact AT sequence the hardware team verified working on 2026-08-26:

```
AT                                     ; wake, 5-retry loop
AT+CPIN?                               ; SIM ready check
AT+CMEE=2                              ; verbose errors
AT+CMQTTDISC / REL / STOP / NETCLOSE   ; cleanup previous session
AT+CGDCONT=1,"IP","airtelgprs.com"     ; data attach
AT+CDNSCFG="8.8.8.8","8.8.4.4"         ; force Google DNS
AT+NETOPEN                             ; expect +NETOPEN: 0
AT+CNTP="pool.ntp.org",0,1,2           ; UTC NTP sync
AT+CCLK?                               ; verify RTC updated
AT+CMQTTSTART                          ; expect +CMQTTSTART: 0
AT+CSSLCFG="sslversion",0,3            ; auto-negotiate TLS
AT+CSSLCFG="ignorelocaltime",0,1       ; pilot only
AT+CSSLCFG="authmode",0,0              ; NO cert verify (pilot only)
AT+CSSLCFG="enableSNI",0,1             ; CRITICAL for caddy-l4 routing
AT+CMQTTACCQ=0,"AGR-MN-0001",1         ; SSL client acquire
AT+CMQTTCFG="version",0,4              ; MQTT 3.1.1
AT+CMQTTSSLCFG=0,0                     ; bind SSL ctx 0
AT+CMQTTCONNECT=0,"tcp://…:8883",…     ; connect
```

**Security caveat (production migration path):** `authmode=0` accepts
any server certificate — vulnerable to MITM. Before real deployment,
upload Let's Encrypt ISRG Root X1 via `AT+CCERTDOWN` and set
`MODEM_AUTHMODE=2` in `pilot_config.h`, then reflash. See project skill
§17.3 for the full hardening steps.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `[modem] SIM not ready` | SIM missing, PIN-locked, or antenna disconnected | Reseat SIM; verify no PIN; check antenna |
| `+NETOPEN: <error>` other than 0 | APN wrong or no cellular coverage | Confirm SIM operator; update `MODEM_APN` in `pilot_config.h` |
| `+CMQTTCONNECT: 0,32` | TLS handshake failure | Verify `enableSNI=1`, RSA cert on Caddy, port 80 open for ACME. See project skill §17. |
| `+CMQTTCONNECT: 0,3` | Bad credentials | Rerun `agro_backend/scripts/dev/provision_mqtt_credential.sh AGR-MN-0001` and update `MQTT_PASSWORD` |
| `[bme] init FAIL` | I2C wiring or wrong address | Check pull-ups on SDA/SCL, confirm 0x76/0x77 in `I2C scan` output |
| No `[lora] RX` messages while Sub Node is on | Frequency / SF mismatch | Both firmwares must agree on `LORA_FREQUENCY_HZ`, SF, BW, CR. Defaults in `pilot_config.h` and `sub_node_config.h` match. |
| `[map] unknown NODE_ID` | Sub Node's `NODE_ID` not in `NODE_MAP` | Extend the table in `pilot_config.h` and reflash |
| `[mqtt] publish FAILED` repeats | Modem lost connection | Firmware auto-reconnects every 5 s. If persistent, cellular link is down. |

## Files in this folder

| Path | Purpose |
|---|---|
| `platformio.ini` | PlatformIO env, board, deps. |
| `include/pilot_config.h` | All deployment-specific constants + `NODE_MAP`. |
| `src/main.cpp` | Full firmware — direct-register sensor drivers, modem AT wrapper, MQTT publish, LoRa RX parser, JSON builder. |
| `README.md` | You are here. |
