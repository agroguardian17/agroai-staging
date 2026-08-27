# AgroGuardian V2 backend

The active backend is a Python 3.12 FastAPI hexagonal monolith for precision-agriculture telemetry, authentication, plot reads, and pilot alerts. It runs with PostgreSQL/PostGIS, Mosquitto, and ChromaDB; the optional Streamlit dashboard lives under `dashboard/`. Two rule engines coexist: the crop-agnostic device-health engine (7 pilot rules, per-message) and the ginger-specific agronomic engine (431 rules, daily batch — see `ginger/`).

## Read the documentation

**New to the project? Read this first:** [Project overview](docs/PROJECT_OVERVIEW.md) — a single doc that explains use case, problem, actors, hardware, full data flow, architecture, every folder, database, rules, notifications, auth, deployment, config, testing, what's live vs scaffolded, roadmap, glossary, and a command cheat sheet.

Then the reference-density docs:

- [Codebase guide](docs/CODEBASE_GUIDE.md) — architecture, runtime flows, database, rules, dashboard, deployment, tests, and known gaps.
- [API reference](docs/API_REFERENCE.md) — endpoints, payloads, authentication, errors, and examples.
- [Development and operations](docs/DEVELOPMENT.md) — local setup, migrations, pilot seed, MQTT smoke tests, dashboard, and deployment checks.
- [Hardware wire contract](docs/HARDWARE_WIRE_CONTRACT.md) — Main Node MQTT topic and telemetry payload contract, plus the Sub Node → Main Node LoRa CSV format.
- [Sub Node firmware change notes](docs/SUB_NODE_FIRMWARE_CHANGES.md) — the three edits applied to the teammate's ATmega328P sketch (now shipped in `firmware/sub_node/`).
- [Ginger Engine integration (Round G)](docs/GINGER_ENGINE_CHANGES.md) — what changed to add the 431-rule daily ginger advisory engine alongside the pilot rules.
- [Schema decisions](docs/SCHEMA_DECISIONS.md) — database reconciliation and multi-tenancy decisions.
- [Configuration](docs/CONFIGURATION.md) — every supported environment variable, Compose override, secret, and deployment setting.
- [File reference](docs/FILE_REFERENCE.md) — file-by-file map of the application, migrations, dashboard, deployment, scripts, tests, ginger engine, and firmware.
- [Accounts checklist](ACCOUNTS_TO_FILL.md) — external accounts and secrets needed for later deployment phases.

## Repository layout

```text
app/
  domain/          Pure entities, enums, validation, metrics, and rules
  application/     Use cases and Protocol ports (adds build_farm_brain)
  infra/           HTTP, MQTT, Postgres, JWT, WhatsApp, LLM, event adapters
                   (adds ginger/pg_state_store)
  jobs/            Long-lived work: MQTT ingest broker + ginger daily scheduler
  lib/             Logging, metrics, and time helpers
  config.py        Typed environment configuration
  main.py          FastAPI factory and lifespan (spawns ingest + ginger scheduler)
ginger/            Teammate's ginger advisory engine (7 files) + compiled KB SQL
alembic/           Database migrations, through revision 0011
dashboard/         Streamlit operations dashboard
deploy/            Caddy (custom build), Mosquitto, Prometheus, staging, Coolify
docs/              Overview, codebase guide, API, config, dev, hardware, schema,
                   ginger integration, sub-node firmware notes
rules/             Reserved rule assets; active pilot rules are Python definitions
scripts/dev/       Pilot seed, MQTT credential, ingest diagnostics, helpers
tests/             Domain, application, HTTP, MQTT, persistence, adapter, ginger

../firmware/       Hardware firmware living in a sibling directory:
  main_node/       ESP32-WROOM-32 PlatformIO project (LoRa RX → MQTTS bridge)
  sub_node/        ATmega328P Arduino sketch (sensors → LoRa TX)
```

## Quick start with Docker

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD, AUTH_JWT_SECRET, and MQTT_BROKER_PASSWORD.
docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml exec app alembic upgrade head
curl http://localhost:8000/api/v1/health
```

Development endpoints:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/api/v1/docs`
- Postgres: `localhost:5433`
- Mosquitto: `localhost:1883` and `localhost:8883`
- ChromaDB: `localhost:8001`

## Quality checks

```bash
pytest -q
pytest -q --cov=app --cov-fail-under=80
ruff check .
ruff format --check .
mypy app/
```

The current implementation stores valid MQTT readings (with `water_flow_lpm` and `water_pressure_bar` accepted), evaluates the seven pilot device-health rules per message unless `CALIBRATION_MODE=true`, runs the ginger agronomic engine as a daily batch at 06:30 IST for every active ginger `crop_season`, and exposes the results through authenticated plot and alert endpoints (including `/plots/{id}/ginger_advisories`). Weather/heartbeat MQTT kinds, outbound alert dispatch, automatic Claude advisory generation on device-health alerts, the dashboard login screen, and several provider integrations are intentionally future-phase work; see the [codebase guide](docs/CODEBASE_GUIDE.md#current-limitations-and-security-debt).

Proprietary — all rights reserved.
