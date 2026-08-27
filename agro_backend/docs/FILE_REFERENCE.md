# Complete repository file reference

This index covers every tracked file in the repository at the time of this
documentation pass. Empty `__init__.py` files are included because they define
Python package boundaries even when they contain no runtime code. Generated
virtual environments and caches are intentionally not part of the repository
and are not documented as source files.

## Root and backend control files

| File | Purpose |
|---|---|
| [`README.md`](../../README.md) | Repository entry point and documentation links. |
| [`agro_backend/.cursorrules`](../.cursorrules) | Project engineering rules and architectural constraints; it is guidance, not a runtime validator. |
| [`agro_backend/.env.example`](../.env.example) | Safe configuration template containing variable names and non-secret defaults. |
| [`agro_backend/.gitignore`](../.gitignore) | Ignores local environments, caches, `.env`, keys, and build artifacts. Operational Mosquitto files still need security cleanup. |
| [`agro_backend/ACCOUNTS_TO_FILL.md`](../ACCOUNTS_TO_FILL.md) | External-account checklist and the provider values that may eventually be required. |
| [`agro_backend/Dockerfile`](../Dockerfile) | Multi-stage Python image; installs native geospatial dependencies, pre-bakes the embedding model, copies app/ginger/migrations/rules/seeder, and runs as user `agro`. |
| [`agro_backend/Makefile`](../Makefile) | Local quality, Docker, migration, and Caddy-rendering targets. Must be run from `agro_backend/`. |
| [`agro_backend/README.md`](../README.md) | Backend quick start, local endpoints, tests, and architecture links. |
| [`agro_backend/alembic.ini`](../alembic.ini) | Alembic script location and logging configuration; the URL is supplied by `DATABASE_URL_SYNC`. |
| [`agro_backend/pyproject.toml`](../pyproject.toml) | Python package metadata, dependencies, test settings, coverage gate, Ruff, and mypy configuration. |
| `agro_backend/.github/workflows/ci.yml` | GitHub Actions lint/type/test/multi-architecture build pipeline. |

## Application package

### Package markers and composition

| File | Purpose |
|---|---|
| `app/__init__.py` | Root package marker. |
| `app/main.py` | FastAPI factory, lifespan, Sentry setup, middleware, router registration, and `/metrics`. Starts/stops MQTT ingest. |
| `app/config.py` | Typed settings, environment parsing, secret wrappers, URL normalization, cached settings, and production safety guard. |
| `app/deps.py` | Original settings-only dependency helper retained for compatibility; active repository/auth dependency wiring is in `app/infra/http/deps.py`. |

### Domain: pure business logic

| File | Purpose |
|---|---|
| `app/domain/__init__.py` | Domain package marker. |
| `app/domain/sensor.py` | Frozen `Reading` model, telemetry enums, and sensor constants. Uses `Decimal` for measurements. |
| `app/domain/plot.py` | Frozen plot model and `DataTier`/`PlotStatus` enums. |
| `app/domain/alert.py` | Alert severity/type/dispatch enums and immutable alert candidate. |
| `app/domain/auth.py` | OTP, refresh-secret, phone-masking, JWT-claim value types, and hashing helpers. |
| `app/domain/metrics.py` | Derived moisture, battery, frost, dry-run, and sensor-health metrics. |
| `app/domain/validation_gates.py` | Pure range, stuck, MAD-outlier, and cross-sensor validation math. |
| `app/domain/rules.py` | Generic immutable rule/ruleset engine; no database, clock, or I/O. |
| `app/domain/rule_definitions.py` | Seven active pilot rules, Marathi templates, cooldowns, and threshold exports. |

### Application use cases and ports

| File | Purpose |
|---|---|
| `app/application/__init__.py` | Application package marker. |
| `app/application/ingest_telemetry.py` | Validates a domain reading, persists it through `ReadingRepo`, and publishes `telemetry.ingested` for a fresh insert. |
| `app/application/validate_reading.py` | Fetches historical windows through a port, runs domain gates in canonical order, and returns an updated immutable reading. |
| `app/application/process_reading.py` | Composes ingest and rule evaluation; skips rule evaluation for idempotent duplicates. |
| `app/application/evaluate_rules.py` | Runs pilot rules, applies repository-backed cooldowns, persists alerts, and publishes `alert.created`. |
| `app/application/send_otp.py` | Creates/throttles OTP challenges and delegates delivery to a WhatsApp/SMS port. |
| `app/application/verify_otp.py` | Verifies and consumes OTPs, checks farmer state, and issues access/refresh tokens. |
| `app/application/refresh_token.py` | Validates a hashed refresh session, rotates it, and issues a new token pair. |
| `app/application/logout.py` | Revokes one refresh session or all sessions for a farmer. |
| `app/application/compose_advisory.py` | Prepared alert-to-Claude advisory use case; not wired to the current startup/event path. |
| `app/application/ports/__init__.py` | Port package marker. |
| `app/application/ports/reading_repo.py` | Reading persistence and history Protocol. |
| `app/application/ports/alert_repo.py` | Alert persistence, cooldown, listing, and resolution Protocols plus views. |
| `app/application/ports/plot_repo.py` | Plot lookup/listing Protocol. |
| `app/application/ports/farmer_repo.py` | Farmer identity lookup Protocol. |
| `app/application/ports/crop_season_repo.py` | Active crop-season lookup Protocol. |
| `app/application/ports/ai_suggestion_repo.py` | AI suggestion value type and persistence Protocol. |
| `app/application/ports/otp_repo.py` | OTP challenge persistence/throttle Protocol. |
| `app/application/ports/auth_session_repo.py` | Hashed refresh-session persistence Protocol. |
| `app/application/ports/token_issuer.py` | Access-token issue/verify Protocol and invalid-token exception. |
| `app/application/ports/whatsapp_sender.py` | OTP sender result and provider Protocol. |
| `app/application/ports/chat_model.py` | Provider-neutral chat request/response and model Protocol. |
| `app/application/ports/event_bus.py` | Event names and publish Protocol for `pg_notify` and future subscribers. |

### Infrastructure adapters

| File | Purpose |
|---|---|
| `app/infra/__init__.py` | Infrastructure package marker. |
| `app/infra/http/__init__.py` | HTTP adapter package marker. |
| `app/infra/http/deps.py` | Lazy async engine/session singleton, repository providers, JWT dependency, bearer-token verification, and WhatsApp adapter selection. |
| `app/infra/http/health.py` | Liveness and readiness-shaped routes. Readiness is still a phase-0 stub. |
| `app/infra/http/auth.py` | OTP, verify, refresh, logout, and `/me` routes plus request/response models. |
| `app/infra/http/plots.py` | Authenticated plot metadata, readings, alerts, and suggestion routes. |
| `app/infra/http/alerts.py` | Tenant alert queue and resolve route. |
| `app/infra/mqtt/__init__.py` | MQTT adapter package marker. |
| `app/infra/mqtt/schemas.py` | Strict Pydantic MQTT wire model, Decimal coercion, topic parser, and wire-to-domain projection. |
| `app/infra/mqtt/broker.py` | Paho MQTT v5 subscriber, TLS setup, reconnect logging, bounded thread-to-async queue, parsing, processing, and drop metrics. |
| `app/infra/auth/__init__.py` | Auth adapter package marker. |
| `app/infra/auth/jwt_issuer.py` | HS256 JWT implementation over `python-jose`. |
| `app/infra/events/__init__.py` | Event adapter package marker. |
| `app/infra/events/pg_notify_bus.py` | PostgreSQL `pg_notify` publisher with an 7,500-byte safety limit. |
| `app/infra/llm/__init__.py` | LLM adapter package marker. |
| `app/infra/llm/claude_chat.py` | Anthropic async client adapter and transient/permanent error mapping. |
| `app/infra/llm/log_only_chat.py` | No-network chat stub for development/tests. |
| `app/infra/whatsapp/__init__.py` | WhatsApp adapter package marker. |
| `app/infra/whatsapp/meta_cloud_sender.py` | Meta Cloud API OTP-template sender. |
| `app/infra/whatsapp/log_only_sender.py` | Development sender that logs the OTP; never use for production delivery. |
| `app/infra/persistence/__init__.py` | Persistence adapter package marker. |
| `app/infra/persistence/base.py` | SQLAlchemy declarative base. |
| `app/infra/persistence/engine.py` | Async engine and sessionmaker factories. |
| `app/infra/persistence/pg_farmer_repo.py` | PostgreSQL farmer identity adapter. |
| `app/infra/persistence/pg_plot_repo.py` | PostgreSQL plot listing/lookup adapter. |
| `app/infra/persistence/pg_reading_repo.py` | PostgreSQL reading insert/history/list adapter with duplicate idempotency. |
| `app/infra/persistence/pg_alert_repo.py` | PostgreSQL alert creation, cooldown, listing, and resolution adapter. |
| `app/infra/persistence/pg_otp_repo.py` | PostgreSQL active OTP lookup, throttling, and challenge persistence adapter. |
| `app/infra/persistence/pg_auth_session_repo.py` | PostgreSQL hashed refresh-session adapter. |
| `app/infra/persistence/pg_crop_season_repo.py` | PostgreSQL active crop-season adapter. |
| `app/infra/persistence/pg_ai_suggestion_repo.py` | PostgreSQL AI-suggestion read/write adapter. |
| `app/infra/persistence/models/__init__.py` | Imports/registers ORM model modules. |
| `app/infra/persistence/models/core.py` | Tenant, users, legacy auth rows, and audit-log ORM models. |
| `app/infra/persistence/models/farms.py` | Farmer, farm, plot, and crop-season ORM models. |
| `app/infra/persistence/models/devices.py` | Device registry, components, installations, service, and calibration ORM models. |
| `app/infra/persistence/models/readings.py` | Sensor, weather, forecast, and satellite ORM models. |
| `app/infra/persistence/models/events.py` | Irrigation, electricity, water-source, and farmer-action ORM models. |
| `app/infra/persistence/models/alerts.py` | Alert, dispatch-log, and dead-letter ORM models. |
| `app/infra/persistence/models/ai.py` | Suggestion, learning-log, and chat-message ORM models. |
| `app/infra/persistence/models/billing.py` | Subscription and performance-report ORM models. |
| `app/infra/persistence/models/system.py` | Feature flags, system config, unmatched ingest, outbox, and WhatsApp inbound ORM models. |
| `app/infra/forecast/__init__.py` | Reserved forecast adapter package. No active provider implementation. |
| `app/infra/satellite/__init__.py` | Reserved satellite adapter package. No active provider implementation. |
| `app/infra/storage/__init__.py` | Reserved R2/B2 storage adapter package. |
| `app/infra/notify/__init__.py` | Reserved outbound notification adapter package. |
| `app/infra/ota/__init__.py` | Reserved OTA adapter package. |
| `app/infra/ai/__init__.py` | Reserved AI adapter package. |
| `app/infra/ai/tools/__init__.py` | Reserved AI tool package. |

### Jobs and shared libraries

| File | Purpose |
|---|---|
| `app/jobs/__init__.py` | Jobs package marker. |
| `app/jobs/ingest_startup.py` | Builds repositories/event bus/rule dependencies from settings and starts the MQTT broker during FastAPI lifespan. |
| `app/lib/__init__.py` | Shared-library package marker. |
| `app/lib/logging.py` | Structlog configuration, standard-library log bridge, redaction, and phone masking. |
| `app/lib/metrics.py` | Prometheus counters/gauges/histograms for HTTP, ingest, rules, alerts, and provider calls. |
| `app/lib/time.py` | UTC/IST timezone helpers and aware-datetime normalization. |

## Database and migrations

| File | Purpose |
|---|---|
| `alembic/env.py` | Synchronous Alembic runner that reads `DATABASE_URL_SYNC`; intentionally uses hand-written SQL with `target_metadata=None`. |
| `alembic/versions/__init__.py` | Migration package marker. |
| `alembic/versions/0001_init_21_tables.py` | Initial source schema and tenant table. |
| `alembic/versions/0002_v3_additional_tables.py` | v3 users, operational, AI, feature, and system tables/columns. |
| `alembic/versions/0003_extensions.py` | UUID, PostGIS, pgcrypto, and optional vector extensions. |
| `alembic/versions/0004_plots_satellite_only.py` | Plot data tier and satellite-only/sub-node consistency trigger. |
| `alembic/versions/0005_partition_timeseries.py` | Range partitions, monthly partitions, reading columns, and idempotency constraints. |
| `alembic/versions/0006_aggregates.py` | Hour/day materialized views and latest-plot view. |
| `alembic/versions/0007_audit_log.py` | Audit trigger function and master-table triggers. |
| `alembic/versions/0008_rls_policies.py` | Roles, grants, tenant RLS, ownership policies, and AI review guard. |
| `alembic/versions/0009_auth_otp_tables.py` | Active `otp_challenges` and `auth_sessions` tables. |

Migrations are authoritative for the deployed schema; the ORM registry is not
used for autogeneration.

## Dashboard

| File | Purpose |
|---|---|
| `dashboard/README.md` | Dashboard setup, static-token auth, launch, and limitations. |
| `dashboard/requirements.txt` | Streamlit, HTTPX, and dashboard runtime dependencies. |
| `dashboard/api_client.py` | Thin HTTP-only client using `AGRO_API_BASE_URL` and `ACCESS_TOKEN`. |
| `dashboard/app.py` | Streamlit landing page and identity card. |
| `dashboard/pages/01_Farmer_Overview.py` | Plot cards with latest reading and top open alert. |
| `dashboard/pages/02_Plot_Detail.py` | Reading charts, alert table, and persisted-suggestion view. |
| `dashboard/pages/03_Ops_Queue.py` | Tenant-wide alert filtering and resolve forms. |

## Deployment and operations

| File | Purpose |
|---|---|
| `docker-compose.dev.yml` | Local Postgres, Mosquitto, Chroma, and hot-reload app stack. |
| `docker-compose.prod.yml` | VPS/Coolify-shaped Caddy, Postgres, Mosquitto, Chroma, app, Prometheus, and Grafana stack. |
| `deploy/caddy/Caddyfile` | Caddy template for API, public MQTT TLS, dashboard, and private metrics/Grafana hostnames. |
| `deploy/caddy/Dockerfile` | Builds Caddy with `caddy-l4` so raw MQTT/TCP can be proxied. |
| `deploy/mosquitto/mosquitto.conf` | Development listeners: anonymous plain `1883` and credentialed convenience `8883`. |
| `deploy/mosquitto/mosquitto.prod.conf` | Production private authenticated listener on `1883`; Caddy owns public TLS. |
| `deploy/mosquitto/passwd` | Mosquitto bcrypt password database; operational secret-bearing file. |
| `deploy/mosquitto/acl` | Mosquitto topic permissions; operational secret/config file. |
| `deploy/prometheus/prometheus.yml` | Scrapes the app's internal `/metrics` endpoint every 30 seconds. |
| `deploy/staging/README.md` | Current direct Lightsail staging runbook, including Docker, UFW, Caddy, MQTT, seeding, and smoke test. |
| `deploy/coolify/README.md` | Optional Coolify deployment path and migration notes; not required for the current direct VPS setup. |

## Developer scripts

| File | Purpose |
|---|---|
| `scripts/dev/seed_pilot.py` | Idempotently seeds the pilot tenant, farmer, farm, Main Node, one Sub Node, two plots (one hardware, one satellite-only), and crop seasons. Scope revised 2026-08-26 from 4 → 2 plots; extend `PLOTS` to scale out. |
| `scripts/dev/cleanup_stale_pilot_data.py` | Removes stale rows left over from the pre-2-plot scope: `PLOT_PILOT_003/004`, `AGR-SN-0002`, and every referencing row across `crop_seasons`, `alerts_notifications`, `ai_suggestions`, `node_sensor_readings`. Single transaction; idempotent; supports `--dry-run`. |
| `scripts/dev/fake_main_node.py` | Generates plausible QoS-1 telemetry against a plain MQTT listener for non-hardware testing. |
| `scripts/dev/provision_mqtt_credential.sh` | Updates a Mosquitto bcrypt credential and ACL; production mounts require the documented host-side permission procedure. |
| `scripts/dev/tail_ingest.py` | Filters structured logs into color-tagged ingest diagnostics. |
| `scripts/dev/render-caddyfile.sh` | Cross-platform shell renderer for an IP/sslip.io or real-domain Caddyfile. |
| `scripts/dev/render-caddyfile.ps1` | PowerShell renderer for Windows hosts. |

## Documentation

| File | Purpose |
|---|---|
| `docs/CODEBASE_GUIDE.md` | Architecture, runtime flows, domain behavior, persistence, deployment, and known gaps. |
| `docs/CONFIGURATION.md` | Complete environment-variable and Compose configuration reference. |
| `docs/FILE_REFERENCE.md` | This file-by-file index. |
| `docs/API_REFERENCE.md` | HTTP routes, auth requirements, payloads, and errors. |
| `docs/DEVELOPMENT.md` | Local development, testing, migrations, pilot seed, dashboard, and deployment workflow. |
| `docs/HARDWARE_WIRE_CONTRACT.md` | Exact MQTT topic, payload, validation, TLS, and firmware smoke-test contract. |
| `docs/SCHEMA_DECISIONS.md` | Reconciliation of the source schema and v3 roadmap decisions. |
| `rules/README.md` | Explains that runtime pilot rules are Python definitions, not files in this directory. |

## Tests

All test package `__init__.py` files are package markers. The tests mirror the
architecture and are the executable behavior reference:

### Shared and cross-cutting tests

| File | Coverage |
|---|---|
| `tests/__init__.py` | Test package marker. |
| `tests/conftest.py` | Shared settings, app, HTTP client, and database fixtures. |
| `tests/test_config.py` | Settings defaults, parsing, and production-secret validation. |
| `tests/test_health.py` | Health/readiness and metrics HTTP behavior. |
| `tests/test_logging.py` | Redaction, masking, and structured logging behavior. |
| `tests/test_time.py` | Aware UTC/IST/time-normalization helpers. |

### Domain tests

| File | Coverage |
|---|---|
| `tests/domain/__init__.py` | Domain-test package marker. |
| `tests/domain/test_sensor.py` | Reading immutability, enums, and sensor model behavior. |
| `tests/domain/test_plot.py` | Plot model, enum, and geometry/data-tier behavior. |
| `tests/domain/test_alert.py` | Alert enums and immutable candidate behavior. |
| `tests/domain/test_auth.py` | OTP/refresh hashing, masking, expiry, and claim values. |
| `tests/domain/test_metrics.py` | Derived metrics and calibration thresholds. |
| `tests/domain/test_validation_gates.py` | Range, stuck, MAD, cross-sensor, and gate ordering math. |
| `tests/domain/test_rules.py` | Pure rule-engine evaluation and template rendering. |
| `tests/domain/test_rule_definitions.py` | Pilot rule IDs, thresholds, cooldowns, and predicates. |
| `tests/domain/test_domain_purity.py` | AST import guard for domain-layer dependency purity. |

### Application tests

| File | Coverage |
|---|---|
| `tests/application/__init__.py` | Application-test package marker. |
| `tests/application/test_ingest_telemetry.py` | Save/event behavior for valid and duplicate readings. |
| `tests/application/test_validate_reading.py` | Repository history orchestration and validation flags. |
| `tests/application/test_process_reading.py` | Fresh-insert rule evaluation vs duplicate skip. |
| `tests/application/test_evaluate_rules.py` | Cooldowns, alert creation, events, and calibration short-circuit. |
| `tests/application/test_send_otp.py` | OTP creation, throttling, masking, and sender errors. |
| `tests/application/test_verify_otp.py` | OTP verification and token-pair issuance. |
| `tests/application/test_refresh_token.py` | Refresh rotation and invalid sessions. |
| `tests/application/test_logout.py` | Single-session and everywhere logout. |
| `tests/application/test_compose_advisory.py` | Prepared alert-to-LLM advisory orchestration. |
| `tests/application/test_ports_are_protocols.py` | Port shape and application dependency boundaries. |
| `tests/application/test_application_purity.py` | AST guard ensuring application code does not import infrastructure directly. |

### HTTP, MQTT, and adapter tests

| File | Coverage |
|---|---|
| `tests/infra/__init__.py` | Infrastructure-test package marker. |
| `tests/infra/ai/__init__.py` | Reserved AI infrastructure-test package marker. |
| `tests/infra/http/__init__.py` | HTTP-test package marker. |
| `tests/infra/http/test_auth_routes.py` | Auth route statuses, auth errors, and dependency overrides. |
| `tests/infra/http/test_plot_routes.py` | Plot visibility and nested reading/alert/suggestion routes. |
| `tests/infra/http/test_alert_routes.py` | Alert queue filters and resolve behavior. |
| `tests/infra/mqtt/__init__.py` | MQTT-test package marker. |
| `tests/infra/mqtt/test_schemas.py` | Topic parsing, strict payload validation, Decimal coercion, and timestamps. |
| `tests/infra/mqtt/test_broker.py` | Paho callback bridge, queue/drop classification, and drain processing. |
| `tests/infra/auth/__init__.py` | Auth-adapter test marker. |
| `tests/infra/auth/test_jwt_issuer.py` | JWT issue/verify and malformed claim handling. |
| `tests/infra/events/__init__.py` | Event-adapter test marker. |
| `tests/infra/events/test_pg_notify_bus.py` | Notify payload size and SQL publish behavior. |
| `tests/infra/llm/__init__.py` | LLM-test package marker. |
| `tests/infra/llm/test_claude_chat.py` | Anthropic success/error mapping with `respx`. |
| `tests/infra/llm/test_log_only_chat.py` | No-network chat stub behavior. |
| `tests/infra/whatsapp/__init__.py` | WhatsApp-test package marker. |
| `tests/infra/whatsapp/test_meta_cloud_sender.py` | Meta success, provider failures, and network errors. |

### Persistence tests

| File | Coverage |
|---|---|
| `tests/infra/persistence/__init__.py` | Persistence-test package marker. |
| `tests/infra/persistence/conftest.py` | Database engine/session fixtures for repository tests. |
| `tests/infra/persistence/test_models.py` | ORM metadata/model shape. |
| `tests/infra/persistence/test_schema_db.py` | Database schema/integration assertions. |
| `tests/infra/persistence/test_pg_farmer_repo.py` | Farmer repository. |
| `tests/infra/persistence/test_pg_plot_repo.py` | Plot repository. |
| `tests/infra/persistence/test_pg_reading_repo.py` | Reading persistence, idempotency, and history. |
| `tests/infra/persistence/test_pg_alert_repo.py` | Alert repository and cooldown queries. |
| `tests/infra/persistence/test_pg_otp_repo.py` | OTP repository. |
| `tests/infra/persistence/test_pg_auth_session_repo.py` | Auth-session repository. |
| `tests/infra/persistence/test_models.py` | Model registration and column behavior. |
| `tests/fixtures/__init__.py` | Future shared fixture package marker. |
| `tests/e2e/__init__.py` | End-to-end test package marker; no full e2e suite is currently present. |

### Ginger tests (Round G)

| File | Coverage |
|---|---|
| `tests/infra/ginger/__init__.py` | Ginger-adapter test package marker. |
| `tests/infra/ginger/test_import.py` | Locks the flat-import shim in `agro_backend/ginger/__init__.py`: `from runner import Runner`, `from persistence import PersistentRunner`, etc. all resolve. |
| `tests/infra/ginger/test_pg_state_store.py` | `PgStateStore.load` returns `{}` on missing row, returns `_reset_reason` on version mismatch, `log_advisory([])` does not open a connection. Mocked `psycopg2.connect`. |
| `tests/application/test_build_farm_brain.py` | Every declared `kb_farm_brain_fields` name is a dict key in the built state; known-good inputs populate expected values; missing reading yields Nones for sensors but season-derived fields still populate. Locks `SYNTHETIC_FIELDS` for the guardrail proposals. |

## Ginger advisory engine (Round G — teammate's delivery)

Standalone package at `agro_backend/ginger/`, sibling to `app/`. Not folded into `app/infra/` because the engine files use flat imports.

| File | Purpose |
|---|---|
| `ginger/__init__.py` | Inserts `ginger/engine/` onto `sys.path` at import time so the flat imports in the engine files resolve. Consumer contract: `import ginger` before any `from runner import ...`. |
| `ginger/engine/trigger_dsl.py` | DSL parser + three-valued evaluator (`TRUE`/`FALSE`/`UNKNOWN`). Grammar supports `AND`/`OR`/`NOT`, `IN`, `BETWEEN`, `IS NULL/NOT NULL/TRUE/FALSE`, `DURATION(field > x) > n unit`, `WITHIN(...)`, `MONTH IN [...]`, `STAGE IN [...]`. Undeclared field names are a parse error. |
| `ginger/engine/precedence.py` | Typed relations (`SUPPRESSES`, `SUPERSEDES`, `BUNDLES`, `SEQUENCES`, `ESCALATES`) plus multi-diagnosis (`CONFIRMED`/`PROBABLE`/`AMBIGUOUS`/`NO_CANDIDATE`). Records fallback use so unrecorded fallbacks are detectable. |
| `ginger/engine/notification_policy.py` | Four delivery classes (`SILENT_GUARD`, `EVENT`, `WINDOW`, `ONCE_UNTIL_RESOLVED`) implementing edge-detection + reminder ladders. |
| `ginger/engine/expert_override.py` | Runtime override API: 5 kinds (`THRESHOLD`, `DELIVERY`, `SEVERITY`, `DISABLE`, `PARAMETER`), 3 scopes (`plot > cluster > global`), 16 immutable rules refused. Refused attempts are logged, not discarded. |
| `ginger/engine/persistence.py` | State store interface + `FileStateStore` + `SqliteStateStore` + `PersistentRunner`. Postgres backend lives in `app/infra/ginger/pg_state_store.py`. |
| `ginger/engine/runner.py` | `Runner.run(ctx, day)` entry point that composes trigger → override → precedence → notification policy → message. |
| `ginger/engine/runtime_loader.py` | `JsonSource`, `PostgresSource`, `SqliteSource` — reads rules from the database, not from build files (see arch doc §11A). `build_runner(source, state_store)` constructs a `PersistentRunner`. |
| `ginger/generated/agroguardian_ginger_kb.sql` | Compiled 1.1 MB SQL loaded by Alembic migration 0010. **DO NOT EDIT** — regenerated upstream from the domain JSON files. |
| `app/infra/ginger/__init__.py` | Adapter package marker. |
| `app/infra/ginger/pg_state_store.py` | Postgres implementation of the `StateStore` interface. Fills the "PostgreSQL adapter is a known gap" hole in the teammate's arch doc §15. Uses psycopg2 (sync) — the daily job wraps in `asyncio.to_thread`. |
| `app/application/build_farm_brain.py` | Assembles the per-plot per-day dict of ~305 `kb_farm_brain_fields`. Populates ~85 from our repos (latest reading + plot + crop season + synthetic fields); the rest are `None` and the engine reports `UNKNOWN`. |
| `app/jobs/ginger_daily.py` | The daily job. `run_daily(deps)` iterates active ginger `crop_seasons`, builds Farm Brain state, calls the runner via `asyncio.to_thread`, persists messages to `ai_suggestions` with `ai_model_version='ginger-engine/v1.0'`. |
| `app/jobs/ginger_scheduler.py` | APScheduler wrapper. `build_and_start_scheduler(settings)` returns a running `AsyncIOScheduler` with the daily cron trigger, or `None` when `GINGER_JOB_ENABLED=false`. |
| `alembic/versions/0010_ginger_kb.py` | Loads the compiled SQL knowledge base. Adds 19 `kb_*` tables + 4 runtime tables + 16 views + `trg_reject_immutable_override`. Idempotent. |
| `docs/GINGER_ENGINE_CHANGES.md` | Complete Round G integration doc: files touched, migration details, rollback path, known limitations, dev runbook. |

## Firmware (sibling directory `../firmware/`)

Not part of the Python backend build. Documented here so the whole system is on one map.

| File | Purpose |
|---|---|
| `firmware/README.md` | System picture + first-time bring-up order (cloud → Sub Node → Main Node → verify in Postgres). |
| `firmware/main_node/platformio.ini` | PlatformIO project for the ESP32-WROOM-32. Pins library versions (LoRa 0.8, PubSubClient 2.8, ArduinoJson 7.1, TinyGSM 0.12) and sets `TINY_GSM_MODEM_A7672X`, `MQTT_MAX_PACKET_SIZE=1024`. |
| `firmware/main_node/include/pilot_config.h` | Everything that varies per deploy: `MQTT_HOST`, `MQTT_PASSWORD`, pilot UUIDs, Sub Node → plot map, GSM pins, LoRa SPI pins, `GSM_APN`, LoRa frequency. |
| `firmware/main_node/src/main.cpp` | Main Node firmware. Boot: modem power-cycle → LTE registration → PDP → NTP → LoRa → MQTTS. Main loop: `LoRa.parsePacket()` → `parseCsv()` → `plotForSubNode()` → `buildJson()` → `mqtt.publish()`. Auto-reconnect on modem or MQTT drop. |
| `firmware/main_node/README.md` | Flash + monitor commands, expected serial output, troubleshooting table, known limitations. |
| `firmware/sub_node/sub_node.ino` | ATmega328P production sketch. Reads DS18B20 + capacitive soil (with `rawToVwc` calibration) + battery + pressure + water flow (pulse-counted) + RS485 NPK (with Modbus CRC-16); prepends `NODE=<id>` from EEPROM to a CSV frame; transmits over LoRa. EC converted to mS/cm on-board. |
| `firmware/sub_node/eeprom_provisioner/eeprom_provisioner.ino` | One-time sketch that writes the Sub Node's ID to EEPROM address 0. Change the `NODE_ID` constant, upload, watch the serial read-back, then flash the production sketch. |
| `firmware/sub_node/README.md` | MiniCore board setup, DIP-28 pinout, two-step flash procedure, soil probe calibration walkthrough, CSV frame format, resource budget, troubleshooting. |
| `docs/SUB_NODE_FIRMWARE_CHANGES.md` | Archive of the three edits that took the teammate's original sketch to production shape (EEPROM `NODE_ID`, SOIL calibration, EC in mS/cm). Kept as a diff reference; the applied version is `firmware/sub_node/sub_node.ino`. |
