# AUDIT/01 — Three-Source Drift Map

**Date:** 2026-09-15 · **Method:** read-only (local git/`.venv`, `gh`, `ssh agro-vps`). No writes to GitHub or VPS. One local-only action: a throwaway `agri_migtest` DB created + dropped for the migration drill.

**Sources:** **A** = local `~/Documents/agri-AI`; **B** = GitHub `agroguardian17/agroai-staging`; **C** = staging VPS `agro-staging-01` (13.207.20.67), live compose dir `/home/ubuntu/agri-AI-live/agro_backend`.

---

## 0. Headline — the tracked code is a clean three-way match

`HEAD` (local) == `origin/main` (GitHub) == live VPS checkout `/home/ubuntu/agri-AI-live` = **`f46a8a0`**, all three clean (0 dirty on the live tree). All six deploy configs are **byte-identical** local↔VPS. Staging DB is at Alembic **0013** (= local head). A **fresh-DB `alembic upgrade head` applied 0001→0013 cleanly and `0013↔0012` is reversible.** The drift is entirely at the *edges* — repo visibility/secrets, CI, extensions, `.env` completeness, backups, host size, and one dormant orphan tree.

---

## 1. Drift table  (`what | local | github | vps | severity`)

| What | Local (A) | GitHub (B) | VPS (C) | Sev |
|---|---|---|---|---|
| Tracked code HEAD | `f46a8a0` clean | `f46a8a0` | `f46a8a0` clean (agri-AI-live) | ✅ OK |
| Alembic head / applied | `0013` (head) | `0013` in tree | `0013` **current** (gate passed) | ✅ OK |
| Fresh-DB migrate + reverse | pass 0001→0013, 0013↔0012 OK | (CI would run — but CI dead) | n/a | ✅ OK |
| 6 deploy config files | sha set X | in tree | **identical sha** | ✅ OK |
| Logical table count | — | — | **60** (57 plain + 3 partition parents; 96 `r` incl 39 leaves; 118 info_schema incl 19 views) | ✅ reconciled |
| **Repo visibility** | — | **PUBLIC** | — | 🔴 BLOCKER |
| **Committed secrets** (`deploy/mosquitto/passwd`+`acl`, `pilot_config.h` MQTT pw) | tracked | **tracked in PUBLIC repo** | present | 🔴 BLOCKER |
| **CI execution** | workflow at `agro_backend/.github/` (wrong level) | **0 workflows registered, 0 runs** | — | 🔴 HIGH |
| CI migration gate | — | test job: `alembic upgrade head \|\| true` masks failure | — | 🟠 MED |
| Branch protection on `main` | — | **none** | — | 🟠 MED |
| **DB backups / cron / systemd** | — | — | **none** (only `docker.service`; no pg_dump, no timer) | 🔴 HIGH |
| **pgvector extension** | migration 0003 "best-effort"; skill claims present | claims present | **ABSENT** (postgis/pgcrypto/uuid-ossp/fuzzystrmatch/tiger/topology only) | 🟠 MED |
| Staging `.env` completeness | `.env` 85-key parity w/ example | example (85 keys) | **18 keys only** — no `ANTHROPIC_API_KEY`, no `META_WHATSAPP_*`, `SENTRY_DSN`, `R2/B2`, `GINGER_JOB_*`, `OTP_*`, JWT ttls, `CORS/TRUSTED_HOSTS` | 🟠 MED (blocks Round 13/14 LLM+WhatsApp on staging) |
| Orphan VPS checkout | — | — | `/home/ubuntu/agro_backend` @ **`dc49b05`** ("ai integration"/"transfer round 10"), pre-transfer lineage, **not** containing `f46a8a0`, dormant (not the live dir) | 🟠 MED |
| Running app image | — | CI builds with `push:false` | `ghcr.io/**agroguardian**/agro-backend:**latest**` (mutable tag; GHCR org ≠ repo owner `agroguardian17`; provenance unverified) | 🟠 MED |
| Host RAM / swap | — | — | **1.9 GiB, 0 swap** (SETUP rec 2–4 GB); 889 MiB avail | 🟠 MED |
| TLS cert (edge :8883) | — | — | LE, `mqtts-13-207-20-67.sslip.io`, expires **2026-11-24** (~70 d; Caddy auto-renews) | ✅ OK |
| Staging telemetry | — | — | `node_sensor_readings` 21 rows (→2026-09-09), `main_node_readings` 10 (→2026-08-30) — test data, **not empty** as SETUP implies | ℹ️ INFO |
| `kb_rules` | — | — | **431** | ✅ OK |
| `device_calibration` seed | — | — | 1 row (AGR-SN-0001) | ✅ OK |
| Test collection | **596 across 51 files** | — | — | ℹ️ (skill/docs say ~470 — Phase 2/I) |
| Sibling repo | — | `agroguardian17/agroguardian` **PRIVATE**, pushed 2026-05-29 (likely original monorepo) | — | ℹ️ INFO |

---

## 2. Source detail

### A — Local
- `alembic heads` = `0013 (head)`; history intact `<base>→0001→…→0013`.
- `pytest --collect-only` = 596 tests / 51 files (via `.venv` 3.12.13).
- Docker up (29.5.2). Fresh-DB drill on throwaway `agri_migtest`: full `0001→0013` apply clean; `current`=0013; `downgrade -1`→0012 then `upgrade`→0013 clean. **Migration chain is healthy and reversible.**

### B — GitHub (`agroguardian17/agroai-staging`)
- **PUBLIC**, description empty, default branch `main`, latest `f46a8a0` (2026-09-09), diskUsage 1.2 MB.
- **0 PRs, 0 issues, 0 tags/releases, 0 workflow runs, 0 registered workflows, no branch protection.** CI is inert here (the workflow file lives one directory too deep at `agro_backend/.github/`).
- Sibling: `agroguardian17/agroguardian` (PRIVATE, 2026-05-29).

### C — Staging VPS (`agro-staging-01`, read-only)
- Ubuntu/AWS, up 40 d, disk 38 % (37 G free), **RAM 1.9 GiB / swap 0**.
- 7 containers healthy; images: caddy `agro-caddy-l4:staging` (local build), app `ghcr.io/agroguardian/agro-backend:latest` (healthy), postgres `postgis/postgis:15-3.4` (healthy), mosquitto `2.0.18`, chroma `0.5.20`, prometheus `v2.55.1`, grafana `11.3.0`.
- **Live compose dir `/home/ubuntu/agri-AI-live` @ `f46a8a0`, 0 dirty** — matches GitHub/local exactly. (`agro_backend` under it is a subdir, not a separate repo — correct.)
- **Orphan `/home/ubuntu/agro_backend` @ `dc49b05`** — old lineage, dormant; risk is only that someone runs compose from the wrong dir. Recommend removal (Phase 6, with your OK).
- DB: `alembic current`=0013; extensions lack **pgvector**; `kb_rules`=431; `device_calibration`=1; test telemetry present.
- `prometheus.yml` has `rule_files: /etc/prometheus/alerts.yml` wired; alerts.yml sha matches repo.
- **No cron, no backup/systemd timers.** Cert valid to 2026-11-24.
- `.env` = 18 keys, `APP_ENV`=staging (value redacted); missing keys fall back to code defaults, but **`ANTHROPIC_API_KEY` is absent** → any real LLM advisory (Round 13) on staging would fall back to the log-only chat model until the key is added.

---

## 3. Correction to the initial C1 read
The first VPS pass flagged apparent "deploy drift" (`dc49b05`, 21 dirty, `agro_backend not a git checkout`). C2 resolved it: the **live** tree is `agri-AI-live @ f46a8a0` (clean, in sync); `dc49b05` is a **separate dormant orphan checkout**, and the "not a git checkout" was just because the repo root is one level up. **No live deploy drift on tracked code.**

---

## 4. Feeds into
- **Blockers → Phase 3 report top:** public repo + committed secrets (combined), no backups.
- **HIGH → fix batches:** CI relocation + `|| true` removal; secret removal/rotation + history scrub.
- **MED:** pgvector decision, staging `.env` completion (esp. `ANTHROPIC_API_KEY` for Round 13), orphan-checkout removal, image-tag pinning, RAM/swap, branch protection.
- **Doc-drift (Phase 2/I):** "60 tables" is right (document the partition arithmetic); "~470 tests" → 596; "pgvector present" → absent; "staging empty" → has test data.
