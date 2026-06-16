# Accounts & Secrets — Fill-in Checklist

> **What this is:** every external account you need to sign up for, in priority order, with exactly which `.env` variable each generated value goes into.
>
> **Cost reality:** every account below has a free tier sufficient for the pilot. The only paid commitment in Phase 0 is the optional **AWS Lightsail $20/month** when you're ready to deploy to the cloud — for local development you don't need it.

Legend:
- ⏱ = signup/approval time
- 🔑 = where to paste the value (in `agro_backend/.env`)
- 💰 = cost during pilot

---

## Tier 0 — Right now, on your machine (no signups)

These three values are needed before you can `docker compose up`. **Generate them locally**:

```powershell
cd agro_backend
Copy-Item .env.example .env

# Generate three random 32-byte base64 strings
1..3 | ForEach-Object {
    $b = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($b)
    [Convert]::ToBase64String($b)
}
```

Paste the three lines printed into `.env`:

| `.env` key | Purpose |
|---|---|
| `POSTGRES_PASSWORD` | Postgres superuser password (`agro` user). Same string also referenced via `DATABASE_URL`. **Update both `DATABASE_URL` and `DATABASE_URL_SYNC`** to replace `CHANGE_ME` with this value. |
| `AUTH_JWT_SECRET` | Signs JWT access/refresh tokens. Rotate quarterly in production. |
| `MQTT_BROKER_PASSWORD` | Service account password for the MQTT broker. |

**Also pick a value for** `META_WHATSAPP_VERIFY_TOKEN` — any random string works (used to verify Meta's webhook callbacks). You can generate it with the same loop.

After this you can `docker compose -f docker-compose.dev.yml up -d` and hit `http://localhost:8000/api/v1/health`. ✅

---

## Tier 1 — This week (needed for Fast Path Days 7–11)

These take real time (24–48h approval in some cases). **Start now in parallel** while you build out Phases 1–4.

### 1. Anthropic (Claude Sonnet 4.6 + Haiku 4.5)

- **Signup:** <https://console.anthropic.com>
- ⏱ Instant
- 💰 Add **$20** of credit to start. Pilot consumption is ~$3/month on the Sonnet+Haiku mix.
- After login: Settings → API Keys → Create Key

🔑 **Paste into `.env`:**

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 2. WhatsApp Cloud API (Meta) — OTP + Advisory

- **Signup:** <https://developers.facebook.com> → Create App → Business → Add **WhatsApp** product.
- ⏱ App creation instant. **Template approval 24–48h.**
- 💰 Free during pilot (test mode = 1,000 free conversations/month).
- **Critical:** Submit **BOTH** templates in the same session:
  1. **Authentication template** — for OTP delivery. Name: `agroguardian_otp_v1`. Language: `mr` (Marathi). Use Meta's example template as starting point.
  2. **Utility template** — for advisory messages. Name: `agroguardian_advisory_v1`. Language: `mr`.
- Add your phone + 4 founder/farmer phones as **test recipients** (max 5 in test mode).
- Generate a **System User access token** (60-day) — *not* the temporary 24-hour token from the Quickstart panel. Find it under: Business Settings → Users → System users → Add → Generate token → select WhatsApp Business Management + WhatsApp Business Messaging.

🔑 **Paste into `.env`:**

```
META_WHATSAPP_PHONE_NUMBER_ID=...           # WhatsApp → API Setup → "Phone number ID"
META_WHATSAPP_BUSINESS_ACCOUNT_ID=...       # WhatsApp → API Setup → "WhatsApp Business Account ID"
META_WHATSAPP_TOKEN=EAAG...                 # the 60-day system user token
META_WHATSAPP_VERIFY_TOKEN=<your random string from Tier 0>
```

The two template names already match the values in `.env.example`; only override if you used different names in Meta.

### 3. NASA Earthdata (SMAP soil moisture)

- **Signup:** <https://urs.earthdata.nasa.gov/users/new>
- ⏱ 24-hour approval
- 💰 Free, forever
- After approval, log in → Profile → confirm your username & password work.

🔑 **Paste into `.env`:**

```
NASA_EARTHDATA_USERNAME=your-username
NASA_EARTHDATA_PASSWORD=your-password
```

### 4. Copernicus Data Space (Sentinel-2 imagery)

- **Signup:** <https://dataspace.copernicus.eu/>
- ⏱ Instant. Then go to: <https://shapps.dataspace.copernicus.eu/dashboard/#/account/settings> → OAuth clients → Create a new client.
- 💰 Free tier ~30,000 processing units/month — comfortably enough for 4 plots × daily ingest.

🔑 **Paste into `.env`:**

```
COPERNICUS_CLIENT_ID=...
COPERNICUS_CLIENT_SECRET=...
```

(The `COPERNICUS_BASE_URL` and `COPERNICUS_TOKEN_URL` are already set correctly in `.env.example`.)

---

## Tier 2 — Before you deploy to the cloud (Days 12–14)

Skip these until you're ready to push the prototype to AWS Lightsail. Local development doesn't need any of them.

### 5. AWS Lightsail (Mumbai)

- **Signup:** <https://lightsail.aws.amazon.com>
- ⏱ AWS account creation instant; Lightsail provisioning ~60 seconds
- 💰 **$20/month flat** — 2 vCPU / 4 GB RAM / 80 GB SSD / 3 TB egress, plus ~$4/month for automatic daily snapshots
- **First action after signup:** Console → Billing → Budgets → create email alert at **$30/month**. This is your safety net against surprise charges.
- Provision: Mumbai → Ubuntu 22.04 LTS → $20 plan → name `agro-prod-01` → upload your SSH public key → create
- Attach a static IP (free while attached): Networking tab → Create static IP → attach to instance
- **Open the Lightsail Firewall** (this is the #1 AWS gotcha — UFW alone is not enough):
  - Networking tab → IPv4 Firewall → add rules for TCP 22, 80, 443, **8883**
- Enable automatic snapshots: Snapshots tab → Enable → daily at 03:00 IST

No `.env` keys for Lightsail itself — by design (provider portability charter). The IP is plugged into Caddy via `make caddyfile-prod IP=<your-ip>`.

### 6. Cloudflare R2 (object storage — rasters, photos, firmware)

- **Signup:** <https://dash.cloudflare.com> → R2 → Create bucket
- ⏱ Instant
- 💰 Free tier: 10 GB storage, 1M class-A operations/month. Pilot uses < 1 GB.
- Create three buckets: `agro-rasters`, `agro-photos`, `agro-firmware`
- Generate an API token: R2 → "Manage R2 API Tokens" → Create token → grant Object Read & Write on those buckets
- Note your **Account ID** (top-right of the R2 dashboard)

🔑 **Paste into `.env`:**

```
R2_ACCOUNT_ID=<your account id>
R2_ACCESS_KEY_ID=<from token>
R2_SECRET_ACCESS_KEY=<from token>
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
```

### 7. Backblaze B2 (cold backups for Postgres weekly dumps)

- **Signup:** <https://www.backblaze.com/sign-up/cloud-storage>
- ⏱ Instant
- 💰 Free tier: 10 GB storage. Pilot uses ~100 MB.
- Create bucket: `agro-backups` (private)
- Create application key: Account → App Keys → Add a New Application Key → restrict to bucket `agro-backups`

🔑 **Paste into `.env`:**

```
B2_KEY_ID=<keyID>
B2_APPLICATION_KEY=<applicationKey>
B2_ENDPOINT_URL=https://s3.<region>.backblazeb2.com    # e.g. s3.us-west-001.backblazeb2.com
B2_BUCKET_BACKUPS=agro-backups
```

### 8. Sentry (error tracking) — optional but recommended

- **Signup:** <https://sentry.io>
- ⏱ Instant
- 💰 Developer plan free
- Create project: Python → FastAPI → copy the DSN

🔑 **Paste into `.env`:**

```
SENTRY_DSN=https://<key>@<org>.ingest.sentry.io/<project-id>
```

(Leave blank to disable Sentry — the app boots fine without it.)

### 9. Better Stack (log aggregation) — optional

- **Signup:** <https://betterstack.com> → Logs
- ⏱ Instant
- 💰 Free: 1 GB/month logs

🔑 **Paste into `.env`:**

```
BETTER_STACK_TOKEN=<source token>
```

(Leave blank to disable — logs still go to stdout.)

### 10. UptimeRobot (uptime pinger)

- **Signup:** <https://uptimerobot.com>
- ⏱ Instant
- 💰 Free: 50 monitors at 5-min interval
- Create a monitor: HTTP → `https://api-<your-ip-with-dashes>.sslip.io/api/v1/health` → 5-minute interval

No `.env` keys — UptimeRobot is configured entirely from its web dashboard.

### 11. Tailscale (private mesh for admin SSH + Grafana access)

- **Signup:** <https://login.tailscale.com>
- ⏱ Instant
- 💰 Free: 100 devices
- Install on your laptop and on the VPS (`curl -fsSL https://tailscale.com/install.sh | sh`)

No `.env` keys — Tailscale is OS-level.

### 12. Doppler (secrets manager — optional alternative to `.env`)

- **Signup:** <https://www.doppler.com>
- ⏱ Instant
- 💰 Free: unlimited secrets, 5 users

If you'd rather not maintain `.env` files manually, Doppler syncs secrets to environment variables. Optional — `.env` works fine for the pilot.

### 13. Firebase Cloud Messaging (push notifications)

- **Signup:** <https://console.firebase.google.com> → Add project
- ⏱ Instant
- 💰 Free for the pilot's volume
- Project Settings → Service accounts → Generate new private key → save as `secrets/fcm-sa.json`
- Mount that file into the container in `docker-compose.prod.yml` (or via Coolify secret store)

🔑 **Paste into `.env`:**

```
FCM_PROJECT_ID=<your-firebase-project-id>
FCM_SERVICE_ACCOUNT_JSON_PATH=/secrets/fcm-sa.json
```

### 14. GitHub repo + Coolify

- Create a private repo `agroguardian` (or any name) in your GitHub org
- On the Lightsail VPS, install Coolify: `curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash`
- Connect Coolify to GitHub via PAT (read-only on the private repo)
- Coolify auto-deploys on push to `main` from `docker-compose.prod.yml`

No `.env` keys — Coolify reads them from its own secret store, populated from the same `.env.example` template.

---

## Tier 3 — Post-pilot (Phases 13–14, do NOT block on these)

**Start the paperwork in parallel while the pilot ships, but the pilot does not depend on these.**

### Razorpay (Phase 14 — subscriptions)

- **Signup:** <https://dashboard.razorpay.com/signup>
- ⏱ KYC takes **5–7 days** (PAN, GST, business bank account, registered entity)
- 💰 2% per transaction (no monthly fee)
- Start the KYC paperwork **now** so it doesn't gate Phase 14 in three months.
- Pilot does not use Razorpay; the codebase intentionally has no `razorpay` SDK dependency.

### MSG91 + DLT registration (Phase 13 — SMS fallback)

- **DLT registration** with TRAI takes 7–10 days (Vilpower/Smartping/Jio Platforms). Start later — only matters when commercial launch needs SMS for non-WhatsApp farmers.

---

## Quick reality check

After you complete **Tier 0 + Tier 1** (≈ 30 minutes of clicking + 24–48h waiting for WhatsApp/Earthdata approval), you have everything needed to ship the **Day-14 working prototype** locally:

- Phase 0: ✅ already complete
- Phase 1: needs DB only (already on your machine via Docker)
- Phase 2: needs MQTT only (already on your machine via Docker)
- Phase 3: needs WhatsApp Cloud API (Tier 1 #2)
- Phase 5 (slimmed): needs Anthropic (Tier 1 #1)
- Phase 6 (deferred to weeks 3+): needs Copernicus + NASA (Tier 1 #3, #4)
- Phase 10 (slimmed): no extra accounts needed

**Tier 2 only matters when you're ready to deploy outside your laptop.** The Fast Path's Day-14 demo can run entirely against `localhost:8000`.

---

## What if I leave a value blank?

The app is designed to **boot with empty external secrets** in development. Specifically:

- No `ANTHROPIC_API_KEY` → AI advisory generation fails at runtime, but the rest of the API works.
- No WhatsApp creds → OTP request returns 503 with a clear log line; everything else works.
- No `SENTRY_DSN` → Sentry is silently disabled.
- No `BETTER_STACK_TOKEN` → logs only stream to stdout.
- No `R2_*` / `B2_*` → object storage operations fail; sensor ingest still works (those don't need storage).

**In production**, the `_assert_production_safe()` guard refuses to start with default/empty secrets for: `AUTH_JWT_SECRET`, `POSTGRES_PASSWORD`, `MQTT_BROKER_PASSWORD`, `ANTHROPIC_API_KEY`. This prevents accidental deploys with insecure defaults.

---

## Where to ask if something goes wrong

Each integration has a known set of failure modes documented in [Roadmap Part 9](../AgroGuardian_FINAL_Roadmap.md#part-9--common-failure-points). Common ones:

- WhatsApp template rejected on first submission → Part 9 #29 (language code, wording, button parameter)
- Copernicus rate limits silently truncating → Part 9 #27 (retry+backoff; cap concurrency)
- NASA Earthdata token expires every 60 days → Part 9 #28 (refresh script needed)
- Lightsail firewall vs UFW → Part 9 #36 (must open both)
- Lightsail static IP charges if detached → Part 9 #37 (delete it explicitly when retiring instance)

Read those before any integration goes live and you'll dodge the most common pitfalls.
