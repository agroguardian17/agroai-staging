# AgroGuardian Backend — System Overview for the Agronomy Team

**Purpose:** a single, accurate reference to how the deployed backend actually works — the database, the knowledge base (KB), the "mapper" that feeds rules their data, the engine, the advisory/delivery pipeline, and the yield model — so agronomy authoring aligns with production instead of an assumed schema.

**Audience:** Kuldip + VIRAAI agronomy.
**Maintainer:** Backend.
**Status of facts:** taken directly from the deployed code and migrations (Sep 2026). Figures like rule counts are live at time of writing.

> **Why this doc exists.** The 25-Sep deliverables were authored against an *assumed* schema (a single soil-class field, an L1–L4 tier system, a `compliance_tag` on rules, DATE literals in the DSL). The real system differs on each of those. This document is the ground truth; §9 lists the exact vocabulary mismatches to resolve. The companion [`kb_reconciliation_25sep_bundle.md`](kb_reconciliation_25sep_bundle.md) maps each bundle rule to its deployed state.

---

## 1. Architecture at a glance

- **Stack:** FastAPI + SQLAlchemy 2.0 (async, asyncpg) + PostgreSQL/PostGIS. Migrations via Alembic (currently at head **0053**).
- **Shape (hexagonal):** `app/domain` (pure logic, no framework imports), `app/application` (use-cases + `ports/` interfaces), `app/infra` (adapters: persistence, mqtt, whatsapp, satellite, forecast, llm, …). Purity is enforced by AST gates (e.g. `structlog` is forbidden in `app/application`).
- **The KB is a separate authored package**, not hand-written Python rules: `new-docs/AgroGuardian_Ginger_Engine_v1.0_9931/` holds the rule JSON, a Python authoring surface, the DSL engine, and tests. A build step compiles JSON → SQL, and a migration loads it into `kb_*` tables.
- **End-to-end flow:**
  ```
  Sub-node / Main-node telemetry (MQTT)  ┐
  Farmer app inputs, scouting, lab tests ├─► DB tables
  Weather forecast, satellite, IMD norms ┘        │
                                                  ▼
                              THE MAPPER  (build_farm_brain.py)
                     assembles the per-plot "farm brain" field dict
                                                  │
                                                  ▼
                        ENGINE (trigger DSL + precedence + delivery)
                     evaluates 237 machine-triggered rules against it
                                                  │
                                                  ▼
                 Advisory composer → disclaimer → WhatsApp (+ audit trail)
                                                  │
                                                  ▼
                          Yield model (D11) consumes stress signals
  ```

---

## 2. Database

The schema is ~67 application tables + 17 `kb_*` tables. Grouped by purpose (representative, not exhaustive):

**Identity & tenancy:** `tenants`, `users`, `farmers`, `farms`, `plots`, `crop_seasons`, `auth_sessions`, `refresh_tokens`, `otp_challenges`/`otp_codes`, `subscriptions_billing`.

**Devices & telemetry:** `device_registry`, `device_calibration`, `calibration_history`, `component_inventory`, `technician_installations`, `service_maintenance`; readings: `node_sensor_readings`(+`_p` partition), `main_node_readings`, `weather_station_readings`(+`_p`), `satellite_data`, `ingest_unmatched` (telemetry that didn't match a device), `event_outbox`.

**Agronomic state (farmer/plot facts the rules read):** `crop_scouting`, `irrigation_events`, `season_operations`, `lab_soil_tests`, `water_source_status`, `farmer_actions`, `farmer_photos`/`photo_label`, `weather_forecasts`(+`_p`).

**Advisory & AI:** `ai_suggestions` (fired-rule outputs; carries `confidence`, `rule_version`), `advisory_classification`, `ai_learning_log`, `bias_observation`, `chat_messages`, `alerts_notifications`, `notification_dispatch_log`, `notification_dlq`, `wa_inbound_log` (WhatsApp inbound), `advisory_audit` (append-only, immutable — see §6).

**Yield model (D11):** `yield_u_values` (factor→rule map), `variety_potential`, `site_index_config`, `yield_prediction_log`, `yield_actual`.

**Reference / lookup (read by rules):** `variety_stage_water_target` (per-variety water targets, 0051), `variety_n_ceiling` (N ceilings, 0052), `registered_herbicide_registry` (herbicide gate, 0053), plus code-level reference (`imd_normals`, pesticide registry CSV).

**Compliance / DPDP:** `farmer_consent`, `consent_event`, `erasure_request`, `non_compliance_reason`, `audit_log`.

**QA & clustering (D12):** `clusters`, `cluster_config`, `plot_cluster`, plus QA counters (§4).

**KB tables (loaded from compiled SQL):** `kb_rules`, `kb_rule_fields`, `kb_farm_brain_fields`, `kb_golden_tests`, `kb_rule_references`, `kb_rule_dependencies`, `kb_rule_categories`, `kb_precedence`, `kb_duplication_groups`/`kb_duplication_members`, `kb_domains`, `kb_stages`, `kb_source_classes`, `kb_source_tiers`, `kb_open_items`, `kb_overrides`, `kb_override_audit`. Two runtime tables FK to `kb_rules(rule_id)`: `advisory_log` and `kb_overrides` (these FKs are dropped/re-added around every KB reload — see §3.5).

Migrations run 0001 → 0053; each is transactional and reversible. Recent additions: 0044 (`ai_suggestions.confidence`+`rule_version`), 0045 `advisory_audit`, 0046 consent, 0047 erasure, 0048–0049 KB reload (VNMKV B1), 0050–0051 variety water, 0052 N-ceiling, 0053 herbicide registry.

---

## 3. The Knowledge Base

### 3.1 Scale
- **483 rules** across **14 domains**. Of these, **237 have a machine trigger** (`trigger.expr`) and are evaluated by the engine; the other **246 are knowledge entries** (reference/context/manual) with no trigger.
- **365 farm-brain fields** declared across the domain schemas.
- **24 immutable** rules (safety-critical core that overrides cannot disable).

### 3.2 Domains (rule counts)
| Domain | Name | Rules |
|---|---|---|
| D1 | Crop Lifecycle Stages | 22 |
| D2 | Soil & Land Preparation | 27 |
| D3 | Water & Irrigation | 31 |
| D4 | Nutrient & Fertilizer Management | 34 |
| D5 | Pest Management | 34 |
| D6 | Disease Management | 28 |
| D7 | Weather & Climate | 39 |
| D8 | Cultivation Operations | 38 |
| D9 | Harvest & Post-Harvest | 39 |
| D10 | Maharashtra & Kannad-Specific Data | 35 |
| D11 | Yield Impact Data | 34 |
| D12 | AI Training Data Requirements | 36 |
| D13 | Seed & Input Economics | 39 |
| D14 | Satellite & Remote Sensing Intelligence | 47 |

### 3.3 The rule object (JSON schema)
Each rule lives in `knowledge_base/DomainN_Rules_Ginger.json` under `rules[]`. Real fields (from a live rule):
- `rule_id` (e.g. `D03-DS-001`), `category` (e.g. `DS`), `priority`, `stage` (G0–G5), `severity`.
- `trigger`: `{ english, marathi, expr, expr_version, expr_note?, golden_tests[] }` — `golden_tests[]` are `{context, expect: TRUE|FALSE|UNKNOWN, label}`.
- `action`: `{ english, marathi }` (farmer-facing text).
- `reasoning`: `{ agronomic_basis, yield_impact, confidence_score, source_tier, references[] }`.
- `cross_domain_dependencies`: `{ feeds_into[], depends_on[] }`.
- `farm_brain_schema[]`: the fields this rule reads.
- `u_value`, `recoverability`, `source_class`, `kannad_note`, `decision_type`, `automation`, `status`, `immutable`, `delivery`.
- `review`: `{ tier, reviewer, date, outcome, comment_mr }` — **the 2026-09-22 `VIRAAI_AGRONOMY_REVIEW` verdicts live here**, not in a separate tag.

**There is no `compliance_tag` field on rules.** COMPLIANT/CONDITIONAL/etc. is tracked in the compliance document, not the runtime KB. What the KB carries is `review.outcome` (e.g. `conditional`) and `status`.

### 3.4 Controlled vocabularies (these are the alignment-critical ones)
- **`severity`** (SQL CHECK, 4 values): `info` (204 rules), `yellow` (193), `red` (61), `blocking` (25). This is the only "severity" — there is no separate blocking flag.
- **`delivery`** (how/whether a farmer sees it): `SILENT_GUARD` (94), `EVENT` (57), `ONCE_UNTIL_RESOLVED` (48), `WINDOW` (38); 246 rules have no delivery (knowledge-only).
- **`status`:** `AGRONOMIST_REVIEWED` (467), `PHASE_1_RAW_UNVALIDATED` (15), `AUTHOR_DRAFT` (1).
- **`source_class`:** `DERIVED` (215), `SRC-Q` (125), `SRC-D` (80), `EST` (42), `VERIFY` (16), `FIELD` (5).
- **`reasoning.source_tier`:** **`A` (248), `B` (208), `C` (27)** — an evidence-strength scale. ⚠️ This is **not** the bundle's `L1/L2/L3/L4` scale; those don't exist in the KB.
- **Soil fields — there are TWO, not one:**
  - `soil_type` — values include `'vertisol'` (used by D02-LY-001, D08-LY-001).
  - `soil_texture_class` — values `'heavy'` / `'medium'` / `'light'` (used by D03-DS-001).
  The bundle's `{vertisol, heavy_clay, clay_loam_heavy, sandy_loam}` matches neither. See §9.

### 3.5 The trigger DSL (what a rule's `expr` can say)
Defined in `engine/trigger_dsl.py`. **Three-valued logic** (TRUE / FALSE / **UNKNOWN**) — a missing field is UNKNOWN, never silently false. Grammar:
- Boolean: `AND`, `OR`, `NOT`, parentheses.
- Comparison: `field op value` where op ∈ `> >= < <= == !=`; value = number, `'quoted string'`, a bare word (treated as an enum literal), or another field.
- `field IN [v1, v2, …]`, `field BETWEEN lo AND hi`.
- `field IS NULL | IS NOT NULL | IS TRUE | IS FALSE`.
- `DURATION(field > x) > n HOURS|DAYS` (sustained condition; engine supplies `field__duration`).
- `WITHIN(date_field, n DAYS)` (engine supplies `days_to_<x>`).
- `MONTH IN [JUN, JUL, …]`, `STAGE IN [G2, G3, …]`.

**Not supported:** `DATE 'YYYY-MM-DD'` literals, string concatenation `||`, arithmetic, or function calls. So a rule like `planting_date > DATE(season_start_year || '-06-07')` cannot be written today (see §9-D4). **Every field named in an `expr` must be declared** in a domain `_schema` (`farm_brain_fields` or `additions.new_farm_brain_fields`) or it's a parse error.

### 3.6 Precedence (rule-vs-rule resolution)
Relations are declared in `engine/precedence.py` (and mirrored in JSON). **56 relations**, types in use: **`SUPPRESSES` (21), `SUPERSEDES` (10), `BUNDLES` (12), `SEQUENCES` (8), `ESCALATES` (5)**. There is **no `COMPLEMENTS`** — it's not a formal type (the bundle correctly flagged this). Cardinal principle encoded here: **VWC probe > water-budget > satellite** (ground truth wins).

### 3.7 Authoring surface + quality gates (how a rule change is made safely)
A rule is authored across **coupled surfaces that must stay in lockstep**, guarded by `agro_backend/tests/kb/test_authoring_gates.py`:
1. **JSON** — the rule body in `DomainN_Rules_Ginger.json`.
2. **`authoring/triggers_wave*.py`** — `TRIGGERS[rule_id] = {'expr': …, 'tests': [(ctx, expected, label), …]}`. The **drift gate** requires the `.py` expr to exactly equal the JSON expr, and `len(triggers_py) == len(triggers_json)`.
3. **`engine/notification_policy.py` `DELIVERY`**, **`engine/precedence.py` `PRECEDENCE`**, **`engine/expert_override.py` `IMMUTABLE`** — must match the JSON (set-equality).
4. **Golden tests** — the `run_d14_trigger_tests.py` gate parses every `expr`, checks every named field is declared, and runs each rule's golden tests. Baseline today: **237 rules parse, 237 declare all fields, 600/600 golden tests pass**.

To ship a rule change end-to-end:
```
edit JSON + triggers_wave*.py (+ DELIVERY/PRECEDENCE/IMMUTABLE if touched)
  → declare any new field in a domain _schema
  → run the two gates locally (drift + goldens) until green
  → python build/json_to_sql.py …  → regenerates ginger/generated/agroguardian_ginger_kb.sql
  → add a KB-reload Alembic migration (§3.8)
```

### 3.8 KB reload migration (the FK-safe dance)
Loading regenerated KB SQL (pattern in `alembic/versions/0048_*`):
1. `ALTER TABLE advisory_log DROP CONSTRAINT advisory_log_rule_id_fkey` and same for `kb_overrides`.
2. `TRUNCATE` the 15 `kb_*` reference tables `CASCADE`.
3. `op.execute(<regenerated SQL>)` (with the file's `BEGIN;`/`COMMIT;` stripped).
4. Re-add both FKs to `kb_rules(rule_id)`.
Forward-only (downgrade is a no-op) because the KB is derived data.

---

## 4. The Mapper (`app/application/build_farm_brain.py`)

**What it is:** the bridge that turns everything in the DB into the per-plot, per-day **field dictionary ("farm brain")** the KB rules evaluate against. It is keyed on the ~300+ names declared in `kb_farm_brain_fields`; **every declared field is present as a key**, defaulting to `None` (= UNKNOWN) when no source supplies it. Missing sources never raise — they stay UNKNOWN. It returns `FarmBrainState(state, filled, unknown)` so we always know coverage.

**Entry point:** `build_farm_brain(plot_id, today, deps)`. All data sources are injected as repository ports (`FarmBrainDeps`); an absent adapter just leaves its fields UNKNOWN.

### 4.1 Where each field comes from (data sources)
| Source | Table(s) | Example fields it fills |
|---|---|---|
| Latest sub-node reading | `node_sensor_readings` | `soil_moisture_vwc` (from `soil_moisture_avg_pct`), `ec_current` |
| Plot / season / farm facts | `plots`, `crop_seasons`, farm facts | `dap`, `current_stage`, `variety`, `area_acre`, `has_drip`, `dripper_lph` |
| Soil lab test | `lab_soil_tests` | soil chemistry; overrides `soil_texture_class` via USDA triangle when sand/silt/clay % present |
| Scouting | `crop_scouting` | D05/D06 pest & disease observation fields |
| Season economics / operations | `season_economics`, `season_operations` | ~110 agronomy-plan + ops fields (copied by name) |
| Weather station | `weather_station_readings` | `air_temp_max_c/min_c`, `rh_pct`, `dew_point_c`, `vpd_kpa`, `wind_speed_ms` |
| Weather forecast | `weather_forecasts` | `forecast_rain_48h_mm`, `rainfall_last_48h_mm`, `dry_spell_days`, `effective_rainfall_mm`, `heat_stress_days_count`, `severe_weather_alert_active` (proxy, not IMD) |
| Satellite | `satellite_data` | `plot_polygon_wkt`, `plot_area_ha`, NDVI/NDRE/NDMI/EVI, SAR vv/vh/rvi, `lst_c`, peer/regional baselines |
| Yield model | `yield_u_values`, `variety_potential`, `site_index_config` | `predicted_yield_quintal_per_acre`, loss %, u-values applied (§7) |
| QA counters | `advisory_classification`, `farmer_photos`, `photo_label` | `true_alarm_count`, `false_alarm_count`, `photo_uploaded_count`, `photo_labelled_count` |
| Reference (static) | IMD normals module; pesticide registry CSV | `rainfall_deviation_pct`, PHI blocklist gate |

### 4.2 Soil vocabulary is *derived*, not stored raw (important for §9-D1)
The DB `soil_type` column uses agronomist-facing values (black/red/sandy/loamy/mixed). The mapper maps that column into the two KB fields:
- `soil_type` → `_SOIL_TYPE_MAP` → `{vertisol, loam, sandy_loam, red_loam, other}` (unknown → `other`).
- `soil_texture_class` → `_SOIL_TEXTURE_CLASS_MAP` → `{light, medium, heavy}` (unknown → `medium`), stamped `soil_texture_class_source="derived"`. A lab test with particle fractions overrides it (USDA triangle) and stamps `source="lab"`.

So when the KB says `soil_type == 'vertisol'` or `soil_texture_class == 'heavy'`, those enum values are exactly what the mapper can emit. The bundle's `heavy_clay`/`clay_loam_heavy` would never be produced by the mapper → they'd always be UNKNOWN. **New soil classes require a new mapping + a data source, not just a rule edit.**

### 4.3 Synthetic & derived fields
- **Synthetic** (supplied by the mapper/engine, not stored): `current_month`, `days_to_planting`, `days_to_harvest`, plus four engine-side `*_proposed` fields (brand/capability/profit/price claims, filled at attempt time).
- **Composite** (computed, no new source): `vafsa_state` (too_wet/workable/too_dry from VWC vs the season's own saturation/stress thresholds), `prediction_stage`, `cwsi`, PHI-days-remaining, food-safety blocklist gate.
- **`<field>__duration`** (used by the DSL `DURATION(...)` operator): **currently all UNKNOWN** — the reading-history method they need is a follow-up. Any rule using `DURATION(...)` will not fire until that lands. (The module docstring claiming a 24-h VWC duration is stale vs the code.)

### 4.4 Coverage
Fields with no live source stay UNKNOWN and their rules return UNKNOWN (three-valued logic — they do **not** misfire as false). As more adapters/data come online (Main Node install, farm-config ingestion), coverage rises without rule changes. `non_compliance_reason` is deliberately *not* sourced here — it comes from the farmer's own WhatsApp reply, a separate channel.

---

## 5. The Engine runtime (`agro_backend/ginger/engine/`)

> There are two copies of the engine: the **authoring mirror** in `new-docs/.../engine/` (used by the drift/golden gates) and the **deployed** engine in `agro_backend/ginger/engine/`. Production reads rules from Postgres; the gates read from JSON. They must agree — that's what the drift gate enforces.

**Pipeline** (`runner.py`): farm-brain state → evaluate triggers (three-valued) → apply expert overrides → resolve precedence → apply notification policy → compose four-part Marathi messages → order by severity/priority.

### 5.1 Loading rules
`runtime_loader.py` has three sources with an identical `.load()` shape: `JsonSource` (dev / source-of-truth, reads the Domain JSON), **`PostgresSource` (production, reads `kb_rules`/`kb_rule_fields`/`kb_farm_brain_fields`/`kb_precedence`)**, and `SqliteSource` (offline mirror). `build_runner(source)` wires a `Runner`: the **immutable core, delivery map, and precedence graph all come from the DB in production**, and each trigger expr is parsed against the allowed field set (declared fields ∪ synthetic ∪ `__duration`).

### 5.2 Evaluating a day
For each rule: apply any in-force override (may disable / rewrite expr / change severity), then `evaluate(expr, ctx)` → TRUE / FALSE / **UNKNOWN**. **Only TRUE fires; UNKNOWN never fires.** Fired rules carry severity + priority + u_value. Then precedence resolves conflicts, delivery policy decides who actually gets messaged, messages are composed and sorted by `(severity_rank, -priority)`.

### 5.3 Precedence (`precedence.py`) — 5 typed relations
Relations are **typed, not severity-ranked**. `resolve()` applies:
- **SUPPRESSES** / **SUPERSEDES** — object rule removed (recorded).
- **ESCALATES** — subject folds into object; object severity raised to the more urgent; one message.
- **SEQUENCES** — if the subject (e.g. a diagnostic) isn't answered yet, the object (treatment) is held ("diagnosis before treatment").
- **BUNDLES** — surviving anchor pulls bundled members into one farmer message.
- A **fallback-ordering guard** records any adjacent severity change not backed by a typed relation, so a suppressed instruction can't silently reappear.

⚠️ **There is no `FEEDS` relation** in the resolver. The bundle uses "FEEDS" (and "INFORMS") — those aren't engine relations. Cross-domain `feeds_into`/`depends_on` exist only as **inert metadata** (they don't affect firing). Yield-model feeding (e.g. D03-ST-001 → factor-7) happens through the yield pipeline (§7), not a precedence edge.

### 5.4 Delivery classes (`notification_policy.py`) — how a fired rule becomes (or doesn't become) a message
- **SILENT_GUARD** — no message *unless the prohibited action is actually being attempted* (e.g. a herbicide guard stays silent until a herbicide is proposed). This is why blocking guards don't spam.
- **EVENT** — delivered once on the rising edge; re-armed only when the rule stops firing.
- **ONCE_UNTIL_RESOLVED** — issue immediately, then repeat on a `(0,7,21,45,90)`-day ladder, **raising severity rather than frequency**, until `resolve()`d.
- **WINDOW** — dated operation: issue when the window opens, then up to 3 spaced overdue reminders.

A rule's `severity` and `delivery` therefore jointly decide farmer impact — a `blocking` rule with `SILENT_GUARD` delivery is silent until the action is attempted.

### 5.5 Immutable core + expert overrides (`expert_override.py`)
- **Immutable core** (24 rules): banned molecules, no-fungicide-for-bacterial-wilt, PHIs, operator safety, DPDP consent/GPS-coarsening, honest-capability claims, brand independence, no profit guarantees, satellite prohibitions. Enforced **by code path** — an override on an immutable rule raises `OverrideRefused` and logs it. In production the immutable set is read from the DB.
- **Overrides** are scoped (plot/cluster/global), expiring (≤400 days), audited and reversible; kinds: THRESHOLD / DELIVERY / SEVERITY / DISABLE / PARAMETER. Guardrails: can't lower a blocking rule's severity, THRESHOLD's `from` value must actually be in the expr, red/blocking need a longer rationale.

### 5.6 Confidence & message composition
- **Severity** flows: rule → override → ESCALATES raise → ONCE_UNTIL_RESOLVED ladder bump → final `Message.severity` (drives sort + Marathi label/icon).
- **Confidence** = `reasoning.confidence_score`; kept in the **audit trail**, not shown to the farmer, but gates a "guidance only" note when `<0.72` or `source_class ∈ {EST, FIELD}`.
- Messages are composed in **four D12-mandated parts** (what / when / why / what-if-not), in farmer-facing Marathi.

### 5.7 State persistence (`persistence.py`)
Notification memory (first/last issued, active EVENT set, resolved set, window reminders), overrides, and answered-diagnostics are persisted per plot so a fresh daily run doesn't re-fire everything; a downtime `gap_days` is surfaced rather than silently replayed. `advisory_log` records issued advisories (and FKs to `kb_rules`).

---

## 6. Advisory & delivery pipeline

There are **two advisory paths**, both landing in the `ai_suggestions` table and sharing WhatsApp delivery:

1. **Daily deterministic path (the rule engine)** — `suggestion_type='daily'`.
2. **Event-driven LLM path** — an alert fires → Claude composes Marathi prose → `suggestion_type='alert'`.

### 6.1 The daily job
- **Schedule:** APScheduler cron, **06:30 Asia/Kolkata** daily (`GINGER_JOB_*` config), `misfire_grace_time=1h` (runs late rather than skipping). `app/jobs/ginger_scheduler.py`.
- **Body** (`app/jobs/ginger_daily.py`): compute "today" in IST → list active Ginger seasons → for each plot: `build_farm_brain(...)` (§4) → run the engine (`run_day`) via `asyncio.to_thread` (engine is sync/psycopg2, backend is async) → for each returned message: render → **append the disclaimer** → write one `ai_suggestions` row (`ai_model_version='ginger-engine/v1.0'`, `rule_version='ginger-kb/v1.0'`, plus `rule_id`/`confidence` from the engine) → **record an immutable `advisory_audit` row**.
- **Idempotency:** the engine's `advisory_log` keys on `(plot_id, day, rule_id)`; a UNIQUE index on `ai_suggestions` is noted as a future safeguard.

### 6.2 The disclaimer (`app/domain/disclaimer.py`)
Mandated by LEGAL §7.2 (IT Act §79 safe-harbour does not apply since VIRAAI generates active advice). `DISCLAIMER_MR` (verbatim Marathi: advice is rule/data-based; farmer makes the final call with a qualified agronomist; no yield guarantee; read CIB&RC labels + use PPE) is appended by **both** paths, idempotently, at compose/persist time. English copy is for audit only.

### 6.3 Audit trail (`advisory_audit`, append-only)
Every advisory records immutable **generation facts**: `suggestion_id`, `rule_id`, `rule_version`, `model_version`, `confidence`, `gate_results` (daily path: `{blocklist_hit, phi_days_remaining}`), `inputs` (daily path: `{dap, stage, as_of}`). A `BEFORE UPDATE OR DELETE` trigger `RAISE EXCEPTION`s — rows can never be altered. Delivery outcome lives separately on `ai_suggestions.delivery_status` (audit captures generation, not delivery).

### 6.4 WhatsApp delivery (`app/application/deliver_advisory.py`, `app/infra/whatsapp/`)
- Driven by `suggestion.generated` events + a reconciliation sweep; an atomic claim ensures one worker per suggestion.
- **State machine** on `ai_suggestions.delivery_status`: `pending → in_flight → sent / skipped / failed_permanent / failed_transient`, with backoff `(30,120,480,1800,7200)s` (up to 6 attempts). Transient vs permanent error classification is explicit.
- **Template:** `settings.META_WHATSAPP_ADVISORY_TEMPLATE_NAME` → default **`agroguardian_advisory_v2`** (UTILITY). The **entire Marathi advisory (with disclaimer) is sent as the template's single `{{1}}` body parameter** — required because a proactive message outside the 24h window must be a pre-approved template. Whitespace is sanitized (Meta rejects newlines/tabs in params).
- **Sender selection:** `MetaCloudWhatsappSender` only if `META_WHATSAPP_TOKEN` + `META_WHATSAPP_PHONE_NUMBER_ID` are set; otherwise a **`LogOnlyWhatsappSender`** so the pipeline runs end-to-end in dev/staging without a verified WABA.
- **Webhook:** `GET/POST /webhooks/whatsapp` — GET is Meta's verify handshake (`META_WHATSAPP_VERIFY_TOKEN`); POST verifies `X-Hub-Signature-256` HMAC (`META_WHATSAPP_APP_SECRET`), logs inbound farmer replies to `wa_inbound_log`, and turns replies into `farmer_action`s. Delivery-status receipts are parsed but **not yet persisted**.

### 6.5 What is NOT implemented yet (so agronomy doesn't assume it)
- **No urgency tiers, no push notifications.** Every advisory goes out the same way (one WhatsApp template), regardless of severity/confidence. `severity` decides whether an *alert* is created upstream, but delivery does not branch on it.
- **`confidence` is recorded but does not gate or prioritise delivery** (confidence-band scoring is a later round).
- **No human-in-the-loop review** by default (`ADVISORY_REQUIRE_REVIEW=False`) until the agronomist review UI exists.

> Implication for the bundle: the water-budget rules' `push_notification = TRUE` and `urgency = red/normal/important` fields have **no delivery effect today** — they'd be recorded but not acted on. Urgency→push is future work.

---

## 7. Yield model (D11) and the factor→rule mapping

The yield model runs **inside the daily farm-brain build** (not a separate service). Live implementation: `app/domain/yield_forecast.py` (v1, `ginger-yield/v1-est-phase-1`); an older `yield_model.py` scaffold is superseded.

### 7.1 The formula
`Y_potential = Y_var × SI` (variety ceiling × site index), then `Y_process = Y_potential × Π(1 − uᵢ·Iᵢ)` over loss factors, `Y_final = Y_process + ε_ml` (ε=0 in Season 1). A 90% CI is produced by a 1000-draw Monte-Carlo. Per-factor **attribution** apportions the yield gap, with a remainder as `unexplained_pct`. Written to `yield_prediction_log` (best-effort; a log failure never blocks the advisory).

### 7.2 The factor register (`yield_u_values`) and factor→rule mapping
15 loss factors, each with a `u_value` (max loss), a `signal_field` (the farm-brain field that drives intensity `I`), and a **`representative_rule_id`** (the KB rule the loss is attributed to). Examples:

| # | factor_key | u | signal_field | rep. rule |
|---|---|---|---|---|
| 1 | soft_rot | 0.60 | rot_incidence_pct | D06-ROT-001 |
| 2 | waterlogging | 0.35 | standing_water_hours_observed | D03-DR-001 |
| 3 | bacterial_wilt | 0.50 | wilt_incidence_pct | D06-WILT-001 |
| **7** | **drought_fill (G3-G4)** | **0.20** | **dry_spell_days** | **D03-ST-001** |
| 13 | late_planting | 0.20 | planting_date | D01-PW-001 |
| 14 | wrong_drip_design | 0.15 | drip_lateral_spacing_ft | D03-DS-001 |
| 15 | herbicide_damage | 0.40 | herbicide_post_emergent_date | D08-WD-001 |

All factors are currently `L4 / EST_phase_1` with placeholder `confidence=0.50`, to be recalibrated after Season 1. **Interdependence clusters** (e.g. `soft_rot_cluster={1,2,11}`) prevent double-counting a causal chain: only the max-loss member of a cluster enters the survival product.

### 7.3 "Factor-7" and D03-ST-001 (directly relevant to the water-budget bundle)
Factor-7 = **drought during rhizome fill**. Its intensity is computed **directly from the `dry_spell_days` field**: `I₇ = clamp01(dry_spell_days / 30)`, loss `= Y_potential × 0.20 × I₇`. `D03-ST-001` is its `representative_rule_id` — i.e. **the attribution label**, appended to `u_values_applied` so a loss traces back to that rule. **Important:** `D03-ST-001` is *referenced by the register but not yet deployed as a KB rule* — it's gated on `flow_telemetry_present` (Water-Budget v1.3 §9). The yield model still works today because factor-7 reads `dry_spell_days` directly, independent of the rule firing. So the bundle's plan to have D03-ST-001 "feed factor-7" is partly already true (the register points at it) and partly blocked (the rule body awaits hardware).

---

## 8. Reference lookup tables (just added from the 25-Sep bundle)
- **`variety_stage_water_target`** (0051): per variety (`IISR-Mahima`/`IISR-Varada`/`Nadia-local`) × stage (G0–G5, LIFECYCLE) → water targets + DAP bands. Source tier L3 (indicative), re-calibrated from Season-1 data.
- **`variety_n_ceiling`** (0052): per variety → total N ceiling (kg N/acre), split schedule, DAP-150 late cutoff.
- **`registered_herbicide_registry`** (0053): 13 products × compliance tier (recommended-practice / hard-block / off-label-needs-verification), doses, timing, PHI.

These are keyed by variety/product and read by the (future) rules; they don't depend on the rule vocabulary.

---

## 9. Vocabulary & schema mismatches to resolve (the drift)

| # | Bundle assumes | Deployed reality | Resolution |
|---|---|---|---|
| D1 | one `soil_texture_class ∈ {vertisol, heavy_clay, clay_loam_heavy, sandy_loam}` | two fields: `soil_type` (has `vertisol`) + `soil_texture_class` (`heavy/medium/light`) | agree a single mapping; recommend reusing existing fields for Season 1 |
| D2 | rules carry a `compliance_tag` (COMPLIANT/…) | no such field; verdicts live in `review.outcome` + a separate tracker | retags are tracker edits, not code |
| D3 | `D04-MC-004` free for basal ZnSO₄ | `D04-MC-004` is a live heat/rain spray rule | assign ZnSO₄ a new id (e.g. `D04-MC-005`) |
| D4 | DSL has `DATE` literals + `||` | DSL has neither | keep `MONTH IN […]`, or add a `planting_doy` int field, or build DATE support |
| D5 | evidence tiers `L1–L4` | evidence tiers `A/B/C` (`reasoning.source_tier`) | map L-scale → A/B/C |
| D6 | new N fields, wilt `years_since_last_wilt`, etc. | existing `n_applied_kg_per_acre`, `field_history_wilt`, `previous_crops_3yr` | reconcile field-by-field before authoring |

The rule-by-rule mapping (which bundle rules are already applied vs pending vs blocked) is in [`kb_reconciliation_25sep_bundle.md`](kb_reconciliation_25sep_bundle.md).

---

## 10. How to propose a rule change (checklist for agronomy)

For each new/changed rule, give backend:
1. **rule_id** (confirm it's free, or that you intend to edit an existing one).
2. **trigger** in DSL terms that the grammar in §3.5 supports, using **fields that exist** (§3.4) — or name the new field + its data source so we can declare and populate it.
3. **severity** from the 4-value enum; **delivery** from the 4-value enum.
4. **action** text (English + Marathi).
5. **golden tests**: at least a fire case + a near-miss (context → expected TRUE/FALSE).
6. **precedence** using only the 5 formal relations (§3.6).
7. **source_tier** on the `A/B/C` scale + references.

Backend then implements it across the coupled surfaces (§3.7), proves the gates green, regenerates the SQL, and ships a reload migration.
