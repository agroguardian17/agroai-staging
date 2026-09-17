# Pilot Readiness

**As of 2026-09-16 · main @ `317a5a9` · migrations head `0016` · staging deployed**

The single operational page for taking AgroGuardian V2 from "code complete" to "live with
real farmers." It answers three questions:

1. **What is built** (§1) — and what's still just a stub.
2. **What is dormant, and the exact env switch that wakes each** (§2).
3. **The ordered steps you run to go live** (§3) — with the exact commands, the exact
   expected output, and what to do when a step fails.

Companion docs:
- **[`ACCOUNTS_TO_FILL.md`](ACCOUNTS_TO_FILL.md)** — where to *get* each credential (signup click-paths, scopes, costs). This page tells you what to *do* with each value once you hold it.
- **[`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)** — the meaning and runtime effect of every single `.env` variable.

Conventions used below:
- `$` prefix = a command **you** run (I can't write to the VPS). Read-only commands are safe to run repeatedly; the only mutating actions are editing `.env` and `docker compose ... up -d`.
- `<your-host>` = your public hostname, e.g. `api-13-233-x-x.sslip.io` during the sslip.io phase, or your real domain later.
- All VPS commands assume you're in the compose directory (the folder holding `docker-compose.prod.yml`), typically `~/agroguardian/agro_backend`. Adjust the path to match your VPS layout.

---

## 1. What is built and green ✅

The full advisory loop exists end-to-end, tested (full suite green, CI-enforced 80% coverage gate), and running on staging right now:

```
sensor packet → MQTT → node_sensor_readings (partitioned)
   → rule engine → alert (row) + alert.created NOTIFY on channel agro_events
   → advisory_subscriber: dispatch_advisory (atomic claim, so no double-send)
        → compose_advisory → Claude Sonnet → ai_suggestions (Marathi body)
   → delivery_subscriber: deliver_advisory → WhatsApp Utility template
   → farmer replies on WhatsApp → /webhooks/whatsapp
        → record_action_from_reply → farmer_actions
   → nightly 04:00 IST learning job → ai_learning_log (advice vs. what the farmer actually did)
```

| Capability | State on staging | Entry point |
|---|---|---|
| Sensor ingest (MQTT → Postgres, partitioned tables) | **Live** | `app/jobs/ingest_startup.py` |
| Rule engine + alert creation | **Live** | `app/application/` |
| Advisory composition (Claude Sonnet) | **Running, log-only** (no API key yet) | `app/jobs/advisory_subscriber.py` |
| WhatsApp outbound delivery | **Running, log-only** (no WABA yet) | `app/jobs/delivery_subscriber.py` |
| WhatsApp inbound webhook (replies) | **Returns 403** (verify token/secret unset) | `app/infra/http/webhooks.py` |
| Farmer-action capture from replies | **Wired, waiting on inbound** | `app/application/record_action_from_reply.py` |
| Weather forecasts (Open-Meteo, nightly 03:00 IST) | **Live** (Open-Meteo needs no key) | `app/jobs/forecast_scheduler.py` |
| Nightly learning log (04:00 IST) | **Live** | `app/jobs/learning_scheduler.py` |
| Ginger knowledge job (06:30 IST) | **Live** | `app/jobs/ginger_scheduler.py` |
| Sub-node registration | **Live** | `app/application/register_sub_node.py` |
| Ops dashboard (Streamlit, read-only DB) | **Live behind basic-auth** | `dashboard/` |

**None of the above needs new code to run.** The three "log-only / 403" rows are *deliberate,
tested fallbacks* — they flip to real behavior the instant their credentials exist (§2 + §3).

---

## 2. Dormant switches — what wakes each one

Every dormant capability is gated by an **environment variable**, not by missing code. Set the
value in `.env` on the VPS, recreate the affected container, and the fallback disappears.

| To turn on… | Set in `.env` | Fallback when empty | Recreate |
|---|---|---|---|
| **Real AI advisories** | `ANTHROPIC_API_KEY` | `LogOnlyChatModel` writes a stub suggestion so the pipeline still exercises end-to-end | `app` |
| **WhatsApp outbound** (OTP + advisory) | `META_WHATSAPP_PHONE_NUMBER_ID`, `META_WHATSAPP_BUSINESS_ACCOUNT_ID`, `META_WHATSAPP_TOKEN` | delivery logs "would send" and marks the row sent (no real message) | `app` |
| **WhatsApp inbound** (replies → actions) | `META_WHATSAPP_VERIFY_TOKEN`, `META_WHATSAPP_APP_SECRET` | webhook GET/POST returns 403 | `app` |
| **Agronomist review gate** (hold advice for human OK) | `ADVISORY_REQUIRE_REVIEW=true` | advisories auto-send | `app` |
| **Error tracking** | `SENTRY_DSN` | silently disabled | `app` |
| **Log shipping** | `BETTER_STACK_TOKEN` | logs to stdout only | `app` |

> **Production boot guard.** `_assert_production_safe()` in [`app/config.py`](app/config.py)
> **refuses to start** in production if any of these are still default/empty:
> `AUTH_JWT_SECRET`, `POSTGRES_PASSWORD`, `MQTT_BROKER_PASSWORD`, `ANTHROPIC_API_KEY`.
> So on the prod profile the Anthropic key is **mandatory** — the container will crash-loop with
> `Refusing to start in production with default/empty secrets: ANTHROPIC_API_KEY` until it's set.
> That's by design: it prevents shipping prod with a stub advisory model.

### Not-yet-built — needs code **and** credentials (post-pilot)

These are empty package stubs today — `app/infra/satellite/` and `app/infra/storage/` contain
only an empty `__init__.py`. **Credentials alone will not activate them**; each needs an adapter
written and wired. They are **not on the pilot critical path** — the pilot ships on
sensors + advisory + WhatsApp.

| Capability | Work needed | Credentials (see `ACCOUNTS_TO_FILL.md`) |
|---|---|---|
| Satellite NDVI (Sentinel-2) | Copernicus adapter in `app/infra/satellite/` + ingest job (~1 day) | `COPERNICUS_CLIENT_ID/SECRET` |
| Soil-moisture (SMAP) | NASA Earthdata adapter (~1 day) | `NASA_EARTHDATA_*` |
| Object storage (rasters/photos/firmware) | R2 adapter in `app/infra/storage/` (~0.5 day) | `R2_*` |
| Off-site backups | B2 adapter + backup cron (~0.5 day) | `B2_*` |
| Push notifications | FCM adapter (~1 day) | `FCM_*` |

When you want any of these, say so and I'll build it as its own PR — but it needs the matching
credential present to write a real integration test against.

---

## 3. From your side — go-live, step by step

Two things gate the pilot:

- **(A) the Anthropic key** — 5 minutes, no approval wait, unblocks real advice instead of stubs. **Do this first.**
- **(B) Meta WhatsApp** — the 24–48h approval item (template review). **Start it today in parallel** so the wait runs while you do everything else.

Then **(C)** optional hardening you want in place before real farmers, **(D)** seeding real
data, and **(E)** the daily-ops routine.

---

### A. Turn on real AI advisories

**Time:** ~5 min. **Blocks on:** nothing.

**A1. Create the key.** Anthropic Console → **API Keys** → **Create Key**. Full detail in
`ACCOUNTS_TO_FILL.md` Tier 1 #1. Add ~$20 credit (pilot burn ≈ $3/month on the Sonnet+Haiku mix).
Copy the `sk-ant-...` value **immediately** — the console shows it once.

**A2. Put it in the VPS env.** SSH in, open the prod env file:

```bash
$ nano ~/agroguardian/agro_backend/.env
```
Find the line `ANTHROPIC_API_KEY=` (it's currently empty) and set it:
```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxx
```
Leave `ANTHROPIC_MODEL_SONNET=claude-sonnet-4-5` and `ANTHROPIC_MODEL_HAIKU=claude-haiku-4-5`
as-is — those are the model ids the `ModelRole` layer resolves. Save (`Ctrl+O`, `Enter`, `Ctrl+X`).

**A3. Recreate just the app container** so it re-reads `.env` (this does **not** touch Postgres,
MQTT, or the dashboard):

```bash
$ docker compose -f docker-compose.prod.yml up -d app
```
Expected: `Recreating agro_backend-app-1 ... done`. If instead you get a crash-loop, jump to the
troubleshooting box below.

**A4. Verify the log-only fallback is gone.** The advisory subscriber logs
`advisory_subscriber.no_anthropic_key` on every startup while the key is missing. After A3 it
must be **absent**:

```bash
$ docker compose -f docker-compose.prod.yml logs --since 3m app | grep -i "no_anthropic_key\|advisory_subscriber.started"
```
Expected: you see `advisory_subscriber.started` and **no** `no_anthropic_key` line.

**A5. End-to-end check.** Wait for a real alert (or nudge a sensor over threshold), then read the
latest suggestions straight from Postgres:

```bash
$ docker compose -f docker-compose.prod.yml exec postgres \
    psql -U agro -d agro -c \
    "select suggestion_id, suggestion_type, review_status, delivery_status, \
            left(full_message_marathi, 70) as preview, generated_at \
     from ai_suggestions order by generated_at desc limit 3;"
```
Expected: a genuinely composed Marathi sentence in `preview` — not the fixed log-only stub text.
That confirms Claude is live end-to-end.

> **Troubleshooting A**
> - **`Refusing to start in production ... ANTHROPIC_API_KEY`** in `docker compose logs app` → the key didn't get read. Check for a typo in the key name, a stray space, or that you edited the `.env` the compose file actually loads (`docker compose -f docker-compose.prod.yml config | grep ANTHROPIC` shows what it resolved).
> - **`401 authentication_error`** in the logs when an alert fires → key is wrong/revoked. Regenerate in the Anthropic console.
> - **`400 model_not_found`** → the `ANTHROPIC_MODEL_*` id is wrong for your account; keep the defaults above.
> - Suggestions still look like stubs → you're reading old rows; check `created_at` is *after* the restart.

---

### B. Turn on WhatsApp (advisory outbound + replies inbound; OTP is deferred)

The advisory sender posts to
`POST /{graph_version}/{phone_number_id}/messages` with a **body-only template**: the whole Marathi
message is passed as template parameter `{{1}}`. That single **advisory** template is the only one
the pilot needs. (The OTP sender uses an Authentication template with a copy-code button — that's a
future login feature, deferred; see the note in B1.)

> **⚠️ What the Test WABA can and can't do (verified 2026-09-16).** The WhatsApp use case gives you a
> "Test WhatsApp Business Account." Confirmed behavior:
> - ✅ **Creates your advisory template** (Marketing/Utility) — it goes **Active** on the Test WABA. So you can build and test the advisory pilot on the test number **now**, no real WABA needed.
> - ✅ **Sends** to your 5 accepted test recipients.
> - ❌ **Rejects the OTP (Authentication) template** — Authentication category is gated behind **business verification**. This is category-specific; your advisory template is unaffected.
>
> **What still needs a real (production) WABA:** sending to **real, non-test farmers**, and (later) the
> OTP template. A real WABA needs a **registerable phone number** (spare SIM, or landline/VoIP that
> takes a *voice* call — SMS not required; number must not already be on the consumer WhatsApp app).
> Until then, everything below works against the **test number + your advisory template** (or
> `hello_world`) for a full technical dry-run — see B0.

#### B0 — Interim: prove the outbound path on the test number (no real WABA needed)

Does everything except the template *content* — token, phone-number ID, sender code, `wamid`,
delivery-status webhook:

1. From **Use cases → Connect with customers through WhatsApp → Customize → API Setup**, grab the test WABA's `META_WHATSAPP_PHONE_NUMBER_ID` + `META_WHATSAPP_BUSINESS_ACCOUNT_ID`, and generate the 60-day System User token → `META_WHATSAPP_TOKEN` (works on the test WABA too).
2. Add your own phone as a test recipient (API Setup → "To" → Manage phone number list → accept on your handset).
3. In `.env`, temporarily: `META_WHATSAPP_ADVISORY_TEMPLATE_NAME=hello_world` (a pre-approved Utility sample, no variables), then `docker compose -f docker-compose.prod.yml up -d app`.
4. Trigger an advisory and confirm a `wamid`:
   ```bash
   $ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
       "select suggestion_id, delivery_status, delivery_provider_message_id, delivery_last_error \
        from ai_suggestions order by generated_at desc limit 3;"
   ```
   A `hello_world` message on your phone + a `wamid` = the delivery pipeline is green. Swap the
   template name back to `agroguardian_advisory_v1` once the real template is approved (B1).

#### B1 — Create the advisory template (works on the Test WABA; approval usually minutes)

Full signup/navigation detail is in `ACCOUNTS_TO_FILL.md` Tier 1 #2 (note the "use cases" layout —
API Setup lives under **Use cases → Customize**, not a top-level WhatsApp nav item). The
pilot-critical specifics:

1. **Advisory template (the only one the pilot needs), language `mr` (Marathi):**
   - Name `agroguardian_advisory_v1`, category **Utility**. Body is a single parameter `{{1}}`.
     ⚠️ Meta **rejects** a body that is *only* `{{1}}`, and rejects a variable at the very start or
     very end. So wrap it with fixed Marathi text on both sides. A body that passes review:

     ```
     नमस्कार 🌱 तुमच्या शेतासाठी आजचा सल्ला:
     {{1}}
     — AgroGuardian
     ```
     Provide a realistic sample value when Meta asks (it validates the example renders), e.g.
     `आज संध्याकाळी 20 मिनिटे ठिबक सिंचन करा; माती कोरडी आहे.`
2. **If Meta flags it as *Marketing* instead of Utility:** fine — accept Marketing (still delivers to
   test recipients), or reword to strictly transactional text to keep Utility. Either way, the UI
   **truncates long names** — click the template to read the exact saved name and set
   `META_WHATSAPP_ADVISORY_TEMPLATE_NAME` in `.env` to match it **exactly**, or sends fail with
   `meta_132001` ("template does not exist").
   - **OTP template — deferred, off the critical path.** The Authentication-category OTP template is
     gated behind **business verification** and fails on the Test WABA. Skip it for the pilot; the
     sensor→advisory→reply loop never uses OTP. When you want it later: add a pre-built auth template
     from **WhatsApp Manager → Template library**, or complete Business verification then create
     `agroguardian_otp_v1` (Authentication, `mr`, Meta's built-in copy-code layout). Leave
     `META_WHATSAPP_OTP_TEMPLATE_NAME` in `.env` as-is until then — it's simply unused.
3. **Test recipients (test mode caps at 5):** WhatsApp → **API Setup** → "To" field → **Manage
   phone number list** → add your phone + up to 4 farmer/founder phones. Each person must reply to
   Meta's confirmation on their handset. Store each number as **E.164 with `+91`** — the code stores
   `farmers.phone` as E.164 (e.g. `+918123456789`) and matches inbound replies against it.
4. **Generate a 60-day System User token — NOT the 24h Quickstart token:** Business Settings →
   **Users → System users** → (create or pick one) → **Generate new token** → app = your app →
   scopes **`whatsapp_business_management`** + **`whatsapp_business_messaging`** → 60-day expiry →
   Generate. Copy it (`EAAG...`). ⏰ **Set a calendar reminder for ~day 55** to regenerate; when it
   expires, outbound silently starts failing with an auth error until you rotate it.
5. **Pick your verify token now:** any random string (e.g. `openssl rand -hex 16`). You'll type the
   *same* string into Meta's webhook config (B3) and into `.env`. Write it down.

#### B2 — Set outbound credentials and send a real message

You need three values from B1 (templates may still be "in review" — outbound to **test
recipients** works before public approval):

```bash
$ nano ~/agroguardian/agro_backend/.env
```
```
META_WHATSAPP_PHONE_NUMBER_ID=...          # WhatsApp → API Setup → "Phone number ID" (a long number)
META_WHATSAPP_BUSINESS_ACCOUNT_ID=...      # WhatsApp → API Setup → "WhatsApp Business Account ID"
META_WHATSAPP_TOKEN=EAAG...                # the 60-day System User token from B1.4
```
Leave `META_WHATSAPP_ADVISORY_TEMPLATE_NAME=agroguardian_advisory_v1`,
`META_WHATSAPP_OTP_TEMPLATE_NAME=agroguardian_otp_v1`, and `META_WHATSAPP_GRAPH_VERSION=v20.0`
as-is unless you named the templates differently in Meta. Recreate the app:

```bash
$ docker compose -f docker-compose.prod.yml up -d app
```
Now trigger an advisory to a **test-recipient farmer** (an alert on their plot, or the internal
send path if you have one). Confirm it left the building with a provider message id:

```bash
$ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
    "select suggestion_id, delivery_status, delivery_provider_message_id, delivery_last_error \
     from ai_suggestions where delivery_status in ('sent','failed_permanent') \
     order by generated_at desc limit 5;"
```
Expected: `delivery_status='sent'` and a non-null `delivery_provider_message_id` (a `wamid...`
string). The message should appear on the test phone within seconds.

> **Troubleshooting B2** (read `delivery_last_error` — the sender records the Meta error there)
> - **`meta_131030` / "recipient not in allowed list"** → that phone isn't a confirmed test recipient. Add it in B1.3 and have them accept.
> - **`meta_132001` / "template does not exist"** → name/language mismatch. `META_WHATSAPP_ADVISORY_TEMPLATE_NAME` must equal the Meta template name exactly, and the template's language must be `mr` (matching `farmers.language_preference='marathi'`, which the code maps to `mr`).
> - **`meta_100` / invalid parameter** → usually a newline in the parameter; the sender already collapses whitespace, so this more often means the template body still starts/ends with `{{1}}` — fix the template (B1.1).
> - **`meta_190` (auth)** → the token expired or lacks a scope. Regenerate with both `whatsapp_business_*` scopes (B1.4).
> - **`delivery_status='sent'` but no message on the phone** → the recipient hasn't accepted the test-recipient invite, or is on a non-test number while you're still in test mode.
>
> Transient errors (network, `meta_130429` rate-limit, `meta_80008`, HTTP 429) are **not** failures —
> the delivery subscriber retries them with backoff (30s, 120s, 480s, 1800s, 7200s). Only 4xx
> "bad template / bad recipient / revoked token" become `failed_permanent`.

#### B3 — Turn on inbound (farmer replies → `farmer_actions`)

Set the two verification secrets:
```bash
$ nano ~/agroguardian/agro_backend/.env
```
```
META_WHATSAPP_VERIFY_TOKEN=<the random string from B1.5>
META_WHATSAPP_APP_SECRET=<Meta → App Dashboard → App Settings → Basic → "App Secret" → Show>
```
Recreate the app:
```bash
$ docker compose -f docker-compose.prod.yml up -d app
```
Now register the webhook in Meta → **WhatsApp → Configuration → Webhooks**:
- **Callback URL:** `https://<your-host>/webhooks/whatsapp`
  Caddy already routes `/webhooks/*` → `app:8000`, so no proxy change is needed.
- **Verify token:** the *same* random string you put in `.env`.
- Click **Verify and save**. Meta calls `GET /webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...`; the app echoes the challenge and returns **200** (it returned 403 before the token was set).
- Under **Webhook fields**, **Subscribe** to **`messages`** (this delivers both inbound texts and delivery-status receipts).

Verify the handshake yourself (replace the token):
```bash
$ curl -s -o /dev/null -w '%{http_code}\n' \
    "https://<your-host>/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=<the string>&hub.challenge=42"
# expect: 200
```
Then send a reply from a test phone (e.g. the farmer answers "५०० लिटर" or "हो") and confirm it
was captured as an action:
```bash
$ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
    "select action_id, farmer_id, action_type, water_liters, farmer_followed_ai, source, recorded_at \
     from farmer_actions order by recorded_at desc limit 5;"
```
Expected: a new row, with `quantity` parsed even from Devanagari digits (`५००` → `500`) and
`followed` set from a Marathi/English yes/no. Also watch the app log:
```bash
$ docker compose -f docker-compose.prod.yml logs --since 2m app | grep whatsapp.webhook
```
Expected: `whatsapp.webhook.inbound recorded=1 ... actions_recorded=1`.

> **Troubleshooting B3**
> - **"The callback URL or verify token couldn't be validated"** in Meta → the token in `.env` and in the Meta form don't match, or the app wasn't recreated after setting it (rerun B3's `up -d app`), or `<your-host>` isn't publicly reachable over HTTPS (test the `curl` above from your laptop, not the VPS).
> - **Handshake 200 but replies don't appear as actions** → the sender's phone isn't a known farmer. Inbound from an unknown number is recorded but produces no action (`unknown_sender` in the log). The farmer's `farmers.phone` must be their E.164 number with `+91`.
> - **POST returns 403 on real deliveries** → the `X-Hub-Signature-256` HMAC failed. That means `META_WHATSAPP_APP_SECRET` is wrong; copy it again from App Settings → Basic. (With the secret unset the app skips the check; with it set it's enforced.)
> - **Nothing at all arrives** → confirm you subscribed the **`messages`** field, not just saved the callback URL.

#### B4 — Promote to a real WABA + your own number (leave the test sandbox)

The Test WABA is capped at 5 test recipients. To reach real farmers you register **your own phone
number** — one **never used on WhatsApp** (delete any consumer/Business-app account on it first) that
can receive an **SMS or voice call** — on a **new production WABA**. Account-side signup summary is in
`ACCOUNTS_TO_FILL.md` 2g; this is the operational runbook.

**B4.1 — Add + verify the number.** App → **Use cases → WhatsApp → Customize → API Setup → Add phone
number** → **create a new WABA** (not "Test WhatsApp Business Account") → set a **display name**
(`AgroGuardian`, goes to Meta review) → enter the number → verify by SMS or voice.

**B4.2 — Register the number for the Cloud API** (a new number can't send until registered — set a
6-digit two-step PIN). If API Setup doesn't prompt, do it via API (replace the new phone-number ID;
choose your own PIN):
```bash
$ docker compose -f docker-compose.prod.yml exec -e NEW_PNID=<NEW_PHONE_NUMBER_ID> -T app python - <<'PY'
import os, json, urllib.request, urllib.error
ver=os.environ.get("META_WHATSAPP_GRAPH_VERSION","v20.0"); pnid=os.environ["NEW_PNID"]; tok=os.environ["META_WHATSAPP_TOKEN"]
req=urllib.request.Request(f"https://graph.facebook.com/{ver}/{pnid}/register",
    data=json.dumps({"messaging_product":"whatsapp","pin":"123456"}).encode(),
    headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"})
try: print("REGISTERED", urllib.request.urlopen(req).read().decode())
except urllib.error.HTTPError as e: print("HTTP", e.code, e.read().decode())
PY
```
Expected `{"success":true}`.

**B4.3 — Grant the token the new WABA.** Business Settings → System users → your `agro-backend` user
→ **Add assets → WhatsApp accounts →** new WABA → **Full control**. Then **regenerate** the 60-day
token (scopes `whatsapp_business_management` + `whatsapp_business_messaging`) so it carries the new
WABA.

**B4.4 — Recreate the advisory template on the new WABA** (templates are per-WABA). WhatsApp Manager →
switch to the new WABA → create `agroguardian_advisory_v1` (Marathi) as **Utility**; accept
**Marketing** if reflagged. Same name = no `.env` change.

**B4.5 — Point `.env` at the new number** and restart:
```bash
$ cd ~/agri-AI-live/agro_backend
$ sed -i 's/^META_WHATSAPP_PHONE_NUMBER_ID=.*/META_WHATSAPP_PHONE_NUMBER_ID=<NEW_PHONE_NUMBER_ID>/' .env
$ sed -i 's/^META_WHATSAPP_BUSINESS_ACCOUNT_ID=.*/META_WHATSAPP_BUSINESS_ACCOUNT_ID=<NEW_WABA_ID>/' .env
$ sed -i 's/^META_WHATSAPP_TOKEN=.*/META_WHATSAPP_TOKEN=<NEW_60DAY_TOKEN>/' .env
$ docker compose -f docker-compose.prod.yml up -d app
```

**B4.6 — Verify** the number belongs to the WABA and the template is APPROVED-`mr` (prints nothing
secret):
```bash
$ docker compose -f docker-compose.prod.yml exec -T app python - <<'PY'
import os, json, urllib.request, urllib.error
ver=os.environ.get("META_WHATSAPP_GRAPH_VERSION","v20.0"); waba=os.environ["META_WHATSAPP_BUSINESS_ACCOUNT_ID"]
pnid=os.environ["META_WHATSAPP_PHONE_NUMBER_ID"]; tok=os.environ["META_WHATSAPP_TOKEN"]
def get(u):
    r=urllib.request.Request(u,headers={"Authorization":f"Bearer {tok}"})
    try: return json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e: return {"__err__":e.code,"b":e.read().decode()[:300]}
pns=get(f"https://graph.facebook.com/{ver}/{waba}/phone_numbers?fields=id,display_phone_number,code_verification_status")
print("phone matches env:", pnid in [p.get("id") for p in pns.get("data",[])], pns.get("data"))
tpl=get(f"https://graph.facebook.com/{ver}/{waba}/message_templates?fields=name,language,status&limit=100")
print("templates:", [(t.get("status"),t.get("language"),t.get("name")) for t in tpl.get("data",[])])
PY
```
Want: `phone matches env: True` and `('APPROVED','mr','agroguardian_advisory_v1')`. Then a real send
(B2's probe / an injected alert) delivers to any opted-in WhatsApp number — no test-recipient cap.

> **Messaging limits:** an **unverified** business with an approved display name sends business-
> initiated template messages to **~250 unique recipients / 24h** (fine for the pilot). Business
> verification (Business Settings → Security Center) raises this and unlocks the OTP/Authentication
> template. WhatsApp policy still requires recipients to have **opted in** before you message them.

---

### C. Optional hardening before real farmers

| Step | Why it matters for the pilot | Exactly how |
|---|---|---|
| **Agronomist review gate** | For week 1 you want a human to eyeball AI advice before it reaches a farmer's phone. | Set `ADVISORY_REQUIRE_REVIEW=true`, `docker compose ... up -d app`. Suggestions then sit in a review state instead of auto-sending; approve them in the dashboard's **Advisory Pipeline** page. Flip back to `false` once you trust the output (a few days in). |
| **Sentry error tracking** | Catch runtime exceptions you'd otherwise only find by grepping logs. | Set `SENTRY_DSN=...` (see `ACCOUNTS_TO_FILL.md` Tier 2 #8), recreate `app`. Trigger a test error and confirm it lands in the Sentry dashboard. |
| **No `CHANGE_ME` left in prod** | The boot guard blocks the four critical ones, but rotate anything still on a default. | `grep CHANGE_ME .env` should return nothing. Rotate `MQTT_BROKER_PASSWORD` (also update the broker's password file), `AUTH_JWT_SECRET` (invalidates existing tokens — do before real logins), `POSTGRES_PASSWORD` (also update `DATABASE_URL` + `DATABASE_URL_SYNC`). Do one at a time and recreate the affected service. |
| **Branch protection on `main`** | Prevent an unreviewed push from auto-deploying to prod. | GitHub → repo → Settings → Branches → Add rule for `main` → require a PR + require the CI status check to pass. **Needs org-admin — I can't set it.** |

---

### D. Seed real pilot data (not the smoke-test rows)

Before a real farmer gets a real message, the DB needs real, constraint-valid rows. The gotchas
that bit us during build (use the exact enum values):

- `farmers.language_preference` = **`marathi`** (full word; the code maps it to `mr` for Meta). Not `mr`.
- `farmers.phone_primary` = **E.164 with `+91`**, e.g. `+918123456789`. (The DB column is `phone_primary`; the code exposes it as `.phone`.) This is what inbound replies match against.
- `farms.payment_status` = **`paid`** (not `active`); `plots.soil_type` = **`loamy`** (not `loam`); field-visit `visit_type` = **`installation`** (not `install`).
- Every tenant-scoped row needs a real `tenant_id` (the pilot tenant, tier `pilot_internal`).

Confirm what's actually there before going live (a dashboard read, or SQL):
```bash
$ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
    "select count(*) filter (where phone_primary like '+91%') as farmers_ok, count(*) as farmers_total from farmers;"
$ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
    "select d.device_id, d.serial_number, d.device_status, c.updated_at as last_calibrated \
     from device_registry d left join device_calibration c on c.device_id = d.device_id \
     order by d.device_id;"
```
Confirm each field device's **calibration** row exists — an uncalibrated node produces
readings the rule engine will misjudge.

---

### E. Daily-ops routine (first two weeks)

Quick, read-only checks — run these each morning (or point the dashboard at them):

```bash
# 1. Everything healthy from the outside:
$ curl -s https://<your-host>/api/v1/health          # {"status":"ok",...}

# 2. Nightly jobs actually fired (forecast 03:00, learning 04:00, ginger 06:30 IST):
$ docker compose -f docker-compose.prod.yml logs --since 24h app | grep -E "forecast_scheduler.tick_ok|learning_scheduler.tick_ok|ginger_scheduler.tick_ok"

# 3. Advisory pipeline snapshot (review state × delivery state — nothing wedged in_flight/pending):
$ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
    "select review_status, delivery_status, count(*) from ai_suggestions group by 1,2 order by 3 desc;"

# 4. Delivery retry backlog (failed_transient rows and when they next retry):
$ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
    "select delivery_status, count(*), min(delivery_next_retry_at) as next_retry \
     from ai_suggestions group by delivery_status;"

# 5. Container health (all 'healthy', none 'unhealthy'/restarting):
$ docker compose -f docker-compose.prod.yml ps
```
- The advisory reconciler self-heals stale `in_flight` rows every 60s, so a transient crash won't wedge the pipeline — but a *growing* `in_flight` or `failed_permanent` count means dig in.
- **Backups:** the B2 adapter isn't built yet (§2), so until then take a manual dump on a cadence you control:
  ```bash
  $ docker compose -f docker-compose.prod.yml exec postgres \
      pg_dump -U agro -d agro | gzip > ~/agro-backup-$(date +%F).sql.gz
  ```
  Copy it off the VPS. Set a cron for it, or ask me to build the B2 backup adapter.

---

### F. End-to-end dry run with dummy data (no hardware)

Drive the **entire live pipeline** — reading → alert → Claude advisory → WhatsApp → reply →
`farmer_actions` — with one injected sensor reading. No firmware, no field node. This is the real
runtime path (same MQTT topic, schema, and rule engine hardware would use), just with a synthetic
frame. Two helper scripts ship in the repo: `scripts/dev/seed_pilot.py` (fixture farmer/farm/plot/
device) and `scripts/dev/inject_test_reading.py` (one guaranteed-`LOW_WATER` frame at 8 % moisture;
the pilot target is 28 %).

**Preconditions:** `ANTHROPIC_API_KEY` set (A), Meta outbound creds set (B2), and
`META_WHATSAPP_ADVISORY_TEMPLATE_NAME` = your exact template name. Keep `ADVISORY_REQUIRE_REVIEW=false`
for this run (otherwise the advisory waits for approval before sending). Get the scripts onto the VPS
with `git pull` in the compose dir.

**F1. Seed the fixture data — with your own WhatsApp test-recipient number as the farmer's phone.**
Real delivery only reaches a number that's an accepted Meta test recipient (B1), so seed the farmer
with *your* phone:

```bash
$ docker compose -f docker-compose.prod.yml exec -e PILOT_PHONE="+91XXXXXXXXXX" \
    app python scripts/dev/seed_pilot.py
```
It's idempotent (fixed UUIDs) and prints the farmer/farm/plot/node ids at the end. The injector
defaults to these same ids, so no copying ids around.

**F2. Start watching the pipeline** (leave this running in one terminal):

```bash
$ docker compose -f docker-compose.prod.yml logs -f app | grep -E "ingest|alert|advisory|whatsapp|delivery"
```

**F3. Inject one low-moisture reading.** The broker has no host port, so run the script *inside* the
`app` container (it has paho + the broker creds). Pipe the host file straight into the container's
python — no copy needed:

```bash
$ docker compose -f docker-compose.prod.yml exec -T app python - < scripts/dev/inject_test_reading.py
```
(To force a different alert, pass args after the dash, e.g. `... python - --moisture 3 < scripts/dev/inject_test_reading.py`.)

**F4. Verify each stage** (should all happen within a few seconds):

```bash
# a) the reading landed
$ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
    "select node_id, soil_moisture_avg_pct, recorded_at from node_sensor_readings \
     order by recorded_at desc limit 1;"

# b) a LOW_WATER alert fired (table is alerts_notifications)
$ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
    "select alert_type, severity, device_id, alert_value, alert_threshold, triggered_at \
     from alerts_notifications order by triggered_at desc limit 3;"

# c) Claude composed a Marathi advisory
$ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
    "select suggestion_id, review_status, delivery_status, left(full_message_marathi,70) as preview \
     from ai_suggestions order by generated_at desc limit 1;"

# d) WhatsApp delivered it (a wamid, and the message on your phone)
$ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
    "select delivery_status, delivery_provider_message_id, delivery_last_error \
     from ai_suggestions order by generated_at desc limit 1;"
```

**F5. Close the loop.** Reply to the WhatsApp message from your phone (e.g. `५०० लिटर` or `हो`) and
confirm it's captured as an action (needs inbound webhook, B3):
```bash
$ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
    "select action_type, water_liters, farmer_followed_ai, source, recorded_at \
     from farmer_actions order by recorded_at desc limit 3;"
```

**F6. (Optional) Fire the learning job now** instead of waiting for 04:00 IST — restart `app` and
watch for `learning_scheduler.tick_ok`, or check the table after the next nightly run:
```bash
$ docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c \
    "select learning_id, suggestion_type, suggestion_accuracy, learning_applied_at \
     from ai_learning_log order by learning_applied_at desc limit 3;"
```

> **If a stage stalls:** advisory stub text instead of real Marathi → `ANTHROPIC_API_KEY` (A). No
> `wamid` → read `delivery_last_error`: `meta_132001` = template-name mismatch, `meta_131030` =
> phone not an accepted test recipient, `meta_190` = token. `delivery_status='skipped'` with
> `ADVISORY_REQUIRE_REVIEW=true` → approve it in the dashboard or set the flag false. No alert after
> the reading landed → confirm `PLOT_PILOT_001` has an active crop season (seed_pilot creates one).

**Cleanup** (optional): `scripts/dev/cleanup_stale_pilot_data.py` is in the image if you want to
remove the fixture rows afterward.

---

## 4. Go-live checklist (ordered)

- [ ] **A.** `ANTHROPIC_API_KEY` set → real Marathi advisory verified in `ai_suggestions.full_message_marathi` (A5).
- [ ] **B1.** Meta app created; `agroguardian_advisory_v1` (Utility/Marketing) created + Active in `mr`, and `META_WHATSAPP_ADVISORY_TEMPLATE_NAME` set to its exact saved name; 60-day System User token generated; test recipients added + accepted; verify-token string chosen. (OTP template deferred — not required.)
- [ ] **B2.** Outbound creds set → a real template lands on a test phone with a `wamid` `delivery_provider_message_id`.
- [ ] **B3.** Verify token + app secret set; webhook verified in Meta (handshake `curl` = 200); a real reply appears in `farmer_actions` with `actions_recorded=1` in the log.
- [ ] **C.** Review gate ON for week 1; Sentry on; `grep CHANGE_ME .env` empty; branch protection on `main`.
- [ ] **D.** Real farmers/farms/plots/devices seeded with constraint-valid values; every device calibrated.
- [ ] **E.** `/api/v1/health` green; nightly jobs seen firing once; dashboard reachable behind auth; a manual `pg_dump` taken and copied off-box; UptimeRobot pinging `/api/v1/health`.

When **A + B** are ticked, the pilot is live: a sensor threshold produces a Claude-authored Marathi
advisory, delivered over WhatsApp, and the farmer's reply is captured and fed into the nightly
learning log.

---

## 5. What I cannot do for you (and why)

- **Edit the VPS / restart services / run `alembic upgrade` / any destructive DB op** — blocked by your standing rule (read-only VPS inspection only). Every mutating command above is yours to run; I'll help interpret the output.
- **Enter any credential** (Anthropic key, Meta token, DB/MQTT passwords) — these are secrets; I only tell you which variable each belongs to and how to verify it took effect.
- **Set branch protection / rotate secrets** — needs your GitHub-admin rights and per-action typed approval.
- **Write the satellite / storage / FCM / B2 adapters** — not built yet; each is a half-to-one-day PR and needs its matching credential present to test. Say which one and I'll start it.
