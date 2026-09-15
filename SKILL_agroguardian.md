---
name: "agroguardian-context"
description: "Load full AgroGuardian V2 project context — problem, solution, architecture, code state (backend + firmware), roadmap, decisions, blockers, long-term goal. Use whenever the user mentions AgroGuardian, agro_backend, Sub Node, Main Node, Ginger Engine, LoRa, Aurangabad, ginger crop, MQTT ingest, Marathi advisory, Caddy MQTT, A7672S, IRLZ44N, VIRAAI, BME280, INA219, DS3231, rain gauge, anemometer, device_calibration, TelemetryInRaw, v2-master heartbeat, SD outbox, WIN field, 5-min cadence, v2.1 firmware, uptime_seconds, fault_flags, wind_gust_pulses_max, backlog_pending, main_node_readings, weather_station_readings, Round 17, Round 17.5, or anything about the precision-ag IoT platform. Trigger on any mention of the project even in passing — this is the single source of truth."
---

# AgroGuardian V2 — Full Project Context

Durable snapshot of AgroGuardian V2. Ground truth is the code in `agro_backend/` and `firmware/`. Second-most-authoritative: `agro_backend/docs/DATA_INVENTORY.md`, `agro_backend/docs/SETUP.md`, `agro_backend/docs/HARDWARE_WIRE_CONTRACT.md`, `agro_backend/docs/SCHEMA_DECISIONS.md`.

**Recent milestones (chronological):**

- 2026-08-26 — workspace cleanup, pilot scope cut to 2 plots. Firmware landed in-repo.
- 2026-08-26 — Round 16 shipped: raw-payload ingestion (`v2-raw`) + per-device calibration table.
- 2026-08-27 v1 — backend clock-skew safety net + JSONB Decimal/datetime/UUID fix. Firmware timestamp year-window (rejects 2070) + DS3231 sync-back + `time_source` field. Master-only heartbeat (`v2-master`) shipped on the firmware side.
- 2026-08-27 v2 — Sub Node 5-min cadence + LowPower deep sleep + PCINT flow counting + WDT + NPK retry + WIN field + post-TX LED codes. Main Node ESP32 task WDT + SD outbox + boot.log. Backend accepts `window_s` and `v2-master`.
- 2026-09-05 v2.1 — Sub Node adds `UP=` (uptime) + `FLT=` (fault flags). Main Node parses them + wind gust max tracking + `backlog_pending` marker on drained rows. Backend accepts all new fields.
- 2026-09-05 — Round 17 shipped: `weather_station_readings` promoted out of `sensor_health_json` into its own Main-Node-keyed table. Broker persists on both `v2-raw` and `v2-master` paths, idempotent.
- 2026-09-05 — Round 17.5 shipped: `main_node_readings` table (migration 0013), domain `MainNodeReading`, port + `PgMainNodeReadingRepo`, broker metering + persistence, API routes `/api/v1/main_nodes/{id}/heartbeat[/history]` and `/weather/latest[/history]`.
- 2026-09-08 — Alignment pass: brought reference forward, restored `rule_files` line in `prometheus.yml`, added ORM model `models/main_node.py` so `Base.metadata` knows the new table.
- 2026-09-13 — FINAL firmware v2.1 frozen — no more firmware changes planned. Everything from here is software-side.

## 1. Problem

Smallholder ginger farmers in Aurangabad make daily irrigation and crop decisions with incomplete information. Five failure modes to fix: over-irrigation, under-irrigation, pump dry-run, frost damage, no feedback loop. Explicitly not solved: pest detection, market pricing, subsidy paperwork.

## 2. Solution

Precision-ag IoT + AI advisory platform. Buried sensors → LoRa 433 MHz → 4G gateway → MQTT-TLS → FastAPI/Postgres backend → two rule engines (7 device-health + 431 Ginger KB) → Marathi advisory to farmer's phone (WhatsApp).

**North star:** *"the whole stack exists to produce one good 4-sentence Marathi message at 7 AM."*

## 3. Actors

| Actor | Role |
|---|---|
| Farmer | Marathi-only. WhatsApp OTP + advisories. |
| Agronomist / ops team | English UI. Streamlit dashboard. `kb_overrides` for per-plot rule tuning. |
| Sub Node | Buried sensor (ATmega328P), LoRa only, no internet. 5-min cycle + deep sleep. |
| Main Node | ESP32 + 4G gateway. Only device speaking MQTT. Buffers to SD on outage. |
| Backend | Everything downstream of MQTT — `agro_backend/`. |

## 4. Pilot scope

- 1 farm, 1 farmer, 2 plots, 1 Main Node, 1 Sub Node. Crop: Ginger variety Mahima, Kharif 2026.
- `AGR-SN-0001 → PLOT_PILOT_001` (hardware); `PLOT_PILOT_002` satellite-only.
- Seeded IDs (`agro_backend/scripts/dev/seed_pilot.py`): Tenant `11111111-…`, Farmer `aaaaaaaa-…`, Farm `bbbbbbbb-…`, Main Node `AGR-MN-0001`, Sub Node `AGR-SN-0001`.
- Hardware confirmed working 2026-08-27 (LoRa link, NPK sensor, IRLZ44N gate).

## 5. Data flow

```
Sub Node (every 5 min):
  wake -> WDT reset -> sensors (soil/battery/pressure ADC, DS18, NPK Modbus x up to 3 retries)
       -> compute WIN = ms since last TX
       -> LoRa TX single CSV line: NODE,SEQ,WIN,UP,SOIL,BAT,PRESS,FLOW,FTOT,DST,NOK,NT,NM,EC,PH,N,P,K[,FLT],FW
       -> LED code (1=OK, 2=NPK failed, 3=TX failed)
       -> deepSleepMs(remaining); PCINT0 on PB1 keeps flow counter live

Main Node (event-driven LoRa + timer heartbeat):
  loop:
    WDT reset
    reconnectMqttIfDown -> drain SD outbox (batch 20)
    LoRa.parsePacket -> parse CSV (WIN/UP/FLT included) -> publishSubNodeTelemetry
       (on failure: append (topic, payload) to /outbox.jsonl, backlog_pending=false marker)
    every 5 min: publishMasterHeartbeat ($schema=v2-master), sub_node_online flag
       (heartbeats NOT queued to SD — freshness matters more than history)

MQTT-TLS :8883 over 4G (Airtel APN=airtelgprs.com) -> Caddy caddy-l4 -> Mosquitto -> Broker

IngestBroker (paho -> asyncio) — dispatch by $schema:
   ├─ v2         -> TelemetryIn.to_domain() -> Reading
   ├─ v2-raw     -> fetch device_calibration -> TelemetryInRaw.to_domain(cal) -> Reading
   │                also persists master_readings block to weather_station_readings
   └─ v2-master  -> TelemetryMaster: meter + log + persist to main_node_readings
                    + persist master_readings block to weather_station_readings

Accepted paths -> _normalize_clock_skew safety net -> process_reading -> ingest_telemetry
   -> UPSERT node_sensor_readings, idempotent on (node_id, recorded_at)
   ├─ evaluate_rules (7-rule device-health, per-message)
   │     alert -> alerts_notifications + NOTIFY agro_events
   │     [Round 13 SHIPPED 2026-09-15] advisory_subscriber (LISTEN agro_events) -> dispatch_advisory -> compose_advisory -> Claude -> ai_suggestions
   └─ daily 06:30 IST: Ginger Engine batch -> 431 rules -> ai_suggestions
```

## 6. Architecture — hexagonal / ports-and-adapters

```
app/
  domain/       PURE. stdlib + Decimal + uuid + datetime + enum only.
                Includes: sensor.Reading, main_node_reading.MainNodeReading,
                weather_station_reading.WeatherStationReading, device_calibration,
                plot, alert, rules, rule_definitions, validation_gates, auth.
  application/  Use cases. Imports domain + application.ports only.
    ports/      14 Protocols including reading_repo, main_node_reading_repo,
                weather_station_reading_repo, device_calibration_repo, ai_suggestion_repo,
                alert_repo, event_bus, farmer_repo, plot_repo, otp_repo, auth_session_repo,
                chat_model, crop_season_repo, token_issuer, whatsapp_sender.
  infra/        Adapters. ONLY layer allowed to import frameworks.
                Includes: mqtt.broker (Round-17/17.5 aware), mqtt.schemas (v2 + v2-raw + v2-master),
                persistence.pg_*_repo, persistence.models.main_node (ORM),
                http.main_nodes (Round 17.5 API), events.pg_notify_bus.
  jobs/         ingest_startup (builds all repos), ginger_daily, ginger_scheduler
  lib/          logging (structlog), metrics (Prometheus, incl. agro_main_node_heartbeat_total), time
ginger/         Teammate-delivered — DO NOT edit.
```

Enforced by `tests/domain/test_domain_purity.py` and `tests/application/test_application_purity.py` (AST scan).

## 7. Tech stack

Python 3.12 + FastAPI + SQLAlchemy 2.0 async + asyncpg + Postgres 15 (PostGIS + pgcrypto; **pgvector is best-effort and absent on the pilot `postgis/postgis` image** — RAG uses ChromaDB) + Mosquitto 2.x + Claude (Sonnet + Haiku; model ids from `settings.ANTHROPIC_MODEL_*` injected at the composition layer — a `ModelRole` enum is planned, not yet built) + Meta WhatsApp Cloud API + Streamlit + Cloudflare R2 / Backblaze B2 (planned) + AWS Lightsail Mumbai + Caddy custom build with `caddy-l4` + GitHub Actions + Coolify + Prometheus + Grafana + Sentry + Tailscale + Arduino/PlatformIO firmware.

**Firmware libraries.** Sub Node adds Rocket Scream `LowPower` (Arduino Library Manager: "Low-Power" by Rocket Scream Electronics; `platformio.ini`: `lib_deps = rocketscream/Low-Power`). Main Node uses ESP32 SDK built-in `esp_task_wdt.h`.

**Provider Portability Charter.** Lightsail treated as "a Linux VPS"; no AWS-managed services (Cognito, S3-native, RDS, Lambda, SES, SNS/SQS, CloudWatch, ALB/NLB, Route 53). `boto3` only against S3-compatible endpoints (R2/B2).

## 8. Repository layout

```
proj/
├─ AgroGuardian_FINAL_Roadmap.md   184 KB roadmap v1.2 (aspirational)
├─ README.md                       Pointer into agro_backend/docs
├─ agro_backend/                   Backend — canonical source of truth (250 files)
├─ firmware/                       Sub Node + Main Node firmware (v2.1 FINAL)
├─ reference/agri-AI/              Read-only snapshot of what runs on Mac + VPS
├─ new-docs/                       Ginger Engine upstream drop
└─ outputs/                        Export scripts + patch bundles + migration bundler
```

`agro_backend/` layout: `app/{domain,application,infra,jobs,lib}` + `ginger/` (teammate-delivered) + `dashboard/` + `deploy/{caddy,coolify,mosquitto,prometheus,staging}` + `alembic/versions/0001..0013` + `docs/` + `scripts/dev/` + `tests/` (~470 tests).

## 9. Docs (`agro_backend/docs/`)

- **`SETUP.md`** — definitive end-to-end setup guide.
- **`DATA_INVENTORY.md`** — every table, every field, every source label. 1094 lines. Ground truth for "where does field X come from?".
- **`HARDWARE_WIRE_CONTRACT.md`** — MQTT wire format, all three `$schema` variants, calibration formulas.
- **`SCHEMA_DECISIONS.md`** — every reconciliation decision from PDF schema vs roadmap v3.
- `PROJECT_OVERVIEW.md`, `CODEBASE_GUIDE.md`, `API_REFERENCE.md`, `CONFIGURATION.md`, `DEVELOPMENT.md`, `FILE_REFERENCE.md`, `GINGER_ENGINE_CHANGES.md`, `SUB_NODE_FIRMWARE_CHANGES.md`.

## 10. Domain layer (pure)

11 modules: `sensor` (`Reading`), `main_node_reading` (`MainNodeReading` — Round 17.5), `weather_station_reading` (`WeatherStationReading` — Round 17), `plot`, `alert`, `metrics` (thresholds), `rules`, `rule_definitions` (`PILOT_RULESET`), `validation_gates`, `auth`, `device_calibration` (Round 16 — 8 pure conversion functions).

**Calibration math (all clamped/total, no exceptions):**
- Soil: `pct = (DRY - raw) / (DRY - WET) × 100`, clamped [0,100]. Capacitive probe: HIGH ADC = dry.
- Battery: `V = adc × VREF/1023 × divider_ratio`.
- Pressure: `bar = ((adc × VREF/1023) - offset) × scale`, clamped ≥ 0.
- Flow: `L/min = pulses × 60 / (window_s × pulses_per_L)`. `window_s` from firmware `raw_readings.window_s` (2026-08-27 v2 override); if `window_s == 0` first cycle, returns `None` (no data).
- NPK: temp = raw/10, moisture = raw/10, pH = raw/100, EC(mS/cm) = µS/cm / 1000.

## 11. Application layer

**Use cases (10):** `build_farm_brain`, `compose_advisory`, `evaluate_rules`, `ingest_telemetry`, `logout`, `process_reading`, `refresh_token`, `send_otp`, `validate_reading`, `verify_otp`.

**Ports (14):** `ai_suggestion_repo`, `alert_repo`, `auth_session_repo`, `chat_model`, `crop_season_repo`, `device_calibration_repo`, `event_bus`, `farmer_repo`, `main_node_reading_repo` (Round 17.5), `otp_repo`, `plot_repo`, `reading_repo`, `token_issuer`, `weather_station_reading_repo` (Round 17), `whatsapp_sender`.

## 12. The 7 device-health rules

`PILOT_RULESET` in `app/domain/rule_definitions.py`. Marathi templates, cooldowns per `(plot_id, alert_type)`:

`low_battery` (WARNING/12h), `battery_critical` (CRITICAL/2h), `low_water` (WARNING/4h), `dry_run` (CRITICAL/30m), `sensor_fault` (INFO/6h), `frost` (WARNING/4h), `tamper` (CRITICAL/1h).

**Cadence tuning:** at 5-min cadence, all cooldowns still work (wall-clock). Rules run 12× per hour instead of ~260×; `history_for_stuck_check` returning 6 samples now spans 30 min. A transient `dry_run` < 5 min may be missed — consider N=2 hysteresis when Round 13 subscriber ships.

## 13. API endpoints

**15 pre-Round-17.5 + 4 new = 19 today.** Base: `/api/v1/health`, `/ready`, `/auth/{send_otp,verify_otp,refresh,logout}`, `/me`, `/plots`, `/plots/{id}`, `/plots/{id}/{readings,alerts,suggestions,ginger_advisories}`, `/alerts`, `/alerts/{id}/resolve`, `/metrics` (Tailscale-gated). **Round 17.5 additions:** `/api/v1/main_nodes/{id}/heartbeat`, `/heartbeat/history?limit=N`, `/weather/latest`, `/weather/history?limit=N`. Round 14 will add `/webhooks/whatsapp`.

## 14. Ginger Engine

Upstream `ginger/` package (do NOT edit). Compiled KB `agroguardian_ginger_kb.sql` = 1.16 MB → 19 `kb_*` tables + 16 diagnostic views + 431 rules across ~15 domains. Integration: `pg_state_store.py`, `build_farm_brain.py` (~85 of ~305 fields populated), `ginger_daily.py` at 06:30 Asia/Kolkata, `/api/v1/plots/{id}/ginger_advisories`, Prometheus counters.

**Rules structure (`kb_rules`):** `rule_id` (`D<domain2>-<seq>` format), `priority` 1–5, `severity` info/yellow/red/blocking, `stage_code` (nullable = all stages), `trigger_expr` (mini-DSL evaluated against Farm Brain), `action_mr` (Marathi advisory template), `agronomic_basis` (40+ char, CHECK-enforced), `confidence_score`, `u_value` (for dedup weighting), `kannad_note` (20+ char field-team note).

**Overrides:** `kb_overrides` is the sanctioned adjustment surface. Per-plot / per-cluster / global scope. Mandatory 15+ char Marathi rationale. 400-day max expiry. Immutable rules refuse override. Every apply logged to `kb_override_audit`.

## 15. Database (60 tables total)

35 core + 23 ginger (19 tables + 4 runtime) + `device_calibration` (Round 16) + `main_node_readings` (Round 17.5) = 60.

**Migrations 0001–0013:**
- 0001: 21 base tables from PDF schema
- 0002: 13 v3 tables incl. `event_outbox`, `users`, `otp_codes`, `refresh_tokens`, `audit_log`
- 0003: extensions (uuid-ossp, postgis, pgcrypto, vector)
- 0004: `plots.node_id` nullable + `data_tier` trigger
- 0005: monthly partitions on `node_sensor_readings`
- 0006: materialized views
- 0007: audit log on 9 tables
- 0008: RLS + roles
- 0009: OTP + auth sessions
- 0010: ginger KB (1.16 MB SQL)
- 0011: `water_pressure_bar` column
- 0012: `device_calibration` table + seeds AGR-SN-0001 defaults
- **0013: `main_node_readings` table** (Round 17.5)

`event_outbox` exists, unused — Round 13 will use it. Migration `0014_advisory_status` reserved for Round 13.

## 16. IoT layer

### 16.1 Sub Node (`firmware/sub_node/sub_node.ino` — FINAL v2.1)

ATmega328P @ 8 MHz, 3.3 V. Pin map: D2=LoRa DIO0, D3=STATUS_LED, D4=DS18B20, D6/D7=RS485 RX/TX, D8=LoRa RST, D9=Flow (PCINT + polled), D10=LoRa NSS, A0=Soil, A1=Battery, A2=IRLZ44N NPK gate, A3=Pressure.

LoRa RA-02 SX1278 @ 433 MHz, TxPower 17, SF7, BW 125 kHz, CR 4/5, CRC.

**5-min cycle:** wake → WDT reset → sensor reads → 10 s NPK stabilise → NPK read + up to 2 retries at 300 ms → LoRa TX single CSV line → post-TX LED code (1/2/3 blinks) → `deepSleepMs(remaining)` via `LowPower.powerDown(SLEEP_8S, ADC_OFF, BOD_OFF)` in a loop; PCINT0 on PB1 (D9) keeps flow counter live during sleep.

**LoRa CSV (≤ 220 bytes):**
```
NODE=AGR-SN-0001,SEQ=42,WIN=300,UP=8420,SOIL=412,BAT=780,PRESS=340,FLOW=1750,FTOT=8241,
DST=27.50,NOK=1,NT=291,NM=357,EC=1045,PH=645,N=58,P=79,K=197[,FLT=npk_crc,ds18_disc],FW=viraai-sn-1.0.0-raw
```

All raw. `FLT=` omitted when no faults.

### 16.2 Main Node (`firmware/main_node/src/main.cpp` — FINAL v2.1)

ESP32-WROOM-32. Pins: GPIO 14/33 modem RX/TX; GPIO 5/32/27 LoRa CS/RST/DIO0; GPIO 13 SD_CS; GPIO 16/17/34 rain/wind/wind-dir; I2C 21/22; SPI 18/19/23.

I2C: BME280 @ 0x76/0x77, INA219 @ 0x40, DS3231 @ 0x68 — direct-register drivers.

**A7672S sequence (verified working):** AT wake → CPIN? → cleanup → `CGDCONT=1,"IP","airtelgprs.com"` → CDNSCFG → NETOPEN → CNTP → CMQTTSTART → CSSLCFG (sslversion=3, ignorelocaltime=1, authmode=0 pilot only, enableSNI=1) → CMQTTACCQ → CMQTTCFG version 4 → CMQTTSSLCFG → CMQTTCONNECT.

**Watchdog:** `esp_task_wdt_init(ESP32_TASK_WDT_S=90, true)` in setup; loop task registered via `esp_task_wdt_add(NULL)`. `modemRead()` kicks WDT every 5 s during long AT waits.

**SD offline outbox:** on publish failure, `sdAppendOutboxLine(topic, payload)` writes `{"t":"<topic>","p":<payload>}` to `/outbox.jsonl` on SD. Cap `SD_OUTBOX_MAX_BYTES=5 MB` (rotates by truncation on overflow). On next successful reconnect, `sdDrainOutbox(SD_OUTBOX_DRAIN_BATCH=20)` re-publishes; drained rows get `backlog_pending=true` via post-JSON `strstr` patch. Heartbeats are NOT queued.

**Boot log:** one line per boot to `/boot.log` with ISO timestamp + sensor init flags.

**Timestamp handling (2026-08-27):** `nowIsoUtcWithSource()` walks modem NTP → DS3231 → "none" sentinel; both sources reject years outside `[TIME_MIN_YEAR=2025, TIME_MAX_YEAR=2099]`. `syncRtcFromModemOnce()` mirrors modem NTP → DS3231 on first plausible response.

**Sub Node liveness (2026-08-27 v2):** `MASTER_HEARTBEAT_MS=300000` (5 min). `SUB_NODE_SILENCE_THRESHOLD_MS=900000` (15 min = 3 missed cycles). Heartbeat topic: `agro/v2/<tenant>/<farm>/<MAIN_NODE_ID>/telemetry`, `$schema=agro-guardian/telemetry/v2-master`.

**LoRa CSV parsing (2026-09-05 v2.1):** `subApply()` recognises `UP=`, `FLT=`, `WIN=`. `buildTelemetryJson()` emits `uptime_seconds`, `fault_flags`, `window_s` inside `raw_readings`; adds `wind_gust_pulses_max` to `master_readings` (from 3-second sliding-bucket ISR max tracking); adds top-level `backlog_pending`.

### 16.3 MQTT wire contract (final)

Three `$schema` variants; backend parses all three:

- **`agro-guardian/telemetry/v2`** — calibrated. Producer sends pre-calibrated engineering units. Used by `fake_main_node.py`.
- **`agro-guardian/telemetry/v2-raw`** — Round 16. Raw sensor outputs in `raw_readings` + `master_readings`. Used by `viraai-*-1.0.0-raw` firmware.
- **`agro-guardian/telemetry/v2-master`** — 2026-08-27 v2. Master-only heartbeat. `master_readings` + `sub_node_online` + `sub_node_silence_ms`. Topic uses `MAIN_NODE_ID` in the sub-node slot.

Topic filter: `agro/v2/+/+/+/telemetry`. QoS 1. `extra="forbid"` on every model.

**`v2-raw` fields:**
- `raw_readings`: **`window_s`** (int, optional, three-way encoding), **`uptime_seconds`** (v2.1), **`fault_flags`** (v2.1, str), `soil_adc`, `battery_adc`, `pressure_adc` (0–1023); `flow_pulses_window`, `flow_pulses_total`; `ds18b20_temp_c`; `npk_ok`; `npk_temp_raw`, `npk_moisture_raw`, `npk_ec_us_cm`, `npk_ph_raw`, `npk_nitrogen_mg_kg`, `npk_phosphorus_mg_kg`, `npk_potassium_mg_kg`; `sub_node_fw`.
- `master_readings`: `bme280_*`, `ina219_*`, `rain_pulses_window`, `wind_pulses_window`, **`wind_gust_pulses_max`** (v2.1), `wind_dir_adc`, `lora_rssi_dbm`, `lora_snr_db`, **`time_source`**, **`sub_node_online`**.
- Top-level: **`backlog_pending`** (v2.1, bool default false).

**NPK short-circuit:** `npk_ok=false` → six NPK-derived Reading fields as `None`.

**Broker-side clock-skew safety net (2026-08-27):** `_normalize_clock_skew(reading)` rewrites `recorded_at` + `received_at_master` to server UTC when outside `[-365 d, +1 d]`. Preserves originals in `sensor_health_json`, sets `validation_warn`.

## 17. Deploy topology

Lightsail Mumbai `13.207.20.67` / `mqtts-13-207-20-67.sslip.io`. Firewall: 80, 443, 8883. `docker-compose.prod.yml` runs Caddy (custom, `caddy-l4` v0.1.2) + Mosquitto + Postgres + Chroma + app + Prometheus (with alertmanager rules from `deploy/prometheus/alerts.yml`) + Grafana.

TLS fix in `agro_backend/deploy/`: `key_type rsa2048`, SNI Layer-4 routing, `mqtts-…sslip.io { respond 404 }` HTTP site for ACME.

## 18. Configuration

**Backend** — `app/config.py::Settings` + `.env.example`. Defaults: `CALIBRATION_MODE=false`, `GINGER_JOB_ENABLED=true`, `GINGER_JOB_HOUR=6`, `GINGER_JOB_MINUTE=30`, `GINGER_JOB_TIMEZONE=Asia/Kolkata`. Production guard refuses boot on default `AUTH_JWT_SECRET`, `POSTGRES_PASSWORD`, `MQTT_BROKER_PASSWORD`, or empty `ANTHROPIC_API_KEY`.

Broker clock-skew: `MAX_CLOCK_SKEW_FUTURE=timedelta(days=1)`, `MAX_CLOCK_SKEW_PAST=timedelta(days=365)` — these are **module-level constants in `app/infra/mqtt/broker.py`**, not `Settings` fields (not env-configurable).

**Sub Node** (`firmware/sub_node/sub_node_config.h`):
- `CYCLE_PERIOD_MS=300000` (5 min), `NPK_STABILIZE_MS=10000`, `DS18B20_WAIT_MS=800`.
- `WDT_TIMEOUT_CODE=WDTO_8S`, `NPK_RETRY_ATTEMPTS=3`, `NPK_RETRY_GAP_MS=300`.
- `LED_BLINK_MS=150`, `LED_BLINK_GAP_MS=150`.

**Main Node** (`firmware/main_node/include/pilot_config.h`):
- `MASTER_HEARTBEAT_MS=300000`, `SUB_NODE_SILENCE_THRESHOLD_MS=900000`.
- `ESP32_TASK_WDT_S=90`.
- `SD_OUTBOX_PATH="/outbox.jsonl"`, `SD_OUTBOX_DRAIN_BATCH=20`, `SD_OUTBOX_MAX_BYTES=5_242_880`.
- `TIME_MIN_YEAR=2025`, `TIME_MAX_YEAR=2099`.
- `WIND_GUST_BUCKET_MS=3000`, `WIND_GUST_HISTORY` sliding-bucket depth.

## 19. Roadmap status

| Phase | Name | Status |
|---|---|---|
| 0 | Bootstrap + cloud infra | ✅ |
| 1 | DB + RLS + audit | ✅ 0001–0013 |
| 2 | MQTT ingest + validation + hexagonal | ✅ + 2026-08-27 clock-skew net |
| 3 | REST API + WhatsApp OTP | ✅ + Round 17.5 main_node endpoints |
| 4 | Rules + processing | ✅ |
| 5 | AI / RAG / agent loop | ⚠️ ~30 % (Ginger Engine yes; compose_advisory manual only) |
| 6 | Satellite + weather | ❌ Not started |
| 7 | Notifications | ⚠️ OTP live; advisory blocked on Round 13 |
| 8 | Firmware + OTA | ✅ Firmware v2.1 FINAL, not yet flashed |
| 9 | Farmer app | ❌ Deferred |
| 10 | Dashboard | ✅ |
| 11 | Quota scaffolding | ❌ DB column only |
| 12 | Ops + backups | ⚠️ Partial (Prometheus rules yes; Sentry/backups no) |
| 13 (post-pilot) | MSG91 SMS + DLT | ❌ |
| 14 (post-pilot) | Razorpay + UPI | ❌ |

## 20. Built vs. left

### Built and verified

MQTT ingest, 4 validation gates, idempotent UPSERT, 7-rule device-health engine, OTP→JWT, 19-endpoint API, Ginger Engine + 06:30 IST job, Streamlit dashboard, Meta WhatsApp OTP live, Prometheus + Sentry init.

Firmware v2.1 FINAL in-repo. Hardware confirmed working. Lightsail VPS + MQTT-TLS verified.

Round 16 (v2-raw + device_calibration). 2026-08-27 backend clock-skew net + JSONB fix. Firmware v1/v2 (timestamp hardening + v2-master heartbeat). Firmware v2.1 (uptime + fault flags + wind gust + backlog_pending + backend acceptance). Round 17 (weather_station_readings persistence). Round 17.5 (main_node_readings + API endpoints + ORM model + broker persist + meter).

### Not yet built (next up)

- ✅ **Round 13 — advisory subscriber (SHIPPED 2026-09-15, deployed to staging).** `LISTEN agro_events` → `dispatch_advisory` (6-state machine: pending/in_flight/composed/skipped/failed_transient/failed_permanent, atomic claim + reconciler + reaper + backoff retries) → `compose_advisory` → Claude → `ai_suggestions`; emits `suggestion.generated`. Migration `0014_advisory_status`. ~1131 LOC incl. tests (the earlier "~150 LOC" estimate was optimistic).
- **Round 14 — WhatsApp advisory go-live.** WABA verification, utility template, webhook route.
- **Round 18 — nightly weather rollup** for `air_temp_min/max/rain_mm_today/…`.
- Farmer app; OTA; satellite ingestion; production hardening; regulatory clearance.

### Not deployed

**The full stack runs on the staging VPS `agro-staging-01` (13.207.20.67):** Caddy + Postgres + Mosquitto + FastAPI app + Prometheus + Grafana + Chroma (confirmed 2026-09-15). Round 13 is deployed there (DB at migration `0014`). Not yet done on staging: `CALIBRATION_MODE` is still `true` (rules short-circuit) and `.env` has no `ANTHROPIC_API_KEY` (advisories use the log-only model). Neither field board flashed yet. (Production is a separate, not-yet-existing environment.)

## 21. Immediate next stages

**Stage 1 — Flash Sub Node.** Arduino IDE + MiniCore + USBasp. Verify Rocket Scream `LowPower` library installed. Boot serial: `CADENCE = 5 min (LowPower deep sleep)`. Cycle serial: `SLEEP=<seconds>s` before each deep-sleep. Post-TX LED pattern.

**Stage 2 — Flash Main Node.** PlatformIO. Boot serial: I2C scan (0x40 + 0x68 + 0x76) → BME/INA/RTC OK → SD OK → LoRa listening → `+CMQTTCONNECT: 0,0` → `[time] DS3231 synced from NTP` → `[mqtt] heartbeat` every 5 min.

**Stage 3 — Bench end-to-end.** Both boards near each other. Verify `[lora] RX` on Main Node serial + row lands in `node_sensor_readings` on VPS. Verify `[outbox] queued` when modem antenna unplugged, then `[outbox] drained` on reconnect. Verify `sub_node_online=false` in heartbeats after Sub Node is off for 15 min.

**Stage 4 — Calibration day.** `CALIBRATION_MODE=true`. Measure real DRY_ADC + WET_ADC on soil probe. `UPDATE device_calibration ...`. Also `pulses_per_L` (bucket test), pressure offset/scale (manometer).

**Stage 5 — Round 13 (advisory subscriber).** Migration 0014, ~150 LOC.

**Stage 6 — Round 14 (WhatsApp advisory go-live).**

**Stage 7 — Round 18 (weather rollup).**

**Stage 8 — Modem TLS hardening.** `authmode=0 → 2` + ISRG Root X1 + MQTT password to ESP32 NVS.

**Stage 9 — Satellite ingestion for PLOT_PILOT_002.**

**Stage 10 — Farm Brain coverage expansion** (target 60–70 %).

**Stage 11 — Round 15 production hardening.** Nightly pg_dump → R2/B2, Sentry alerts, Tailscale, Grafana dashboards.

**Stage 12 — Scope back up.** Extend `PLOTS` + `NODE_MAP`; provision `AGR-SN-0002`.

## 22. Long-term goal

Scale 1 → 10,000 farms. Costs: Pilot ~$28/mo → Enterprise ~$4,000/mo. Invariants: repository pattern, PG native partitioning, hexagonal.

## 23. Key decisions

| Decision | Why | Rejected |
|---|---|---|
| Pilot scope 4 → 2 plots | Focus validation | Full 4-plot day one |
| Raw-values firmware, calibration server-side | Tune per-device without reflash; audit trail | Baked calibration |
| Round 16 dispatch by `$schema` | Support both variants concurrently | Hard cutover |
| Lightsail over Oracle/EC2 | Predictable + built-in IP/DNS/firewall | Oracle, raw EC2 |
| Hexagonal + AST purity | Mechanical swap of external deps | Layered MVC |
| PG LISTEN/NOTIFY | Zero new infra at pilot | Redis/NATS |
| WhatsApp OTP + advisory | Free test mode, no DLT | SMS via MSG91 |
| Sonnet + Haiku via `ModelRole` | 3× cheaper than Opus | Hardcoded model |
| IRLZ44N MOSFET | Stable | AO3401A + 2N7000 — cancelled |
| NPK 10 s stabilization | Empirically required | 1 s |
| RSA cert on Caddy | A7672S unreliable with ECDSA | Default ECDSA |
| SNI-based Layer-4 | caddy-l4 needs SNI | Non-SNI |
| Airtel APN | Pilot SIM | BSNL |
| `sslversion=3` + `authmode=0` pilot | Accept-any-cert; MUST tighten before prod | `authmode=2` at smoke |
| Sub Node LoRa CSV has `NODE=` + `SEQ=` | Future-proof multi-Sub-Node | Anonymous payload |
| Main Node maps NODE→PLOT via `NODE_MAP` | Sub Node doesn't need to know its plot | Plot ID over LoRa |
| Ginger Engine as data-driven KB | Editable by agronomy | 431 rules as Python |
| Decimal for measurements | Avoids float drift | float |
| `sslip.io` before real domain | Zero-config wildcard DNS + LE cert | Buy domain before brand |
| Defence-in-depth on device time (firmware year window + backend `_normalize_clock_skew`) | Firmware primary; backend safety net | Drop on skew (loses data) |
| New `$schema=v2-master` for master heartbeat | Cleanly separates Sub Node dead vs Main Node/LoRa dead | Reuse v2-raw with nulled raw |
| Sub Node 5-min cadence | 20× data reduction; matches ginger decision timescale | 60 s (unnecessary) / 15 min (misses transients) |
| PCINT flow counting during LowPower sleep | Losing 1500+ irrigation pulses per window would kill flow measurement | Poll-only (breaks with sleep) |
| `WIN=<seconds>` on wire | WDT clock is ±10-15%; nominal 300s can be 260-340s | Bake window into config |
| `MASTER_HEARTBEAT_MS=300000` (match cadence) | 60 s heartbeat = 5× 4G overhead with no ops-resolution gain | Keep 60 s |
| SD outbox: Sub-Node-telemetry-only, NOT heartbeats | Telemetry is authoritative history; stale heartbeat has no ops value | Queue everything / queue nothing |
| Round 17.5 `main_node_readings` as separate table (not on `node_sensor_readings`) | Main Node heartbeat is infrastructure-level, no plot_id/farmer_id | Nullable plot_id on `node_sensor_readings` (degrades queries) |
| `raw_readings.window_s` uses three-way `Optional[int]` encoding | Distinguish pre-v2 (field absent) from v2 first-cycle (0) from v2 steady-state (>0) | Required int, sentinel -1, or two fields |

## 24. Open blockers

1. ✅ Lightsail VPS, MQTT-TLS, pilot scope, firmware in-repo, Round 16, backend clock-skew net, firmware v1/v2/v2.1, Round 17, Round 17.5.
2. ✅ Hardware physical validation (LoRa/NPK/IRLZ44N gate).
3. **Neither board flashed yet.** Firmware v2.1 is the final; export bundle is ready.
4. **Modem TLS is `authmode=0`** — MITM-vulnerable, pilot only.
5. **MQTT password in `pilot_config.h`** — rotate + NVS before deploy.
6. **Round 13 event-subscriber not built.**
7. **Round 14 WhatsApp go-live** blocked on WABA verification.
8. **Farm Brain coverage ~28 %.**
9. **`pump_current_amps` not sensed on current Main Node hardware** — several irrigation rules and `electricity_schedule_log` rely on flow-inference.
10. Placeholders: sowing/harvest dates.
11. **No object storage wired.**
12. **No production Sentry alerting / backups / Grafana.**
13. **LoRa 433 MHz regulatory clearance** not done for commercial deployment.

## 25. Development conventions (`.cursorrules`)

- Never import `fastapi`, `sqlalchemy`, `anthropic`, `structlog`, `pydantic`, `httpx`, `paho` from `domain/` or `application/`.
- Decimal for measurements; never float.
- TZ-aware datetimes via `app/lib/time.py`.
- Repository pattern; every DB access via `Pg*Repo` behind a Protocol.
- Model selection via `ModelRole`; never hardcode `claude-…`.
- `text()` uses `CAST(:name AS type)`; never `:name::type`.
- Function-scoped async DB fixtures.
- Fake Protocol impls in tests.
- One file per use case; `execute()`; `@dataclass(frozen=True)` deps.
- JSON never crosses LoRa.
- Firmware: Sub Node uses `F("...")` on every Serial string; no dynamic allocation. Volatile counters + ATOMIC_BLOCK for multi-byte access.
- Round 16: `to_domain()` on `TelemetryInRaw` takes a `DeviceCalibration` arg.
- 2026-08-27 v1: any JSONB payload with `Decimal`/`datetime`/`UUID` goes through `_jsonb_param()`. Clock-skew normalisation runs post-`to_domain()`, pre-ingest.
- 2026-08-27 v2 firmware: Sub Node cycle = one deep-sleep-bounded loop iteration; anything long-running MUST call `wdt_reset()` at ≤ 8 s intervals. Flow counters `volatile` + ATOMIC_BLOCK-guarded. PCINT enable/disable paired around `LowPower.powerDown`. Main Node SD outbox is Sub-Node-telemetry-only; heartbeats bypass. `esp_task_wdt_reset()` inside any function that can block > 5 s.
- 2026-09-05 v2.1: `UP=` / `FLT=` fields on Sub Node CSV; `uptime_seconds` / `fault_flags` / `wind_gust_pulses_max` / `backlog_pending` on backend schemas — all optional/defaulted for back-compat.

## 26. Glossary

| Term | Meaning |
|---|---|
| VIRAAI v1.0 | Hardware team's name for current spec |
| Sub Node / Main Node / AGR-MN-0001 / AGR-SN-0001 / PLOT_PILOT_001/002 | Pilot devices + plots |
| Round | Dev team incremental delivery unit |
| Phase | Roadmap numbering |
| Ginger Engine / Round G | Teammate 431-rule daily engine |
| Farm Brain | ~305-field per-plot dict; ~85 populated |
| CALIBRATION_MODE | Env flag; `evaluate_rules` short-circuits |
| Cooldown | Min time between same-type alerts |
| compose_advisory | Alert → Claude → Marathi advisory |
| event_outbox | Planned transactional-outbox table (backend) |
| `$schema` | `v2` (calibrated), `v2-raw` (raw ADC), or `v2-master` (master heartbeat) |
| `device_calibration` | Round 16 table; per-Sub-Node calibration constants |
| `TelemetryInRaw` | Round 16 pydantic model; nested `RawReadings` + `MasterReadings` |
| `TelemetryMaster` | Round 17.5 pydantic model; `MasterReadingsHeartbeat` |
| `MainNodeReading` | Round 17.5 domain type; row in `main_node_readings` |
| `WeatherStationReading` | Round 17 domain type; row in `weather_station_readings` |
| `_normalize_clock_skew` | Broker-side safety net; rewrites impossible timestamps + `validation_warn` |
| `_jsonb_param` | JSONB writer with Decimal/datetime/UUID handler |
| `WIN` (CSV) / `window_s` (JSON) | Wall-clock seconds since Sub Node's previous TX. 0 = first cycle |
| `UP` (CSV) / `uptime_seconds` (JSON) | v2.1: `millis()/1000` on Sub Node |
| `FLT` (CSV) / `fault_flags` (JSON) | v2.1: comma-separated Sub Node fault tags (`npk_crc`, `npk_short`, `npk_hdr`, `ds18_disc`) |
| `wind_gust_pulses_max` | v2.1: max pulses in any 3s bucket over master reporting window |
| `backlog_pending` | v2.1: true on rows the Main Node drained from `/outbox.jsonl` |
| `time_source` | "ntp"/"rtc"/"none" — provenance of the payload timestamp |
| `sub_node_online` | Main Node's view of Sub Node liveness; false if last LoRa RX > 15 min |
| `sub_node_silence_ms` | ms since last LoRa RX (0 if never) |
| PCINT0 | ATmega328P pin-change interrupt group 0 (PORTB); flow counting during LowPower sleep |
| `LowPower.powerDown` | Rocket Scream helper — deep sleep, ADC + BOD off, WDT-timed wake |
| `esp_task_wdt` | ESP32 SDK task watchdog |
| `SD_OUTBOX_PATH` | `/outbox.jsonl` on Main Node SD |
| `/boot.log` | Main Node boot log |
| caddy-l4 | Caddy plugin for raw-TCP L4; terminates MQTT-TLS |
| sslip.io | Free wildcard DNS |
| IRLZ44N / MT3608 | NPK 12 V rail hardware |
| RA-02 / SX1278 | LoRa module/chip |
| A7672S | SIMCom 4G Cat-1 modem |
| BME280 / INA219 / DS3231 | Main Node I2C sensors |
| ISRG Root X1 | Let's Encrypt root CA (needed for `authmode=2`) |
| `NODE_MAP` | Main Node's compile-time `NODE_ID → PLOT_ID` table |
| Round 17 / 17.5 | Weather-station / Main-Node-readings persistence and API |

## 27. How to use this skill

- Refer here first before searching the codebase.
- When code and this document disagree, **code wins**; update the skill for durable changes.
- When the user modifies the backend or firmware, re-read the changed files; decide if the skill needs updating.
- Don't invent architecture. Hexagonal + purity tests + Provider Portability Charter are non-negotiable.
- Don't touch `ginger/` — upstream-owned.
- When suggesting next work, follow §21. Stages 1–4 are the critical path to real telemetry landing in Postgres.
- When user asks about plots, pilot is 2 plots — NOT 4.
- When user asks about wire format: three variants (`v2`, `v2-raw`, `v2-master`), all parsed. `v2.1` refers to firmware version, not schema — the schema is still `v2-raw`/`v2-master`.
- When user asks about cadence, Sub Node is 5 min. Data volume ~288 rows/day/plot.
- When user asks about firmware timestamps: firmware year-window → firmware NTP-to-RTC sync-back → backend `_normalize_clock_skew` safety net.
- When user asks about power / battery / sleep, Sub Node uses Rocket Scream LowPower.powerDown in 8s chunks with PCINT-wakeable flow counting.
- When user says "test"/"check"/"review", run domain + application purity tests first.
- Lead any explanation with §1 (problem), §2 (solution), §4 (pilot scope), §20 (built vs. left).

*End of skill. Ground truth: `agro_backend/` + `firmware/`. Documentation: `agro_backend/docs/{DATA_INVENTORY.md, SETUP.md, HARDWARE_WIRE_CONTRACT.md, SCHEMA_DECISIONS.md}`. Firmware v2.1 is FINAL.*
