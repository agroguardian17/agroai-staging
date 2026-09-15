# AUDIT/02 — Findings

**Date:** 2026-09-15 · **Method:** read-only (code, migrations, firmware, deploy, tests, docs; local `.venv`; three background inventory agents; VPS read-only from AUDIT/01). No code changed.

**Severity key:** 🔴 blocker · 🟠 high · 🟡 medium · ⚪ low · ℹ️ info

**Verified CLEAN (checked, no defect):**
- **A/contract:** firmware CSV → Main Node JSON `raw_readings`/`master_readings` → backend `TelemetryInRaw`/`TelemetryMaster` match field-for-field; all six wire models `extra="forbid"`; `$schema` v2/v2-raw/v2-master all dispatched; topic filter `agro/v2/+/+/+/telemetry` catches telemetry + heartbeat; `window_s` three-way handled in `calibrate_flow_lpm`; `npk_ok=false` short-circuit present.
- **C/correctness:** calibration math matches skill §10 exactly; `_normalize_clock_skew` bounds (1 d future / 365 d past) applied post-`to_domain`, pre-ingest, duck-typed across Reading/MainNodeReading/WeatherStationReading; idempotent UPSERT `(node_id, recorded_at)`; 4 validation gates run in order; `_jsonb_param`/`CAST(:x AS type)` discipline followed; **no `float` on measurements, no naive `datetime` in domain/application, domain+application purity tests pass (38/38)**.
- **D/robustness:** bounded ingest queue (drop+meter, never blocks paho); per-message try/except keeps drain loop alive; external HTTP timeouts (WhatsApp 10 s, Claude 30 s); DB pool timeout 30 s.
- **F/API:** all endpoints carry `response_model` + `ClaimsDep` auth (health/ready/metrics correctly open); Round 17.5 `main_nodes` routes ARE tested (`test_main_nodes.py`).

---

## A — Contract

**F-001 · ⚪ · `app/infra/mqtt/schemas.py` (MasterReadings/Heartbeat `time_source`)** — `time_source` is accepted as free `str` (≤16), not validated against the `ntp`/`rtc`/`none` set the firmware emits. *Impact:* a malformed provenance string persists silently. *Fix:* `Literal["ntp","rtc","none"]` or a validator. *Blast:* schema + 1 test.

**F-002 · ℹ️ · `firmware/*/…_config.h`** — firmware version literals are still `viraai-sn-1.0.0-raw` / `viraai-mn-1.0.0-raw` despite "v2.1" behaviour in skill/comments. Firmware is frozen → **doc note only**, no change.

## B — Naming

**F-003 · 🟡 · cross-cutting (`weather_station_readings`)** — the same physical Main Node is keyed `main_node_id` everywhere (device_registry, `main_node_readings`, firmware, NODE_MAP) **except** `weather_station_readings`, which uses `master_node_id` (DB column, `WeatherStationReading`, API `WeatherRow`, DATA_INVENTORY). *Impact:* join friction + easy mis-wiring (`_persist_weather` already has to map `main_node_id`→`master_node_id`). *Fix:* standardize on `main_node_id` (rename column + domain + repo + API) — needs a migration, so **defer to a post-Round-13 batch**; or consciously document the split. *Blast:* 1 column rename migration + domain/repo/API/docs.

## C — Correctness

**F-004 · 🟡 · `app/infra/ginger/pg_state_store.py:155`** — `datetime.utcnow().isoformat()` writes a **naive** UTC timestamp into `advisory_log`, violating `.cursorrules #2` (tz-aware everywhere). *Impact:* naive ts in ginger advisory history; ambiguous on comparison/serialisation. *Fix:* `datetime.now(UTC)`. *Blast:* 1 line + test. (Infra layer, so not a purity violation — a correctness/convention one.)

**F-005 · 🟡 · `app/application/compose_advisory.py:46`** — `chat_model_name: str = "claude-sonnet-4-5"` hardcodes a model id in the application layer, against `.cursorrules #21` / skill §25. *Impact:* model choice not config-driven; drifts from `settings.ANTHROPIC_MODEL_SONNET`. *Fix:* make it required and pass `settings.ANTHROPIC_MODEL_SONNET` at the jobs seam (this is the agreed Round 13 wiring). *Blast:* use case + deps + `test_compose_advisory`.

## D — Robustness

**F-006 · ⚪ · `app/infra/llm/claude_chat.py` / `compose_advisory.py`** — the adapter classifies transient/permanent but **does not retry**; `compose_advisory` calls `complete()` once. No retry/backoff exists today. *Impact:* a transient LLM blip drops the advisory (acceptable while compose is manual-only). *Fix:* the Round 13 retry state machine covers this — no separate action.

## E — Schema / migrations

**F-007 · ⚪ (downgraded from 🟡) · `alembic/versions/0006_aggregates.py`** — 4 materialized views (`node_readings_hourly/daily`, `weather_hourly/daily`) are created `WITH DATA` + UNIQUE indexes but **nothing ever runs `REFRESH MATERIALIZED VIEW`**, so they only hold their creation-time snapshot. **Re-characterized during Batch D:** grep confirms **no code in `app/` or `dashboard/` queries these 4 views or `v_plot_latest_state`** — they have *no consumer*, so the staleness breaks no feature. *Fix (decision, not a refresh job):* either wire a consumer + a refresh job when a feature needs them, or drop the views. Not scheduled — a refresh scheduler for dead objects would be churn. *Blast:* n/a until a consumer exists.

**F-008 · 🟡 · `alembic/versions/0012`, `0013` (device_calibration, main_node_readings)** — both tables are tenant-scoped (`tenant_id NOT NULL`) but were added **after** 0008 and never enrolled in RLS (`ALL_RLS_TABLES` doesn't include them). *Impact:* no DB-level tenant isolation on calibration + heartbeat history. **Mitigated:** RLS is dormant defence-in-depth (app never `SET ROLE`s / sets session GUCs — SCHEMA_DECISIONS §10); app-layer repo scoping is the active protection. *Fix:* a migration enrolling both in the RLS policy set. *Blast:* 1 migration.

**F-009 · ⚪ · migrations (all)** — 103 FK `REFERENCES` lack an explicit `ON DELETE`; only 2 specify one (`main_node_readings` CASCADE). *Impact:* deleting a farmer/farm/device defaults to `NO ACTION` (blocked by dependents) with no documented policy. *Fix:* define per-table `ON DELETE` intent (design task; deferrable). *Blast:* migration(s).

**F-010 · ⚪ · `app/infra/persistence/models/core.py` vs 0009** — active auth tables `otp_challenges` + `auth_sessions` (0009) have **no ORM model**; legacy `otp_codes` + `refresh_tokens` have ORM models but are unused. *Impact:* `Base.metadata.create_all()` ≠ the migrated schema (would create dead tables, miss live ones). Migrations are authoritative (`target_metadata=None`), so no runtime break. *Fix:* add ORM models for the active tables (or document create_all as non-authoritative). *Blast:* 2 models. (Known: CODEBASE_GUIDE limitation #8.)

**F-029 · 🟡 · `alembic/versions/0008_rls_policies.py` `downgrade()`** — the full `upgrade head → downgrade base → upgrade head` round-trip **fails at 0008**: `DROP ROLE authenticated_role` raises `DependentObjectsStillExist` because grants made to the role on tables created in 0001/0002 (and matview grants) still depend on it when 0008 downgrades (later migrations already rolled back, but the base tables remain). So the migration chain is **not fully reversible** (`.cursorrules #18`). *Discovered by:* running `test_migration_roundtrip` (Batch E). *Impact:* a clean `alembic downgrade base` is impossible; blocks enabling the destructive round-trip in CI. *Fix:* in 0008 `downgrade()`, `REVOKE`/`REASSIGN`/`DROP OWNED BY … CASCADE` (or drop dependent grants) before `DROP ROLE`. **⚠️ Editing an existing migration file — flagged for your ruling** (the mandate's "modify Alembic history" stop-condition); alternative is to accept non-reversibility and document it. *Blast:* 0008 downgrade body + re-run round-trip.

## F — API

**F-011 · 🟡 · `app/infra/http/health.py:66` (`/ready`)** — readiness is a phase-0 stub: returns `ok=True` for postgres/mosquitto/chroma **without pinging them**, and the prod `app` container declares **no Docker healthcheck** either. *Impact:* false-green readiness; an orchestrator/LB can't detect a degraded backend (DB down still reports ready). *Fix:* implement real probes (`SELECT 1`, broker connect check, chroma heartbeat) + add a compose healthcheck. *Blast:* health.py + test + compose.

## G — Deploy / ops  (detail in AUDIT/01; carried here with fix intent)

**F-012 · 🔴 · GitHub `agroai-staging` (PUBLIC) + repo** — committed secrets in a **public** repo: `deploy/mosquitto/passwd`, `deploy/mosquitto/acl`, and the device MQTT password in `firmware/main_node/include/pilot_config.h`. *Impact:* live credential exposure. *Fix:* make repo private; rotate the MQTT credential; `git rm --cached` + history scrub (git-filter-repo/BFG); move secrets to deploy-only storage. *Blast:* repo settings + history rewrite (coordinate; force-push to a rewritten history is the one case needing explicit approval).

**F-013 · 🟠 · staging VPS** — no DB backups: no cron, no `pg_dump`, no systemd timer. *Impact:* total data loss on volume failure. *Fix:* nightly `pg_dump` → R2/B2 + systemd timer + restore drill.

**F-014 · 🟠 · `agro_backend/.github/workflows/ci.yml`** — CI never runs (workflow nested below repo root → 0 workflows/0 runs on GitHub), and its test job masks migration failure with `alembic upgrade head || true`; no branch protection on `main`. *Impact:* zero automated quality gate. *Fix:* move `.github/` to repo root, drop `|| true`, add required status checks + branch protection.

**F-015 · 🟡 · `docker-compose.prod.yml` + host** — only `postgres` has a healthcheck; `app` and others have none; no restart backoff caps; no `mem_limit`/`cpus`; host is 1.9 GiB RAM / 0 swap (under the 2–4 GB rec). *Impact:* silent unhealthy containers; OOM risk. *Fix:* healthchecks on app/mosquitto/caddy, resource limits, add swap.

**F-016 · 🟡 · running image `ghcr.io/agroguardian/agro-backend:latest`** — mutable `:latest` tag; GHCR org `agroguardian` ≠ repo owner `agroguardian17`; CI builds with `push:false` so nothing publishes it → **image provenance unverifiable** (can't map running image → commit). *Impact:* can't reproduce/rollback deterministically. *Fix:* pin by digest or immutable SHA tag; align GHCR namespace; have CI build+push on tag.

**F-017 · 🟡 · VPS `/home/ubuntu/agro_backend@dc49b05`** — dormant orphan checkout (pre-transfer lineage, doesn't contain `f46a8a0`, 21 dirty). *Impact:* someone could `docker compose` from the wrong dir. *Fix:* remove after confirming it's unused (Phase 6, with approval).

## H — Tests

**F-018 · ⚪ · `tests/infra/persistence/test_schema_db.py:210`** — `test_migration_roundtrip` (full `upgrade head → downgrade base → upgrade head`) is `skipif AGRO_RUN_DESTRUCTIVE != 1`, so reversibility is not exercised by default or in CI. *Impact:* a non-reversible migration wouldn't be caught automatically. (My manual drill covered `0013↔0012` only.) *Fix:* run it in a dedicated CI job once CI lives.

**F-019 · ℹ️ · CI** — 80% coverage gate is configured but never enforced (CI dead — see F-014). 596 tests collected across 51 files; purity green.

## I — Doc-vs-code drift

**F-020 · 🟡 · `FILE_REFERENCE.md`, `CODEBASE_GUIDE.md`, `API_REFERENCE.md`, `PROJECT_OVERVIEW.md`, `DEVELOPMENT.md`** — all frozen at ~migration 0009 / Round G: no Round 16/17/17.5 (device_calibration, weather_station_readings, main_node_readings, the 4 `main_nodes` endpoints, migrations 0010–0013), and understate tests ("~470" vs 596). (`DATA_INVENTORY.md` and `SKILL` are current.) *Fix:* refresh the five stale docs.

**F-021 · 🟡 · `PROJECT_OVERVIEW.md §5–6`** — states LoRa carries a **binary** frame and the SIM is **BSNL (`bsnlnet`)**; reality is **CSV** over LoRa and **Airtel (`airtelgprs.com`)** (HARDWARE_WIRE_CONTRACT + firmware + DATA_INVENTORY). Also "Sensors today: DS18B20 + capacitive; coming: NPK" — NPK is live. *Fix:* correct §5–6.

**F-022 · ⚪ · OTP hashing** — `app/domain/auth.py` uses **salted SHA-256** (`sha256$<salt>$<hex>`). PROJECT_OVERVIEW/CODEBASE say **bcrypt/passlib**; DATA_INVENTORY says **Argon2id**. Both wrong. *Note:* SHA-256 is defensible for a short-TTL 6-digit OTP with lockout, but decide if it should be strengthened; `users.password_hash` "Argon2id" is aspirational (no staff-login flow exists). *Fix:* correct docs (+ a security decision).

**F-023 · ⚪ · skill §7/§17** — claims **pgvector** present; it's absent by design (0003 best-effort with documented fallback; RAG uses ChromaDB). *Fix:* correct skill wording.

**F-024 · ⚪ · skill §18** — says clock-skew bounds are in `Settings`; they're module constants in `broker.py` (`MAX_CLOCK_SKEW_FUTURE/PAST`), not env-configurable. *Fix:* correct skill (or move to Settings if configurability is wanted).

**F-025 · ⚪ · `.cursorrules #21` / skill §25** — mandate `ModelRole (PRIMARY/TRIAGE)`; not implemented (config strings + the F-005 hardcode). *Fix:* amend the rule text now ("model ids from `settings.ANTHROPIC_MODEL_*`; `ModelRole` planned"); implement the enum in a later round. (Ties F-005.)

**F-026 · ⚪ · `HARDWARE_WIRE_CONTRACT.md §4.3`** — documents the **old** Sub Node CSV (`BAT,BATP,DST,SOIL,…,NMOIST`). Actual v2.1 CSV is `NODE,SEQ,WIN,UP,SOIL,BAT,PRESS,FLOW,FTOT,DST,NOK,NT,NM,EC,PH,N,P,K[,FLT],FW`. (The JSON contract §11–13 is current.) *Fix:* update §4.3.

**F-027 · ⚪ · `SUB_NODE_FIRMWARE_CHANGES.md`, FILE_REFERENCE, PROJECT_OVERVIEW §9** — reference `firmware/sub_node/eeprom_provisioner/…` + an EEPROM node-ID flow; the frozen firmware uses a compile-time `NODE_ID` in `sub_node_config.h` and the provisioner dir doesn't exist (AUDIT/00 T-b). *Fix:* doc correction.

**F-028 · ℹ️ · skill §17/§20** — "backend/Postgres/dashboard local-only; only TLS edge on VPS" is wrong (staging runs the full stack). This is the mandated correction; `CONFIGURATION.md` already describes it correctly.

## J — Doc-vs-doc conflicts  (⚠️ catalog only — resolution needs your approval, per the mandate)

| # | Conflict | Sources | Proposed winner (why) |
|---|---|---|---|
| J-1 | Migration head | PROJECT_OVERVIEW/CODEBASE/DEVELOPMENT/FILE_REFERENCE say ≤0009/0011 · SKILL/DATA_INVENTORY/code say 0013 | **0013** (code/migrations win) |
| J-2 | Table count | PROJECT_OVERVIEW header "58" · its own TOC "35" · SKILL "60" | **60 logical** (verified via pg_class: 57 plain + 3 partition parents) |
| J-3 | LoRa payload | PROJECT_OVERVIEW "binary" · HARDWARE_WIRE_CONTRACT/SKILL/firmware "CSV" | **CSV** (code wins) |
| J-4 | Modem APN | PROJECT_OVERVIEW "BSNL bsnlnet" · SKILL/firmware/DATA_INVENTORY "Airtel airtelgprs.com" | **Airtel** (firmware wins) |
| J-5 | Test count | SKILL/PROJECT_OVERVIEW "~470" · actual 596 | **596** (measured) |
| J-6 | OTP hash | PROJECT_OVERVIEW/CODEBASE "bcrypt" · DATA_INVENTORY "Argon2id" · code SHA-256 | **salted SHA-256** (code wins) |
| J-7 | Deployment state | SKILL §17/§20 "local-only" · CONFIGURATION.md "staging runs stack" · reality full stack | **full stack on staging** (CONFIGURATION right) |
| J-8 | Pilot scale | roadmap "4 plots / 2 Sub Nodes" · SKILL/seed "2 plots / 1 Sub Node" | **2 plots / 1 Sub Node** (seed/code win) |
| J-9 | Model id | roadmap + `.cursorrules` "claude-sonnet-4-6" · config/skill "claude-sonnet-4-5" | **claude-sonnet-4-5** (config wins) |
| J-10 | Firmware version | skill milestones "v2.1" · firmware literal "1.0.0-raw" | both true (behaviour v2.1, string 1.0.0-raw) — **doc-note, no code change** |

---

## Severity tally
- 🔴 blocker: **1** (F-012)
- 🟠 high: **2** (F-013, F-014)
- 🟡 medium: **11** (F-003, F-004, F-005, F-007, F-008, F-011, F-015, F-016, F-017, F-020, F-021)
- ⚪ low: **11** (F-001, F-006, F-009, F-010, F-018, F-022, F-023, F-024, F-025, F-026, F-027)
- ℹ️ info: F-002, F-019, F-028
- J-catalog: 10 doc-vs-doc conflicts awaiting your reconciliation ruling.

## Firmware / ginger — NOT proposed for change
- Firmware v2.1 is frozen: F-001, F-002, F-026, F-027 all resolve as **backend/doc** fixes, never firmware edits.
- `ginger/` upstream: no defects found in it during this pass; `pg_state_store.py` (F-004) is **our** adapter, not `ginger/`.
