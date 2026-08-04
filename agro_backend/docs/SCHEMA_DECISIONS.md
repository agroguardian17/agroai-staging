# Schema Decisions — PDF Source vs. Roadmap v3 Requirements

This document records every reconciliation decision made when implementing the
Phase 1 database schema. There are two authoritative inputs:

1. **`Agro_Guardian_AI_Database_Schema 1.pdf`** — the 21-table / 400+ column
   "source" schema. Authoritative for **column names, data types, enums**.
2. **Historical `AgroGuardian_FINAL_Roadmap.md` design notes** — added the
   **v3 layer**: multi-tenancy,
   RLS, partitioning, audit logging, 14 additional tables, and specific column
   additions (Parts 2.2–2.8).

The roadmap/PDF artifacts are historical inputs from the original generation
process and are not present in this checkout. Where those inputs disagree or
the source is silent, the decision and its rationale are recorded here so they
can be reviewed and reversed cleanly.

---

## 1. Primary key types

The PDF mixes UUID and string-style IDs in its examples (e.g. `FARM_MH_001`,
`PLOT_001_Z1`, `AGR-MH-0042`). Roadmap Prompt 1.1 resolves this:

> "PKs are UUID v4 except where the schema doc uses a string ID (device_id, plot_id as TEXT)."

**Decision:**

| Entity | PK column | Type | Rationale |
|---|---|---|---|
| farmers | farmer_id | UUID | entity table |
| farms | farm_id | UUID | entity table |
| plots | plot_id | TEXT | roadmap explicitly TEXT; domain `Plot.plot_id: str` |
| crop_seasons | season_id | UUID | entity table |
| node_sensor_readings | reading_id | BIGINT IDENTITY | PDF BIGSERIAL; high-volume |
| weather_station_readings | weather_id | BIGINT IDENTITY | PDF BIGSERIAL |
| satellite_data | sat_id | BIGINT IDENTITY | PDF BIGSERIAL |
| weather_forecasts | forecast_id | BIGINT IDENTITY | PDF BIGSERIAL |
| electricity_schedule_log | elec_id | BIGINT IDENTITY | PDF BIGSERIAL |
| irrigation_events | irrigation_id | BIGINT IDENTITY | PDF BIGSERIAL |
| water_source_status | source_id | BIGINT IDENTITY | PDF BIGSERIAL |
| ai_suggestions | suggestion_id | UUID | entity table |
| farmer_actions | action_id | BIGINT IDENTITY | PDF BIGSERIAL |
| ai_learning_log | learning_id | BIGINT IDENTITY | PDF BIGSERIAL |
| device_registry | device_id | TEXT | roadmap explicitly TEXT |
| component_inventory | component_id | UUID | PDF UUID |
| technician_installations | installation_id | UUID | PDF UUID |
| service_maintenance | service_id | UUID | PDF UUID |
| alerts_notifications | alert_id | BIGINT IDENTITY | PDF BIGSERIAL |
| subscriptions_billing | subscription_id | UUID | PDF UUID |
| product_performance_bi | perf_id | BIGINT IDENTITY | PDF BIGSERIAL |

`node_id` and `master_node_id` are TEXT foreign keys to `device_registry.device_id`.

UUID defaults use `gen_random_uuid()` (Postgres 13+ core function — no extension
needed, so table creation in 0001 does not depend on the extensions migration 0003).

---

## 2. Multi-tenancy (the biggest v3 patch)

The PDF has **no `tenant_id` column anywhere**. The roadmap mandates
(`.cursorrules` #7, Part 2.8):

> "every tenant-scoped table has tenant_id UUID NOT NULL with RLS enabled."

**Decision:** add `tenant_id UUID NOT NULL REFERENCES tenants(id)` to every
business table. The `tenants` table is created **first** in 0001 so all FKs
resolve. The pilot tenant row is seeded in 0002.

Tables that receive `tenant_id`: all 21 source tables, plus v3 tables
`otp_codes` (nullable — pre-auth), `refresh_tokens`, `chat_messages`,
`calibration_history`, `wa_inbound_log`, `notification_dispatch_log`,
`notification_dlq`, `ingest_unmatched`, `feature_flags`.

Tables WITHOUT `tenant_id` (global): `tenants`, `users` (cross-tenant staff),
`audit_log` (records actor + table, global), `event_outbox` (global),
`system_config` (global).

---

## 3. Enums → TEXT + CHECK

Per `.cursorrules` and roadmap Prompt 1.1, all PDF `ENUM` columns become
`TEXT` + `CHECK (col IN (...))`. This avoids Postgres native ENUM types, which
are painful to alter. Every enum's allowed values are taken verbatim from the
PDF.

---

## 4. Time-series partitioning (roadmap 0005)

Roadmap 0005 partitions `node_sensor_readings`, `weather_station_readings`,
`weather_forecasts` by `RANGE (recorded_at)`, monthly, 13 months pre-created.

**Problem:** `weather_forecasts` has no `recorded_at` in the PDF (it has
`fetched_at` and `forecast_for_date`).

**Decision:**
- `node_sensor_readings` → partition by `recorded_at` ✓ (column exists)
- `weather_station_readings` → partition by `recorded_at` ✓ (column exists)
- `weather_forecasts` → partition by **`fetched_at`** (the semantic
  "recorded_at" for a forecast row — when we recorded it). Documented deviation.

Postgres requires the partition key in every UNIQUE/PK. Therefore:
- `node_sensor_readings`: PK `(reading_id, recorded_at)`, UNIQUE `(node_id, recorded_at)` (idempotency).
- `weather_station_readings`: PK `(weather_id, recorded_at)`, UNIQUE `(master_node_id, recorded_at)`.
- `weather_forecasts`: PK `(forecast_id, fetched_at)`, plus a non-unique index
  on `(farm_id, forecast_for_date, forecast_hour)` for lookups. Idempotent
  re-fetch is handled at the application layer in Phase 6 (delete-then-insert
  per fetch batch), since a cross-partition unique on the forecast target is
  not possible when partitioning by `fetched_at`.

`satellite_data` is **not** partitioned (1–2 rows/week; PDF retention "forever"
for indices). Plain table.

---

## 5. v3 column additions (roadmap Part 2.4)

Added on top of the PDF columns:

| Table | Added columns | Migration |
|---|---|---|
| farmers | `phone_hash BYTEA`, `phone_encrypted BYTEA` | 0002 |
| crop_seasons | `sowing_date_inferred BOOLEAN DEFAULT FALSE` | 0002 |
| device_registry | `broker_secret_hash TEXT`, `calibration_json JSONB DEFAULT '{}'` | 0002 |
| ai_suggestions | `prompt_template_version TEXT`, `llm_cost_inr NUMERIC(10,4)`, review columns (see §6) | 0002 |
| plots | `data_tier TEXT NOT NULL DEFAULT 'satellite_only'` | 0004 |
| node_sensor_readings | `soil_temp_rootzone_c`, `soil_n_bucket/p/k SMALLINT`, `cadence_mode TEXT CHECK`, `backlog_pending`, `validation_warn`, `low_battery_flag` | 0005 (during partition rebuild) |
| tenants | `tier TEXT CHECK`, `features JSONB` | 0002 |

PDF `ai_suggestions` already contains `ai_model_version` and `tokens_used`, so
those are **not** re-added (avoids duplicate-column errors). Only
`prompt_template_version` and `llm_cost_inr` are new.

---

## 6. ai_suggestions review columns

Roadmap 0008 references an `ai_suggestions_review` RLS policy and a trigger
"that rejects changes outside review_* columns" (agronomist queue, Phase 10).
The PDF has no review columns. **Decision:** add in 0002:

- `confidence_score NUMERIC(4,3)` — 0..1 confidence (Phase 5)
- `confidence_band TEXT CHECK (... IN ('autosend','autosend_caveat','queue','block'))`
- `review_status TEXT NOT NULL DEFAULT 'none' CHECK (... IN ('none','pending','approved','rejected','edited'))`
- `reviewed_by UUID` (FK users.user_id, nullable)
- `reviewed_at TIMESTAMPTZ`
- `review_notes TEXT`

These are the only columns the agronomist BEFORE-UPDATE trigger permits a
non-admin agronomist to change.

---

## 7. GPS boundaries: JSONB, not PostGIS geometry

The PDF stores `gps_boundary_geojson` as **JSONB** on `farms` and `plots`.
Roadmap Phase 6 mentions `ST_GeomFromGeoJSON` (PostGIS). **Decision:** keep
JSONB per the PDF for Phase 1. The PostGIS extension is created in 0003 for
later use; if spatial indexing is needed, Phase 6 can add a generated
`geometry(POLYGON, 4326)` column derived from the JSONB. No geometry columns
in Phase 1 — this keeps the ORM free of geoalchemy2 typing complexity for now.

---

## 8. Audit log target tables

Roadmap Part 8 #8 lists the master tables that get audit triggers:
`farmers, farms, plots, crop_seasons, device_registry, subscriptions_billing,
users, tenants, calibration_history`. The trigger reads
`current_setting('app.current_user_role', true)` and
`current_setting('app.current_user_id', true)` and writes OLD/NEW JSONB to
`audit_log`. Implemented in 0007.

---

## 9. Materialized views (roadmap 0006 / §2.5)

Four views with per-row UNIQUE indexes (required for `REFRESH ... CONCURRENTLY`):

- `node_readings_hourly` — avg/min/max of moisture, temp, ph, ec, n/p/k per
  `(tenant_id, plot_id, node_id, bucket_hour)`
- `node_readings_daily` — same, per day
- `weather_hourly` — avg temp/humidity/rain/wind per `(tenant_id, farm_id, bucket_hour)`
- `weather_daily` — same, per day

Column choices are derived from the PDF reading/weather tables. Documented in
the migration.

---

## 10. Roles

0008 creates `authenticated_role NOLOGIN` (the role intended for
farmer/staff requests, subject to RLS) and `service_role NOLOGIN BYPASSRLS`
(ingest + cron). The migration grants both roles to the current login role,
but the current FastAPI dependency layer does not yet set the per-request
session GUCs or switch roles. Application-level repository scoping is the
active protection today; treat the database RLS layer as defense in depth until
that session wiring is implemented.

---

## 11. Things intentionally deferred

- `users.tenant_id`: users are cross-tenant staff (admin/agronomist/technician);
  RLS for staff is role-based, not tenant-scoped. No `tenant_id` on `users`.
- `subscriptions_billing` stays empty in pilot (`pilot_internal` tier). Table
  and columns exist per PDF + minimal v3 additions, but no Razorpay wiring.
- Vector columns (pgvector): extension created; no vector columns until a phase
  needs them (RAG uses ChromaDB, not pgvector, in the pilot).

---

## 11b. Identifiers beginning with a digit

SQL identifiers cannot start with a digit. The PDF columns `4g_signal_strength`
(device_registry) and `4g_signal_tested` / `4g_signal_result`
(technician_installations) are renamed to `signal_4g_strength`,
`signal_4g_tested`, `signal_4g_result`.

---

## 11c. Non-immutable index predicate fix

Roadmap §2.6 defines:

```sql
CREATE INDEX otp_codes_phone_unverified ON otp_codes (phone_e164, created_at DESC)
  WHERE verified_at IS NULL AND expires_at > now();
```

Postgres rejects `now()` in a partial-index predicate (functions in index
predicates must be IMMUTABLE). **Decision:** drop the `expires_at > now()`
clause; the index predicate is `WHERE verified_at IS NULL`. Expiry is filtered
at query time in the auth code.

## 11d. dispatch_status on alerts_notifications

Roadmap §2.6 references `alerts_notifications.dispatch_status` (partial index
`alerts_notifications_pending`), but the PDF has no such column. **Decision:**
add `dispatch_status TEXT NOT NULL DEFAULT 'pending' CHECK (... IN
('pending','sent','failed','dlq'))` in 0002. The PDF's `whatsapp_sent` /
`sms_sent` booleans are kept; `dispatch_status` is the v3 dispatch state machine
used by the notification pipeline (Phase 8).

## 11e. The 35-table count

Total = 35 = 21 (PDF) + 14 (v3). The 14 v3 tables are: `tenants` (created in
0001) plus the 13 created in 0002 (`users`, `otp_codes`, `refresh_tokens`,
`audit_log`, `notification_dispatch_log`, `notification_dlq`,
`ingest_unmatched`, `event_outbox`, `feature_flags`, `system_config`,
`chat_messages`, `calibration_history`, `wa_inbound_log`). There is no
`prompt_templates` table — `ai_suggestions.prompt_template_version` is a plain
version string for replay traceability.

---

## 11f. node_sensor_readings v3 columns + cadence_mode values

Added during the 0005 partition rebuild (Part 2.4): `soil_temp_rootzone_c REAL`,
`soil_n_bucket / soil_p_bucket / soil_k_bucket SMALLINT`, `backlog_pending`,
`validation_warn`, `low_battery_flag` BOOLEAN, and `cadence_mode TEXT CHECK`.

The roadmap specifies `cadence_mode TEXT CHECK (...)` but not the value set
(it lives in the unavailable technical ref). **Decision (inferred):**
`CHECK (cadence_mode IN ('normal','rapid','low_power','storm','maintenance'))`.
Adjust the CHECK in 0005 if the technical ref defines different modes.

## 11g. 0005 assumes empty time-series tables

0005 DROPs and re-creates `node_sensor_readings`, `weather_station_readings`,
`weather_forecasts` as range-partitioned tables. This is safe because these
tables are empty during initial schema setup (0001–0008 applied together to a
fresh DB) and nothing has inbound FKs to them. If you ever re-partition a
populated table, write a dedicated data-copy migration instead.

13 monthly child partitions are created per table (current month + 12 forward),
matching the roadmap's verification (`pg_inherits` count = 13).

---

## 11h. RLS correctness fixes over the roadmap template

The roadmap §2.8 / Prompt 1.5 template has three issues fixed in 0008:

1. **`tenant_iso` must be RESTRICTIVE.** Postgres OR's permissive policies per
   command. A permissive `tenant_iso` would let any in-tenant row through
   regardless of the ownership/read policy. 0008 declares `tenant_iso AS
   RESTRICTIVE FOR ALL`, so it is AND'd with the permissive read/write policies.
2. **`FOR INSERT, UPDATE, DELETE` is invalid SQL.** `CREATE POLICY ... FOR`
   accepts exactly one command. 0008 emits three separate write policies
   (`_ins` / `_upd` / `_del`), each restricted to `('admin','technician')`.
3. **Ownership for tables without `farmer_id`.** The template's `plots_read`
   uses `farmer_id`, but `plots` has only `farm_id`. 0008 groups tables:
   - *farmer-owned* (have `farmer_id`): `farmer_id = current_farmer_id`.
   - *farm-owned* (have `farm_id` only): `farm_id IN (SELECT farm_id FROM farms)`
     — the `farms` RLS already narrows to the farmer's farms.
   - *staff-only* (`component_inventory`, ops/notification tables): farmers get
     no rows; only staff roles read.

`tenants`, `users`, `audit_log`, `system_config` are **not** RLS-enabled
(global/staff). Grants to `authenticated_role` are scoped to the tenant tables +
views only — never `users` (password hashes) or `audit_log`. `service_role` is
`BYPASSRLS` and gets `ALL`. The migration also `GRANT`s both roles to the
current login role so the app can `SET ROLE` into them.

## 11i. ai_suggestions agronomist review guard

0008 adds `ai_suggestions_review` (UPDATE policy for `agronomist`) plus a
BEFORE UPDATE trigger `ai_suggestions_review_guard` that raises if an agronomist
changes any column other than `review_status`, `reviewed_by`, `reviewed_at`,
`review_notes`.

---

## 12. Verification status

The migration chain is currently deployed through `0009_auth_otp_tables` in
the pilot VPS. Keep verifying a fresh database with `alembic upgrade head` and
an explicit downgrade/upgrade drill before trusting a new migration. Do not
infer migration health from ORM import success: the migrations are hand-written
SQL and include partitions, materialized views, triggers, roles, and RLS.
