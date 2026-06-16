# AgroGuardian V2 — Backend

> **Status**: Phase 0 (Bootstrap) complete. Following the [Fast Path](../AgroGuardian_FINAL_Roadmap.md#06--fast-path-to-working-prototype-2-week-mvp-track) toward a 2-week working prototype.

A FastAPI hexagonal monolith for precision agriculture. One Aurangabad farm, four plots, one Main Node, two Sub Nodes — designed to scale to thousands of farms without a rewrite.

## What's in this directory

```
agro_backend/
├── app/                    # FastAPI app — hexagonal layout (domain / application / infra)
│   ├── domain/             # Pure dataclasses + functions. ZERO framework imports.
│   ├── application/        # Use cases + Protocol ports. Calls infra via ports only.
│   ├── infra/              # Adapters: HTTP, MQTT, Postgres, Anthropic, satellite, ...
│   ├── jobs/               # APScheduler cron jobs
│   ├── lib/                # Cross-cutting helpers (logging, metrics, time, jwt, otp)
│   ├── config.py           # pydantic-settings — single source of truth
│   ├── deps.py             # FastAPI dependencies
│   └── main.py             # App factory + lifespan
├── alembic/                # Database migrations (Phase 1 fills versions/)
├── deploy/                 # Caddy / Mosquitto / Prometheus / Coolify config
├── firmware/               # ESP32 + ATmega328P PlatformIO projects (Phase 8)
├── rules/                  # Crop + universal rule JSON (Phase 4 indexes into ChromaDB)
├── scripts/                # Dev tooling (fake_main_node, render-caddyfile, ...)
├── tests/                  # pytest suite (unit + integration + e2e)
├── docker-compose.dev.yml  # Local stack: postgres + mosquitto + chroma + app
├── docker-compose.prod.yml # Lightsail/Coolify production stack
├── Dockerfile              # Multi-stage, multi-arch (amd64 + arm64)
├── pyproject.toml          # Python 3.12 deps + ruff + mypy + pytest config
├── alembic.ini             # Migration config
├── Makefile                # Common dev tasks
├── .env.example            # Every env var documented (NO real secrets)
├── .cursorrules            # 28 rules — Cursor enforcement
└── ACCOUNTS_TO_FILL.md     # What you need to sign up for, in order
```

## Prerequisites

- **Python 3.12.x** (you have `3.12.10` ✓)
- **Docker Desktop for Windows** — install from <https://www.docker.com/products/docker-desktop/>. Required for running Postgres/Mosquitto/ChromaDB locally.
- **Git** (already have it).
- (Optional) `make` via `choco install make` or use the PowerShell scripts directly.

## First run (~10 minutes after Docker is installed)

1. **Fill in your accounts/secrets** — see [ACCOUNTS_TO_FILL.md](ACCOUNTS_TO_FILL.md). For the very first local run you can leave most fields blank; only `POSTGRES_PASSWORD`, `AUTH_JWT_SECRET`, and `MQTT_BROKER_PASSWORD` need values to start the stack.

2. **Copy `.env.example` to `.env`**:

   ```powershell
   cd agro_backend
   Copy-Item .env.example .env
   ```

3. **Generate three random secrets** in PowerShell:

   ```powershell
   # Generate 32-byte random base64 strings (one for each)
   1..3 | ForEach-Object {
       $b = New-Object byte[] 32
       [System.Security.Cryptography.RandomNumberGenerator]::Fill($b)
       [Convert]::ToBase64String($b)
   }
   ```

   Paste the three outputs into `.env` for `POSTGRES_PASSWORD`, `AUTH_JWT_SECRET`, `MQTT_BROKER_PASSWORD`.

4. **Bring up the stack**:

   ```powershell
   docker compose -f docker-compose.dev.yml up -d --build
   ```

5. **Verify**:

   ```powershell
   curl http://localhost:8000/api/v1/health
   # Expected: {"status":"ok","version":"0.0.1","commit":"dev","env":"development"}
   ```

6. **Open the interactive docs**: <http://localhost:8000/api/v1/docs>

## Local Python development (without Docker)

For tight inner-loop work (running tests, lint, type-checks) you don't need Docker:

```powershell
cd agro_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q
ruff check .
mypy app/
```

(Tests will skip Postgres/MQTT integration cases when no containers are running. Phase 0 unit tests don't need them.)

## Common tasks

| Task | Command |
|------|---------|
| Bring up the dev stack | `docker compose -f docker-compose.dev.yml up -d` |
| Tail app logs | `docker compose -f docker-compose.dev.yml logs -f app` |
| Bring it all down | `docker compose -f docker-compose.dev.yml down` |
| Run all tests | `pytest -q` |
| Run with coverage | `pytest -q --cov=app --cov-fail-under=80` |
| Lint + format check | `ruff check . && ruff format --check .` |
| Type-check | `mypy app/` |
| Format auto-fix | `ruff format . && ruff check . --fix` |
| New migration | `alembic revision -m "description"` |
| Apply migrations | `alembic upgrade head` |
| Render production Caddyfile | `pwsh ./scripts/dev/render-caddyfile.ps1 -IP 13.235.50.100` |

## Architecture

The codebase is a **hexagon** (ports & adapters):

- `app/domain/` — pure Python dataclasses + functions. Imports only stdlib + numpy + shapely. Importable from a plain Python REPL.
- `app/application/` — use cases (`generate_advisory`, `ingest_telemetry`, `send_otp`, ...) calling outbound `Protocol` ports. Never imports `infra/`.
- `app/infra/` — adapters that implement the ports (Postgres repos, Anthropic client, MQTT broker, FCM, WhatsApp, satellite clients).

**Why this matters**: swapping any external dependency (LLM vendor, SMS provider, payment processor, satellite source) is one new file. The roadmap's [Provider Portability Charter (Part 0.5)](../AgroGuardian_FINAL_Roadmap.md#05--provider-portability-charter-v12--aws-edition) is what lets us migrate off AWS Lightsail in 2 hours if pricing or quotas ever change.

## Roadmap snapshot

| Phase | What | Status |
|------:|------|--------|
| 0 | Bootstrap + cloud infra | ✅ done |
| 1 | DB schema + RLS + audit log (35 tables, 4 mat. views) | next |
| 2 | MQTT ingest + 4-gate validation + idempotent UPSERT | |
| 3 | REST API + WhatsApp-OTP auth | |
| 4 | Derived metrics + hot rules + crop stages | |
| 5 | AI / RAG / agent loop (Sonnet 4.6 + Haiku 4.5) | |
| 6 | Copernicus + NASA Earthdata + Open-Meteo + IMD | |
| 7 | FCM + WhatsApp dispatch | |
| 8 | Firmware + OTA (parallel) | |
| 9 | Expo farmer app | |
| 10 | Streamlit founder dashboard | |
| 11 | Quota scaffolding | |
| 12 | Ops + calibration + backups | |
| 13 (post) | MSG91 SMS adapter | |
| 14 (post) | Razorpay subscriptions | |

Fast Path inside this: Phase 0 + Phase 1 (Days 1–3) → Phase 2 (Days 4–6) → Phase 3 (Days 7–8) → Phase 5 slimmed (Days 9–11) → Phase 10 slimmed (Days 12–14). Real hardware, Expo app, satellite, T3 chat, T4 reflection, OTA, full quota all defer to Weeks 3–12.

## Pilot infra cost

~$28/month. AWS Lightsail Mumbai $20 + automatic snapshots $4 + Backblaze B2 $1 + LLM $3 + free-tier monitoring. Detailed projection in [Roadmap §12.5](../AgroGuardian_FINAL_Roadmap.md#125-cost-projection-v12--aws-lightsail-pricing).

## Security posture (already enforced)

- All secrets via env, never in repo. `.env` gitignored; `SecretStr` in `Settings` redacts `repr()`.
- `_assert_production_safe()` refuses to boot in production with default secrets.
- structlog redacts `password`, `token`, `otp`, `code`, `authorization`, etc. from any event.
- Phone numbers reduced to last-4 digits in any log line (`.cursorrules` rule #24).
- `print()` is banned via `.cursorrules` rule #9.
- AWS-specific managed services are banned via `.cursorrules` rules #25–26 (provider portability).

## Where to look next

- `ACCOUNTS_TO_FILL.md` — checklist of external accounts needed to ship the prototype
- `deploy/coolify/README.md` — production deploy runbook (after Lightsail VPS is provisioned)
- `../AgroGuardian_FINAL_Roadmap.md` — the full roadmap; Part 12.2 has the verbatim Lightsail setup runbook

## License

Proprietary — all rights reserved.
