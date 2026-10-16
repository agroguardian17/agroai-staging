# Debugging & Observability Hardening — Plan

**Status:** executed in **2 rounds** — **Round 1 BUILT** (PR #114), **Round 2 BUILT** (branch `feat/debug-hardening-round2`, stacked on Round 1).
**Author:** engineering
**Date:** 2026-10-15
**Scope:** server-side only (`agro_backend/`). Firmware is out of scope; this starts where data arrives on the server.
**Ground truth:** the code in `agro_backend/`. Where this plan and code disagree, code wins.

## Execution — 2 rounds (condensed from the 5 phases below)

- **Round 1 — Detection core (BUILT):** the job-run ledger + `instrument_job` on all 9 cron schedulers + job metrics (Phase 1); the diagnostics battery with **freshness + invariant** checks, the `diagnostics_result` table and the nightly `diagnostics_scheduler` (Phases 2–3, DB-only so it runs in CI); the **Scheduler Health** and **System Diagnostics** dashboard pages. Migrations **0068** (`job_run`) + **0069** (`diagnostics_result`); retention wired. Flags `JOB_RUN_LEDGER_ENABLED`, `DIAGNOSTICS_ENABLED` (default on). All additive, best-effort, behaviour-preserving.
- **Round 2 — Tooling, external deps & coverage (BUILT):** external **dependency self-tests** (`app/infra/diagnostics/dependency_checks.py` — CDSE token, USGS M2M login, Meta Graph reachability, Anthropic config) added to the nightly battery; the **`make diagnose`** / `python -m app.ops.diagnose` one-command red/green report (freshness + invariants + deps + pipeline self-test, non-zero exit on fail); the SELECT-vs-`_row_to_view` guard **generalised to every `Pg*Repo`** (`tests/infra/persistence/test_pg_repo_select_cols.py`); the pipeline self-test added to CI as a gate (`make selftest`); a unified **Daily Health** dashboard pane (`20_Daily_Health.py`).

**Advisory-path trace — deliberate non-goal (documented):** the compose/deliver `LISTEN/NOTIFY` path already persists its state durably (`ai_suggestions`, append-only `advisory_audit`, `notification_dispatch_log`/`dlq`, delivery_status) plus the `advisory_composed_total` / `advisory_delivered_total` metrics — richer than the ingest/daily paths had before trace. A dedicated per-advisory trace table would be redundant for the pilot, so Round 2 covers that path's *health* via the Anthropic + Meta dependency checks and the advisory freshness/counters instead. Revisit if a concrete debugging gap appears.

The per-phase detail below is retained as the design reference; the two rounds are just how it ships.

---

## 1. Why this exists

Even after the system was built and deployed, real issues kept surfacing **late and by accident** —
usually during a manual dashboard review, sometimes weeks after the fact. A representative list from
the last two months:

| Issue | How it was found | Root failure mode |
|---|---|---|
| `k_source` outage (daily pipeline silently dead ~2.5 weeks) | noticed `satellite_data` hadn't updated | silent exception, no alert, no freshness check |
| Landsat/LST returning 403 | all `lst_c` values were `None` on the dashboard | external dependency down, no self-test |
| `crop_age_days` frozen at 50 | spotted a stale number by eye | wrong-value bug, no invariant check |
| Duplicate daily advisories | counted rows manually | missing invariant/constraint, found late |
| Monthly partition exhaustion (latent) | code review | no forward-looking data check |
| Sub-node silence (no alert existed) | review | missing watchdog (since fixed, #113) |

**The common root cause:** *failures and bad data do not announce themselves.* The platform is very
good at **inspection once you already suspect something** (the Pipeline Inspector, #107–#110) but has
almost no **proactive detection** and **no one-command diagnosis**. This plan closes that gap.

**Decision (2026-10-15):** surfacing is **dashboards + metrics only** for now — no push alerts
(no Sentry paging, no email/WhatsApp digest) until we choose to turn one on. Everything below is
designed so a push channel can be added later as a thin layer on top, without rework.

---

## 2. What already exists (we build on this, not rebuild)

| Capability | Where | Notes |
|---|---|---|
| Structured logging **with tracebacks** | `app/lib/logging.py` | `dict_tracebacks` before `JSONRenderer` (the post-`k_source` fix). |
| Prometheus registry + `/metrics` | `app/lib/metrics.py`, `app/main.py` | Good HTTP/ingest/LLM/ginger/advisory counters. **No scheduler-run metrics yet.** |
| Liveness + readiness | `app/infra/http/health.py` | `/health` (process up) + `/ready` (Postgres/MQTT/Chroma reachable). **No per-job health.** |
| Sentry | `app/main.py` `_init_sentry`, `app/config.py` | Wired, but **only `FastApi/Starlette/Asyncio` integrations** and DSN-gated. No `LoggingIntegration`, and scheduler exceptions are caught — so **job failures never reach Sentry**. (Left off per the dashboards-only decision; revisit later.) |
| Pipeline trace (ingest) | `pipeline_trace` table (migration 0064), `build_pipeline_trace`, Pipeline Inspector + Stage Health pages | Raw↔calibrated per message. |
| Daily-run trace | `plot_run_trace` table (0065), `build_plot_run_trace`, Daily Run Inspector | Farm-brain coverage, rules fired, advisories. |
| Pipeline self-test | `app/infra/pipeline_selftest.py`, `17_Pipeline_Self_Test` | Golden payloads through the real validators. |
| SELECT-vs-mapper guard | `tests/infra/persistence/test_pg_crop_season_repo_select.py` | **Only covers one repo** (the one that broke). |

All trace/self-test work is already flag-gated (`PIPELINE_TRACE_ENABLED`), best-effort, and retention-bounded.
This plan follows the same charter.

---

## 3. Gaps (verified against current code)

1. **Scheduler/job failures are a dead end.** Every tick does `log.exception("…tick_failed")` inside
   its own `except` (e.g. `app/jobs/satellite_scheduler.py:91`). The error is *logged only* — not
   persisted, not metered, and **not sent to Sentry** (caught + no `LoggingIntegration`). A failing
   nightly job is invisible unless someone greps logs. **This is the `k_source` failure mode.**
2. **No data-freshness / staleness detection** — nothing notices when a table stops getting fresh rows.
3. **No external-dependency self-test** (CDSE / USGS / Anthropic / Meta) — the Landsat-403 class is
   only found by accident.
4. **No invariant / reconciliation checks** — crop-age drift, duplicate advisories, partition-window
   exhaustion would each be caught by a cheap assertion, but none exist.
5. **Trace coverage stops at ingest + daily-run** — the advisory compose/deliver `LISTEN/NOTIFY` path
   is untraced.
6. **The SELECT-vs-`_row_to_view` guard covers only one repo**, not all `Pg*Repo`.
7. **No single "is everything OK?" pane** and **no one-command local/box diagnosis**.

---

## 4. Design charter (non-negotiable)

So this strengthens debugging **without affecting the running system**, every item obeys:

- **Additive only** — new tables, new jobs, new dashboard pages, new tests. No schema changes to hot tables, no behavior change to ingest/daily/advisory paths.
- **Flag-gated** — each capability behind an env flag; default on only where cost is zero.
- **Best-effort** — every diagnostic write is wrapped so a failure in the diagnostic can **never** break a job or a hot path (the pipeline-trace rule).
- **Bounded** — new tables get retention via the existing nightly retention worker.
- **Purity-safe** — pure checks live in `app/domain`/`app/application`; infra calls (DB, providers) stay in `app/infra`. No new framework imports in domain/application.
- **Shipped as a stack** of small PRs merged in order, each lint + type + test green; migrations additive; flags enabled in staging first.

---

## 5. The phases

### Phase 1 — Job-run ledger + Scheduler Health *(highest ROI: makes silent job failures visible)*

**Deliverables**
- Migration: table `job_run` — `id, job_name, started_at, finished_at, status (ok|failed|skipped), summary JSONB, error_type, error_message, trace_id, created_at`.
- `JobRunRepo` port + `PgJobRunRepo` (best-effort writes).
- `instrument_job(job_name, repo)` async context manager used by **every** scheduler tick: records
  start/end/status + a small summary dict, and on exception records `error_type/error_message` (then
  re-raises or swallows exactly as today — no behavior change).
- New metrics in `app/lib/metrics.py`: `agro_job_runs_total{job,status}` (Counter) and
  `agro_job_last_success_timestamp{job}` (Gauge).
- Dashboard page **"Scheduler Health"**: per job — last run, status, age-since-last-success, and a red
  flag when age exceeds that job's expected interval.
- Flag `JOB_RUN_LEDGER_ENABLED` (default on). Retention wired into `retention_scheduler`.

**Why first:** this alone turns the `k_source` class from "invisible for weeks" into "red on the
dashboard the next morning," with zero changes to what the jobs actually do.

### Phase 2 — Freshness + dependency self-tests *(catch stale data & dead integrations)*

**Deliverables**
- `app/application/diagnostics/` — **pure** freshness checks returning structured results
  (`check_id, ok, observed, expected, detail`): `node_sensor_readings` max-age; `weather_forecasts`
  and `ai_suggestions` present for today (given an active season); `satellite_data` within the revisit
  window; partition window covers today + N months.
- `app/infra/diagnostics/` — dependency self-tests reusing existing providers: CDSE token, USGS M2M
  download, Anthropic model-resolves, Meta WhatsApp reachability — each returns `ok/fail + real error`.
- Migration: table `diagnostics_result` (one row per check per run). `DiagnosticsRepo` + Pg impl.
- `diagnostics_scheduler` (nightly, after the daily jobs) runs the whole battery → `diagnostics_result`
  + the Phase-1 metrics pattern. Flag `DIAGNOSTICS_ENABLED`.
- Extends the #110 self-test philosophy from ingest to the whole system.

### Phase 3 — Invariant / reconciliation checks *(catch wrong-value bugs)*

**Deliverables** — assertions for the exact classes already hit, run inside the Phase-2 battery, each
failure a finding carrying the offending IDs:
- `crop_age` recomputed from `sowing_date` == value used in today's advisory.
- ≤ 1 ginger advisory per `(plot, day, rule_id)`.
- No advisory row without its disclaimer + `advisory_audit` record.
- Partition catch-all / forward window present.
- Every active plot has the geometry/polygon its enabled features expect.

### Phase 4 — One-command diagnosis + CI guard *(track & fix fast, anywhere)*

**Deliverables**
- `python -m app.ops.diagnose` + `make diagnose`: runs freshness + invariants + dependency self-tests
  + pipeline self-test, prints a **red/green report**, exits non-zero on any failure. Runnable locally,
  on the box, and in CI.
- **Generalize** the SELECT-vs-`_row_to_view` guard to **every** `Pg*Repo` (one parametrized static
  test) so the `k_source` class can never ship again.
- CI: add the pipeline self-test + the generalized repo guard to `.github/workflows/ci.yml`.

### Phase 5 — Close trace coverage + single "Daily Health" pane

**Deliverables**
- Add best-effort trace to the advisory compose/deliver `LISTEN/NOTIFY` path (the one untraced stage),
  mirroring `build_plot_run_trace`.
- Dashboard page **"Daily Health"**: one pane uniting the job-run ledger, freshness, dependency
  self-tests, invariant findings, and validation-failure counts — the single "is everything OK today?"
  view.
- *(Deferred, per the dashboards-only decision)* an optional daily ops digest (email / WhatsApp-to-ops)
  that fires only on red — a thin layer over the Phase-2/3 results when we decide to turn it on.

---

## 6. New surfaces summary

**Tables (all additive, retention-bounded):** `job_run`, `diagnostics_result`.
**Metrics:** `agro_job_runs_total{job,status}`, `agro_job_last_success_timestamp{job}`, and per-check
gauges from the diagnostics battery.
**Dashboard pages:** "Scheduler Health" (P1), "Daily Health" (P5).
**CLI:** `python -m app.ops.diagnose` / `make diagnose` (P4).
**Flags:** `JOB_RUN_LEDGER_ENABLED`, `DIAGNOSTICS_ENABLED` (default on; zero cost when idle).

## 7. Rollout

Stacked PRs **1 → 5**, merged in order; each lint/type/test-green; DB-gated tests on the dev stack;
migrations additive; flags enabled in **staging first**, then prod. No hot-path or domain-purity changes
at any step.

## 8. What this buys you

- Job failures go **red on a dashboard the next morning** (ledger + metrics) instead of silent for weeks.
- Stale data and dead integrations are **detected automatically** (freshness + dependency self-tests).
- Wrong-value regressions are **caught by invariants + a CI guard** before they reach prod.
- **One command** (`make diagnose`) to triage locally, on the box, or in CI.

## 9. Open questions for review

1. Expected-interval thresholds per job for the Scheduler Health red flag (e.g. ginger daily → 26h,
   satellite → 10 days to allow revisit cadence). Draft table to be filled in Phase 1.
2. Retention window for `job_run` / `diagnostics_result` (default to `PIPELINE_TRACE_RETENTION_DAYS` = 30?).
3. Confirm "dashboards + metrics only" stays for the whole stack, with the push digest kept as a
   deferred Phase-5 option.

---

*Decisions log: 2026-10-15 — surfacing is dashboards + metrics only (no push alerts); plan to be
reviewed as a repo doc before implementation.*
