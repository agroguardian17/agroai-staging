# AgroGuardian V2 — Full System & Current Status

**Audience:** a new engineer/teammate joining the project. Read this top-to-bottom to understand the whole system, then use Part B for exactly what is live vs pending today.
**Ground truth:** the code in `agro_backend/` + `firmware/`. This doc is a map, current as of 2 Oct 2026 (migration head **0063**). Where this doc and code disagree, code wins.

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

**Migrations 0001→0063** (reversible, transactional). Milestones since the pilot core (0001–0013): 0014/0016 advisory status+delivery · 0019 satellite D14 panel · 0021 lab soil tests · 0022–0026 crop-season agronomy plan / scouting / economics / operations · 0028/0033 forecast ET0-solar / wind-gust · 0030/0046/0047 consent / consent-capture / erasure · 0031/0038–0040 yield model + U-value register + prediction log · 0041/0042 D12 QA + cluster store · 0044/0045 advisory audit (columns + append-only table) · 0048–0049 VNMKV KB reload + Kannad site index · 0050–0053 variety water re-seed / N-ceiling / herbicide registry · 0054–0059 firing-intent KB batches (see §A6) · **0060 water-budget KB rules (D03-WB-*/D03-ST-001)** · **0061 `crop_seasons.sensor_pipe_position`** · **0062 `plot_stage_log`** (D03-SB-003 previous-stage history) · **0063 final-decision KB rules (D04-MC-005 basal ZnSO₄, D06-BW-004 wilt-history prompt)**.

## 6. The Knowledge Base (Ginger Engine)

- **495 rules across 14 domains** (D1 Lifecycle … D14 Satellite). **296 are machine-triggered** (have a `trigger.expr`); the rest are knowledge/reference entries with no trigger. **24 immutable** (safety core).
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
- **Ginger KB engine** (`ginger/engine/`, runs at 06:30 IST + inside build_farm_brain): loads rules from Postgres in production; evaluates the 296 triggers three-valued (only TRUE fires); resolves precedence; applies the delivery policy (SILENT_GUARD only speaks when the prohibited action is attempted; EVENT once on rising edge; ONCE_UNTIL_RESOLVED on a 0/7/21/45/90-day ladder raising severity; WINDOW dated with up to 3 overdue reminders); composes four-part Marathi messages; state persists per plot so a fresh run doesn't re-fire.

## 9. Advisory pipeline & delivery

Event-driven over Postgres `LISTEN/NOTIFY` (channel `agro_events`):
`evaluate_rules` emits `alert.created` → **advisory_subscriber** → `dispatch_advisory` (atomic claim) → `compose_advisory` (Claude Sonnet; **log-only if `ANTHROPIC_API_KEY` empty**) → writes `ai_suggestions` + **appends the verbatim Marathi disclaimer** (`app/domain/disclaimer.py`, LEGAL §7.2) + records an **append-only `advisory_audit`** row → emits `suggestion.generated` → **delivery_subscriber** → `deliver_advisory` → WhatsApp `send_template`. There is also the daily deterministic Ginger path writing `ai_suggestions` directly. Both subscribers are **started at app startup and enabled by default**. No urgency tiers / no push notifications yet; confidence is recorded but doesn't gate delivery.

**WhatsApp:** `MetaCloudWhatsappSender` is used **only if `META_WHATSAPP_TOKEN` + `META_WHATSAPP_PHONE_NUMBER_ID` are set**, else `LogOnlyWhatsappSender`. Template `agroguardian_advisory_v2` (UTILITY; whole Marathi message goes in the single `{{1}}` body param). Webhook `/webhooks/whatsapp` is live (GET verify + POST HMAC).

## 10. Yield model (D11)

Runs inside build_farm_brain (`app/domain/yield_forecast.py`, v1). `Y_potential = Y_var × SI`, then `Y_process = Y_potential × Π(1 − uᵢ·Iᵢ)` over 15 loss factors, 90% CI by 1000-draw Monte-Carlo, per-factor attribution. `yield_u_values` maps each factor to a `representative_rule_id` (e.g. factor-7 drought_fill → D03-ST-001, intensity from `dry_spell_days`). All factors currently L4/EST placeholder confidence, to recalibrate after Season 1.

## 11. Satellite & weather

- **Weather forecast (Open-Meteo)** — `app/infra/forecast/open_meteo.py` + `forecast_scheduler.py`, nightly **03:00**, no key needed, writes `weather_forecasts`; build_farm_brain reads the stored rows.
- **Weather station** — Main Node BME280/INA219/rain/wind, MQTT → `weather_station_readings`.
- **Satellite (Sentinel-2 optical + Sentinel-1 SAR via CDSE)** — `app/infra/satellite/cdse_provider.py` (real OAuth2 + Statistical API) + `satellite_scheduler.py` (02:30) → `satellite_data`. **Enabled on staging** (`SATELLITE_JOB_ENABLED=true` + CDSE OAuth creds). Fetches scenes within a 20-day lookback for each active plot **that has a boundary polygon** (`plots.gps_boundary_geojson`); a plot without one is skipped (`skipped_no_polygon`). Note the cadence: Sentinel-2 ~5-day revisit (clouds filtered), Sentinel-1 ~6–12-day — so a new row appears every few days, not daily.
- **LST/thermal (Landsat 8/9 via USGS M2M)** — `app/infra/lst/usgs_m2m.py` + `landsat_scheduler.py` (04:30). **Enabled on staging** (`LANDSAT_JOB_ENABLED=true` + USGS M2M creds); same boundary-polygon requirement.

## 11a. Water-budget engine (D03-WB / D03-ST-001)

Turns the single-pipe drip flow reading (`node_sensor_readings.water_flow_lpm`) into per-plant dose/deficit ratios the D03-WB rules read. Pure math in `app/domain/water_budget.py` (deficit ratio, VWC classification, per-plant cumulative, geometry completeness); `WaterBudgetRepo` + `PgWaterBudgetRepo` supply variety stage targets (`variety_stage_water_target`, by DAP window), lifecycle high-end, cumulative drip litres (`SUM(water_flow_lpm)×cadence`), last-irrigation and last-flow timestamps. `build_farm_brain._populate_water_budget` derives the ~11 D03-WB fields each run, degrading to UNKNOWN per missing input. **Geometry** (`planting_layout`/`dripper_spacing_cm`/`drippers_per_acre`/`rows_per_bed`/`plants_per_acre`, captured via the dashboard **Plot Geometry** page → `crop_seasons`) gates D03-WB-008 until complete; `plot_status` (pre_planting/growing/post_harvest) is derived in the mapper from season dates and gates the pre-planting prompts D04-MC-005 / D06-BW-004. Previous-run stage for the D03-SB-003 transition rule is persisted in `plot_stage_log` (written by `ginger_daily`, read by the mapper).

## 12. DPDP / consent / compliance

Consent capture + notice (`app/domain/consent_notice.py`, verbatim §3.1) + age gate; `farmer_consent`/`consent_event` (append-only); withdrawal + erasure (anonymise-in-place) via `withdraw_consent`/`request_erasure`/`fulfil_erasures` + retention scheduler; append-only `advisory_audit` (immutable generation record) and `audit_log`. The disclaimer is mandatory on every advisory (IT Act §79 safe-harbour doesn't apply since VIRAAI generates active advice).

## 13. Deploy topology

Lightsail Mumbai; `docker-compose.prod.yml` runs Caddy (custom `caddy-l4`) + Mosquitto + Postgres + Chroma + app + Prometheus + Grafana. Only the TLS/MQTT edge is on the VPS today; backend/Postgres/dashboard otherwise local. Deploy a migration set with: `docker compose -f docker-compose.prod.yml build app && up -d app && exec app alembic upgrade head`.

---

# PART B — CURRENT STATUS (live vs pending), 2 Oct 2026

## B1. Status at a glance

| Subsystem | State | Notes |
|---|---|---|
| Hardware (Sub/Main Node, v2.1) | 🟢 **LIVE** | Connected; live telemetry flowing (per you). Firmware frozen. |
| MQTT ingest (v2/v2-raw/v2-master) | 🟢 **LIVE** | Writes node_sensor_readings + weather_station_readings + main_node_readings; idempotent. |
| **Flow telemetry** (`water_flow_lpm`) | 🟢 **LIVE** | Calibrated L/min lands in node_sensor_readings. **Water-budget blocker resolved.** |
| Device-health rules (7) | 🟢 **LIVE** | Per-message on ingest → alerts + NOTIFY. |
| Weather forecast (Open-Meteo) | 🟢 **LIVE** | Nightly 03:00, on by default. |
| Weather station (Main Node) | 🟢 **LIVE** | MQTT-populated. |
| Ginger KB engine (06:30 daily) | 🟢 **LIVE** | 495 rules / 296 triggered; writes ai_suggestions (verified: 19 advisories in a staging run). |
| **Water-budget engine (D03-WB)** | 🟢 **LIVE** | Compute layer derives deficit/dose ratios from `water_flow_lpm`; runs in build_farm_brain. Accurate once plot geometry is captured. |
| **Plot-geometry capture** | 🟢 **LIVE (dashboard)** | Streamlit **Plot Geometry** page writes `crop_seasons`; clears the D03-WB-008 gate. |
| **previous_stage (D03-SB-003)** | 🟢 **LIVE** | `plot_stage_log` written each run; transition rule fires once a plot is seen on a 2nd day. |
| Advisory compose subscriber | 🟢 **LIVE** | LISTEN agro_events → compose_advisory (Claude). Event-driven (fires on alerts), not scheduled. |
| Advisory delivery subscriber | 🟡 **off (by choice)** | `ADVISORY_DELIVERY_ENABLED=false` on staging while WhatsApp creds are pending — advisories compose + store, don't deliver. |
| Disclaimer + advisory_audit | 🟢 **LIVE** | Appended/recorded on every advisory. |
| Yield model (D11) | 🟢 **LIVE** | Runs in build_farm_brain (L4/EST placeholder calibration). |
| Consent / erasure / retention | 🟢 **LIVE** | Jobs + append-only tables. |
| Learning / QA-digest / retention jobs | 🟢 **LIVE** | 04:00 / 18:00 / 02:30. |
| **Satellite (Sentinel optical+SAR)** | 🟢 **LIVE (staging)** | `SATELLITE_JOB_ENABLED=true` + CDSE creds; fetching for PLOT_PILOT_001. New scenes every few days (revisit cadence), not daily. |
| **LST/thermal (Landsat)** | 🟢 **LIVE (staging)** | `LANDSAT_JOB_ENABLED=true` + USGS M2M creds. Runs 04:30. |
| Claude advisory text | 🟡 **key-gated** | Set `ANTHROPIC_API_KEY` (set on staging); verify the model id resolves (connectivity test). |
| WhatsApp send (Meta Cloud) | 🔴 **off (pending creds)** | Needs `META_WHATSAPP_TOKEN` + `META_WHATSAPP_PHONE_NUMBER_ID` (+ Live app). Template + webhook ready. |
| PLOT_PILOT_002 (satellite-only) | 🟡 **needs boundary** | Satellite is on, but this plot has no `gps_boundary_geojson` → `skipped_no_polygon`. Add its polygon to get data. |
| Farmer app | 🔴 **not built** | Several new KB fields need farmer-app capture surfaces. |
| OTA / object storage / prod backups | 🔴 **not built** | Roadmap. |
| VPS full deploy | 🟢 **deployed (staging)** | App/DB/schedulers running on the Lightsail box (`~/agri-AI-live`); migrations at head 0063. |

Legend: 🟢 live · 🟡 built but gated/config-needed · 🔴 off / not built.

## B2. Firing-intent KB rules — where each stands (this workstream)
- **Batch 1 (5 ready rules)** live: D01-PH-004, D02-DR-004, D02-ST-002, D02-LY-001 (blocking flat-layout gate), D02-LY-004 (layout prompt).
- **v1.2 cluster-2** live: D01-PW-001 (late-planting warning, `planting_doy>158`), D06-BW-001 (wilt gate), D03-SB-003 (stage transition — **now firing**: `previous_stage` is persisted in `plot_stage_log`), source_tier vocab fix.
- **Batch 2 (D06 disease)** live: D06-CH-002/FH-001/FH-002/ST-001/ST-002. **Batches 3–9** (36 firing-intent rules, D04/D05/D09/D10/D11/D12) live/dormant-safe.
- **Water-budget suite** live (0060): D03-WB-001..008 + D03-ST-001, fed by the compute engine (§11a). D03-WB-008 (geometry gate) clears once the Plot Geometry form is filled.
- **Final-decision rules (Kuldip, 0063)** live: **D04-MC-005** basal ZnSO₄ (`plot_status='pre_planting' AND agro_climatic_zone='marathwada_central'`), **D06-BW-004** wilt-history capture prompt, **D03-SB-004 SUPPRESSES D03-MN-002** (low-battery VWC veto; D03-MN-004 deliberately left live — it's rain-gap, not VWC).
- **Dormant** (wired, correct, fire only when a source exists): rules whose fields have no source yet — e.g. `years_since_last_wilt`, `harvest_complete`, `soft_rot_confirmed_in_cluster`, `seed_treatment_planned`, `fungicide_option_about_to_be_shown`. Need **farmer-app / ops / engine-composer** sources.
- **Agronomy decisions RESOLVED** (Kuldip, 30 Sep–1 Oct): soil vocab stays Season-1; D04-MC-005 fires `marathwada_central` only; D04-NS-003 & D08-WD-001 keep deployed triggers (Season-2 specs reserved as D04-NS-003-ledger / **D08-WD-002**); ZnSO₄ partial-dose tier reserved as **D04-MC-006**; D03-WL-004 reserved for a probe-driven waterlog companion. **KB closed for Season 1 on the buildable side.**

## B3. What's left (concrete)

**Config (staging):** satellite (`SATELLITE_JOB_ENABLED=true` + CDSE), Landsat (`LANDSAT_JOB_ENABLED=true` + USGS M2M), and `ANTHROPIC_API_KEY` are **set**; `ADVISORY_DELIVERY_ENABLED=false` by choice. Still pending:
1. **WhatsApp** — `META_WHATSAPP_TOKEN` + `META_WHATSAPP_PHONE_NUMBER_ID` (+ Meta app Live + verified WABA), then flip `ADVISORY_DELIVERY_ENABLED=true`.
2. **PLOT_PILOT_002 boundary** — set `gps_boundary_geojson` so satellite/Landsat stop skipping it.
3. **Verify the Claude model id** resolves (a stale `ANTHROPIC_MODEL_*` alias would fail composition silently) — connectivity test on the box.

**Done this cycle (0060–0063 + follow-ups):** water-budget rules + compute engine; plot-geometry capture (Streamlit); `previous_stage` persistence (D03-SB-003); the 3 final-decision KB rules; prod-log tracebacks + `ginger_daily` runner; the `k_source` pipeline hotfix.

**Product/data sources (unblock remaining dormant rules):**
4. Farmer-app capture screens for the new fields (wilt years, harvest_complete, seed-treatment dates, emergence, processing route, etc.); ops flags (soft_rot_confirmed_in_cluster, cibrc_verified, mandi price); engine-composer flags (fungicide/chemical about-to-show).
5. Season-2 KB activations when their sources land: D04-NS-003 cumulative-N ledger, D08-WD-002 herbicide registry gate, D03-WL-004 probe-driven waterlog, D04-MC-006 ZnSO₄ partial-dose.

**Platform hardening / roadmap:**
6. Object storage (R2/B2); nightly pg_dump backups; production Sentry alerting + Grafana; modem TLS `authmode=0→2` + secret rotation; OTA; farmer app; LoRa 433 MHz regulatory clearance for scale-up.

## B4. Operational lesson (1 Oct 2026) — the k_source outage

The daily pipeline (satellite / Landsat / ginger / forecast) was silently failing for ~2.5 weeks: `PgCropSeasonRepo._row_to_view` read `r.k_source` but `_SELECT_COLS` never selected it (added to the view in 0029, omitted from the SELECT), so every `list_active_by_crop` raised `NoSuchColumnError`. It was invisible because **prod/staging logging used `JSONRenderer` with no traceback processor** — `log.exception` emitted `"exc_info": true` and dropped the stack. Fixes: `dict_tracebacks` in the JSON logger (errors now carry the stack), a no-DB static test asserting `_SELECT_COLS` covers every column `_row_to_view` reads, and the `k_source` SELECT. **Lesson:** never ship JSON logging without a traceback processor; a repo whose mapper reads a column must select it (now guarded by a test).

---

*Maintainer note: regenerate this doc's Part B whenever config flags, schedulers, or the migration head change. Ground truth: `agro_backend/` + `firmware/`.*
