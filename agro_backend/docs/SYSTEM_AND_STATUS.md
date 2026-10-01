# AgroGuardian V2 — Full System & Current Status

**Audience:** a new engineer/teammate joining the project. Read this top-to-bottom to understand the whole system, then use Part B for exactly what is live vs pending today.
**Ground truth:** the code in `agro_backend/` + `firmware/`. This doc is a map, current as of 29 Sep 2026 (migration head **0058**). Where this doc and code disagree, code wins.

---

# PART A — THE SYSTEM

## 1. What it is

Smallholder **ginger** farmers in Aurangabad (Kannad taluka, Marathwada) make daily irrigation/crop decisions with incomplete information. AgroGuardian is a **precision-ag IoT + AI advisory platform** that closes five failure modes: over-irrigation, under-irrigation, pump dry-run, frost damage, and no feedback loop.

**North star:** *the whole stack exists to produce one good 4-sentence Marathi WhatsApp message at 7 AM.*

**Pilot scope (deliberately small):** 1 farm, 1 farmer, **2 plots**, 1 Main Node, 1 Sub Node. Crop: variety **Mahima**, Kharif 2026. `AGR-SN-0001 → PLOT_PILOT_001` (hardware); `PLOT_PILOT_002` is satellite-only. Not solved in pilot: pest detection, market pricing, subsidy paperwork.

**Actors:** Farmer (Marathi, WhatsApp OTP + advisories) · Agronomist/ops (English Streamlit dashboard, tunes rules via `kb_overrides`) · Sub Node (buried sensor) · Main Node (4G gateway) · Backend (everything downstream of MQTT).

## 2. End-to-end data flow

```
Sub Node (ATmega328P, buried, LoRa only, 5-min cycle + deep sleep)
  soil/battery/pressure/flow/DS18B20/NPK  -> one LoRa CSV line (433 MHz)
        │
        ▼
Main Node (ESP32 + A7672S 4G, the only device speaking MQTT; SD outbox on outage)
  parse CSV -> MQTT-TLS :8883 over 4G
        │
        ▼
Caddy (caddy-l4, SNI L4 routing) -> Mosquitto -> IngestBroker (paho -> asyncio)
  dispatch by $schema:
    v2 / v2-raw  -> Reading -> UPSERT node_sensor_readings (idempotent on node_id, recorded_at)
                              -> 7-rule device-health engine -> alerts_notifications + NOTIFY agro_events
    v2-raw/master-> weather_station_readings   (Main Node BME280/INA219/rain/wind)
    v2-master    -> main_node_readings         (gateway heartbeat/liveness)
        │
        ▼  (Postgres LISTEN/NOTIFY 'agro_events')
  advisory_subscriber -> dispatch_advisory -> compose_advisory (Claude) -> ai_suggestions
        │                                                        + append disclaimer + advisory_audit
        ▼
  delivery_subscriber -> deliver_advisory -> WhatsApp template (agroguardian_advisory_v2)
        │
   plus daily 06:30 IST: Ginger KB engine (484-rule) -> build_farm_brain -> ai_suggestions
   plus nightly jobs: weather forecast (03:00), learning (04:00), qa_digest (18:00), retention (02:30)
   plus (off by default): satellite fetch (02:30), Landsat LST (04:30)
        │
        ▼
   Yield model (D11) runs inside build_farm_brain: Y_var × SI × Π(1 − uᵢ·Iᵢ)
```

## 3. Architecture — hexagonal / ports-and-adapters

- `app/domain/` — **pure** (stdlib + Decimal/uuid/datetime/enum only). Sensor `Reading`, `MainNodeReading`, `WeatherStationReading`, `device_calibration` (8 pure conversion fns), plot, alert, rules, disclaimer, consent, age, geo_area.
- `app/application/` — use cases + `ports/` (Protocols). ~10+ use cases (build_farm_brain, compose_advisory, evaluate_rules, ingest_telemetry, deliver_advisory, dispatch_advisory, record_consent, withdraw_consent, fulfil_erasures, …). Imports domain + ports only.
- `app/infra/` — the **only** layer allowed framework imports: `mqtt`, `persistence` (`Pg*Repo` + ORM models), `whatsapp`, `satellite`, `forecast`, `lst`, `llm`, `http`, `events` (`pg_notify_bus`), `auth`, `ota`, `storage`, `notify`.
- `app/jobs/` — startup wiring + schedulers (see §A11).
- `ginger/` — teammate-delivered engine package (**do not edit**).

**Purity is enforced** by AST scans (`tests/domain/test_domain_purity.py`, `tests/application/test_application_purity.py`): no `fastapi`/`sqlalchemy`/`anthropic`/`structlog`/`pydantic`/`paho` in domain or application. Measurements use `Decimal`, never float. DB access only via `Pg*Repo` behind a Protocol. Model choice via `ModelRole`, never a hardcoded `claude-…`.

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2.0 async + asyncpg · Postgres 15 (PostGIS + pgvector + pgcrypto) · Mosquitto · Claude (Sonnet + Haiku) · Meta WhatsApp Cloud API · Streamlit · Caddy (`caddy-l4`) · Prometheus/Grafana/Sentry · AWS Lightsail Mumbai · Arduino/PlatformIO firmware. **Provider-portability charter:** no AWS-managed services; S3-compatible (R2/B2) only.

## 4. IoT / firmware (v2.1 FINAL — frozen 2026-09-13)

**Sub Node** (`firmware/sub_node/`): ATmega328P @ 8 MHz, 3.3 V. LoRa RA-02 SX1278 @ 433 MHz. 5-min cycle: wake → WDT reset → read soil(A0)/battery(A1)/pressure(A3)/DS18B20(D4)/NPK(RS485, IRLZ44N-gated 12 V) → LoRa TX one CSV line → LED code → `LowPower.powerDown` in 8 s chunks; **PCINT0 keeps the flow counter live during sleep**.

**Main Node** (`firmware/main_node/`): ESP32-WROOM. I2C BME280(0x76)/INA219(0x40)/DS3231(0x68); rain/wind/wind-dir GPIOs; SD card. A7672S 4G modem → MQTT-TLS. **SD outbox** (`/outbox.jsonl`, 5 MB cap) buffers Sub-Node telemetry on outage and re-publishes on reconnect (`backlog_pending=true`); heartbeats are not queued. Task WDT 90 s. Timestamp defence-in-depth: firmware year-window [2025,2099] → NTP→DS3231 sync-back → backend `_normalize_clock_skew` safety net.

**MQTT wire contract — three `$schema` variants (all parsed):**
- `…/telemetry/v2` — pre-calibrated engineering units (used by the fake node).
- `…/telemetry/v2-raw` — **raw ADC + pulses** in `raw_readings` + Main-Node `master_readings`; backend calibrates server-side using `device_calibration`. This is what the real firmware sends.
- `…/telemetry/v2-master` — Main-Node-only heartbeat (`sub_node_online`, `sub_node_silence_ms`).
Topic `agro/v2/+/+/+/telemetry`, QoS 1, `extra="forbid"`.

**Calibration (pure, server-side, `app/domain/device_calibration.py`):** soil `pct=(DRY-raw)/(DRY-WET)×100`; battery/pressure linear; **flow `L/min = pulses×60/(window_s×pulses_per_L)`** with a three-way `window_s` contract (absent→cal default, 0→unknown/None, >0→use it); NPK scaling. Constants per Sub Node in `device_calibration` (migration 0012).

## 5. Database (~67 app tables + 17 `kb_*` tables)

By subsystem (representative):
- **Identity/tenancy:** tenants, users, farmers, farms, plots, crop_seasons, auth_sessions, refresh_tokens, otp_*, subscriptions_billing.
- **Devices/telemetry:** device_registry, device_calibration, calibration_history, technician_installations, component_inventory, service_maintenance; readings: **node_sensor_readings**(+partitions), **main_node_readings**, **weather_station_readings**(+partitions), **satellite_data**, ingest_unmatched, event_outbox.
- **Agronomic state (rules read these):** crop_scouting, irrigation_events, season_operations, lab_soil_tests, water_source_status, farmer_actions, farmer_photos/photo_label, weather_forecasts(+partitions).
- **Advisory/AI:** ai_suggestions (fired-rule outputs; confidence, rule_version, delivery_status), advisory_classification, ai_learning_log, bias_observation, chat_messages, alerts_notifications, notification_dispatch_log/dlq, wa_inbound_log, **advisory_audit** (append-only, trigger-enforced).
- **Yield model (D11):** yield_u_values (factor→rule map), variety_potential, site_index_config, yield_prediction_log, yield_actual.
- **Reference lookups:** variety_stage_water_target, variety_n_ceiling, registered_herbicide_registry, imd_normals (code), pesticide registry CSV (code).
- **Compliance/DPDP:** farmer_consent, consent_event, erasure_request, non_compliance_reason, audit_log.
- **QA/clustering (D12):** clusters, cluster_config, plot_cluster, QA counters.
- **KB (loaded from compiled SQL):** kb_rules, kb_rule_fields, kb_farm_brain_fields, kb_golden_tests, kb_precedence, kb_rule_categories, kb_rule_references, kb_rule_dependencies, kb_duplication_groups/members, kb_domains, kb_stages, kb_source_classes, kb_source_tiers, kb_open_items, kb_overrides, kb_override_audit.

**Migrations 0001→0058** (reversible, transactional). Milestones since the pilot core (0001–0013): 0014/0016 advisory status+delivery · 0019 satellite D14 panel · 0021 lab soil tests · 0022–0026 crop-season agronomy plan / scouting / economics / operations · 0028/0033 forecast ET0-solar / wind-gust · 0030/0046/0047 consent / consent-capture / erasure · 0031/0038–0040 yield model + U-value register + prediction log · 0041/0042 D12 QA + cluster store · 0044/0045 advisory audit (columns + append-only table) · 0048–0049 VNMKV KB reload + Kannad site index · 0050–0053 variety water re-seed / N-ceiling / herbicide registry · 0054–0058 firing-intent KB batches (see §A6).

## 6. The Knowledge Base (Ginger Engine)

- **484 rules across 14 domains** (D1 Lifecycle … D14 Satellite). **249 are machine-triggered** (have a `trigger.expr`); the other ~235 are knowledge/reference entries with no trigger. **24 immutable** (safety core).
- **Rule anatomy** (`knowledge_base/DomainN_Rules_Ginger.json`): `rule_id`, `category`, `priority`, `stage`, `severity`, `trigger{english, marathi, expr, expr_version, golden_tests[]}`, `action{english, marathi}`, `reasoning{agronomic_basis, yield_impact, confidence_score, source_tier, references}`, `farm_brain_schema[]`, `u_value`, `recoverability`, `source_class`, `kannad_note`, `decision_type`, `automation`, `status`, `immutable`, `delivery`, `review{tier, reviewer, date, outcome, comment_mr}`. **No `compliance_tag`** — that lives in a separate tracker; the KB carries `review.outcome` + `status`.
- **Controlled vocabularies:** `severity` = info/yellow/red/blocking (only). `delivery` = SILENT_GUARD/EVENT/ONCE_UNTIL_RESOLVED/WINDOW. `reasoning.source_tier` = **A/B/C** (evidence strength; not L1–L4). Two soil fields: `soil_type` (incl. `vertisol`) and `soil_texture_class` (heavy/medium/light) — both **derived by the mapper** from the DB `soil_type` column.
- **Trigger DSL** (`engine/trigger_dsl.py`): three-valued (TRUE/FALSE/**UNKNOWN** — a missing field is UNKNOWN, never silently false). Supports AND/OR/NOT, comparisons, `IN`, `BETWEEN`, `IS NULL/NOT NULL/TRUE/FALSE`, `DURATION(...) > n HOURS|DAYS`, `WITHIN(date, n DAYS)`, `MONTH IN […]`, `STAGE IN […]`. **No** DATE literal, `||`, arithmetic, or functions. Every field named must be declared or it's a parse error (an undeclared bare word is silently treated as a string literal — a real footgun).
- **Precedence** (centralised in Domain11 `_schema.additions.precedence.graph`, mirrored in `engine/precedence.py`): 5 formal relations — SUPPRESSES, SUPERSEDES, ESCALATES, BUNDLES, SEQUENCES (no FEEDS/COMPLEMENTS). Cardinal rule: **VWC probe > water-budget > satellite**.
- **Authoring is multi-surface and gate-guarded** (`tests/kb/test_authoring_gates.py`): to add/change a rule you edit the JSON **and** `authoring/triggers_wave*.py` (expr + golden tests, byte-identical expr) **and** `notification_policy.DELIVERY` / `precedence.PRECEDENCE` / `expert_override.IMMUTABLE` as applicable, declare any new field in a domain `_schema`, then regenerate `ginger/generated/agroguardian_ginger_kb.sql` via `build/json_to_sql.py` and ship a **KB-reload migration** (FK-safe: drop advisory_log/kb_overrides FKs → TRUNCATE 15 kb_* tables → load SQL → re-add FKs). Two gates must stay green: **drift** (authoring .py == JSON) and **golden** (all triggers parse, fields declared, goldens pass).
- **Overrides:** `kb_overrides` is the sanctioned per-plot/cluster/global tuning surface (15+ char Marathi rationale, ≤400-day expiry, immutable rules refuse override, every apply audited).

## 7. The Mapper — "Farm Brain" (`app/application/build_farm_brain.py`)

Turns everything in the DB into a per-plot, per-day **field dict** keyed on the ~300+ names in `kb_farm_brain_fields`; every declared field is a key, defaulting to `None` (UNKNOWN) when no source supplies it. Sources: latest sub-node reading, plot/season/farm facts, lab soil test, scouting, season economics/operations, weather station, weather forecast, satellite, yield model, QA counters, reference (IMD normals, pesticide registry). **Soil enums are derived** from the DB `soil_type` column via explicit maps (so `vertisol`/`heavy` are what the engine sees). Coverage grows as sources come online; fields with no source stay UNKNOWN and their rules simply don't fire (safe).

## 8. The engines

- **7 device-health rules** (`app/domain/rule_definitions.py` `PILOT_RULESET`): low_battery, battery_critical, low_water, dry_run, sensor_fault, frost, tamper — evaluated per-message on ingest, with per-`(plot,alert_type)` cooldowns; fire → `alerts_notifications` + NOTIFY.
- **Ginger KB engine** (`ginger/engine/`, runs at 06:30 IST + inside build_farm_brain): loads rules from Postgres in production; evaluates the 249 triggers three-valued (only TRUE fires); resolves precedence; applies the delivery policy (SILENT_GUARD only speaks when the prohibited action is attempted; EVENT once on rising edge; ONCE_UNTIL_RESOLVED on a 0/7/21/45/90-day ladder raising severity; WINDOW dated with up to 3 overdue reminders); composes four-part Marathi messages; state persists per plot so a fresh run doesn't re-fire.

## 9. Advisory pipeline & delivery

Event-driven over Postgres `LISTEN/NOTIFY` (channel `agro_events`):
`evaluate_rules` emits `alert.created` → **advisory_subscriber** → `dispatch_advisory` (atomic claim) → `compose_advisory` (Claude Sonnet; **log-only if `ANTHROPIC_API_KEY` empty**) → writes `ai_suggestions` + **appends the verbatim Marathi disclaimer** (`app/domain/disclaimer.py`, LEGAL §7.2) + records an **append-only `advisory_audit`** row → emits `suggestion.generated` → **delivery_subscriber** → `deliver_advisory` → WhatsApp `send_template`. There is also the daily deterministic Ginger path writing `ai_suggestions` directly. Both subscribers are **started at app startup and enabled by default**. No urgency tiers / no push notifications yet; confidence is recorded but doesn't gate delivery.

**WhatsApp:** `MetaCloudWhatsappSender` is used **only if `META_WHATSAPP_TOKEN` + `META_WHATSAPP_PHONE_NUMBER_ID` are set**, else `LogOnlyWhatsappSender`. Template `agroguardian_advisory_v2` (UTILITY; whole Marathi message goes in the single `{{1}}` body param). Webhook `/webhooks/whatsapp` is live (GET verify + POST HMAC).

## 10. Yield model (D11)

Runs inside build_farm_brain (`app/domain/yield_forecast.py`, v1). `Y_potential = Y_var × SI`, then `Y_process = Y_potential × Π(1 − uᵢ·Iᵢ)` over 15 loss factors, 90% CI by 1000-draw Monte-Carlo, per-factor attribution. `yield_u_values` maps each factor to a `representative_rule_id` (e.g. factor-7 drought_fill → D03-ST-001, intensity from `dry_spell_days`). All factors currently L4/EST placeholder confidence, to recalibrate after Season 1.

## 11. Satellite & weather

- **Weather forecast (Open-Meteo)** — `app/infra/forecast/open_meteo.py` + `forecast_scheduler.py`, nightly **03:00**, no key needed, writes `weather_forecasts`; build_farm_brain reads the stored rows.
- **Weather station** — Main Node BME280/INA219/rain/wind, MQTT → `weather_station_readings`.
- **Satellite (Sentinel-2 optical + Sentinel-1 SAR via CDSE)** — `app/infra/satellite/cdse_provider.py` (real OAuth2 + Statistical API) + `satellite_scheduler.py` (02:30) → `satellite_data`. **Gated off** by `SATELLITE_JOB_ENABLED` + Copernicus creds.
- **LST/thermal (Landsat 8/9 via USGS M2M)** — `app/infra/lst/usgs_m2m.py` + `landsat_scheduler.py` (04:30). **Gated off** by `LANDSAT_JOB_ENABLED` + USGS creds.

## 12. DPDP / consent / compliance

Consent capture + notice (`app/domain/consent_notice.py`, verbatim §3.1) + age gate; `farmer_consent`/`consent_event` (append-only); withdrawal + erasure (anonymise-in-place) via `withdraw_consent`/`request_erasure`/`fulfil_erasures` + retention scheduler; append-only `advisory_audit` (immutable generation record) and `audit_log`. The disclaimer is mandatory on every advisory (IT Act §79 safe-harbour doesn't apply since VIRAAI generates active advice).

## 13. Deploy topology

Lightsail Mumbai; `docker-compose.prod.yml` runs Caddy (custom `caddy-l4`) + Mosquitto + Postgres + Chroma + app + Prometheus + Grafana. Only the TLS/MQTT edge is on the VPS today; backend/Postgres/dashboard otherwise local. Deploy a migration set with: `docker compose -f docker-compose.prod.yml build app && up -d app && exec app alembic upgrade head`.

---

# PART B — CURRENT STATUS (live vs pending), 29 Sep 2026

## B1. Status at a glance

| Subsystem | State | Notes |
|---|---|---|
| Hardware (Sub/Main Node, v2.1) | 🟢 **LIVE** | Connected; live telemetry flowing (per you). Firmware frozen. |
| MQTT ingest (v2/v2-raw/v2-master) | 🟢 **LIVE** | Writes node_sensor_readings + weather_station_readings + main_node_readings; idempotent. |
| **Flow telemetry** (`water_flow_lpm`) | 🟢 **LIVE** | Calibrated L/min lands in node_sensor_readings. **Water-budget blocker resolved.** |
| Device-health rules (7) | 🟢 **LIVE** | Per-message on ingest → alerts + NOTIFY. |
| Weather forecast (Open-Meteo) | 🟢 **LIVE** | Nightly 03:00, on by default. |
| Weather station (Main Node) | 🟢 **LIVE** | MQTT-populated. |
| Ginger KB engine (06:30 daily) | 🟢 **LIVE** | 484 rules / 249 triggered; writes ai_suggestions. |
| Advisory compose subscriber | 🟢 **LIVE** | LISTEN agro_events → compose_advisory (Claude). Log-only if ANTHROPIC key empty. |
| Advisory delivery subscriber | 🟢 **LIVE (log-only)** | Runs end-to-end; **sends to WhatsApp only when Meta token+phone-id set** — else logs. |
| Disclaimer + advisory_audit | 🟢 **LIVE** | Appended/recorded on every advisory. |
| Yield model (D11) | 🟢 **LIVE** | Runs in build_farm_brain (L4/EST placeholder calibration). |
| Consent / erasure / retention | 🟢 **LIVE** | Jobs + append-only tables. |
| Learning / QA-digest / retention jobs | 🟢 **LIVE** | 04:00 / 18:00 / 02:30. |
| WhatsApp send (Meta Cloud) | 🟡 **BUILT, not live** | Needs `META_WHATSAPP_TOKEN` + `META_WHATSAPP_PHONE_NUMBER_ID` (+ Live app). Template + webhook ready. |
| Claude advisory text | 🟡 **gated on key** | Needs `ANTHROPIC_API_KEY`, else log-only placeholder. |
| **Satellite (Sentinel optical+SAR)** | 🔴 **OFF** | Full adapter+scheduler, but `SATELLITE_JOB_ENABLED=false` + blank Copernicus creds → `satellite_data` empty. |
| **LST/thermal (Landsat)** | 🔴 **OFF** | Same: `LANDSAT_JOB_ENABLED=false` + blank USGS creds. |
| PLOT_PILOT_002 (satellite-only) | 🔴 **no data** | No sub-node + satellite off ⇒ receiving nothing until satellite is enabled. |
| Farmer app | 🔴 **not built** | Several new KB fields need farmer-app capture surfaces. |
| OTA / object storage / prod backups | 🔴 **not built** | Roadmap. |
| VPS full deploy | 🟡 **partial** | Only TLS/MQTT edge on VPS; app/DB local. |

Legend: 🟢 live · 🟡 built but gated/config-needed · 🔴 off / not built.

## B2. Firing-intent KB rules — where each stands (this workstream)
- **Batch 1 (5 ready rules)** live: D01-PH-004, D02-DR-004, D02-ST-002, D02-LY-001 (blocking flat-layout gate), D02-LY-004 (layout prompt).
- **v1.2 cluster-2** live: D01-PW-001 (late-planting warning, `planting_doy>158` — functional), D06-BW-001 (wilt gate), D03-SB-003 (stage transition), source_tier vocab fix.
- **Batch 2 (D06 disease)** live: D06-CH-002/FH-001/FH-002/ST-001/ST-002.
- **Dormant** (wired, correct, but never fire until a data source exists): every rule whose fields have no source yet — e.g. `years_since_last_wilt`, `harvest_complete`, `soft_rot_confirmed_in_cluster`, `seed_treatment_planned`, `previous_stage`, `fungicide_option_about_to_be_shown`. These need **farmer-app / ops / engine-composer** sources.
- **Held on agronomy decisions:** D04-MC-005 (ZnSO₄ — needs the `agro_climatic_zone` zone-vocab map: mapper emits `marathwada_central/western/eastern`, not `western_scarcity`); D04-NS-003 & D08-WD-001 keep their deployed triggers until N-ledger / `proposed_herbicide_input` sources exist (swapping now would regress live coverage).
- **Batch 3+ (D04/D05, D09/D11/D12 …)** pending agronomy authoring.

## B3. What's left (concrete)

**Config to flip on (no code):**
1. `META_WHATSAPP_TOKEN` + `META_WHATSAPP_PHONE_NUMBER_ID` (+ Meta app Live + verified WABA) → WhatsApp advisories actually send.
2. `ANTHROPIC_API_KEY` → real Claude advisory text (else log-only).
3. `SATELLITE_JOB_ENABLED=true` + Copernicus/CDSE OAuth client → satellite NDVI/SAR for PLOT_PILOT_002.
4. `LANDSAT_JOB_ENABLED=true` + USGS ERS token → LST/thermal.

**Now-unblocked build work (flow is live):**
5. Author the **8 D03-WB water-budget rules + D03-ST-001** against `water_flow_lpm` (they were held on exactly this). Note: the old spec's `flow_telemetry_present` gate maps to `water_flow_lpm IS NOT NULL`; use confidence handling via three-valued logic + the `<0.72` guidance note (no confidence-gate DSL).
6. Wire the `compute_water_budget()` / dose engine per the water-budget v1.3 spec, now that flow lands.

**Product/data sources (unblock the dormant rules):**
7. Farmer-app capture screens for the new fields (wilt years, harvest_complete, seed-treatment dates, emergence, processing route, etc.); ops flags (soft_rot_confirmed_in_cluster, cibrc_verified, mandi price); engine composer flags (fungicide/chemical about-to-show); a per-plot `previous_stage` persistence in the mapper.
8. Agronomy decisions still open: D04-MC-005 zone-vocab map; N-events ledger model for D04-NS-003; `proposed_herbicide_input` channel for D08-WD-001.

**Platform hardening / roadmap:**
9. Full VPS deploy of app+DB (not just the edge); object storage (R2/B2); nightly pg_dump backups; production Sentry alerting + Grafana; modem TLS `authmode=0→2` + secret rotation; OTA; farmer app; LoRa 433 MHz regulatory clearance for scale-up.

---

*Maintainer note: regenerate this doc's Part B whenever config flags, schedulers, or the migration head change. Ground truth: `agro_backend/` + `firmware/`.*
