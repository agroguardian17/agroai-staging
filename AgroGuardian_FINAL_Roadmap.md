# AgroGuardian V2 — Final CTO Execution Roadmap (v1.2)

**Audience:** Co-founder / engineering lead, executing in Cursor IDE with Claude
**Pilot:** Chhatrapati Sambhaji Nagar (Aurangabad), Maharashtra — 1 farm, 4 plots, 1 Main Node, 2 Sub Nodes
**Source:** Sections 1–11 of the AgroGuardian V2 Technical Reference + five founder alignment rounds
**Stack:** AWS Lightsail Mumbai · Self-hosted Postgres 15 · FastAPI hexagonal monolith · Claude Sonnet 4.6 + Haiku 4.5 · React Native + Expo · Streamlit · Mosquitto · ChromaDB · Copernicus Data Space · NASA Earthdata · Cloudflare R2 + Backblaze B2 · WhatsApp Meta Cloud API (advisory + OTP) · FCM
**Pilot infrastructure cost:** ~$25/month (Lightsail $20 + snapshots $4 + B2 $1)
**Pilot critical path:** 12 phases · ~12 weeks (with a "Fast Path to Working Prototype" 2-week MVP track inside it)
**Post-pilot:** 2 additional phases (SMS + Razorpay) before commercial launch

## What's new in v1.2 (major: AWS Lightsail replaces Oracle Cloud)

- **Oracle Cloud abandoned** — too many signup/operational issues. Switched to **AWS Lightsail Mumbai**, which is the same architecture (Linux VPS, Docker Compose, all the same containers) on a more reliable provider.
- **AWS Lightsail Mumbai (`ap-south-1`) at $20/month** (2 vCPU / 4 GB RAM / 80 GB SSD / 3 TB egress). Plus $4/mo for automatic snapshots, $1/mo for B2 backups = **~$25/month total pilot infra**.
- **Provider Portability Charter (Part 0.5) is now MORE important, not less.** Same rules: zero AWS-specific service dependencies. We treat Lightsail as "a Linux VPS that happens to be on AWS" — no Cognito, no S3 (Cloudflare R2 instead), no RDS (self-hosted Postgres), no SES, no Lambda, no SNS/SQS. This makes migration to any other Linux VPS provider a 2-hour job.
- **Domain still non-blocking** via `sslip.io` — works identically on AWS as on any other VPS.
- **Fast Path to Working Prototype (Part 0.6)** unchanged — 2-week MVP track inside the 12-week pilot.
- **Setup runbook (Part 12.2) fully rewritten** for AWS Lightsail with every command verbatim. Includes the Lightsail-specific Firewall configuration (which is separate from UFW — same "two firewalls" gotcha as Oracle had).
- **Part 9 (common failures)** updated with AWS Lightsail-specific gotchas, removed Oracle ones.

## Why AWS Lightsail and not full EC2

Lightsail is "EC2 with simpler pricing and a friendlier console." For a 3-person team with no DevOps engineer:
- **Predictable pricing** ($20/mo flat, no surprise bill spikes)
- **Built-in static IP** (EC2 charges $0.005/h for unattached EIPs)
- **Built-in DNS zone** (EC2 needs Route 53 setup separately)
- **Built-in firewall** (cleaner than security groups for our 4-port scenario)
- **Built-in snapshots** ($0.05/GB/mo automatic)
- **Built-in metrics** (basic CloudWatch metrics included)
- **Built-in load balancer** ($18/mo, when scale forces it in Phase 2+)
- **Migration to full EC2 is one VPS-to-VPS migration** if you ever outgrow Lightsail — exactly the same procedure as moving to any other provider per Part 0.5 Rule 5.

When we hit ~200 farms (per scalability ladder in Part 12.4), we migrate to EC2 + RDS. Until then, Lightsail saves us hours of AWS Console fiddling that we'd otherwise waste.

---

# How to use this document

Chunk it across Cursor chats per Part 10. Every prompt is **copy-paste ready** and ends with the same enforcement clauses (explain, no placeholders, hexagon-consistent, scalable production-quality).

This is the single self-contained reference — no "see v2" cross-references. Read top to bottom once, then dip into individual phases as you build.

---

# PART 0 — Decisions, Stack, Pre-flight

## 0.1 Confirmed decisions

| # | Topic | Decision |
|---|---|---|
| 1 | Compute | **AWS Lightsail Mumbai (`ap-south-1`) — $20/month plan.** 2 vCPU / 4 GB RAM / 80 GB SSD / 3 TB egress. Ubuntu 22.04 LTS (x86_64). Static IP included free. Automatic snapshots at $0.05/GB/mo. Provider-portable by design (Part 0.5) — migration to DigitalOcean Bangalore, Linode Mumbai, Hetzner, or full AWS EC2 is a 2-hour job if ever needed. |
| 2 | Database | Self-hosted **Postgres 15 + PostGIS + pgvector + pgcrypto** on the same VPS. Weekly `pg_dump` to **Backblaze B2**. Daily provider-level snapshots. |
| 3 | Payments | **Deferred to post-pilot Phase 14**. Pilot uses a `pilot_internal` tier with all quotas bypassed. Razorpay + UPI AutoPay scaffolding documented; KYC runs in parallel but does not block pilot. |
| 4 | Tenant model | **One tenant per organization.** Pilot ships 1 tenant containing 1 farmer + 1 farm + 4 plots. |
| 5 | WhatsApp | **Meta Cloud API in test mode** — used for BOTH OTP auth (`authentication` template) AND advisory notifications. 5 verified test recipients, 1,000 free conversations/month. |
| 6 | SMS | **Deferred to post-pilot Phase 13** (MSG91 + DLT). `SmsClient` Protocol defined now so future-add is one adapter file. |
| 7 | Satellite | **Copernicus Data Space Ecosystem** (Sentinel-2, commercial-safe free tier) + **NASA Earthdata** (SMAP). Both free forever. |
| 8 | Architecture | **Hexagonal (ports-and-adapters) + Repository pattern + versioned APIs + Postgres NOTIFY domain events + per-tenant feature flags.** |
| 9 | Monitoring | All free-tier: **UptimeRobot** + **Better Stack** + **Sentry** + self-hosted **Prometheus + Grafana**. |
| 10 | CI/CD + auth | **GitHub Actions + Coolify** (self-hosted PaaS on the same VPS). **FastAPI-native auth** with JWT + phone OTP via **WhatsApp**. |
| 11 | LLM | **Claude Sonnet 4.6** for T1/T3 (PRIMARY role). **Claude Haiku 4.5** for T2/T4 + classification (TRIAGE role). Adapter pattern keeps Gemini/Llama swap-in as one new file. Benchmark planned month 3. |

## 0.2 Stack summary

- **Language:** Python 3.12
- **Backend:** FastAPI + uvicorn behind Caddy reverse proxy
- **DB driver:** SQLAlchemy 2.0 async + asyncpg + Alembic
- **DB:** Postgres 15 with postgis, vector, pgcrypto, uuid-ossp
- **Time-series:** Postgres native declarative range partitioning by month
- **Vector store:** ChromaDB persistent
- **MQTT broker:** Mosquitto 2.x, per-device username/password + ACL
- **Scheduler:** APScheduler (AsyncIOScheduler)
- **Validation:** pydantic v2
- **Auth:** FastAPI-native — OTP via WhatsApp Meta Cloud API; JWT (HS256); refresh tokens hashed
- **Logging:** structlog → Better Stack via HTTP shipper
- **Metrics:** prometheus-client → /metrics → self-hosted Grafana (Tailscale-only)
- **HTTP client:** httpx (async)
- **Embeddings:** sentence-transformers `paraphrase-multilingual-mpnet-base-v2`
- **LLM:** Anthropic Python SDK — Sonnet 4.6 (PRIMARY) + Haiku 4.5 (TRIAGE)
- **Satellite:** sentinelhub-py against Copernicus Data Space; earthaccess against NASA Earthdata
- **Weather:** Open-Meteo + IMD (httpx)
- **Notifications:** Firebase Admin SDK (FCM), Meta Graph API (WhatsApp advisory + OTP)
- **Farmer app:** React Native + Expo SDK 51 + TypeScript + react-query + zustand + zod + i18next
- **Dashboard:** Streamlit
- **TS type generation:** openapi-typescript + openapi-fetch
- **Object storage:** Cloudflare R2 (zero egress)
- **Cold backups:** Backblaze B2
- **CDN / DNS / SSL:** Cloudflare Free + Cloudflare Tunnel
- **CI/CD:** GitHub Actions + Coolify
- **Reverse proxy:** Caddy (auto Let's Encrypt)
- **Secrets:** Doppler Free
- **Remote access:** Tailscale Free
- **Firmware Sub Node:** AVR-GCC + PlatformIO + RadioLib
- **Firmware Main Node:** ESP-IDF 5.x + PlatformIO + Arduino-ESP32 + RadioLib
- **Deferred (post-pilot):** razorpay SDK (Phase 14), MSG91 SMS (Phase 13)

## 0.3 Single-VPS topology

```
                       Internet (Cloudflare DNS + Tunnel)
                                      │
                                      ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │  AWS Lightsail Mumbai (ap-south-1a) · $20/month plan            │
   │  2 vCPU · 4 GB RAM · 80 GB SSD · Ubuntu 22.04 LTS (x86_64)     │
   │                                                                  │
   │  ┌──────────┐                                                   │
   │  │  Caddy   │  :443/:8883/:80, auto Let's Encrypt              │
   │  └────┬─────┘                                                   │
   │       │                                                          │
   │   ┌───┼────────────────┬─────────────┬────────────────────┐    │
   │   ▼   ▼                ▼             ▼                    ▼    │
   │  ┌──────────┐  ┌──────────────┐  ┌─────────┐   ┌──────────────┐│
   │  │ FastAPI  │  │ Mosquitto    │  │ Coolify │   │ Streamlit    ││
   │  │ + APS    │  │ MQTT broker  │  └─────────┘   └──────────────┘│
   │  └────┬─────┘  └──────┬───────┘                                ││
   │       │               │                                         │
   │       ▼               ▼                                         │
   │  ┌──────────────────────────────────────────────────────┐      │
   │  │  Postgres 15 (PostGIS + pgvector + pgcrypto)         │      │
   │  └──────────────────────────────────────────────────────┘      │
   │  ┌──────────────────────────────────────────────────────┐      │
   │  │  ChromaDB persistent  @ /data/chroma                 │      │
   │  └──────────────────────────────────────────────────────┘      │
   │  ┌──────────────────────────────────────────────────────┐      │
   │  │  Prometheus + Grafana (Tailscale-only)               │      │
   │  └──────────────────────────────────────────────────────┘      │
   │                                                                  │
   │  Outbound: Backblaze B2, Cloudflare R2, Anthropic, Meta WA,    │
   │            FCM, Open-Meteo, IMD, Copernicus, NASA Earthdata    │
   └──────────────────────────────────────────────────────────────────┘
```

## 0.4 Pre-flight checklist (v1.2 — AWS Lightsail)

Items in **bold** have multi-day external lead times — kick them off on day 1; the rest are 5–30 min self-serve signups.

1. **AWS account setup.** If you don't already have one: go to `aws.amazon.com` → "Create AWS Account" → enter email, password, billing address, credit card, phone (instant SMS OTP), pick **Basic Support (free)**. Activation is usually instant; sometimes takes a few minutes. Cost discipline: enable **Billing Alerts** at $30/mo from day 1 (Billing → Budgets → Create budget → email alert at $30). This catches any surprise spend before it hurts.

2. **Provision Lightsail instance.** Console → Lightsail → "Create instance":
   - Instance location: **Mumbai (ap-south-1)**, Availability Zone A
   - Platform: Linux/Unix
   - Blueprint: **OS Only → Ubuntu 22.04 LTS**
   - Instance plan: **$20/month** (2 vCPU, 4 GB RAM, 80 GB SSD, 3 TB egress)
   - Identify your instance: `agro-prod-01`
   - SSH key: upload your `~/.ssh/id_rsa.pub` (or generate one — Lightsail will offer)
   - Click "Create instance". Provisioning takes ~60 seconds.

3. **Attach a static IP** (free as long as it's attached). Lightsail → Networking tab → "Create static IP" → attach to `agro-prod-01`. Note this IP on a sticky note.

4. **Enable automatic snapshots.** Lightsail → your instance → Snapshots tab → "Enable automatic snapshots" → daily at 03:00 IST. Cost: ~$4/mo for an 80 GB instance, kept 7 days rolling.

5. **Domain — DEFERRED.** Brand name not finalized, not a blocker. Use `sslip.io` for the prototype: `api-<your-static-ip-with-dashes>.sslip.io` resolves automatically without DNS configuration. Caddy + Let's Encrypt HTTP-01 challenge works against it out of the box. When you lock the brand, buy the domain via Cloudflare Registrar and change one line in `deploy/caddy/Caddyfile`.

6. **Create Anthropic API account** at console.anthropic.com. Add $20 initial credit.

7. **Register at developers.facebook.com** → create app → add WhatsApp product. Verify the farmer's phone and founders' phones as test recipients. **Submit BOTH the OTP `authentication` template and the advisory template in the same session.** Approval takes 24–48 h. Note: Meta requires a Business display name — use a placeholder like "AgroGuardian Prototype" if legal name isn't finalized; you can rename later.

8. **Register at urs.earthdata.nasa.gov** (free, 24-hour approval).

9. **Register at dataspace.copernicus.eu** (free, instant OAuth credentials).

10. Sign up for Backblaze B2 (10 GB free), Cloudflare R2 (10 GB free), Better Stack Free, Sentry Free, UptimeRobot Free, Doppler Free, Tailscale Free.

11. Create GitHub organization + private repo `agroguardian` (or `agroguardian-prototype` — GitHub allows renaming with redirects).

12. Install Cursor IDE; connect to Anthropic API key.

**Start in parallel but not blocking:** Razorpay KYC + sole proprietorship registration. Takes 5–7 days; you'll need it before Phase 14 but the pilot ships without it.

**Why the domain isn't a blocker — concrete example:**

Today, your AWS Lightsail static IP is (say) `13.235.50.100`. Caddy will issue a valid Let's Encrypt cert for `api-13-235-50-100.sslip.io` because `sslip.io` resolves any subdomain of the form `*-A-B-C-D.sslip.io` to IP `A.B.C.D`. From the cert authority's perspective, this is a real public DNS name. The farmer app talks to `https://api-13-235-50-100.sslip.io/api/v1/...`. When you lock the brand and buy `agroguardian.in`, you:
1. Add an A record at Cloudflare pointing `api.agroguardian.in` to the same IP
2. Change one line in `Caddyfile`: `api-13-235-50-100.sslip.io {` → `api.agroguardian.in {`
3. `docker compose restart caddy` — Caddy reissues for the new hostname automatically
4. Update `EXPO_PUBLIC_API_URL` in the Expo app's env config
5. Done — no data migration, no certificate dance.

---

## 0.5 Provider Portability Charter (v1.2 — AWS edition)

This is the discipline that makes **AWS Lightsail a deployment target** and not a *dependency*. We treat Lightsail as "a Linux VPS that happens to be on AWS" — nothing more. Read this once and refer back any time Cursor (or you) considers introducing a vendor-specific service.

### Rule 1 — Use only commodity Linux services

The entire stack runs on a vanilla Ubuntu 22.04 VPS via Docker Compose. Nothing assumes AWS under the hood.

**Allowed:** Docker, Postgres, Mosquitto, Caddy, FastAPI, ChromaDB, Coolify, Tailscale, fail2ban, UFW, systemd — all of which run identically on any Ubuntu/Debian VPS from any provider.

**Forbidden in pilot code:** AWS Cognito (we use FastAPI-native auth), AWS S3 (Cloudflare R2 instead, S3-compat), AWS RDS (self-hosted Postgres), AWS SES (use WhatsApp/FCM for messaging), AWS Lambda (APScheduler does our crons), AWS SNS / SQS (Postgres NOTIFY/LISTEN), AWS CloudWatch (Prometheus + Grafana), AWS Secrets Manager (Doppler / env), AWS IAM Identity Center, AWS ALB/NLB (Caddy is our reverse proxy), AWS Route 53 (Cloudflare DNS), or the `boto3` SDK when used for *AWS-specific* services. If you reach for any AWS-specific managed service, stop — there's a provider-neutral equivalent already in the stack.

**Allowed AWS usage (Lightsail itself, only):** the Lightsail web console for provisioning + firewall + snapshots + DNS zone reading. None of this is in code; it's all clickops. Code is provider-agnostic.

**Permitted use of `boto3`/`aioboto3`:** ONLY for S3-compatible APIs against Cloudflare R2 and Backblaze B2 (both use S3 protocol). The endpoint URL is configurable via env (`R2_ENDPOINT_URL`, `B2_ENDPOINT_URL`) — never hardcoded to `s3.amazonaws.com`.

### Rule 2 — All persistent state in provider-portable services

| State | Where it lives | Why it's portable |
|---|---|---|
| Postgres | Self-hosted Docker container on the VPS, bind-mounted volume | `pg_dump` + `pg_restore` migrate any Postgres to any Postgres in 30 minutes |
| ChromaDB | Self-hosted Docker container, bind-mounted volume | `/data/chroma` is a flat file index — `tar` and `scp` it anywhere |
| Object storage (rasters, photos, firmware) | **Cloudflare R2** (S3-compatible API) | Independent of compute provider. Zero egress fees mean restoration cost is fixed |
| Cold backups | **Backblaze B2** (S3-compatible API) | Independent of compute provider |
| DNS + CDN | **Cloudflare** | Works against any IP from any provider |
| Secrets | **Doppler** (or env vars) | Doppler sync works to any host; env vars are universal |
| Vector embeddings | Computed locally by `sentence-transformers` (CPU) | No managed embedding service to lock into |

### Rule 3 — Connection-string-only configuration

Every external service is connected via a **single environment variable** that is provider-agnostic:

```
DATABASE_URL=postgresql+asyncpg://user:pwd@host:5432/agro
MQTT_BROKER_HOST=mosquitto
R2_ACCESS_KEY_ID=...           # S3-compatible
B2_KEY_ID=...                  # S3-compatible
ANTHROPIC_API_KEY=...
```

There is no `AWS_ACCESS_KEY_ID`, `AWS_REGION`, or `LIGHTSAIL_INSTANCE_ID` anywhere in the codebase. The fact that we're on AWS is configured by the **deploy environment**, not by code.

### Rule 4 — Infra-as-code is Docker Compose, not Terraform-against-AWS

`docker-compose.prod.yml` is the deployment manifest. Coolify reads it and runs it. The same file runs unchanged on:
- AWS Lightsail Mumbai (current)
- AWS EC2 (any size — direct upgrade path when scale forces it)
- DigitalOcean Bangalore
- Linode Mumbai
- Hetzner Cloud
- Oracle Cloud (if it ever works)
- A laptop in a co-founder's office

Only the IP in the Caddyfile and the volume size change per provider.

**No Terraform, no CloudFormation, no CDK.** The Lightsail console clickops are documented in Part 12.2. When we outgrow Lightsail (Phase 2+, ~200 farms), we migrate to EC2 + RDS following the same Rule 5 procedure below — not by rewriting infrastructure in Terraform.

### Rule 5 — Two-hour migration procedure

If you ever need to move off AWS Lightsail (to EC2, DO, Hetzner, anywhere else):

1. Provision the new VPS (any Linux, ≥ 2 vCPU / 4 GB / 80 GB SSD). 15 min.
2. Install Docker + Coolify on the new host (same one-liner). 15 min.
3. Take a fresh `pg_dump --format=custom` + `tar czf chroma.tar.gz /data/chroma` on the current Lightsail. 10 min.
4. `scp` both to the new host; `pg_restore` and `tar xzf` to restore. 20 min.
5. Update the Cloudflare A record (or sslip.io hostname if still on that) to the new IP. 5 min.
6. Update `META_WHATSAPP_VERIFY_TOKEN` callback URL in Meta dashboard. 5 min.
7. Restart device fleet or wait for next MQTT reconnect (devices cache the broker host in flash; push a `cmd` via the existing channel to refresh sooner). 30 min if pushed.

**Total: ~2 hours zero-downtime, or 4 hours with a verification window.**

The fact that we use AWS today changes none of these steps. Same procedure as moving from Oracle would have been. Same procedure as moving from DigitalOcean would be. The hexagon doesn't care.

### Rule 6 — Things that ARE intentionally vendor-specific (and that's fine)

These are **product-level** choices, not infra-level:

- **Anthropic** (LLM) — hexagonal `LlmClient` Protocol; Gemini/Llama swap is one file (Part 12.6)
- **Meta WhatsApp Cloud API** — hexagonal `WhatsAppClient` Protocol; swap to Gupshup/Twilio is one file
- **Razorpay** (Phase 14) — hexagonal `PaymentClient` Protocol; swap to Cashfree is one file
- **Copernicus + NASA** — these are the data providers; abstracted behind `SatelliteClient`

Each lives behind a port. None of them depends on AWS being the compute host.

### Cursor enforcement

Append this to `.cursorrules` (Part 10.2):

```
25. Never reference AWS-specific managed services in code: no Cognito, no SES,
    no Lambda, no SNS/SQS, no RDS, no CloudWatch, no Secrets Manager, no DynamoDB,
    no Route 53, no ALB/NLB, no IAM Identity Center, no Step Functions, no EventBridge.
    The provider-neutral equivalent is already in the stack — check Part 0.5 Rule 2.
    boto3/aioboto3 are ALLOWED but ONLY against Cloudflare R2 and Backblaze B2
    (S3-compatible endpoints — always configure via R2_ENDPOINT_URL / B2_ENDPOINT_URL
    env vars, never hardcode 's3.amazonaws.com').
```

This single rule guarantees you can move off AWS in an afternoon two years from now if pricing changes or quotas vanish.

---

## 0.6 Fast Path to Working Prototype (2-week MVP track)

The 12-week pilot plan builds the full production system. If you want a **demoable prototype faster** — for a co-founder, an investor, the farmer, or yourself — here's the 2-week subset of the same phases. **Nothing in this fast path compromises the foundation.** It just defers what the demo doesn't need.

### Days 1–3 — Foundation (Phase 0 + Phase 1)

- AWS Lightsail VPS provisioned, Docker Compose stack up
- Caddy on `sslip.io` issuing real Let's Encrypt SSL
- Postgres + Mosquitto + ChromaDB + FastAPI running
- All 35 tables created with RLS + audit log
- Pilot tenant + 1 farmer + 1 farm + 4 plots seeded
- CI green, Coolify auto-deploying on push to main

**Defer from full Phase 1:** the materialized view refresh cron — schema views exist (empty); the cron lands in Phase 4.

### Days 4–6 — Ingest demo (Phase 2)

- pydantic schemas + 4-gate validation + idempotent UPSERT
- Fake Main Node publisher emitting 4 plots × 96 cycles/day of realistic telemetry
- `/metrics` Prometheus endpoint live
- Telemetry flowing end-to-end: synthetic → Mosquitto → FastAPI → Postgres

**Defer:** satellite + forecast ingest (Phase 6) waits for Days 8–9 if you have time, or post-prototype.

### Days 7–8 — Auth (Phase 3)

- WhatsApp OTP flow live (Meta test mode, 5 verified recipients)
- JWT issuance + refresh + RLS verified end-to-end
- Read endpoints: `/me`, `/me/farms`, `/plots/{id}/state`, `/plots/{id}/sensor_history`

**Defer:** the Expo farmer app (Phase 9). The demo runs through `curl` + a tiny Streamlit "farmer view" page.

### Days 9–11 — AI advisory generation (Phase 5, slimmed)

- Anthropic adapter (Sonnet for T1, Haiku for T2)
- Rule JSON files for sugarcane + ginger + universal-safety
- ChromaDB indexing + retrieval working
- T1 prompt template rendered + sent
- Advisory generation cron at 02:30 IST writing real `ai_suggestions` rows
- Confidence scoring + band classification

**Defer:** T3 chat (5.6) and T4 outcome reflection (5.7). The demo shows one good Marathi advisory per plot per day — that's the wow moment.

### Days 12–14 — Founder demo dashboard (Phase 10, slimmed)

- Streamlit auth shell
- Live Operations view (one row per plot, live data)
- Single-Farm Deep-Dive view (sensor charts + latest advisory)
- Agronomist Queue view (read-only — approve/reject flow comes with full Phase 10)

**Defer:** AI Accuracy view, Device Health view, Ops Console — all post-prototype.

### What the prototype proves at Day 14

✅ Hexagonal architecture intact (domain layer importable with no framework deps)
✅ Telemetry flows end-to-end with idempotency + validation
✅ Auth works with real WhatsApp OTP
✅ Claude Sonnet generates a real Marathi advisory based on real (synthetic) sensor data
✅ Agronomist can see the full pipeline in a single dashboard view
✅ Infrastructure is one-afternoon-portable to another provider
✅ Total infra cost: **~$28/month** (Lightsail $20 + snapshots $4 + B2 $1 + LLM $3, free-tier monitoring)

### Deferred to weeks 3–12

- Real hardware (Phase 8 firmware) — until then, fake Main Node publishes
- Expo farmer app (Phase 9) — until then, Streamlit suffices
- Satellite + forecast ingest (Phase 6) — sensor data alone is enough for demo
- T3 chat + T4 outcome reflection (5.6–5.7) — daily advisory is the demo hook
- Notification dispatch (Phase 7) — dashboard renders advisories; nothing to send yet
- OTA + signing (Phase 8.3) — no devices to update
- Quota scaffolding (Phase 11) — `pilot_internal` tier is fine
- Calibration + ops console (Phase 12) — post-prototype

### Day-14 success criteria

You should be able to:
1. SSH into your Lightsail instance (`ssh -i ~/.ssh/agro_lightsail.pem ubuntu@<static-ip>`), run `docker compose ps`, see all containers healthy
2. Run `python scripts/dev/fake_main_node.py --duration 60` and watch rows appear in `node_sensor_readings`
3. Trigger the advisory cron (`POST /api/v1/admin/cron/run/advisory_generation`) and see new rows in `ai_suggestions` with realistic Marathi text
4. Log into the Streamlit dashboard at `https://dashboard-<ip>.sslip.io` and see 4 plots with their latest advisories rendered
5. Walk the demo without a single "well, that's not built yet" moment for the core flow

### Code-quality non-negotiables (even on the fast path)

The user explicitly asked for no quality compromise, so these still apply at every Phase prompt:

- **Hexagonal layering:** domain layer has zero framework imports. Verify after each Phase by importing `app.domain.*` in a plain Python REPL.
- **Repository pattern:** every DB access goes through a repo class; routes never write raw SQL.
- **Type-annotated everything:** mypy strict mode green at all times.
- **Coverage gate 80% in CI:** no exceptions during the fast path. Cursor writes tests with the implementation, not after.
- **Migrations always reversible:** every Alembic file has a `downgrade()`.
- **Multi-arch Docker images** (`linux/amd64` + `linux/arm64`) verified in CI. Pilot runs `amd64` on Lightsail x86_64; the `arm64` build keeps the door open for Graviton EC2 t4g instances later.
- **Secrets never in repo:** `.env.example` only.
- **Audit log on every master table write:** Phase 1 sets this up; never silenced later.

The fast path is about **reducing surface area for the prototype**, not about cutting corners on the surface you do build.

---

# PART 1 — System Architecture (Hexagonal)

## 1.1 Mental model

The codebase is a **hexagon**. At the core: domain logic that knows nothing about FastAPI, Postgres, MQTT, Anthropic, Meta, or any framework. Around it:

- **Inbound adapters (ports IN):** HTTP routes (FastAPI), MQTT subscribers, webhook handlers, CLI. They translate external input into pure domain dataclasses, call use cases, translate domain output back.
- **Outbound adapters (ports OUT):** Postgres repositories, ChromaDB repo, Anthropic client, FCM + WhatsApp adapters, Copernicus + NASA clients. The **only** places that touch I/O.

Use cases call outbound adapters via **Protocols**, never concrete classes. Swapping any adapter is one new file with zero domain or use-case changes.

## 1.2 Component diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        INBOUND ADAPTERS                            │
│  HTTP API (FastAPI)  ·  MQTT subscriber  ·  Webhook handlers       │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                      APPLICATION (use cases)                       │
│  IngestTelemetry  ·  GenerateAdvisory  ·  DispatchAlert  ·         │
│  ChangeCrop  ·  SendOtp  ·  VerifyOtp  ·  FarmerChat  ·            │
│  CheckQuota  ·  HandlePaymentEvent (Phase 14)                      │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                            DOMAIN                                  │
│  Pure dataclasses + pure functions.                               │
│  Sensor, Plot, CropSeason, SuggestionCandidate, Severity, etc.    │
│  Derived metrics, rule engine, confidence scoring, tier limits.   │
└────────────────────────────────────────────────────────────────────┘
                                ▲
                                │ (Protocols only)
┌────────────────────────────────────────────────────────────────────┐
│                       OUTBOUND ADAPTERS                            │
│  PgPlotRepo · PgReadingRepo · ChromaRuleRepo ·                     │
│  AnthropicClient (Sonnet + Haiku) ·                                │
│  FcmAdapter · WhatsAppAdapter (advisory + OTP) ·                   │
│  CopernicusSentinel2 · NASAEarthdataSMAP ·                         │
│  OpenMeteoForecast · IMDForecast · PgNotifyEventBus                │
│  [Phase 13] SmsMsg91Adapter   [Phase 14] RazorpayClient            │
└────────────────────────────────────────────────────────────────────┘
```

## 1.3 Domain events via Postgres NOTIFY/LISTEN

Zero new infra. Producers call `events.publish(name, payload)` → `NOTIFY agro_events, '<json>'`. Consumers run a long-lived `LISTEN` task. Swap to NATS/Redis Streams later via one adapter.

Catalogue:

| Event | Producer | Consumer(s) |
|---|---|---|
| `telemetry.ingested` | Ingest worker | Hot-rule evaluator, dashboard live view |
| `alert.created` | Rule engine | Notification dispatcher |
| `alert.dispatched` | Dispatcher | Metrics, audit log |
| `plot.crop_changed` | Crop-change use case | T1 advisory pre-generator |
| `suggestion.generated` | T1 advisory job | Dashboard, learning loop |
| `device.offline` / `.online` | Health watchdog | Ops alerts |
| `subscription.state_changed` | Razorpay handler (Phase 14) | Quota enforcement, UI banner |

## 1.4 Auth model — WhatsApp OTP

Flow:

1. Farmer enters phone in app → `POST /api/v1/auth/otp/request {phone_e164}`
2. Backend generates 6-digit code; stores `bcrypt(code)` + 5-min expiry in `otp_codes`; sends via Meta Cloud API `authentication` template
3. Farmer receives WhatsApp message; types code into app
4. App → `POST /api/v1/auth/otp/verify {phone_e164, code}`
5. Backend validates; finds-or-creates `farmer` row; issues 15-min JWT + 30-day refresh token (hashed)
6. App stores tokens in expo-secure-store

**Why WhatsApp over SMS:** free during pilot (counts against the 1,000 free conversations/month), more reliable than SMS in India (no carrier filtering, no DLT registration), same channel the farmer uses for advisories. Meta's `authentication` template is pre-built for OTP delivery.

**Future flexibility:** `OtpDeliveryClient` Protocol means swapping in MSG91 SMS is one env-var change after Phase 13.

Admins/agronomists/technicians authenticate via email + password (Argon2id) — no WhatsApp dependency.

## 1.5 Tenancy

One tenant per organization. Pilot ships **one** tenant ("AgroGuardian Pilot — Aurangabad") with `tier='pilot_internal'`. Every tenant-scoped table has `tenant_id UUID NOT NULL`. RLS uses session variables set on every request:

```sql
SET LOCAL app.current_tenant_id = '<uuid>';
SET LOCAL app.current_user_role = 'farmer';
SET LOCAL app.current_farmer_id = '<uuid>';
```

Policies reference `current_setting('app.current_tenant_id', true)::uuid`. The `, true` returns null instead of erroring when unset (important for cron jobs).

## 1.6 Storage architecture

| Bucket | Contents | Retention | Access |
|---|---|---|---|
| Cloudflare R2 `agro-rasters` | Sentinel-2 raster crops | 90 days (R2 lifecycle rule) | service-token; signed URLs |
| Cloudflare R2 `agro-photos` | Farmer photos (Phase 2) | Forever | service-token; signed URLs |
| Cloudflare R2 `agro-firmware` | OTA binaries, ed25519-signed | Last 5 per device class | service-token write; signed read |
| Backblaze B2 `agro-backups` | Weekly pg_dump.gz | 12-week rolling + last-of-quarter | service-token only |
| Local VPS volume `/data/chroma` | ChromaDB index | Until rebuilt | process-local |

## 1.7 Background job topology

| Job | Cadence | Owner |
|---|---|---|
| MQTT ingest (always-on) | continuous asyncio task | Ingest worker |
| Hot-rule evaluation | per-message synchronous | Ingest worker |
| Hourly aggregate refresh | every 5 min (trailing 2 h) | APScheduler |
| Daily aggregate refresh | 02:00 IST | APScheduler |
| Crop-stage update | 02:00 IST | APScheduler |
| Sentinel-2 + SMAP ingest | 03:00 IST | APScheduler |
| Open-Meteo forecast pull | every 6 h | APScheduler |
| IMD forecast pull (Jun-Oct) | every 6 h | APScheduler |
| T1 morning advisory generation | 02:30 IST | APScheduler |
| Notification dispatch | every 30 s drain | APScheduler |
| Retention purge (drop old partitions) | 03:00 IST | APScheduler |
| Partition rotation (create next month) | 1st of month 01:00 IST | APScheduler |
| Weekly pg_dump → Backblaze B2 | Sunday 03:00 IST | APScheduler |
| Outcome reflection (T+7 / T+14) | 04:00 IST daily | APScheduler |
| Agronomist queue sample | 1st of month 04:00 IST | APScheduler |
| Device offline watchdog | every 5 min | APScheduler |

## 1.8 Logging, metrics, monitoring

- **Logs:** structlog JSON to stdout → shipped to Better Stack
- **Metrics:** prometheus-client at `/metrics` (Tailscale-only) → scraped by self-hosted Prometheus → Grafana
- **Uptime:** UptimeRobot pinging `https://api.agroguardian.in/health` every 5 min from 3 regions
- **Errors:** Sentry SDK in FastAPI + RN app
- **Critical alerts:** UptimeRobot + Better Stack → email + Telegram bot

Counter set:
- `ingest.{received,parse_error,duplicate,unknown_tenant}`
- `validation.fail.{range,stuck,outlier,cross_sensor}`
- `dispatch.{success,failure}.{fcm,whatsapp}`
- `llm.calls.{sonnet,haiku}`, `llm.tokens.{model}`, `llm.cost_inr.{model}`
- `auth.otp.{requested,verified.success,verified.fail}` (labeled by transport)

---

# PART 2 — Database Design

## 2.1 Operational reality

Postgres 15 is operationally boring at pilot scale. Required ops:
- Weekly `pg_dump` → B2 (Phase 12)
- Autovacuum/analyze (defaults are fine for our row volume)
- Monthly partition rotation (Phase 1 cron)

Not needed at pilot: replication, PgBouncer pooling, read replicas, Timescale extension, PITR.

## 2.2 The 21 source tables + 14 v3 additional tables

**Source 21 tables (from the technical reference):**
`farmers, farms, plots, crop_seasons, node_sensor_readings, weather_station_readings, satellite_data, weather_forecasts, electricity_schedule_log, irrigation_events, water_source_status, ai_suggestions, farmer_actions, ai_learning_log, device_registry, component_inventory, technician_installations, service_maintenance, alerts_notifications, subscriptions_billing, product_performance_bi`

**14 v3 additional tables:**

| Table | Purpose |
|---|---|
| `tenants` | One row per organization. Includes `tier` column. |
| `users` | Admin/agronomist/technician accounts with Argon2id password hash |
| `otp_codes` | Phone OTP store with expiry, transport (`whatsapp` in pilot), single-use marker |
| `refresh_tokens` | Hashed refresh tokens with revocation |
| `audit_log` | Trigger-driven write log on master tables |
| `notification_dispatch_log` | Per-channel delivery receipts |
| `notification_dlq` | Dead-letter queue for failed dispatch |
| `ingest_unmatched` | Quarantine for unknown tenant/farm/device triplets |
| `event_outbox` | Optional transactional outbox |
| `feature_flags` | Per-tenant feature toggles |
| `system_config` | Hot-reloadable runtime config |
| `chat_messages` | T3 farmer chat history (90-day rolling) |
| `calibration_history` | Lab calibration log per device per sensor |
| `wa_inbound_log` | Inbound WhatsApp messages (for 24-h window logic, advisory + OTP unified) |

## 2.3 Schema patches over source

1. **Extensions:** `uuid-ossp`, `postgis`, `vector`, `pgcrypto`
2. **`plots.node_id` nullable** + `data_tier` enum (`'satellite_only' | 'sub_node'`) + BEFORE trigger that keeps `data_tier` consistent with `node_id`
3. **Time-series tables converted to monthly range-partitioned** with 13 months pre-created + rotation cron
4. **RLS via `current_setting('app.current_*')`** instead of `auth.jwt()` (Supabase-only)

## 2.4 v3 column additions

| Table | Column | Reason |
|---|---|---|
| `node_sensor_readings` | `soil_temp_rootzone_c REAL` | DS18B20 separate from NPK probe head |
| `node_sensor_readings` | `soil_N_bucket SMALLINT`, `soil_P_bucket`, `soil_K_bucket` | What was transmitted on LoRa |
| `node_sensor_readings` | `cadence_mode TEXT CHECK (...)` | Mode-driven cadence |
| `node_sensor_readings` | `backlog_pending BOOLEAN`, `validation_warn BOOLEAN`, `low_battery_flag BOOLEAN` | Per-row flags |
| `plots` | `data_tier TEXT NOT NULL DEFAULT 'satellite_only'` | §1.3 of technical ref |
| `device_registry` | `broker_secret_hash TEXT` | Per-device MQTT bcrypt |
| `device_registry` | `calibration_json JSONB DEFAULT '{}'` | Per-sensor slope/intercept |
| `ai_suggestions` | `prompt_template_version TEXT`, `ai_model_version TEXT`, `tokens_used INT`, `llm_cost_inr NUMERIC(10,4)` | Cost / replay traceability |
| `farmers` | `phone_hash BYTEA`, `phone_encrypted BYTEA` | pgcrypto + indexable hash |
| `crop_seasons` | `sowing_date_inferred BOOLEAN DEFAULT FALSE` | True for Plot 3 satellite-inferred |
| `tenants` | `tier TEXT NOT NULL DEFAULT 'basic' CHECK (...)`, `features JSONB DEFAULT '{}'` | Tier-aware quotas |
| `otp_codes` | `transport TEXT NOT NULL CHECK (transport IN ('whatsapp','sms'))`, `wa_message_id TEXT`, `attempts INT DEFAULT 0` | Pluggable OTP transport |

## 2.5 Materialized views

- `node_readings_hourly` — refresh every 5 min (trailing 2 h)
- `node_readings_daily` — refresh nightly 02:00 IST
- `weather_hourly` — same cadence as node_readings_hourly
- `weather_daily` — same cadence as node_readings_daily

Plus non-materialized view `v_plot_latest_state` for dashboard (computed at query time).

`REFRESH MATERIALIZED VIEW CONCURRENTLY` requires a unique index on every view — created in the migration.

## 2.6 Indexes that matter

```sql
-- Idempotency (drives ingest UPSERT)
CREATE UNIQUE INDEX node_sensor_readings_idem ON node_sensor_readings (node_id, recorded_at);

-- Hot-path queries: "last 24h of plot X"
CREATE INDEX node_sensor_readings_plot_time ON node_sensor_readings (plot_id, recorded_at DESC);
CREATE INDEX node_sensor_readings_farm_time ON node_sensor_readings (farm_id, recorded_at DESC);
CREATE INDEX node_sensor_readings_tenant_time ON node_sensor_readings (tenant_id, recorded_at DESC);

-- Satellite — typical query "latest for plot"
CREATE INDEX satellite_data_plot_date ON satellite_data (plot_id, image_date DESC);

-- Events
CREATE INDEX ai_suggestions_plot_generated ON ai_suggestions (plot_id, generated_at DESC);
CREATE INDEX alerts_notifications_pending ON alerts_notifications (dispatch_status, severity)
  WHERE dispatch_status = 'pending';

-- Auth
CREATE INDEX otp_codes_phone_unverified ON otp_codes (phone_e164, created_at DESC)
  WHERE verified_at IS NULL AND expires_at > now();
CREATE UNIQUE INDEX users_email_lower ON users (LOWER(email));
CREATE UNIQUE INDEX farmers_phone_hash ON farmers (phone_hash);
```

## 2.7 Retention rules

| Table | Raw | Aggregate |
|---|---|---|
| `node_sensor_readings` | 90 days (drop month-partitions) | hourly: 2 yr · daily: forever |
| `weather_station_readings` | 90 days | hourly: 2 yr · daily: forever |
| `weather_forecasts` | 14 days | none |
| `satellite_data` | indices: forever · raster cache: 90 days | none |
| `ai_suggestions`, `farmer_actions`, `ai_learning_log`, `alerts_notifications` | forever | none |
| `chat_messages` | 90 days | none |
| `otp_codes` | 30 days | none |
| `audit_log` | forever | none |

## 2.8 RLS policy template

```sql
ALTER TABLE plots ENABLE ROW LEVEL SECURITY;

-- Tenant isolation
CREATE POLICY plots_tenant_iso ON plots
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Read: farmer sees own; admin/agronomist/technician/service see all (within tenant)
CREATE POLICY plots_read ON plots
  FOR SELECT TO authenticated_role
  USING (
    current_setting('app.current_user_role', true) IN ('admin','agronomist','service','technician')
    OR farmer_id = current_setting('app.current_farmer_id', true)::uuid
  );

-- Write: admin + technician only
CREATE POLICY plots_write ON plots
  FOR INSERT, UPDATE, DELETE TO authenticated_role
  USING (current_setting('app.current_user_role', true) IN ('admin','technician'))
  WITH CHECK (current_setting('app.current_user_role', true) IN ('admin','technician'));

-- Service role bypasses RLS for ingest + cron
ALTER ROLE service_role BYPASSRLS;
```

---

# PART 3 — API Architecture

All endpoints under `/api/v1/`. Pagination via cursor (`{last_id, last_ts}` base64-encoded). Errors via RFC 7807 problem+json. Idempotency keys on POSTs that create resources.

## 3.1 Farmer routes (pilot)

```
POST   /api/v1/auth/otp/request          # {phone_e164} → 204; sends WhatsApp OTP
POST   /api/v1/auth/otp/verify           # {phone_e164, code} → {access_token, refresh_token, expires_in}
POST   /api/v1/auth/refresh              # {refresh_token} → new pair (single-use rotation)
POST   /api/v1/auth/logout               # revokes refresh

GET    /api/v1/me
PATCH  /api/v1/me                        # update lang, notification_preferences
POST   /api/v1/me/fcm_token              # register/refresh FCM token
GET    /api/v1/me/farms

GET    /api/v1/farms/{farm_id}/plots
GET    /api/v1/plots/{plot_id}/state     # v_plot_latest_state
GET    /api/v1/plots/{plot_id}/sensor_history?hours=N
GET    /api/v1/plots/{plot_id}/satellite_history?weeks=N
GET    /api/v1/plots/{plot_id}/forecast?days=N
GET    /api/v1/plots/{plot_id}/suggestions?limit=N
GET    /api/v1/plots/{plot_id}/alerts?limit=N
POST   /api/v1/plots/{plot_id}/alerts/{alert_id}/acknowledge
POST   /api/v1/plots/{plot_id}/farmer_actions
POST   /api/v1/plots/{plot_id}/crop_change
POST   /api/v1/plots/{plot_id}/boundary/walk
POST   /api/v1/plots/{plot_id}/boundary/draw
POST   /api/v1/plots/{plot_id}/force_refresh   # rate-limited 4/h/device

POST   /api/v1/chat                      # SSE-streaming T3
GET    /api/v1/chat/history?limit=50
```

## 3.2 Admin / agronomist / technician routes

```
POST   /api/v1/auth/login                # {email, password}

GET    /api/v1/admin/devices
POST   /api/v1/admin/devices             # provision; returns plain MQTT secret ONCE
POST   /api/v1/admin/devices/{device_id}/cmd
POST   /api/v1/admin/ota/upload
POST   /api/v1/admin/ota/release/{manifest_id}/{canary|promote|abort}
POST   /api/v1/admin/calibration/update
POST   /api/v1/admin/cron/run/{job_name}
GET    /api/v1/admin/ingest/stats

GET    /api/v1/agronomist/queue
POST   /api/v1/agronomist/suggestions/{id}/approve
POST   /api/v1/agronomist/suggestions/{id}/edit_and_approve
POST   /api/v1/agronomist/suggestions/{id}/reject
GET    /api/v1/admin/ai_accuracy?from=&to=
```

## 3.3 Webhooks (pilot)

```
POST   /api/v1/webhooks/whatsapp/inbound     # Meta inbound messages
POST   /api/v1/webhooks/whatsapp/delivery    # Meta delivery receipts
```

## 3.4 Internal

```
GET    /api/v1/health                    # liveness
GET    /api/v1/ready                     # readiness (checks DB + MQTT + Chroma)
GET    /metrics                          # Prometheus (Tailscale-only)
```

## 3.5 Deferred (Phase 14)

```
POST   /api/v1/billing/subscribe
POST   /api/v1/billing/portal
GET    /api/v1/billing/status
POST   /api/v1/webhooks/razorpay
```

## 3.6 Conventions

- Timestamps: ISO-8601 UTC with `Z`
- Money: `Decimal` in Python, `NUMERIC(12,2)` in DB; never float
- IDs: UUID v4 except where schema doc specifies a string ID
- Marathi strings: UTF-8, max 4 KB per message
- Pagination: opaque base64 cursor `{last_id, last_ts}`
- Idempotency: client supplies `Idempotency-Key` header on creating POSTs; server caches result by key for 24 h
- Rate limiting: `slowapi`, in-process LRU keyed by `farmer_id` or IP

---

# PART 4 — Frontend Architecture

## 4.1 Farmer app (React Native + Expo SDK 51)

```
agro_app/
├── app.config.ts                    # Expo config (typed)
├── tsconfig.json
├── package.json
├── eas.json
├── src/
│   ├── api/
│   │   ├── client.ts                # openapi-fetch + JWT interceptor
│   │   ├── types.gen.ts             # generated from /openapi.json
│   │   ├── refresh.ts               # silent refresh flow
│   │   └── queries/                 # React Query hooks
│   ├── auth/
│   │   ├── otp.ts                   # WhatsApp OTP flow
│   │   ├── jwt.ts                   # SecureStore + decode + expiry
│   │   └── store.ts                 # zustand auth slice
│   ├── components/
│   │   ├── AdvisoryCard.tsx
│   │   ├── SensorCard.tsx
│   │   ├── ChartHistory.tsx
│   │   ├── ChatBubble.tsx
│   │   ├── ConfidenceBadge.tsx
│   │   └── primitives/              # Button, Card, Text, Input
│   ├── i18n/
│   │   ├── index.ts
│   │   ├── mr.json                  # Marathi (default)
│   │   └── en.json
│   ├── screens/
│   │   ├── Login.tsx                # WhatsApp OTP UX
│   │   ├── HomeTab.tsx
│   │   ├── SensorsTab.tsx
│   │   ├── PlotDetail.tsx
│   │   ├── ChatTab.tsx
│   │   ├── SettingsTab.tsx
│   │   ├── CropChangeWizard/
│   │   │   ├── Step1.tsx ... Step6.tsx
│   │   │   └── index.tsx
│   │   └── BoundaryWalk.tsx
│   ├── store/
│   │   └── appStore.ts              # zustand
│   ├── lib/
│   │   ├── voice.ts                 # expo-speech Marathi STT/TTS
│   │   ├── push.ts                  # FCM token register/refresh
│   │   ├── geo.ts                   # GPS perimeter walk
│   │   ├── format.ts                # Marathi numerals, dates
│   │   └── analytics.ts
│   ├── theme/
│   │   └── colors.ts
│   └── App.tsx
└── tests/
```

Pinned packages (SDK 51-compatible): `expo-router`, `expo-secure-store`, `expo-notifications`, `expo-speech`, `expo-av`, `expo-location`, `expo-localization`, `react-native-maps`, `react-native-svg`, `react-native-gifted-charts` (or `victory-native` — pick after 2-day spike), `@tanstack/react-query`, `zustand`, `react-hook-form`, `zod`, `i18next`, `react-i18next`, `openapi-fetch`, `openapi-typescript` (dev).

## 4.2 Dashboard (Streamlit)

```
agro_dashboard/
├── streamlit_app.py
├── pages/
│   ├── 1_Live_Operations.py
│   ├── 2_Agronomist_Queue.py
│   ├── 3_Single_Farm_Deep_Dive.py
│   ├── 4_AI_Accuracy.py
│   ├── 5_Device_Health.py
│   └── 6_Ops_Console.py             # admin-only
├── components/
│   ├── auth.py                      # JWT cookie verification
│   ├── api_client.py
│   ├── sensor_cards.py
│   ├── alert_table.py
│   └── charts.py
├── requirements.txt
└── .streamlit/config.toml
```

## 4.3 Component conventions

- All Marathi strings in `i18n/mr.json`; never hard-code in JSX
- All API calls go through React Query hooks
- All forms use react-hook-form + Zod (mirroring backend pydantic)
- Auth: silent refresh 60 s before access-token expiry
- Date formatting: `lib/format.ts` only (Marathi numerals consistent)
- Each component exports default + named `Props` type

---

# PART 5 — Backend Folder Layout

```
agro_backend/
├── pyproject.toml
├── Dockerfile                       # multi-arch (linux/amd64 + linux/arm64)
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── .env.example
├── .cursorrules
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 0001_init_21_tables.sql
│       ├── 0002_v3_additional_tables.sql
│       ├── 0003_extensions.sql
│       ├── 0004_plots_satellite_only.sql
│       ├── 0005_partition_timeseries.sql
│       ├── 0006_aggregates.sql
│       ├── 0007_audit_log.sql
│       ├── 0008_rls_policies.sql
│       ├── 0009_event_outbox.sql
│       └── ...
│
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI() + lifespan + scheduler boot
│   ├── config.py                    # pydantic-settings BaseSettings
│   ├── deps.py                      # get_session, get_current_user, require_role
│   │
│   ├── domain/                      # PURE — no framework imports
│   │   ├── sensor.py
│   │   ├── plot.py
│   │   ├── alert.py
│   │   ├── suggestion.py
│   │   ├── derived_metrics.py
│   │   ├── crop_stage.py
│   │   ├── rules_engine.py
│   │   ├── confidence.py
│   │   ├── tier.py                  # Tier enum + TIER_LIMITS
│   │   ├── subscription.py          # state machine (Phase 14 wires effects)
│   │   └── exceptions.py
│   │
│   ├── application/
│   │   ├── ingest_telemetry.py
│   │   ├── evaluate_hot_rules.py
│   │   ├── generate_advisory.py
│   │   ├── dispatch_alert.py
│   │   ├── change_crop.py
│   │   ├── send_otp.py              # uses OtpDeliveryClient
│   │   ├── verify_otp.py
│   │   ├── farmer_chat.py
│   │   ├── check_quota.py           # no-op for pilot_internal
│   │   └── ports/
│   │       ├── __init__.py
│   │       ├── reading_repo.py      # Protocol
│   │       ├── plot_repo.py
│   │       ├── alert_repo.py
│   │       ├── suggestion_repo.py
│   │       ├── rule_repo.py
│   │       ├── llm_client.py
│   │       ├── fcm_client.py
│   │       ├── whatsapp_client.py
│   │       ├── sms_client.py        # PORT only; no pilot impl
│   │       ├── otp_delivery_client.py
│   │       ├── satellite_client.py
│   │       ├── forecast_client.py
│   │       └── event_bus.py
│   │
│   ├── infra/
│   │   ├── http/                    # FastAPI routes
│   │   ├── mqtt/                    # broker.py, schemas.py, validation.py
│   │   ├── persistence/             # Pg<X>Repo + SQLAlchemy models
│   │   ├── ai/                      # AnthropicClient (Sonnet + Haiku)
│   │   ├── satellite/               # CopernicusSentinel2, NASAEarthdataSMAP
│   │   ├── forecast/                # OpenMeteo, IMD
│   │   ├── notify/                  # fcm.py, whatsapp_meta.py (advisory + OTP)
│   │   ├── events/                  # pg_notify_bus.py
│   │   ├── storage/                 # r2_client.py, b2_client.py
│   │   └── ota/                     # signing, manifest, rollout
│   │
│   ├── jobs/
│   │   ├── scheduler.py
│   │   ├── aggregate.py
│   │   ├── retention.py
│   │   ├── partition_rotate.py
│   │   ├── crop_stage_update.py
│   │   ├── satellite_ingest.py
│   │   ├── forecast_pull.py
│   │   ├── advisory_generation.py
│   │   ├── outcome_reflection.py
│   │   ├── notify_drain.py
│   │   ├── monthly_review_sample.py
│   │   ├── pg_dump_backup.py
│   │   └── device_offline_watchdog.py
│   │
│   └── lib/
│       ├── time.py
│       ├── geo.py
│       ├── retry.py
│       ├── metrics.py
│       ├── logging.py
│       ├── otp.py
│       └── jwt.py
│
├── rules/
│   ├── universal/                   # U-SAFE-*.json
│   ├── sugarcane/                   # SG-*.json
│   └── ginger/                      # GN-*.json
│
├── firmware/
│   ├── sub_node/                    # PlatformIO ATmega328P
│   └── main_node/                   # PlatformIO ESP32
│
├── deploy/
│   ├── caddy/Caddyfile
│   ├── mosquitto/mosquitto.conf
│   ├── mosquitto/acl
│   └── coolify/
│
└── tests/
    ├── conftest.py
    ├── domain/                      # ONLY stdlib + numpy + shapely imports
    ├── application/                 # use cases with stubbed ports
    ├── infra/
    └── e2e/
```

**The critical discipline:** `app/domain/` has zero framework imports. You should be able to `import app.domain.derived_metrics` from a plain Python REPL with only `numpy + shapely` installed and it works. That's the test for whether the hexagon is intact.


---

# PART 6 — Development Phases

**Pilot critical path (Phases 0–12, ~12 weeks):**

| Phase | What | Days |
|---|---|---|
| 0 | Bootstrap + cloud infra | 2–3 |
| 1 | DB + RLS + audit log | 3–5 |
| 2 | MQTT ingest + validation + hexagonal repos | 5–7 |
| 3 | REST API + WhatsApp-OTP auth | 4–6 |
| 4 | Processing + rules + crop stages | 7–10 |
| 5 | AI / RAG / agent loop (Sonnet + Haiku) | 6–9 |
| 6 | Copernicus + NASA Earthdata + Open-Meteo | 5–7 |
| 7 | Notifications (FCM + WhatsApp) | 2–3 |
| 8 | Firmware + OTA | 10–15 (parallel) |
| 9 | Farmer app | 10–14 |
| 10 | Dashboard | 5–7 |
| 11 | Quota scaffolding + tier-aware no-op | 1–2 |
| 12 | Ops + calibration + backups | 5–10 |

**Post-pilot (before commercial launch):**

| Phase | What | Days |
|---|---|---|
| 13 | MSG91 SMS adapter + DLT registration | 2 |
| 14 | Razorpay subscriptions + UPI AutoPay | 4–5 |

---

## PHASE 0 — Project bootstrap + cloud infra (2–3 days)

**Goal:** every developer can `git clone → docker compose up → curl /health` locally. CI green. Coolify deploying on push to main. Cursor integrated with Anthropic.

**Files:** `pyproject.toml`, `Dockerfile` (multi-arch), `docker-compose.dev.yml`, `docker-compose.prod.yml`, `.env.example`, `.cursorrules`, `.gitignore`, `.github/workflows/ci.yml`, `app/main.py` (with `/health`), `app/config.py`, `alembic.ini`, `alembic/env.py`, `tests/conftest.py`, `tests/test_health.py`, `deploy/caddy/Caddyfile`, `deploy/mosquitto/mosquitto.conf`.

**Database tables:** none yet.

**APIs:** `GET /api/v1/health` → `{"status":"ok","version":"0.0.1","commit":"<sha>"}`.

**Dependencies (pip):**

Production: `fastapi`, `uvicorn[standard]`, `pydantic>=2.5`, `pydantic-settings`, `sqlalchemy[asyncio]>=2.0`, `asyncpg`, `alembic`, `structlog`, `httpx`, `paho-mqtt`, `anthropic`, `sentence-transformers`, `chromadb`, `apscheduler`, `prometheus-client`, `passlib[argon2]`, `python-jose[cryptography]`, `firebase-admin`, `sentry-sdk[fastapi]`, `slowapi`, `sentinelhub`, `earthaccess`, `shapely`, `geoalchemy2`, `rasterio`, `xarray`.

Dev: `pytest`, `pytest-asyncio`, `testcontainers[postgres]`, `ruff`, `mypy`, `respx`, `hypothesis`.

**Environment variables:**

```
# App
APP_ENV=development|staging|production
APP_VERSION=0.0.1
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://agro:<pwd>@postgres:5432/agro
DATABASE_URL_SYNC=postgresql://agro:<pwd>@postgres:5432/agro
POSTGRES_PASSWORD=<secret>

# Auth
AUTH_JWT_SECRET=<32-byte random>
AUTH_JWT_ACCESS_TTL_SECONDS=900
AUTH_JWT_REFRESH_TTL_SECONDS=2592000
OTP_TRANSPORT=whatsapp

# MQTT
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=8883
MQTT_BROKER_USER=service
MQTT_BROKER_PASSWORD=<secret>
MQTT_TLS_CA_PATH=/etc/ssl/certs/ca.crt

# Anthropic
ANTHROPIC_API_KEY=<key>
ANTHROPIC_MODEL_SONNET=claude-sonnet-4-6
ANTHROPIC_MODEL_HAIKU=claude-haiku-4-5-20251001
USD_INR_RATE=83.0

# WhatsApp Meta Cloud API (advisory + OTP)
META_WHATSAPP_PHONE_NUMBER_ID=<id>
META_WHATSAPP_BUSINESS_ACCOUNT_ID=<id>
META_WHATSAPP_TOKEN=<long-lived token>
META_WHATSAPP_VERIFY_TOKEN=<webhook verify>
META_WHATSAPP_OTP_TEMPLATE_NAME=agroguardian_otp_v1
META_WHATSAPP_ADVISORY_TEMPLATE_NAME=agroguardian_advisory_v1

# FCM
FCM_SERVICE_ACCOUNT_JSON=/secrets/fcm-sa.json

# Satellite
COPERNICUS_CLIENT_ID=<>
COPERNICUS_CLIENT_SECRET=<>
NASA_EARTHDATA_USERNAME=<>
NASA_EARTHDATA_PASSWORD=<>

# Storage
R2_ACCOUNT_ID=<>
R2_ACCESS_KEY_ID=<>
R2_SECRET_ACCESS_KEY=<>
R2_BUCKET_RASTERS=agro-rasters
R2_BUCKET_PHOTOS=agro-photos
R2_BUCKET_FIRMWARE=agro-firmware

B2_KEY_ID=<>
B2_APPLICATION_KEY=<>
B2_BUCKET_BACKUPS=agro-backups

# Monitoring
SENTRY_DSN=<>
BETTER_STACK_TOKEN=<>

# CORS
CORS_ALLOWED_ORIGINS=https://app.agroguardian.in,https://dashboard.agroguardian.in,https://agroguardian.in

# OTA (Phase 8)
OTA_SIGNING_PRIVATE_KEY_PEM=<base64 ed25519 PEM>
OTA_SIGNING_PUBLIC_KEY_PEM=<base64>

# Deferred — Phase 13/14 only
# MSG91_AUTH_KEY=
# MSG91_SENDER_ID=
# RAZORPAY_KEY_ID=
# RAZORPAY_KEY_SECRET=
# RAZORPAY_WEBHOOK_SECRET=
```

**Testing:** `tests/test_health.py` confirms 200 + JSON contract; `tests/test_config.py` confirms required env vars present.

**Deployment steps:**

1. Provision AWS Lightsail Mumbai $20/month instance with a static IP (per Part 12.2 runbook).
2. SSH in; install Docker + Docker Compose Plugin; install Coolify via official one-liner.
3. Point `api.agroguardian.in` at the VPS via Cloudflare DNS (A record, proxy OFF for Let's Encrypt to issue).
4. Connect GitHub repo to Coolify; configure auto-deploy on `main` push.
5. Coolify pulls + builds + runs prod compose; Caddy auto-issues Let's Encrypt SSL.
6. `curl https://api.agroguardian.in/api/v1/health` → 200.

**Common mistakes:**
- Real secrets in `.env.example` — only key names allowed
- Forgetting `--proxy-headers` on uvicorn — breaks IP detection behind Caddy
- Skipping Alembic and adding it later — retrofit is painful
- Building a non-multi-arch image — won't run on ARM Ampere

**Expected output:** healthy URL, green CI, Coolify dashboard showing the running stack.

### Cursor prompts for Phase 0

#### Prompt 0.1 — Repo scaffold

```
Cursor task: bootstrap the AgroGuardian V2 backend.

Read Part 5 of the FINAL roadmap (folder layout). Create the full directory tree
with empty __init__.py files and these populated files:

1) pyproject.toml — Python 3.12. Dependencies (production):
   fastapi, uvicorn[standard], pydantic>=2.5, pydantic-settings,
   sqlalchemy[asyncio]>=2.0, asyncpg, alembic, structlog, httpx,
   paho-mqtt, anthropic, sentence-transformers, chromadb, apscheduler,
   prometheus-client, passlib[argon2], python-jose[cryptography],
   firebase-admin, sentry-sdk[fastapi], slowapi, sentinelhub, earthaccess,
   shapely, geoalchemy2, rasterio, xarray.
   Dev: pytest, pytest-asyncio, testcontainers[postgres], ruff, mypy,
   respx, hypothesis.
   Use [tool.pytest.ini_options] asyncio_mode="auto".
   Use [tool.ruff] line-length=100, target-version="py312".
   Use [tool.mypy] check_untyped_defs=true, disallow_untyped_defs=true.

   IMPORTANT: razorpay SDK is NOT a pilot dependency. Add it only in Phase 14.

2) Dockerfile — multi-stage, ARM64 + amd64 compatible:
   Stage 1: python:3.12-slim-bookworm, apt install build deps, pip install
     --no-cache-dir --target=/install.
   Stage 2: python:3.12-slim-bookworm, copy /install to site-packages,
     copy app/, copy rules/, expose 8000, CMD ["uvicorn","app.main:app",
     "--host","0.0.0.0","--port","8000","--proxy-headers",
     "--forwarded-allow-ips=*"].

3) docker-compose.dev.yml — services:
   - postgres (postgis/postgis:15-3.4 — verify multi-arch tag), healthcheck
     pg_isready, volume pgdata, env POSTGRES_USER=agro, POSTGRES_DB=agro,
     POSTGRES_PASSWORD from .env
   - mosquitto (eclipse-mosquitto:2.0.18, volume mosquitto-data + config)
   - chroma (chromadb/chroma:latest, volume /data/chroma)
   - app (build context ., depends on postgres+mosquitto+chroma,
     env_file .env, volume ./app for hot-reload)

4) docker-compose.prod.yml — same minus source mount; plus caddy
   (caddy:2-alpine + Caddyfile), prometheus (Tailscale-only via Caddy ACL),
   grafana (Tailscale-only).
   Networks: internal (postgres, chroma, app, mosquitto, prometheus,
   grafana), edge (caddy, app).

5) .env.example — every variable from Part 6 Phase 0 of the roadmap;
   one-line comment per key; NO real secrets.

6) .gitignore — Python, venv, .env*, __pycache__, *.db, /data/,
   /node_modules/, .DS_Store, .ruff_cache, .mypy_cache, /coverage/.

7) .cursorrules — paste verbatim from Part 10.2 of the roadmap.

8) .github/workflows/ci.yml — three jobs:
   - lint: ruff check . && ruff format --check . && mypy app/
   - test: postgres:15 service container; export DATABASE_URL +
     DATABASE_URL_SYNC + AUTH_JWT_SECRET=test; run alembic upgrade head;
     pytest -q --cov=app --cov-fail-under=80.
   - build: docker buildx build --platform linux/amd64,linux/arm64 .
     (no push; verifies multi-arch build).

9) app/__init__.py and app/main.py — FastAPI app, lifespan handler
   (startup: scheduler.start, broker.start; shutdown: reverse), CORS
   reading CORS_ALLOWED_ORIGINS, structlog setup, Sentry init guarded
   by APP_ENV != 'development', GET /api/v1/health.

10) app/config.py — pydantic-settings BaseSettings reading from .env;
    every variable typed correctly; secrets via SecretStr.

11) alembic.ini, alembic/env.py — sync Alembic for migrations
    (DATABASE_URL_SYNC), async runtime engine.

12) deploy/caddy/Caddyfile — uses sslip.io for the prototype phase
    (domain name not finalized yet). Replace `IP-WITH-DASHES` literally
    with the AWS Lightsail static IP using dashes (e.g., 13.235.50.100
    -> 13-235-50-100). When the brand domain is bought, change these
    four hostnames in one go and `docker compose restart caddy`.

    {
      email ops@example.com   # placeholder; replace when brand email exists
    }
    api-IP-WITH-DASHES.sslip.io {
      reverse_proxy app:8000
    }
    mqtt-IP-WITH-DASHES.sslip.io:8883 {
      reverse_proxy mosquitto:8883
    }
    dashboard-IP-WITH-DASHES.sslip.io {
      reverse_proxy streamlit:8501
    }
    metrics-IP-WITH-DASHES.sslip.io {
      @tailscale remote_ip 100.64.0.0/10
      handle @tailscale {
        reverse_proxy grafana:3000
      }
      respond 403
    }

    Why sslip.io and not nip.io: identical mechanism, sslip.io's TLS
    record is more reliable with Let's Encrypt rate limits and supports
    both dash-form and dot-form. Either works; we pick sslip.io for
    consistency.

    The IP-WITH-DASHES substitution is automated by a small make target
    `make caddyfile-prod` documented in deploy/coolify/README.md so you
    don't typo it.

13) deploy/mosquitto/mosquitto.conf — listener 8883 TLS,
    allow_anonymous false, password_file, acl_file (per-device generated
    in Phase 1).

14) tests/conftest.py — postgres testcontainer fixture (session-scoped),
    httpx AsyncClient fixture, monkeypatched Settings.

15) tests/test_health.py — verifies GET /api/v1/health.

After writing: docker compose -f docker-compose.dev.yml up -d postgres
mosquitto chroma; pip install -e .; pytest -q. Show output, then explain
in 10 lines what each file does.

Coding standards:
- Production-quality, no TODOs.
- Type-annotate everything that crosses a function boundary.
- Async wherever I/O is involved.
- Maintain consistency with the hexagonal architecture in Part 1.
```

#### Prompt 0.2 — Coolify deploy + Cloudflare wiring

```
Cursor task: produce deploy/coolify/README.md documenting:

1) SSH into VPS, install Docker + Docker Compose Plugin.
2) Install Coolify via official one-liner.
3) Connect GitHub PAT (read access to private repo).
4) Create Docker Compose resource pointing at docker-compose.prod.yml.
5) Set environment variables in Coolify's secret store, one per
   .env.example key.
6) Configure auto-deploy on push to main.
7) Set up Caddy reverse proxy for api.agroguardian.in; confirm
   Let's Encrypt SSL issued.
8) Verify: curl https://api.agroguardian.in/api/v1/health.

Troubleshooting section for:
- Coolify failing to pull image (registry auth)
- Postgres failing on ARM (volume perms, image tag)
- Caddy ACME rate limits (use staging endpoint first)
- Tailscale not connecting (tailscale up --advertise-tags=tag:vps)

Coding standards: clear step-by-step, commands verbatim with expected
output. No vague "configure as needed".
```

---

## PHASE 1 — Database schema, migrations, RLS, audit log (3–5 days)

**Goal:** all 21 source tables + 14 v3 additional tables live, partitioned, RLS-enforced, audit-logged. Alembic up + down clean.

**Files:** migration SQL files in `alembic/versions/`, SQLAlchemy ORM models in `app/infra/persistence/models/`.

**Tables:** 35 total (21 + 14). Materialized views: 4. Trigger functions: `audit_trigger_fn`, `plots_set_data_tier`.

**Tests:**
- `test_migrations.py` — `alembic upgrade head` + `downgrade base` + `upgrade head` round-trip clean
- `test_rls.py` — fake JWT claims via SET LOCAL; verify cross-tenant returns 0 rows
- `test_partitioning.py` — insert a row 6 months ahead; verify correct child partition
- `test_audit_log.py` — UPDATE a `farmers` row; verify audit_log row

**Common mistakes:**
- Forgetting `service_role BYPASSRLS` — ingest worker stalls
- Skipping `CREATE UNIQUE INDEX` on materialized views — `REFRESH CONCURRENTLY` fails
- Using `auth.jwt()` (Supabase-only) — won't work on self-hosted
- Missing `tenant_id` on a tenant-scoped table — RLS no-op
- Multi-arch Postgres image mismatch on ARM — verify the tag before pinning

### Cursor prompts for Phase 1

#### Prompt 1.1 — Initial 21-table migration

```
Cursor task: alembic/versions/0001_init_21_tables.sql.

Create every table from §2.2.1 of the AgroGuardian technical reference
(I will paste the schema doc summary at the top of this chat) — all 21.
Use raw SQL, not op.create_table.

Rules:
- Every tenant-scoped table has tenant_id UUID NOT NULL FK to tenants
  (CREATE tenants first).
- PKs are UUID v4 except where the schema doc uses a string ID
  (device_id, plot_id as TEXT).
- Money is NUMERIC(12,2). Never REAL/DOUBLE PRECISION.
- Timestamps are TIMESTAMPTZ.
- ENUM-style columns use TEXT + CHECK constraint.
- Add COMMENT ON TABLE and COMMENT ON COLUMN for any non-obvious column.
- Foreign keys with ON DELETE explicit (CASCADE on natural child rows,
  RESTRICT otherwise).
- NO indexes here — those land in 0005/0006.

After writing: alembic upgrade head. Show \dt; verify 22 tables (21 +
tenants). If a column type is ambiguous, pick the most defensible
default (TEXT > VARCHAR, JSONB > TEXT, UUID > TEXT for IDs) and note
it in a -- comment.

Coding standards: production-grade, no TODOs, every opinionated choice
commented inline.
```

#### Prompt 1.2 — V3 additional tables

```
Cursor task: alembic/versions/0002_v3_additional_tables.sql.

Create the 14 v3 tables from Part 2.2:
- users (Argon2id password_hash TEXT — holds the full PHC string)
- otp_codes (id, phone_e164, code_hash, transport TEXT CHECK
  (transport IN ('whatsapp','sms')), wa_message_id TEXT NULL,
  attempts INT DEFAULT 0, expires_at TIMESTAMPTZ, verified_at TIMESTAMPTZ
  NULL, created_at TIMESTAMPTZ DEFAULT now())
- refresh_tokens (token_hash BYTEA, user_or_farmer_id UUID, role TEXT,
  expires_at, revoked_at NULL)
- audit_log (actor_type, actor_id, table_name, row_pk JSONB, operation,
  old_data JSONB, new_data JSONB, at TIMESTAMPTZ DEFAULT now())
- notification_dispatch_log (alert_id, channel, provider_message_id,
  status, error_code, error_message, dispatched_at)
  UNIQUE (alert_id, channel)
- notification_dlq (alert_id, channels TEXT[], last_error, retry_count,
  moved_to_dlq_at)
- ingest_unmatched (topic, payload JSONB, reason, first_seen, last_seen)
- event_outbox (id, event_name, payload JSONB, published BOOLEAN,
  published_at)
- feature_flags (tenant_id, flag_name, enabled BOOLEAN, payload JSONB)
- system_config (key, value JSONB, updated_at)
- chat_messages (id, farmer_id, role TEXT CHECK (role IN
  ('user','assistant','system')), content TEXT, tokens_used INT,
  llm_cost_inr NUMERIC(10,4), context JSONB, created_at)
- calibration_history (device_id, sensor TEXT, slope NUMERIC, intercept
  NUMERIC, lab_id TEXT, calibrated_at, recorded_at)
- wa_inbound_log (id, tenant_id, farmer_id NULL, wa_message_id TEXT
  UNIQUE, phone_e164, body TEXT, received_at, processed BOOLEAN DEFAULT
  FALSE)

Special on tenants:
ALTER TABLE tenants ADD COLUMN tier TEXT NOT NULL DEFAULT 'basic'
  CHECK (tier IN ('pilot_internal','basic','standard','pro'));
ALTER TABLE tenants ADD COLUMN features JSONB NOT NULL DEFAULT '{}';

Insert the pilot tenant row:
INSERT INTO tenants (id, name, tier, features)
VALUES ('11111111-1111-1111-1111-111111111111',
        'AgroGuardian Pilot — Aurangabad',
        'pilot_internal',
        '{"all_features_unlocked": true}'::jsonb);

Coding standards: every CREATE TABLE has COMMENT ON TABLE.
```

#### Prompt 1.3 — Extensions, patches, partitioning, aggregates

```
Cursor task: write 0003_extensions.sql, 0004_plots_satellite_only.sql,
0005_partition_timeseries.sql, 0006_aggregates.sql.

0003: CREATE EXTENSION IF NOT EXISTS "uuid-ossp", postgis, vector,
pgcrypto.

0004: ALTER plots.node_id nullable; ADD plots.data_tier with CHECK;
CREATE FUNCTION + TRIGGER plots_set_data_tier (verbatim from §2.2.2
patch 2 of the AgroGuardian doc).

0005: For node_sensor_readings, weather_station_readings,
weather_forecasts:
- Rename to _old.
- CREATE PARTITION BY RANGE (recorded_at) with full column set including
  v3 additions from Part 2.4.
- CREATE UNIQUE INDEX <table>_idem ON ... (node_id_or_master, recorded_at).
- CREATE INDEX <table>_plot_time, <table>_farm_time, <table>_tenant_time.
- DO $$ FOR i IN 0..12 LOOP create monthly child partitions $$.
- INSERT INTO <table> SELECT * FROM <table>_old (no-op if empty).
- DROP TABLE <table>_old.

0006: CREATE MATERIALIZED VIEW node_readings_hourly, node_readings_daily,
weather_hourly, weather_daily — full column sets per §2.5.2.
Each gets UNIQUE INDEX so REFRESH CONCURRENTLY works.

After writing: alembic upgrade head; verify
SELECT count(*) FROM pg_inherits WHERE inhparent =
'node_sensor_readings'::regclass → expect 13.
```

#### Prompt 1.4 — Audit log triggers

```
Cursor task: 0007_audit_log.sql.

CREATE OR REPLACE FUNCTION audit_trigger_fn() RETURNS TRIGGER:
- Reads current_setting('app.current_user_role', true) and
  current_setting('app.current_user_id', true).
- Captures TG_OP, TG_TABLE_NAME, OLD as JSONB, NEW as JSONB.
- INSERTs into audit_log.

CREATE TRIGGER on every master table (farmers, farms, plots,
crop_seasons, device_registry, subscriptions_billing, users, tenants,
calibration_history) FOR EACH ROW EXECUTE FUNCTION audit_trigger_fn().

Tests in tests/test_audit_log.py: UPDATE a farmer; verify a row in
audit_log with the right old/new diff.
```

#### Prompt 1.5 — RLS policies

```
Cursor task: 0008_rls_policies.sql.

For every tenant-scoped table from Part 2.6:
1) ALTER TABLE ... ENABLE ROW LEVEL SECURITY.
2) CREATE POLICY <table>_tenant_iso USING (tenant_id =
   current_setting('app.current_tenant_id', true)::uuid).
3) CREATE POLICY <table>_read FOR SELECT USING (
     current_setting('app.current_user_role', true) IN
       ('admin','agronomist','service','technician')
     OR farmer_id = current_setting('app.current_farmer_id', true)::uuid
   ).
4) CREATE POLICY <table>_write FOR INSERT,UPDATE,DELETE
   USING (current_setting('app.current_user_role', true) IN
            ('admin','technician'))
   WITH CHECK (current_setting('app.current_user_role', true) IN
            ('admin','technician')).

Special: ai_suggestions also gets ai_suggestions_review FOR UPDATE
policy for agronomist role, with a BEFORE UPDATE trigger that rejects
changes outside review_* columns.

CREATE ROLE authenticated_role NOLOGIN;
CREATE ROLE service_role NOLOGIN BYPASSRLS;

Tests in tests/test_rls.py: with a connection that does
  SET LOCAL app.current_tenant_id = '<tenant1>';
  SET LOCAL app.current_user_role = 'farmer';
  SET LOCAL app.current_farmer_id = '<farmer1>';
assert SELECT FROM plots returns only farmer1's plots; with a different
tenant_id assert 0 rows.
```

#### Prompt 1.6 — SQLAlchemy 2.0 ORM models

```
Cursor task: app/infra/persistence/models/ — one file per group.

Use SQLAlchemy 2.0 `mapped_column` and `Mapped[]` typing. Define Base in
app/infra/persistence/base.py.

Files:
- core.py: tenants, users, otp_codes, refresh_tokens, audit_log
- farms.py: farmers, farms, plots, crop_seasons
- devices.py: device_registry, component_inventory,
  technician_installations, service_maintenance, calibration_history
- readings.py: node_sensor_readings (with partition_by table arg),
  weather_station_readings, weather_forecasts, satellite_data
- events.py: irrigation_events, electricity_schedule_log,
  water_source_status, farmer_actions
- ai.py: ai_suggestions, ai_learning_log, chat_messages
- alerts.py: alerts_notifications, notification_dispatch_log,
  notification_dlq
- billing.py: subscriptions_billing, product_performance_bi
- system.py: feature_flags, system_config, ingest_unmatched,
  event_outbox, wa_inbound_log

Type rules:
- TIMESTAMPTZ -> Mapped[datetime] with DateTime(timezone=True)
- NUMERIC(12,2) -> Mapped[Decimal] with Numeric(12,2)
- JSONB -> Mapped[dict] with JSONB
- Geometry -> Mapped[Any] with geoalchemy2.Geometry('POLYGON', srid=4326)
- TEXT CHECK enum -> Mapped[str] with String + CheckConstraint

For partitioned tables:
  __table_args__ = (
    UniqueConstraint('node_id', 'recorded_at',
                     name='node_sensor_readings_idem'),
    {'postgresql_partition_by': 'RANGE (recorded_at)'}
  )

Smoke test tests/test_models.py: import every module, assert
Base.metadata.tables has >= 35 entries.

Coding standards: every column has a type annotation. No Any. Use
`T | None` consistently for nullable.
```

---

## PHASE 2 — MQTT ingest + validation + hexagonal repos (5–7 days)

**Goal:** sensor data flows from a fake Main Node publisher through validation gates into Postgres, idempotently, with Prometheus metrics. Repositories implement application ports.

**Files:**
- `app/domain/sensor.py`, `app/domain/plot.py` (pure dataclasses)
- `app/application/ports/{reading_repo,plot_repo,alert_repo,suggestion_repo,rule_repo,event_bus}.py`
- `app/application/ingest_telemetry.py`
- `app/infra/mqtt/{broker,schemas,validation}.py`
- `app/infra/persistence/{pg_reading_repo,pg_plot_repo,pg_alert_repo,pg_suggestion_repo}.py`
- `app/infra/events/pg_notify_bus.py`
- `app/lib/metrics.py`
- `scripts/dev/fake_main_node.py`
- `tests/fixtures/telemetry/*.json`

**APIs:** `GET /metrics` (Prometheus), `GET /api/v1/admin/ingest/stats`.

**Tests:**
- Unit: each validation gate with edge cases
- Integration: postgres + mosquitto testcontainers; publish 30 synthetic JSONs; assert 30 rows
- Idempotency: publish same `(node_id, recorded_at)` twice; assert one row
- Backlog replay: 200 messages timestamped 6 days ago; all land
- Repository contract: each repo implements its Protocol port

**Common mistakes:**
- Missing `ON CONFLICT ... DO NOTHING` — duplicates explode the unique index
- In-memory stuck-check state — restarts lose context (use SQL)
- Unbounded queue — set `maxsize=5000` and emit backpressure metric
- Subscribing without `qos=1` — risks message loss

### Cursor prompts for Phase 2

#### Prompt 2.1 — Pure domain layer

```
Cursor task: create app/domain/sensor.py and app/domain/plot.py.

Pure Python. ZERO framework imports (no sqlalchemy, no fastapi, no
pydantic). Use dataclasses + StrEnum from stdlib + Decimal.

sensor.py:
- class CadenceMode(StrEnum): NORMAL, ALERT, CONSERVATION, STORM
- @dataclass(frozen=True) Reading with fields:
  tenant_id (UUID-as-str), node_id, plot_id, farm_id,
  recorded_at (datetime aware), received_at_master (datetime aware),
  battery_voltage_v (Decimal),
  soil_moisture_1_pct (Decimal | None),
  soil_moisture_2_pct, soil_moisture_avg_pct,
  soil_temp_c, soil_temp_rootzone_c, soil_ph, soil_ec_ms_cm,
  soil_n_mg_kg, soil_p_mg_kg, soil_k_mg_kg,
  soil_n_bucket (int | None), soil_p_bucket, soil_k_bucket,
  signal_rssi_dbm (int),
  cadence_mode (CadenceMode), validation_warn (bool),
  low_battery_flag, backlog_pending,
  firmware_version (str),
  sensor_health (dict[str, str]).

plot.py:
- class DataTier(StrEnum): SUB_NODE, SATELLITE_ONLY
- @dataclass(frozen=True) Plot:
  plot_id (str), farm_id (UUID), tenant_id (UUID), plot_name (str),
  area_acre (Decimal), data_tier (DataTier), node_id (str | None),
  gps_boundary_geojson (dict | None).

Add tests/domain/test_sensor.py importing from app.domain.sensor.
Construct a Reading; assert frozen behavior.
NO other imports except stdlib + the domain module — this proves the
hexagon is intact.

Coding standards: every field has a type annotation. No __post_init__
business logic — domain dataclasses are dumb data carriers.
```

#### Prompt 2.2 — Application ports

```
Cursor task: app/application/ports/ — Protocol classes.

reading_repo.py:
class ReadingRepo(Protocol):
    async def save(self, reading: Reading) -> str | None: ...
    async def latest_for_plot(self, plot_id: str, limit: int) -> list[Reading]: ...
    async def recent_for_node(self, node_id: str, since: datetime) -> list[Reading]: ...
    async def history_for_stuck_check(self, node_id: str, field: str,
                                       minutes: int) -> list[Decimal | None]: ...
    async def history_for_mad_check(self, node_id: str, field: str,
                                     hours: int) -> list[Decimal]: ...

plot_repo.py:
class PlotRepo(Protocol):
    async def find(self, plot_id: str) -> Plot | None: ...
    async def for_farmer(self, farmer_id: str) -> list[Plot]: ...
    async def for_tenant(self, tenant_id: str) -> list[Plot]: ...
    async def update_data_tier(self, plot_id: str, tier: DataTier) -> None: ...

alert_repo.py, suggestion_repo.py, rule_repo.py, event_bus.py — same
pattern.

Use typing.Protocol with @runtime_checkable. NO implementations here —
these are pure contracts.

tests/application/test_ports_are_protocols.py: verify each port is a
runtime_checkable Protocol.
```

#### Prompt 2.3 — Pydantic MQTT schemas

```
Cursor task: app/infra/mqtt/schemas.py.

Implement TelemetryIn, WeatherIn, HeartbeatIn, AlertIn, HealthIn —
pydantic v2 BaseModels matching §1.9 of the AgroGuardian technical
reference (I will paste §1.9 at the top of this chat).

Rules:
- Field(alias="$schema") for discriminator.
- Literal types for enumerated fields.
- Every numeric Field has ge/le bounds matching §2.4.2 RANGES.
- Timezone-aware datetime with field_validator rejecting recorded_at
  outside [now() - 7 days, now() + 1 hour].
- Optional[T] = None for satellite-only NULL fields.

Add parse_inbound(topic: str, raw: bytes) -> Union[...] | None.
Returns None if parse fails; logs + increments
metrics.ingest_parse_error.

Add to_domain() method on each: TelemetryIn.to_domain() -> Reading.
The boundary between infra pydantic and pure domain dataclass.

Tests: tests/infra/test_mqtt_schemas.py with fixtures
tests/fixtures/telemetry/*.json; assert parse + to_domain works.

Coding standards: production-quality, reject ambiguous input early.
```

#### Prompt 2.4 — Validation gates

```
Cursor task: app/infra/mqtt/validation.py.

Four gates per §2.4 of AgroGuardian:

1) validate_range(field: str, value: Decimal | None) ->
   tuple[Decimal | None, str | None] — pure function using RANGES dict
   matching §2.4.2.

2) async def is_stuck(repo: ReadingRepo, node_id: str, latest: Decimal,
                       field: str) -> bool — uses
   repo.history_for_stuck_check. 4 of 6 in 90 min same value -> stuck.

3) async def is_outlier_mad(repo, node_id, value, field, k=3.5) -> bool.

4) cross_sensor_consistency(reading: Reading) -> dict[str, str] —
   pure; returns sensor_health flags.

Compose into:
async def validate_reading(repo: ReadingRepo, reading: Reading)
    -> Reading:
    """Returns a new Reading (dataclasses.replace) with sanitized fields
    and validation_warn=True if any flag fired, sensor_health populated."""

Tests in tests/infra/test_validation.py per gate (use a fake
ReadingRepo for unit tests; integration in tests/infra/test_ingest_e2e.py
uses real Postgres testcontainer).

Coding standards: every gate < 30 lines, single responsibility. Never
silently swallow exceptions.
```

#### Prompt 2.5 — Postgres repositories

```
Cursor task: app/infra/persistence/pg_reading_repo.py.

class PgReadingRepo implements application.ports.reading_repo.ReadingRepo.

Constructor takes AsyncSessionMaker.

save(reading): use text() with INSERT ... ON CONFLICT (node_id,
recorded_at) DO NOTHING RETURNING reading_id pattern. Returns reading_id
or None. On None, increment metrics.ingest_duplicate.

history_for_stuck_check uses parameterized SQL with field name
validated against a hardcoded allowlist (NO SQL injection on column).

history_for_mad_check uses array_agg.

Add tests/infra/test_pg_reading_repo.py with postgres testcontainer:
- save returns id first call, None on duplicate
- history_for_stuck_check returns last 6 rows
- history_for_mad_check returns 24-h array

Also implement pg_plot_repo.py, pg_alert_repo.py, pg_suggestion_repo.py
following the same pattern.

Coding standards: every method async, type-annotated, has docstring with
the SQL it issues. NO raw f-string SQL — always parameterized.
```

#### Prompt 2.6 — Application use case + MQTT broker

```
Cursor task: app/application/ingest_telemetry.py and
app/infra/mqtt/broker.py.

ingest_telemetry.py:
@dataclass(frozen=True) IngestDeps:
    reading_repo: ReadingRepo
    plot_repo: PlotRepo
    alert_repo: AlertRepo
    event_bus: EventBus
    metrics: MetricsRegistry

async def execute(reading: Reading, deps: IngestDeps) -> IngestResult:
    validated = await validate_reading(deps.reading_repo, reading)
    reading_id = await deps.reading_repo.save(validated)
    if reading_id:
        await deps.event_bus.publish("telemetry.ingested",
            {"plot_id": validated.plot_id, "reading_id": reading_id})
        await evaluate_hot_rules(deps, validated)  # stub until Phase 4
    return IngestResult(reading_id=reading_id, dropped=reading_id is None)

broker.py:
class IngestBroker:
    def __init__(self, settings: Settings, deps_factory: Callable): ...
    async def start(self):
        # paho-mqtt thread-based loop bridged to asyncio.Queue (maxsize 5000)
    async def drain(self):
        # forever: queue.get -> parse_inbound -> to_domain ->
        # ingest_telemetry.execute -- per message
    async def stop(self): ...

In app/main.py lifespan: start broker on startup, stop on shutdown.

Tests tests/infra/test_ingest_e2e.py: postgres + mosquitto testcontainers,
publish 10 synthetic telemetry JSONs via paho publisher, assert 10 rows
in node_sensor_readings.

Coding standards: never silently swallow exceptions; every drop reason
goes to structlog with topic + reason + node_id (no full payload).
Backpressure (queue.qsize > 4000) emits a WARN.
```

#### Prompt 2.7 — Fake Main Node publisher

```
Cursor task: scripts/dev/fake_main_node.py.

CLI tool (argparse) publishing synthetic telemetry to local mosquitto.

Args:
--rate (cycles/min, default 4)
--duration (seconds, default 300)
--tenant, --farm-id, --master-node-id
--sub-nodes (comma list, default "NODE_AGN_001,NODE_AGN_002")
--simulate-outage (start_sec, duration_sec — buffer messages, replay
 after, simulating SD-card backlog)
--break-sensors (comma list: stuck|range|outlier)

Generate plausible drifting values:
- soil_moisture: 30±5% with slow sinusoidal drift + noise
- soil_temp: 25-32°C
- battery_voltage: starts 7.2, drifts -0.001 V per cycle
- N/P/K: 800-1200 / 400-700 / 900-1300 mg/kg

Publish to agro/<tenant>/<farm_id>/<master_node_id>/telemetry as JSON
matching §1.9 schema.

After writing, run for 5 min against local stack; verify rows.

Robust to broker disconnects (reconnect + continue). < 200 lines total.
```

---

## PHASE 3 — REST API + WhatsApp-OTP auth (4–6 days)

**Goal:** read-side API + auth where OTP is delivered via WhatsApp Cloud API. JWT issued by FastAPI, refresh-token rotation enforced, RLS verified end-to-end.

**Files:**
- `app/lib/jwt.py`, `app/lib/otp.py`
- `app/application/ports/otp_delivery_client.py`
- `app/application/{send_otp,verify_otp}.py`
- `app/infra/notify/whatsapp_otp.py` (later extended to also handle advisory in Phase 7)
- `app/infra/http/{auth,me,farms,plots,readings,alerts,farmer_actions,boundary}.py`
- `app/deps.py` (full version)
- Generated TS types → `agro_app/src/api/types.gen.ts`

**APIs:** all read endpoints from Part 3.1 + auth endpoints.

**Tests:**
- Per endpoint: 200, 401, 403, 404, 422
- RLS: farmer A's JWT cannot read farmer B's plots even via direct ID lookup
- OTP: rate-limited (3/10min/phone request, 5/10min verify), 5-min expiry, single-use, locked after 5 wrong attempts
- Pagination: cursor works
- TS types generation: `npm run gen-types` produces a non-empty diff-free file

### Cursor prompts for Phase 3

#### Prompt 3.1 — JWT + OTP libraries + application use cases

```
Cursor task: create app/lib/jwt.py, app/lib/otp.py,
app/application/ports/otp_delivery_client.py, and
app/application/{send_otp,verify_otp}.py.

jwt.py:
- create_access_token(claims: dict) -> str — HS256, 15-min exp.
- create_refresh_token() -> tuple[plain: str, hash: bytes]. Random
  32-byte; hash via blake2b.
- decode_access_token(token: str) -> dict. Raises InvalidTokenError.

otp.py:
- generate_code() -> str. secrets.choice over digits, 6 chars.
- hash_code(code: str) -> str. bcrypt cost 10.
- verify_code(code: str, hashed: str) -> bool. Constant-time.

ports/otp_delivery_client.py:
class OtpDeliveryClient(Protocol):
    async def send_otp(self, phone_e164: str, code: str) -> str:
        """Returns provider message_id. Raises on permanent failure."""

application/send_otp.py:
async def execute(phone_e164: str, deps: SendOtpDeps) -> None:
    """Pilot: WhatsAppOtpAdapter. Phase 13: switchable to SmsClient via
    OTP_TRANSPORT env var."""
    # Rate-limit: 3 / phone / 10 min.
    # Pick adapter from deps.otp_transport.
    # Generate code; hash; INSERT otp_codes(phone, code_hash, transport,
    #   expires_at=now()+5min).
    # await deps.otp_transport.send_otp(phone, code)
    # Store wa_message_id from response on otp_codes row.

application/verify_otp.py:
async def execute(phone_e164, code, deps) -> tuple[access, refresh]:
    # SELECT latest unverified, unexpired otp_code for phone.
    # If none, raise OtpInvalid.
    # If wrong, increment attempts; if >= 5, lock 30 min (OtpLocked).
    # Mark verified_at.
    # find_or_create farmer by phone_hash.
    # Issue access + refresh; store refresh hash in refresh_tokens.

Tests tests/application/test_otp.py: happy path, rate limit, expired,
wrong code, replay attack, max attempts.

Coding standards: NEVER log OTP code. Constant-time comparisons only.
```

#### Prompt 3.2 — WhatsApp OTP adapter

```
Cursor task: app/infra/notify/whatsapp_otp.py.

class WhatsAppOtpAdapter implements OtpDeliveryClient (and later
WhatsAppClient in Phase 7 — for now, just OTP).

Uses httpx (no SDK) to call Meta Cloud API:

POST https://graph.facebook.com/v20.0/{phone_number_id}/messages
Headers: Authorization: Bearer <META_WHATSAPP_TOKEN>
Body:
{
  "messaging_product": "whatsapp",
  "to": phone_e164_no_plus,
  "type": "template",
  "template": {
    "name": settings.META_WHATSAPP_OTP_TEMPLATE_NAME,
    "language": {"code": "mr"},
    "components": [
      {"type": "body",
       "parameters": [{"type": "text", "text": code}]},
      {"type": "button", "sub_type": "url", "index": "0",
       "parameters": [{"type": "text", "text": code}]}
    ]
  }
}

Note: The 'authentication' template category requires the URL button
copy parameter — see Meta docs:
https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates#authentication-templates

Return: messages[0].id from response.

Error handling:
- 400 / template not approved -> raise PermanentDispatchError
- 400 / invalid recipient -> raise InvalidRecipientError
- 5xx / timeout -> retry once with backoff; then TransientError
- 429 -> RateLimitedError

Tests with respx:
- Successful send returns message_id.
- 400 template_not_approved raises Permanent.
- 5xx retried once then raises Transient.

Coding standards: NEVER log OTP code in any error path. Last-4 of phone
only in logs.
```

#### Prompt 3.3 — FastAPI auth routes + deps

```
Cursor task: create app/infra/http/auth.py and update app/deps.py.

deps.py:
- async def get_session() yields AsyncSession; on entry executes
    SET LOCAL app.current_tenant_id = ...
    SET LOCAL app.current_user_role = ...
    SET LOCAL app.current_user_id = ...
    SET LOCAL app.current_farmer_id = ...
  from a context-local populated by current-user middleware.
- async def get_current_user(token: str = Depends(oauth2_scheme))
    -> CurrentUser dataclass.
- def require_role(*roles): factory returning Depends.
- Rate-limit dependency via slowapi.

auth.py routes:
- POST /api/v1/auth/otp/request — body OtpRequestBody{phone_e164}
  (pydantic E.164 validator). Calls send_otp.execute. Returns 204.
- POST /api/v1/auth/otp/verify — body OtpVerifyBody{phone_e164, code}.
  Returns {access_token, refresh_token, expires_in, token_type,
  farmer:{id, name, language}}.
- POST /api/v1/auth/refresh — body {refresh_token}; verifies hash;
  revokes used token (single-use rotation); issues new pair.
- POST /api/v1/auth/logout — revokes refresh.
- POST /api/v1/auth/login — admin/agronomist/technician email + password;
  Argon2id verify; same token response.

Rate limits via slowapi:
- /auth/otp/request: 3 / 10 min / phone
- /auth/otp/verify: 5 / 10 min / phone
- /auth/refresh: 10 / hour / refresh_token
- /auth/login: 10 / hour / IP

Tests tests/infra/http/test_auth.py with httpx AsyncClient:
- 204 on valid OTP request (mock WhatsAppOtpAdapter)
- 429 on 4th request within 10 min
- 200 on verify with valid code; tokens returned
- 401 on verify with wrong code
- 401 on protected route without auth
- 200 on protected route with valid JWT
- 401 on refresh with revoked token (single-use enforced)

Coding standards: every route has response_model. Phone in logs is
last-4 only.
```

#### Prompt 3.4 — Read endpoints

```
Cursor task: implement read endpoints from Part 3.1.

Files:
- app/infra/http/me.py — GET/PATCH /me, /me/farms, /me/fcm_token
- app/infra/http/farms.py — GET /farms/{id}/plots
- app/infra/http/plots.py — GET /plots/{id}/{state,sensor_history,
  satellite_history,forecast,suggestions,alerts}
- app/infra/http/alerts.py — POST /alerts/{id}/acknowledge

For each:
- pydantic response model
- depends on get_session + get_current_user
- uses corresponding repository (NOT raw SQLAlchemy in route — keep
  the hexagon)
- pagination via cursor for list endpoints
- OpenAPI summary + description on every route

Tests tests/infra/http/ — one file per resource. Cover 200/401/403/404/
422 for each route. Use httpx AsyncClient + a seeded fixture
(tests/fixtures/seed.py creates tenant + farmer + farm + 4 plots + 100
readings).

Coding standards: routes < 30 lines each. Heavy lifting in repos and
use cases.
```

#### Prompt 3.5 — Generated TypeScript types

```
Cursor task: wire up openapi-typescript + openapi-fetch in agro_app/.

agro_app/package.json scripts:
  "gen-types": "openapi-typescript http://localhost:8000/openapi.json
                 -o src/api/types.gen.ts"

agro_app/src/api/client.ts:
import createClient from "openapi-fetch";
import type { paths } from "./types.gen";
import { getAccessToken, refreshIfNeeded } from "../auth/jwt";

export const api = createClient<paths>({
  baseUrl: process.env.EXPO_PUBLIC_API_URL,
  fetch: async (input, init = {}) => {
    await refreshIfNeeded();
    const token = await getAccessToken();
    init.headers = { ...init.headers, Authorization: `Bearer ${token}` };
    return fetch(input, init);
  },
});

CI job gen-types-check: runs gen-types, fails on git diff.

Show usage: const { data, error } = await api.GET("/api/v1/me/farms");
```

---

## PHASE 4 — Processing: derived metrics, hot rules, rule engine, crop stages (7–10 days)

**Goal:** §3 of the technical reference shipped — derived metrics computed; hot rules fire on every ingest; warm/cold rules run on schedule; cold-tier builds the daily SuggestionCandidate; crop stages updated nightly.

**Files:**
- `app/domain/{derived_metrics,crop_stage,hot_rules,rules_engine,confidence,alert}.py`
- `app/application/{evaluate_hot_rules,dispatch_alert}.py`
- `app/jobs/crop_stage_update.py`
- `app/infra/ai/chroma_rule_repo.py`
- `rules/universal/*.json`, `rules/sugarcane/*.json`, `rules/ginger/*.json`

### Cursor prompts for Phase 4

#### Prompt 4.1 — Derived metrics (pure)

```
Cursor task: app/domain/derived_metrics.py — PURE functions, no
framework imports beyond stdlib + math.

Implement EXACTLY per §3.2 of AgroGuardian technical reference:
- saturation_vapor_pressure_kpa(t)  -- Magnus
- vpd_kpa(t, rh)
- spray_status(delta_t) -> tuple[Literal['RED','GREEN','YELLOW'], str]
- wet_bulb_celsius(t, rh)  -- Stull 2011
- delta_t_celsius(t, rh)
- et0_fao56(t_max, t_min, rh_max, rh_min, u2_m_s, rs_mj_m2_day,
            elevation_m, julian_day)
- etc_mm(et0, kc)
- dew_point_c(t, rh)
- fog_detected(rh, t_minus_dew) -> bool
- fog_intensity(t_minus_dew) -> Literal['none','light','moderate','dense']
- frost_risk(min_temp_forecast) -> bool
- heat_index_c(t, rh)  -- NWS Rothfusz
- leaf_wetness_pct(rh, t_minus_dew, rain_2h_mm)

Use Decimal for inputs; return Decimal with explicit rounding (VPD 3
places, DeltaT 1, ET0 2).

compare_et0(my_et0, om_et0) -> bool — True if disagreement > 30%.

Tests tests/domain/test_derived_metrics.py: ≥ 3 cases per function with
reference values from cited papers (use Hypothesis property-based tests
for the monotonic ones).

Coding standards: every function has docstring with paper citation. NO
imports from anywhere except stdlib + math + decimal.
```

#### Prompt 4.2 — Crop stage state machine

```
Cursor task: app/domain/crop_stage.py and app/jobs/crop_stage_update.py.

domain/crop_stage.py:
STAGE_TABLES per §3.5.3 (sugarcane_adsali + ginger).
compute_stage(crop_key, sowing_date, today=None) -> dict with keys
crop_age_days_today, current_growth_stage, days_in_current_stage,
days_to_next_stage, days_to_harvest, kc_now.

For Plot 3 (no known sowing): infer_sowing_date_from_ndvi(plot_id,
session) -> tuple[date, confidence: Decimal]. Walk back through
satellite_data finding first NDVI >= 0.20. Mark
crop_seasons.sowing_date_inferred=TRUE when used.

jobs/crop_stage_update.py: APScheduler 02:00 IST. For each active
crop_season: compute stage; UPDATE crop_seasons. For inferred-sowing
plots with < 30 days NDVI: also re-infer + refine.

Tests: walk Adsali year day-by-day; assert correct stage at every cutoff.
```

#### Prompt 4.3 — Hot rules

```
Cursor task: app/domain/hot_rules.py and
app/application/evaluate_hot_rules.py.

Domain HOT-001..HOT-007 per §3.3.1 — pure functions:
def hot_001(reading: Reading) -> AlertCandidate | None: ...
def hot_002(reading) -> AlertCandidate | None: ...
... etc.

application/evaluate_hot_rules.py:
async def execute(deps, reading) -> list[AlertId]:
    candidates = run_all_hot_rules(reading)
    fired = []
    for c in candidates:
        if await should_fire(deps.alert_repo, c.alert_type,
                             reading.plot_id):
            aid = await deps.alert_repo.create(c)
            await deps.event_bus.publish("alert.created",
                                          {"id": str(aid)})
            fired.append(aid)
    return fired

should_fire implements debounce (consecutive cycles) + cooldown.

Wire into application/ingest_telemetry.py.

Tests:
- single low_battery doesn't fire (debounce 3)
- three consecutive DO fire
- tamper fires immediately (no debounce)
```

#### Prompt 4.4 — Rule JSON files + ChromaDB indexer

```
Cursor task:

1) rules/sugarcane/SG-001.json through SG-007.json — from §3.6.1, EXACT
JSON shape per §3.4.3.
2) rules/ginger/GN-001..007.json — from §3.6.2.
3) rules/universal/U-SAFE-001..005.json — from §3.6.3.

4) app/infra/ai/chroma_rule_repo.py:
class ChromaRuleRepo implements application.ports.rule_repo.RuleRepo.
- __init__: chromadb.PersistentClient(path=settings.CHROMA_PATH)
- reindex(): drops + recreates rules_universal, rules_sugarcane,
  rules_ginger collections. Uses sentence-transformers
  paraphrase-multilingual-mpnet-base-v2 (pre-bake into Docker image to
  avoid cold-start download).
- retrieve(crop_key, query_text, k, data_tier) -> list[RuleHit]:
  embeds query; queries collection; filters by data_tier metadata.
- Pin embedding model name in chroma metadata so future model upgrades
  trigger automatic reindex.

5) Lifespan hook: on app startup, reindex if any rule JSON file is
newer than the ChromaDB manifest (sha-based).

Tests: reindex() works; rules_sugarcane has N entries; "day 121 moisture
low" retrieves SG-001 in top-3.
```

#### Prompt 4.5 — Rule engine evaluator (pure)

```
Cursor task: app/domain/rules_engine.py.

PURE. Inputs: PlotState dataclass + list of Rule dataclasses (loaded
from JSON elsewhere). Outputs: list of RuleMatch.

Implement per §3.4.4 of AgroGuardian:
- all_conditions_met(rule, plot_state) -> bool
- compute_rule_confidence(rule, plot_state) -> Decimal
- resolve_conflicts(matches) -> list[RuleMatch]
  (higher-layer wins; safety_override blocks same-category lower)
- evaluate_rules(plot_state, rules) -> list[RuleMatch]

Tests tests/domain/test_rules_engine.py:
- SG-001 + U-SAFE-001 (rain > 20mm): assert SG-001 blocked
- SG-001 + Layer-4 Marathwada-vertisol modifier: assert Layer-4 wins
- No matches: returns []
```

#### Prompt 4.6 — Alerts pipeline (debounce, cooldown, severity)

```
Cursor task: app/domain/alert.py and app/application/dispatch_alert.py.

domain/alert.py:
class Severity(StrEnum): CRITICAL, WARNING, ADVISORY, INFO, FORECAST
DEFAULT_CHANNELS = {Severity.CRITICAL: {'fcm','whatsapp','sms'}, ...}
COOLDOWN_HOURS = {Severity.CRITICAL: 1, ...}
DEBOUNCE_CYCLES = {'low_battery': 3, 'tamper': 1, ...}

application/dispatch_alert.py:
async def should_fire(repo, alert_type, plot_id) -> bool
async def write_alert(repo, candidate) -> str | None
async def resolve_alert(repo, alert_id, notes) -> None

Tests: cooldown blocks second alert in window; resolves to allow refire.
```

---

## PHASE 5 — AI / RAG / agent loop with Sonnet + Haiku (6–9 days)

**Goal:** §4 of the doc shipped using **Claude Sonnet 4.6** for T1 daily advisory + T3 farmer chat, **Claude Haiku 4.5** for T2 alerts + T4 outcome reflection. Adapter pattern enables a Gemini/Llama benchmark in month 3 via one new file.

**Files:**
- `app/application/ports/llm_client.py`
- `app/infra/ai/{anthropic_client,tool_runner,prompts,confidence}.py`
- `app/infra/ai/tools/` (6 tool files)
- `app/infra/ai/prompts/{T1,T2,T3,T4}.txt`
- `app/application/{generate_advisory,farmer_chat}.py`
- `app/domain/confidence.py`
- `app/jobs/{advisory_generation,outcome_reflection}.py`
- `app/infra/http/chat.py` (SSE)
- `scripts/bench_llms.py` (month-3 benchmark scaffold)

### Cursor prompts for Phase 5

#### Prompt 5.1 — Anthropic client adapter (Sonnet + Haiku routing)

```
Cursor task: app/infra/ai/anthropic_client.py and
app/application/ports/llm_client.py.

ports/llm_client.py:
class ModelRole(StrEnum):
    PRIMARY = 'primary'      # quality-sensitive (T1, T3)
    TRIAGE = 'triage'        # cheap classify (T2, T4)

class LlmClient(Protocol):
    async def complete(self, *, model_role: ModelRole, system: str,
                       user: str, tools: list[ToolDef] | None,
                       max_tokens: int) -> LlmResponse: ...
    async def complete_streaming(self, *, model_role: ModelRole,
                                  system: str, user: str,
                                  tools: list[ToolDef] | None,
                                  max_tokens: int)
                                  -> AsyncIterator[LlmChunk]: ...

The point of ModelRole (not a model name) is that swapping vendors is
one adapter file; use cases never know which model is running.

infra/ai/anthropic_client.py:
class AnthropicClient implements LlmClient.
- Reads settings.ANTHROPIC_MODEL_SONNET and ANTHROPIC_MODEL_HAIKU.
- _resolve_model(role):
    PRIMARY -> Sonnet
    TRIAGE -> Haiku
- Uses anthropic.AsyncAnthropic SDK.
- Tracks tokens_in, tokens_out, cost_inr per call:
    PRICING_USD_PER_MILLION = {
      'claude-sonnet-4-6':       {'in': 3.00, 'out': 15.00},
      'claude-haiku-4-5-20251001': {'in': 0.80, 'out': 4.00},
    }
- Converts USD -> INR via settings.USD_INR_RATE.
- Implements tool_use loop with max_iter=5.
- Implements complete_streaming via the SDK's messages.stream API.

Tests tests/infra/ai/test_anthropic_client.py with respx + stubbed SDK:
- PRIMARY -> Sonnet; TRIAGE -> Haiku
- tool_use loop terminates correctly
- Cost tracking correct
- max_iter exhaustion raises ToolUseLoopExceeded

Future-proofing: add a stub app/infra/ai/gemini_client.py with class
GeminiClient implements LlmClient raising NotImplementedError —
documents the seam for the month-3 benchmark.

Coding standards: API key never logged. Failed calls increment
metrics.llm_failure; retry with exponential backoff once.
```

#### Prompt 5.2 — Tool implementations

```
Cursor task: app/infra/ai/tools/ — six files.

Each tool:
- input_schema dict at module level (Anthropic tool_use shape)
- async def execute(deps, **kwargs) -> dict

Tools per §4.5:
- get_latest_readings.py (plot_id, hours)
- get_satellite_indices.py (plot_id, weeks)
- get_forecast.py (farm_id, days)
- get_irrigation_history.py (plot_id, days)
- get_action_history.py (plot_id, days)
- query_rules.py (crop, category, stage)

Each calls the corresponding repo via deps. Returns small dict (< 5 KB).
Validates inputs strictly — raise ValueError on bad input so Anthropic
surfaces it back to Claude.

tool_runner.py:
TOOL_REGISTRY = {"get_latest_readings": get_latest_readings.execute, ...}
TOOL_DEFINITIONS = [load each input_schema with name + description]

Tests per tool with a seeded DB.
```

#### Prompt 5.3 — Confidence scoring (pure)

```
Cursor task: app/domain/confidence.py — PURE.

compute_confidence(c: SuggestionCandidate, llm_self_assessed: Decimal)
-> Decimal exactly per §4.6.1 of AgroGuardian. Each multiplicative
factor named clearly:
- data_tier_penalty(c)
- stale_satellite_penalty(c)
- sensor_health_penalty(c)
- low_battery_penalty(c)
- rule_strength_factor(c)
- conflict_count_factor(c)
- moisture_disagreement_factor(c)
- llm_blend(score, llm_self) -- 70/30

def classify_band(score: Decimal)
    -> Literal['autosend','autosend_caveat','queue','block']

Bands: ≥0.90 autosend; 0.75-0.89 autosend_caveat; 0.55-0.74 queue;
< 0.55 block.

Tests: Hypothesis property-based — score always in [0,1], monotonic in
good signals, low score classifies right.
```

#### Prompt 5.4 — Prompt templates

```
Cursor task: app/infra/ai/prompts/{T1,T2,T3,T4}.txt verbatim from §4.4
of AgroGuardian.

Each file starts:
# version: 1
# model_role: primary | triage

T1 (daily advisory):    model_role: primary
T2 (alert response):    model_role: triage
T3 (farmer chat):       model_role: primary
T4 (outcome reflection):model_role: triage

Use Jinja2 {{var}} placeholders.

app/infra/ai/prompts/__init__.py:
@dataclass(frozen=True) RenderedPrompt: system, user, version,
                                          model_role

def render(template_name: str, **vars) -> RenderedPrompt:
    # Read file; parse #version + #model_role headers; split on [SYSTEM]
    # [USER]; render via jinja2.Template with autoescape=False.

Tests: render T1 with sample SuggestionCandidate; assert no {{ in
output; assert model_role == 'primary'.
```

#### Prompt 5.5 — Advisory generation cold-tier job

```
Cursor task: app/application/generate_advisory.py and
app/jobs/advisory_generation.py.

generate_advisory.execute(plot_id, deps) per §4.1.2 flow:
1) Load PlotState from repos.
2) Build SuggestionCandidate (rule engine + derived metrics + recent
   actions + satellite + weather).
3) Retrieve top-12 rules from ChromaDB.
4) Render T1 -> RenderedPrompt(system, user, version='1',
   model_role='primary').
5) await deps.llm.complete(model_role=ModelRole.PRIMARY, system=...,
   user=..., tools=ENABLED_TOOLS, max_tokens=600). Routes to Sonnet.
6) compute_confidence; classify_band.
7) Write ai_suggestions row with prompt_template_version='T1.v1',
   ai_model_version='sonnet-4-6', tokens_used, llm_cost_inr.
8) If band=='queue', also write alerts_notifications row severity=advisory
   alert_type=agronomist_review_needed.

Cost cache: by (crop, stage, soil_type_decile, weather_decile,
sensor_decile) hashed. Reuse cached suggestion < 24 h old.

Anthropic batch API: when generating > 20 plots in one go, use the
batch endpoint (50% discount).

jobs/advisory_generation.py: 02:30 IST cron. Idempotent per plot per day.

Tests: stub LlmClient returns canned JSON; assert ai_suggestions row
written with correct fields.

Coding standards: every step idempotent. Cost-cache key construction
documented in docstring.
```

#### Prompt 5.6 — Farmer chat (SSE) using Sonnet

```
Cursor task: app/application/farmer_chat.py and app/infra/http/chat.py.

http/chat.py:
POST /api/v1/chat — body ChatRequest{message, context}. Returns SSE
stream.

farmer_chat.execute(deps, request, async_yield):
- Load farmer + plots + last 14 days actions/suggestions.
- Render T3 (model_role='primary').
- Stream from deps.llm.complete_streaming(model_role=PRIMARY,
                                            tools=ENABLED, max_tokens=800).
- On tool_use blocks: execute via tool_runner; yield {type:tool_call}
  + {type:tool_result} SSE events.
- Yield {type:token} per token.
- On done: yield {type:done} and persist chat_messages row.

Token budget: cap 1600 input (truncate history if exceeded) + 800
output.

Rate limit: pilot_internal tier bypasses; Basic tier 10 messages/day.

Tests: stubbed streaming SDK; SSE event order verified; chat_messages
row written.
```

#### Prompt 5.7 — Outcome reflection (T4) using Haiku

```
Cursor task: app/jobs/outcome_reflection.py.

Daily 04:00 IST:
1) Find ai_suggestions where generated_at <= now - 7 days AND no
   ai_learning_log row.
2) Gather farmer_actions in window, ndvi/moisture before/after, new
   alerts.
3) Render T4 (model_role='triage').
4) deps.llm.complete(model_role=ModelRole.TRIAGE, ...) -> Haiku.
5) Parse JSON; INSERT ai_learning_log row.
6) If 'inconclusive' at T+7, defer to T+14.

Tests: seeded suggestion + actions; assert ai_learning_log row written.
```

#### Prompt 5.8 — Month-3 benchmark scaffold

```
Cursor task: scripts/bench_llms.py.

Streamlit one-pager (or CLI):
1) Loads last 100 SuggestionCandidate records + corresponding T1
   prompts as rendered.
2) For each, re-renders T1 and calls:
   - AnthropicClient -> Sonnet
   - AnthropicClient -> Haiku
   - GeminiClient (stub today; real when ready)
3) Records latency, token cost, JSON validity, cited_rule_ids accuracy
   (set difference vs original Sonnet response).
4) Surfaces side-by-side Marathi comparison for human review.

Save results to bench_results/{date}.json.

Coding standards: read-only — never writes to ai_suggestions.
```

---

## PHASE 6 — Copernicus + NASA Earthdata + Open-Meteo + IMD (5–7 days)

**Goal:** §5 of the doc shipped with commercial-safe satellite stack.

**Files:**
- `app/application/ports/{satellite_client,forecast_client}.py`
- `app/infra/satellite/{copernicus_sentinel2,nasa_earthdata_smap,enrich}.py`
- `app/infra/forecast/{open_meteo,imd}.py`
- `app/application/onboarding/boundary.py`
- `app/infra/http/boundary.py`
- `app/jobs/{satellite_ingest,forecast_pull}.py`

### Cursor prompts for Phase 6

#### Prompt 6.1 — Copernicus Sentinel-2

```
Cursor task: app/infra/satellite/copernicus_sentinel2.py.

Use the official sentinelhub-py library. Configure for the Copernicus
Data Space free tier:
  config.sh_base_url = "https://sh.dataspace.copernicus.eu"
  config.sh_client_id = settings.COPERNICUS_CLIENT_ID
  config.sh_client_secret = settings.COPERNICUS_CLIENT_SECRET
  config.sh_token_url =
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

class CopernicusSentinel2 implements
application.ports.satellite_client.SatelliteClient.

async def fetch_latest_indices(self, plot_geojson: dict, plot_id: str,
                               look_back_days: int = 30) -> dict | None:
    # Catalog query: bbox of plot polygon, last look_back_days,
    #   cloud cover < 20%.
    # Get latest scene's tile date.
    # Process API request with custom evalscript computing NDVI, NDRE,
    #   NDWI, NDMI, EVI, SAVI returning multi-band GeoTIFF.
    # Read with rasterio; mask with the polygon; compute
    #   mean/min/max/stdev per band using numpy.ma.
    # Upload raster crop to Cloudflare R2 (key: rasters/{plot_id}/{date}.tif)
    # Return dict matching satellite_data fields.

Evalscript template (Copernicus Data Space supports custom evalscripts
via Process API) computes all 6 indices in one round-trip — see
https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Evalscript/V3.html

detect_stressed_zones(image_bytes, field) — vectorize NDVI < 0.40 mask
via rasterio.features.shapes + shapely; return (stressed_area_pct,
geojson).

Tests with fixture polygon over agricultural area in Maharashtra (public
test polygon I'll provide). Skip integration test in CI if no CDSE
credentials.

Coding standards: rate-limited at SDK level (~30,000 PU/month free tier
— see Copernicus docs). Retry with exponential backoff on 5xx.
```

#### Prompt 6.2 — NASA Earthdata SMAP

```
Cursor task: app/infra/satellite/nasa_earthdata_smap.py.

Use earthaccess library. Auth:
  earthaccess.login(strategy="environment")
reads EARTHDATA_USERNAME and EARTHDATA_PASSWORD from env.

class NasaEarthdataSmap implements SatelliteClient (subset).

async def fetch_smap_soil_moisture(self, plot_geojson, days=7)
    -> dict | None:
    # earthaccess.search_data(short_name='SPL4SMGP', ...) for bbox.
    # Take most recent granule.
    # Download via earthaccess (or OPeNDAP subset URL for bbox slice).
    # Open with xarray; extract sm_surface, sm_rootzone for plot.
    # Mean over plot pixels (1-2 pixels at 9km).
    # Return dict matching satellite_data fields.

normalize_to_0_1(m3m3): clamp 0..0.5 m3/m3 -> 0..1.

Tests: with fixture polygon, fetch latest SMAP; assert non-null.

Coding standards: earthaccess caches downloads in ~/.earthaccess —
mount as volume so restarts don't re-download.
```

#### Prompt 6.3 — Satellite ingest job

```
Cursor task: app/jobs/satellite_ingest.py.

03:00 IST daily. For each plot with gps_boundary_geojson NOT NULL:
1) Skip if last image_date < 3 days old.
2) fetch_latest_indices via Copernicus.
3) fetch_smap_soil_moisture via NASA.
4) Combine into one satellite_data row when both exist for same date;
   else partial row.
5) Run enrich.classify_ndvi/ndwi/score; populate enum + score columns.
6) Evaluate satellite-derived rules (NDVI drop > 0.10 in 7d -> alert;
   stressed_area_pct > 25 -> alert).

Per-plot failure does NOT stop others — try/except per plot with
structured log.

Tests: mocked satellite clients; expected rows written.
```

#### Prompt 6.4 — Weather forecast pull

```
Cursor task: app/infra/forecast/open_meteo.py, imd.py,
jobs/forecast_pull.py.

open_meteo.py: fetch_open_meteo_forecast(lat, lon, hours_ahead=72) per
§5.4.1. timezone='Asia/Kolkata'. Pull hourly: temperature_2m,
relative_humidity_2m, precipitation_probability, precipitation,
windspeed_10m, winddirection_10m, cloud_cover,
et0_fao_evapotranspiration, visibility, apparent_temperature.

imd.py: best-effort against IMD Mausam public API. If endpoint changes,
log+skip but don't error.

forecast_pull.py: every 6 h (00, 06, 12, 18 IST). For each farm:
- Fetch Open-Meteo
- If month in (Jun-Oct), also fetch IMD; cross-check (§5.4.2)
- Bulk UPSERT into weather_forecasts on (farm_id, forecast_for_datetime)
- Compute spray_suitability, irrigation_recommendation, frost_risk,
  heat_wave_risk at write time

Tests: stub httpx; 72 rows / farm / pull.
```

#### Prompt 6.5 — Boundary onboarding

```
Cursor task: app/application/onboarding/boundary.py +
app/infra/http/boundary.py.

boundary.py:
smooth_walk_to_polygon(pings, accuracy_threshold_m=15.0) per §5.6.2:
1) Drop low-quality pings (accuracy > threshold).
2) Moving-average smoothing (window 5).
3) Douglas-Peucker simplification via shapely (tolerance ~2e-5).
4) Sanity-check area (>= 200 m², <= 25 acres).

http/boundary.py:
POST /api/v1/plots/{plot_id}/boundary/walk — body: list of
{lat, lon, accuracy_m, ts}. Returns {polygon_geojson, area_acre}.
POST /api/v1/plots/{plot_id}/boundary/draw — body: {polygon_geojson}.

Both write to plots.gps_boundary_geojson via PostGIS
(ST_GeomFromGeoJSON).

Tests: 50 pings forming 30m square; area_acre ≈ 0.22 within 10%.
```

---

## PHASE 7 — Notifications: FCM + WhatsApp (2–3 days)

**Goal:** §7 of the doc shipped for FCM and WhatsApp. `SmsClient` Protocol defined; no implementation. SMS adapter file is a stub raising NotImplementedError so the seam is documented but the channel is silently dropped from routing in pilot.

**Files:**
- `app/application/ports/{fcm,whatsapp,sms}_client.py`
- `app/infra/notify/{fcm,whatsapp_meta,dispatcher,routing,dlq}.py`
- `app/jobs/notify_drain.py`

### Cursor prompts for Phase 7

#### Prompt 7.1 — Channel ports

```
Cursor task: app/application/ports/{fcm,whatsapp,sms}_client.py.

fcm_client.py:
class FcmClient(Protocol):
    async def send(self, token: str, payload: NotificationPayload)
        -> DispatchResult: ...

whatsapp_client.py:
class WhatsAppClient(Protocol):
    async def send_advisory(self, phone_e164: str,
                            payload: NotificationPayload)
        -> DispatchResult: ...
    async def send_otp(self, phone_e164: str, code: str) -> str:
        """Returns provider message_id. Also implements OtpDeliveryClient."""

sms_client.py:
class SmsClient(Protocol):
    async def send(self, phone_e164: str, payload: NotificationPayload)
        -> DispatchResult: ...
    # NO implementation in pilot.
    # Phase 13 adds SmsMsg91Adapter implementing both this and
    # OtpDeliveryClient.

DispatchResult: {success, provider_message_id, error_code,
                 error_message, retire_destination}
NotificationPayload: {title_marathi, body_marathi, deep_link, data,
                      severity, template_name}.
```

#### Prompt 7.2 — FCM adapter

```
Cursor task: app/infra/notify/fcm.py.

Use firebase-admin SDK. Initialize once at module load with
firebase_admin.initialize_app(credentials.Certificate(
  settings.FCM_SERVICE_ACCOUNT_JSON)).

class FcmAdapter implements FcmClient.
- send(token, payload): builds messaging.Message with notification +
  data + android-specific channel_id ('agro-critical' for CRITICAL,
  'agro-warning' for WARNING, etc.).
- Handles UnregisteredError -> retire_destination=True.
- Handles InvalidArgumentError -> retire_destination=True; log.
- Handles QuotaExceeded -> retry (transient).

Tests with mocked firebase_admin: retire on UnregisteredError; retry on
QuotaExceeded.
```

#### Prompt 7.3 — WhatsApp adapter (advisory + OTP unified)

```
Cursor task: app/infra/notify/whatsapp_meta.py.

class WhatsAppAdapter implements BOTH WhatsAppClient AND
OtpDeliveryClient. Replaces the Phase 3 stub.

Initialize with META_WHATSAPP_TOKEN, META_WHATSAPP_PHONE_NUMBER_ID.

async def send_advisory(phone_e164, payload) -> DispatchResult:
    # Check wa_inbound_log for last inbound from phone < 24 h.
    # If yes -> text message: {"type":"text","text":{"body": body}}
    # If no -> template message with name=ADVISORY_TEMPLATE_NAME and
    #          body parameters from payload.data
    # Returns DispatchResult; retires destination on permanent failures.

async def send_otp(phone_e164, code) -> str:
    # Always uses authentication template (regardless of 24-h window).
    # Returns provider message_id.

Error handling:
- 400 code 131026 (24-h window closed) -> retry as template
- 400 code 132xxx (template issue) -> raise PermanentDispatchError
  (alert ops via Sentry — template rejected or revoked)
- 5xx -> retry once with backoff
- 429 -> raise RateLimitedError

Tests with respx:
- send_advisory inside 24-h window -> text type
- send_advisory outside 24-h window -> template type
- send_otp always uses authentication template
- 132xxx -> Permanent
- 5xx retried once

Coding standards: never log the OTP. Last-4 of phone in logs only.
```

#### Prompt 7.4 — Dispatcher worker + routing + DLQ

```
Cursor task: app/infra/notify/{dispatcher,routing,dlq}.py +
app/jobs/notify_drain.py.

routing.py:
REGISTERED_CHANNELS = {'fcm', 'whatsapp'}   # pilot
# Phase 13 will add 'sms' once SmsMsg91Adapter is wired in main.py.

def resolve_channels(severity, prefs) -> list[ChannelName]:
    base = DEFAULT_CHANNELS[severity]
    return [c for c in base
            if prefs.get(c + '_enabled', True)
            and c in REGISTERED_CHANNELS]

dispatcher.py:
async def dispatch_one(alert_row, deps) -> DispatchOutcome:
    farmer = await deps.farmer_repo.find(alert_row.farmer_id)
    channels = resolve_channels(alert_row.severity,
                                 farmer.notification_preferences)
    outcomes = []
    for ch in channels:
        try:
            client = deps.channel_clients[ch]
            recipient = (farmer.fcm_token if ch == 'fcm'
                         else farmer.phone_e164)
            payload = alert_row.to_payload()
            if ch == 'whatsapp':
                result = await client.send_advisory(recipient, payload)
            else:
                result = await client.send(recipient, payload)
            await deps.dispatch_log.record(alert_row.id, ch, result)
            if result.retire_destination:
                await deps.farmer_repo.invalidate_destination(farmer.id, ch)
            outcomes.append(result)
        except Exception as e:
            await deps.dispatch_log.record_failure(alert_row.id, ch, str(e))
    return DispatchOutcome(outcomes=outcomes)

notify_drain.py: every 30 s, drain alerts where dispatch_status='pending'
LIMIT 50. Retry per [30s, 2min, 10min, 1h, 6h]; then DLQ.

Idempotency: dispatch_log UNIQUE (alert_id, channel).

Tests: stubbed adapters; verify retry + DLQ; verify SMS dropped silently
in pilot.
```

---

## PHASE 8 — Firmware + OTA (10–15 days, parallelizable with cloud phases)

**Goal:** real Sub Node + Main Node firmware shipped; OTA pipeline working with ed25519 signing. This phase runs in parallel with Phases 1–7; by Phase 7 your cloud should be processing fake-Main-Node telemetry, and replacing the fake with real hardware is the final pre-install step.

### Cursor prompts for Phase 8

#### Prompt 8.1 — Sub Node firmware (ATmega328P)

```
Cursor task: firmware/sub_node/ — full PlatformIO project.

platformio.ini:
[env:atmega328p_8mhz]
platform = atmelavr
board = pro8MHzatmega328
framework = arduino
upload_protocol = usbasp
upload_flags = -Pusb
build_flags = -DF_CPU=8000000L -Wall -Wextra -Os
lib_deps =
    jgromes/RadioLib@^7.0
    PaulStoffregen/OneWire@^2.3.7
    milesburton/DallasTemperature@^3.11

Implement loop() per §1.7 of AgroGuardian:
- src/main.c — setup() + loop() driving wake-measure-validate-transmit-sleep
- src/lora.c/h — RadioLib SX1278 (433 MHz, SF9, BW125, CR4/5, 14 dBm,
  sync 0x12)
- src/npk_modbus.c/h — manual CRC16, 9600 baud RS485 via SoftwareSerial
- src/sensors.c/h — capacitive moisture ADC, DS18B20 1-Wire, battery
  divider
- src/packet.c/h — pack_npk, telemetry_packet_t (12-byte) per §1.6.1
- src/cadence.c/h — decide_cadence(reading, mode) state machine (§1.4.1)
- src/eeprom.c/h — 8-slot backlog ring buffer
- src/sleep.c/h — WDT-driven deep sleep

After build, verify:
avr-size .pio/build/atmega328p_8mhz/firmware.elf
=> text < 28000, data < 1500.

Add `make sim` target compiling host-x86 stub that prints each cycle.

Coding standards: no malloc, no recursion, no floats unless absolutely
necessary, every ISR < 10 lines.
```

#### Prompt 8.2 — Main Node firmware (ESP32)

```
Cursor task: firmware/main_node/ — full PlatformIO project,
ESP-IDF + Arduino.

platformio.ini:
[env:esp32_main]
platform = espressif32@^6.5
board = esp32dev
framework = arduino, espidf
monitor_speed = 115200
build_flags = -DCORE_DEBUG_LEVEL=3
board_build.partitions = partitions_dual_ota.csv
lib_deps =
    jgromes/RadioLib@^7.0
    adafruit/Adafruit BME280 Library@^2.2
    knolleary/PubSubClient@^2.8
    bblanchon/ArduinoJson@^7.0

FreeRTOS tasks (src/main.cpp):
- task_lora_rx (priority 5, core 0)
- task_weather (priority 3, core 1, 5-min period)
- task_modem (priority 4, core 0)
- task_mqtt (priority 4, core 1)
- task_sd_buffer (priority 3, core 1)
- task_health (priority 2, core 1, 5-min period)
- task_cmd_handler (priority 4, core 0)
- task_ota (priority 5, core 1, on-demand)

Implement per §1.8 of AgroGuardian:
- src/lora_gateway.cpp — receive Sub Node packets, decode, forward as
  JSON on outbox queue
- src/modem_4g.cpp — A7672S AT command driver
- src/mqtt_client.cpp — PubSubClient over WiFiClientSecure with CA bundle
- src/sd_buffer.cpp — outbox JSONL to /sd/outbox/YYYY-MM-DD.jsonl; drain
  at 1 msg / 250 ms on reconnect
- src/weather.cpp — BME280 + IST anemometer pulse counter + wind vane
  resistor divider + rain tipping bucket
- src/ota.cpp — ESP-IDF OTA partition swap with ed25519 verification
- src/config_runtime.cpp — hot-reloadable config from /sd/config.json
  for §8.7

Partitions: 4 MB = factory + ota_0 + ota_1 + storage.

Tests firmware/main_node/tests/ with Unity framework.

Coding standards: OTA MUST verify ed25519 signature + SHA-256 before
swap, MUST mark new partition valid after first successful MQTT connect,
MUST roll back on boot failure.
```

#### Prompt 8.3 — OTA server pipeline

```
Cursor task: app/infra/ota/ + app/infra/http/ota.py.

signing.py:
def sign_binary(path: str) -> bytes:
    """ed25519 sign with OTA_SIGNING_PRIVATE_KEY_PEM."""
def verify_binary(path: str, sig: bytes, public_key_pem: bytes) -> bool

manifest.py:
@dataclass Manifest:
    manifest_id: str
    device_class: Literal["sub_node", "main_node"]
    version: str
    binary_url: str           # R2 signed URL
    sha256: bytes
    signature: bytes
    rollout_percentage: int   # 10 -> 50 -> 100
    aborted: bool

rollout.py:
def pick_devices_for_canary(device_class, percentage) -> list[device_id]
def maybe_promote(manifest_id) -> bool   # checks success rate

http/ota.py routes (admin-only):
POST /api/v1/admin/ota/upload (multipart)
POST /api/v1/admin/ota/release/{manifest_id}/canary
POST /api/v1/admin/ota/release/{manifest_id}/promote
POST /api/v1/admin/ota/release/{manifest_id}/abort
GET  /api/v1/devices/{device_id}/ota/manifest  -- device polls

Tests:
- ed25519 sign+verify round-trip
- Canary 0 -> 10 -> 50 -> 100; abort halts
- Rejected device sees no manifest update

Coding standards: never expose private key in any response. Public key
baked into firmware at build time AND in R2 metadata for pin-verify.
```

---

## PHASE 9 — Farmer App (10–14 days)

**Goal:** the 4-tab Expo app per §6.2. Login uses WhatsApp OTP.

### Cursor prompts for Phase 9

#### Prompt 9.1 — Expo bootstrap + WhatsApp-OTP login

```
Cursor task: bootstrap agro_app/ with Expo SDK 51 + TypeScript.

npx create-expo-app@latest agro_app --template typescript
cd agro_app
npx expo install expo-router expo-secure-store expo-notifications
  expo-speech expo-av react-native-maps expo-location expo-localization
npm i @tanstack/react-query zustand react-hook-form zod
  openapi-fetch i18next react-i18next react-native-svg
npm i -D openapi-typescript

Create:
- src/api/client.ts (Prompt 3.5 spec)
- src/auth/jwt.ts — SecureStore + decode + auto-refresh
- src/auth/otp.ts —
    requestOtp(phone) -> POST /api/v1/auth/otp/request
    verifyOtp(phone, code) -> POST /api/v1/auth/otp/verify
- src/i18n/index.ts — i18next, default 'mr'
- src/i18n/mr.json — include WhatsApp-OTP strings:
    "login.phone_label": "मोबाईल नंबर"
    "login.send_otp": "OTP पाठवा"
    "login.otp_sent_whatsapp": "OTP तुमच्या WhatsApp वर पाठवला गेला आहे"
    "login.otp_label": "WhatsApp वर आलेला 6-अंकी कोड भरा"
    "login.verify": "पुष्टी करा"
    "login.error.invalid": "कोड बरोबर नाही. परत प्रयत्न करा."
    "login.error.expired": "कोड संपला आहे. नवीन OTP मागवा."
    "login.error.locked": "खूप वेळा चुकीचा कोड. 30 मिनिटांनी प्रयत्न करा."
    "login.error.rate_limit": "कृपया 10 मिनिटांनी प्रयत्न करा."
- src/store/appStore.ts — zustand auth state
- src/screens/Login.tsx — two-step (phone -> code) with WhatsApp-specific
  copy. WhatsApp icon next to "OTP पाठवा".
- src/App.tsx — NavigationContainer + bottom tabs + auth gate

Tests: render Login, type phone, verify API call mock fires with E.164.
Verify WhatsApp-specific Marathi copy appears.

Coding standards: every component default-exports; Props type exported
named; no inline Marathi.
```

#### Prompt 9.2 — Home tab

```
Cursor task: src/screens/HomeTab.tsx + components/AdvisoryCard.tsx +
components/ConfidenceBadge.tsx.

HomeTab:
- For each plot in currentFarm.plots, render AdvisoryCard.
- Pull-to-refresh refetches GET /plots/{id}/suggestions?limit=1.

AdvisoryCard:
- Plot header: cropName + stage + day count
- Confidence badge (color from band)
- Full Marathi message body
- आज करायचे: action highlighted
- "Why?" expander: cited rule_ids + english_explanation (small)
- "I did this" button -> POST /plots/{id}/farmer_actions with type from
  first cited rule

Empty state: 'अद्याप सल्ला आला नाही. AI रात्री अॅडव्हायझरी तयार करते.'

Tests: render with fixture; tap I-did-this; verify POST.
```

#### Prompt 9.3 — Sensors tab + 24h chart

```
Cursor task: src/screens/SensorsTab.tsx + components/SensorCard.tsx +
components/ChartHistory.tsx.

SensorCard per plot:
- Sensor-only plot: moisture/N/P/K/pH/EC/temp/battery cards
- Satellite-only plot: NDVI/NDWI/SMAP cards + 'Satellite-only' badge
- Tap any value -> ChartHistory modal with last 24h chart
- Sensor-health band at bottom: green/amber/red

ChartHistory: use react-native-gifted-charts OR victory-native (pick
after 2-day spike; document decision).

Force Refresh button: POST /plots/{id}/force_refresh; show 429 toast on
rate-limit.

Tests: snapshot test; satellite-only fixture renders satellite layout.
```

#### Prompt 9.4 — Chat tab + voice

```
Cursor task: src/screens/ChatTab.tsx + components/ChatBubble.tsx +
src/lib/voice.ts.

UI: bubble list (FlatList inverted) + input bar with mic button.

Mic press: expo-speech recognition mr-IN -> fill input.
Send: SSE connection to POST /api/v1/chat via react-native-event-source.
Stream tokens into growing assistant bubble; render tool_call /
tool_result chips inline.
On done: expo-av TTS plays assistant message in Marathi.

History: useInfiniteQuery against GET /chat/history?cursor=...

KVK button: if confidence < 0.70, show 'KVK ला संपर्क करा' one-tap dial.

Tests: stubbed SSE; verify token order + TTS invocation.
```

#### Prompt 9.5 — Crop-change wizard

```
Cursor task: src/screens/CropChangeWizard/{Step1..6,index}.tsx.

Each step matches §6.4.2 exactly. State in useReducer. Confirm at
Step 6: POST /plots/{id}/crop_change. On 200, show success + 'New
advisory will be ready in ~3 min', navigate Home.

Tests: walk 6 steps; verify POST body shape.

Coding standards: each step < 150 lines; Marathi in i18n.
```

#### Prompt 9.6 — Boundary walk

```
Cursor task: src/screens/BoundaryWalk.tsx + src/lib/geo.ts.

expo-location watchPositionAsync at 1 Hz; accumulate pings in zustand.
Live polygon on react-native-maps.

End Walk: POST /plots/{id}/boundary/walk. Display server-smoothed
polygon; Confirm or Redo.

Accuracy > 15m too long -> warning ('कमी अचूकता — आकाश दिसेल अशा ठिकाणी जा').

Draw-on-map fallback (Method B): polygon-drawing UI on react-native-maps.

Tests: simulated pings produce expected polygon shape.
```

---

## PHASE 10 — Founder/Agronomist Dashboard (5–7 days)

**Goal:** §6.3's five views + ops console — Streamlit.

### Cursor prompts for Phase 10

#### Prompt 10.1 — Streamlit auth shell

```
Cursor task: agro_dashboard/streamlit_app.py + components/auth.py +
components/api_client.py.

streamlit_app.py:
- Login form (email + password) -> POST /api/v1/auth/login -> JWT
  stored in st.session_state
- Sidebar nav role-gated:
  - admin: all 6 pages
  - agronomist: 2 (Queue), 3 (Single Farm), 4 (AI Accuracy)
  - technician: 3, 5 (Device Health)
- Auto-refresh selector (off | 30s | 60s) at top

api_client.py: thin httpx wrapper signing every request with JWT.

Tests: 3 different JWTs (admin/agronomist/technician); verify right
pages appear; others 403.
```

#### Prompt 10.2 — The five views + ops console

```
Cursor task: agro_dashboard/pages/1_Live_Operations.py through
6_Ops_Console.py.

1_Live_Operations.py: auto-refresh; one row per active plot with columns
from §6.3.3. Default sort by latest critical alert. Filters by farm,
crop, data_tier, severity, last-contact-recency.

2_Agronomist_Queue.py: implement §6.3.2 layout verbatim. Approve /
Approve-edited / Reject buttons call corresponding API.

3_Single_Farm_Deep_Dive.py: pick farm + plot; render 7-day NDVI,
24-hour sensor lines, 14-day forecast strip, recent actions, recent
suggestions.

4_AI_Accuracy.py: aggregate ai_learning_log by rule_id last 30 days;
suggestion_accuracy stacked bar; confidence-band drift line.

5_Device_Health.py: per-device battery + RSSI + last-seen; OTA status;
fault history.

6_Ops_Console.py (admin-only): system health summary; DLQ replay; force
OTA check; recompute crop stages; reindex rules; SQL inspector with
hardcoded allowlist (never accept arbitrary SQL).

Coding standards: @st.cache_data(ttl=...) aggressively. Each page < 300
lines.
```

---

## PHASE 11 — Quota scaffolding + tier-aware no-op (1–2 days)

**Goal:** the code paths for tier-aware features exist from day one, so adding real quotas + Razorpay billing in Phase 14 is a config-and-side-effect change, not a refactor.

**Files:**
- `app/domain/tier.py`
- `app/application/check_quota.py`
- Integration in `chat.py` and `advisory_generation.py`

### Cursor prompts for Phase 11

#### Prompt 11.1 — Quota scaffolding

```
Cursor task: app/domain/tier.py + app/application/check_quota.py.

domain/tier.py:
class Tier(StrEnum):
    PILOT_INTERNAL = 'pilot_internal'
    BASIC = 'basic'
    STANDARD = 'standard'
    PRO = 'pro'

@dataclass(frozen=True)
class TierLimits:
    max_chat_messages_per_day: int   # -1 == unlimited
    max_active_plots: int
    advisory_quality: ModelRole       # PRIMARY (Sonnet) or TRIAGE (Haiku)
    satellite_features: Literal['basic', 'full']
    priority_support: bool

TIER_LIMITS = {
    Tier.PILOT_INTERNAL: TierLimits(-1, -1, ModelRole.PRIMARY, 'full', True),
    Tier.BASIC:          TierLimits(10, 4,  ModelRole.TRIAGE,  'basic', False),
    Tier.STANDARD:       TierLimits(50, 10, ModelRole.PRIMARY, 'full',  False),
    Tier.PRO:            TierLimits(-1, -1, ModelRole.PRIMARY, 'full',  True),
}

application/check_quota.py:
async def execute(deps, farmer_id, resource, amount=1)
    -> tuple[bool, str | None]:
    """Returns (allowed, marathi_denial_message_or_None).
    PILOT: tenant.tier=='pilot_internal' always returns (True, None).
    Phase 14 wires real subscription state checks."""
    tenant = await deps.tenant_repo.find_by_farmer(farmer_id)
    if tenant.tier == Tier.PILOT_INTERNAL:
        return (True, None)
    limits = TIER_LIMITS[tenant.tier]
    if resource == 'chat_messages_per_day':
        if limits.max_chat_messages_per_day < 0:
            return (True, None)
        used = await deps.quota_repo.usage_today(farmer_id, resource)
        if used + amount > limits.max_chat_messages_per_day:
            return (False, 'दैनिक मर्यादा संपली. उद्या परत प्रयत्न करा.')
    return (True, None)

Integrate:
- chat.py: before LLM call (skipped for pilot_internal)
- advisory_generation.py: pick model_role from limits.advisory_quality
  (pilot_internal always gets PRIMARY = Sonnet)

Tests: with pilot_internal farmer, 100 chat calls succeed; with Basic
tier (future), 11th call returns 429 with Marathi message.

Coding standards: every quota check is non-blocking. Failed quota
lookups fail open (allow) but log a warning.
```

---

## PHASE 12 — Operations: monitoring + calibration + backups + ops console (5–10 days)

**Goal:** §9 (calibration) and §10 (operations) shipped. System survives a 3 AM page.

### Cursor prompts for Phase 12

#### Prompt 12.1 — Calibration pipeline

```
Cursor task: app/application/calibration.py + http/calibration.py.

POST /api/v1/admin/calibration/update — admin-only. Body:
{device_id, sensor, slope, intercept, lab_id, calibrated_at}.

Updates device_registry.calibration_json[sensor] = {slope, intercept,
calibrated_at, lab_id}; INSERTs calibration_history row.

Queues a downlink Cfg packet on next contact (writes to a pending_cfg
table; MQTT broker on next health publish sends the Cfg ACK to device).

Weekly drift-detection job:
- For Sub Node plots: compare moisture_1 vs moisture_2 over last 7 days;
  if mean deviation > 8% -> create sensor_drift_suspected alert.
- For satellite-only plots: compare SMAP vs nearest sensor plot's
  moisture; if deviation > 20% -> alert.

Tests: synthetic divergence triggers alert.
```

#### Prompt 12.2 — Backup + restore drill

```
Cursor task: app/jobs/pg_dump_backup.py + scripts/restore_drill.py.

pg_dump_backup.py: Sunday 03:00 IST.
- subprocess.run(["pg_dump","--format=custom","--no-owner","--no-acl",
                  "-d","agro","-f","/tmp/dump.bin"])
- gzip /tmp/dump.bin
- Upload to Backblaze B2 via b2sdk:
  backups/agro-{YYYY-MM-DD}.dump.gz
- Server-side encrypt with B2 SSE-B2.
- Retention rule: last 12 weekly + last-of-quarter forever.

scripts/restore_drill.py:
- --backup-id (date or 'latest')
- docker run a fresh postgres
- download backup from B2
- pg_restore into the container
- smoke test query (count farmers, plots, ai_suggestions)
- report time-to-restore

ops/runbooks/restore_drill.md — quarterly procedure documented.

Tests: pg_dump runs locally; restore_drill against small local backup.
```

#### Prompt 12.3 — Ops console + admin endpoints

```
Cursor task: agro_dashboard/pages/6_Ops_Console.py + app/infra/http/admin.py
extensions.

Ops console (admin-only):
- System health summary (ingest rates last hour, alert rates, DLQ depth,
  broker pending)
- DLQ replay button per row
- Force OTA check per device
- Recompute crop stages now
- Reindex rules
- SQL inspector with hardcoded allowlist (e.g., 'farms count by tenant',
  'plots by data_tier', 'subscriptions by state' — but never accept
  arbitrary SQL).

Admin endpoints:
- POST /api/v1/admin/cron/run/{job_name}
- POST /api/v1/admin/dlq/{id}/replay
- POST /api/v1/admin/devices/{id}/cmd
- POST /api/v1/admin/rules/reindex
- POST /api/v1/admin/crop_stages/recompute

Each admin endpoint writes audit_log.

Tests: role gating; non-admin sees 403; ops actions log audit rows.
```

---

## PHASE 13 (post-pilot) — MSG91 SMS adapter + DLT registration (2 days)

**Goal:** SMS as a fallback channel for non-smartphone farmers.

**Pre-requisites:**
- DLT registration with TRAI (5–7 days lead time; see runbook below)
- Transactional templates approved

### Cursor prompts for Phase 13

#### Prompt 13.1 — MSG91 SMS adapter

```
Cursor task: app/infra/notify/sms_msg91.py.

class SmsMsg91Adapter implements both SmsClient AND OtpDeliveryClient.

Uses httpx against MSG91 Flow API:

POST https://control.msg91.com/api/v5/flow/
Headers: authkey: {MSG91_AUTH_KEY}
Body:
{
  "template_id": "<DLT-registered template id>",
  "short_url": "0",
  "recipients": [
    {
      "mobiles": phone_e164_without_plus,
      "<template_var_1>": code_or_message_param,
      ...
    }
  ]
}

Two methods:
- async def send(phone, payload) -> DispatchResult — alert template
- async def send_otp(phone, code) -> str — OTP template

Each picks the right template_id from settings:
- MSG91_TEMPLATE_OTP_DLT_ID
- MSG91_TEMPLATE_ALERT_DLT_ID

Error handling per MSG91 docs:
- success in response -> message_id captured
- 200 with error -> PermanentDispatchError if DLT template rejected,
  TransientError on rate-limit

Register in app/main.py REGISTERED_CHANNELS to add 'sms'.

In settings: OTP_TRANSPORT can now be 'sms' OR 'whatsapp'. Pilot stays
'whatsapp'; commercial non-WhatsApp farmers use 'sms'.

Tests with respx: both methods + error mapping.
```

#### Prompt 13.2 — DLT registration runbook

```
Cursor task: ops/runbooks/dlt_registration.md.

Document step-by-step:
1) Pick DLT provider (Vilpower/Vodafone, Smartping, Jio Platforms).
2) Submit entity details — PAN, GST, business address.
3) Submit header (sender ID) — 6-char alphanumeric.
4) Submit transactional template — must match exact wording of messages
   we send (variables marked as {#var#}).
5) Wait 24-48 h per template for approval.
6) Once approved, copy DLT template ID into MSG91 dashboard; MSG91
   verifies match and issues MSG91 internal template_id.
7) Store both DLT_TEMPLATE_ID and MSG91_TEMPLATE_ID in env.
8) Test in MSG91 sandbox before flipping live.

Estimated total: 7-10 days end-to-end.

Common rejections:
- Template doesn't match exact wording -> resubmit
- Sender ID conflicts -> pick another
- Entity not GST-registered -> register for GST first
```

---

## PHASE 14 (post-pilot) — Razorpay subscriptions + UPI AutoPay (4–5 days)

**Goal:** real billing for commercial customers.

**Pre-requisites:**
- Razorpay KYC done (PAN, GST, business bank, registered entity)
- Plans created in Razorpay dashboard (one per SKU per cycle)
- Webhook URL registered: `https://api.agroguardian.in/api/v1/webhooks/razorpay`

### Cursor prompts for Phase 14

#### Prompt 14.1 — Razorpay client + UPI AutoPay

```
Cursor task: app/infra/payments/{razorpay_client,upi_autopay}.py +
app/application/ports/payment_client.py +
app/application/{start_subscription,handle_payment_event}.py.

ports/payment_client.py:
class PaymentClient(Protocol):
    async def start_subscription(self, plan_id: str, customer: Customer,
                                  notes: dict) -> SubscriptionStartResult: ...
    async def cancel_subscription(self, sub_id: str,
                                   at_cycle_end: bool) -> None: ...
    async def fetch_subscription(self, sub_id: str) -> SubscriptionState: ...
    def verify_webhook(self, raw_body: bytes,
                       signature: str) -> WebhookEvent: ...

infra/payments/razorpay_client.py:
class RazorpayClient implements PaymentClient.
Uses official razorpay Python SDK.

Methods:
- start_subscription: creates Razorpay Subscription with method='upi'
  (UPI AutoPay primary); returns short_url for mandate authorization.
- cancel_subscription: cancel_at_cycle_end param.
- fetch_subscription: current status.
- verify_webhook: HMAC-SHA256 with RAZORPAY_WEBHOOK_SECRET; rejects on
  mismatch; parses event payload.

application/start_subscription.py:
async def execute(deps, farmer_id, sku) -> dict:
    farmer = await deps.farmer_repo.find(farmer_id)
    cust_id = await deps.payment_client.ensure_customer(farmer)
    sub = await deps.payment_client.start_subscription(
        plan_id=PLAN_IDS[sku], customer=cust_id,
        notes={'farmer_id': farmer_id})
    await deps.subscription_repo.create(
        tenant_id=farmer.tenant_id, sku=sku,
        razorpay_sub_id=sub.sub_id, state=TRIAL)
    return {'short_url': sub.short_url, 'sub_id': sub.sub_id}

application/handle_payment_event.py:
async def execute(deps, event):
    # Idempotent on event.id (processed_webhook_events dedup).
    sub = await deps.subscription_repo.find_by_razorpay_id(
        event.subscription_id)
    new_state = compute_next_state(sub.state, event.kind)
    if new_state != sub.state:
        await deps.subscription_repo.update_state(sub.id, new_state)
        await deps.event_bus.publish("subscription.state_changed",
            {"sub_id": str(sub.id), "old": sub.state.value,
             "new": new_state.value})
        await run_side_effects(sub, new_state, deps)

Side effects on state change (use existing dispatcher):
- ACTIVE -> GRACE: WhatsApp template 'first_payment_failed_v1'
- GRACE -> SUSPENDED: pause advisory generation; flag tenant
- SUSPENDED -> ACTIVE: re-enable; 'welcome_back_v1'
- ACTIVE -> CANCELLED: 'subscription_ended_v1'

In check_quota.py: swap the pilot_internal special-case for real
subscription-state check — but ONLY when tenant.tier != 'pilot_internal'.
This way the pilot tenant continues to work without any subscription row.

Tests: stubbed SDK; every event type per state; assert transitions +
side effects.

Coding standards: webhook idempotent on event id. Never log full
Razorpay payloads.
```

#### Prompt 14.2 — Webhook endpoint + idempotency

```
Cursor task: app/infra/http/webhooks_razorpay.py.

POST /api/v1/webhooks/razorpay:
- Read raw body before parsing.
- Verify signature using X-Razorpay-Signature.
- Parse event; check processed_webhook_events for event.id; skip if
  exists.
- INSERT processed_webhook_events with event.id, kind, received_at.
- Call handle_payment_event.execute(event).
- Return 200 quickly (Razorpay retries on 5xx for 24 h).

Tests: signature verification with real HMAC sample; double-delivery
of same event id is no-op.
```

---

# PART 7 — Testing Strategy

## 7.1 Layers + coverage targets

| Layer | Scope | Tool | Target |
|---|---|---|---|
| Unit (domain) | Pure functions — derived metrics, validation gates, confidence, packet packing | pytest | 95% |
| Unit (application) | Use cases with stubbed ports | pytest + asyncmock | 85% |
| Integration | DB + MQTT testcontainers | pytest + testcontainers | All write paths |
| API contract | FastAPI TestClient with sample JWTs | pytest + httpx | Every endpoint, every status |
| Property-based | Confidence monotonicity, packet round-trip, derived metric bounds | Hypothesis | All packing functions |
| Frontend unit | Components | RN Testing Library | 70% |
| E2E (cloud) | Streamlit + fake Main Node | Playwright | 5 critical flows |
| E2E (app) | Phase 2 — Detox | Detox | Login + advisory + chat |
| Hardware-in-loop | Desk Sub + Main Node | Manual script | Telemetry round-trip + OTA |

## 7.2 Critical user flows to E2E test

1. Farmer registers via **WhatsApp OTP** → 4 plots visible → today's advisory in Marathi → "I did this" → action persisted.
2. Fake Main Node publishes 30 messages → 30 rows land → hourly view refreshes → home shows latest.
3. Sensor stuck 3 cycles → `sensor_fault` fires → FCM received → farmer dismisses → resolved.
4. Crop-change wizard → new crop_seasons row → next day T1 targets new crop.
5. Agronomist sees queued suggestion → edits Marathi → approves → autosend with reviewed_by.
6. OTA upload Main Node v1.0.1 → canary 10% → success → promote → all updated.
7. 4G outage 1h → Main Node buffers ~12 messages → reconnect → all messages drain with correct timestamps.
8. Boundary walk: 50 pings → smoothed polygon → satellite ingest produces NDVI within 24h.
9. Farmer types phone → receives WhatsApp OTP → enters code → app reaches Home tab with 4 plots visible.
10. Bad code 5 times → account locked 30 min → Marathi error message.

## 7.3 CI gates

- `ruff check` must pass
- `mypy app/` must pass
- `pytest --cov-fail-under=80` must pass
- `alembic upgrade head` then `downgrade base` then `upgrade head` round-trip clean
- `docker buildx build --platform linux/amd64,linux/arm64` must produce runnable images
- TypeScript types generation must produce zero diff against committed `types.gen.ts`

---

# PART 8 — Security Checklist

| # | Control | Phase |
|---|---|---|
| 1 | TLS on every wire — MQTT 8883, HTTPS, Cloudflare-terminated edges | 0 |
| 2 | Per-device MQTT username/password, bcrypt-hashed, plain shown ONLY at provisioning | 1 / 8 |
| 3 | RLS via `current_setting` on every tenant-scoped table from day 1 | 1 |
| 4 | service_role BYPASSRLS only for ingest/cron; never exposed to clients | 1 |
| 5 | All secrets in env / Doppler, never in repo, `.env` gitignored | 0 |
| 6 | Phone numbers pgcrypto-encrypted; phone_hash for indexed lookup | 1 |
| 7 | Aadhaar stays NULL in pilot; subsidy SKU adds it with consent | doc |
| 8 | Audit log trigger on `farmers`, `farms`, `plots`, `device_registry`, `subscriptions_billing`, `crop_seasons`, `users`, `tenants`, `calibration_history` | 1 |
| 9 | Cloudflare WAF + rate limits at edge | 0 |
| 10 | FastAPI CORS strict allowlist | 0 |
| 11 | slowapi rate limits on `/auth/otp/*`, `/chat`, `/auth/login` | 3 |
| 12 | Anthropic API key never logged; redacted in Sentry | 5 |
| 13 | Farmer photos: private R2 bucket; signed URL with 5-min TTL | 9 |
| 14 | OTA binaries ed25519-signed; public key baked into firmware | 8 |
| 15 | Sensitive admin endpoints log actor + before/after to `audit_log` | 3 |
| 16 | UptimeRobot + Sentry on; Telegram bot for critical | 12 |
| 17 | Weekly B2 backup; quarterly restore drill | 12 |
| 18 | Log redaction: never log phone, JWT, API keys, OTP codes | all |
| 19 | Tailscale-only Prometheus + Grafana exposure | 0 |
| 20 | Cloudflare Tunnel — no inbound ports open on VPS firewall except 80/443/8883 | 0 |
| 21 | `fail2ban` for SSH brute-force on VPS | 0 |
| 22 | Argon2id for user passwords; bcrypt for OTP codes; blake2b for refresh hashes | 1 / 3 |
| 23 | JWT short-lived (15 min) with refresh rotation | 3 |
| 24 | Single-use refresh token rotation enforced; revoked on logout | 3 |
| 25 | WhatsApp `authentication` template is the ONLY OTP transport in pilot. SMS adapter not registered. | 3 / 7 |
| 26 | OTP codes hashed (bcrypt) at rest; never logged; redacted in Sentry breadcrumbs | 3 |
| 27 | OTP request rate-limited 3/10min/phone; verify rate-limited 5/10min/phone with 30-min lockout after 5 failures | 3 |
| 28 | WhatsApp template content reviewed by agronomist team before approval; revisions go through Meta re-approval | 7 |
| 29 | OWASP top-10 checklist reviewed before commercial launch | 12+ |
| 30 | DLT-registered SMS templates before MSG91 adapter goes live | 13 |
| 31 | Razorpay webhook signature verify + idempotency on event id | 14 |

---

# PART 9 — Common Failure Points

1. **Cursor invents columns** — paste Part 2 into every DB chat. Otherwise it invents `device_status_id` or similar.
2. **Cursor regenerates pydantic v1 syntax** — `.cursorrules` blocks it. Reject outputs with `class Config:` or `@validator(`.
3. **Mosquitto silently rejects ACL** — always test with `mosquitto_pub -d`. The verbose output tells you if username/password and ACL match.
4. **RLS bites the ingest worker** — service_role MUST BYPASSRLS.
5. **APScheduler fires twice on uvicorn reload** — start scheduler only in lifespan.
6. **Anthropic tool_use loop never terminates** — always set `max_iter`.
7. **ChromaDB index goes stale** — pin embedding model version in metadata; reindex on mismatch.
8. **Sentinel-2 returns nothing for 3 weeks during monsoon** — degrade gracefully; lean on SMAP.
9. **FCM tokens go stale** — null them on `not-registered` error immediately.
10. **WhatsApp 24-hour window** — template vs text branching is essential.
11. **Time zone bugs** — use `timezone='Asia/Kolkata'` in cron specs; never subtract 5h30m manually.
12. **Sub Node packet NPK overflow** — clamp before packing.
13. **OTA bricks the Main Node** — always test rollback before first canary.
14. **sentence-transformers cold start** — pre-bake model into Docker image.
15. **Streamlit reruns on every interaction** — cache aggressively with `@st.cache_data(ttl=...)`.
16. **Postgres partition overflow if device clock drifts** — validate `recorded_at` server-side.
17. **`REFRESH CONCURRENTLY` requires unique index** — always create it in the same migration.
18. **Cursor duplicates imports** — say "modify existing imports" explicitly.
19. **Marathi rendering on cheap Android** — bundle Noto Sans Devanagari with Expo.
20. **AWS Lightsail $20 plan is x86_64; future migration to Graviton (ARM) needs multi-arch images** — `docker buildx build --platform linux/amd64,linux/arm64` in CI is non-negotiable so the upgrade path stays open.
21. **Caddy + Cloudflare proxy can double-issue Let's Encrypt** — set Cloudflare SSL to "Full (strict)" and let Caddy issue.
22. **Coolify auto-deploy races with long-running migrations** — make migrations forward-compatible (add-then-deprecate; never drop in same deploy).
23. **Postgres NOTIFY payload limit is 8000 bytes** — emit only IDs in events; consumers re-fetch.
24. **Self-hosted Postgres on tiny disks** — monitor disk free; partition pruning is your only friend.
25. **Tailscale ACL misconfiguration locks you out** — test with second device first.
26. **Backblaze B2 has no India region** — accept egress latency at restore time.
27. **Copernicus Data Space rate limits silently truncate evalscript responses** — wrap in retry+backoff; cap concurrent requests.
28. **NASA Earthdata token expires every 60 days** — refresh script + monitoring required.
29. **WhatsApp `authentication` template rejected on first submission** — common reasons: language code mismatch (use `mr` not `mr_IN`), too generic "verification code" wording, missing URL button parameter. Use Meta's example template as starting point.
30. **WhatsApp 1,000 free conversations scoped per business account** — not per app.
31. **Anthropic Sonnet's tool_use can return a tool call even when prompt says no** — defensive parsing for both `text` and `tool_use` stop reasons.
32. **Cost-cache invalidation** — if you update rules mid-day, cached suggestions go stale. Always wipe cost cache on `reindex_rules`.
33. **`pilot_internal` tier is special** — add it to every CHECK constraint, enum, TIER_LIMITS map. `domain/tier.py` is source of truth.
34. **Multi-arch Postgres image mismatch** — verify the postgis tag supports ARM before pinning. `docker manifest inspect` confirms.
35. **Cursor agents skip writing `downgrade()` in Alembic** — explicitly require it in `.cursorrules`.
36. **Lightsail's instance Firewall blocks ports even when UFW allows them** — Lightsail has a *cloud-level* firewall on top of the VPS-level UFW. Both must allow the port. Symptom: `curl` from outside hangs forever, `nc -zv` from another machine shows "connection refused". Fix: Lightsail Console → your instance → Networking tab → IPv4 Firewall → add rules for TCP 80, 443, 8883 from `0.0.0.0/0`. This is the #1 AWS gotcha.
37. **Lightsail static IP charges $0.005/h if detached** — if you delete the instance without first detaching/deleting the static IP, AWS keeps charging you ~$3.60/month for an unused IP. Always delete the static IP explicitly when retiring the instance (Lightsail Console → Networking → Static IPs → your IP → Delete).
38. **Lightsail bandwidth overage** — the $20 plan includes 3 TB egress/month. Beyond that, $0.09/GB. At pilot scale you'll use < 50 GB/month so it's a non-issue, but if you accidentally `curl`-loop something on the VPS, costs spike fast. The Billing Alert at $30 catches this within hours.
39. **Lightsail snapshot retention** — automatic daily snapshots retain 7 days by default. If you want longer history, manually create monthly snapshots (Console → Snapshots → Create snapshot manually). Each manual snapshot is the same $0.05/GB/mo.
40. **AWS-region-specific quirks for Mumbai (`ap-south-1`)** — Lightsail Mumbai supports all the standard features but doesn't yet have the "Container Service" feature (only EC2 has containers in this region). We don't use Container Service anyway; we use Docker Compose on the instance. Just don't reach for the "Containers" tab in Lightsail Console — it'll redirect or 404.
41. **AWS Billing surprises from un-deleted resources** — when experimenting, you may spin up Lightsail load balancers ($18/mo each), block-storage disks (extra $0.10/GB/mo per attached disk), database services (~$15-200/mo). After any experiment, go to Lightsail → resource type → confirm only your one $20 instance + one static IP + snapshot policy exist. The $30/mo Billing Alert is your safety net.
42. **`sslip.io` Let's Encrypt rate limit** — only ~50 cert issuances per registered domain per week. Caddy reuses certs across restarts, so this only matters if you `docker volume rm` the Caddy data volume during testing. Fix: don't wipe the Caddy volume; if you must, wait a week or use `acme.zerossl.com` as the issuer (Caddyfile-configurable).
43. **Cloudflare proxy + Let's Encrypt HTTP-01 challenge fight each other** — if you proxy the Caddy domain through Cloudflare (orange-cloud), Cloudflare intercepts port 80 and ACME HTTP-01 fails. Fix during prototype: keep DNS records gray-cloud (Proxy: OFF). Switch to orange-cloud only after Caddy has issued and stored the cert, and configure Caddy to renew via DNS-01 challenge (Cloudflare API token).
44. **Cursor invents AWS-specific code if you mention "AWS"** — Cursor's training data associates "AWS" with `boto3` for everything. Rule 25 in `.cursorrules` (Part 10.2) prevents this. If you see `import boto3` against `s3.amazonaws.com`, or any `import` of `cognito`, `lambda_handler`, `dynamodb`, `sns`, `sqs`, `ses` — reject the diff. The only legitimate `boto3` use is against `R2_ENDPOINT_URL` or `B2_ENDPOINT_URL` for S3-compat object storage.
45. **AWS Lightsail Mumbai region uses x86_64, not ARM** — our multi-arch Docker images (Phase 0 Prompt 0.1's `docker buildx build --platform linux/amd64,linux/arm64`) work on both; this is precisely why we built them multi-arch. If you ever migrate to ARM (Graviton EC2 t4g.medium ~$24/mo with $200 12-month credit), the images already work.

---

# PART 10 — Cursor Workflow

## 10.1 Multi-chat strategy

| Cursor chat | Paste these sections of the final roadmap |
|---|---|
| Backend / domain / application / API | 0, 0.5 (portability charter), 1, 2, 3, 5, current Phase prompts |
| Frontend (RN app) | 0.4, 4, 9 prompts, i18n/mr.json |
| Streamlit dashboard | 0.4, 4.2, Phase 10 prompts |
| Database / migrations | 0.4, 2, Phase 1 prompts |
| AI / RAG / LLM | 0.4, Phase 5 prompts |
| Satellite + forecast | 0.4, 1.6 (storage), Phase 6 prompts |
| Notifications | 0.4, 1.3 (events), Phase 7 prompts |
| Firmware Sub Node | 0 (hardware notes in technical ref), Phase 8.1 prompt |
| Firmware Main Node | 0, Phase 8.2 prompt |
| OTA service | 0, 1.6, Phase 8.3 prompt |
| Quota / future-billing | 0.4, Phase 11 prompt |
| DevOps / CI / deploy | 0.3, 0.4, **0.5 (portability)**, Phase 12.2 runbook |
| Fast-path prototype | 0.6, current Phase prompts only |
| Testing / QA | Parts 7, 9 |
| Post-pilot SMS | Phase 13 prompts |
| Post-pilot Razorpay | Phase 14 prompts |

## 10.2 `.cursorrules` (paste verbatim)

```
You are working on AgroGuardian V2 — a precision agriculture platform built
with FastAPI + self-hosted Postgres 15 + React Native + Streamlit + Claude
(Sonnet 4.6 + Haiku 4.5). The architecture is hexagonal (ports-and-adapters);
domain logic has zero framework imports.

Strict rules:
1. Python 3.12. Async SQLAlchemy 2.0 only (mapped_column, Mapped[]).
   pydantic v2 only (no class Config:, no @validator).
2. All timestamps are TIMESTAMPTZ in DB and timezone-aware datetime in Python.
3. Money fields are NUMERIC(12,2) and Decimal in Python. Never float.
4. Never silently swallow exceptions. Log with structlog and re-raise or
   convert to a domain exception.
5. Every API endpoint has an OpenAPI summary, a response_model, and at
   least one test covering 200 + auth.
6. Never invent column names. The 21-table schema + the 14 v3 additional
   tables in Part 2.2 of the roadmap are authoritative.
7. Multi-tenancy: every tenant-scoped table has tenant_id UUID NOT NULL
   with RLS enabled.
8. Marathi strings live in i18n files (mr.json) or rule JSON files.
   Never hard-coded in Python or JSX.
9. No print(). Use structlog.
10. No TODOs in production code. If something is incomplete, raise
    NotImplementedError with a clear message.
11. Maintain consistency with the AgroGuardian final roadmap that was
    pasted at the top of the chat.
12. Domain layer (app/domain/) imports ONLY stdlib + numpy + shapely +
    Decimal/datetime. NEVER fastapi, sqlalchemy, anthropic, etc.
13. Application layer (app/application/) imports domain + ports
    (Protocols). NEVER infra/.
14. Infra layer implements ports. Use cases call ports, not concrete classes.
15. Explain the code you generate in 5-15 lines after the diff.
16. When asked to modify an existing file, MODIFY it — don't rewrite from
    scratch and don't duplicate imports.
17. When in doubt, ask before generating large outputs.
18. Migrations are always reversible. Every Alembic file has a downgrade.
19. Tests use fixtures, not real network calls. External APIs (Anthropic,
    Meta WA, FCM, NASA, Copernicus) are stubbed via respx or mocks.
20. ARM64 + amd64 Docker images required. CI checks with
    docker buildx build --platform linux/amd64,linux/arm64.
21. LLM model selection is via ModelRole (PRIMARY=Sonnet, TRIAGE=Haiku),
    not by model name. Never hardcode 'claude-sonnet-4-6' in use cases.
22. Razorpay SDK is NOT a pilot dependency. subscriptions_billing exists
    but is empty. Pilot tenant uses tier='pilot_internal'.
23. SMS adapter exists as a Protocol only. Pilot uses WhatsApp for both
    advisory and OTP.
24. OTP codes are NEVER logged, even in error paths. Last-4 of phone only
    in any log.
25. Never reference AWS-specific managed services in code: no Cognito, no
    SES, no Lambda, no SNS/SQS, no RDS, no CloudWatch, no Secrets Manager,
    no DynamoDB, no Route 53, no ALB/NLB, no IAM Identity Center, no Step
    Functions, no EventBridge. The provider-neutral equivalent is already
    in the stack — check Part 0.5 Rule 2 of the roadmap.
26. boto3 / aioboto3 are ALLOWED but ONLY against Cloudflare R2 and
    Backblaze B2 (S3-compatible endpoints). Always configure via
    R2_ENDPOINT_URL / B2_ENDPOINT_URL env vars; never hardcode
    `s3.amazonaws.com`. Backups also use b2sdk natively against B2.
27. Caddy uses sslip.io hostnames during the prototype phase. Generate
    the IP-substituted Caddyfile via the `make caddyfile-prod` target,
    never by hand. When a real domain is purchased later, the same
    target accepts a DOMAIN argument and regenerates.
28. Code quality is non-negotiable even on the Fast Path (Part 0.6).
    The fast path reduces scope, not standards. Every file gets tests,
    type annotations, audit log triggers, and reversible migrations.
```

## 10.3 Verification loop after every Cursor task

1. **Read the diff** before applying. Cursor sometimes touches files you didn't ask about.
2. **Run the test** for that change. If no test exists, ask Cursor to write one.
3. **Run lint + types**: `ruff check && mypy app/`.
4. **Manually exercise** the endpoint or script.
5. **Diff against the previous commit** — verify no unrelated code was touched.
6. **If the change crosses a phase boundary, refactor immediately** — half-finished modules accrue debt fast.

## 10.4 When to refactor

- Before Phase 5 (AI) — processing module gets dense
- Before Phase 9 (frontend) — generate OpenAPI types once; never hand-edit
- After Phase 7 (notifications) — dispatcher gets gnarly; refactor after first end-to-end alert
- After Aurangabad install — you'll learn things (LoRa drops at noon, NDVI stubble confusion); bake them in as code
- **Month 3 LLM benchmark** — if Gemini Pro wins, adapter swap is one file

## 10.5 When to extract a service from the monolith

- Pull **ingest worker** out when MQTT > 10k msg/min sustained, or ingest p99 drags API p99
- Pull **AI worker** out when LLM calls become a meaningful compute share

Both are 50+ farm problems. Resist earlier — the hexagon makes future extraction mechanical.

---

# PART 11 — Final CTO Recommendations

## 11.1 The 10 things to do this week (v1.2 — AWS Lightsail)

1. **Create AWS account** (if you don't have one) and enable **Billing Alerts at $30/mo** before anything else. Console → Billing → Budgets → email alert at $30. This is your safety net.
2. **Provision Lightsail Mumbai $20 instance** with Ubuntu 22.04 + a static IP. Enable automatic snapshots. Note the static IP on a sticky note.
3. **Open Lightsail Firewall** for TCP 80, 443, 8883 from `0.0.0.0/0` (Lightsail Console → instance → Networking → IPv4 Firewall). This is the #1 AWS gotcha — UFW alone is not enough.
4. **Compute `sslip.io` hostnames** from the static IP. Verify with `dig +short api-<ip-dashes>.sslip.io` returns your IP.
5. **Create Anthropic account**; add $20 credit.
6. **Register at developers.facebook.com** → WhatsApp Cloud API → add farmer + founders as test recipients. **Submit BOTH the OTP `authentication` template and the advisory template in the same session** (24–48 h approval).
7. **Register at urs.earthdata.nasa.gov + dataspace.copernicus.eu** (instant).
8. Provision Cloudflare R2 + Backblaze B2 + Doppler + Tailscale + Sentry + Better Stack + UptimeRobot — all free tiers, ~30 min total.
9. Set up GitHub repo + Cursor on dev machine; paste `.cursorrules` from Part 10.2 (with Rules 25–28 included).
10. Run Phase 0 prompts; ship the `/health` endpoint to `https://api-<ip>.sslip.io/api/v1/health` by end of week.

**Then immediately:** open the Part 12.2 runbook and check off every validation step before moving to Phase 1.

**Start in parallel but not blocking pilot:** Razorpay KYC + sole-prop registration. Saves 5–7 days when Phase 14 starts; doesn't block pilot.

**Bonus:** read the AgroGuardian technical reference end-to-end one more time — you'll spot something the roadmap missed.

## 11.2 What NOT to do, even if Cursor suggests it

- Do not microservice-ify the pilot.
- Do not switch ChromaDB to Pinecone "for scale" before scale.
- Do not build a custom rule-editor admin UI in pilot — JSON-on-disk + git is correct.
- Do not buy paid Mosquitto before HiveMQ Cloud Free saturates.
- Do not fine-tune any model in pilot — RAG-first is right.
- Do not implement Sentinel-1 SAR for monsoon — Phase 2.
- Do not enable Aadhaar in pilot — compliance overhead with zero product value.
- Do not let agronomists edit rule JSON files via admin UI — bad rules are catastrophic; PR flow is worth the friction.
- Do not skip audit log on master tables — your only forensic trail at 3 AM.
- Do not over-engineer partition rotation — declarative + monthly cron is enough.
- Do not implement an SMS adapter in pilot — `SmsClient` Protocol is enough.
- Do not call Anthropic models by name in use cases — always go through ModelRole.
- Do not populate `subscriptions_billing` in pilot — leave it empty.
- Do not hard-code 'pilot_internal' in business logic; it's a tier enum value with all quotas bypassed.
- Do not reach for AWS-specific managed services (Cognito, S3, RDS, Lambda, SES, SNS, SQS, CloudWatch, Secrets Manager, DynamoDB, Route 53, ALB/NLB, IAM Identity Center). The provider-neutral equivalent is already in the stack — Part 0.5 Rule 2. The portability charter is what lets you sleep at night about AWS pricing changes or quota issues.
- Do not import `boto3` against `s3.amazonaws.com`. The only legitimate `boto3` use is S3-compat against `R2_ENDPOINT_URL` (Cloudflare R2) or `B2_ENDPOINT_URL` (Backblaze B2) — both configured via env, never hardcoded.
- Do not put `sslip.io` literals in code — they live only in `deploy/caddy/Caddyfile` and in the Expo env config. Code refers to URLs via `EXPO_PUBLIC_API_URL` and `API_BASE_URL` env vars. When the brand domain lands, no code changes.
- Do not skip the Lightsail Firewall configuration. UFW is *not* sufficient on AWS Lightsail; both firewalls must allow each port. Symptom of forgetting: connection refused with no helpful error.
- Do not leave the Lightsail static IP detached after deleting the instance. AWS will keep charging $0.005/h for unused static IPs (~$3.60/mo of phantom spend).
- Do not skip Billing Alerts. $30/mo is the right initial threshold; any spike means something has gone wrong with a resource you forgot.
- Do not spin up Lightsail "Container Services" or "Database Services" or "Load Balancers" without explicit cost approval. Each adds $15–80/mo. The pilot needs none of them.
- Do not run the Fast Path (Part 0.6) without writing tests for each phase you ship. The fast path reduces scope, not standards.

## 11.3 Single thing most likely to kill the pilot

**Battery anxiety on the Sub Nodes.** If cadence-mode logic miscalibrates and the ER18505 cells drain in 3 months instead of 18, you'll have a farmer with broken sensors during sugarcane grand-growth. Three defenses:

1. Test Conservation/Storm transitions on a desk Sub Node before installing.
2. Fire low-battery alert 90 days before predicted exhaustion, not 7.
3. Keep 2 field-replacement battery packs in your bag at every farm visit.

## 11.4 Single thing most likely to make the pilot succeed

**Reading the 7 AM Marathi advisory yourself, every morning, weeks 1–4.** The technical reference is rigorous, the architecture is sound, but the product is what the farmer reads on their phone. If a single message is too long, too jargon-heavy, or too vague to act on, you will not catch it from a dashboard. You'll catch it by reading what your AI sent your farmer this morning.

The whole stack — LoRa packets, rule engine, satellite indices, confidence gates, ChromaDB, Claude — exists to produce one good 4-sentence Marathi message at 7 AM. Treat it that way and you'll ship a product that works.

---

# PART 12 — Cloud Infrastructure Runbook + Scalability Ladder

## 12.1 Single-VPS topology (pilot)

```
Provider:    AWS Lightsail (Mumbai, ap-south-1, AZ-A)
Instance:    $20/month plan — 2 vCPU / 4 GB RAM / 80 GB SSD
OS:          Ubuntu 22.04 LTS (x86_64)
Network:     1 Static IPv4 (free while attached) + 1 dynamic IPv6
Bandwidth:   3 TB egress/month included; $0.09/GB beyond
Snapshots:   Automatic daily snapshots @ $0.05/GB/mo ≈ $4/mo for 80 GB
```

Upgrade path (when scale forces):
```
Lightsail $40/mo: 4 vCPU / 16 GB / 160 GB        (~100 farms)
Lightsail $80/mo: 8 vCPU / 32 GB / 320 GB        (~250 farms)
AWS EC2 + RDS:   t3.large + db.t3.medium         (~500 farms; ~$120/mo)
AWS ECS Fargate: managed services + Aurora       (5000+ farms; ~$800/mo)
```

Software (Docker Compose, identical regardless of provider):
```yaml
services:
  caddy:           # 80/443/8883 TLS + auto Let's Encrypt
  postgres:        # 5432 internal only
  mosquitto:       # 8883 TLS via Caddy
  app:             # FastAPI :8000 internal
  chroma:          # :8000 internal
  prometheus:      # :9090 Tailscale-only
  grafana:         # :3000 Tailscale-only
```

Latency budget Aurangabad → Lightsail Mumbai ≈ 30 ms p50 / 60 ms p99 — same as Oracle would have been; not a factor in product UX.

## 12.2 Setup runbook — AWS Lightsail Mumbai (one-time, ~90 min)

This runbook assumes you've already provisioned a Lightsail $20/month instance (2 vCPU / 4 GB / 80 GB SSD) in `ap-south-1a` and attached a static IP.

**AWS-specific notes before starting:**
- **No idle-reclamation policy.** Unlike Oracle Always Free, Lightsail charges you a flat $20/month and the instance stays up indefinitely. No "must be active" requirement.
- **Two firewalls again.** Lightsail has its own firewall (configured in the Networking tab) on top of UFW. Both must allow each port. This is the #1 gotcha — exact same shape as Oracle's OCI Security List was.
- **Billing alerts.** Set up before any other config: Console → Billing → Budgets → email alert at $30/mo. This catches any surprise spend within hours of it happening.

```bash
# 0. (One-time, on your laptop) AWS Lightsail accepted your SSH public key
#    during provisioning. You can also use the default Lightsail key, which
#    is downloadable from Console → Account → SSH keys.
#    Save it to ~/.ssh/agro_lightsail.pem and chmod 600.

# 1. SSH into the VPS using the static IP you attached
ssh -i ~/.ssh/agro_lightsail.pem ubuntu@<static-ip>
# (Replace ubuntu@ with the username shown in Lightsail's "Connect using SSH"
# panel — usually "ubuntu" for the Ubuntu 22.04 blueprint.)

# 2. Set hostname so logs are sensible
sudo hostnamectl set-hostname agro-prod-01

# 3. Update + install Docker (works identically on AWS / DO / Hetzner / any Linux)
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl ca-certificates gnupg lsb-release jq
curl -fsSL https://get.docker.com | sudo bash
sudo usermod -aG docker $USER
newgrp docker

# 4. Verify x86_64 architecture (Lightsail $20 plan is x86_64; multi-arch
#    Docker images we built in CI cover both amd64 and arm64 so this Just Works)
uname -m   # should print: x86_64

# 5. Tailscale (private mesh for admin SSH + metrics + Grafana)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --advertise-tags=tag:vps
# Auth via the URL printed; use your existing Tailscale account.

# 6. fail2ban for SSH brute-force protection
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban

# 7. UFW firewall — only the ports we actually need
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow 80     # Caddy ACME HTTP-01 challenge
sudo ufw allow 443    # API + Streamlit
sudo ufw allow 8883   # MQTT TLS
sudo ufw enable

# 7a. ALSO open the same ports in Lightsail's instance Firewall
#     (Lightsail has a CLOUD-LEVEL firewall on top of UFW — both must allow.
#     This is the #1 AWS gotcha — UFW open + Lightsail firewall closed
#     = connection refused with no helpful error.)
#
#     Lightsail Console → your instance → Networking tab → IPv4 Firewall:
#     Add rules:
#       SSH    | TCP | 22   | restricted to your IP recommended (or 0.0.0.0/0)
#       HTTP   | TCP | 80   | 0.0.0.0/0
#       HTTPS  | TCP | 443  | 0.0.0.0/0
#       Custom | TCP | 8883 | 0.0.0.0/0   <-- MQTT TLS
#
#     (SSH should ideally be Tailscale-only once Tailscale is configured;
#     remove the public SSH rule from Lightsail Firewall after verifying
#     Tailscale works.)

# 8. Install Coolify (self-hosted PaaS, deploys Docker Compose stacks)
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash
# Visit http://<static-ip>:8000 → create admin account.
# (After Tailscale works, restrict Coolify access to Tailscale via Caddy.)

# 9. Compute your sslip.io hostnames (no domain purchase needed)
#    Lightsail static IP example: 13.235.50.100
#    -> api hostname:        api-13-235-50-100.sslip.io
#    -> mqtt hostname:       mqtt-13-235-50-100.sslip.io
#    -> dashboard hostname:  dashboard-13-235-50-100.sslip.io
#    Verify resolution before continuing:
dig +short api-13-235-50-100.sslip.io
# expected output: 13.235.50.100

# 10. In Coolify: connect GitHub PAT (read access to private repo);
#     create Docker Compose resource pointing at docker-compose.prod.yml;
#     set environment variables (every key from .env.example);
#     run `make caddyfile-prod IP=13.235.50.100` LOCALLY to
#     produce the IP-substituted Caddyfile and commit + push;
#     trigger deploy from Coolify.

# 11. Verify Caddy issued Let's Encrypt (takes ~30 s on first request)
curl -v https://api-13-235-50-100.sslip.io/api/v1/health
# Expected: HTTP/2 200, JSON {"status":"ok","version":"0.0.1","commit":"<sha>"}

# 12. Provider-portable daily backup of Postgres → Backblaze B2
#     (intentionally NOT Lightsail snapshots — works on any host)
cat <<'CRON' | sudo tee /etc/cron.daily/pg-backup-b2
#!/bin/bash
set -euo pipefail
docker exec agro_postgres pg_dump --format=custom --no-owner --no-acl \
  -d agro -U agro | gzip > /tmp/agro-$(date +%Y-%m-%d).dump.gz
docker exec agro_app python -m app.jobs.pg_dump_backup \
  --file /tmp/agro-$(date +%Y-%m-%d).dump.gz
rm /tmp/agro-$(date +%Y-%m-%d).dump.gz
CRON
sudo chmod +x /etc/cron.daily/pg-backup-b2

# 13. Lightsail snapshots (already enabled in pre-flight Step 4)
#     are an EXTRA safety layer on top of the B2 backup. You can disable
#     them any time without losing the B2 trail above.
#     Lightsail Console → your instance → Snapshots tab → verify enabled.

# 14. (Optional but recommended) Disable Lightsail's public SSH port
#     once Tailscale is verified working:
#     Lightsail Console → Networking → IPv4 Firewall → remove SSH (port 22)
#     rule. SSH henceforth only over Tailscale (100.64.0.0/10 range).
```

**Validation checklist after setup:**
- [ ] `docker compose ps` shows all containers `healthy` (postgres, mosquitto, chroma, app, caddy, prometheus, grafana)
- [ ] `curl https://api-<ip>-with-dashes.sslip.io/api/v1/health` returns 200 with valid SSL
- [ ] `mosquitto_sub -h mqtt-<ip>-with-dashes.sslip.io -p 8883 --cafile /etc/ssl/certs/ca-certificates.crt -t test -d -u service -P <pwd>` connects (clean test for MQTT TLS)
- [ ] Tailscale: `tailscale status` shows your laptop + the VPS as peers
- [ ] Grafana reachable from Tailscale-connected laptop at `https://metrics-<ip>.sslip.io`
- [ ] `sudo tail -f /var/log/fail2ban.log` shows fail2ban started
- [ ] AWS Console → Billing → Budgets shows the $30/mo alert is active
- [ ] Lightsail Console → Snapshots tab shows automatic snapshots enabled
- [ ] Lightsail Firewall has TCP 80 + 443 + 8883 open (port 22 should be Tailscale-only after migration)
- [ ] `df -h` shows >50 GB free on `/` (initial usage ~10 GB after Docker images pulled)

**When you finalize the brand name and buy the domain:**
1. Add A records in Cloudflare for `api.<brand>.in`, `mqtt.<brand>.in`, `dashboard.<brand>.in` pointing at the Lightsail static IP.
2. Run `make caddyfile-prod DOMAIN=<brand>.in` (regenerates Caddyfile using the real domain).
3. Commit + push → Coolify auto-deploys → Caddy reissues SSL.
4. Update `EXPO_PUBLIC_API_URL` in the Expo app env config.
5. Update `META_WHATSAPP_VERIFY_TOKEN` callback URL in Meta dashboard.
6. Push a `cmd` MQTT message to the Main Node updating its broker host (no firmware reflash needed — Phase 8.7 config hot-reload).

**When you migrate to another host** (DigitalOcean, Hetzner, EC2, anywhere): follow Part 0.5 Rule 5 procedure. The IP changes; the hexagon doesn't.

**When you outgrow Lightsail $20** (around 100 farms based on the scalability ladder in Part 12.4):
- **Option A — Lightsail $40/mo plan** (4 vCPU / 16 GB / 160 GB SSD). Resize via Console → your instance → Plans → Change. Takes ~5 min with a brief downtime.
- **Option B — Migrate to EC2** (t3.large + EBS gp3 + RDS db.t3.medium). Follow Rule 5; takes ~2 hours; gives you proper horizontal scaling room.

Both options work; Option A is the smoother path until you hit ~500 farms.

## 12.3 Backups + DR

**Three layers of recovery:**

1. **Daily snapshots** via Lightsail (instance-level). RPO 24 h, RTO 30 min. $0.05/GB/mo (~$4/mo on the 80 GB plan). Enabled in pre-flight Step 4.
2. **Weekly pg_dump → Backblaze B2** (database-level). RPO 7 d, RTO 1 h. Cost ~$0.05/mo at pilot.
3. **Schema-only dump on every deploy** committed to repo. Recovery from "schema borked, data fine".

**Quarterly restore drill is mandatory.** Time it; document it; fix surprises before they become emergencies.

## 12.4 Scalability ladder

| Inflection | Symptom | Action |
|---|---|---|
| 1–10 farms | Single VPS healthy | Vertical only |
| 10–50 farms | Postgres CPU < 40% | Resize Lightsail to $40 plan (4 vCPU/16 GB) — stop, resize, start (~5 min downtime) |
| 50 farms | Ingest p99 drags API p99 | Move Mosquitto + ingest worker to 2nd small VPS |
| 100 farms | Postgres CPU > 60% at peak | Split DB to own VPS; add PgBouncer (transaction mode) |
| 200 farms | API p99 > 500 ms | Run 2× FastAPI behind Caddy LB |
| 500 farms | LLM > ₹50K/mo | Haiku-first; cache by bin; consider fine-tuning |
| 1000 farms | Backup window > 1 h | Move to managed Postgres (Crunchy Bridge, Neon Scale, Aurora) |
| 5000 farms | Single DB write maxed | Shard by tenant_id; migrate to Citus or TimescaleDB |
| 10000 farms | Operational complexity | ECS Fargate / EKS; dedicated DevOps |

Three architectural choices preserve all these escape paths:
1. **Repository pattern** — swap DB in 2 files, not 200
2. **Postgres native partitioning** — move to TimescaleDB/Citus without schema rewrites
3. **Hexagonal layering** — domain doesn't know about Postgres, FastAPI, or Anthropic. Replace any one of them without touching domain code.

## 12.5 Cost projection (v1.2 — AWS Lightsail pricing)

| Phase | Compute | Snapshots | DB | Storage | Backups | Monitor | LLM | WA/SMS | Total/mo |
|---|---|---|---|---|---|---|---|---|---|
| **Pilot (1 farm)** | **$20 Lightsail** | **$4** | $0 self-host | $0 R2 free | $1 B2 | $0 free tiers | ~$3 Sonnet+Haiku | $0 WA test | **~$28** |
| Growth (50 farms) | $40 Lightsail upgrade | $8 | included | $2 | $4 | $0 | ~$40 cached | $30 WA prod | **~$125** |
| Scale (500 farms) | $80 Lightsail max | $16 | included | $20 | $30 | $50 BetterStack | ~$300 batch + Haiku-first | $300 WA + SMS | **~$800** |
| Enterprise (5000) | $400 EC2+RDS+ALB | included | $200 | $100 | $100 | $200 | ~$1500 | $1500 | **~$4000** |

Pilot total: **$28/month** (~₹2,300/month) — well within bootstrap budget.

The Sonnet+Haiku mix produces ~3× cost reduction vs Opus on T1/T3 with no measurable Marathi quality loss at our token volumes.

At 50 farms, the cost cache (per §4.10 of the technical reference) drops batched LLM cost to ~$40/month vs ~$70/month uncached.

**Where the $28/month comes from:**
- Lightsail $20 instance — fixed
- Daily snapshots ~$4 (80 GB × $0.05/mo) — adjustable; turn off to save if confident in B2
- Backblaze B2 storage ~$0.50 for 100 GB × 12 weeks of weekly dumps — minimal
- Backblaze B2 egress only on restore — effectively $0 in steady state
- LLM ~$3 for one farm at one advisory/plot/day with Sonnet + Haiku
- WhatsApp Cloud API test mode — free
- All monitoring on free tiers (UptimeRobot, Sentry, Better Stack)

**Where you save money if you want to:**
- Skip Lightsail snapshots ($4/mo) and rely on B2 weekly dumps alone — safe if you're disciplined about the weekly verify drill
- Use the Lightsail $10/mo plan (1 vCPU / 2 GB / 60 GB) — fits the pilot but tight; sentence-transformers + Postgres + Mosquitto + FastAPI on 2 GB is the absolute floor. Recommend only if cash is brutally constrained.

## 12.6 Migration paths

| Need | Migration | Code change |
|---|---|---|
| Move DB to managed Postgres | Update DATABASE_URL; `pg_dump | pg_restore`; verify | 0 lines |
| Swap LLM (Claude → Gemini → Llama) | New adapter implementing `LlmClient` + ModelRole mapping | 1 new file |
| Swap SMS provider (post-Phase 13) | New `SmsClient` Protocol implementation | 1 new file |
| Add Razorpay (Phase 14) | New `PaymentClient` implementation + use cases | 4 new files |
| Add Sentinel-1 SAR | New `SatelliteClient` Protocol implementation | 1 new file |
| Switch event bus (Postgres NOTIFY → NATS) | New `EventBus` Protocol implementation | 1 new file |
| Add second tenant (FPO) | Insert row in tenants; provision farmers/farms | 0 lines |
| Add Hindi/English UI | Add `i18n/hi.json`, `i18n/en.json`; toggle in Settings | UI only |
| Add new crop | Add `rules/<crop>/*.json`; update STAGE_TABLES | 1 dict entry + N JSONs |
| Add new sensor type | Extend Reading dataclass + schema migration + validation gate | 3 files |
| Move to Kubernetes | Replace docker-compose.prod.yml with Helm chart | Infra only |
| Add Pro-tier SKU | Add to TIER_LIMITS dict; add Razorpay plan; UI gate | 3 files |

Every one of these is **mechanical**, not architectural — because the hexagon enforces the seams that make them so.

---

*End of final roadmap (v1.2). 14 phases · ~80 Cursor prompts · ~12 weeks pilot (or 2-week prototype via Fast Path Part 0.6) · ~$28/mo pilot infra · AWS Lightsail Mumbai + provider-portable by design (Part 0.5) · 1 farmer · 4 plots · 1 Main Node · 2 Sub Nodes · 1 cleanly-architected hexagon whose seams will pay you back for the next 5 years.*
