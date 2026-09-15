# AgroGuardian V2 — Migration to a New Machine

**Read this document top-to-bottom before doing anything.** It bootstraps a fresh Claude session on a new laptop with the full context of the project.

**What you get in this bundle (default "context-only" mode):**

- `proj/` — the *context* directory. Contains `reference/agri-AI/` (snapshot of what's running on Mac + VPS), `outputs/` (all patch bundles + export scripts + docs), `new-docs/` (Ginger Engine reference material), the 184 KB `AgroGuardian_FINAL_Roadmap.md`, and the top-level `README.md`. **Does NOT contain `agro_backend/` or `firmware/`** because you've already transferred those to the new laptop via git or an earlier explicit export. If you ran `python migrate_export.py --include-code`, those two folders are also present.
- `SKILL_agroguardian.md` — the AgroGuardian project skill. Save this on the new Claude before starting real work; otherwise Claude has no persistent memory of the pilot's decisions, wire format, KB structure, or open blockers.
- `MIGRATION_GUIDE.md` — this file.
- `MANIFEST.txt` — SHA-256 of every entry, for transfer-integrity verification.

---

## 1. What the project is (30-second recap for the new Claude)

**AgroGuardian V2** is a precision-ag IoT + AI advisory platform for smallholder ginger farmers in Aurangabad, Maharashtra.

- **Hardware:** One buried Sub Node (ATmega328P, LoRa 433 MHz) + one Main Node (ESP32 + A7672S 4G modem) per farm. Sensors: capacitive soil probe, NPK Modbus probe, DS18B20 temp, flow, pressure, battery, weather (BME280, INA219, rain gauge, anemometer, wind vane).
- **Data path:** Sub Node → LoRa CSV every 5 min → Main Node → MQTT-TLS over 4G → Lightsail Mumbai VPS running Caddy (`caddy-l4`) → Mosquitto → FastAPI ingest broker → Postgres.
- **Advisory path:** Sensor + satellite + weather → Ginger Engine (data-driven KB, 431 rules across ~15 domains) → daily 06:30 IST → one Marathi WhatsApp message per plot at 07:00 IST.
- **Codebase discipline:** Hexagonal, pure domain layer enforced by AST scan, Postgres RLS + monthly partitioning, hand-written Alembic migrations, `.cursorrules` in the repo, `docs/DATA_INVENTORY.md` as the single source of truth for every field and its provenance.
- **Pilot scope:** 1 farm, 1 farmer, 2 plots (1 hardware, 1 satellite-only), 1 Main Node, 1 Sub Node. Kharif 2026 ginger, variety Mahima.

The full picture is in the AgroGuardian skill (see §3 below) and in `proj/agro_backend/docs/`. Do not proceed on a real task without reading at least `docs/DATA_INVENTORY.md` and `docs/SETUP.md`.

---

## 2. On the new laptop — restore the project files

Unzip this bundle anywhere. You will get an `agroguardian-migration-YYYYMMDD/` folder with `proj/`, `MIGRATION_GUIDE.md` (this), `SKILL_agroguardian.md`, and `MANIFEST.txt`.

Then decide where the working tree should live. Recommended: match the previous machine's layout to keep every path in every doc still valid.

**On a Mac:**

```bash
# Recommended: same layout as the previous machine (paths in docs still work)
mkdir -p ~/repos/agri-AI
rsync -a agroguardian-migration-YYYYMMDD/proj/ ~/repos/agri-AI/

# Verify integrity against the manifest
cd agroguardian-migration-YYYYMMDD
while read -r sha _ rel _; do
    [ -f "proj/$rel" ] || continue
    actual=$(shasum -a 256 "proj/$rel" | awk '{print $1}')
    [ "$actual" = "$sha" ] || echo "MISMATCH: $rel"
done < MANIFEST.txt
```

**On Windows PowerShell:**

```powershell
# Adjust the source path to wherever you unzipped
$src = "$env:USERPROFILE\Downloads\agroguardian-migration-YYYYMMDD"
$dst = "$env:USERPROFILE\Repos\proj"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item -Recurse -Force "$src\proj\*" $dst
```

The `proj/` subtree contains (default context-only mode):

| Folder / file | What's in it | Present in default mode? |
|---|---|---|
| `agro_backend/` | Full Python backend — app, tests, alembic, docs, scripts, deploy configs, ginger KB. | Only with `--include-code` (you have it via git) |
| `firmware/` | Sub Node (Arduino IDE) + Main Node (PlatformIO). | Only with `--include-code` |
| `reference/agri-AI/` | Snapshot of what was actually running on the Mac + VPS. Read-only reference — don't edit it, only compare. | ✅ Always |
| `outputs/` | All the export scripts and patch bundles built in prior sessions — the patch bundles let you re-apply exact deltas on the target if git history diverges. | ✅ Always |
| `new-docs/` | Ginger Engine reference material from the teammate who authored the KB. | ✅ Always |
| `AgroGuardian_FINAL_Roadmap.md` | 184 KB roadmap v1.2 (aspirational; SCHEMA_DECISIONS.md cites it). | ✅ Always |
| `README.md` | Pointer into `agro_backend/docs`. | ✅ Always |

**Merge into your existing `agro-guardian/` layout** rather than replacing anything you already have. On the new laptop you should end up with `agro_backend/` and `firmware/` from git, plus `reference/`, `outputs/`, `new-docs/`, and the roadmap alongside them.

---

## 3. On the new laptop — restore the AgroGuardian skill

The single most important piece for Claude to have context on this project is the AgroGuardian skill. Without it, the new Claude will not know:

- The wire contract (`$schema=v2` vs `v2-raw` vs `v2-master`, the three-way `window_s` encoding, `time_source` / `sub_node_online` semantics, master-only heartbeat).
- The 60-file schema, the 431-rule KB structure, the hexagonal purity rules.
- What's done vs what's open (Round 13 advisory subscriber, Round 14 WhatsApp go-live, TLS `authmode=2` hardening, LoRa regulatory clearance).
- The decisions log — why Airtel, why 5-min cadence, why raw values, why SNI-based L4 routing, etc.

**To restore the skill on the new Claude:**

1. Start a new Claude session on the new laptop, in Cowork mode with your project folder connected.
2. Open the file `SKILL_agroguardian.md` (top-level in this bundle).
3. Ask the new Claude to save it as a skill. A message like:

   > "Save the attached SKILL_agroguardian.md as a skill named `agroguardian-context` with `overwrite: true`. The description from the skill's own frontmatter is the description. Use it as the single source of truth for this project."

4. The new Claude uses its `save_skill` tool to persist it. From then on, any conversation mentioning AgroGuardian, agro_backend, LoRa, ginger, or any of the trigger keywords in the skill's description will auto-load the full context.

5. Test: ask the new Claude "what's the current Round we're on?" — it should answer "Round 17.5 shipped, Round 13 is next" or similar without you having to explain.

---

## 4. On the new laptop — bring up the dev environment

Follow `proj/agro_backend/docs/SETUP.md` — that's the definitive step-by-step. Highlights of what you'll do:

1. **Prereqs:** Python 3.12, Docker Desktop, PlatformIO CLI, Arduino IDE + MiniCore + USBasp, Rocket Scream `LowPower` library, `sha256sum` or `shasum`.
2. **Local Postgres + Mosquitto:** `docker compose -f docker-compose.dev.yml up -d`.
3. **Migrations + seed:** `alembic upgrade head && python scripts/dev/seed_pilot.py`.
4. **Verify tests:** `pytest -q`. Expected: all green (~470 tests). If red, do not proceed to VPS or firmware flashing.
5. **VPS deploy:** `docker compose -f docker-compose.prod.yml up -d` on the Lightsail box, with a proper `.env` (real `AUTH_JWT_SECRET`, `POSTGRES_PASSWORD`, `MQTT_BROKER_PASSWORD`, `ANTHROPIC_API_KEY`; the app's config validator refuses to boot in prod without them).
6. **Firmware:** Sub Node via Arduino IDE + USBasp, Main Node via `pio run -t upload`. Bench-test the seven scenarios in SETUP.md §6 before deploying to the field.

---

## 5. Where the project currently stands (as of migration day)

**Shipped:**

- Round 3–7: MQTT ingest broker + 4 validation gates + idempotent UPSERT into `node_sensor_readings`.
- Round 8: OTP → JWT with refresh rotation; 15-endpoint read API.
- Round 9–10: 7-rule device-health engine with Marathi templates + cooldowns.
- Round 12: Streamlit dashboard.
- Round 16: Raw-payload ingestion (`v2-raw`) + per-device calibration table (`device_calibration`). Sub Node emits raw ADC counts; backend calibrates.
- **Round 17:** `weather_station_readings` promoted out of `sensor_health_json` into its own table. Broker persists from both `v2-raw` and `v2-master` paths (idempotent on `master_node_id, recorded_at`).
- **Round 17.5:** Main Node master-only heartbeat (`v2-master`) — new schema, new `main_node_readings` table (migration 0013), new `MainNodeReading` domain + `PgMainNodeReadingRepo` adapter, broker persists + meters via `agro_main_node_heartbeat_total{sub_node_online}`, API routes at `/api/v1/main_nodes/{id}/heartbeat` + `/weather` with pagination.
- **Firmware v2.1 (this is the FINAL firmware — no more changes planned):** Sub Node 5-min cadence + LowPower deep sleep + PCINT flow counting + ATmega WDT + NPK Modbus retries + `WIN=` (on-device flow window in seconds) + `UP=` (uptime) + `FLT=` (fault flags) + post-TX LED status codes. Main Node ESP32 task WDT + SD outbox for offline buffering + boot log + heartbeat + parse of UP/FLT into JSON + wind gust tracking + `backlog_pending` marker on drained rows.
- Backend clock-skew safety net (`_normalize_clock_skew`) rewrites impossible timestamps to server UTC and stamps `validation_warn=true`.
- Ginger Engine — 431 rules across ~15 domains, hand-authored by the agronomy team, imported via migration 0010. Runs daily at 06:30 IST.
- Documentation: `HARDWARE_WIRE_CONTRACT.md`, `SCHEMA_DECISIONS.md`, `DATA_INVENTORY.md` (full field-level source labels for every column in every table), `SETUP.md`.
- Prometheus alertmanager rules: `MainNodeDown`, `SubNodeDown`, `IngestBrokerDroppingMessages`, `IngestQueueGrowing`, `HttpErrorRateHigh`.

**Not yet built (in priority order):**

- **Round 13 — advisory subscriber.** `LISTEN agro_events` → `compose_advisory.execute()`. Migration `0014_advisory_status`. About 150 LOC. Blocked on nothing — this is the next thing to build.
- **Round 14 — WhatsApp advisory go-live.** Needs WABA business verification (compliance thread), utility template, `POST /api/v1/webhooks/whatsapp`.
- **Round 18 — nightly weather rollup** populating `weather_station_readings.air_temp_min/max/rain_mm_today/…` from raw pulses.
- Farmer app (Phase 9 — deferred; WhatsApp-first for now).
- Modem TLS hardening: `authmode=0` → `authmode=2` + ISRG Root X1 + MQTT password from firmware to ESP32 NVS.
- LoRa 433 MHz regulatory clearance with a TEC consultant for commercial deployment.
- Farm Brain coverage expansion from ~85 fields to 60–70% of the 305-field spec.
- Object storage wiring (Cloudflare R2 or Backblaze B2 — Provider Portability Charter forbids AWS-managed S3).
- Production Sentry alerts + backups + Tailscale + Grafana dashboards.

**Open blockers:**

1. Firmware v2.1 has not been physically flashed to the field boards yet — the current session ended with the bundles ready but the flash hasn't happened.
2. Modem TLS is `authmode=0` — MITM-vulnerable, pilot only.
3. MQTT password lives in `firmware/main_node/include/pilot_config.h` — must rotate + move to NVS before real deployment.
4. WhatsApp Business API not yet verified for the pilot number.
5. `pump_current_amps` isn't sensed on the current Main Node hardware, so several irrigation rules and `electricity_schedule_log` rely on flow-inference only.

**Key open questions (for the new Claude to raise if relevant):**

- KB authoring workflow — the 1.16 MB SQL blob has to come from somewhere. What tool does the agronomy team use to write rules? Recommend building a Notion/Airtable → SQL converter with golden-test enforcement.
- Second crop identity (cotton vs tomato) — depends on where the next farm partnership lands.
- Farmer app vs WhatsApp-forever — for the first 5000 farmers WhatsApp is enough; app makes sense when we need photos, sliders, or offline capture.
- Whether valve/pump actuation ever ships (Tier-Pro price includes it; changes liability model).
- Whether we sell anonymised aggregated data to agri-input suppliers (with consent; moral edge, answer may be "no").

---

## 6. Verifying nothing was lost in transit

The bundle contains a `MANIFEST.txt` listing every entry with its SHA-256. To spot-check:

**Mac / Linux:**

```bash
cd agroguardian-migration-YYYYMMDD
# Pick 10 random files from the manifest and re-hash each
awk '{print $1, $2}' MANIFEST.txt | shuf | head -10 | while read sha rel; do
    actual=$(shasum -a 256 "$rel" | awk '{print $1}')
    [ "$actual" = "$sha" ] && echo "OK  $rel" || echo "MISMATCH $rel"
done
```

**PowerShell:**

```powershell
Set-Location agroguardian-migration-YYYYMMDD
$sample = Get-Content MANIFEST.txt | Where-Object {$_ -notmatch '^#'} | Get-Random -Count 10
foreach ($line in $sample) {
    $expected, $rel = ($line -split '\s+', 3)[0..1]
    if (Test-Path $rel) {
        $actual = (Get-FileHash $rel -Algorithm SHA256).Hash.ToLower()
        if ($actual -eq $expected) { "OK  $rel" } else { "MISMATCH $rel" }
    }
}
```

Any mismatch means the zip was corrupted in transit — re-transfer and re-verify.

---

## 7. First conversation on the new Claude — recommended script

Once the code and the skill are in place, open a new Claude session and paste something like this to prime the context:

> I've migrated the AgroGuardian V2 project from another machine. The `agroguardian-context` skill has been saved and should auto-load when you see any of its trigger words. Please:
>
> 1. Read `agro_backend/docs/SETUP.md`, `agro_backend/docs/DATA_INVENTORY.md`, and `agro_backend/docs/SCHEMA_DECISIONS.md` end-to-end so you have the ground-truth view of the codebase.
> 2. Report back: what's the state of the pilot, what Round is next, and what open blockers exist.
> 3. Do not modify anything until I confirm you have the full picture right.

If Claude answers well, you're set. If it's confused about basics (wire schema, pilot scope, what's shipped), the skill didn't load — check step 3 of this guide.

---

## 8. Fast-path — if you just want to keep coding

If you don't care about the full ceremony and just want to pick up where you left off:

1. Unzip.
2. `mkdir -p ~/repos/agri-AI && rsync -a proj/ ~/repos/agri-AI/`.
3. Save `SKILL_agroguardian.md` as a skill on the new Claude.
4. In the new Claude: "read `agro_backend/docs/SETUP.md` and tell me what you'd do next."

That gets you productive in about 5 minutes. Everything else in this guide is background / recovery / verification.

---

## 9. If something goes wrong

- **The zip won't extract** — `unzip -t agroguardian-migration-*.zip` to test integrity. If it errors, the transfer was corrupted; re-transfer.
- **The skill won't save on the new Claude** — check that the session has the `save_skill` tool (Cowork mode should). If not, paste the entire `SKILL_agroguardian.md` content in the first message as a system-prompt-like preface.
- **The new Claude claims not to know about a specific field or table** — the DATA_INVENTORY.md doc is the authoritative reference. Point Claude at the specific section.
- **`pytest -q` fails on the new machine** — most common cause is missing `.env`, missing local Postgres, or missing Python 3.12 exactly. See SETUP.md §1.
- **Firmware won't compile** — Sub Node needs Rocket Scream `LowPower` library installed via Arduino Library Manager. Main Node needs `pio` on PATH. See SETUP.md §4 and §5.

---

*End of migration guide. If in doubt, `docs/SETUP.md` in the extracted `proj/agro_backend/` is the ground truth for setup, and the AgroGuardian skill is the ground truth for context. When those two disagree with anything in this guide, they win — update this guide.*
