# Configuration and environment variables

This is the complete configuration reference for the current repository.
The application reads settings through `app/config.py` using Pydantic Settings.
Docker Compose also reads some variables while interpolating the compose file.
Those are two different consumers: a variable can be valid for Compose even if
the Python application never reads it, and vice versa.

Create the local file with:

```bash
cd agro_backend
cp .env.example .env
```

Never commit `.env`, provider credentials, service-account JSON, private OTA
keys, or a real Mosquitto password file. Values in this document are names and
examples only.

## How configuration is loaded

1. `app/config.py` loads `.env` and process environment variables.
2. Environment variable names are case-insensitive and unknown names are ignored.
3. `get_settings()` caches one `Settings` object per process.
4. `APP_ENV=production` activates a startup guard that rejects the obvious
   default/empty values for `AUTH_JWT_SECRET`, `POSTGRES_PASSWORD`,
   `MQTT_BROKER_PASSWORD`, and `ANTHROPIC_API_KEY`.
5. `docker-compose.dev.yml` and `docker-compose.prod.yml` override the service
   hostnames so containers use `postgres`, `mosquitto`, and `chroma` on the
   internal Docker network.

The repository currently uses `APP_ENV=staging` for the AWS Lightsail pilot.
That is deliberate: the staging deployment keeps the production-shaped Compose
topology without enabling the stricter `APP_ENV=production` Anthropic check.

## Required for local Docker development

| Variable | Example | Used by | Meaning |
|---|---|---|---|
| `POSTGRES_USER` | `agro` | Compose + app | Database role name. |
| `POSTGRES_DB` | `agro` | Compose + app | Database name. |
| `POSTGRES_PASSWORD` | generated secret | Compose + app | Postgres role password. |
| `DATABASE_URL` | `postgresql+asyncpg://...` | FastAPI | Async SQLAlchemy DSN. In Compose, the host is rewritten to `postgres`. |
| `DATABASE_URL_SYNC` | `postgresql://...` | Alembic + seed | Synchronous psycopg2 DSN. |
| `AUTH_JWT_SECRET` | generated secret | Auth | HS256 signing key for access JWTs. |
| `MQTT_BROKER_PASSWORD` | generated secret | FastAPI + Mosquitto operations | Password paired with `MQTT_BROKER_USER`; it must match the bcrypt entry in `deploy/mosquitto/passwd`. |
| `GRAFANA_ADMIN_PASSWORD` | generated secret | Production Compose | Required by the Grafana service interpolation. It is not read by Python. |

Development can use the local defaults for non-secret settings, but replacing
all default secrets is still recommended. The Python test environment supplies
its own values through CI/test fixtures.

## App identity and logging

| Variable | Default | Meaning |
|---|---|---|
| `APP_ENV` | `development` | One of `development`, `staging`, `production`, or `test`. Controls production safety checks, docs exposure, and adapter selection. |
| `APP_VERSION` | `0.0.1` | API version shown by `/api/v1/health` and FastAPI metadata. |
| `APP_GIT_SHA` | `dev` | Release/commit label shown by health and startup logs. CI can inject the commit SHA. |
| `LOG_LEVEL` | `INFO` | Structured logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. |

## Database and connection pool

| Variable | Default | Meaning |
|---|---|---|
| `POSTGRES_USER` | `agro` | Compose-created database role. |
| `POSTGRES_DB` | `agro` | Compose database name. |
| `POSTGRES_PASSWORD` | `agro` in Python only | Secret used by Postgres and the app. Never use this default outside local development. |
| `DATABASE_URL` | local async DSN | Runtime SQLAlchemy `asyncpg` connection string. |
| `DATABASE_URL_SYNC` | local sync DSN | Alembic and synchronous pilot-seed connection string. |
| `DB_POOL_SIZE` | `10` | SQLAlchemy pool size. |
| `DB_MAX_OVERFLOW` | `5` | Temporary connections above the pool size. |
| `DB_POOL_TIMEOUT_S` | `30` | Seconds to wait for a pool connection. |

When the app runs inside Compose, use service DNS names (`postgres`) rather
than `localhost`. When running the seed script directly on a laptop, use the
host-mapped port (`5433`) and export a matching `DATABASE_URL_SYNC`.

## Authentication and OTP

| Variable | Default | Meaning |
|---|---|---|
| `AUTH_JWT_SECRET` | development placeholder | HS256 signing secret. Rotating it invalidates existing access tokens. |
| `AUTH_JWT_ACCESS_TTL_SECONDS` | `900` | Access-token lifetime; 15 minutes. |
| `AUTH_JWT_REFRESH_TTL_SECONDS` | `2592000` | Refresh-token lifetime; 30 days. |
| `AUTH_JWT_ISSUER` | `agroguardian` | JWT `iss` claim. |
| `AUTH_JWT_AUDIENCE` | `agroguardian-app` | JWT `aud` claim. |
| `AUTH_JWT_ALGORITHM` | `HS256` | Fixed by the settings type; do not change without changing the issuer implementation. |
| `OTP_TRANSPORT` | `whatsapp` | `whatsapp` is the pilot path; `sms` is reserved for a future MSG91 adapter. |
| `OTP_CODE_TTL_SECONDS` | `300` | OTP validity window. |
| `OTP_MAX_ATTEMPTS` | `5` | Failed attempts before the challenge is locked. |
| `OTP_LOCKOUT_MINUTES` | `30` | Throttle/lockout window used by the OTP use case. |

In development and tests, the HTTP dependency selects the log-only WhatsApp
sender. In production it selects the Meta sender only when Meta credentials
are present. The log-only sender exposes the OTP in development logs; never use
that behavior as a production delivery mechanism.

## MQTT and hardware ingest

| Variable | Default | Meaning |
|---|---|---|
| `MQTT_BROKER_HOST` | `localhost` | Hostname the backend subscriber connects to. Compose overrides it to `mosquitto`. |
| `MQTT_BROKER_PORT` | `1883` | Listener used by the backend subscriber. In staging/production this is the private plain-MQTT listener. |
| `MQTT_BROKER_USER` | `service` | Backend subscriber username. The aggregate pilot normally uses `main-node-001` so the Main Node and backend share the provisioned ACL. |
| `MQTT_BROKER_PASSWORD` | `CHANGE_ME` | Password for the backend MQTT client. It must match the Mosquitto password file. |
| `MQTT_TLS_CA_PATH` | `/etc/ssl/certs/ca-certificates.crt` | CA bundle used only when the backend client itself uses TLS. |
| `MQTT_USE_TLS` | `false` | Whether the backend-to-Mosquitto connection uses TLS. In the current VPS topology it stays `false`; Caddy terminates public TLS on `8883` and forwards to Mosquitto `1883`. |
| `MQTT_QUEUE_MAXSIZE` | `5000` | Maximum in-process async queue depth between the Paho callback thread and the ingest task. |
| `CALIBRATION_MODE` | `false` | When true, readings are persisted and validation still runs, but the **device-health** rule engine short-circuits (no alerts, no events). Use during hardware calibration so wonky readings don't spam the ops queue. **Does not affect the ginger engine** — that has its own `GINGER_JOB_ENABLED` switch. |

## Ginger advisory job (Round G)

| Variable | Default | Meaning |
|---|---|---|
| `GINGER_JOB_ENABLED` | `true` | Master switch for the ginger advisory scheduler. When false, `build_and_start_scheduler` returns `None` and the lifespan skips APScheduler startup entirely — useful in tests, during outages, or when running the app in a batch-only context. |
| `GINGER_JOB_TIMEZONE` | `Asia/Kolkata` | IANA timezone that "today" is computed in. Pilot is Aurangabad; the farmer's day boundary is IST midnight. Do NOT use UTC — `date.today()` on a UTC-running container rolls at midnight UTC and would misattribute the day at the boundary. |
| `GINGER_JOB_HOUR` | `6` | Hour of day (in `GINGER_JOB_TIMEZONE`) the job fires. |
| `GINGER_JOB_MINUTE` | `30` | Minute of hour the job fires. Default 06:30 IST — before the farmer's workday. |

All four are read once at process startup by `app/jobs/ginger_scheduler.py`. Change any of them → restart the app container.

There are two MQTT hops in staging/production:

```text
Main Node/laptop -- TLS :8883 --> Caddy Layer-4 -- plain private :1883 --> Mosquitto
                                                        ^
                                                        |
                                      FastAPI backend subscriber :1883
```

Therefore do not set the app's internal `MQTT_BROKER_PORT` to `8883` unless
you intentionally change the topology. Firmware and external smoke tests use
the public TLS hostname and port `8883`.

## ChromaDB and AI

| Variable | Default | Meaning |
|---|---|---|
| `CHROMA_HOST` | `localhost` | Chroma hostname; Compose overrides to `chroma`. |
| `CHROMA_PORT` | `8001` | Host port when running outside Compose; Compose overrides the app value to container port `8000`. |
| `CHROMA_PERSIST_PATH` | `/data/chroma` | Chroma persistence path. |
| `CHROMA_EMBEDDING_MODEL` | `paraphrase-multilingual-mpnet-base-v2` | Multilingual embedding model name. The backend image pre-bakes this model. |
| `ANTHROPIC_API_KEY` | empty | Claude credential. Required by the current production startup guard, optional for staging ingest and development. |
| `ANTHROPIC_MODEL_SONNET` | `claude-sonnet-4-5` | Configured Sonnet model name. |
| `ANTHROPIC_MODEL_HAIKU` | `claude-haiku-4-5` | Configured Haiku model name. |
| `USD_INR_RATE` | `83.0` | Cost-conversion input for future accounting. |
| `LLM_MAX_TOOL_ITER` | `5` | Maximum future tool-iteration budget. |

The Claude adapter and advisory use case exist, but they are not wired into the
current FastAPI lifespan or MQTT event subscriber. An alert row does not
currently cause a Claude advisory automatically.

## WhatsApp / Meta Cloud API

| Variable | Meaning |
|---|---|
| `META_WHATSAPP_PHONE_NUMBER_ID` | Meta phone-number resource used by the Messages endpoint. |
| `META_WHATSAPP_BUSINESS_ACCOUNT_ID` | WABA identifier; stored for future webhook/management work. |
| `META_WHATSAPP_TOKEN` | Meta access token. |
| `META_WHATSAPP_VERIFY_TOKEN` | Webhook verification secret; webhook handling is not currently exposed. |
| `META_WHATSAPP_OTP_TEMPLATE_NAME` | OTP template name, default `agroguardian_otp_v1`. |
| `META_WHATSAPP_ADVISORY_TEMPLATE_NAME` | Future advisory template, default `agroguardian_advisory_v1`. |
| `META_WHATSAPP_GRAPH_VERSION` | Meta Graph API version, default `v20.0`. |

## FCM, satellite, weather, and storage

These variables are typed configuration seams for later integrations. They do
not make those integrations live by themselves.

| Variable(s) | Meaning |
|---|---|
| `FCM_SERVICE_ACCOUNT_JSON_PATH`, `FCM_PROJECT_ID` | Firebase service-account path and project identifier for future push notifications. |
| `COPERNICUS_CLIENT_ID`, `COPERNICUS_CLIENT_SECRET` | Sentinel-2 credentials. |
| `COPERNICUS_BASE_URL`, `COPERNICUS_TOKEN_URL` | Copernicus processing and OAuth endpoints. Trailing slashes are stripped. |
| `NASA_EARTHDATA_USERNAME`, `NASA_EARTHDATA_PASSWORD` | NASA Earthdata credentials. |
| `OPEN_METEO_BASE_URL`, `IMD_BASE_URL` | Weather provider base URLs. |
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT_URL` | Cloudflare R2 S3-compatible credentials and endpoint. |
| `R2_BUCKET_RASTERS`, `R2_BUCKET_PHOTOS`, `R2_BUCKET_FIRMWARE` | R2 bucket names. |
| `B2_KEY_ID`, `B2_APPLICATION_KEY`, `B2_ENDPOINT_URL` | Backblaze B2 credentials and S3-compatible endpoint. |
| `B2_BUCKET_BACKUPS` | B2 backup bucket name. |

No AWS-managed service is required by the application code. Lightsail is only
the current VPS host; object storage settings remain provider-neutral.

## Monitoring and HTTP security

| Variable | Default | Meaning |
|---|---|---|
| `SENTRY_DSN` | empty | Enables Sentry when non-empty and `APP_ENV` is not `test`. |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.1` | Sentry trace sampling. |
| `SENTRY_PROFILES_SAMPLE_RATE` | `0.1` | Sentry profile sampling. |
| `BETTER_STACK_TOKEN` | empty | Reserved for external log shipping; stdout remains the current deployment log path. |
| `BETTER_STACK_INGEST_HOST` | `in.logs.betterstack.com` | Better Stack ingest host. |
| `CORS_ALLOWED_ORIGINS` | localhost API/dashboard origins | Comma-separated browser origins. The value must not be empty. |
| `TRUSTED_HOSTS` | `*` | Comma-separated host allow-list. `*` disables `TrustedHostMiddleware`. |

Production Caddy hides `/api/v1/docs`, `/api/v1/redoc`, and
`/api/v1/openapi.json` publicly. It also gates `/metrics` and Grafana by the
Tailscale address range in the current template.

## OTA signing

| Variable | Meaning |
|---|---|
| `OTA_SIGNING_PRIVATE_KEY_PEM` | Private Ed25519 PEM, represented as a secret string; future firmware-signing path. |
| `OTA_SIGNING_PUBLIC_KEY_PEM` | Public key distributed to firmware; future path. |

`PROJECT_ROOT` is derived from the location of `app/config.py`; it is not read
from the environment and should not be added to `.env`.

## Compose-only and generated files

- `GRAFANA_ADMIN_PASSWORD` is mandatory for `docker compose -f
  docker-compose.prod.yml config` and `up`; put it in `.env` even if Grafana
  is not part of the current pilot smoke test.
- `deploy/caddy/Caddyfile.prod` is generated from `deploy/caddy/Caddyfile` and
  must exist before the production Compose stack starts.
- `deploy/mosquitto/passwd` contains bcrypt hashes, not plaintext passwords;
  `deploy/mosquitto/acl` controls topic access. Both are mounted read-only by
  Compose, which is why credential updates use a disposable Mosquitto utility
  container and host-side permissions.
- The current repository tracks the `passwd` and `acl` paths. Treat that as a
  security debt: remove operational credential files from Git history and add
  them to the ignore policy before using a real fleet credential.

## Safe validation commands

These commands inspect names and Compose interpolation without printing secret
values:

```bash
cd agro_backend
awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/{print $1}' .env | sort
docker compose -f docker-compose.prod.yml config >/tmp/agro-compose-rendered.yml
docker compose -f docker-compose.prod.yml ps
```
