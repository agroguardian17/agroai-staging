# AUDIT/04 — Fix Plan (batched)

**Date:** 2026-09-15 · Each batch = one PR (branch off latest `main`, ≤ ~400 LOC of code; doc batches may exceed in prose). Ordered by risk/urgency then dependency. **Nothing executes until you tick a batch's approval box.** `0014` is reserved for Round 13, so any *schema* migration here is **0015** and is sequenced **after** Round 13 to keep the Alembic chain linear (0013 → 0014 R13 → 0015). Pre-Round-13 batches are migration-free by design.

**Legend:** each batch lists Findings · Files · Migration · Tests · Doc/skill edits · Blast radius · Rollback · Approval.

---

## Batch A — Secret-exposure remediation  🔴 (do first)
- **Findings:** F-012 (+ T-004 partial).
- **What:** (1) **[you]** make `agroai-staging` **private** in GitHub settings; (2) **[you]** rotate the MQTT device credential on the VPS via the documented `DEVELOPMENT.md` procedure (new `openssl rand`, regenerate `deploy/mosquitto/passwd`, restart mosquitto) — this makes the committed password inert; (3) `git rm --cached deploy/mosquitto/passwd deploy/mosquitto/acl` + ignore them; (4) **[you, explicit]** history scrub (git-filter-repo/BFG) to purge the secret from past commits, then **force-push** (the one action needing your explicit go-ahead).
- **Files:** `deploy/mosquitto/passwd`, `deploy/mosquitto/acl` (untrack), `.gitignore`.
- **Migration:** no.
- **Tests:** n/a (ops).
- **Doc/skill:** note the rotation in `DEVELOPMENT.md`; update skill §24 blocker status.
- **Blast radius:** repo history rewrite (coordinate — everyone re-clones); broker restart (brief MQTT blip; no boards flashed yet so no field impact).
- **Rollback:** history rewrite is irreversible by design; keep a pre-rewrite backup clone. Broker cred rotation is forward-only.
- **⚠️ Firmware note:** the password also sits in the frozen `pilot_config.h`. Rotating the broker cred neutralises the exposure **without editing firmware**; the new password is set at flash time (SETUP §5). I will **not** edit firmware unless you explicitly direct it.
- **Approval:** `[ ] Approved by user`  (and separately: `[ ] Approved: history rewrite + force-push`)

## Batch B — Repo hygiene  ⚪
- **Findings:** T-004, T-005, T-001, T-002, T-003.
- **What:** add root `.gitignore` (`.DS_Store`, `Claude outputs/`, `.venv/`, `__pycache__/`, `*.pyc`, `.env`); `git rm --cached firmware/.DS_Store`; **[your calls]** T-001 commit `SKILL_agroguardian.md` + `MIGRATION_GUIDE.md` (recommend yes); T-002 commit `new-docs/` as tracked read-only reference (recommend yes) *or* add to `.gitignore`; T-003 you move `Claude outputs/Freelance_Web_CRM.xlsx` out of the repo dir.
- **Files:** `/.gitignore` (new), untrack `firmware/.DS_Store`, (optionally add skill/migration-guide/new-docs).
- **Migration:** no. **Tests:** n/a.
- **Blast radius:** trivial; no code paths touch these.
- **Rollback:** `git revert` the commit.
- **Approval:** `[ ] Approved by user`  · your calls: `[ ] commit skill+migration-guide` `[ ] new-docs: commit / ignore (circle one)` `[ ] I'll remove the CRM file`

## Batch C — Code correctness quick fixes  🟡/⚪
- **Findings:** F-004, F-001, F-010.
- **What:** F-004 `pg_state_store.py:155` `utcnow()` → `now(UTC)`; F-001 `time_source` → `Literal["ntp","rtc","none"]` (+ None) in `schemas.py` `MasterReadings`/`MasterReadingsHeartbeat`; F-010 add ORM models for `otp_challenges` + `auth_sessions` (parity only — no migration).
- **Files:** `app/infra/ginger/pg_state_store.py`, `app/infra/mqtt/schemas.py`, `app/infra/persistence/models/core.py` (or new `auth.py` model module).
- **Migration:** no (F-010 models mirror existing 0009 tables).
- **Tests:** update `test_pg_state_store`; add a `test_schemas` case for bad `time_source` rejected; `test_models` picks up the two new models. Run purity (infra — unaffected) + full suite.
- **Doc/skill:** none.
- **Blast radius:** small, infra-only; wire schema tightens (firmware only ever sends the 3 valid values, so no field impact).
- **Rollback:** `git revert`.
- **Approval:** `[ ] Approved by user`

## Batch D — Real ops signals: matview refresh + `/ready`  🟡
- **Findings:** F-007, F-011.
- **What:** F-007 add an APScheduler interval job that `REFRESH MATERIALIZED VIEW CONCURRENTLY` the 4 views (`node_readings_hourly/daily`, `weather_hourly/daily`) on a sane cadence (e.g. hourly); F-011 implement real `/ready` probes (`SELECT 1`, MQTT connect check, chroma heartbeat) + add a Docker healthcheck to the `app` service.
- **Files:** `app/infra/http/health.py`, a new `app/jobs/refresh_views.py` (+ wire into `ginger_scheduler`/lifespan), `docker-compose.prod.yml` (+`.dev`).
- **Migration:** no. **Tests:** `test_health` real-probe cases (mocked deps); job unit test.
- **Blast radius:** medium — `/ready` behaviour changes (now can report not-ready); new background job. Verify it doesn't false-negative on healthy stacks.
- **Rollback:** `git revert`; matviews simply go stale again.
- **Approval:** `[ ] Approved by user`

## Batch E — CI resurrection  🟠
- **Findings:** F-014, F-016, F-018, F-019.
- **What:** move `agro_backend/.github/` → repo-root `.github/` (set `working-directory: agro_backend` / paths); drop `|| true` on `alembic upgrade head`; add a job running the destructive migration round-trip (`AGRO_RUN_DESTRUCTIVE=1`); make `build-multiarch` **push** an immutable SHA-tagged image on tag builds to the correct GHCR namespace (F-016); **[you]** enable branch protection on `main` with required checks.
- **Files:** move + edit `.github/workflows/ci.yml`.
- **Migration:** no. **Tests:** CI itself is the test; verify a PR triggers it.
- **Blast radius:** low locally; first real CI run may surface latent lint/type/coverage failures (that's the point).
- **Rollback:** revert the move.
- **Approval:** `[ ] Approved by user`  · `[ ] enable branch protection`

## Batch F — Backups + prod-compose hardening  🟠 (deploy-gated, Phase 6 execution)
- **Findings:** F-013, F-015.
- **What:** nightly `pg_dump` → R2/B2 with a systemd timer + a documented restore drill (F-013); add healthchecks to `app`/`mosquitto`/`caddy`, restart backoff, `mem_limit`/`cpus`, and add swap on the host (F-015).
- **Files:** new `deploy/backup/` script + systemd unit + timer; `docker-compose.prod.yml`.
- **Migration:** no. **Tests:** restore-from-dump drill on a throwaway DB.
- **Prereq (you):** R2 or B2 bucket + credentials.
- **Blast radius:** VPS changes — executed under Phase 6 with per-step approval, not from this batch's merge.
- **Rollback:** disable timer; revert compose.
- **Approval:** `[ ] Approved by user`

## Batch G — Documentation reconciliation  🟡 (gated on your J-1..J-10 ruling)
- **Findings:** F-020, F-021, F-022, F-023, F-024, F-025, F-026, F-027, F-028, F-002, J-1..J-10.
- **What:** refresh the 5 stale reference docs to Round 17.5 state; fix `PROJECT_OVERVIEW §5–6` (CSV, Airtel, NPK live); fix `HARDWARE_WIRE_CONTRACT §4.3` CSV; correct OTP-hash wording; skill §7/§17 (pgvector), §18 (clock-skew consts), §17/§20 (deployment + staging box name); `.cursorrules #21` ModelRole text; remove `eeprom_provisioner` references; apply the J-1..J-10 winners.
- **Files:** `docs/{FILE_REFERENCE,CODEBASE_GUIDE,API_REFERENCE,PROJECT_OVERVIEW,DEVELOPMENT,HARDWARE_WIRE_CONTRACT}.md`, `SKILL_agroguardian.md`, `.cursorrules`, `SUB_NODE_FIRMWARE_CHANGES.md`.
- **Migration:** no. **Tests:** n/a (prose). **Blast radius:** docs only.
- **Rollback:** `git revert`.
- **Approval:** `[ ] Approved by user`  · `[ ] approve J-1..J-10 as proposed (or amend)`

## Batch H — Schema hardening  🟡 (**post-Round-13**, migration 0015)
- **Findings:** F-008 (+ F-009 if you rule on a policy).
- **What:** migration **0015** (down_revision `0014`) enrolling `device_calibration` + `main_node_readings` in RLS (mirroring 0008 group semantics); optionally set explicit `ON DELETE` policies (F-009) once you decide cascade intent.
- **Files:** `alembic/versions/0015_*.py`; tests in `test_schema_db`.
- **Migration:** **yes (0015)** — sequenced after Round 13's 0014.
- **Blast radius:** additive RLS; reversible downgrade. **Rollback:** `alembic downgrade 0014`.
- **Approval:** `[ ] Approved by user`  (defer until Round 13 merged)

## Batch I — `main_node_id` naming unification  🟡 (**post-Round-13**, optional, migration)
- **Findings:** F-003.
- **What:** rename `weather_station_readings.master_node_id` → `main_node_id` (migration) + domain/repo/API/doc updates, OR formally document the split and close as won't-fix.
- **Blast radius:** cross-cutting (column + `WeatherStationReading` + repo + `main_nodes` API `WeatherRow` + docs). Higher risk → its own batch.
- **Approval:** `[ ] Approved by user`  ·  `[ ] rename` / `[ ] document-and-close`

## Phase 6 (separate) — Staging cleanup
- **F-017** remove orphan `/home/ubuntu/agro_backend@dc49b05` (read-only confirm it's unreferenced first). Handled under the Phase-6 staging plan with per-step approval, not a code PR.

---

## Recommended order
A (security) → B (hygiene) → C (quick correctness) → E (CI, so later batches get gated) → D (ops signals) → G (docs, after J ruling) → F (backups/compose, Phase-6 exec) → **Round 13** → H (schema RLS 0015) → I (rename) → Phase 6 cleanup.

## Not scheduled (need a decision first)
- **F-009** FK `ON DELETE` policy — needs your cascade-intent ruling before it can be a migration.
- **F-006** LLM retry — delivered *by* Round 13, not a separate batch.
- **F-005** hardcoded model — delivered *by* Round 13 wiring (skill/rules text is fixed in Batch G).

---

# Resolution status — as of 2026-09-15 (end of engagement)

Legend: ✅ shipped & merged · 🔵 PR open (awaiting your merge) · 🟣 done on VPS · ⏸️ deferred to you.

## Shipped (merged to `main`)
| PR | Batch | Findings | Notes |
|---|---|---|---|
| ✅ #1 | B — repo hygiene | T-003/T-004/T-005, F-001(.DS_Store) | root `.gitignore`; untracked `firmware/.DS_Store` |
| ✅ #2 | C — correctness | F-004, F-001, F-010 | tz-aware ginger ts; `time_source` Literal; OtpChallenge + AuthSession ORM models |
| ✅ #3 | E — CI resurrection | F-014 | workflow moved to repo root; `|| true` removed on migrations |
| ✅ #4 | D — ops signals | F-007, F-011 | matview refresh job; real `/ready` probes + app healthcheck |
| ✅ #5 | E2 — CI disk | F-014 (follow-up) | free ~20 GB runner disk before install |
| ✅ #6 | Round 13 | F-005, F-006 | advisory subscriber; migration 0014; delivers the model-id de-hardcode + LLM retry |
| ✅ #7 | CI tuning | — | skip arm64 multi-arch on PRs (~1h → ~15m) |

## Open PRs (awaiting your merge)
| PR | Batch | Findings | Notes |
|---|---|---|---|
| 🔵 #8 | G — docs | F-002, F-020..F-028, J-1..J-10 | reconcile stale docs to code; applies the J-winners |
| 🔵 #9 | — | F-029, F-003, F-009, F-018, F-019 | reversible 0008 downgrade + re-enable CI round-trip; SCHEMA_DECISIONS §14 documents F-003/F-009 (document-and-close) |
| 🔵 #10 | B (calls) | T-001, T-002 | track SKILL, MIGRATION_GUIDE, roadmap, new-docs |
| 🔵 #11 | H — schema | F-008 | migration **0015**: RLS on `device_calibration` (staff-only) + `main_node_readings` (farm-owned) |
| 🔵 #12 | F — deploy | F-015, F-016 | compose healthchecks + resource caps; GHCR namespace fix + immutable-tag CI push |

## Done on the VPS (staging)
- 🟣 **F-017** — the stale pre-transfer checkout (git `dc49b05`, 21 dirty files, HTTPS remote) was **moved aside**, not deleted: `/home/ubuntu/agro_backend` → `/home/ubuntu/agro_backend.ORPHAN-dc49b05-moved-20260915` with a `DO_NOT_USE_README.txt`. Verified first that no systemd unit, cron, Coolify (none installed), or live process references it. All 7 containers kept running (app + postgres healthy). Canonical deploy dir is `/home/ubuntu/agri-AI-live/agro_backend` (tracks `main`, SSH remote). Undo: `mv` it back.
  - *Observed during F-017:* the `agro-prod` compose project is currently **split** across two dirs — `postgres`/`chroma`/`grafana` containers were created from the old dir and were not recreated during the Round 13 deploy, so `docker compose ls` lists both config files. Harmless (named volumes hold the data), but a redeploy of the full stack from `agri-AI-live` would converge it. Left for your call — not touched.

## Deferred to you (need your action or a resource)
- ⏸️ **F-012 / Batch A** — repo was made **private** (Phase 1 ✅). Still yours: rotate the committed MQTT device credential on the VPS (per `DEVELOPMENT.md`), and the optional git-history scrub + force-push. Not performed here (secret rotation and history rewrite are explicitly out of scope without your typed go-ahead).
- ⏸️ **F-013 / Batch F backups** — nightly `pg_dump` → R2/B2 + restore drill. Needs a bucket + credentials from you before it can be wired.
- ⏸️ **Batch I / F-003 rename** — resolved as **document-and-close** (§14). The physical `master_node_id` → `main_node_id` rename remains optional/future.
- ⏸️ **Branch protection** on `main` (required checks) — a GitHub settings change only you can make.

## CI note
Merge order matters for CI green: **#9 before #11/#12** is not required (independent), but #9 re-enables the destructive migration round-trip which, once merged, will exercise the full `0008…0015` chain — so land #11 (0015) and #9 (0008 fix) and the round-trip covers 0015 automatically.
