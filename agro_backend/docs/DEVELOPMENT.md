# Development and operations guide

All commands in this document are run from `agro_backend/` unless stated otherwise.
The project was copied between a Windows laptop, a Mac, and an AWS Lightsail
VPS; do not assume a command from an older bootstrap script matches the current
checkout. In particular, `make` targets only exist in `agro_backend/Makefile`.

## Prerequisites

- Python 3.12.x
- Docker and Docker Compose v2 for the local infrastructure stack
- Git
- `make` is optional; use the direct commands if it is unavailable
- PowerShell 7 or Git Bash/WSL on Windows when rendering Caddy
- `mosquitto_pub` for laptop MQTT smoke tests

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
   GRAFANA_ADMIN_PASSWORD=<strong-local-password>
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

When the app runs inside Compose, its service-to-service hosts are overridden
to `postgres`, `mosquitto`, and `chroma`. `GRAFANA_ADMIN_PASSWORD` is required
by the production Compose file even if you are only testing the app.

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

The production Dockerfile now copies the seeder into the image. If an older
running image reports that `scripts/dev/seed_pilot.py` does not exist, rebuild
and recreate the app image:

```bash
docker compose -f docker-compose.prod.yml build app
docker compose -f docker-compose.prod.yml up -d --force-recreate app
```

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

The pydantic `TelemetryIn` model also accepts `water_flow_lpm` and `water_pressure_bar` as of migration 0011 — matches the Sub Node's flow-pulse counter and analog pressure transducer.

## Firmware

The hardware firmware lives at the repository root under `../firmware/` (sibling to `agro_backend/`). Two projects:

- `firmware/main_node/` — PlatformIO C++ for the ESP32-WROOM-32. LoRa RX → CSV parse → JSON build → MQTTS publish via the SIMCom A7672S 4G modem. See `firmware/main_node/README.md`.
- `firmware/sub_node/` — Arduino IDE sketch for the ATmega328P. Sensor reads → binary/CSV LoRa TX. Two-step flash procedure (EEPROM node-ID provisioner → production sketch). See `firmware/sub_node/README.md`.

`firmware/README.md` is the tie-together doc with the first-time bring-up order (cloud → Sub Node → Main Node → verify in Postgres).

## Ginger engine (Round G)

The ginger advisory engine ships as a daily batch, spun up by `app/jobs/ginger_scheduler.py` at 06:30 IST. To force a manual run in development:

```bash
docker compose -f docker-compose.dev.yml exec app python -c "
import asyncio
from datetime import date
from app.config import get_settings
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_reading_repo import PgReadingRepo
from app.infra.persistence.pg_plot_repo import PgPlotRepo
from app.infra.persistence.pg_crop_season_repo import PgCropSeasonRepo
from app.infra.persistence.pg_ai_suggestion_repo import PgAiSuggestionRepo
from app.jobs.ginger_daily import GingerDailyDeps, run_daily

async def main():
    s = get_settings()
    sm = _ensure_engine(s)
    deps = GingerDailyDeps(
        reading_repo=PgReadingRepo(sm),
        plot_repo=PgPlotRepo(sm),
        crop_season_repo=PgCropSeasonRepo(sm),
        ai_suggestion_repo=PgAiSuggestionRepo(sm),
        sync_dsn=s.DATABASE_URL_SYNC,
    )
    n = await run_daily(deps, override_today=date.today())
    print(f'wrote {n} advisories')

asyncio.run(main())
"
```

Skip the scheduler entirely by adding `GINGER_JOB_ENABLED=false` to `.env` and restarting the app container. See [GINGER_ENGINE_CHANGES](GINGER_ENGINE_CHANGES.md) for the full integration architecture and rollback procedure.

## Deployment checklist

For direct Lightsail staging, read [`../deploy/staging/README.md`](../deploy/staging/README.md). Coolify is optional; read [`../deploy/coolify/README.md`](../deploy/coolify/README.md) only if you intentionally adopt it.

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
| No MQTT readings | Internal app broker must be `mosquitto:1883` with `MQTT_USE_TLS=false`; external hardware/laptop uses Caddy TLS `8883`. Then check credentials, topic shape, `ingest_broker.subscribed`, and queue/drop metrics |
| Payload is silently absent | `tail_ingest.py`; unknown fields, naive timestamps, wrong enums, or invalid `$schema` are rejected |
| Repeated QoS-1 packet creates no new alert | Expected if `(node_id, recorded_at)` already exists; duplicates skip rule evaluation |
| Dashboard shows 401 | Access token expired; mint a new token or use the refresh endpoint |
| Dashboard is empty | Confirm pilot rows exist, the token's farmer/tenant owns the seeded data, and the API base URL is correct |
| Production docs are unavailable | Expected: production FastAPI/Caddy intentionally hides `/docs`, `/redoc`, and OpenAPI |

## AWS Lightsail lessons from the current deployment

- `make caddyfile-prod IP=...` must be run from `~/agro_backend`, not `~`.
- Render `deploy/caddy/Caddyfile.prod` before starting the production stack.
- The custom Caddy image needs the Layer-4 plugin; the stock Caddy image only
  handles HTTP and caused the MQTT proxy to fail.
- Caddy binds `:8883` inside the container. Docker maps the VPS host's public
  port; do not bind the container listener to the VPS IP.
- Create `deploy/mosquitto/passwd` and `acl` as regular files before Docker
  starts. A missing file bind mount may become a directory and produce “not a
  directory”.
- A `read-only file system` error from `mosquitto_passwd` means the command was
  run against the broker's read-only mount. Update the host file with a
  one-off `eclipse-mosquitto:2.0.18` container instead.
- Set a real ACME email in the Caddy template; `ops@example.com` is only a
  placeholder.
- The complete environment-variable semantics, including why the app uses
  internal port `1883` while firmware uses public `8883`, are in
  [`CONFIGURATION.md`](CONFIGURATION.md).

## Production MQTT credential procedure

Use a new random secret. Do not reuse a password that was pasted into a chat,
terminal transcript, or old `.env`:

```bash
cd ~/agro_backend
MQTT_PASSWORD="$(openssl rand -hex 24)"
sudo install -m 644 /dev/null deploy/mosquitto/passwd
sudo install -m 644 /dev/null deploy/mosquitto/acl

docker run --rm \
  -v "$PWD/deploy/mosquitto:/mosquitto/config" \
  eclipse-mosquitto:2.0.18 \
  mosquitto_passwd -b -c /mosquitto/config/passwd \
  main-node-001 "$MQTT_PASSWORD"

sudo chown 1883:1883 deploy/mosquitto/passwd deploy/mosquitto/acl
sudo chmod 600 deploy/mosquitto/passwd
sudo chmod 700 deploy/mosquitto/acl
sudo sed -i "s/^MQTT_BROKER_PASSWORD=.*/MQTT_BROKER_PASSWORD=$MQTT_PASSWORD/" .env

docker compose -f docker-compose.prod.yml restart mosquitto
docker compose -f docker-compose.prod.yml up -d --force-recreate app
```

The ACL must contain a matching user and permission, for example:

```text
user main-node-001
topic readwrite agro/v2/#
```

Store the generated password in the Main Node configuration and a secure
password manager. Do not print it in shared output.

## Safe change workflow

For a persisted or externally visible change, update the owning code, matching
tests, migration/wire/API documentation, and deployment notes together. Do not
edit an applied migration or use destructive Git commands to force a VPS to
match a copied tree. Diagnose the running state and make a forward, reversible
change.
