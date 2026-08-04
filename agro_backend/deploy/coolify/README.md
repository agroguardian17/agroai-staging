# Optional Coolify Deploy Runbook

> **Prerequisites:** AWS Lightsail VPS provisioned per [ACCOUNTS_TO_FILL.md](../../ACCOUNTS_TO_FILL.md) Tier 2 #5, with static IP attached and Lightsail Firewall open for TCP 22, 80, 443, 8883. Direct Compose deployment is the simpler, currently proven path; Coolify is optional.

This runbook turns a freshly provisioned Ubuntu 22.04 Lightsail instance into the production AgroGuardian backend, accessible at `https://api-<your-ip-with-dashes>.sslip.io`. Total time: ~90 minutes including waiting for Let's Encrypt.

For the direct VPS procedure, see [`../staging/README.md`](../staging/README.md). This file only covers the optional Coolify layer.

## Step-by-step

### 1. SSH in

```bash
ssh -i <PATH_TO_LIGHTSAIL_PRIVATE_KEY> ubuntu@<static-ip>
```

(Or use the "Connect using SSH" button in the Lightsail console for a browser terminal.)

### 2. Install Docker + Docker Compose Plugin

```bash
sudo hostnamectl set-hostname agro-prod-01
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl ca-certificates gnupg lsb-release jq
curl -fsSL https://get.docker.com | sudo bash
sudo usermod -aG docker $USER
newgrp docker
docker --version       # confirm 24.x or higher
docker compose version # confirm v2.x
```

### 3. Tailscale (for private admin access)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --advertise-tags=tag:vps
# Authorize via the URL printed
tailscale status      # confirm VPS appears in your tailnet
```

### 4. fail2ban + UFW

```bash
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban

sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8883
sudo ufw enable
```

**Reminder:** the Lightsail Console firewall must ALSO have rules for these ports — UFW alone is not enough. (See ACCOUNTS_TO_FILL.md Tier 2 #5.)

### 5. Install Coolify

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash
```

Visit `http://<static-ip>:8000` → create the admin account. Bookmark this URL; restrict to Tailscale once you're confident the instance is fine.

### 6. Render the production Caddyfile

On your **local machine** (or in CI):

```powershell
cd agro_backend
pwsh ./scripts/dev/render-caddyfile.ps1 -IP <static-ip>
```

This writes `deploy/caddy/Caddyfile.prod`. Run it from the repository directory;
do not run `make caddyfile-prod` from `~`. A real ACME email must be configured
in the Caddy template before deployment.

### 7. Connect Coolify to GitHub

In the Coolify UI:

1. **Sources** → Add a new GitHub source → use a Personal Access Token with `repo` (read) scope. (Or use a GitHub App — Coolify recommends apps over PATs.)
2. **Resources** → New Resource → Docker Compose → select your `agroguardian` repo, branch `main`, file `agro_backend/docker-compose.prod.yml`.
3. **Environment Variables** → paste the required keys from
   [`CONFIGURATION.md`](../../docs/CONFIGURATION.md). The values that came
   from the Tier 1/2 signups in `ACCOUNTS_TO_FILL.md` go in here. **Important:**
   also set `APP_GIT_SHA` to the deployment commit so `/health` reports it.
4. **Auto-deploy** → enable on push to `main`.
5. **Deploy** — first deploy takes ~5 minutes (image build + dependencies).

### 8. Verify Caddy issued Let's Encrypt

After Coolify reports "Running":

```bash
curl -v https://api-<your-ip-with-dashes>.sslip.io/api/v1/health
```

Expected: `HTTP/2 200`, JSON `{"status":"ok","version":"0.0.1","commit":"<sha>","env":"production"}`.

If Caddy fails to issue (rate limits or HTTP-01 challenge issues), check `docker compose -f docker-compose.prod.yml logs caddy` and verify ports 80 + 443 are open in **both** Lightsail Firewall and UFW.

### 9. Set up backups

The repository contains B2/R2 configuration seams but no completed backup
worker. Until a tested `pg_dump` + restore procedure is added, rely only on
Lightsail snapshots and treat them as insufficient for real farmer data.

### 10. Set up UptimeRobot

Create a HTTP(s) monitor pointing at the health URL above. Email + Telegram alert on `down`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `curl` from outside hangs | Lightsail Firewall closed | Console → Networking → IPv4 Firewall → add port |
| Caddy stuck issuing cert | Cloudflare proxy ON | Set DNS record to gray-cloud (Proxy: OFF) on first issuance |
| Coolify can't pull image | GitHub PAT expired or wrong scope | Regenerate PAT with `repo` scope |
| Postgres container restart loop | `POSTGRES_PASSWORD` unset | Coolify env vars must include this; restart resource |
| `/api/v1/ready` looks healthy while a dependency fails | Readiness is currently a phase-0 stub, not a real dependency probe | `docker compose ps`; check each container's logs |
| `mosquitto_sub` returns "Connection refused" | Lightsail Firewall missing TCP 8883 | Same fix as above |
| Tailscale ACL locks you out | Aggressive ACL change | Test changes from a 2nd device first |

## Migration to a new VPS (any provider)

Migration to a new VPS is a controlled operation:

1. Provision new Linux VPS, install Docker
2. `pg_dump --format=custom` on the current Lightsail
3. `tar czf chroma.tar.gz /data/chroma`
4. `scp` both to the new host; `pg_restore` and `tar xzf`
5. Update DNS (or `make caddyfile-prod IP=<new-ip>` for sslip.io)
6. Update Meta WhatsApp webhook callback URL
7. Update the firmware broker host configuration (or wait for the device's next reconnect)

Same procedure no matter the destination — DigitalOcean, Hetzner, Linode, EC2, or another Lightsail region.

## When you outgrow $20 plan (~100 farms)

- **Easy:** Lightsail Console → your instance → Plans → Resize to $40 (~5 min downtime)
- **Better long-term:** move to a larger provider-neutral compute/database arrangement after load and backup requirements justify it. The application intentionally avoids hard-coded AWS managed services.

The hexagon makes both mechanical, not architectural.

## Current Coolify limitation

`docker-compose.prod.yml` contains a Caddy route for `streamlit:8501`, but it
does not define a `streamlit` service. Deploying the compose file therefore
does not make the dashboard available unless a separate Streamlit service is
added and placed on the same Docker network. The API, MQTT, Postgres, Chroma,
Prometheus, and Grafana services are the currently defined production services.
