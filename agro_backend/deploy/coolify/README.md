# Coolify Deploy Runbook

> **Prerequisites:** AWS Lightsail VPS provisioned per [ACCOUNTS_TO_FILL.md](../../ACCOUNTS_TO_FILL.md) Tier 2 #5, with static IP attached and Lightsail Firewall open for TCP 22, 80, 443, 8883.

This runbook turns a freshly provisioned Ubuntu 22.04 Lightsail instance into the production AgroGuardian backend, accessible at `https://api-<your-ip-with-dashes>.sslip.io`. Total time: ~90 minutes including waiting for Let's Encrypt.

For the verbatim, command-by-command version with explanatory commentary, see [Roadmap Part 12.2](../../../AgroGuardian_FINAL_Roadmap.md#122-setup-runbook--aws-lightsail-mumbai-one-time-90-min). This file is the operator-facing distillation.

## Step-by-step

### 1. SSH in

```bash
ssh -i ~/.ssh/agro_lightsail.pem ubuntu@<static-ip>
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

This writes `deploy/caddy/Caddyfile.prod`. Commit and push to `main`.

### 7. Connect Coolify to GitHub

In the Coolify UI:

1. **Sources** → Add a new GitHub source → use a Personal Access Token with `repo` (read) scope. (Or use a GitHub App — Coolify recommends apps over PATs.)
2. **Resources** → New Resource → Docker Compose → select your `agroguardian` repo, branch `main`, file `agro_backend/docker-compose.prod.yml`.
3. **Environment Variables** → paste each key from `.env.example`. The values that came from the Tier 1/2 signups in `ACCOUNTS_TO_FILL.md` go in here. **Important:** also set `APP_GIT_SHA` to `${SOURCE_COMMIT}` so the `/health` endpoint reports the deployed commit.
4. **Auto-deploy** → enable on push to `main`.
5. **Deploy** — first deploy takes ~5 minutes (image build + dependencies).

### 8. Verify Caddy issued Let's Encrypt

After Coolify reports "Running":

```bash
curl -v https://api-<your-ip-with-dashes>.sslip.io/api/v1/health
```

Expected: `HTTP/2 200`, JSON `{"status":"ok","version":"0.0.1","commit":"<sha>","env":"production"}`.

If Caddy fails to issue (rate limits or HTTP-01 challenge issues), check `docker compose -f docker-compose.prod.yml logs caddy` and verify ports 80 + 443 are open in **both** Lightsail Firewall and UFW.

### 9. Set up B2 backups

The repo already has the cron stub in [Phase 12.2 Prompt](../../../AgroGuardian_FINAL_Roadmap.md#prompt-122--backup--restore-drill); land that file in Phase 12. Until then, Lightsail's automatic snapshots provide a 7-day rolling recovery window.

### 10. Set up UptimeRobot

Create a HTTP(s) monitor pointing at the health URL above. Email + Telegram alert on `down`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `curl` from outside hangs | Lightsail Firewall closed | Console → Networking → IPv4 Firewall → add port |
| Caddy stuck issuing cert | Cloudflare proxy ON | Set DNS record to gray-cloud (Proxy: OFF) on first issuance |
| Coolify can't pull image | GitHub PAT expired or wrong scope | Regenerate PAT with `repo` scope |
| Postgres container restart loop | `POSTGRES_PASSWORD` unset | Coolify env vars must include this; restart resource |
| `/api/v1/ready` returns false | One of postgres/mosquitto/chroma not started | `docker compose ps`; check that container's logs |
| `mosquitto_sub` returns "Connection refused" | Lightsail Firewall missing TCP 8883 | Same fix as above |
| Tailscale ACL locks you out | Aggressive ACL change | Test changes from a 2nd device first |

## Migration to a new VPS (any provider)

Per [Roadmap Part 0.5 Rule 5](../../../AgroGuardian_FINAL_Roadmap.md#rule-5--two-hour-migration-procedure), migration is a 2-hour operation:

1. Provision new Linux VPS, install Docker
2. `pg_dump --format=custom` on the current Lightsail
3. `tar czf chroma.tar.gz /data/chroma`
4. `scp` both to the new host; `pg_restore` and `tar xzf`
5. Update DNS (or `make caddyfile-prod IP=<new-ip>` for sslip.io)
6. Update Meta WhatsApp webhook callback URL
7. Push a `cmd` MQTT message to refresh device broker hosts (or wait for next reconnect)

Same procedure no matter the destination — DigitalOcean, Hetzner, Linode, EC2, or another Lightsail region.

## When you outgrow $20 plan (~100 farms)

- **Easy:** Lightsail Console → your instance → Plans → Resize to $40 (~5 min downtime)
- **Better long-term:** Migrate to EC2 t3.large + RDS db.t3.medium (~2h via the procedure above; ~$120/mo)

The hexagon makes both mechanical, not architectural.
