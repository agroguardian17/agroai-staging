# Development and operations guide

All commands in this document are run from `agro_backend/` unless stated otherwise.

## Prerequisites

- Python 3.12.x
- Docker and Docker Compose v2 for the local infrastructure stack
- Git
- `make` is optional; use the direct commands if it is unavailable

## First-time local setup

1. Create the local environment file:

   ```bash
   cp .env.example .env
   ```

2. Set at least these values before starting Docker:

   ```dotenv
   POSTGRES_PASSWORD=<strong-local-password>
   AUTH_JWT_SECRET=<strong-local-secret>
   MQTT_BROKER_PASSWORD=<strong-local-password>
   ```

   Keep `APP_ENV=development`. The defaults in `app/config.py` are intended for unit tests and local-only work, not deployment.

3. Start the local stack:

   ```bash
   docker compose -f docker-compose.dev.yml up -d --build
   ```

4. Apply migrations:

   ```bash
   docker compose -f docker-compose.dev.yml exec app alembic upgrade head
   ```

5. Verify the app:

   ```bash
   curl http://localhost:8000/api/v1/health
   open http://localhost:8000/api/v1/docs  # macOS; use a browser on other systems
   ```

The development stack maps Postgres to `localhost:5433`, Mosquitto to `localhost:1883`/`8883`, ChromaDB to `localhost:8001`, and FastAPI to `localhost:8000`.

## Local Python environment

For tests and static checks without starting Docker:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install -e '.[dev]'
```

The repository's development dependencies include pytest, coverage, testcontainers for Postgres integration tests, Ruff, mypy, respx, and Hypothesis.

## Quality commands

```bash
pytest -q
pytest -q --cov=app --cov-report=term-missing --cov-fail-under=80
ruff check .
ruff format --check .
mypy app/
```

Equivalent Make targets are `test`, `test-cov`, `lint`, `format`, and `typecheck`.

## Database workflow

```bash
alembic upgrade head
alembic downgrade -1
alembic revision -m "describe the schema change"
```

`DATABASE_URL` is the async application DSN. `DATABASE_URL_SYNC` is used by Alembic. The migration history currently ends at `0009_auth_otp_tables`.

Do not edit an already-applied migration. When adding a field or changing an enum, update the domain/wire model, SQLAlchemy model, a new Alembic migration, relevant tests, and any wire/schema documentation in the same change.

## Pilot seed and MQTT smoke test

Seed the deterministic pilot entities after migrations:

```bash
PILOT_PHONE=+918123456789 python scripts/dev/seed_pilot.py
```

The script creates the pilot tenant/farmer/farm, Main Node, two Sub Nodes, four plots, and active crop seasons. It prints the IDs used in the MQTT topic.

The authoritative payload examples are in [`HARDWARE_WIRE_CONTRACT.md`](HARDWARE_WIRE_CONTRACT.md). For a local broker, publish to the topic shown there using port 1883 and the Mosquitto credentials configured for the development stack.

For a compact ingest diagnostic stream:

```bash
docker compose -f docker-compose.dev.yml logs -f app \
  | python scripts/dev/tail_ingest.py
```

Use `CALIBRATION_MODE=true` while sensor calibration is in progress. Readings are saved, but no rules or alerts are created.

## Dashboard development

Use a separate environment for Streamlit:

```bash
python3.12 -m venv .venv-dashboard
source .venv-dashboard/bin/activate
python -m pip install -r dashboard/requirements.txt
export AGRO_API_BASE_URL=http://localhost:8000
export ACCESS_TOKEN=<short-lived-access-token>
streamlit run dashboard/app.py
```

The dashboard currently expects a static access token. Mint it through the OTP API, then restart Streamlit after changing `ACCESS_TOKEN`.

## MQTT credentials and hardware

`scripts/dev/provision_mqtt_credential.sh` provisions a Mosquitto user from the local credential file. The Main Node is the MQTT client in aggregate mode; Sub Nodes send data to the Main Node over the field link and do not authenticate directly to Mosquitto.

Before firmware integration, reconcile the payload enum values with `app/domain/sensor.py` and `app/infra/mqtt/schemas.py`. The backend currently accepts:

- transmission: `esp_now`, `lora`, `rs485`, `wifi`;
- cadence: `normal`, `rapid`, `low_power`, `storm`, `maintenance`.

## Deployment checklist

For staging, read [`../deploy/staging/README.md`](../deploy/staging/README.md). For the full production path, read [`../deploy/coolify/README.md`](../deploy/coolify/README.md).

At minimum, production needs:

- non-default Postgres, JWT, MQTT, and Anthropic secrets;
- `APP_ENV=production` and correct database DSNs;
- TLS configuration for MQTT and Caddy;
- a rendered production Caddyfile;
- the Caddy Layer-4 build for raw MQTT/TCP;
- migrations applied before seeding or serving farmer traffic;
- backup and restore procedures before real farmer data is accepted;
- monitoring access restricted to the intended private network.

Never place credentials in the repository or paste them into issue comments/logs.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| App does not start | `.env`, required secrets, Docker service health, `docker compose logs app` |
| `/ready` says healthy but a dependency fails | The endpoint is currently a phase-0 stub; inspect each container directly |
| No MQTT readings | Broker host/port/TLS credentials, topic shape, `ingest_broker.subscribed`, queue/drop metrics |
| Payload is silently absent | `tail_ingest.py`; unknown fields, naive timestamps, wrong enums, or invalid `$schema` are rejected |
| Repeated QoS-1 packet creates no new alert | Expected if `(node_id, recorded_at)` already exists; duplicates skip rule evaluation |
| Dashboard shows 401 | Access token expired; mint a new token or use the refresh endpoint |
| Dashboard is empty | Confirm pilot rows exist, the token's farmer/tenant owns the seeded data, and the API base URL is correct |
| Production docs are unavailable | Expected: production FastAPI/Caddy intentionally hides `/docs`, `/redoc`, and OpenAPI |
