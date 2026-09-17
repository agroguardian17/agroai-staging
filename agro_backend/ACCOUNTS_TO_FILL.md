# Accounts & Secrets — Fill-in Checklist

> **What this is:** every external account you may need, in priority order, with the exact
> click-path to get each value and the exact `.env` variable it belongs to. For the *runtime
> meaning* of each variable, see [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md). For what to *do*
> after pasting values (restart which service, how to verify it worked), see
> [`PILOT_READINESS.md`](PILOT_READINESS.md).
>
> **Cost reality:** every account below has a free tier sufficient for the pilot. The only paid
> commitments are **Anthropic (~$3–20)** and, when you deploy to the cloud, the **VPS (~$20/month)**.

Legend: ⏱ = signup/approval time · 🔑 = where the value goes in `agro_backend/.env` · 💰 = cost during pilot

> **How to edit `.env` safely (read this once):**
> - Values with a `$` in them (some bcrypt hashes, some tokens) must be **single-quoted** or the `$` doubled to `$$`, or `docker compose` will try to expand them. Example: `DASHBOARD_PASSWORD_HASH='$2a$14$....'`.
> - No spaces around `=`. No quotes needed for ordinary values.
> - Never commit `.env`. It's git-ignored; keep it that way.
> - After editing, apply with `docker compose -f docker-compose.prod.yml up -d <service>` (usually `app`). See PILOT_READINESS §3 for which service each value needs.

---

## Tier 0 — Right now, on your machine (no signups)

Four values must exist before `docker compose up`. **Generate them locally** — they are secrets,
not accounts.

**macOS / Linux:**
```bash
cd agro_backend
cp .env.example .env
# print four independent 32-byte base64 secrets:
for i in 1 2 3 4; do openssl rand -base64 32; done
```
**Windows PowerShell:**
```powershell
cd agro_backend
Copy-Item .env.example .env
1..4 | ForEach-Object {
    $b = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($b)
    [Convert]::ToBase64String($b)
}
```

Paste the four printed lines into `.env`:

| `.env` key | Purpose | Notes |
|---|---|---|
| `POSTGRES_PASSWORD` | Postgres password for the `agro` user | **Also** replace `CHANGE_ME` inside **both** `DATABASE_URL` and `DATABASE_URL_SYNC` with this same value, or the app can't connect. |
| `AUTH_JWT_SECRET` | Signs JWT access/refresh tokens | Changing it later logs everyone out. Rotate quarterly in prod. |
| `MQTT_BROKER_PASSWORD` | MQTT broker service-account password | Must also match the broker's password file (`deploy/mosquitto/`). |
| `META_WHATSAPP_VERIFY_TOKEN` | Random string Meta echoes back during webhook verification | You'll type the *same* string into Meta's webhook form later (Tier 1 #2 / PILOT_READINESS §3 B3). |

> The production boot guard (`_assert_production_safe` in `app/config.py`) **refuses to start** if
> `AUTH_JWT_SECRET`, `POSTGRES_PASSWORD`, `MQTT_BROKER_PASSWORD`, or `ANTHROPIC_API_KEY` is left at a
> default/empty value. So these aren't optional in prod.

After this you can `docker compose -f docker-compose.dev.yml up -d` and hit
`http://localhost:8000/api/v1/health` → expect `{"status":"ok",...}`. ✅

---

## Tier 1 — This week (start now; some have approval waits)

### 1. Anthropic (Claude Sonnet + Haiku) — the AI advisory brain

**Why:** without this, advisories run in log-only stub mode (and prod refuses to boot).
⏱ Instant · 💰 add **$20** credit; pilot burn ≈ $3/month.

**Step by step:**
1. Go to <https://console.anthropic.com> and sign in (or sign up).
2. Top-right → **Settings** (gear) → **Billing** → **Add credits** → add **$20**. (No credit = 400 errors at advisory time.)
3. Left nav → **API Keys** → **Create Key**. Name it `agroguardian-prod`. Click **Create**.
4. **Copy the `sk-ant-...` value immediately** — the console shows the full key exactly once. If you lose it, delete and recreate.

🔑 **Paste into `.env`:**
```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxx
```
Leave the model ids as shipped (`ANTHROPIC_MODEL_SONNET=claude-sonnet-4-5`,
`ANTHROPIC_MODEL_HAIKU=claude-haiku-4-5`) — the `ModelRole` layer resolves PRIMARY→Sonnet,
TRIAGE→Haiku from these.

**Verify:** PILOT_READINESS §3 A5 (a real Marathi suggestion appears in `ai_suggestions`).

---

### 2. WhatsApp Cloud API (Meta) — advisory delivery + inbound replies (OTP is optional/deferred)

**Why:** the channel that reaches farmers. This is the **longest pole** (template approval 24–48h)
— start it **today**. ⏱ App creation instant; **template approval 24–48h**. 💰 Free in test mode
(1,000 conversations/month, up to 5 test recipients).

**Only ONE template is required for the pilot** — the advisory template. The OTP template is for a
future farmer-login flow and is **not on the pilot critical path** — skip it if it gives you trouble
(see the Authentication-category note in 2d).

The backend expects specific template shapes, so build them exactly as below:
- **Advisory** template (required) = **body-only**; the whole Marathi message is passed as `{{1}}`.
- **OTP** template (optional) = **Authentication type**; Meta auto-adds the copy-code button the OTP sender needs.

#### 2a. Create the app and add WhatsApp
1. Go to <https://developers.facebook.com>, log in, → **My Apps** → **Create App**.
2. Use case: choose the **"Connect with customers through WhatsApp"** use case (or **Other → Business**) → name it `agro-app` → select your Business portfolio (create one if prompted) → **Create app**.
3. This auto-provisions a **Test WhatsApp Business Account (Test WABA)** + a **test phone number**. See the Test-WABA note below for what it can and can't do.

> ### ⚠️ Test WABA — what works, what doesn't (verified 2026-09-16)
> The WhatsApp use case creates a **"Test WhatsApp Business Account."** Real behavior we confirmed:
> - ✅ **Sends** pre-approved samples (`hello_world`, `jaspers_market_*`) to your 5 test recipients.
> - ✅ **Creates your own non-Authentication templates** — the **advisory** template (Marketing/Utility) was created and went **Active** on the Test WABA. So you can build and test the advisory pilot on the test number *now*.
> - ❌ **Rejects Authentication-category templates** (the OTP one) with *"does not have permission to create message template"* — Authentication templates are gated behind **business verification**. This is category-specific, not a blanket block.
>
> **What still needs a real (production) WABA:** sending to **real (non-test) farmers**, and creating
> the **OTP/Authentication** template. A real WABA needs a **registerable phone number** (a spare SIM,
> or a landline/VoIP that can take a *voice call* — Meta offers "call me" verification, so SMS isn't
> required; the number must **not** already be on the consumer WhatsApp app).
>
> **So for a technical dry-run right now (no real WABA/number):** use your created advisory template
> (or `hello_world`) and send from the test number to your own phone to prove the whole outbound path
> (token → send → `wamid` → status webhook). See PILOT_READINESS §3 B0.

#### 2b. Grab the IDs (new "use cases" layout)
The current Meta UI hides WhatsApp under **Use cases**, not a top-level nav item:
1. App dashboard → left nav **Use cases** → **Connect with customers through WhatsApp** → **Customize**.
2. In the WhatsApp submenu → **API Setup** (may be labeled **Configuration** / **Quickstart**).
3. Copy **Phone number ID** (a long number, *not* the phone number itself) → `META_WHATSAPP_PHONE_NUMBER_ID`.
4. Copy **WhatsApp Business Account ID** → `META_WHATSAPP_BUSINESS_ACCOUNT_ID`.

**Fallback (if you can't find API Setup):** the IDs also live in **WhatsApp Manager**
(business.facebook.com/wa/manage/) → **Account tools → Phone numbers** (Phone number ID) and
**Overview** (WABA ID). Note: the `business_id=...` in the URL is your *business portfolio* ID — a
different thing, not the WABA ID.

#### 2c. Add test recipients (test mode caps at 5)
1. On **API Setup**, under the "To" field → **Manage phone number list** → add your phone + up to 4 farmer/founder phones (E.164, e.g. `+9181234...`).
2. Each recipient gets a WhatsApp confirmation they must accept on their handset. **They won't receive anything until they accept.**
3. Store these same numbers as `farmers.phone` in the DB in **E.164 with `+91`** — that's what inbound replies match against.

#### 2d. Create the templates (WhatsApp Manager → Message templates → Manage templates → Create)

**① Advisory template — REQUIRED, works on the Test WABA:**
1. **WhatsApp Manager** → **Message templates** → **Manage templates** → **Create template**.
2. Category: **Utility**. Name: `agroguardian_advisory_v1`. Language: **Marathi (mr)**.
3. Body — must have fixed text around the variable (a body that's only `{{1}}`, or that starts/ends with a variable, is **rejected**):
   ```
   नमस्कार 🌱 तुमच्या शेतासाठी आजचा सल्ला:
   {{1}}
   — AgroGuardian
   ```
4. Sample value for `{{1}}` (Meta validates the example renders): `आज संध्याकाळी 20 मिनिटे ठिबक सिंचन करा; माती कोरडी आहे.`
5. Submit. It shows **In review** briefly, then **Active**. (Confirmed working on the Test WABA — you do **not** need a real WABA for this one.)

> **If it's auto-flagged "Category does not match" → Marketing:** that's fine — accept **Marketing**,
> it still delivers to accepted test recipients (all the pilot needs). Or reword to strictly
> transactional text (no greetings) to keep it Utility. Either way, **keep the name and set `.env` to
> the exact name Meta saved** (the UI truncates long names — click the template to see the full name):
> ```
> META_WHATSAPP_ADVISORY_TEMPLATE_NAME=<exact name from Meta, e.g. agroguardian_advisory_v1>
> ```

**② OTP template — OPTIONAL, deferred (needs business verification):**
> ⏸️ **Skip this for the pilot.** OTP is only for a future farmer-login flow; the sensor→advisory→reply
> loop does not use it. Authentication-category templates are **gated behind business verification** —
> on an unverified/Test WABA they fail with *"does not have permission to create message template"*
> (the advisory template above is unaffected because it isn't Authentication category).
>
> When you do want OTP later, either:
> - Add a pre-built authentication template from **WhatsApp Manager → Template library** (may bypass the custom-create gate), **or**
> - Complete **Business verification** (Business Settings → Security Center → Business verification), then create it: Category **Authentication**, Name `agroguardian_otp_v1`, Language **mr**, using Meta's built-in Authentication layout (it auto-adds the `copy_code` button the OTP sender expects — do **not** hand-build the button).
>
> Leave `META_WHATSAPP_OTP_TEMPLATE_NAME=agroguardian_otp_v1` in `.env` as-is; it's simply unused until then.

#### 2e. Generate a 60-day System User token (NOT the 24h Quickstart token)
The token on the API Setup panel expires in **24 hours** — useless for a deployment. Instead:
1. **Business Settings** (business.facebook.com/settings) → **Users → System users**.
2. Create one (e.g. `agro-backend`, role Admin) or select an existing one → **Add assets** → assign your **app** and your **WhatsApp account** with full control.
3. **Generate new token** → select your app → token expiration **60 days** → scopes: **`whatsapp_business_management`** + **`whatsapp_business_messaging`** → **Generate**.
4. Copy the `EAAG...` token.
   ⏰ **Set a calendar reminder for ~day 55 to regenerate.** When it expires, outbound fails with a `meta_190` (auth) error recorded in `ai_suggestions.delivery_last_error` until you rotate it. (A refresh script is the long-term fix — Part 9 #28.)

#### 2f. Get the App Secret (for inbound signature verification)
1. App dashboard → **App Settings → Basic**.
2. **App Secret** → **Show** (may re-prompt your FB password) → copy.

🔑 **Paste into `.env`:**
```
META_WHATSAPP_PHONE_NUMBER_ID=...          # from 2b
META_WHATSAPP_BUSINESS_ACCOUNT_ID=...      # from 2b
META_WHATSAPP_TOKEN=EAAG...                # 60-day System User token from 2e
META_WHATSAPP_VERIFY_TOKEN=...             # the random string you set in Tier 0
META_WHATSAPP_APP_SECRET=...               # from 2f
```

**Webhook registration** (done from the app, after these are set + app restarted — full steps in
PILOT_READINESS §3 B3):
- Callback URL: `https://<your-host>/webhooks/whatsapp` · Verify token: the same string · Subscribe field: **`messages`**.

**Common first-submission failures** (Part 9 #29): wrong language code (use `mr` not `mr_IN`);
variable at start/end of body; button parameter mismatch on OTP (use Meta's built-in Auth layout).

#### 2g. Promote to a REAL WABA + your own number (leave the test sandbox)

The Test WABA is capped at 5 test recipients and can't reach real farmers. To go live you register
your **own phone number** (one **never used on WhatsApp** — consumer or Business app; delete that
account first if it was) on a **new production WABA**. The number must receive an **SMS or voice
call** for the verification code (voice = a landline/IVR works). Full runbook with the exact commands
is in **PILOT_READINESS §3 B4**; the account-side essentials:

1. **App → Use cases → WhatsApp → Customize → API Setup → Add phone number →** create a **new WABA**
   (not "Test WhatsApp Business Account"), set a **display name** (e.g. `AgroGuardian`, goes to Meta
   review), enter the number, verify by SMS/voice.
2. **Register the number for the Cloud API** — set a 6-digit two-step PIN (API Setup prompt, or
   `POST /{phone_number_id}/register`). A number can't send via the API until it's registered.
3. **Grant the System User the new WABA** (Business Settings → System users → Add assets → the new
   WhatsApp account → Full control) and **regenerate the 60-day token** so it carries the new WABA.
4. **Recreate the advisory template on the new WABA** — templates are per-WABA and don't carry over.
   Submit `agroguardian_advisory_v1` (Marathi) as **Utility**; if Meta reflags it to **Marketing**,
   accept it (still delivers). Keep the exact name so `.env` needs no change.
5. **Update `.env`** with the new `META_WHATSAPP_PHONE_NUMBER_ID`, `META_WHATSAPP_BUSINESS_ACCOUNT_ID`,
   and `META_WHATSAPP_TOKEN`; restart `app`.

🔑 **Result:** an **unverified** business with an approved display name can send business-initiated
template messages to **~250 unique recipients / 24h** — enough for the pilot, no test-recipient list.
**Business verification** (Business Settings → Security Center) later raises limits and unlocks the
Authentication/OTP template (2d ②).

---

### 3. NASA Earthdata (SMAP soil moisture) — *post-pilot; adapter not built yet*

**Why:** feeds soil-moisture into advisories. **Note:** the NASA adapter is **not written yet**
(`app/infra/satellite/` is an empty stub), so this credential sits unused until that PR lands. Sign
up now if you want the approval done early. ⏱ 24-hour approval · 💰 free forever.

1. <https://urs.earthdata.nasa.gov/users/new> → register → confirm via the email link.
2. Wait for approval (~24h) → log in → **Profile** → confirm username/password work.
3. (When the adapter exists, you'll also authorize the specific SMAP data application in your Earthdata profile — that step comes with the adapter PR.)

🔑 **Paste into `.env`:**
```
NASA_EARTHDATA_USERNAME=your-username
NASA_EARTHDATA_PASSWORD=your-password
```

---

### 4. Copernicus Data Space (Sentinel-2 NDVI) — *post-pilot; adapter not built yet*

**Why:** satellite NDVI/vegetation index. **Note:** the Copernicus adapter is **not written yet**
(empty `app/infra/satellite/`), so this credential is dormant until that PR. Sign up early if you like.
⏱ Instant · 💰 free tier ~30,000 processing units/month (plenty for a 2–4 plot pilot).

1. <https://dataspace.copernicus.eu/> → **Register** → verify email → log in.
2. Go to <https://shapps.dataspace.copernicus.eu/dashboard/#/account/settings> → **OAuth clients** → **Create a new OAuth client**.
3. Name it `agroguardian`. On create, it shows a **Client ID** and a **Client Secret** — **copy the secret now**, it's shown once.

🔑 **Paste into `.env`:**
```
COPERNICUS_CLIENT_ID=...
COPERNICUS_CLIENT_SECRET=...
```
(`COPERNICUS_BASE_URL` and `COPERNICUS_TOKEN_URL` are already correct in `.env.example`.) Silent
rate-limit truncation is a known trap (Part 9 #27) — the adapter, when built, retries with backoff
and caps concurrency.

---

## Tier 2 — Before deploying to the cloud

Skip until you push off your laptop. Local dev needs none of these.

### 5. VPS (Lightsail Mumbai, or equivalent)

⏱ ~2 min to provision · 💰 **$20/month** (2 vCPU / 4 GB / 80 GB SSD) + ~$4/month snapshots.

1. <https://lightsail.aws.amazon.com> → sign in.
2. **FIRST, set a billing guardrail:** AWS Console → **Billing → Budgets** → create a **$30/month** email alert. This is your runaway-charge safety net.
3. Lightsail → **Create instance** → region **Mumbai (ap-south-1)** → **Linux/Ubuntu 22.04 LTS** → **$20** plan → name `agro-prod-01` → upload your **SSH public key** → **Create**.
4. **Networking** tab → **Create static IP** → attach to `agro-prod-01` (free while attached; **delete it explicitly** when you retire the instance or AWS bills for a detached IP — Part 9 #37).
5. **Open the Lightsail firewall** (the #1 gotcha — Lightsail's own firewall is separate from UFW; you must open both — Part 9 #36): Networking tab → **IPv4 Firewall** → add TCP rules for **22, 80, 443, 8883**.
6. **Snapshots** tab → **Enable automatic snapshots** → daily ~03:00 IST.

No `.env` key for the VPS itself. The IP feeds Caddy via `make caddyfile-prod IP=<your-ip>` (never
hand-edit the Caddyfile — Part 0.5 / rule 27). When you buy a real domain later, the same target
takes a `DOMAIN=` argument.

### 6. Cloudflare R2 (object storage) — *adapter not built yet*

**Note:** `app/infra/storage/` is an empty stub; R2 is dormant until that adapter PR. ⏱ instant ·
💰 free tier 10 GB + 1M ops/month (pilot < 1 GB).

1. <https://dash.cloudflare.com> → **R2** → **Create bucket** three times: `agro-rasters`, `agro-photos`, `agro-firmware`.
2. R2 → **Manage R2 API Tokens** → **Create API token** → permission **Object Read & Write** → scope to those three buckets → **Create**. Copy the **Access Key ID** + **Secret Access Key** (shown once).
3. Note your **Account ID** (top-right of the R2 overview page).

🔑 **Paste into `.env`:**
```
R2_ACCOUNT_ID=<account id>
R2_ACCESS_KEY_ID=<from token>
R2_SECRET_ACCESS_KEY=<from token>
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
```
(Never hardcode `s3.amazonaws.com` — always the R2 endpoint. Rule 26.)

### 7. Backblaze B2 (cold backups) — *adapter not built yet*

**Note:** B2 backup adapter not written yet; until then take manual `pg_dump`s (PILOT_READINESS §3 E).
⏱ instant · 💰 free tier 10 GB.

1. <https://www.backblaze.com/sign-up/cloud-storage> → sign up.
2. **B2 Cloud Storage → Buckets → Create a Bucket** → name `agro-backups` → **Private**.
3. **App Keys → Add a New Application Key** → restrict to bucket `agro-backups` → **Create**. Copy **keyID** + **applicationKey** (shown once).
4. Note the bucket's **Endpoint** (Buckets list, e.g. `s3.us-west-001.backblazeb2.com`).

🔑 **Paste into `.env`:**
```
B2_KEY_ID=<keyID>
B2_APPLICATION_KEY=<applicationKey>
B2_ENDPOINT_URL=https://s3.<region>.backblazeb2.com
B2_BUCKET_BACKUPS=agro-backups
```

### 8. Sentry (error tracking) — optional, recommended
⏱ instant · 💰 dev plan free.
1. <https://sentry.io> → sign up → **Create project** → platform **Python → FastAPI** → copy the **DSN**.
🔑 `SENTRY_DSN=https://<key>@<org>.ingest.sentry.io/<project-id>` (blank = Sentry silently off).

### 9. Better Stack (log aggregation) — optional
⏱ instant · 💰 free 1 GB/month.
1. <https://betterstack.com> → **Logs** → **Connect source** → copy the **source token**.
🔑 `BETTER_STACK_TOKEN=<source token>` (blank = stdout only).

### 10. UptimeRobot (uptime pinger) — recommended
⏱ instant · 💰 free 50 monitors.
1. <https://uptimerobot.com> → **Add New Monitor** → HTTP(s) → URL `https://<your-host>/api/v1/health` → 5-min interval → set an email/SMS alert contact.
No `.env` key.

### 11. Tailscale (private admin mesh) — optional
1. <https://login.tailscale.com> → sign up → install on laptop + VPS (`curl -fsSL https://tailscale.com/install.sh | sh`). Lets you reach SSH/Grafana without exposing them publicly. No `.env` key.

### 12. Firebase Cloud Messaging (push) — *adapter not built yet*
1. <https://console.firebase.google.com> → **Add project** → **Project Settings → Service accounts → Generate new private key** → save as `secrets/fcm-sa.json` → mount it into the app container in `docker-compose.prod.yml`.
🔑 `FCM_PROJECT_ID=<project id>`, `FCM_SERVICE_ACCOUNT_JSON_PATH=/secrets/fcm-sa.json`.

### 13. Dashboard basic-auth (already deployed — how to set the password)
The ops dashboard sits behind Caddy `basic_auth`. To set/rotate the password:
1. Generate a bcrypt hash:
   ```bash
   docker run --rm caddy:2 caddy hash-password --plaintext 'your-strong-password'
   ```
   (Run it **once** — a duplicated paste concatenates into an `unknown flag --rm` error.)
2. 🔑 In `.env`, **single-quote** the hash (it contains `$`):
   ```
   DASHBOARD_USER=ops
   DASHBOARD_PASSWORD_HASH='$2a$14$....'
   ```
3. Recreate Caddy: `docker compose -f docker-compose.prod.yml up -d caddy`. Verify: the dashboard URL returns **401** without creds, **200** with them.

---

## Tier 3 — Post-pilot (do NOT block the pilot on these)

- **Razorpay** (subscriptions) — <https://dashboard.razorpay.com/signup>. KYC takes **5–7 days** (PAN, GST, business bank account). Start the paperwork now so it doesn't gate a later phase; the pilot has no `razorpay` dependency and uses tier `pilot_internal`.
- **MSG91 + DLT registration** (SMS fallback) — TRAI DLT registration takes 7–10 days. Only matters when non-WhatsApp farmers need SMS. The SMS adapter is a Protocol-only stub for the pilot.

---

## Priority summary

| When | Accounts | Gates |
|---|---|---|
| **Today** | #1 Anthropic, #2 Meta WhatsApp (start template review) | The pilot's two live blockers |
| This week | #10 UptimeRobot, #13 dashboard password, #8 Sentry | Ops hygiene |
| Before cloud deploy | #5 VPS | Leaving your laptop |
| When adapters are built | #3 NASA, #4 Copernicus, #6 R2, #7 B2, #12 FCM | Dormant features (need code first) |
| Paperwork in parallel | #14 Razorpay, MSG91/DLT | Post-pilot phases |

**Fastest path to a live pilot:** Tier 0 (10 min) → #1 Anthropic (5 min) → #2 Meta (submit today,
approves in 24–48h) → deploy. Everything else is either ops polish or dormant-until-built.

---

## What if I leave a value blank?

The app **boots with empty external secrets in development** by design:
- No `ANTHROPIC_API_KEY` → advisory runs in log-only stub mode (**but prod refuses to boot** — see the boot guard).
- No `META_WHATSAPP_*` → delivery logs "would send"; inbound webhook returns 403; OTP requests fail cleanly.
- No `SENTRY_DSN` / `BETTER_STACK_TOKEN` → those integrations silently disable; logs still hit stdout.
- No `R2_*` / `B2_*` / `NASA_*` / `COPERNICUS_*` → those adapters are stubs anyway; sensor ingest and advisory are unaffected.

**In production**, `_assert_production_safe()` (`app/config.py`) hard-fails startup with a clear
message if `AUTH_JWT_SECRET`, `POSTGRES_PASSWORD`, `MQTT_BROKER_PASSWORD`, or `ANTHROPIC_API_KEY`
is default/empty.

---

## Where to look when an integration misbehaves

Deployment-specific failure modes live in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) and
[`deploy/staging/README.md`](deploy/staging/README.md); operational verification for each live
integration is in [`PILOT_READINESS.md`](PILOT_READINESS.md) §3. The recurring traps:

- WhatsApp template rejected → Part 9 #29 (language code, variable placement, button param).
- Meta token expires every 60 days → Part 9 #28 (rotate; refresh script needed).
- Copernicus silent rate-limit truncation → Part 9 #27 (retry+backoff, cap concurrency).
- Lightsail firewall vs UFW → Part 9 #36 (open **both**).
- Lightsail static IP billed when detached → Part 9 #37 (delete it explicitly on teardown).
