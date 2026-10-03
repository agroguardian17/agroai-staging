# AgroGuardian V2 — The Complete End-to-End Guide

**Audience:** everyone — from a non-technical stakeholder who wants to understand *what this is and why it matters*, to a new engineer who needs to understand *every moving part*. Read Part I for the story; Parts II–VII for the system; Part VIII for where we stand.

**Status:** current as of 3 Oct 2026 · migration head **0063** · KB **495 rules / 296 triggered**. Ground truth is always the code in `agro_backend/` + `firmware/`; this guide is the map. For the exhaustive per-column database catalog see [`DATA_INVENTORY.md`](DATA_INVENTORY.md); for live-vs-pending status see [`SYSTEM_AND_STATUS.md`](SYSTEM_AND_STATUS.md).

---

# Table of contents

- **Part I — The non-technical story**: the problem, the solution, the actors, the pilot, a day in the life.
- **Part II — The technology from zero**: the big picture, the journey of one reading, and plain-language tutorials for every unfamiliar piece (LoRa, MQTT, Mosquitto, Caddy, Postgres & its extensions, Chroma, and the rest).
- **Part III — Hardware & firmware**: the Sub Node, the Main Node, the sensors, the wire format.
- **Part IV — The database**: how the 60 tables are organised, what each group holds, and how rows get filled.
- **Part V — The Knowledge Base**: what it is, the anatomy of a rule, the trigger language, how advice is chosen and delivered, and how it is authored and compiled.
- **Part VI — The engines & data flows**: every pipeline, every scheduled job.
- **Part VII — Deploy & operations**: how it runs, how to switch features on, how we watch it.
- **Part VIII — Where we stand & what's left.**

---
---

# PART I — THE NON-TECHNICAL STORY

## 1. The problem

Smallholder ginger farmers in the Kannad block of Chhatrapati Sambhajinagar district (Marathwada, Maharashtra) make daily, high-stakes decisions — *when to irrigate, how much, when to spray, when to feed the crop* — with almost no objective information. They go by feel, by habit, and by what a neighbour did. Ginger is a 7–8 month, water-hungry, disease-prone, high-investment crop, so a few wrong calls across a season can wipe out the margin.

Five specific failure modes cost them money and yield again and again:

1. **Over-irrigation** — water is scarce and electricity for the pump is rationed, yet the instinct under stress is "more water is safer." Waterlogged ginger rots.
2. **Under-irrigation** — the opposite error during a dry spell, stunting the rhizome during the critical bulking window.
3. **Pump dry-run** — running the pump when the source is empty burns out the motor (a large unplanned cost).
4. **Frost / cold damage** — an unforecast cold night damages the crop with no warning.
5. **No feedback loop** — nobody measures what actually happened, so the same mistakes repeat every season and no learning accumulates.

**What this project explicitly does *not* try to solve:** pest *detection* by image, live market pricing, or subsidy paperwork. The scope is deliberately narrow: get the water, nutrient, weather and disease-risk decisions right, in the farmer's language, on time.

## 2. The solution

AgroGuardian is a **precision-agriculture IoT + AI advisory platform**. In one sentence:

> Buried sensors measure the soil and the weather → the readings travel by radio and mobile network to a server → the server runs the numbers through an agronomy "rule book" and an AI → the farmer gets a short, plain-Marathi message on WhatsApp telling them exactly what to do that day.

The guiding principle the whole team repeats:

> **"The entire stack exists to produce one good four-sentence Marathi message at 7 AM."**

Everything — the hardware, the radios, the database, the rule engine, the AI — is in service of that one daily message being *correct, timely, and actionable*. If a farmer reads it over morning tea and does what it says, the system worked.

**How it solves each failure mode:**

| Failure mode | How AgroGuardian addresses it |
|---|---|
| Over-irrigation | Soil-moisture probe + a water-budget model + saturation veto rules say "stop / don't irrigate today." |
| Under-irrigation | Dry-spell + stage-aware + per-plant deficit rules say "irrigate N litres." |
| Pump dry-run | Flow + pressure sensors + a real-time "dry_run" safety rule fire a critical alert within minutes. |
| Frost / cold | Weather-station + forecast rules warn the night before. |
| No feedback loop | Every advisory is logged; farmer actions are recorded; a nightly "learning" job turns outcomes into model adjustments. |

## 3. The actors

| Actor | Who / what | How they interact |
|---|---|---|
| **Farmer** | Marathi-speaking smallholder. The end beneficiary. | Receives WhatsApp advisories; logs in by phone OTP; reports what they did. |
| **Agronomist / ops team** | The humans who tune and supervise the system (English). | Use a Streamlit dashboard; can override individual rules per plot; review advisory quality. |
| **Sub Node** | A buried battery sensor box (microcontroller). | Reads soil/NPK/flow every 5 minutes, sends one radio message, sleeps. No internet. |
| **Main Node** | A solar/mains gateway box (ESP32 + 4G). | The *only* device with internet. Receives the radio messages, adds weather, and forwards everything to the server over the mobile network. |
| **Backend** | The server software — everything in `agro_backend/`. | Ingests data, runs the engines, composes and delivers advice, stores everything. |

## 4. The pilot scope

Deliberately tiny, to prove the whole chain before scaling:

- **1 farm, 1 farmer, 2 plots, 1 Main Node, 1 Sub Node.** Crop: ginger, variety **Mahima**, Kharif 2026 season.
- `AGR-SN-0001 → PLOT_PILOT_001` has the hardware (sensors). `PLOT_PILOT_002` is **satellite-only** (no buried sensor; monitored from space).
- Location: Kannad, Chhatrapati Sambhajinagar, Marathwada.

## 5. A day in the life of the system

1. **All day, every 5 minutes:** the buried Sub Node wakes, measures the soil and sends a tiny radio packet; the Main Node forwards it to the server, which stores it and checks the 7 safety rules (e.g. is the pump dry-running right now?).
2. **02:30 at night:** the server pulls fresh satellite imagery for each plot (crop vigour, moisture).
3. **03:00:** it fetches tomorrow's weather forecast.
4. **04:30:** it pulls thermal/land-surface-temperature imagery (crop water stress).
5. **06:30 morning:** the big moment — the server assembles everything it knows about each plot into a single "Farm Brain" snapshot, runs it through the **495-rule agronomy knowledge base**, and composes the day's advisory. An AI (Claude) phrases it naturally in Marathi.
6. **~7 AM:** the advisory is delivered to the farmer's WhatsApp (once the messaging credentials are live).
7. **Throughout:** the farmer can reply/log what they did; the agronomist watches the dashboard; a nightly job turns outcomes into learning.

---
---

# PART II — THE TECHNOLOGY, EXPLAINED FROM ZERO

## 6. The 10,000-foot architecture

```
   ┌──────────┐   LoRa radio    ┌───────────┐   MQTT over 4G (TLS)   ┌─────────────────────────────┐
   │ Sub Node │ ──433 MHz CSV──▶│ Main Node │ ──────────────────────▶│  EDGE: Caddy ▶ Mosquitto     │
   │ (buried) │                 │ (gateway) │                         │  (TLS termination + broker)  │
   └──────────┘                 └───────────┘                         └───────────────┬─────────────┘
     soil, NPK,                   + weather station                                    │ MQTT
     flow, battery                + 4G modem + SD buffer                               ▼
                                                                        ┌─────────────────────────────┐
   External data:                                                       │  BACKEND (FastAPI, Python)   │
   • Sentinel-2/1 satellite (CDSE)  ─────────────────────────────────▶ │  IngestBroker → repositories │
   • Landsat LST (USGS)             ─────────────────────────────────▶ │  Rule engines + mapper       │
   • Open-Meteo weather forecast    ─────────────────────────────────▶ │  Advisory pipeline           │
                                                                        └───────┬──────────────┬───────┘
                                                                                │              │
                                                                     ┌──────────▼───┐   ┌──────▼───────┐
                                                                     │ PostgreSQL   │   │ Anthropic    │
                                                                     │ (+PostGIS…)  │   │ Claude (AI)  │
                                                                     └──────────────┘   └──────┬───────┘
                                                                                               │
                                                                                      ┌────────▼────────┐
                                                                                      │ WhatsApp (Meta) │ ▶ Farmer
                                                                                      └─────────────────┘
   Humans: Agronomist/ops ─▶ Streamlit dashboard ─▶ reads/writes Postgres directly
```

## 7. The journey of one reading (end-to-end)

This single narrative touches almost every component; the tutorials in §8 then explain each named piece.

1. A **Sub Node** buried in PLOT_PILOT_001 wakes from deep sleep, reads its sensors (soil moisture, temperature, NPK, battery, water flow, pressure), and builds one line of CSV text.
2. It transmits that line over **LoRa** (a long-range, low-power radio) at 433 MHz. LoRa is used because the sensor is buried in a field with no WiFi and must sip battery — it can't run 4G itself.
3. The **Main Node** (the only device with internet) hears the LoRa packet, parses it, adds its own weather-station readings, and publishes it as a JSON message over **MQTT** — a lightweight messaging protocol designed for exactly this kind of intermittent, low-bandwidth device-to-server link — carried over the **4G** mobile network, encrypted with **TLS**.
4. The message arrives at the server's **edge**. **Caddy** (with the `caddy-l4` add-on) terminates TLS and routes the encrypted MQTT stream to **Mosquitto**, the MQTT broker, which hands it to the backend.
5. The backend's **IngestBroker** receives the message, applies per-device **calibration** (raw sensor counts → real engineering units like % moisture and L/min), and **UPSERTs** it into the `node_sensor_readings` table in **PostgreSQL** — idempotently, so a re-sent message never double-counts.
6. On that same message, the **7 device-health rules** run immediately. If one fires (e.g. `dry_run`), an alert is written and a `NOTIFY` is published, which wakes the **advisory subscriber** to compose and (eventually) deliver a message.
7. Every night the scheduled jobs enrich the plot's picture (satellite, forecast, thermal). At 06:30 the **Farm Brain mapper** assembles all of it into one field dictionary, the **Ginger KB engine** evaluates the 296 triggered rules against it, **Claude** phrases the winning advice in Marathi, and it's stored (and delivered over **WhatsApp** once live).

## 8. Infrastructure tutorials — what each piece is and *why* we use it

Each entry: **What it is** · **Why we need it here** · **How we use it**.

### 8.1 LoRa (433 MHz radio)
**What:** "Long Range" radio — a wireless technology that trades data *speed* for *distance and battery life*. It can send a few hundred bytes over kilometres on a coin-cell-scale power budget.
**Why:** the sensor is buried in a field. There is no WiFi, and a 4G modem in every buried node would be expensive and power-hungry. LoRa lets a tiny battery-powered node talk to one gateway far away.
**How:** the Sub Node sends one short CSV line per 5-minute cycle (SF7/BW125/CR4-5, TxPower 17). Only the Main Node listens; it's the bridge from radio to internet.

### 8.2 MQTT
**What:** a **publish/subscribe messaging protocol** built for unreliable, low-bandwidth, many-device networks. Devices *publish* messages to named *topics*; servers *subscribe* to those topics. It tolerates drops and reconnects gracefully.
**Why:** classic request/response HTTP is heavy and brittle for a 4G field device. MQTT keeps a lightweight persistent connection, buffers, and resumes — ideal for telemetry.
**How:** the Main Node publishes to topics like `agro/v2/<tenant>/<farm>/<node>/telemetry` with QoS 1 (at-least-once). The backend subscribes to `agro/v2/+/+/+/telemetry` (the `+` are wildcards) and dispatches by the message's `$schema`.

### 8.3 Mosquitto
**What:** the most common open-source **MQTT broker** — the server process that receives published messages and fans them out to subscribers.
**Why:** something has to sit in the middle accepting device connections and delivering to the backend. Mosquitto is that middleman.
**How:** runs as a container; the backend connects to it as a subscriber; devices connect (through Caddy) as publishers, authenticated by a per-device password (Argon2id-hashed in `device_registry.broker_secret_hash`).

### 8.4 TLS, Caddy, and `caddy-l4`
**What:** **TLS** is the encryption that makes "https" and "mqtts" secure. **Caddy** is a modern web server/reverse proxy famous for *automatic* HTTPS certificates (it fetches and renews Let's Encrypt certs on its own). **`caddy-l4`** is an add-on that lets Caddy route raw **Layer-4 (TCP)** streams, not just HTTP.
**Why:** device traffic must be encrypted end-to-end, and the server needs valid TLS certificates without manual renewal. MQTT is a raw TCP stream (not HTTP), so plain Caddy isn't enough — `caddy-l4` routes the encrypted MQTT stream (port 8883) to Mosquitto while normal Caddy handles the HTTPS API (443) and the ACME certificate challenge (80).
**How:** Caddy listens on 80/443/8883; it terminates TLS and forwards MQTT to Mosquitto and HTTPS to the FastAPI app. We use **sslip.io** (a free DNS service that maps `mqtts-13-207-20-67.sslip.io` → `13.207.20.67`) so we get a real hostname for certificates without buying a domain.

### 8.5 PostgreSQL and its extensions
**What:** **PostgreSQL** ("Postgres") is the relational database — the system's single source of truth. We run Postgres 15 with three extensions:
- **PostGIS** — adds geospatial types and functions (store plot boundary polygons, compute areas, match satellite tiles to plots).
- **pgvector** — adds a vector type for AI embeddings (semantic search / future RAG over agronomy text).
- **pgcrypto** — cryptographic functions (hashing, random IDs) inside the database.
**Why:** the data is deeply relational (farmers → farms → plots → seasons → readings → advisories) and needs strong guarantees (transactions, constraints, foreign keys). PostGIS is essential because plots and satellite data are geographic. pgvector future-proofs AI retrieval. pgcrypto keeps secrets handling in-DB where useful.
**How:** 60 tables; monthly **partitioning** on the high-volume `node_sensor_readings`; **Row-Level Security** + roles; strict CHECK constraints (e.g. rule severities, recoverability classes). Schema changes are versioned with Alembic (§14).

### 8.6 ChromaDB
**What:** a **vector database** — stores text embeddings and does similarity search.
**Why:** for AI features that need "find the most relevant agronomy knowledge for this situation" (retrieval-augmented generation). It's wired as a seam for future use.
**How:** runs as a container (`chroma`), multilingual embedding model configured; not on the critical daily path yet.

### 8.7 FastAPI + async + asyncpg
**What:** **FastAPI** is the Python web framework serving the HTTP API. **async** (asynchronous) Python lets one process handle many I/O operations concurrently without threads. **asyncpg** is the fast async Postgres driver; **SQLAlchemy 2.0** is the ORM/query layer on top.
**Why:** the backend is I/O-bound (lots of DB and network calls); async handles many concurrent requests and background jobs efficiently on a small VPS.
**How:** FastAPI serves `/api/v1/...` endpoints (auth, plots, readings, alerts, advisories, health). The MQTT broker and schedulers run inside the same app process via the FastAPI "lifespan."

### 8.8 APScheduler
**What:** "Advanced Python Scheduler" — runs functions on a schedule (cron-like) inside the app.
**Why:** the daily pipeline (satellite 02:30, forecast 03:00, Landsat 04:30, ginger advisory 06:30, learning, QA digest, retention) needs reliable timed execution.
**How:** each job is registered at startup with a cron trigger in the configured timezone (Asia/Kolkata); each scheduler module is independently toggleable by an env flag.

### 8.9 Prometheus + Grafana
**What:** **Prometheus** scrapes and stores time-series **metrics** (counters, timings). **Grafana** draws dashboards and alerts from them.
**Why:** to know the system is healthy — messages ingested, rules fired, job durations, errors — without reading logs by hand.
**How:** the app exposes `/metrics`; Prometheus scrapes it; Grafana visualises; alert rules live in `deploy/prometheus/alerts.yml`.

### 8.10 Docker, Docker Compose, Coolify
**What:** **Docker** packages each service into a container (a reproducible, isolated unit). **Docker Compose** runs the whole multi-container stack from one file. **Coolify** is an optional self-hosted PaaS that manages Compose deployments with a UI and auto-deploy-on-push.
**Why:** so the same stack (Caddy, Mosquitto, Postgres, app, …) runs identically on a laptop and on the server, started with one command.
**How:** `docker-compose.prod.yml` defines every service, network (`internal`/`edge`), and volume. Deploy = pull the new image, `up -d`, `alembic upgrade head`.

### 8.11 Tailscale
**What:** a zero-config private network (VPN) that connects your machines securely.
**Why:** so the team can reach admin surfaces (metrics, the box) privately, without exposing them to the public internet.
**How:** the VPS joins the tailnet; admin-only endpoints are gated to it.

### 8.12 Alembic
**What:** the database **migration** tool for SQLAlchemy — every schema change is a numbered, reversible script.
**Why:** the schema evolves constantly; migrations make changes versioned, repeatable, and safe to roll forward/back across environments.
**How:** scripts `0001 … 0063` in `alembic/versions/`; deploy runs `alembic upgrade head`. KB changes ship as special "reload" migrations (§24).

### 8.13 structlog
**What:** structured logging — logs are JSON objects (fields) in production, pretty text in development.
**Why:** machine-parseable logs are searchable and alertable. (Lesson learned: JSON logging must include a *traceback processor*, or exceptions log `"exc_info": true` with no stack — see §35.)
**How:** `app/lib/logging.py`; every module binds `log = structlog.get_logger(__name__)`.

### 8.14 Anthropic Claude (Sonnet + Haiku)
**What:** the large language model that phrases advisories in natural Marathi. **Sonnet** = the capable model (advisory composition); **Haiku** = the cheap/fast model (triage/classification).
**Why:** the KB decides *what* to say (deterministically, auditable); Claude makes it *read naturally* for a farmer. The split keeps the agronomy decisions rule-based and the language human.
**How:** `app/infra/llm/`; model chosen by a semantic `ModelRole`; requires `ANTHROPIC_API_KEY`. If the key is empty a log-only stub runs so nothing breaks in dev.

### 8.15 Meta WhatsApp Cloud API
**What:** the official API for sending WhatsApp messages from a business number.
**Why:** WhatsApp is how rural Maharashtra actually communicates; it's the delivery channel for the daily advisory and the OTP login.
**How:** `app/infra/whatsapp/`; a template message (`agroguardian_advisory_v2`, UTILITY category) carries the whole Marathi body; a webhook receives inbound. Needs Meta credentials + a Live app (currently pending).

### 8.16 Streamlit
**What:** a Python framework for building data dashboards quickly.
**Why:** the agronomy/ops team needs an internal UI to inspect data, enter plot facts, and tune rules — without building a full web frontend.
**How:** the `dashboard/` app reads Postgres directly (read-only by default); specific pages (Data Entry, **Plot Geometry**) write. For the pilot, *all human data entry happens here* — the farmer mobile app is a later phase.

---
---

# PART III — HARDWARE & FIRMWARE

## 9. The two devices

### Sub Node (`firmware/sub_node/` — ATmega328P, FINAL v2.1)
A buried, battery-powered sensor box. Every 5 minutes it wakes, reads:
- **Soil moisture** (capacitive probe, A0) and **soil temperature** (DS18B20).
- **NPK + pH + EC** (RS-485 Modbus soil sensor, power-gated by a MOSFET to save battery).
- **Battery voltage**, **water pressure** (ADC), **water flow** (pulse-counted even during sleep).

It computes the window since its last send, builds **one CSV line**, transmits it over LoRa, blinks a status LED, and deep-sleeps. It has **no clock of its own** reliable enough and **no internet** — it just shouts one line and sleeps.

### Main Node (`firmware/main_node/` — ESP32 + A7672S 4G, FINAL v2.1)
The gateway. It:
- Listens for Sub Node LoRa packets and parses the CSV.
- Runs its own **weather station** (BME280 temp/humidity/pressure, INA219 power, rain gauge, anemometer, wind vane) via I²C.
- Keeps time (DS3231 real-time clock + NTP), rejecting implausible years.
- Publishes everything as JSON over **MQTT-TLS** on 4G (Airtel APN).
- **Buffers to an SD card** when offline and drains the backlog on reconnect, so no data is lost during an outage.
- Sends a **master heartbeat** every 5 minutes so the backend knows it's alive even when the Sub Node is quiet.

## 10. The three message formats (`$schema`)

The backend understands three message shapes, dispatched by a `$schema` field:
- **`…/telemetry/v2`** — pre-calibrated engineering units (used by test simulators).
- **`…/telemetry/v2-raw`** — raw sensor counts + a calibration reference; the backend converts them using the per-device `device_calibration` row. This is what the real firmware sends.
- **`…/telemetry/v2-master`** — the Main-Node-only heartbeat (its own weather + "is the Sub Node alive?" flags).

**Calibration** turns raw into real, e.g. soil `% = (DRY − raw)/(DRY − WET) × 100`, flow `L/min = pulses × 60 / (window_s × pulses_per_L)`. A clock-skew safety net rewrites impossible timestamps to server time and flags them.

---
---

# PART IV — THE DATABASE

> This part explains **how the database is organised and how rows get filled**, group by group. The **complete field-by-field catalog** — every column, its type, its source label, and notes — lives in [`DATA_INVENTORY.md`](DATA_INVENTORY.md) (1,100+ lines, the maintained reference). Read this part to understand the *shape and the flow*; use DATA_INVENTORY as the dictionary.

## 11. How to read a field's "source"

Every column has a provenance label — *who fills it and how*:
- **FI** = Farmer Input · **FO** = Field Ops · **TECH** = technician at install · **OPS** = ops/agronomy team · **SN/FW** = device/firmware · **CAL** = calibration · **SYS** = system/auto · **DERIVED** = computed by the backend from other data.

This matters because a KB rule can only fire if the fields it reads actually have a source. Many rules are "dormant" precisely because their fields are `FI`/`FO` fields that the farmer app (not yet built) would capture.

## 12. The 60 tables, by group

**Group A — Identity:** `tenants`, `farmers`, `farms`, `plots`, `crop_seasons`. The hierarchy everything hangs off: a tenant has farmers, who have farms, which have plots, which have crop seasons. *Filled by:* ops + farmer intake (via the dashboard today).
- `plots` holds area, GPS, soil type, the **boundary polygon** (`gps_boundary_geojson` — required for satellite), and `plot_status` (operational lifecycle: active/fallow/harvested).
- `crop_seasons` is the richest table: identity (variety, dates), the **agronomy plan** (bed geometry, drip layout, nutrient plan, VWC thresholds — migrations 0022/0024), `k_source` (0029), and the **water-budget geometry** including `sensor_pipe_position` (0061).

**Group B — Hardware:** `device_registry`, `device_calibration`, `component_inventory`, `calibration_history`, `technician_installations`, `service_maintenance`. The physical devices and their calibration/service history. *Filled by:* TECH/OPS at install and service visits; `device_calibration` seeds the per-Sub-Node conversion constants.

**Group C — Live telemetry (streaming):** `node_sensor_readings` (the big one — one row per Sub Node per 5 min, **monthly-partitioned**, idempotent on `(node_id, recorded_at)`), `weather_station_readings`, `main_node_readings` (heartbeat), plus planned `water_source_status` and the learned `electricity_schedule_log`. *Filled by:* the IngestBroker from MQTT. This is where `water_flow_lpm` — the input to the water-budget engine — lands.

**Group D — External data:** `satellite_data` (one row per satellite pass per plot — NDVI/NDRE/SAR/LST/CWSI), `weather_forecasts`. *Filled by:* the satellite/Landsat/forecast scheduled jobs.

**Group E — Advisory pipeline (derived + AI):** `ai_suggestions` (one row per advisory), `irrigation_events`, `farmer_actions`, `ai_learning_log`, and **`plot_stage_log`** (per-plot growth-stage history, migration 0062, powering the D03-SB-003 transition rule). *Filled by:* the engines + farmer reports + the learning job.

**Group F — Alerts & notifications:** `alerts_notifications` (one row per fired device-health rule), `notification_dispatch_log`, `notification_dlq` (dead-letter queue for failed deliveries). *Filled by:* the device-health engine + the delivery subscriber.

**Group G — Business & billing:** `subscriptions_billing`, `product_performance_bi`. *Filled by:* ops/rollups.

**Group H — Auth & security:** `users` (staff), `otp_codes`, `refresh_tokens`, `auth_sessions`, `audit_log`, plus DPDP/consent tables (`farmer_consent`, `consent_event`, `erasure_request`). *Filled by:* the auth + consent/erasure flows.

**The Knowledge-Base tables** (loaded from compiled SQL, not hand-written): `kb_rules`, `kb_rule_fields`, `kb_farm_brain_fields`, `kb_golden_tests`, `kb_precedence`, `kb_rule_categories`, `kb_rule_references`, `kb_rule_dependencies`, `kb_duplication_groups`/`_members`, `kb_domains`, `kb_stages`, `kb_source_classes`, `kb_source_tiers`, `kb_open_items`, plus the runtime `engine_state`, `advisory_log`, `kb_overrides`, `kb_override_audit`. These are explained in Part V.

## 13. Reference / lookup tables

Keyed by variety or product, read *by* the rules:
- **`variety_stage_water_target`** — per-variety, per-growth-stage water targets by DAP (days-after-planting) window; the backbone of the water-budget engine.
- **`variety_n_ceiling`** — max nitrogen per acre per variety.
- **`registered_herbicide_registry`** — CIB&RC-registered herbicides (compliance).

## 14. Migrations (0001 → 0063)

Each is a transactional, reversible schema step. Milestones: `0001` the 21 base tables · `0003` extensions (PostGIS/pgvector/pgcrypto) · `0005` monthly partitions · `0008` RLS + roles · `0010` the first KB load · `0012` device calibration · `0013` main-node heartbeat · `0019` satellite panel · `0022/0024` crop-season agronomy plan · `0029` `k_source` · `0048–0059` the VNMKV + firing-intent KB batches · **`0060` water-budget KB rules** · **`0061` `sensor_pipe_position`** · **`0062` `plot_stage_log`** · **`0063` the final-decision KB rules**.

## 15. Key schema design decisions

- **Idempotent ingest:** readings UPSERT on `(node_id, recorded_at)`, so a re-sent/backlogged message never double-counts.
- **Partitioning:** `node_sensor_readings` is partitioned by month — the only table that grows without bound.
- **Row-Level Security + roles:** tenant isolation enforced in the database, not just the app.
- **Append-only audit:** `advisory_audit`, `consent_event`, `audit_log` are immutable records for compliance (India's DPDP Act).
- **Data tiers:** a plot with hardware vs a satellite-only plot are handled by a `data_tier` concept so the engine knows which signals to expect.

---
---

# PART V — THE KNOWLEDGE BASE (the heart of the system)

## 16. What the KB is

The Knowledge Base is the **agronomy rule book, encoded as data**. It is **495 rules across 14 domains**; **296** have a machine-readable trigger (the engine evaluates them), the rest are reference/knowledge entries. It is authored by agronomists as JSON, validated by automated gates, compiled to one big SQL file, and loaded into the `kb_*` tables. The engine reads rules *from the database at runtime*.

**The 14 domains:**

| # | Domain | # | Domain |
|---|---|---|---|
| D1 | Crop Lifecycle Stages | D8 | Cultivation Operations |
| D2 | Soil & Land Preparation | D9 | Harvest & Post-Harvest |
| D3 | Water & Irrigation | D10 | Maharashtra & Kannad-Specific Data |
| D4 | Nutrient & Fertilizer Mgmt | D11 | Yield Impact Data |
| D5 | Pest Management | D12 | AI Training Data Requirements |
| D6 | Disease Management | D13 | Seed & Input Economics |
| D7 | Weather & Climate | D14 | Satellite & Remote Sensing |

## 17. Anatomy of a rule (every field)

A rule in `knowledge_base/DomainN_Rules_Ginger.json`:

| Field | What it is |
|---|---|
| `rule_id` | Unique ID `D<domain>-<category>-<seq>`, e.g. `D04-MC-005`. |
| `category` | Sub-group within the domain (e.g. `MC` = micronutrients), declared per domain. |
| `priority` | 1–5 (ranking when several fire). |
| `severity` | `info` / `yellow` / `red` / `blocking` (the only allowed values). |
| `stage` | Growth stage it applies to (`null` = all stages). |
| `trigger.english` / `.marathi` | Human description of when it fires. |
| `trigger.expr` | The machine condition in the **trigger DSL** (§18). |
| `trigger.expr_version` | DSL version tag. |
| `trigger.golden_tests[]` | `{context, expect}` cases proving the expr evaluates correctly. |
| `action.english` / `.marathi` | The advice text (Marathi is what the farmer sees). |
| `reasoning.agronomic_basis` | *Why* (≥40 chars, enforced) — the evidence. |
| `reasoning.yield_impact` | Expected effect on yield. |
| `reasoning.confidence_score` | 0–1. |
| `reasoning.source_tier` | Evidence strength **A/B/C** (A = institutional/peer-reviewed). |
| `reasoning.references[]` | Citations. |
| `farm_brain_schema[]` | The farm-brain fields this rule reads (all must be declared). |
| `u_value` | Yield-loss weight for the D11 model (dedup-aware). |
| `recoverability` | `none`/`partial`/`full`/`same_season`. |
| `source_class` | Provenance class (SRC-Q/SRC-D/DERIVED/EST/VERIFY/FIELD). |
| `kannad_note` | Local field-team note (≥20 chars, enforced). |
| `decision_type` | e.g. `PLANNING_GUIDANCE`, `SENSOR_ALERT`, `DATA_CAPTURE`, `BLOCK`. |
| `automation` | `full`/`assisted`/`advisory`/`refusal`/`none`. |
| `delivery` | How/when it's shown (§21). |
| `immutable` | `true` = a safety rule that cannot be overridden. |
| `review{tier, reviewer, date, outcome}` | Agronomist sign-off trail. |

There is deliberately **no `compliance_tag`** in the rule — compliance tagging lives in a separate tracker; the KB carries `review.outcome` + `status`.

## 18. The trigger DSL (the little language rules are written in)

`trigger.expr` is a tiny, safe expression language (`engine/trigger_dsl.py`). Example:
```
plot_status == 'pre_planting' AND agro_climatic_zone == 'marathwada_central' AND basal_znso4_applied_kg_acre IS NULL
```

**Three-valued logic** is the key idea: every expression is **TRUE / FALSE / UNKNOWN**. A field with no data is **UNKNOWN**, *never silently false*. A rule only fires on **TRUE**. This is why missing data makes rules *dormant* (safe) rather than misfiring.

**Supported:** `AND/OR/NOT`, parentheses, comparisons (`==`, `!=`, `<`, `>`, `<=`, `>=`), `IN [...]`, `BETWEEN`, `IS NULL / IS NOT NULL / IS TRUE / IS FALSE`, `DURATION(field > x) > n HOURS|DAYS`, `WITHIN(date, n DAYS)`, `MONTH IN [...]`, `STAGE IN [...]`.
**Not supported (by design):** arithmetic, DATE literals, string concatenation, functions. This is why the water-budget engine pre-computes *ratios* in Python and the rules just compare them to constants (§26).
**Footgun:** an undeclared bare word is silently treated as a string literal — so every field a rule names **must be declared**, or comparisons quietly never match. The gates (§24) catch this.

## 19. Controlled vocabularies (the allowed values)

- `severity`: `info` / `yellow` / `red` / `blocking`.
- `delivery`: `SILENT_GUARD` / `EVENT` / `ONCE_UNTIL_RESOLVED` / `WINDOW`.
- `source_tier`: `A` / `B` / `C` (evidence strength — *not* L1–L4).
- **Soil** has two fields: `soil_type` (incl. `vertisol`) and `soil_texture_class` (`heavy`/`medium`/`light`) — both **derived by the mapper** from the DB soil column.

## 20. Precedence (resolving rules that fire together)

When multiple rules fire, a precedence graph decides what the farmer actually sees. Five relation types (centralised in Domain11's graph, mirrored in `engine/precedence.py`):
- **SUPPRESSES** — A stops B from being issued (e.g. a saturated-soil probe reading suppresses an "irrigate" instruction).
- **SUPERSEDES** — A replaces B.
- **ESCALATES** — A raises B's severity (merge into one stronger message).
- **BUNDLES** — A and B become one combined message.
- **SEQUENCES** — A must be answered before B is evaluated.

**Cardinal rule:** **VWC probe > water-budget > satellite** — a direct soil-moisture measurement always wins over a modelled estimate, which wins over a satellite inference.

## 21. Delivery policy (how/when advice reaches the farmer)

Each rule's `delivery` class controls cadence so the farmer isn't spammed:
- **SILENT_GUARD** — speaks only when the prohibited action is about to happen (e.g. "don't spray before rain").
- **EVENT** — fires once on the rising edge of a condition.
- **ONCE_UNTIL_RESOLVED** — a standing issue; says it once, then re-escalates on a 0/7/21/45/90-day ladder until resolved.
- **WINDOW** — dated action with up to 3 overdue reminders.

## 22. Immutable rules & overrides

- **Immutable rules** (24 of them) are the safety core (e.g. never recommend a blocklisted pesticide); they refuse any override.
- **`kb_overrides`** is the sanctioned per-plot/cluster/global tuning surface for the agronomist: a 15+ character Marathi rationale, ≤400-day expiry, every apply audited to `kb_override_audit`. This lets ops tune a rule for one plot without editing the KB.

## 23. The Farm Brain mapper — how fields get filled (`app/application/build_farm_brain.py`)

The engine doesn't read the database directly; it reads a **single per-plot, per-day dictionary** called the Farm Brain. The mapper builds it:
1. Start with every declared `kb_farm_brain_fields` name set to `None` (UNKNOWN).
2. Fill from each source: latest sub-node reading, plot/season/farm facts, lab soil test, scouting, economics/operations, weather station, weather forecast, satellite, yield model, QA counters, reference tables.
3. **Derive** composite fields — soil enums, `dap`, `plot_status` (crop-cycle phase from season dates), the water-budget ratios, `previous_stage` (from `plot_stage_log`), VWC status, etc.
4. Anything with no source stays UNKNOWN; its rules simply don't fire.

> **Naming caution:** the Farm-Brain field `plot_status` (`pre_planting`/`growing`/`post_harvest`, mapper-derived) is **distinct from** the `plots.plot_status` column (`active`/`fallow`/`harvested`). Same name, different meaning — the mapper never reads the column into the field (documented in DATA_INVENTORY).

## 24. Authoring & compilation — how a rule goes from idea to live

Authoring touches several coupled surfaces, guarded by two gates, then ships as a migration:
1. Edit the rule **JSON** (`knowledge_base/DomainN_Rules_Ginger.json`).
2. Mirror the trigger in `authoring/triggers_wave*.py` (expr **byte-identical** + golden tests).
3. Update `notification_policy.DELIVERY` / `precedence.PRECEDENCE` / `expert_override.IMMUTABLE` as needed; declare any new field in a domain `_schema`.
4. **Two gates must pass** (`tests/kb/test_authoring_gates.py`): the **drift gate** (authoring `.py` ≡ JSON for triggers/delivery/precedence/immutable, counts equal) and the **golden gate** (every trigger parses, every field is declared, every golden test passes).
5. **Compile:** `build/json_to_sql.py` turns the JSON into one big `ginger/generated/agroguardian_ginger_kb.sql` (it also validates categories, counts, confidence bounds, unique action text, etc.).
6. **Ship a KB-reload migration:** FK-safe (drop `advisory_log`/`kb_overrides` FKs → TRUNCATE the 15 `kb_*` tables → load the SQL → re-add FKs).

This discipline is why the KB can change frequently without breaking the engine.

## 25. Worked example — the basal-zinc rule (D04-MC-005)

Agronomist decision: *"In the Kannad zone, recommend 10 kg/acre basal zinc sulphate before planting, until it's recorded as applied."* Becomes:
- `trigger.expr`: `plot_status == 'pre_planting' AND agro_climatic_zone == 'marathwada_central' AND basal_znso4_applied_kg_acre IS NULL`
- Fields: `plot_status` (mapper-derived from dates), `agro_climatic_zone` (mapper-derived from district — Kannad → `marathwada_central`), `basal_znso4_applied_kg_acre` (awaiting a capture source → stays NULL → rule fires).
- `severity` info, `delivery` ONCE_UNTIL_RESOLVED, golden tests for fire/no-fire, precedence (none). Compiled, shipped as migration 0063. It fires the moment a plot enters pre-planting in that zone, and goes silent once the dose is recorded.

## 26. The water-budget engine (deep dive)

The showcase of "KB decides, Python computes." The problem: turn **one drip pipe's flow reading** into a **per-plant water deficit** the rules can act on — but the DSL has no arithmetic.

Solution — a compute layer (`app/domain/water_budget.py` + `PgWaterBudgetRepo`) produces *ratios*, and the rules compare those to constants:
- **Inputs:** live `water_flow_lpm` from `node_sensor_readings`; per-variety stage targets from `variety_stage_water_target`; plot geometry from `crop_seasons` (captured on the dashboard's **Plot Geometry** page).
- **Computed each run (in the mapper):** `plot_plants_estimated`, cumulative litres per plant, `stage_water_deficit_ratio = 1 − min(1, cumulative/target)`, `per_plant_cumulative_vs_lifecycle_ratio` (over-irrigation), `vwc_status` (saturated/low/ok — the probe veto), `days_since_last_irrigation`, `days_since_last_flow_reading`, `planting_geometry_incomplete`.
- **Rules (D03-WB-001…008 + D03-ST-001)** then read those: e.g. `stage_water_deficit_ratio > 0.25 AND vwc_status != 'saturated'` → "irrigate." Each degrades to UNKNOWN when an input is missing, so the suite is dormant-safe until flow + geometry exist.
- **Gates:** `planting_geometry_incomplete` (D03-WB-008) blocks until the geometry form is filled; the VWC probe reading always vetoes a modelled "irrigate."

---
---

# PART VI — THE ENGINES & DATA FLOWS

## 27. Device-health engine (real-time)
7 rules in `app/domain/rule_definitions.py` run on **every** incoming reading: `low_battery`, `battery_critical`, `low_water`, `dry_run`, `sensor_fault`, `frost`, `tamper`. Each has a per-`(plot, alert_type)` cooldown. Firing writes `alerts_notifications` + a Postgres `NOTIFY`, which wakes the advisory pipeline. This is the fast safety net (minutes), separate from the daily agronomy engine.

## 28. Ginger KB daily engine
At 06:30 IST (`ginger_daily.py`): for each active ginger season → build the Farm Brain → evaluate the 296 triggers three-valued → resolve precedence → apply delivery policy → compose four-part Marathi messages → write `ai_suggestions`, append the mandatory legal disclaimer, record an immutable `advisory_audit` row. State persists per plot (`engine_state`) so a re-run doesn't re-fire. *(Verified in a staging run: 19 advisories across 2 plots.)*

## 29. Advisory pipeline (event-driven)
Over Postgres `LISTEN/NOTIFY`: `evaluate_rules` emits `alert.created` → **advisory_subscriber** claims it atomically → `compose_advisory` (Claude Sonnet) → writes `ai_suggestions` + disclaimer + audit → emits `suggestion.generated` → **delivery_subscriber** → `deliver_advisory` → WhatsApp. Both subscribers start with the app. Delivery is currently **off by choice** on staging (`ADVISORY_DELIVERY_ENABLED=false`) until WhatsApp credentials are live; compose is event-driven (fires on alerts, not on a schedule).

## 30. Satellite & Landsat flows
- **Satellite (02:30):** for each active plot *with a boundary polygon*, fetch Sentinel-2 (optical: NDVI/NDRE) + Sentinel-1 (SAR) from Copernicus/CDSE → `satellite_data`. Plots without a polygon are skipped. New scenes appear every few days (revisit cadence + cloud filtering), not daily.
- **Landsat (04:30):** land-surface-temperature / crop-water-stress from USGS → `satellite_data`.
Both are **enabled on staging**.

## 31. Yield model (D11)
Runs inside the mapper: `Y_potential = Y_variety × SiteIndex`, then multiply by `(1 − uᵢ·Iᵢ)` over ~15 loss factors, with a 1000-draw Monte-Carlo confidence interval and per-factor attribution. Each factor maps to a `representative_rule_id`. Calibration is placeholder until Season-1 actuals arrive.

## 32. Weather
- **Forecast (03:00):** Open-Meteo, no key needed → `weather_forecasts`; the mapper reads the stored window for D07 rain/frost rules.
- **Station:** Main Node BME280/rain/wind over MQTT → `weather_station_readings`.

## 33. The scheduled jobs (cron table)

| Time (IST) | Job | Writes | Flag |
|---|---|---|---|
| 02:30 | Satellite fetch | `satellite_data` | `SATELLITE_JOB_ENABLED` |
| 02:30 | Retention/erasure sweep | anonymises due records | `RETENTION_JOB_ENABLED` |
| 03:00 | Weather forecast | `weather_forecasts` | `FORECAST_JOB_ENABLED` |
| 04:00 | Learning writer | `ai_learning_log` | `LEARNING_JOB_ENABLED` |
| 04:30 | Landsat LST | `satellite_data` | `LANDSAT_JOB_ENABLED` |
| 06:30 | **Ginger daily advisory** | `ai_suggestions` | `GINGER_JOB_ENABLED` |
| Sun 18:00 | QA digest | report files | `QA_DIGEST_JOB_ENABLED` |
| continuous | Advisory compose + deliver subscribers | `ai_suggestions`, WhatsApp | `ADVISORY_SUBSCRIBER_ENABLED` / `ADVISORY_DELIVERY_ENABLED` |

All are built and wired in `app/main.py`'s lifespan; each is independently toggleable.

---
---

# PART VII — DEPLOY & OPERATIONS

## 34. Deploy topology & switching features on

Lightsail (Mumbai) runs `docker-compose.prod.yml`: Caddy (+caddy-l4) + Mosquitto + Postgres + Chroma + app + Prometheus + Grafana + dashboard. Deploy = pull the image, `docker compose up -d app`, `alembic upgrade head`.

**Configuration** is environment variables (`.env` on the box, or Coolify's UI). Most jobs default **on**; the ones that need credentials:
- `ANTHROPIC_API_KEY` → Claude advisory text.
- `SATELLITE_JOB_ENABLED=true` + `COPERNICUS_CLIENT_ID/SECRET` → satellite.
- `LANDSAT_JOB_ENABLED=true` + `USGS_M2M_USERNAME/TOKEN` → Landsat.
- `META_WHATSAPP_TOKEN` + `META_WHATSAPP_PHONE_NUMBER_ID` (+ Live app) → WhatsApp delivery.

A production boot-guard refuses to start with default/empty secrets (`AUTH_JWT_SECRET`, `POSTGRES_PASSWORD`, `MQTT_BROKER_PASSWORD`, `ANTHROPIC_API_KEY`).

## 35. Observability & a hard-won lesson

The app exposes Prometheus metrics; Grafana dashboards + alerts watch them; logs are structured JSON.

**Lesson (Oct 2026 — the `k_source` outage):** the daily pipeline silently failed for ~2.5 weeks because a repository read a column (`k_source`) the SELECT didn't fetch, raising on every active-season lookup — and it was *invisible* because the JSON logger had **no traceback processor**, so exceptions logged `"exc_info": true` with no stack. Two fixes landed: a traceback processor in the logger, and a static test asserting the SELECT covers every column the mapper reads. **Takeaways:** never ship JSON logging without rendering tracebacks; a repo that reads a column must select it (now test-guarded).

---
---

# PART VIII — WHERE WE STAND & WHAT'S LEFT

## 36. Live now (verified)
- **Hardware → ingest:** Sub/Main Node v2.1 (frozen) streaming; MQTT ingest writing readings/weather/heartbeats idempotently; **flow telemetry live**.
- **Device-health rules** (real-time), **weather forecast**, **weather station**.
- **Ginger KB engine** (495 rules / 296 triggered) — produced 19 advisories in a staging run.
- **Water-budget engine** (compute + D03-WB rules) — runs; accurate once geometry is captured.
- **Plot-geometry capture**, **`previous_stage`/D03-SB-003**, **yield model**, **consent/erasure/retention**, **learning/QA jobs**.
- **Satellite + Landsat** — enabled on staging; fetching for PLOT_PILOT_001.
- **Advisory compose** (event-driven) with **Claude key set** on staging.
- **VPS** — app/DB/schedulers deployed; migrations at head 0063.

## 37. Config-gated / in-progress
- **WhatsApp delivery** — needs Meta credentials + a Live app; then flip `ADVISORY_DELIVERY_ENABLED=true`.
- **PLOT_PILOT_002 boundary polygon** — set `gps_boundary_geojson` so satellite/Landsat stop skipping it.
- **Verify the Claude model id** resolves (a stale `ANTHROPIC_MODEL_*` alias would fail composition).

## 38. Not built yet
- **Farmer mobile app** — the biggest gap. Many KB rules are *dormant* because their fields (wilt history, harvest-complete, seed-treatment dates, applied doses, etc.) need farmer/ops capture surfaces that live in an app not yet built. For the pilot, the Streamlit dashboard is the stand-in.
- **Object storage** (R2/B2), **nightly DB backups**, **production Sentry alerting**, **OTA firmware**, **full RAG over agronomy text**.
- **Season-2 KB activations** already authored and reserved, awaiting their data sources: D04-NS-003 cumulative-N ledger, D08-WD-002 herbicide registry gate, D03-WL-004 probe waterlog, D04-MC-006 ZnSO₄ partial-dose.

## 39. The shape of "done" for the pilot
The agronomy KB is **closed for Season 1** (all of Kuldip's decisions integrated). The remaining path to a farmer actually reading a 7 AM Marathi advisory is short and mostly **configuration + data capture**, not new engineering: WhatsApp credentials, the PLOT_PILOT_002 boundary, and the farmer-app capture screens that light up the dormant rules. The engine, the pipeline, the data layer, and the knowledge base are built, deployed, and verified.

---

*Maintainer note: this guide is a synthesis. When it disagrees with the code, the code wins. Keep [`SYSTEM_AND_STATUS.md`](SYSTEM_AND_STATUS.md) (status), [`DATA_INVENTORY.md`](DATA_INVENTORY.md) (field catalog), and [`HARDWARE_WIRE_CONTRACT.md`](HARDWARE_WIRE_CONTRACT.md) (wire format) as the authoritative detail references.*
