# AgroGuardian V2 — End-to-End Setup Guide

This is the definitive step-by-step for bringing the system up from an empty machine to a running pilot. Read it once end-to-end before starting; the order matters.

**Deliverables at the end:**

- A working dev environment on the Mac (Docker, Postgres, Alembic, app running locally).
- The Lightsail VPS running Caddy + Mosquitto + Postgres + the FastAPI app + Prometheus + Grafana.
- Two flashed devices in the field: one Sub Node (`AGR-SN-0001`), one Main Node (`AGR-MN-0001`).
- Every 5 minutes: one telemetry packet plus one heartbeat landing in Postgres. Every ~7 AM: one Marathi advisory ready for WhatsApp dispatch.

**What this guide assumes:**

- The pilot's hardware (LoRa link, NPK sensor, IRLZ44N gate, MT3608 boost) has been physically verified. See §5 of the AgroGuardian project skill.
- You have access to the `agri-AI/` repo on the Mac and root on the Lightsail VPS.
- You have the two SHA-verified patch bundles from `outputs/`:
  - `outputs/apply_backend_v2_wire.sh` (25-file bundle; backend + docs + alertmanager + tests).
  - `outputs/export_firmware_v2.sh` (8-file bundle; complete firmware tree).

---

## 0. Prerequisites

**Mac (development):**

- macOS 13+ with Homebrew.
- Python 3.12: `brew install python@3.12`.
- Docker Desktop.
- PlatformIO CLI: `brew install platformio`.
- Arduino IDE 2.x with MiniCore board manager (for Sub Node).
- USBasp driver.
- The Rocket Scream `LowPower` library installed in Arduino: Library Manager → search "Low-Power" → install by Rocket Scream Electronics.
- `sha256sum` (`brew install coreutils`) or `shasum -a 256` — either works with the bundles.

**VPS (Lightsail Mumbai, or any Linux VPS):**

- Ubuntu 22.04 LTS, 2 GB RAM minimum (4 GB recommended once Ginger KB runs).
- Docker + Docker Compose plugin.
- UFW enabled with ports 80, 443, 8883 open.
- A DNS-resolvable hostname pointing at the box. Pilot uses `mqtts-13-207-20-67.sslip.io` — no registration required. If you have a real domain, use that.
- 20 GB disk for Postgres time-series data (with monthly partitioning, one Sub Node produces ~200 MB/year of telemetry).

**Accounts (fill in `.env` values from these):**

- Anthropic API key (for Claude Sonnet + Haiku).
- Meta WhatsApp Business API (WABA) — pilot can defer this and use `LogOnlyWhatsappSender`.
- Sentry DSN — optional for pilot.
- Google Earth Engine service account — optional, for satellite ingestion (Phase 6).

---

## 1. Bring up the dev environment on the Mac

```bash
git clone <origin> ~/repos/agri-AI
cd ~/repos/agri-AI/agro_backend
```

Copy the env template and fill the required fields:

```bash
cp .env.example .env
```

Minimum viable `.env` for local dev (dev mode; no real MQTT broker, no real WhatsApp):

```
APP_ENV=dev
APP_VERSION=0.1.0
APP_GIT_SHA=$(git rev-parse --short HEAD)

DATABASE_URL=postgresql+asyncpg://agro:agro@localhost:5432/agro
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

AUTH_JWT_SECRET=dev_only_change_me_before_production
AUTH_JWT_ISSUER=agro-guardian
AUTH_JWT_AUDIENCE=agro-guardian
AUTH_JWT_ALGORITHM=HS256
AUTH_JWT_ACCESS_TTL_SECONDS=900

MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_BROKER_USER=service
MQTT_BROKER_PASSWORD=dev_only_change_me
MQTT_USE_TLS=false
MQTT_QUEUE_MAXSIZE=5000

CALIBRATION_MODE=false
GINGER_JOB_ENABLED=false        # keep off in dev; run manually when needed

ANTHROPIC_API_KEY=              # required in prod, empty in dev

META_WHATSAPP_TOKEN=            # required in prod, empty in dev
META_WHATSAPP_PHONE_NUMBER_ID=

CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

Start Postgres + Mosquitto locally:

```bash
docker compose -f docker-compose.dev.yml up -d
```

Install Python deps into a virtual env:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'    # installs runtime + dev extras from pyproject.toml
```

Run migrations against local Postgres:

```bash
alembic upgrade head
```

Expected: 13 migrations apply cleanly, ending with `0013_main_node_readings`. Verify:

```bash
psql "$DATABASE_URL" -c "SELECT version_num FROM alembic_version;"
# → 0013
```

Seed the pilot data:

```bash
python scripts/dev/seed_pilot.py
```

This creates the tenant, farmer, farm, both plots (`PLOT_PILOT_001` hardware, `PLOT_PILOT_002` satellite-only), Main Node `AGR-MN-0001`, Sub Node `AGR-SN-0001`, and one active `crop_seasons` row for Kharif 2026 ginger.

Verify the tests pass:

```bash
ruff check .
pytest -q
```

Expected: all green. If anything red, do not proceed — fix it before deploying to VPS.

Start the app locally to sanity-check HTTP routes:

```bash
uvicorn app.main:app --reload --port 8000
```

Then in another shell:

```bash
curl -s http://localhost:8000/api/v1/health | jq
curl -s http://localhost:8000/api/v1/ready  | jq
```

Both should return `status: ok`.

---

## 2. Apply the patch bundles (idempotent — safe to re-run)

If your local checkout is older than the current shipped state (Round 17 weather persistence, Round 17.5 heartbeat persistence, v2.1 wire additions), apply the backend patch bundle:

```bash
bash outputs/apply_backend_v2_wire.sh --dry-run --dest ~/repos/agri-AI/agro_backend
# review what would change; then:
bash outputs/apply_backend_v2_wire.sh --dest ~/repos/agri-AI/agro_backend
```

The script:

- Refuses to write to a directory that isn't an `agro_backend/` (preflight guard).
- Leaves untouched any file whose SHA-256 already matches the bundle.
- Backs up any changed file as `<file>.bak.<utc-ts>` before overwrite (skip with `--force`).
- Verifies SHA-256 post-write.

Re-run migrations + tests:

```bash
alembic upgrade head           # no-op if already at 0013
ruff check . && pytest -q
```

Similarly for the firmware bundle, on the Mac or wherever you author firmware:

```bash
bash outputs/export_firmware_v2.sh --dest ~/repos/agri-AI
```

This lands `firmware/sub_node/` and `firmware/main_node/` at the current final state.

---

## 3. Bring up the Lightsail VPS

SSH in as root (or a sudo user):

```bash
ssh ubuntu@13.207.20.67
```

Clone the repo (or rsync from the Mac):

```bash
sudo mkdir -p /opt/agri-AI
sudo chown $USER /opt/agri-AI
cd /opt/agri-AI
git clone <origin> .
```

Populate the production env file. Compared to dev, the fields that MUST be real:

```
APP_ENV=production
APP_VERSION=<git tag>
APP_GIT_SHA=<git rev-parse --short HEAD>

DATABASE_URL=postgresql+asyncpg://agro:<STRONG-PW>@postgres:5432/agro

AUTH_JWT_SECRET=<32+ chars random>
POSTGRES_PASSWORD=<STRONG-PW>

MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=1883
MQTT_BROKER_USER=agro-backend
MQTT_BROKER_PASSWORD=<STRONG-PW>
MQTT_USE_TLS=false                                   # internal Docker net → TLS-terminated at Caddy edge
CALIBRATION_MODE=false
GINGER_JOB_ENABLED=true
GINGER_JOB_HOUR=6
GINGER_JOB_MINUTE=30
GINGER_JOB_TIMEZONE=Asia/Kolkata

ANTHROPIC_API_KEY=<real>

META_WHATSAPP_TOKEN=<real>
META_WHATSAPP_PHONE_NUMBER_ID=<real>

SENTRY_DSN=<optional>
```

**The app's config validator refuses to boot in production with any of the following:** default `AUTH_JWT_SECRET`, default `POSTGRES_PASSWORD`, default `MQTT_BROKER_PASSWORD`, or empty `ANTHROPIC_API_KEY`. All four must be set to real values.

Generate the Mosquitto password file (once):

```bash
docker run --rm eclipse-mosquitto:2 mosquitto_passwd -c -b /dev/stdout main-node-001 <STRONG-DEVICE-PW> \
  > deploy/mosquitto/passwd
docker run --rm eclipse-mosquitto:2 mosquitto_passwd -b /dev/stdout agro-backend <STRONG-BACKEND-PW> \
  >> deploy/mosquitto/passwd
chmod 600 deploy/mosquitto/passwd
```

Keep `<STRONG-DEVICE-PW>` — it goes into the Main Node firmware config (`pilot_config.h::MQTT_PASSWORD`).

Bring everything up:

```bash
docker compose -f docker-compose.prod.yml up -d
```

This starts: Postgres, Mosquitto, Caddy (with `caddy-l4` for MQTT-TLS), the FastAPI app, Prometheus (loading `deploy/prometheus/prometheus.yml` which now points at `alerts.yml`), Grafana, Chroma.

Verify each service:

```bash
docker compose ps                # all should be up + healthy
docker compose logs -f app       # look for "app.startup"
docker compose exec app alembic upgrade head    # first-time only
docker compose exec app python scripts/dev/seed_pilot.py   # first-time only
```

External sanity checks (from the Mac):

```bash
# HTTPS health
curl -s https://mqtts-13-207-20-67.sslip.io/api/v1/health | jq
# → status: ok

# MQTT-TLS handshake (does not require valid creds to see the socket accept TLS)
openssl s_client -connect mqtts-13-207-20-67.sslip.io:8883 -servername mqtts-13-207-20-67.sslip.io </dev/null
# → CONNECTED, then handshake output; certificate chain from Let's Encrypt

# MQTT authenticated subscribe (proves broker + creds + Caddy L4 routing)
mosquitto_sub -h mqtts-13-207-20-67.sslip.io -p 8883 \
  --cafile /etc/ssl/certs/ca-certificates.crt \
  -u agro-backend -P <STRONG-BACKEND-PW> \
  -t 'agro/v2/#' -v
# → hangs open with no output (no messages yet)
```

If any of the three above fails, do NOT flash any device — debug the VPS side first.

---

## 4. Flash the Sub Node (`AGR-SN-0001`)

**Order matters:** do the multimeter check on the IRLZ44N gate first, then flash.

- Confirm A2 pin drives ~12 V on the NPK rail via the MT3608 boost during the NPK-active window.

Open Arduino IDE 2.x:

1. **Tools → Board → MiniCore → ATmega328**.
2. **Tools → Clock → External 8 MHz**.
3. **Tools → BOD → 2.7 V**.
4. **Tools → EEPROM → Retained**.
5. **Tools → Compiler LTO → Enabled**.
6. **Tools → Variant → 328P / 328PA**.
7. **Tools → Bootloader → No bootloader**.
8. **Tools → Programmer → USBasp (slow)**.

Open `firmware/sub_node/sub_node.ino`.

Confirm `sub_node_config.h::NODE_ID` matches this physical board — for the pilot, `"AGR-SN-0001"`.

**First-time only:** Tools → **Burn Bootloader**. This programs fuses (external 8 MHz + BOD 2.7 V). It doesn't install a bootloader.

**Every flash:** **Sketch → Upload Using Programmer** (Ctrl+Shift+U).

Open Serial Monitor @ **9600 baud**. Expected within 15 seconds of power-up:

```
================================
VIRAAI Sub Node — RAW variant
NODE_ID = AGR-SN-0001
FW      = viraai-sn-1.0.0-raw
CADENCE = 5 min (LowPower deep sleep)
LoRa    = 433 MHz SF7 BW125k CR4/5
================================

---- CYCLE 1 ----
SOIL_ADC=...
BAT_ADC=...
PRESS_ADC=...
DS_C=...
NPK: powered ON, stabilizing 10s...
NPK: OK (attempt 1)
NPK: powered OFF
TX: NODE=AGR-SN-0001,SEQ=1,WIN=0,UP=15,SOIL=...
LoRa TX: OK
SLEEP=284s
```

Notes:

- `WIN=0` on the first cycle is expected (unknown window until we've seen a previous TX).
- Status LED blink pattern post-TX: 1 short = OK, 2 = NPK failed but TX OK, 3 = TX failed. Watch the LED.
- After the first cycle the board deep-sleeps for ~4:45 (WDT-timed 8s chunks with PCINT flow counting still live). No serial output during sleep.

**Calibration day (once per Sub Node).** Set `CALIBRATION_MODE=true` in the backend `.env` temporarily. Bury the actual soil probe in bone-dry soil, note the `SOIL_ADC` value. Saturate the same probe, note the new value. Update the calibration row:

```sql
UPDATE device_calibration
SET soil_dry_adc = <DRY>, soil_wet_adc = <WET>,
    updated_by = 'field-cal-2026-09-08',
    notes = 'Manual calibration on plot 001, ginger row 3'
WHERE device_id = 'AGR-SN-0001';
```

The cache TTL on `PgDeviceCalibrationRepo` is 60 s — new values take effect within a minute. Same for pressure (manometer test) and flow (bucket test).

---

## 5. Flash the Main Node (`AGR-MN-0001`)

Update `firmware/main_node/include/pilot_config.h`:

- `MAIN_NODE_ID` — should already be `"AGR-MN-0001"`.
- `PILOT_TENANT_ID` / `PILOT_FARMER_ID` / `PILOT_FARM_ID` — must match the UUIDs seeded by `scripts/dev/seed_pilot.py`.
- `MQTT_HOST` — your VPS FQDN.
- `MQTT_USERNAME` = `main-node-001`.
- `MQTT_PASSWORD` = the `<STRONG-DEVICE-PW>` you added to `deploy/mosquitto/passwd`.
- `MODEM_APN` = `airtelgprs.com` for the pilot SIM (Airtel).
- `NODE_MAP` — one entry per Sub Node this Main Node covers. Pilot has `{ "AGR-SN-0001", "PLOT_PILOT_001" }`.

Flash with PlatformIO:

```bash
cd firmware/main_node
pio run                     # compile
pio run -t upload           # upload via USB
pio device monitor -b 115200
```

Expected serial output within ~60 seconds of power:

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
[sd]   OK, 15104 MB
[lora] listening on 433 MHz SF7 BW125k CR4/5
[modem] wake…
... AT sequence ...
[modem] NTP sync…
[time] DS3231 synced from NTP: 2026-09-08T18:00:00+00:00
[mqtt] CONNECTED
==================================================
 SETUP COMPLETE — waiting for LoRa packets
==================================================
```

Then, every 5 minutes:

```
[lora] RX (176 B, rssi=-71, snr=8.50): NODE=AGR-SN-0001,SEQ=42,...
[mqtt] publish → agro/v2/<tenant>/<farm>/AGR-SN-0001/telemetry
[mqtt] publish OK
```

And independently every 5 minutes (heartbeat, regardless of Sub Node):

```
[mqtt] heartbeat → agro/v2/<tenant>/<farm>/AGR-MN-0001/telemetry (sub_online=true, silence=42000ms)
```

If MQTT is down, telemetry (not heartbeat) queues to SD:

```
[mqtt] offline — queued to SD outbox
```

On reconnect:

```
[outbox] drained 12 line(s) after reconnect
```

---

## 6. Bench end-to-end verification

Do these tests before deploying to the field.

**Test 1 — Sub Node → Main Node → Postgres.** Both boards on your desk near each other. Main Node connected to the VPS. Wait 5 minutes. On the VPS:

```sql
SELECT recorded_at, node_id, plot_id,
       soil_moisture_1_pct, soil_temp_c, water_flow_lpm,
       validation_warn
FROM node_sensor_readings
WHERE node_id = 'AGR-SN-0001'
ORDER BY recorded_at DESC
LIMIT 3;
```

Expected: at least one row with recent `recorded_at`, plausible values, `validation_warn = false`.

**Test 2 — Main Node heartbeat lands.** Wait another 5 minutes:

```sql
SELECT recorded_at, main_node_id, sub_node_online, sub_node_silence_ms,
       bme280_temp_c, time_source, firmware_version
FROM main_node_readings
WHERE main_node_id = 'AGR-MN-0001'
ORDER BY recorded_at DESC
LIMIT 3;
```

Expected: at least one row, `sub_node_online = true`, `time_source = 'ntp'`.

**Test 3 — Weather-station data lands (Round 17).**

```sql
SELECT recorded_at, master_node_id,
       air_temp_c, humidity_pct, atmospheric_pressure_hpa,
       weather_station_battery_v
FROM weather_station_readings
WHERE master_node_id = 'AGR-MN-0001'
ORDER BY recorded_at DESC
LIMIT 5;
```

Expected: rows from BOTH the v2-raw ingest path AND the v2-master heartbeat (~2 rows per 5 minutes; idempotent unique key means duplicates on same second are silently swallowed). Populated `air_temp_c` in a plausible range.

**Test 4 — Sub Node silence detection.** Power off the Sub Node. Wait 15 minutes. Main Node keeps publishing heartbeats. Check:

```sql
SELECT recorded_at, sub_node_online, sub_node_silence_ms
FROM main_node_readings
WHERE main_node_id = 'AGR-MN-0001'
ORDER BY recorded_at DESC
LIMIT 3;
```

Expected: the most recent row has `sub_node_online = false` and `sub_node_silence_ms > 900000`.

**Test 5 — Modem outage → SD outbox drain.** Unplug the 4G antenna from the Main Node's A7672S. Wait 15 minutes (three cycles). Plug it back in. On the Main Node serial:

```
[mqtt] offline — queued to SD outbox
... (repeated for each subsequent cycle)
[mqtt] reconnecting…
[mqtt] reconnect OK
[outbox] drained 3 line(s) after reconnect
```

On the VPS:

```sql
SELECT recorded_at, backlog_pending
FROM node_sensor_readings
WHERE node_id = 'AGR-SN-0001'
ORDER BY recorded_at DESC
LIMIT 10;
```

Expected: three recent rows with `backlog_pending = true`, matching cycles during the outage.

**Test 6 — API endpoints.** From the Mac:

```bash
export TOKEN=<get from POST /api/v1/auth/verify_otp>

curl -s -H "Authorization: Bearer $TOKEN" \
  https://mqtts-13-207-20-67.sslip.io/api/v1/main_nodes/AGR-MN-0001/heartbeat | jq

curl -s -H "Authorization: Bearer $TOKEN" \
  https://mqtts-13-207-20-67.sslip.io/api/v1/main_nodes/AGR-MN-0001/weather/history?limit=5 | jq
```

Both should return real recent data.

**Test 7 — Ginger Engine daily run.** With `GINGER_JOB_ENABLED=true`, wait until the next 06:30 IST or trigger manually:

```bash
docker compose exec app python -m app.jobs.ginger_daily --plot PLOT_PILOT_001
```

Check:

```sql
SELECT generated_at, suggestion_type, full_message_marathi, review_status
FROM ai_suggestions
WHERE plot_id = 'PLOT_PILOT_001'
ORDER BY generated_at DESC
LIMIT 5;
```

Expected: at least one row with a non-null `full_message_marathi`.

---

## 7. Prometheus + alerting

Prometheus loads `deploy/prometheus/prometheus.yml`, which now includes `rule_files: - /etc/prometheus/alerts.yml`. The alerts file ships 5 rules:

- `IngestBrokerDroppingMessages` — non-duplicate drops > 0.1/s for 15 min.
- `IngestQueueGrowing` — queue depth > 1000 for 5 min.
- `MainNodeDown` — no v2-master heartbeat for 15 min.
- `SubNodeDown` — Main Node alive but every heartbeat reports `sub_node_online=false` for 15 min.
- `HttpErrorRateHigh` — 5xx rate > 5% for 10 min.

Verify Prometheus loaded them:

```bash
docker compose exec prometheus wget -qO- http://localhost:9090/api/v1/rules | jq '.data.groups[].name'
# → ["agro_ingest", "agro_main_node", "agro_http"]
```

Grafana dashboards are optional; the pilot works without them. See `deploy/grafana/` (not shipped) for future work.

---

## 8. Deploy to the field

Only after all seven bench tests above pass:

1. Weatherproof the Sub Node enclosure (IP66-rated box, silica gel, sealed cable glands on the probe leads).
2. Weatherproof the Main Node enclosure and antenna mast (same, plus a gas discharge tube on the 4G antenna feed for lightning protection).
3. Bury the Sub Node at planting depth beside a representative ginger row.
4. Mount the Main Node on the pole; confirm serial output over USB before sealing the enclosure.
5. Confirm from the VPS that rows keep landing at the expected cadence for 24 hours.
6. Handover: give the farmer a Marathi one-pager explaining the daily WhatsApp cadence and how to reply.

---

## 9. Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `[modem] SIM not ready` | SIM slot not clicked in / PIN required | Reseat SIM. Set `AT+CPIN=<pin>` if the SIM has a PIN. |
| `[modem] NETOPEN failed` | Wrong APN, no 4G coverage | Confirm APN = `airtelgprs.com` for Airtel; test the SIM in a phone. |
| `[mqtt] CONNECT FAILED` | Wrong password, TLS cert issue, or Caddy L4 SNI mis-route | `mosquitto_sub` from the Mac to prove the broker is reachable. Check Caddy logs. |
| `NPK: short read` for many cycles | RS485 wiring or 12 V rail not delivering | Multimeter the MT3608 boost during the NPK-active window. |
| `[sd] init FAIL` | Wrong FAT format / bad card | Reformat as FAT32, ≤ 32 GB. |
| Rows in `node_sensor_readings` but `validation_warn = true` | Firmware timestamp was bogus; broker corrected it | Check Sub Node's DS3231 wiring; NTP-sync the Main Node's clock. |
| `main_node_readings` empty | Migration 0013 not applied, or `AGR-MN-0001` not in `device_registry` | `alembic upgrade head`; re-run `seed_pilot.py`. |
| `weather_station_readings` empty | Reference-era backend running; missing Round 17 patch | Apply `outputs/apply_backend_v2_wire.sh` on the VPS. |
| Ingest metric `agro_ingest_dropped_total{reason="validation"}` climbing | Firmware wire format ahead of backend schema | Confirm both are on v2.1; re-apply patch bundle if needed. |
| `agro_main_node_heartbeat_total` == 0 | No Main Node reachable, or heartbeats being rejected | Check Main Node MQTT connect + payload validation. |
| Farmer says "no message came" | `GINGER_JOB_ENABLED=false`, or advisory subscriber (Round 13) not built yet | Enable the job; note that automatic WhatsApp delivery is Round 14 — meantime, dispatch manually via `POST /plots/.../suggestions`. |

---

## 10. Rollback

If the patch bundles cause any regression, revert:

```bash
# each overwritten file was backed up as <file>.bak.<utc-ts>
find ~/repos/agri-AI/agro_backend -name "*.bak.*" | while read bak; do
    orig="${bak%.bak.*}"
    mv "$bak" "$orig"
done
alembic downgrade -1        # roll back the last migration
```

Every migration has a `downgrade()` — reversal is safe as long as no application code depends on the new columns. Round 13 (`main_node_readings`) is idempotent to drop.

The firmware bundle also backs up every changed file. To roll back to a prior firmware version, restore the backup and re-flash.

---

## 11. What ships next (not covered here)

- Round 13 — advisory subscriber (`LISTEN agro_events` → `compose_advisory`). Migration `0014_advisory_status`, ~150 LOC.
- Round 14 — WhatsApp advisory go-live. WABA business verification, utility template, `POST /api/v1/webhooks/whatsapp`.
- Round 18 — nightly rollup job populating `weather_station_readings.air_temp_min_c/max/rain_mm_today` from raw pulses.
- Farmer app (Phase 9).
- Modem TLS hardening (`authmode=2` + ISRG Root X1 + MQTT password to ESP32 NVS).
- Regulatory: LoRa 433 MHz at 17 dBm compliance check with a TEC consultant.

---

*End of setup guide. If you hit anything not listed in §9, check `docs/HARDWARE_WIRE_CONTRACT.md` and `docs/DATA_INVENTORY.md` — the answer is almost always in the field-level source labels there.*
