# AUDIT/00 — Machine-Transfer Reconciliation

**Date:** 2026-09-15
**Scope:** Local working copy at `~/Documents/agri-AI` after transfer from a previous laptop.
**Method:** Read-only git + filesystem inspection. Nothing modified.
**Repo:** git root `/Users/priyanshu/Documents/agri-AI`; remote `origin = https://github.com/agroguardian17/agroai-staging.git`.

---

## 0. Headline

The git tree is **clean and in sync with GitHub** — `HEAD == origin/main == f46a8a0`, 0 ahead / 0 behind, no stashes, single branch, no divergence. There is **no classic transfer detritus** (no `.bak`/`.old`/`_copy`/`* 2.*`/`Untitled`/AppleDouble files, no symlinks, no CRLF/mixed line endings, correct exec bits, no foreign absolute paths or old-machine identity strings in tracked source, no leaked IDE configs). `.env` has **full key parity** with `.env.example`.

The real transfer issue is **scope of what git tracks**: GitHub contains only `agro_backend/` (249 files) + `firmware/` (9) + `README.md` (1) = 259. The project's own **source-of-truth documents and the ginger upstream bundle are untracked and exist only on this laptop**. Plus a handful of small hygiene items.

---

## Findings

### T-001 — Source-of-truth docs are untracked / not on GitHub  ·  severity: medium  ·  **NEEDS YOUR CALL**
`SKILL_agroguardian.md`, `AgroGuardian_FINAL_Roadmap.md`, and `MIGRATION_GUIDE.md` sit at the repo root as **untracked** (`git status` = `??`). They are not in `origin/main`. The skill is the declared single source of truth; losing it (or letting it drift from GitHub) is exactly the failure mode this audit exists to prevent.
- **Classification:** real files, currently laptop-only.
- **Recommendation:** commit `SKILL_agroguardian.md` and `MIGRATION_GUIDE.md` to the repo (they *are* project artifacts). `AgroGuardian_FINAL_Roadmap.md` (184 KB, aspirational) — commit as reference or keep out; your call.
- **Blast radius:** additive commit only. No code impact.

### T-002 — `new-docs/` ginger upstream bundle untracked (3.1 MB, ~34 files)  ·  severity: medium  ·  **NEEDS YOUR CALL**
`new-docs/AgroGuardian_Ginger_Engine_v1.0_9931/**` (the upstream JSON knowledge base + engine sources + the teammate's tests + `agroguardian_ginger_kb.sql`) is entirely untracked. `GINGER_ENGINE_CHANGES.md §14` explicitly says this bundle is meant to stay as "archived reference." It is the provenance for the vendored `agro_backend/ginger/` package.
- **Classification:** real upstream reference, `ginger/`-adjacent → **read-only, do not edit** per your rules.
- **Recommendation:** decide one of: (a) commit as tracked reference, (b) add to a root `.gitignore` as intentionally-local reference, or (c) leave untracked. I lean (a) so the KB provenance is versioned alongside the vendored copy.
- **Blast radius:** additive; no code impact.

### T-003 — Unrelated personal file inside the repo working dir  ·  severity: low  ·  **NEEDS YOUR CALL**
`Claude outputs/Freelance_Web_CRM.xlsx` (124 KB) is untracked and unrelated to AgroGuardian — looks like leftover from another task on this machine.
- **Classification:** foreign/leftover, not a project file.
- **Recommendation:** move it out of the repo directory (or delete). I will not touch it without your say-so.

### T-004 — `firmware/.DS_Store` is committed to git  ·  severity: low
`firmware/.DS_Store` is **tracked** (added in `f46a8a0`, the "Prepare clean backend and firmware for deployment" commit) and therefore lives on GitHub. macOS junk in version control.
- **Recommendation:** `git rm --cached firmware/.DS_Store` in the hygiene batch (Phase 4/5), plus T-005.
- **Blast radius:** one file untracked; nothing imports it.

### T-005 — No root-level `.gitignore`  ·  severity: low
The only `.gitignore` is `agro_backend/.gitignore`, which (correctly) ignores `.DS_Store`, `.env`, `.venv/`, `__pycache__/`, caches, `node_modules/` — **but only within `agro_backend/`**. At the repo root there is no ignore file, so root `./.DS_Store`, `Claude outputs/`, and any future root junk are neither ignored nor caught. (`./.DS_Store` currently shows as untracked; `agro_backend/.DS_Store` is correctly ignored by the subtree file.)
- **Recommendation:** add a root `.gitignore` (`.DS_Store`, `Claude outputs/`, `*.pyc`, `__pycache__/`, `.venv/`, `.env`) in the hygiene batch.

### T-006 — Default `python3` is 3.14.5, incompatible with `requires-python >=3.12,<3.13`  ·  severity: low (gotcha, not blocking)
`python3` on this machine is **3.14.5**; `agro_backend/pyproject.toml:10` pins `>=3.12,<3.13`. A bare `pip install -e '.[dev]'` under `python3` would fail. **Mitigation already present:** `agro_backend/.venv` is **Python 3.12.13** with `alembic`, `pytest`, `ruff`, `mypy` all installed, and `python3.12` (Homebrew, 3.12.13) is on PATH.
- **Recommendation:** always drive the project via `agro_backend/.venv/bin/*` (or `python3.12`); never the bare `python3`. Worth a one-line note in `DEVELOPMENT.md`. No code change.

### T-007 — Docker Desktop not running locally  ·  severity: info (environmental)
`docker` CLI present but the daemon socket is down (`/Users/priyanshu/.docker/run/docker.sock` absent). The local dev stack (Postgres/Mosquitto/Chroma via `docker-compose.dev.yml`) is therefore **not up**, so Phase-1 "does `alembic upgrade head` succeed against a fresh local Postgres" and DB-integration tests cannot run until Docker Desktop is started. Not a defect — noting for Phase 1 (needs you to start Docker, or we rely on the staging DB read-only + non-DB tests).

---

## Clean / no action (verified)

| Check | Result |
|---|---|
| Local vs GitHub sync | `HEAD == origin/main == f46a8a0`, 0 ahead / 0 behind |
| Stashes | none |
| Branches | only `main` (tracks `origin/main`); no orphan tracking branches |
| `.bak`/`.old`/`_copy`/`* 2.*`/`Untitled`/`._*`/`Icon` detritus | none |
| Symlinks | none |
| CRLF / mixed line endings on tracked `.sh`/`.py` | none |
| Exec bits on tracked `.sh` | correct (`100755` on both scripts) |
| Foreign absolute paths (`/Users/`, `/home/`, `C:\`, `~/Desktop`) in tracked source | none |
| Old-machine identity (hostname/user/email) in tracked code | none |
| IDE/editor configs (`.vscode`/`.cursor`/`.idea`/`.editorconfig`) | none tracked or present |
| `.env` vs `.env.example` key parity | full parity — 0 missing, 0 extra (values not inspected) |
| `.venv` tooling | Python 3.12.13 + alembic/pytest/ruff/mypy present |

**Note (info):** git commit identity for this repo is `Priyanshu <priyanshunikam171@gmail.com>` (distinct from the session's `hello@gasview.in`). Not a defect — just the identity future commits will carry.

---

## Items that become Phase-4 batches
- **Hygiene batch:** T-004 (`git rm --cached firmware/.DS_Store`) + T-005 (root `.gitignore`). Trivial, low-risk.
- **Doc-tracking batch:** T-001 / T-002 once you rule on what to commit.
- **T-003 / T-006 / T-007:** your actions or one-line doc notes; not code batches.
