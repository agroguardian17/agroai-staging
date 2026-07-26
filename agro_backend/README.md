# AgroGuardian V2 backend

The active backend is a Python 3.12 FastAPI hexagonal monolith for precision-agriculture telemetry, authentication, plot reads, and pilot alerts. It runs with PostgreSQL/PostGIS, Mosquitto, and ChromaDB; the optional Streamlit dashboard lives under `dashboard/`.

## Read the documentation

- [Codebase guide](docs/CODEBASE_GUIDE.md) — architecture, runtime flows, database, rules, dashboard, deployment, tests, and known gaps.
- [API reference](docs/API_REFERENCE.md) — endpoints, payloads, authentication, errors, and examples.
- [Development and operations](docs/DEVELOPMENT.md) — local setup, migrations, pilot seed, MQTT smoke tests, dashboard, and deployment checks.
- [Hardware wire contract](docs/HARDWARE_WIRE_CONTRACT.md) — Main Node MQTT topic and telemetry payload contract.
- [Schema decisions](docs/SCHEMA_DECISIONS.md) — database reconciliation and multi-tenancy decisions.
- [Accounts checklist](ACCOUNTS_TO_FILL.md) — external accounts and secrets needed for later deployment phases.

## Repository layout

```text
app/
  domain/          Pure entities, enums, validation, metrics, and rules
  application/     Use cases and Protocol ports
  infra/           HTTP, MQTT, Postgres, JWT, WhatsApp, LLM, and event adapters
  jobs/            Startup wiring for long-lived ingest work
  lib/             Logging, metrics, and time helpers
  config.py        Typed environment configuration
  main.py          FastAPI factory and lifespan
alembic/           Database migrations, currently through revision 0009
dashboard/         Streamlit operations dashboard
deploy/            Caddy, Mosquitto, Prometheus, staging, and Coolify files
docs/              Architecture, API, development, hardware, and schema docs
rules/             Reserved rule assets; active pilot rules are Python definitions
scripts/dev/       Pilot seed, MQTT credential, ingest diagnostics, and helpers
tests/             Domain, application, HTTP, MQTT, persistence, and adapter tests
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

The current implementation stores valid MQTT readings, evaluates the pilot rules unless `CALIBRATION_MODE=true`, and exposes the results through authenticated plot and alert endpoints. Weather/heartbeat MQTT kinds, outbound alert dispatch, the dashboard login screen, and several provider integrations are intentionally future-phase work; see the [codebase guide](docs/CODEBASE_GUIDE.md#13-known-gaps-and-maintenance-notes).

Proprietary — all rights reserved.
