# Hardening & Observability — Audit, Plan & Backlog (Round 3)

**Status:** PLAN for review — nothing built yet. Produced from a read-only audit (2026-10-24); baseline is
green (ruff / ruff-format / mypy / full test suite all pass, migration head 0069).

**What this answers (your asks):**
- **Task 1a — find all bugs/issues:** Part A (prioritized findings).
- **Task 1b — observability "next level" (see every reading's full journey, every event, raw values; system
  points out issues itself):** Part B (design, phased).
- **Task 1c — tighten the manual test checklist:** Part C.
- **Task 2 — consolidated findings + all pending/on-hold tasks (WhatsApp etc.):** Part E (the backlog).

**Charter (unchanged from Rounds 1–2):** everything additive · flag-gated · best-effort (a trace/diagnostic
failure can **never** affect ingest, the daily job, or any hot path) · bounded retention · no domain-purity or
hot-path change · shipped as small, reviewable PRs. We plan first, then execute one piece at a time.

---

# PART A — Audit findings (prioritized)

Severity: **P0** = safety-net/data-integrity failure · **P1** = silent failure / wrong data · **P2** =
robustness / observability gap · **P3** = cleanup. Each: what · where · impact · evidence · fix · risk.

### P0 — Critical

**A1 — WITHDRAWN (audit error): the watchdog works correctly.**
Originally flagged as "DEVICE_OFFLINE watchdog silently not firing." Verified on the box 2026-10-24: there are
**47 `device_offline` alerts** (first 2026-10-08, last 2026-10-23 17:38) — the watchdog *did* detect the gateway
outage and fired on its 6-hour cooldown. My "0 alerts" conclusion was a **case-sensitivity mistake in my own
query** (`alert_type='DEVICE_OFFLINE'` vs the stored lowercase enum value `'device_offline'`). Running the real
`check_device_liveness` on the box showed `last_triggered_at → 2026-10-23 17:38`, so `raised=0` is the *correct*
cooldown behaviour. **No code bug.** (Lesson → A11.)

**A1′ (reclassified from A1, P1). Alerts fire but are invisible to the operator.**
- *Impact:* the watchdog + the 7 device-health rules create alerts correctly, but `ADVISORY_DELIVERY_ENABLED=false`
  means nothing is delivered, and **no dashboard surfaces them** — so a 2-week outage produced 47 `device_offline`
  alerts (and 103 `low_water`) that **nobody saw**. The detection worked; the *surfacing* didn't.
- *Fix:* surface alerts prominently — an "Alerts" view / the **Event Timeline (R3.2)** + a badge on **Daily
  Health** — and/or an ops notification channel (even an email on red). This is the strongest case for Part B.
  *Risk: low (read-only dashboard) / medium (a notification channel).* 

### P1 — High

**A2. `qa_weekly_digest` fails every Sunday — `PermissionError: 'qa_digests'`.**
- *Where:* `app/infra/qa_digest_writer.py:18` (`base.mkdir(... )` then `write_text`), dir `qa_digests` (relative → `/app`).
- *Impact:* the weekly QA/bias digest is never produced. Also a design smell: it writes to the **container
  filesystem** (ephemeral — lost on every redeploy).
- *Evidence:* `qa_weekly_digest.tick_failed` in logs with `PermissionError(13)` creating `qa_digests`.
- *Fix:* write under a writable, mounted path (a volume or `QA_DIGEST_DIR` pointed at one), or persist the digest
  to Postgres/object storage and surface it on a dashboard page instead of the filesystem. *Risk: low.*

**A3. `weather_forecast` intermittently writes 0 rows (per-farm fetch fails, swallowed to a count).**
- *Where:* `app/application/refresh_forecasts.py:48-54` (per-farm `except … continue`, increments `failed_farms`).
- *Impact:* some nights `rows_written: 0, failed_farms: 1`. No retry, and the **actual error is not surfaced** —
  only a count. A run of consecutive failures would let forecasts silently go stale.
- *Evidence:* `job_run` summaries alternate `{rows_written:28}` and `{rows_written:0, failed_farms:1}`.
- *Fix:* capture the per-farm error (type/message) into the job summary (and the Reading/Event trace, Part B); add
  one retry; and have the diagnostics `forecast_coverage` check *also* require a recent **successful** forecast run
  (not just that some past run covers today). *Risk: low.*

**A4. Failure logs dump the entire `Settings` object.**
- *Where:* structlog `dict_tracebacks` serialises frame locals; `instrument_job` / job `_job` frames hold `settings`.
- *Impact:* every job failure emits a multi-KB log line containing the full config repr (DB URL fragment, IDs,
  bucket names, model ids — secrets are `SecretStr`-masked, but it's noisy and leaks non-secret config).
- *Evidence:* the `qa_weekly_digest.tick_failed` line in your run was ~6 KB of `Settings(...)`.
- *Fix:* keep the traceback but drop/trim frame locals in the JSON renderer (e.g. `dict_tracebacks` with
  `show_locals=False`, or a processor that elides large locals), or avoid binding `settings` in the failing frame.
  *Risk: low; must keep the stack (the k_source lesson).* 

### P2 — Medium

**A5. Dev smoke scripts aren't in the prod image.** `fake_main_node.py`, `inject_test_reading.py`,
`fetch_satellite_once.py`, `probe_cdse_raw.py` are missing at `/app/scripts/dev/` on the box (only `lst_smoke` /
`whatsapp_smoke` are present). *Fix:* COPY `scripts/dev/` into the image (or document running them from a mounted
checkout). Blocks on-box ingest/satellite smoke tests. *Risk: low.*

**A6. `forecast_coverage` diagnostic can mask a dead forecast job** (passes while old-but-future-dated rows
linger). *Fix:* cross-check the `weather_forecast` ledger status (see A3). *Risk: low.*

**A7. Advisory compose/deliver path is untraced** (deferred in Round 2). You can't see a single advisory's journey
(trigger → compose model/tokens/latency/log-only → disclaimer → audit → delivery → WhatsApp status). *Addressed in
Part B (R3.3).* 

**A8. Device-rule evaluation is not traced per reading.** `pipeline_trace` covers ingest stages s1–s7 but not the
7 device-health rules' per-reading evaluation (which rule matched, the input value, cooldown-suppression, the
resulting alert). This is the core gap for "see what happened to this reading." *Addressed in Part B (R3.1).*

### P3 — Cleanup

**A9. `SYSTEM_TEST_AND_RATIONALE.md` has wrong commands** — `make diagnose` only works in-container (host has no
`python`); `alerts_notifications` uses `triggered_at` not `created_at`; `satellite_data` uses `ndvi_min/ndvi_max`
not `ndvi_mean`; dev scripts (A5). *Fix in Part C.*

**A10. `except Exception` audit (35 sites).** Most are intentional best-effort (trace writes, metrics, per-farm
sweeps). *Action:* a one-pass review that each either re-raises on a hot path or is deliberately best-effort
(none found swallowing a critical path in the audit, but worth a documented pass).

**A11. Enum values are stored lowercase (`alert_type`, severities, etc.) — a query/doc footgun.** `AlertType.DEVICE_OFFLINE.value == 'device_offline'`, so a query/doc using a different case **silently returns nothing** — this is what made A1 look like a bug. *Action:* dashboards/docs always use the enum `.value`; add a one-line note where ad-hoc SQL is encouraged (done in the test doc's Part 9).

> **Scope note:** this is a *prioritized* audit of the highest-risk paths + every issue surfaced in testing — not a
> proof of correctness. Part B's observability upgrade is what makes the *remaining* unknowns self-surfacing going
> forward (that's the point of it).

---

# PART B — Observability & telemetry, "next level"

**Your vision:** *"As soon as a reading is sent, I can visually see & verify what happened at each stage — the raw
values, which events occurred, everything — and the system itself points out issues like wrong crop-age or
duplicate advisories."*

**What exists (foundation — we extend, not replace):** `pipeline_trace` (per ingest msg: raw↔calibrated + stage
checklist), `plot_run_trace` (per daily run), the diagnostics battery (freshness + invariants + deps), the
`job_run` ledger, and dashboards 14–20. **Gaps:** no single per-reading *journey* (ingest→rules→events→advisory),
no unified *event timeline*, no per-advisory trace, and anomaly detection is still thin.

Five additive, flag-gated phases:

### R3.1 — Reading Journey (the centerpiece)
Extend the ingest trace to capture, per reading: the **7 device-rule evaluations** (rule id, input value, verdict,
cooldown-suppressed, resulting `alert_id`) and the **`agro_events` NOTIFY** emitted. New dashboard page **"Reading
Journey"**: pick the latest (or any) reading → a single timeline showing **raw payload → calibration (raw↔units) →
validations → persistence → each rule's evaluation → events fired → alerts created**. This is the "see everything
that happened to this reading" view. (Flag extends `PIPELINE_TRACE_ENABLED`; best-effort hooks in the broker's rule
step.)

### R3.2 — Unified Event Timeline
A single chronological **"Event Timeline"** page that merges ingest traces, device/KB alerts, advisories
composed/delivered, `job_run` ticks, diagnostics results, and state transitions — filterable by plot / type / time,
each row drilling into its source record. "See every event in one place." Backed by a thin additive `event_log`
(or a union view over existing tables — chosen in design to avoid write overhead on hot paths).

### R3.3 — Advisory Journey (the Round-2 deferral, now done)
Per advisory: triggering alert/rule → `compose_advisory` (model, tokens, latency, log-only?) → disclaimer appended
→ `advisory_audit` row → delivery attempt → WhatsApp status/webhook. New **"Advisory Journey"** page. Uses the
existing durable rows (`ai_suggestions`, `advisory_audit`, `notification_dispatch_log`) + a light best-effort trace
to stitch them.

### R3.4 — Anomaly engine + "Anomalies" dashboard (the "system points out issues itself" ask)
Promote diagnostics into a richer anomaly detector run per-reading and nightly, each a typed finding with the
offending ids:
- **crop_age drift** (recomputed vs used), **duplicate advisories** (have), **advisory-volume spike/drop**,
- **value out-of-range / stuck sensor** (same value N readings), **calibration drift** (raw↔unit ratio moved),
- **rule-fire-rate anomaly** (a rule that always/never fires), **data-gap** (reading cadence broken — would have
  flagged the 18-Oct outage immediately), **forecast/satellite staleness** (have, extended).
Surfaced on a dedicated **"Anomalies"** page + rolled into Daily Health. This is where "wrong crop-age / multiple
advisories" get caught automatically.

### R3.5 — Notable-events & error stream in the dashboard (stretch)
A lightweight `app_event` table capturing notable structured events (errors, warnings, state changes) so the raw
event stream is **queryable in the dashboard**, not only in `docker logs` — a "Recent Errors/Warnings" page sourced
from `job_run` + `app_event`. (Full log-to-DB shipping stays out of scope; BetterStack/Sentry are the heavy path.)

**Design guards for all five:** best-effort writes wrapped so they never affect ingest/daily/advisory; bounded by
the existing retention worker; per-reading tracing is trivial at pilot volume but designed to sample at scale; the
device-rule hook lives in infra (broker) to keep the domain pure.

---

# PART C — Checklist / test-doc tightening

Enhance `SYSTEM_TEST_AND_RATIONALE.md`:
- **Fix the wrong commands (A9)** and mark which dev scripts are/aren't in the prod image (A5).
- **Add per-stage expected-value tables** (ranges: soil % 0–100, battery pack range, flow ≥ 0, RSSI sanity, LST
  plausibility) and **negative tests** (bad calibration, duplicate `(node_id, recorded_at)`, missing polygon,
  log-only compose, Dev-mode WhatsApp).
- **Add a "device offline / no-readings" triage section** (the exact ladder we just ran: freshness → heartbeat
  parity → Mosquitto conns → Caddy TLS → cert → last RSSI/battery → SIM/field).
- **Tie each stage to its Reading-Journey / Anomaly surface** (R3.1/R3.4) so "verify visually" becomes one click.
- Add the **minute-detail checks**: idempotency, cooldown, precedence, disclaimer presence, tz-correctness of the
  daily run-day, partition window, retention purge.

---

# PART D — Rollout (how we execute without affecting the system)

Order (each its own small PR off `main`, gates green, flag-gated, DB-gated tests in CI):
1. **Doc first (zero risk):** Part C checklist tightening.
2. **P0/P1 bug fixes:** A1 watchdog (+regression test) → A2 qa_digest → A3 forecast detail+retry → A4 log-locals.
3. **Observability R3.1 (Reading Journey)** → R3.4 (Anomalies) → R3.2 (Event Timeline) → R3.3 (Advisory Journey) →
   R3.5 (event stream). Each flag-gated and independently shippable.
4. Deploy to the box per the runbook (`git pull` → build/pull → `up -d app` → `alembic upgrade head`), verify with
   `make diagnose` + the new pages, no hot-path change at any step.

We confirm "no system impact" at each step: additive migrations only, flags default-safe, `pytest`+CI green,
and a `make diagnose` before/after on the box.

---

# PART E — Consolidated backlog (Task 2): findings + pending/on-hold

Everything open, in one place, to tackle one by one. Status: 🔴 not started · 🟡 in progress/partial · ⏸ on-hold
(external) · 🟢 done-pending-verify.

### E1. Bugs (from Part A)
| id | item | sev | status |
|---|---|---|---|
| ~~A1~~ | ~~DEVICE_OFFLINE watchdog not firing~~ — **WITHDRAWN**, watchdog works (47 alerts); my query-case error | — | ✅ not a bug |
| A1′ | alerts fire but are invisible (no delivery, no dashboard surfacing) | P1 | 🔴 (Part B / R3.2) |
| A2 | qa_weekly_digest PermissionError / ephemeral FS | P1 | 🟢 merged #117 + deployed+verified |
| A3 | weather_forecast intermittent 0-rows, no detail/retry | P1 | 🟢 merged #119 + deployed |
| A4 | failure logs dump full Settings (locals) | P1 | 🟢 merged #120 + deployed |
| A5 | dev smoke scripts not in prod image | P2 | 🟢 fixed (Dockerfile ships scripts/dev) |
| A6 | forecast_coverage can mask a dead job | P2 | 🟢 fixed (new `forecast_job_recent` check) |
| A9 | test-doc wrong commands/columns | P3 | 🟢 fixed (Part C, merged #118) |
| A10 | `except Exception` audit pass | P3 | 🟢 done — 34/35 sound; surfaced A12 |
| A11 | enum values stored lowercase — query/doc footgun | P3 | 🟢 noted at AlertType + test doc Part 9 |
| A12 | refresh_satellite swallows per-plot errors to a count (no reason) — same class as A3 | P2 | 🟢 merged #122 + deployed |

### E2. Observability upgrade (Part B)
- **R3.1 Reading Journey — 🟢 done-pending-verify.** Per-rule evaluations + emitted events now captured in the
  `pipeline_trace` `s7_rules`/`s6_persist` stages (no migration — JSONB enrichment), surfaced on the new
  **"Reading Journey"** dashboard page (22). Flag: existing `PIPELINE_TRACE_ENABLED`.
- R3.2 Event Timeline · R3.3 Advisory Journey · R3.4 Anomaly engine · R3.5 event stream — 🔴.

### E3. External / go-live (on-hold, not code)
| item | status | note |
|---|---|---|
| **WhatsApp delivery go-live** | ⏸ | Meta app → **Live** (Business Verification + privacy-policy URL — now available at viraai.in/privacy.html); then set `ADVISORY_DELIVERY_ENABLED=true`. Template `agroguardian_advisory_v2` is UTILITY. (Smoke `131009` earlier was the `XXXX` placeholder number, not a real failure.) |
| **Landsat LST download access** | ⏸ | USGS M2M account needs **download** access approved + `landsat_ot_c2_l2` terms (login works; `lst_smoke` returns "no scenes"/403). `dep_usgs_m2m` green = login only. |
| **PLOT_PILOT_002 boundary polygon** | 🔴 | no `gps_boundary_geojson` → satellite/Landsat skip it. (Pilot is single-plot 001, so low priority.) |
| **Verify Claude model id resolves on the box** | 🟢 | `dep_anthropic` green (sonnet-4-5 / haiku-4-5). |

### E4. Platform hardening / roadmap (not built)
Object storage (R2/B2) · nightly `pg_dump` backups (scaffolded, dormant) · production **Sentry** alerting
(`SENTRY_DSN` empty — wire it) + Grafana dashboards · Tailscale for private `/metrics` · a real domain for the API/
MQTT edge (sslip.io today) · **farmer app** (unblocks ~76 dormant KB fields) · **OTA** firmware · modem TLS
`authmode 0→2` + secret rotation · LoRa 433 MHz regulatory clearance for scale-up.

### E5. Field / device (from the 18-Oct outage)
Main Node 4G link failing on **−111 dBm** — check antenna/signal, SIM data plan, power-cycle; SD outbox replays on
reconnect. (Device-side; not backend.)

---

*Next: on your go-ahead I'll execute Part D in order — Part C doc first (zero risk), then the P0/P1 fixes, then the
observability phases — each as its own PR, nothing touched until reviewed.*
