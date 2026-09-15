# AUDIT/03 — Findings Report (Executive)

**Date:** 2026-09-15 · Full detail in [AUDIT/02-findings.md](02-findings.md); transfer in [00](00-transfer.md); drift in [01](01-drift-map.md).

---

## 1. Executive summary

The **tracked codebase is healthy and in a clean three-way sync** (local == GitHub `f46a8a0` == live VPS `agri-AI-live`). Migrations apply cleanly to a fresh DB and reverse; the firmware↔backend wire contract matches field-for-field; domain/application purity holds; calibration, clock-skew, idempotency, validation gates, and Decimal/tz discipline are all correct. **The risk is entirely operational and documentary**, not in the core code.

**Totals:** 1 blocker · 2 high · 11 medium · 11 low · 3 info · 10 doc-vs-doc conflicts · 7 transfer items (from 00).

### Top 5 most urgent
1. **F-012 🔴 — Secrets committed to a PUBLIC repo** (mosquitto `passwd`/`acl`, firmware MQTT password). Live credential exposure.
2. **F-013 🟠 — No DB backups on staging.** One volume failure = total data loss.
3. **F-014 🟠 — CI is dead** (workflow nested below repo root → never runs) and would mask migration failures (`alembic … || true`); no branch protection. Zero automated quality gate.
4. **F-008 🟡 — RLS gap:** `device_calibration` + `main_node_readings` (post-0008 tables) have no row-level security. (Mitigated: RLS is dormant defence-in-depth today.)
5. **F-011 🟡 — `/ready` is a fake stub** + app container has no healthcheck → false-green ops signals.

### Top 5 quick wins (trivial, high signal)
1. **F-004** — naive `datetime.utcnow()` → `datetime.now(UTC)` in `pg_state_store.py` (1 line).
2. **F-001** — `time_source` → `Literal["ntp","rtc","none"]` in the wire schema.
3. **T-004 / T-005** — `git rm --cached firmware/.DS_Store` + add a root `.gitignore`.
4. **F-023 / F-024 / F-028** — skill text fixes (pgvector absent; clock-skew constants live in `broker.py`; staging runs the full stack).
5. **F-025 + F-005** — align `.cursorrules #21` text to reality; the hardcoded model resolves inside the agreed Round 13 wiring.

---

## 2. Findings, sorted (blocker → info)

| ID | Sev | Cat | One-line | Migration? |
|---|---|---|---|---|
| F-012 | 🔴 | G | Committed secrets in PUBLIC repo | no |
| F-013 | 🟠 | G | No DB backups on staging | no |
| F-014 | 🟠 | G | CI never runs + `\|\| true` + no branch protection | no |
| F-003 | 🟡 | B | `main_node_id` vs `master_node_id` naming split | yes (rename) |
| F-004 | 🟡 | C | Naive `utcnow()` in pg_state_store | no |
| F-005 | 🟡 | C | Hardcoded model in compose_advisory | no |
| F-007 | 🟡 | E | Materialized views never refreshed | no |
| F-008 | 🟡 | E | RLS not applied to device_calibration + main_node_readings | yes (0015) |
| F-011 | 🟡 | F | `/ready` stub + no app healthcheck | no |
| F-015 | 🟡 | G | No healthchecks/limits; 1.9 GB/0 swap host | no |
| F-016 | 🟡 | G | Mutable `:latest` image, unverifiable provenance | no |
| F-017 | 🟡 | G | Orphan `dc49b05` checkout on VPS | no |
| F-020 | 🟡 | I | 5 reference docs frozen at ~0009/Round G | no |
| F-021 | 🟡 | I | PROJECT_OVERVIEW §5–6 wrong (binary LoRa / BSNL) | no |
| F-001 | ⚪ | A | `time_source` not enum-validated | no |
| F-006 | ⚪ | D | No LLM retry today (→ Round 13) | no |
| F-009 | ⚪ | E | 103 FKs lack explicit `ON DELETE` | maybe |
| F-010 | ⚪ | E | No ORM models for active otp_challenges/auth_sessions | no |
| F-018 | ⚪ | H | Migration round-trip test skipped by default | no |
| F-022 | ⚪ | I | OTP-hash docs wrong (it's salted SHA-256) | no |
| F-023 | ⚪ | I | Skill claims pgvector (absent by design) | no |
| F-024 | ⚪ | I | Skill says clock-skew in Settings (it's broker consts) | no |
| F-025 | ⚪ | I | `.cursorrules #21` ModelRole unimplemented | no |
| F-026 | ⚪ | I | HARDWARE_WIRE_CONTRACT §4.3 old CSV | no |
| F-027 | ⚪ | I | Docs reference nonexistent eeprom_provisioner | no |
| F-002 | ℹ️ | A | Firmware version string still 1.0.0-raw | no |
| F-019 | ℹ️ | H | Coverage gate unenforced (CI dead) | no |
| F-028 | ℹ️ | I | Skill §17/§20 deployment state (mandated fix) | no |

Transfer items (from 00): T-001 untracked skill/roadmap/migration-guide · T-002 untracked new-docs · T-003 stray CRM file · T-004 committed `firmware/.DS_Store` · T-005 no root `.gitignore` · T-006 python3.12 gotcha · T-007 Docker not running (resolved — started).

---

## 3. Doc-vs-doc reconciliation proposals  ⚠️ **need your approval before Phase 5 edits any doc**

| # | Conflict | Proposed winner |
|---|---|---|
| J-1 | Migration head (≤0009/0011 vs 0013) | **0013** (code) |
| J-2 | Table count (58 vs 35 vs 60) | **60 logical** (verified) |
| J-3 | LoRa binary vs CSV | **CSV** (code) |
| J-4 | APN BSNL vs Airtel | **Airtel airtelgprs.com** (firmware) |
| J-5 | Test count (~470 vs 596) | **596** (measured) |
| J-6 | OTP hash (bcrypt vs Argon2id vs SHA-256) | **salted SHA-256** (code) |
| J-7 | Deployment (local-only vs full-stack staging) | **full stack on staging** |
| J-8 | Pilot scale (4 plots/2 SN vs 2/1) | **2 plots / 1 Sub Node** (seed) |
| J-9 | Model id (sonnet-4-6 vs 4-5) | **claude-sonnet-4-5** (config) |
| J-10 | Firmware version (v2.1 vs 1.0.0-raw) | both true → doc note |

**One ruling covers all ten** if you agree with "code/config/measurement wins" — reply "approve J-1..J-10 as proposed" (or amend any).

---

## 4. False positives considered and dismissed
- *"Round 17.5 `main_nodes` routes have no tests"* — false: `test_main_nodes.py` exists (just missing from FILE_REFERENCE).
- *"60-table claim is wrong (118 tables)"* — false: 60 logical is correct; partitions (39 leaves) + views (19) inflate raw counts.
- *"pgvector missing = broken deploy"* — false: absent by design (0003 best-effort; RAG uses ChromaDB).
- *"`dc49b05` = live deploy drift"* — false: dormant orphan; the live tree is `f46a8a0`, clean.
- *"RLS barely applied (1 ENABLE statement)"* — false: applied to 29 tables via a loop.
- *"`.env` drift"* — false: local `.env` has full key parity with `.env.example`.
- *"`except Exception` in `domain/rules.py:193` swallows errors"* — false: returns a `None` fallback in a pure helper, not silent control-flow suppression.
- *"Decimal→float in repos violates the no-float rule"* — false: it's the DB-boundary conversion to `double precision` columns; domain/application stay Decimal.

---

## 5. Explicitly NOT changing (and why)
- **Firmware (v2.1 FINAL, frozen):** every firmware-touching finding (F-001, F-002, F-026, F-027) resolves as a **backend or doc** fix. No `.ino`/`.cpp`/`.h` edits proposed. (The committed firmware MQTT password in F-012 is neutralised by rotating the broker credential + making the repo private, **not** by editing the frozen firmware — flagged for your call in Batch A.)
- **`ginger/` (upstream-owned):** no defects found; `pg_state_store.py` (F-004) is our adapter, not `ginger/`.
- **The roadmap (`AgroGuardian_FINAL_Roadmap.md`):** aspirational reference; not reconciled to current state unless you want it (its "4 plots / migrations ≤0009 / single VPS" are known-aspirational).
- **F-009 (FK `ON DELETE`)** and **F-003 (`main_node_id` rename):** surfaced, but each needs a design ruling / is a cross-cutting migration — proposed as deferred batches, not auto-applied.
- **Decimal→float persistence conversions:** intended; columns are `double precision`.

---

## 6. Pointer
Fix plan with batches, dependencies, rollback, and approval checkboxes: **[AUDIT/04-plan.md](04-plan.md)**.
