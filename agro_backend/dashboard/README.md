# AgroGuardian — Internal Ops Dashboard

A team-internal Streamlit dashboard for watching the whole system: every table,
the advisory pipeline end-to-end, and live activity. It reads Postgres
**directly and read-only** (cross-tenant, no RLS session vars) so it can surface
everything without a farmer-facing endpoint per view.

> This is **not** the farmer app. It shows all tenants and all raw data, so it
> must sit behind auth (Caddy basic-auth in prod — see below).

## Pages
| Page | Shows |
|---|---|
| System overview (landing) | migration head, relation counts, headline metrics |
| System Health | ingest freshness, device last-seen, dead-letter queue, state machines |
| Data Explorer | **every** relation — row counts, recent rows, CSV export |
| Telemetry | Sub-Node + Main-Node + weather readings, charted |
| Advisory Pipeline | alert → compose → WhatsApp delivery → farmer reply funnel |
| Devices & Calibration | registry, calibration, installs, maintenance |
| Ginger Knowledge Base | the loaded rule engine (rules, fields, golden tests) |
| Farmers & Farms | tenants, farmers, farms, plots, seasons, billing |
| Live Activity | rolling event timeline, auto-refresh |

Most operational tables are empty until hardware and farmer activity flow — the
dashboard shows that plainly (empty-state notes), so it doubles as a
"what's-flowing-yet" board.

## Run locally

```bash
python3 -m venv .venv-dashboard && source .venv-dashboard/bin/activate
pip install -r dashboard/requirements.txt

# Point it at a database. Either a full URL:
export DASHBOARD_DATABASE_URL="postgresql+psycopg://agro:<pw>@localhost:5433/agro"
# ...or the standard pieces (host defaults to `postgres`, i.e. the compose net):
#   export POSTGRES_USER=agro POSTGRES_PASSWORD=<pw> PGHOST=localhost PGPORT=5433 POSTGRES_DB=agro

streamlit run dashboard/app.py      # opens http://localhost:8501
```

No JWT/OTP needed — it talks to Postgres, not the API. Every connection is
opened `default_transaction_read_only=on`, so the dashboard physically cannot
write.

## Run on the cloud (staging)

The dashboard ships as a compose service (`dashboard`, network alias
`streamlit`) that Caddy publishes at `https://dashboard-<IP-with-dashes>.sslip.io`
behind basic-auth. One-time setup on the VPS:

1. **Pick credentials and hash the password** (bcrypt):
   ```bash
   docker run --rm caddy:2.11.4-alpine caddy hash-password --plaintext 'a-strong-password'
   ```
2. **Add to `.env`** (the Caddy + dashboard containers read it):
   ```dotenv
   DASHBOARD_USER=ops
   DASHBOARD_PASSWORD_HASH=$2a$14$....the-hash-from-step-1....
   ```
3. **Re-render the Caddyfile and bring the stack up** (from the deploy dir):
   ```bash
   make caddyfile-prod IP=<STATIC_IP>
   docker compose -f docker-compose.prod.yml up -d --build dashboard caddy
   ```
4. Open `https://dashboard-<IP-with-dashes>.sslip.io` and log in.

The dashboard container connects to `postgres:5432` on the internal network with
the `POSTGRES_*` creds from `.env`; nothing new is exposed on the host firewall
(traffic goes through Caddy on 443).

> Prefer to keep it off the public internet entirely? Drop the `dashboard-*`
> site block into the Tailscale-gated pattern the Prometheus/Grafana blocks use,
> instead of basic-auth.
