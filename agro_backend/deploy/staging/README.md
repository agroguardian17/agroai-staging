# AgroGuardian Staging Deploy — Trimmed Round 15

> **Purpose:** stand up a Lightsail Mumbai VPS quickly so hardware has a real endpoint to publish to. No Coolify, no domain, no backups yet — that's full Round 15.
> **Runtime:** ~40 minutes end-to-end.
> **Prereqs:** AWS account, Anthropic API key (optional for the pure ingest test).

## Step 1 — Provision the Lightsail instance (5 min)

- Lightsail console → **Create instance** → **Mumbai (ap-south-1)** → **Linux/Unix** → **OS Only** → **Ubuntu 22.04 LTS** → **$20/month** (`medium_2_0`, 2 vCPU, 4 GB RAM, 80 GB SSD, 3 TB egress).
- Instance name: `agro-staging-01`.
- Once running: **Networking → Attach static IP** so the IP survives reboots.
- **Networking → Firewall**, open the following:

  | Port | Purpose |
  | :---: | :--- |
  | 22 | SSH |
  | 80 | Let's Encrypt HTTP-01 challenge (Caddy redirects to 443) |
  | 443 | HTTPS API |
  | 8883 | MQTTS from hardware |

- Note the static IP. From now on `<STATIC_IP>` refers to this address, and `<IP_DASHES>` is the same IP with dots replaced by dashes (used for sslip.io).

## Step 2 — Base OS setup (10 min)

SSH in:

```bash
ssh -i ~/.ssh/agro_lightsail.pem ubuntu@<STATIC_IP>
```

Base packages + Docker + UFW:

```bash
sudo hostnamectl set-hostname agro-staging-01
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl ca-certificates gnupg jq ufw fail2ban git
curl -fsSL https://get.docker.com | sudo bash
sudo usermod -aG docker $USER
newgrp docker

sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8883
sudo ufw enable

sudo systemctl enable --now fail2ban
```

## Step 3 — Clone + configure (5 min)

```bash
cd ~
git clone <your-fork-url> agro_backend
cd agro_backend
cp .env.example .env
```

Edit `.env` — the fields that matter for staging:

```dotenv
APP_ENV=staging
APP_VERSION=0.0.1

# Postgres — generate a strong password; do NOT reuse dev's
POSTGRES_USER=agro
POSTGRES_PASSWORD=<generated>
POSTGRES_DB=agro
DATABASE_URL=postgresql+asyncpg://agro:<generated>@postgres:5432/agro
DATABASE_URL_SYNC=postgresql://agro:<generated>@postgres:5432/agro

# JWT — 32+ random bytes, never CHANGE_ME
AUTH_JWT_SECRET=<openssl rand -hex 32>

# MQTT — backend reaches the internal listener; hardware reaches Caddy on 8883
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=1883
MQTT_BROKER_USER=main-node-001
MQTT_BROKER_PASSWORD=<generated>
MQTT_USE_TLS=true
MQTT_TLS_CA_PATH=/etc/ssl/certs/ca-certificates.crt

# Hardware bench: rules OFF until sensors are calibrated
CALIBRATION_MODE=true

# Anthropic is not required for this staging ingest test.
# ANTHROPIC_API_KEY=
```

## Step 4 — Render the Caddyfile for sslip.io (2 min)

```bash
make caddyfile-prod IP=<STATIC_IP>
```

This produces `deploy/caddy/Caddyfile.prod` with `api-<IP_DASHES>.sslip.io` and `mqtts-<IP_DASHES>.sslip.io` hosts. sslip.io serves those hostnames as A-records to `<STATIC_IP>` automatically — no DNS registrar needed.

The production Compose file builds the Caddy image with the Layer-4 plugin, mounts this rendered file, terminates TLS on public port `8883`, and forwards raw MQTT to Mosquitto's authenticated internal port `1883`. Do not replace the rendered file with the template before starting the stack.

## Step 5 — Start the stack (5 min)

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f app | head -40
```

You should see:

```
{"event":"app.startup","env":"staging","calibration_mode":true, ...}
{"event":"ingest_startup.started","host":"mosquitto","port":8883,"tls":true, ...}
{"event":"ingest_broker.started", ...}
{"event":"ingest_broker.subscribed","topic":"agro/v2/+/+/+/telemetry","qos":1}
```

If any of those are missing, `Ctrl-C` and inspect `docker compose -f docker-compose.prod.yml logs caddy mosquitto app`. The backend should connect to `mosquitto:1883`; only the external hardware/laptop connection uses TLS on `8883`.

## Step 6 — Migrate + seed (2 min)

```bash
docker compose -f docker-compose.prod.yml exec app alembic upgrade head
docker compose -f docker-compose.prod.yml exec -e PILOT_PHONE=+91XXXXXXXXXX \
    app python scripts/dev/seed_pilot.py
```

Save the Main Node ID (`AGR-MN-0001`) and Sub Node IDs (`AGR-SN-0001`, `AGR-SN-0002`) that get printed.

## Step 7 — Provision the Main Node's MQTT credential (2 min)

```bash
./scripts/dev/provision_mqtt_credential.sh main-node-001 <STRONG_PASSWORD>
docker compose -f docker-compose.prod.yml restart mosquitto
```

The same password goes into `.env` as `MQTT_BROKER_PASSWORD` **and** into the Main Node firmware's config. The backend and firmware use the *same* credential — the backend is a subscriber, the firmware is a publisher, but Mosquitto's ACL grants read+write on `agro/v2/#` to the shared user for simplicity in staging.

## Step 8 — Smoke test (5 min)

From your laptop, run `mosquitto_pub` with the minimal payload from `docs/HARDWARE_WIRE_CONTRACT.md` §7.1, aimed at the staging broker over TLS:

```bash
mosquitto_pub \
  -h mqtts-<IP_DASHES>.sslip.io -p 8883 \
  --capath /etc/ssl/certs \
  -u main-node-001 -P '<STRONG_PASSWORD>' \
  -t 'agro/v2/11111111-1111-1111-1111-111111111111/bbbbbbbb-2222-2222-2222-222222222222/AGR-SN-0001/telemetry' \
  -m '{"$schema":"agro-guardian/telemetry/v2","tenant_id":"11111111-1111-1111-1111-111111111111","farmer_id":"aaaaaaaa-1111-1111-1111-111111111111","farm_id":"bbbbbbbb-2222-2222-2222-222222222222","plot_id":"PLOT_PILOT_001","node_id":"AGR-SN-0001","recorded_at":"2026-07-21T13:12:00+00:00","received_at_master":"2026-07-21T13:12:00+00:00","transmission_type":"lora","soil_moisture_avg_pct":42.15}'
```

In another terminal, tail the ingest events:

```bash
docker compose -f docker-compose.prod.yml logs -f app | python scripts/dev/tail_ingest.py
```

Look for:

```
ingest_broker.subscribed topic='agro/v2/+/+/+/telemetry'
```

...followed by an event confirming the row landed. Check the database:

```bash
docker compose -f docker-compose.prod.yml exec postgres \
    psql -U agro -d agro -c \
    "SELECT node_id, plot_id, recorded_at, soil_moisture_avg_pct FROM node_sensor_readings ORDER BY recorded_at DESC LIMIT 5;"
```

## Step 9 — Point the Main Node at staging (firmware round)

Firmware config:

```
MQTT_HOST     = "mqtts-<IP_DASHES>.sslip.io"
MQTT_PORT     = 8883
MQTT_USER     = "main-node-001"
MQTT_PASSWORD = "<STRONG_PASSWORD>"
MQTT_USE_TLS  = true
```

The firmware skeleton (PlatformIO C++) ships in the follow-up bootstrap.

## What's NOT included in this trimmed staging (add for full Round 15)

- Coolify (a UI over docker-compose — nice, not necessary).
- Nightly `pg_dump | zstd | aws s3 cp` to Cloudflare R2. Add before real farmer data flows.
- Tailscale for private `/metrics`. Add before the pilot is publicly announced.
- A real domain (right now sslip.io serves the IP verbatim).
- Sentry DSN + BetterStack Uptime pinger.

Everything above is a `docker compose` restart or a single script — add it after hardware validates.
