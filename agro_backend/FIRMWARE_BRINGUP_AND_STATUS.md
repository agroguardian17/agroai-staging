# Firmware Bring-up & Current Status

**Prepared 2026-09-17 · main @ `317a5a9` · migrations head `0016` · staging `agro-staging-01` (13.207.20.67)**

Read this before connecting hardware today. It covers: (1) exactly where the system stands and
what was verified, (2) a pre-flight checklist to run before powering the Main Node, (3) the
detailed firmware test procedure, (4) what's left on your side, and (5) the next stages.

Companion docs: **[`docs/HARDWARE_WIRE_CONTRACT.md`](docs/HARDWARE_WIRE_CONTRACT.md)** (the
authoritative firmware payload/topic/transport spec — code wins over docs), **[`PILOT_READINESS.md`](PILOT_READINESS.md)** (go-live + WhatsApp), **[`ACCOUNTS_TO_FILL.md`](ACCOUNTS_TO_FILL.md)** (credentials).

---

## 1. Status — what's proven, what's pending

### Verified green today (2026-09-17)
- **Code quality:** `ruff` clean, `mypy` clean (133 files), **full test suite passes (exit 0)**, git tree clean, migrations at head `0016` with no drift.
- **Full advisory loop proven end-to-end on dummy data:** an injected 8 % soil-moisture reading flowed all the way through — `node_sensor_readings` → `low_water` alert in `alerts_notifications` → **Claude composed a real Marathi advisory** → `ai_suggestions`. That's the hard part of the system, working.
- **WhatsApp sender number:** the new production number **+91 70211 98781 is VERIFIED** and matches `.env` (`phone matches env: True`).

### Pending (not blockers for firmware bring-up)
| Item | State | Effect |
|---|---|---|
| Advisory template on the **new** WABA | **PENDING** (`mr`) — awaiting Meta approval | Real advisory WhatsApp sends return `meta_132001` until it flips to APPROVED. `hello_world` is APPROVED and usable for outbound smoke tests meanwhile. |
| Meta app **publish** | Unpublished | Inbound webhooks (farmer replies → `farmer_actions`) only deliver **test** data until the app is published. Outbound advisories don't need it. |
| Business verification | Not started | Raises messaging limits and unlocks the OTP/Authentication template. Not needed for the pilot. |
| Main Node MQTT credential on broker | Verify (see §2) | Firmware can't publish until its username/password is in the broker's `passwd`/`acl`. |
| Device calibration rows | Verify (see §3, Stage 3) | Raw-format firmware needs `device_calibration` rows or the computed values are meaningless. |

**Bottom line:** the backend is code-complete and green. Firmware bring-up is about proving the
**hardware → broker → ingest → rules** hops with real devices; the advisory/WhatsApp hops are
already proven and just wait on the template approval.

---

## 2. Pre-flight checklist (run before powering the Main Node)

All read-only except where noted. Run from `~/agri-AI-live/agro_backend` on the VPS.

**2.1 Services healthy + app on head 0016**
```bash
docker compose -f docker-compose.prod.yml ps
curl -s https://api-13-207-20-67.sslip.io/api/v1/health
docker compose -f docker-compose.prod.yml exec app alembic current
```
Want: all containers `healthy`/`running`, health returns `{"status":"ok",...}`, alembic current = `0016 (head)`.

**2.2 The Main Node's MQTT credential exists on the broker.** The firmware authenticates with a
username/password that must be in the broker's `passwd` + `acl`. Check which node users exist:
```bash
docker compose -f docker-compose.prod.yml exec mosquitto sh -c "cut -d: -f1 /mosquitto/config/passwd"
docker compose -f docker-compose.prod.yml exec mosquitto sh -c "cat /mosquitto/config/acl"
```
The ACL should list your Main Node user (e.g. `main-node-001`) with `topic readwrite agro/v2/#`. If
your firmware uses a **different** username, provision it (**mutating** — needs a mosquitto restart):
```bash
# on the VPS, from the repo dir:
bash scripts/dev/provision_mqtt_credential.sh <firmware-username> '<strong-password>'
docker compose -f docker-compose.prod.yml restart mosquitto
```
Whatever username/password you use here must be flashed into the Main Node firmware config.

**2.3 The public MQTTS endpoint is reachable + TLS terminates** (run from your laptop):
```bash
openssl s_client -connect mqtts-13-207-20-67.sslip.io:8883 -servername mqtts-13-207-20-67.sslip.io </dev/null 2>/dev/null | openssl x509 -noout -subject -dates
```
Want: a valid Let's Encrypt cert with future `notAfter`. (Caddy L4 terminates TLS on 8883 and proxies to `mosquitto:1883`.) Confirm the Lightsail firewall has **TCP 8883 open** (ACCOUNTS_TO_FILL Tier 2 #5).

**2.4 Seed / device row exists for the real node.** The reading FK-references `device_registry`.
Confirm the Sub Node id your firmware will send (`AGR-SN-0001` for the pilot) exists:
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c "select device_id, device_status from device_registry where device_id like 'AGR-%';"
```
If empty, run `seed_pilot.py` (PILOT_READINESS §3 F1).

**2.5 Decide CALIBRATION_MODE** — this is the single most important firmware-bring-up switch:
```bash
docker compose -f docker-compose.prod.yml exec app printenv CALIBRATION_MODE
```
- **First hardware bring-up → set `CALIBRATION_MODE=true`.** Readings are ingested and stored, but the rule engine is short-circuited (no alerts, no advisories, no farmer messages) while you dial in sensor calibration. This is exactly why our earlier dummy test saw no alert until we turned it off.
- **After calibration is confirmed → set `CALIBRATION_MODE=false`** to let alerts + advisories fire.

> ⚠️ Note we set `CALIBRATION_MODE=false` during the dummy-data test. **For real hardware bring-up you
> almost certainly want it back to `true`** until the sensors are calibrated, then flip it off.

---

## 3. Firmware bring-up — detailed test procedure

Work through these stages in order. Each has a clear pass condition; don't advance until the current
stage is green. The **authoritative payload/topic/transport contract is
[`docs/HARDWARE_WIRE_CONTRACT.md`](docs/HARDWARE_WIRE_CONTRACT.md)** — the firmware must match it
exactly (`extra="forbid"`: any unknown field drops the whole message).

### Stage 0 — Firmware config
Flash / configure the Main Node with:
- **Broker:** `mqtts-13-207-20-67.sslip.io`, **port 8883**, **TLS on** (system CA bundle), MQTT v5, QoS 1, keepalive 60 s, auto-reconnect.
- **Credentials:** the username/password from §2.2.
- **Topic:** `agro/v2/11111111-1111-1111-1111-111111111111/bbbbbbbb-2222-2222-2222-222222222222/<node_id>/telemetry` (node_id = the originating Sub Node, e.g. `AGR-SN-0001`).
- **Payload:** per the wire contract. Note the schema discriminator — v2 (`agro-guardian/telemetry/v2`, pre-calibrated %) vs **v2-raw** (`agro-guardian/telemetry/v2-raw`, raw ADC counts that the server calibrates). Confirm which one the frozen firmware emits; the parser dispatches on `$schema`.

### Stage 1 — Connectivity: does the Main Node connect + publish?
Open a live broker subscription **on the VPS** and watch frames arrive as you power the node
(use the `service` account, which can read `agro/#`; substitute its password):
```bash
docker compose -f docker-compose.prod.yml exec mosquitto mosquitto_sub -h localhost -p 1883 -u service -P '<MQTT_BROKER_PASSWORD>' -t 'agro/v2/#' -v
```
**Pass:** you see one line per Sub-Node reading, topic correct, JSON payload present.
**If nothing arrives:** TLS/auth/topic problem — check the node can reach 8883 (firewall), the
credential matches §2.2, and the topic has exactly six segments. Broker auth failures show in
`docker compose -f docker-compose.prod.yml logs mosquitto`.

### Stage 2 — Ingest: are readings landing and schema-valid?
```bash
# readings for the real node
docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c "select node_id, soil_moisture_avg_pct, battery_voltage_v, recorded_at from node_sensor_readings order by recorded_at desc limit 5;"
# validation drops (firmware payload bugs land here, NOT in the DB)
docker compose -f docker-compose.prod.yml logs --since 10m app | grep -iE "ingest|validation|drop|reject|extra|forbid"
```
**Pass:** fresh rows for your node with plausible values.
**If frames arrive at the broker (Stage 1) but no DB rows:** a schema validation failure — the log
will name the offending field. Common firmware bugs: an extra field (`extra="forbid"` drops it), a
naive timestamp (must have `Z`/offset), or a value out of range. Fix firmware, re-send.

### Stage 3 — Calibration (raw-format firmware only)
If the firmware emits **v2-raw** (raw ADC counts), the server converts them using per-device
`device_calibration` rows (Alembic 0012). Without a calibration row the defaults are used and the
computed %/bar values will be wrong.
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c "select device_id, soil_dry_adc, soil_wet_adc, updated_at from device_calibration where device_id='AGR-SN-0001';"
```
**Calibration procedure** (with `CALIBRATION_MODE=true`): take a **dry** reading (probe in air) and a
**wet** reading (probe in saturated soil/water), read the raw ADC values from `node_sensor_readings`,
and write them into `device_calibration` (`soil_dry_adc` = the dry raw value, `soil_wet_adc` = the wet
raw value); repeat for battery/pressure/flow constants as needed. Then re-send and confirm the
computed `soil_moisture_avg_pct` reads ~0 % dry and ~100 % wet.
**Pass:** calibrated values track reality.

### Stage 4 — Rules + advisory (set `CALIBRATION_MODE=false`)
Turn calibration mode off (§2.5), then create a real threshold breach — the easiest physical test is
to **pull the soil probe into open air** so moisture reads well below the 28 % target:
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c "select alert_type, severity, alert_value, triggered_at from alerts_notifications order by triggered_at desc limit 3;"
docker compose -f docker-compose.prod.yml exec postgres psql -U agro -d agro -c "select suggestion_id, review_status, delivery_status, left(full_message_marathi,60) as preview from ai_suggestions order by generated_at desc limit 1;"
```
**Pass:** a `low_water` alert appears, and a Marathi advisory row is composed. (Remember the 4-hour
`low_water` cooldown per plot — one alert per 4 h.)
**Delivery** (`delivery_status`) will be `sent` **only once the new WABA's advisory template is
APPROVED** (§1). Until then expect `failed_permanent / meta_132001`; that's a Meta approval wait, not
a firmware or backend fault.

### Stage 5 — Full loop (once template is APPROVED + app published)
Real advisory lands on the farmer's WhatsApp; farmer reply → `/webhooks/whatsapp` → `farmer_actions`
(inbound needs the app **published** — §4). Verify per PILOT_READINESS §3 F4–F5.

---

## 4. What's left on your side

Ordered by what unblocks the most:

1. **Approve the advisory template on the new WABA** (currently PENDING). Nothing to do but wait for Meta; once APPROVED, real advisory delivery works immediately (no code/config change — name already matches). Re-check: the WABA probe in PILOT_READINESS §3 B4.6.
2. **Provision + flash the Main Node MQTT credential** (§2.2) and point the firmware at `mqtts-13-207-20-67.sslip.io:8883`.
3. **Calibrate the real device** (§3 Stage 3) — required before trusting any field reading.
4. **Publish the Meta app** — needed for inbound farmer replies (Use cases → Step 2 shows the "unpublished ⇒ test webhooks only" banner). Requires a privacy-policy URL + completing app review basics. Outbound advisories don't need it.
5. **Farmer opt-in** — WhatsApp policy requires recipients to have opted in before you message them. Collect opt-in for each pilot farmer.
6. **Seed real farmer/farm/plot rows** with real phone numbers (`phone_primary`, E.164 `+91…`) and `language_preference='marathi'` (PILOT_READINESS §3 D).
7. **Business verification** (parallel, non-blocking) — raises limits + unlocks OTP template.
8. **Secret hygiene before real data:** `grep CHANGE_ME .env` should be empty; keep `ADVISORY_REQUIRE_REVIEW=true` for the first week so a human approves each advisory (PILOT_READINESS §3 C).

## 5. Next stages (sequence)

1. **Today — firmware bring-up:** Stages 0–3 (connectivity → ingest → calibration) with `CALIBRATION_MODE=true`.
2. **Rules live:** flip `CALIBRATION_MODE=false`, prove Stage 4 (real reading → alert → Marathi advisory) on hardware.
3. **WhatsApp outbound live:** once the template is APPROVED, prove Stage 5 outbound to a real (opted-in) farmer.
4. **Close the loop:** publish the Meta app → farmer replies captured as `farmer_actions` → nightly `ai_learning_log`.
5. **Run the pilot:** real farmers on the 2-plot Aurangabad deployment, review gate on for week 1, daily-ops checks (PILOT_READINESS §3 E).
6. **Post-pilot / scale:** business verification (higher limits, OTP); build the dormant adapters when their credentials are ready — satellite NDVI (Copernicus), soil-moisture (SMAP/NASA), object storage (R2), off-site backups (B2), push (FCM); add more plots by extending `seed_pilot.py::PLOTS` (no wire-contract change needed).

---

## 6. Known-good reference values (pilot)

| Thing | Value |
|---|---|
| API base | `https://api-13-207-20-67.sslip.io` |
| MQTTS endpoint (firmware) | `mqtts-13-207-20-67.sslip.io:8883` (TLS, MQTT v5, QoS 1) |
| Broker internal (backend only) | `mosquitto:1883`, `MQTT_USE_TLS=false` |
| Topic | `agro/v2/<tenant>/<farm>/<node>/telemetry` |
| Tenant id | `11111111-1111-1111-1111-111111111111` |
| Farmer id | `aaaaaaaa-1111-1111-1111-111111111111` |
| Farm id | `bbbbbbbb-2222-2222-2222-222222222222` |
| Hardware plot / node | `PLOT_PILOT_001` / `AGR-SN-0001` |
| Moisture target (LOW_WATER threshold) | 28 % (deficit > 0 fires) |
| low_water cooldown | 4 hours per plot |
| WhatsApp sender | +91 70211 98781 (VERIFIED) |
