# AgroGuardian Operations Dashboard

A small Streamlit app over the AgroGuardian read API. Three pages:

| Page | What it shows |
|---|---|
| Farmer Overview | All plots in the caller's scope, side-by-side cards |
| Plot Detail | Pick a plot from the sidebar; tabs for Readings (chart), Alerts, AI Advisories |
| Operations Queue | All alerts for the tenant, filterable, with Resolve buttons |

The dashboard never touches Postgres directly — every screen goes
through `/api/v1/*`. This means the dashboard works just as well from
another machine, behind Caddy, as it does on your laptop.

## One-time setup

```bash
# A separate venv keeps Streamlit's transitive deps out of the backend env.
python3 -m venv .venv-dashboard
source .venv-dashboard/bin/activate
pip install -r dashboard/requirements.txt
```

## Configure auth

Mint a JWT once via the API (the OTP flow lives in the backend at
`/api/v1/auth/send_otp` + `/api/v1/auth/verify_otp`):

```bash
# 1. Trigger an OTP. The code prints to the app log in development
#    (LogOnlyWhatsappSender only; never use that sender in production).
curl -X POST http://localhost:8000/api/v1/auth/send_otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"+91XXXXXXXXXX"}'

# 2. Read the code from the uvicorn log, then:
curl -X POST http://localhost:8000/api/v1/auth/verify_otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"+91XXXXXXXXXX","code":"123456"}'

# Copy the access_token from the response.
```

Export it (only the access token, not the refresh):

```bash
export ACCESS_TOKEN=eyJ...
# Optional - default is http://localhost:8000
export AGRO_API_BASE_URL=http://localhost:8000
```

## Launch

```bash
streamlit run dashboard/app.py
```

Open the URL Streamlit prints (default http://localhost:8501). The
welcome page shows your /me identity card; the sidebar lists the
three pages.

## Common gotchas

- **"ACCESS_TOKEN env var is missing"** — re-export the token in the
  shell that runs Streamlit. Streamlit's own auto-reload doesn't pick
  up env-var changes; restart `streamlit run` after exporting.
- **API 401** — the access token has expired (default 15 minutes).
  Re-run `/auth/verify_otp` (or `/auth/refresh` with the refresh
  token) and re-export.
- **Empty pages** — no data yet. Run `scripts/dev/fake_main_node.py` to seed
  readings. Alerts are created only when a fresh reading matches a pilot rule
  and `CALIBRATION_MODE=false`. Persisted AI suggestions require separate
  advisory-worker wiring; the current MQTT startup path does not create them
  automatically.

## What this round does NOT yet do

- **Live tail.** The dashboard fetches on page load + reruns; there is no
  WebSocket push or automatic polling. Refresh the Streamlit page to see new
  data; a future round can add SSE.
- **Acknowledge (vs resolve).** Round 12 only ships Resolve. An
  "Acknowledged but not closed" state would need a new column on
  `alerts_notifications`.
- **OTP login screen.** Static JWT only. Round 12.5 will swap the env
  var for an in-app OTP login form.
