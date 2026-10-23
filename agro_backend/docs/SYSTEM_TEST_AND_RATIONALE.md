# AgroGuardian — Full System Test Runbook & Tech-Stack Rationale

**What this is:** a single document to (1) **manually test every flow** end-to-end, in order, from the moment
telemetry enters over MQTT to the Marathi WhatsApp advisory and back, including the **external data sources**
(satellite, weather, LLM, WhatsApp); and (2) answer **"why this component and not the alternatives"** for every
major tech choice.

**How to use it:** Part 1 = setup. Part 2 = the sequential stage-by-stage test plan (run top-to-bottom). Part 3
= the rationale ("why X not Y"). Part 4 = external-source deep dive. Part 5 = a tickable master checklist.

**Ground truth:** `agro_backend/` + `firmware/`. Commands target the **staging box** (the live stack) unless
noted; local-dev equivalents use `docker-compose.dev.yml`. Dates/flags current as of 2026-10-21.

> **Shell shorthand used throughout.** On the box, set this once so the commands read cleanly:
> ```bash
> cd ~/agri-AI-live/agro_backend
> DC="docker compose -f docker-compose.prod.yml"
> PSQL="$DC exec -T postgres psql -U agro -d agro -c"
> ```
> Then e.g. `$DC exec app python -m app.ops.diagnose` or `$PSQL "SELECT now();"`.

---

# PART 1 — Setup & ground rules

### 1.1 Two environments
- **Box (staging, live):** `~/agri-AI-live/agro_backend`, `docker-compose.prod.yml`. Real external creds, real
  (or fake-node) telemetry. This is where you test the *live* satellite/weather/LLM paths.
- **Local dev:** `make up` (`docker-compose.dev.yml`) on your Mac — Postgres + Mosquitto + Chroma + app. Good for
  the ingest/calibration/rules/mapper logic without real creds. DB-gated tests run here.

### 1.2 Before you start (one-time)
```bash
$DC ps                         # every container Up/Healthy
$DC exec app alembic current   # must be 0069 (head)
$DC exec app python -m app.ops.diagnose   # red/green of the whole system in one shot
```
`$DC exec app python -m app.ops.diagnose` is your **north-star smoke test** — re-run it after each stage.
(On the box use this container form; a bare `make diagnose` only works where `python` is on PATH, e.g. the dev
stack — on the host it fails with `make: python: No such file or directory`.)

> **Dev-script caveat (verified on the box 2026-10-24):** `fake_main_node.py`, `inject_test_reading.py`,
> `fetch_satellite_once.py`, `probe_cdse_raw.py` are **not baked into the prod image** (only `lst_smoke.py` and
> `whatsapp_smoke.py` are). On the box, use `mosquitto_pub` (Stage 1) to inject a reading, and the live schedulers
> / `make diagnose` for satellite — or run a missing script from a bind-mounted checkout. Fixing the Dockerfile to
> ship `scripts/dev/` is backlog item **A5**.

### 1.3 Safety
- The dashboard DB engine is **read-only** by design; psql above is read-only queries.
- `whatsapp_smoke.py` **sends a real message** — only run it against a number you control.
- Satellite/LST fetches hit paid-quota-free but rate-limited external APIs; don't loop them.
- Never run destructive SQL on the box; use `SELECT` to verify.

---

# PART 2 — Sequential end-to-end test plan

The pipeline, in order. Each stage: **what it does → how to test → what to verify → how it fails.**

```
[0] bring-up → [1] TLS/MQTT edge → [2] ingest broker (schema dispatch) → [3] calibration →
[4] persistence(+partitions) → [5] device-health rules → [6] pipeline trace →
[7] weather forecast → [8] satellite → [9] Landsat LST → [10] daily mapper →
[11] Ginger KB engine → [12] water-budget → [13] yield model → [14] advisory compose (Claude) →
[15] delivery (WhatsApp) → [16] inbound reply → [17] diagnostics/ledger → [18] DPDP → [19] dashboards
```

## Stage 0 — Bring-up & seed
**Test**
```bash
$DC up -d
$DC exec app alembic upgrade head
$DC exec -e PILOT_PHONE=+91XXXXXXXXXX app python scripts/dev/seed_pilot.py   # first time only
```
**Verify:** prints Main Node `AGR-MN-0001` + Sub Node `AGR-SN-0001`; `$PSQL "SELECT plot_id FROM plots;"` shows
`PLOT_PILOT_001`. App logs show the 10+ schedulers `.started`.
**Fails if:** migrations not at head; seed already ran (idempotent — safe to re-run).

## Stage 1 — TLS / MQTT edge (Caddy L4 → Mosquitto)
**What:** hardware connects MQTTS on **:8883**; Caddy terminates TLS and forwards the raw stream to Mosquitto on
private **:1883**; Mosquitto authenticates `main-node-001`.
**Test (from your laptop):**
```bash
# 1. Cert chain (the modem is picky — RSA cert expected)
openssl s_client -connect mqtts-<IP_DASHES>.sslip.io:8883 -servername mqtts-<IP_DASHES>.sslip.io </dev/null | head
# 2. Authenticated publish of a minimal v2 payload (HARDWARE_WIRE_CONTRACT §7.1)
mosquitto_pub -h mqtts-<IP_DASHES>.sslip.io -p 8883 --capath /etc/ssl/certs \
  -u main-node-001 -P '<MQTT_PASSWORD>' \
  -t 'agro/v2/11111111-1111-1111-1111-111111111111/bbbbbbbb-2222-2222-2222-222222222222/AGR-SN-0001/telemetry' \
  -m '{"$schema":"agro-guardian/telemetry/v2","tenant_id":"11111111-1111-1111-1111-111111111111","farmer_id":"aaaaaaaa-1111-1111-1111-111111111111","farm_id":"bbbbbbbb-2222-2222-2222-222222222222","plot_id":"PLOT_PILOT_001","node_id":"AGR-SN-0001","recorded_at":"2026-10-21T06:30:00+00:00","received_at_master":"2026-10-21T06:30:00+00:00","transmission_type":"lora","soil_moisture_avg_pct":42.15}'
```
**Verify:** no TLS error; publish returns 0; app logs `ingest_broker.subscribed topic='agro/v2/+/+/+/telemetry'`
then an ingest event. **Fails if:** `+CMQTTCONNECT: 0,32` on the modem (cert/ECDSA — clear Caddy cert cache, see
`deploy/staging/README.md` §4); auth denied (wrong `MQTT_BROKER_PASSWORD` / `passwd` mismatch).

## Stage 2 — Ingest broker & schema dispatch
**What:** `app/infra/mqtt/broker.py` parses the topic `agro/v2/<tenant>/<farm>/<node>/telemetry`, dispatches on
`$schema`: **`v2`** (pre-calibrated), **`v2-raw`** (raw ADC+pulses — real firmware), **`v2-master`** (gateway
heartbeat). QoS 1; **idempotent on `(node_id, recorded_at)`**.
**Test without hardware** (two options):
```bash
# A. Synthetic Main Node — streams realistic telemetry  (DEV STACK ONLY — not in the prod image, see A5)
$DC exec app python scripts/dev/fake_main_node.py --plot-id PLOT_PILOT_001 --node-id AGR-SN-0001 --rate 1 --duration 30
# B. One guaranteed-alert reading (DEV STACK ONLY — not in the prod image, see A5)
$DC exec app python scripts/dev/inject_test_reading.py --moisture 10 --battery 3.2
# On the BOX (scripts absent): inject a reading with mosquitto_pub (Stage 1), or publish via the real/fake node.
```
**Verify:** `$DC logs --since 2m app | grep -E "ingest|v2-raw|v2-master|dropped"`; a row lands (Stage 4).
Duplicate check: publish the same `(node_id, recorded_at)` twice → only one row. **Fails if:**
`ingest_dropped_total{reason=...}` increments (topic_parse / validation / unknown_tenant) — inspect reason.

## Stage 3 — Server-side calibration (raw → engineering units)
**What:** for `v2-raw`, `TelemetryInRaw.to_domain(cal)` applies per-device constants from `device_calibration`
(migration 0012): soil `% = (DRY-raw)/(DRY-WET)×100`, battery/pressure linear, **flow `L/min =
pulses×60/(window_s×pulses_per_L)`**, NPK scaling. Pure functions in `app/domain/device_calibration.py`.
**Test / verify:** the **Pipeline Inspector** dashboard (page 14) shows **raw ↔ calibrated side-by-side** per
message. Or: `$PSQL "SELECT recorded_at, soil_moisture_avg_pct, water_flow_lpm, battery_voltage_v FROM node_sensor_readings ORDER BY recorded_at DESC LIMIT 3;"` — values in sane ranges. Math-lock is covered by the self-test
(`$DC exec app python -m app.infra.pipeline_selftest`, exit 0). **Fails if:** calibration row missing for the node
→ calibrated values null; self-test fails a math case.

## Stage 4 — Persistence & partitions
**What:** `v2/v2-raw` → `node_sensor_readings` (+monthly partitions, migration 0005; DEFAULT catch-all 0067);
master weather → `weather_station_readings`; `v2-master` → `main_node_readings`.
**Verify:**
```bash
$PSQL "SELECT count(*), max(recorded_at) FROM node_sensor_readings;"
$PSQL "SELECT count(*) FROM weather_station_readings;"
$PSQL "SELECT sub_node_online, sub_node_silence_ms, recorded_at FROM main_node_readings ORDER BY recorded_at DESC LIMIT 3;"
```
Partition health is an invariant in `make diagnose` (`partition_default_present`). **Fails if:** insert hits no
partition (pre-0067 risk — now covered) → check `partition_maintenance` job ran (Scheduler Health page).

## Stage 5 — Device-health rules (7, per message)
**What:** `app/domain/rule_definitions.py` `PILOT_RULESET` evaluates each reading: low_battery, battery_critical,
low_water, dry_run, sensor_fault, frost, tamper → `alerts_notifications` + `NOTIFY agro_events`. Per-`(plot,
alert_type)` cooldowns. (Note: `CALIBRATION_MODE=true` short-circuits all firing — check it's `false` to test.)
**Test:** the `inject_test_reading.py --moisture 10 --battery 3.2` from Stage 2 is engineered to trip alerts.
**Verify:** `$PSQL "SELECT alert_type, severity, triggered_at FROM alerts_notifications ORDER BY triggered_at DESC LIMIT 5;"` (the column is `triggered_at`, not `created_at`)
→ LOW_WATER + LOW_BATTERY rows. **Fails if:** `CALIBRATION_MODE=true` (no alerts by design); cooldown suppressing
a repeat (expected).

## Stage 6 — Pipeline trace (observability of stages 1–5)
**What:** flag `PIPELINE_TRACE_ENABLED=true` writes one `pipeline_trace` row per v2-raw msg (raw/calibrated/stages/
validations/overall). **Verify:** dashboard **14 Pipeline Inspector** (per-message timeline), **15 Stage Health**
(aggregate: which stage/field is systematically off). **Fails if:** flag off → pages say "no traces."

## Stage 7 — Weather forecast (Open-Meteo) — EXTERNAL
**What:** `forecast_scheduler` (03:00 IST, no key) → `weather_forecasts`. There is **no one-shot CLI** for the
forecast job (unlike satellite/LST), so verify the last nightly run rather than forcing one:
```bash
$PSQL "SELECT max(forecast_for_date), count(*) FROM weather_forecasts;"
$PSQL "SELECT status, started_at, summary FROM job_run WHERE job_name='weather_forecast' ORDER BY started_at DESC LIMIT 3;"
```
**Verify:** `max(forecast_for_date) >= today`; the diagnostics check `forecast_coverage` is ✅; the `weather_forecast`
row in the job-run ledger is `ok` within the last ~26 h. To force an off-schedule run for testing, temporarily set
`FORECAST_JOB_HOUR`/`_MINUTE` to a few minutes ahead in `.env` and recreate the app, then revert. **Fails if:**
Open-Meteo unreachable (rare) → `weather_forecast` job shows `failed` in the ledger with the error.

## Stage 8 — Satellite (Sentinel-1/2 via CDSE) — EXTERNAL
**What:** `satellite_scheduler` (02:30) → `satellite_data`; needs `SATELLITE_JOB_ENABLED=true` + Copernicus OAuth +
a plot boundary polygon. **Test now (one-shot, no waiting):**
```bash
$DC exec app python scripts/dev/fetch_satellite_once.py          # (dev stack only — not in prod image, see A5)
$DC exec app python scripts/dev/probe_cdse_raw.py                # (dev stack only — not in prod image, see A5)
$PSQL "SELECT plot_id, image_date, ndvi_value, ndre_value, satellite_source FROM satellite_data ORDER BY image_date DESC LIMIT 5;"
```
On the box (where the fetch scripts aren't present), verify via the nightly run + `dep_cdse` and the query above.
**Verify:** a token 200 + rows with `ndvi_value` etc. (the column is `ndvi_value`, not `ndvi_mean` — the mapper
aliases it to the `ndvi_mean` farm-brain field). Diagnostics `dep_cdse` ✅ and `satellite_fresh` ok/warn.
**Fails if:** blank `COPERNICUS_CLIENT_ID/SECRET` (dep_cdse skip); plot lacks `gps_boundary_geojson`
(`skipped_no_polygon`); revisit cadence means "no new scene for a few days" is normal (warn, not fail).

## Stage 9 — Landsat LST (USGS M2M) — EXTERNAL
**What:** `landsat_scheduler` (04:30) → `satellite_data.lst_c` → derived `cwsi`. **Test now:**
```bash
$DC exec app python scripts/dev/lst_smoke.py --days 30        # prints observations OR a 403
```
**Verify:** prints LST observations → good. **Known blocker:** a **403** = the USGS M2M account lacks *download*
access (login works, download doesn't) — external fix at ers.cr.usgs.gov (approve M2M incl. download + accept
`landsat_ot_c2_l2` terms). `dep_usgs_m2m` checks *login*; the 403 surfaces as stale `lst_c`.

## Stage 10 — Daily mapper → "farm brain"
**What:** `build_farm_brain` turns all DB facts into the per-plot, per-day field dict the KB reads (~375 fields;
UNKNOWN when no source). Runs inside `ginger_daily` (06:30) and the manual runner.
**Test:** `$DC exec app python -m app.jobs.ginger_daily --date 2026-10-21`. **Verify:** dashboard **16 Daily Run
Inspector** shows per-plot coverage (filled vs UNKNOWN), derived fields, rules fired. **Fails if:** a source repo
raises (the k_source class — now guarded) → the run trace shows the stage error.

## Stage 11 — Ginger KB engine (495 rules)
**What:** loads rules from Postgres, evaluates 296 three-valued triggers (only TRUE fires), resolves precedence,
applies delivery policy, composes 4-part Marathi messages → `ai_suggestions`.
**Verify (after Stage 10 run):**
```bash
$PSQL "SELECT rule_id, crop_stage, left(full_message_marathi,40) FROM ai_suggestions WHERE ai_model_version='ginger-engine/v1.0' ORDER BY generated_at DESC LIMIT 10;"
```
Cross-check against **Data Field Usage** doc (§ which fields gate which rules). **Fails if:** no active season/rules
firing (legit — zero is valid); duplicate rows (guarded by the 0066 unique index + diagnostics invariant).

## Stage 12 — Water-budget engine (D03-WB)
**What:** `app/domain/water_budget.py` + `PgWaterBudgetRepo` turn `water_flow_lpm` + plot geometry + variety
targets into per-plant dose/deficit ratios → the 9 D03-WB rules. **Verify:** capture geometry on the **13 Plot
Geometry** page (banner must read "geometry complete ✅"), then after a daily run check the derived fields in the
Daily Run Inspector (`vwc_status`, `stage_water_deficit_ratio`). **Fails if:** geometry incomplete (D03-WB-008
gate) → ratios UNKNOWN (safe).

## Stage 13 — Yield model (D11)
**What:** runs inside `build_farm_brain`: `Y_var × SI × Π(1 − uᵢ·Iᵢ)`, Monte-Carlo CI, per-factor attribution →
`yield_prediction_log`. **Verify:** `$PSQL "SELECT predicted_yield_quintal_per_acre, created_at FROM yield_prediction_log ORDER BY created_at DESC LIMIT 3;"`. **Note:** all factors are L4/EST placeholder confidence until Season-1
recalibration.

## Stage 14 — Advisory compose (Claude) — EXTERNAL (event-driven)
**What:** `evaluate_rules` emits `alert.created` → `advisory_subscriber` (LISTEN agro_events) → `dispatch_advisory`
→ `compose_advisory` (Claude Sonnet; **log-only if `ANTHROPIC_API_KEY` empty**) → `ai_suggestions` + verbatim
disclaimer + append-only `advisory_audit`. **Test:** trip an alert (Stage 5) → watch
`$DC logs -f app | grep -E "advisory|compose"`. **Verify:** `dep_anthropic` ✅; a new `advisory_audit` row; the
model id resolves (a stale `ANTHROPIC_MODEL_*` fails silently — the dep check guards config).

## Stage 15 — Advisory delivery (WhatsApp Meta Cloud) — EXTERNAL
**What:** `delivery_subscriber` → `deliver_advisory` → Meta `send_template` (`agroguardian_advisory_v2`, UTILITY).
Gated by `ADVISORY_DELIVERY_ENABLED` + Meta creds + a **Live** app. **Test:**
```bash
$DC exec app python scripts/dev/whatsapp_smoke.py --to 9198XXXXXXXX --text "चाचणी संदेश"
```
**Verify:** message arrives on the phone; `dep_meta_whatsapp` ✅; `$PSQL "SELECT delivery_status, count(*) FROM ai_suggestions GROUP BY 1;"`. **Gotchas:** app in Development mode silently drops to a prod number; error 131049 =
MARKETING frequency cap (template must be UTILITY — it is). Truth is in the status webhook, not the send ack.

## Stage 16 — Inbound reply (farmer → system)
**What:** `/webhooks/whatsapp` (GET verify + POST HMAC) → `handle_whatsapp_webhook` → `farmer_actions`; the nightly
`learning` job (04:00) turns those into `ai_learning_log` + D12 compliance counters. **Test:** reply to the
advisory on WhatsApp; **Verify:** `$PSQL "SELECT * FROM farmer_actions ORDER BY created_at DESC LIMIT 3;"`.

## Stage 17 — Diagnostics battery & job-run ledger (the observability you deployed)
**What:** nightly `diagnostics_battery` (07:15) + `instrument_job` on all 9 schedulers. **Test:**
```bash
$DC exec app python -m app.ops.diagnose            # on-demand full battery, red/green
```
**Verify:** dashboards **18 Scheduler Health** (every job green/last-success age), **19 System Diagnostics**
(freshness+invariants+deps), **20 Daily Health** (one verdict).

## Stage 18 — DPDP consent / erasure / retention
**What:** consent capture + notice + age gate; withdrawal/erasure (anonymise-in-place) via `fulfil_erasures`;
nightly `retention` (02:30) also purges observability tables. **Verify:** `$PSQL "SELECT consent_advisory, consent_date FROM farmer_consent LIMIT 3;"`; the disclaimer is present on every `ai_suggestions` row (IT Act §79 doesn't
apply — we generate active advice, so the disclaimer is mandatory).

## Stage 19 — Dashboards walkthrough (read-only)
Open each Streamlit page and confirm it loads with live data: 01 System Health · 03 Telemetry · 04 Advisory
Pipeline · 05 Devices & Calibration · 06 Ginger KB · 08 Live Events · 13 Plot Geometry · 14–17 Pipeline/Stage/
Daily-Run/Self-Test · **18–20 Scheduler/Diagnostics/Daily Health**.

---

# PART 3 — Why this tech stack (and not the alternatives)

For each: **what we use → the alternatives → why ours → when we'd switch.** Several rationales are the project's
own, recorded in `PROJECT_OVERVIEW.md`.

### Edge & transport

**MQTT (over TLS) — not HTTP/CoAP/AMQP/raw TCP.** Field devices are on intermittent 4G with tiny payloads and
need server→device capability later. MQTT is a lightweight pub/sub built for exactly this: small fixed header,
persistent session, QoS 1 at-least-once (we dedupe on `(node_id, recorded_at)`), last-will for liveness.
*HTTP* = request/response, no server-push, heavier per-message; *CoAP* = UDP, great for LANs but awkward through
carrier NAT/TLS; *AMQP/Kafka* = broker-heavy, overkill for one gateway. We'd revisit only at very large fleet
scale (then MQTT still wins, just with a cluster broker).

**LoRa 433 MHz (Sub↔Main) — not Wi-Fi/BLE/Zigbee/NB-IoT.** Sub nodes are buried in a field, battery-powered, and
must reach a gateway hundreds of metres away. LoRa gives long range at ultra-low power; Wi-Fi/BLE are short-range
power hogs, Zigbee is mesh-complex, NB-IoT needs a carrier subscription per node. Caveat: **433 MHz needs
regulatory clearance for scale-up** (tracked).

**ATmega328P (Sub Node) — not ESP32.** Documented: *"ultra-low power — deep sleep between reads, 20 W solar + battery, months unattended."* ESP32 is far more capable but its idle draw kills a buried solar node. The 328P's 32 KB
flash / 2 KB SRAM is why the Sub Node sends a **compact CSV frame over LoRa, never JSON** (every byte matters).
The ESP32 *is* used for the Main Node, where 4G/MQTT/TLS/SD need the headroom.

**Caddy with the `caddy-l4` plugin — not nginx/Traefik/HAProxy.** We need automatic Let's Encrypt **and** Layer-4
SNI routing so the *same* edge terminates HTTPS (API/dashboard) and MQTTS (:8883 → Mosquitto :1883). Caddy does
ACME with zero config; `caddy-l4` adds raw-TCP/TLS routing. nginx needs the commercial module or manual certbot;
HAProxy needs external ACME tooling. (RSA cert forced — the SIMCom A7672S modem is unreliable with ECDSA.)

**Mosquitto — not EMQX/HiveMQ/AWS IoT Core.** One gateway, one pilot: Mosquitto is a tiny, rock-solid, file-config
broker. EMQX/HiveMQ shine at millions of connections we don't have; AWS IoT Core violates our **no-AWS-managed-
services** portability charter (and adds lock-in + cost). Swap is trivial if the fleet explodes.

### Data & persistence

**PostgreSQL (one DB) with PostGIS + pgvector + pgcrypto — not MySQL/Mongo/Timescale/a separate vector DB.**
One datastore holds relational facts, **geospatial** plot polygons (PostGIS), **embeddings** (pgvector), and
encryption (pgcrypto) — fewer moving parts, transactional integrity, mature partitioning for time-series readings.
*MySQL* lacks first-class GIS/vector; *Mongo* loses the relational/transactional guarantees the advisory audit
needs; *TimescaleDB* is attractive for pure telemetry but we'd still need a second store for GIS/vector/relational,
so native Postgres monthly partitions win for a pilot's volume. Partition exhaustion is handled (0067 DEFAULT +
the monthly maintenance job).

**Server-side calibration — not on-device.** Raw ADC/pulses go on the wire (`v2-raw`); the backend applies
per-device constants from `device_calibration`. This lets us **re-calibrate without re-flashing** buried firmware,
keep the firmware tiny, and fix calibration bugs centrally. The trade-off (a tiny bit more server work + the raw
values must be trusted) is worth it for unattended hardware.

**Postgres `LISTEN/NOTIFY` for the event bus — not Redis Streams/Kafka/RabbitMQ.** The advisory pipeline is
event-driven (`alert.created` → compose → deliver). At pilot volume, LISTEN/NOTIFY needs **zero new
infrastructure** and is transactional with the write that triggers it. It's deliberately behind a port
(`pg_notify_bus.py`) so *"the day we outgrow it and want Redis Streams, the swap is one file; domain and use cases
don't change."* Kafka/RabbitMQ are operationally heavy for one farm.

### External data sources

**Sentinel-2 (optical) + Sentinel-1 (SAR) via CDSE — not Landsat-only/Planet/MODIS.** Sentinel-2 gives 10 m,
~5-day revisit, free; its red-edge bands (NDRE) matter for crop N/stress. **Sentinel-1 SAR is the key choice:**
radar **sees through clouds** (monsoon!), so we keep a signal when optical is cloud-blocked. *Planet* is daily but
paid/licensed; *MODIS* is 250–500 m — too coarse for a single plot; *Landsat* alone is 16-day revisit (too slow).
**CDSE (Copernicus Data Space)** is the free, open, OAuth2 + Statistical-API access to both — no Google Earth
Engine lock-in, no Sentinel Hub paid tier.

**Landsat 8/9 for LST via USGS M2M — not ECOSTRESS/MODIS LST.** We need **land-surface temperature** (thermal
band ST_B10) for crop water-stress (CWSI). Landsat C2L2 gives calibrated 100 m LST, free, with a stable M2M API.
*MODIS LST* is 1 km (too coarse); *ECOSTRESS* has irregular ISS revisit and harder access. Landsat's 16-day
revisit is acceptable because LST changes slower than we alert.

**Open-Meteo for forecasts — not IMD/OpenWeather/Tomorrow.io/Visual Crossing.** Open-Meteo is **free, no API key,
global, hourly, generous rate limits**, and exposes the agronomy variables we need (ET₀, solar radiation, wind
gusts, VPD inputs). *IMD* is authoritative for India but its API is unreliable/rate-limited (we still use IMD
station **normals** for rainfall-deviation); *OpenWeather/Tomorrow.io/Visual Crossing* are paid at our cadence.
No-key means nothing to rotate or leak.

**Anthropic Claude (Sonnet for compose, Haiku for triage) via a `ModelRole` abstraction — not GPT/Gemini/open
models.** The advice must be safe, well-grounded Marathi with strong instruction-following and a low hallucination
rate on a safety-critical message; Claude is the house model and the platform is Anthropic-built. Crucially, model
choice is **never hardcoded** — it's `ModelRole.PRIMARY/TRIAGE`, so swapping providers/models is a config change.
We'd A/B another model behind the same port if cost/quality shifted.

**Meta WhatsApp Cloud API — not SMS/IVR/a native app (yet).** WhatsApp is where Marathi farmers already are, with
rich text + a reply channel for the feedback loop. Documented as a **deliberate stopgap:** *"WhatsApp works for a
1-farm pilot but doesn't scale to a real farmer UX — no read receipts, no dashboards, no offline caching; push +
a real app is the product; WhatsApp is a bridge."* SMS is 160-char/no-media; IVR is costly and low-bandwidth. The
sender is behind a port, so a Twilio route or an app push can replace it without touching the pipeline.

### Application & ops

**FastAPI + SQLAlchemy 2.0 async + asyncpg — not Django/Flask.** Async fits an I/O-bound ingest + external-API
app; FastAPI gives typed request/response + OpenAPI for free; SQLAlchemy async + asyncpg is the fastest mature
async Postgres path. Django is batteries-heavy (ORM/admin we don't want in a hexagonal design); Flask is sync-first.

**Hexagonal / ports-and-adapters architecture — not a conventional layered monolith.** Every external dependency
(DB, MQTT, LLM, WhatsApp, satellite, event bus) is a **port** with a swappable adapter, and the domain is pure
(enforced by AST purity tests). This is *why* every "we'd switch by changing one file" claim above is true, and
why the calibration/rules are unit-testable without infra. The cost (more interfaces) buys testability + provider
portability — a core project charter.

**APScheduler (in-process) — not Celery/system cron.** The nightly/daily jobs are few and light; APScheduler runs
in the app process with no broker/worker fleet (Celery) and no separate crontab outside the container (harder to
ship/observe). Each tick is now wrapped by `instrument_job` for the job-run ledger. Celery becomes worth it only
with heavy fan-out or retries we don't have.

**Streamlit for the ops dashboard — not React/Retool.** It's an **internal** ops/agronomy tool; Streamlit turns a
Python query into a page in minutes, reads Postgres directly (read-only engine), and needs no separate frontend
build/deploy. React is the farmer-facing product later; Retool is paid/hosted. (Behind the same portability logic:
*"swapping Streamlit for React"* doesn't touch the backend.)

**ChromaDB now, pgvector later — a documented, deliberate deferral.** Chroma is a quick embeddings store for the
KB/RAG bits today; the plan explicitly notes *"swapping ChromaDB for pgvector"* collapses to one adapter when we
want one-fewer-container. pgvector (already in the Postgres image) is the end state.

**AWS Lightsail (Mumbai) — not EC2/GCP/Azure.** Fixed-price, simple VPS with **in-India data residency** (DPDP) at
the lowest ops overhead for a pilot; EC2 is more knobs/cost-variance than one box needs. The charter forbids
AWS-*managed* services (so no RDS/IoT Core) — Lightsail is "just a Linux box," which keeps us portable to any VPS.

**Prometheus + Grafana + Sentry — standard, swappable observability.** Prometheus scrape + Grafana dashboards +
Sentry error-capture are the de-facto open stack; nothing proprietary. (Sentry is wired but DSN-gated; our
dashboards-first debugging layer from this cycle complements it.)

### Firmware specifics
- **SD-card outbox on the Main Node** (`/outbox.jsonl`, 5 MB) buffers Sub-Node telemetry during a 4G outage and
  re-publishes on reconnect (`backlog_pending=true`) — chosen so a network gap never loses a reading; heartbeats
  are *not* queued (liveness must be live).
- **Deep sleep + PCINT flow counter** on the 328P keeps the irrigation pulse count accurate through sleep — a
  firmware design choice that makes server-side flow calibration trustworthy.

---

# PART 4 — External data sources: deep-dive testing

| Source | Auth | Smoke test | ✅ looks like | Common failure |
|---|---|---|---|---|
| **CDSE (Sentinel)** | OAuth2 client-credentials → `COPERNICUS_TOKEN_URL`; Statistical API | `fetch_satellite_once.py`, `probe_cdse_raw.py`; `dep_cdse` | token 200 + NDVI/SAR rows | blank creds (skip); no plot polygon (`skipped_no_polygon`); revisit gap (warn) |
| **USGS M2M (Landsat LST)** | `login-token` (username+token) → apiKey | `lst_smoke.py --days 30`; `dep_usgs_m2m` | prints LST observations | **403 = no download access** (external approval at ers.cr.usgs.gov) |
| **Open-Meteo (forecast)** | none (keyless) | Scheduler Health `weather_forecast`; `forecast_coverage` check | `max(forecast_for_date) >= today` | provider unreachable (rare) → job failed in ledger |
| **Anthropic (Claude)** | `ANTHROPIC_API_KEY` | `dep_anthropic`; watch compose logs | key set + model id resolves | empty key → compose is log-only; stale `ANTHROPIC_MODEL_*` id |
| **Meta WhatsApp** | `META_WHATSAPP_TOKEN` + phone id; app Live | `whatsapp_smoke.py --to …`; `dep_meta_whatsapp` | message delivered; Graph 200 | Dev-mode drop; 131049 (needs UTILITY template); delivery truth only in status webhook |

**Golden rule for external sources:** `make diagnose` runs all five checks at once (CDSE/USGS/Anthropic/Meta +
forecast freshness) — start there, then use the per-source smoke script to dig into any red.

---

# PART 5 — Master sequential checklist

Bring-up
- [ ] `$DC ps` all Up/Healthy · `alembic current` = 0069 · `make diagnose` captured as a baseline
- [ ] `CALIBRATION_MODE` is `false` (so device-health rules actually fire during the test)

Ingest → persistence
- [ ] Stage 1: TLS handshake OK + authenticated `mosquitto_pub` accepted
- [ ] Stage 2: `fake_main_node.py` / `inject_test_reading.py` row ingested; duplicate dropped (idempotent)
- [ ] Stage 3: calibrated values sane (Pipeline Inspector raw↔calibrated); self-test exit 0
- [ ] Stage 4: rows in `node_sensor_readings` / `weather_station_readings` / `main_node_readings`; partition check ✅
- [ ] Stage 5: engineered reading trips LOW_WATER + LOW_BATTERY in `alerts_notifications`
- [ ] Stage 6: Pipeline Inspector + Stage Health populated

External sources
- [ ] Stage 7: `forecast_coverage` ✅ (`max(forecast_for_date) >= today`)
- [ ] Stage 8: `fetch_satellite_once` returns rows; `dep_cdse` ✅; `satellite_fresh` ok/warn
- [ ] Stage 9: `lst_smoke.py` prints observations (or the known 403 is understood)

Decision → advisory → delivery
- [ ] Stage 10: `ginger_daily --date` run; Daily Run Inspector coverage looks right
- [ ] Stage 11: `ai_suggestions` rows with Marathi messages; no duplicates
- [ ] Stage 12: Plot Geometry "complete ✅"; water-budget derived fields present
- [ ] Stage 13: a `yield_prediction_log` row
- [ ] Stage 14: `dep_anthropic` ✅; `advisory_audit` row written on an alert
- [ ] Stage 15: `whatsapp_smoke.py` delivered; `dep_meta_whatsapp` ✅ (or creds pending, understood)
- [ ] Stage 16: reply shows up in `farmer_actions`

Platform
- [ ] Stage 17: Scheduler Health all-green; Diagnostics no unexpected fail; Daily Health = ✅
- [ ] Stage 18: consent rows present; disclaimer on every advisory
- [ ] Stage 19: every dashboard page loads with data

---

# PART 6 — Expected value ranges & calibration sanity

Spot bad data fast. Flag anything outside these (the ingest validators cover some; the rest are eyeball checks
on Telemetry / Pipeline Inspector). *(Ranges are pilot-typical; tune per device.)*

| field (table) | sane range | flag when |
|---|---|---|
| `soil_moisture_avg_pct` (node) | 0–100 % | <0 or >100 (calibration), or identical for many readings (stuck probe) |
| `soil_temp_c` (node) | 0–50 °C | implausible for Kannad; stuck value |
| `soil_ph` (node) | 3–10 | out of band ⇒ sensor/calibration |
| `water_flow_lpm` (node) | ≥ 0 | negative; or null while `pump_running=true` (flow sensor silent → D03-WB-006) |
| `battery_voltage_v` (node) | pack-dependent (pilot ~8.6 V, alert <low-V) | >20 ⇒ bad calibration (self-test catches); flat-lining |
| `signal_rssi_dbm` (node) | −50…−105 usable | worse than ~−105 ⇒ weak 4G (−111 preceded the 18-Oct outage) |
| `air_temp_max_c` (weather) | −5…50 °C | out of band; station vs forecast mismatch |
| `lst_c` (satellite) | 0–60 °C | out of band ⇒ scene/parse issue |
| `ndvi_value` (satellite) | −1…1 (crop 0.2–0.9) | outside [−1,1]; sudden jump ⇒ cloud/scene |
| forecast rainfall/ET fields | ≥ 0 | negatives ⇒ provider parse |

Calibration sanity: on **Pipeline Inspector**, raw↔calibrated must agree with `device_calibration` (soil
`%=(DRY−raw)/(DRY−WET)×100`; `flow=pulses×60/(window_s×pulses_per_L)`). The self-test re-derives these:
`$DC exec app python -m app.infra.pipeline_selftest` (exit 0).

# PART 7 — Negative / failure-mode tests (deliberately break it)

Confirm the system degrades safely, not silently.

- [ ] **Duplicate reading** — publish the same `(node_id, recorded_at)` twice ⇒ exactly **one** row (idempotent).
- [ ] **Bad calibration** — a battery reading >20 V ⇒ pipeline `overall=fail` (self-test case).
- [ ] **Flow first-cycle** — `window_s=0` ⇒ `water_flow_lpm` null + a `warn` (uncomputable, not a crash).
- [ ] **NPK read fail** — `npk_ok=false` ⇒ NPK fields null + `warn` (not a crash).
- [ ] **Missing polygon** — a plot with no `gps_boundary_geojson` ⇒ satellite/Landsat `skipped_no_polygon`, not an error.
- [ ] **Claude key empty** — `ANTHROPIC_API_KEY` unset ⇒ compose is **log-only** (`dep_anthropic` skip), pipeline still runs.
- [ ] **WhatsApp Dev-mode / bad number** — send to a non-allowlisted / placeholder number ⇒ a REJECTED status
      (e.g. `131009`/`131049`), surfaced — not a crash. (`131009` on `9198XXXXXXXX` = the literal placeholder.)
- [ ] **CALIBRATION_MODE=true** ⇒ device-health rules do **not** fire (by design) — confirm, then set false to test alerts.

# PART 8 — Minute-detail invariant checks

- [ ] **Idempotency:** re-ingest ⇒ row count unchanged (`(node_id, recorded_at)` for readings; `(master_node_id, recorded_at)` for weather).
- [ ] **Cooldown:** a 2nd trip of the same `(plot, alert_type)` within its cooldown ⇒ **not** re-created.
- [ ] **Daily-unique advisories:** `$PSQL "SELECT plot_id,(generated_at AT TIME ZONE 'UTC')::date d,rule_id,count(*) FROM ai_suggestions WHERE ai_model_version='ginger-engine/v1.0' AND rule_id IS NOT NULL GROUP BY 1,2,3 HAVING count(*)>1;"` ⇒ **0 rows** (0066 index + diagnostics invariant).
- [ ] **Crop-age not frozen:** recomputed from `sowing_date` must equal what today's advisory used (the old bug stored a snapshot) — cross-check on Daily Run Inspector.
- [ ] **Disclaimer:** every `ai_suggestions` row carries the verbatim Marathi disclaimer; `advisory_audit` is append-only (trigger-enforced).
- [ ] **Precedence:** VWC probe > water-budget > satellite; a SUPPRESSING rule silences the suppressed one (check on a day both would fire).
- [ ] **Tz run-day:** the ginger "today" is computed in `Asia/Kolkata`; `generated_at` stored at UTC-midnight of the IST run-day.
- [ ] **Partition window:** current + `PARTITION_MONTHS_AHEAD` partitions exist + the DEFAULT catch-all (`partition_default_present` ✅).
- [ ] **Retention purge:** `pipeline_trace` / `plot_run_trace` / `job_run` / `diagnostics_result` bounded by their retention days (rows older than the window are gone after the nightly retention tick).
- [ ] **Heartbeat parity:** `max(recorded_at)` of `node_sensor_readings` ≈ that of `main_node_readings` — a divergence localizes sub-node vs gateway (see Part 9).

# PART 9 — "No readings / device offline" triage runbook

When `readings_fresh` fails (or you just see no new rows), run this ladder — the first "wrong" step localizes it.
*(This is the exact sequence that diagnosed the 18-Oct outage; corrected column names.)*

```bash
# 0. How stale, and did BOTH streams stop together? (together ⇒ gateway/edge, not sub-node)
$PSQL "SELECT max(recorded_at) FROM node_sensor_readings;"
$PSQL "SELECT max(recorded_at) FROM main_node_readings;"
# 1. Did the watchdog notice? (should raise device_offline on its 6-h cooldown)
#    NOTE: alert_type is the LOWERCASE enum value — 'device_offline', not 'DEVICE_OFFLINE' (a case mismatch returns 0 rows).
$PSQL "SELECT alert_type,severity,device_id,triggered_at FROM alerts_notifications WHERE alert_type='device_offline' ORDER BY triggered_at DESC LIMIT 5;"
# 2. Is the device even reaching the broker? (DECISIVE)
$DC logs --since 120h mosquitto | grep -iE "new connection|disconnect|denied|error" | tail -40
# 3. Edge/TLS — is the device hitting Caddy but failing the handshake? (reset / bad record MAC ⇒ modem/link)
$DC logs --since 168h caddy | grep -iE "error|8883|tls|certificate" | tail -30
# 4. Server cert sane? (RSA, not expiring, handshakes from a GOOD network)
IP_DASHES=<your-ip-with-dashes>
echo | openssl s_client -connect mqtts-$IP_DASHES.sslip.io:8883 -servername mqtts-$IP_DASHES.sslip.io 2>/dev/null | openssl x509 -noout -dates -issuer | head
openssl s_client -connect mqtts-$IP_DASHES.sslip.io:8883 -servername mqtts-$IP_DASHES.sslip.io </dev/null | grep -E "Verify return code|Public Key"
# 5. Last readings before the cutoff — battery / signal clue
$PSQL "SELECT recorded_at,battery_voltage_v,signal_rssi_dbm FROM node_sensor_readings ORDER BY recorded_at DESC LIMIT 5;"
```

**Branches:** server cert valid + laptop handshake OK + modem resetting on weak RSSI ⇒ **device/4G side** (antenna,
SIM data plan, power-cycle; the SD outbox replays on reconnect). Mosquitto shows **no** device connection in days
⇒ device fully offline. Handshake fails from your laptop too ⇒ **server/Caddy** (clear `/data/caddy/certificates`
+ restart Caddy to re-issue RSA).

---

*Maintainer note: regenerate the stage list / flags when a scheduler, migration head, or external provider
changes. Pair this with `SYSTEM_AND_STATUS.md` (live-vs-pending), `DATA_FIELD_USAGE.md` (field-level),
`HARDENING_AND_OBSERVABILITY_PLAN.md` (findings + roadmap), and `END_TO_END_GUIDE.md` (narrative).*
