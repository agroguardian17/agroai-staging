# AgroGuardian V2 API reference

Base URL in development: `http://localhost:8000`.

The API prefix is `/api/v1`. JSON error bodies generally use a `detail` object with an `error` key. Production disables the interactive docs routes, but the same API routes remain available behind Caddy.

## Authentication

Protected routes require:

```http
Authorization: Bearer <access_token>
```

Access tokens default to 15 minutes. Refresh tokens default to 30 days and rotate on every successful refresh.

## Health and observability

### `GET /api/v1/health`

Unauthenticated liveness endpoint.

Example response:

```json
{
  "status": "ok",
  "version": "0.0.1",
  "commit": "dev",
  "env": "development"
}
```

### `GET /api/v1/ready`

Unauthenticated readiness-shaped response. The current implementation returns phase-0 stub checks; it does not actually ping the services yet.

```json
{
  "ready": true,
  "checks": [
    {"name": "postgres", "ok": true, "detail": "phase-0 stub"},
    {"name": "mosquitto", "ok": true, "detail": "phase-0 stub"},
    {"name": "chroma", "ok": true, "detail": "phase-0 stub"}
  ]
}
```

### `GET /metrics`

Prometheus exposition format. In production Caddy restricts this route to the Tailscale network.

## Authentication routes

### `POST /api/v1/auth/send_otp`

Request:

```json
{"phone": "+918123456789"}
```

The phone field is 8–16 characters and should be E.164. A successful request returns `202`:

```json
{
  "challenge_id": "uuid",
  "expires_at": "2026-07-25T12:00:00Z",
  "masked_phone": "*********6789"
}
```

The server also uses `202` for an unknown phone to avoid account enumeration. Active-challenge or rate-limit violations return `429`; a provider delivery failure returns `502`.

### `POST /api/v1/auth/verify_otp`

Request:

```json
{"phone": "+918123456789", "code": "123456"}
```

Successful response:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<opaque-secret>",
  "access_expires_at": "2026-07-25T12:15:00Z",
  "refresh_expires_at": "2026-08-24T12:00:00Z",
  "token_type": "bearer"
}
```

Errors: `400` for no active challenge, `401` for an invalid code, `403` for an inactive farmer, and `429` for a locked challenge.

### `POST /api/v1/auth/refresh`

Request:

```json
{"refresh_token": "<opaque-secret>"}
```

Returns a new token pair and revokes the presented refresh session. Invalid, expired, or revoked refresh tokens return `401`.

### `POST /api/v1/auth/logout`

Requires an access token.

Revoke one session:

```json
{"refresh_token": "<opaque-secret>"}
```

Revoke all sessions for the farmer:

```json
{"everywhere": true}
```

If `everywhere` is false, `refresh_token` is required. Response:

```json
{"revoked": 1}
```

### `GET /api/v1/me`

Requires an access token. Returns the identity encoded in the access token:

```json
{
  "farmer_id": "uuid",
  "tenant_id": "uuid",
  "role": "farmer",
  "session_id": "uuid"
}
```

## Plot and telemetry routes

All routes in this section require an access token. The plot list is farmer-scoped and staff roles are tenant-scoped. The current detail-route helper checks tenant membership for a farmer token; review that ownership check before using multiple farmers in the same tenant.

### `GET /api/v1/plots`

Returns visible plot metadata:

```json
[
  {
    "plot_id": "PLOT_PILOT_001",
    "farm_id": "uuid",
    "plot_number": 1,
    "plot_name": null,
    "area_acre": "1.0",
    "gps_lat": 19.9,
    "gps_lng": 75.7,
    "node_id": "AGR-SN-0001",
    "data_tier": "sensor",
    "plot_status": "active",
    "irrigation_valve_id": "V_001"
  }
]
```

### `GET /api/v1/plots/{plot_id}`

Returns one plot. Missing or unauthorized plots return the same `404` response.

### `GET /api/v1/plots/{plot_id}/readings?limit=50`

Returns newest-first readings. `limit` is 1–500 and defaults to 50. The response includes recorded time, moisture, root-zone temperature, pH, EC, battery values, cadence, validation warning, and low-battery flag.

### `GET /api/v1/plots/{plot_id}/alerts?limit=50`

Returns newest-first alerts for a plot. `limit` is 1–200 and defaults to 50. The response includes alert type, severity, Marathi message, trigger time, and resolution state.

### `GET /api/v1/plots/{plot_id}/suggestions?limit=50`

Returns newest-first persisted AI suggestions. `limit` is 1–200 and defaults to 50. The response exposes the Marathi message, model version, token count, crop age, and crop stage.

### `GET /api/v1/plots/{plot_id}/ginger_advisories?limit=50`

Same shape as `/suggestions`, filtered to rows where `ai_model_version = 'ginger-engine/v1.0'` — i.e. output from the daily ginger advisory job (`app/jobs/ginger_daily.py`). `limit` is 1–200 and defaults to 50.

Only relevant on plots where the active `crop_seasons.crop_name_english = 'Ginger'`. On non-ginger plots the response is an empty list. Use this endpoint from the dashboard's plot-detail page when you want to distinguish agronomic advisories (this endpoint) from device-health advisories (`/suggestions`).

## Operations alert routes

### `GET /api/v1/alerts`

Lists alerts for the caller's tenant.

Query parameters:

| Parameter | Values/default | Meaning |
| --- | --- | --- |
| `status` | `open` (default), `closed`, `all` | Unresolved, resolved, or both |
| `severity` | `info`, `warning`, `critical` | Optional severity filter |
| `limit` | 1–500, default 50 | Maximum rows |

Each row includes the alert ID/type/severity/message, trigger and resolution times, device/farm/farmer IDs, and optional actual/threshold values.

### `POST /api/v1/alerts/{alert_id}/resolve`

Request:

```json
{"notes": "Checked the battery and replaced the pack."}
```

The notes field is optional. A cross-tenant or missing alert returns `404`; an already resolved alert returns:

```json
{"alert_id": 42, "already_resolved": true}
```

A newly resolved alert returns:

```json
{"alert_id": 42, "resolved": true}
```

## Example curl flow in development

```bash
curl -s http://localhost:8000/api/v1/health

curl -s -X POST http://localhost:8000/api/v1/auth/send_otp \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+918123456789"}'

# Read the OTP from the log-only sender in development.
curl -s -X POST http://localhost:8000/api/v1/auth/verify_otp \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+918123456789","code":"123456"}'

curl -s http://localhost:8000/api/v1/plots \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
```
