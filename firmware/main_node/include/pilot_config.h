/*
 * VIRAAI Main Node — Pilot configuration
 * ======================================
 *
 * Every deployment-specific string lives here. When the pilot's identifiers,
 * MQTT credentials, or the Lightsail IP change, edit this file and reflash.
 *
 * SECURITY NOTE
 * -------------
 * The MQTT password is currently baked into firmware as a compile-time
 * constant. This is acceptable ONLY for the initial pilot smoke test. Before
 * moving to real deployment, migrate credentials to ESP32 NVS (Preferences
 * library) or a provisioning EEPROM, and rotate the value below.
 */

#ifndef PILOT_CONFIG_H
#define PILOT_CONFIG_H

// -------- Firmware identity --------
#define FIRMWARE_VERSION       "viraai-mn-1.0.0-raw"

// -------- Main Node device --------
#define MAIN_NODE_ID           "AGR-MN-0001"

// -------- Cloud identifiers (must match agro_backend/scripts/dev/seed_pilot.py) --------
#define PILOT_TENANT_ID        "11111111-1111-1111-1111-111111111111"
#define PILOT_FARMER_ID        "aaaaaaaa-1111-1111-1111-111111111111"
#define PILOT_FARM_ID          "bbbbbbbb-2222-2222-2222-222222222222"

// -------- MQTT broker --------
#define MQTT_HOST              "mqtts-13-207-20-67.sslip.io"
#define MQTT_PORT              8883
#define MQTT_USERNAME          "main-node-001"
#define MQTT_PASSWORD          "72f7f48d73444811d45c0e0e78ae13e94d4a2ad4c0baf99d"
#define MQTT_KEEPALIVE_SECS    60
#define MQTT_CLEAN_SESSION     1     // 0 = persist subscriptions, 1 = fresh session

// -------- Cellular APN (pilot SIM = Airtel; change here if the SIM changes) --------
#define MODEM_APN              "airtelgprs.com"
#define MODEM_DNS1             "8.8.8.8"
#define MODEM_DNS2             "8.8.4.4"

// -------- TLS on the modem --------
// sslversion:      3 = auto-negotiate (empirically most reliable on A7672S)
// authmode:        0 = do NOT verify server cert  (pilot only — see security note)
// ignorelocaltime: 1 = skip cert notBefore/notAfter check (paired with authmode=0)
// enableSNI:       1 = REQUIRED for caddy-l4 to route to the right cert
#define MODEM_SSLVERSION       3
#define MODEM_AUTHMODE         0
#define MODEM_IGNORE_TIME      1
#define MODEM_ENABLE_SNI       1
#define MODEM_MQTT_VERSION     4      // 4 = MQTT 3.1.1

// -------- LoRa RX --------
#define LORA_FREQUENCY_HZ      433000000UL
#define LORA_SPREADING_FACTOR  7
#define LORA_BANDWIDTH_HZ      125000UL
#define LORA_CODING_RATE       5

// -------- NODE_ID → PLOT_ID mapping (extend as more Sub Nodes come online) --------
// Keep this table in lock-step with agro_backend/scripts/dev/seed_pilot.py::PLOTS
// so the Main Node's inferred plot_id matches the backend's expected plot_id.
#define NODE_MAP_SIZE          1
static const struct { const char* node_id; const char* plot_id; } NODE_MAP[NODE_MAP_SIZE] = {
    { "AGR-SN-0001", "PLOT_PILOT_001" },
    // When AGR-SN-0002 is deployed:
    // { "AGR-SN-0002", "PLOT_PILOT_003" },
};

// -------- Timing --------
#define BOOT_MODEM_RETRIES     5
#define MQTT_RECONNECT_MS      5000UL   // wait between reconnect attempts
#define NTP_SYNC_TIMEOUT_MS    20000UL
#define MASTER_SENSOR_READ_MS  2000UL   // read own weather sensors this often
#define MODEM_UART_BAUD        115200UL

// -------- Timestamp sanity window --------
// Any parsed year outside [MIN, MAX] is treated as "clock not set" and the
// firmware falls back through the timestamp source chain (modem NTP -> RTC ->
// "none"). This is what prevents 2070-01-01 style hardware clock skew from
// leaving the device — the backend also has a safety net (broker-side
// _normalize_clock_skew) but firmware should be the first line of defence so
// bad rows never enter the partition router.
#define TIME_MIN_YEAR          2025
#define TIME_MAX_YEAR          2035

// -------- Sub Node liveness + Main Node heartbeat --------
// Publish a master-only telemetry packet ($schema=agro-guardian/telemetry/
// v2-master) on this cadence even when no LoRa frame arrives. Prevents
// "Sub Node silent" from looking identical to "Main Node dead / LoRa dead"
// downstream: ops sees fresh master_readings + sub_node_online=false and
// knows exactly where the fault is.
//
// Retuned 2026-08-27: Sub Node cadence is now 5 min. Matching the heartbeat
// to the Sub Node cadence cuts 4G data ~5× and keeps ops resolution at
// "1 sample per 5 min" for both liveness paths.
#define MASTER_HEARTBEAT_MS            300000UL   // 5 minutes
// After this long without a LoRa RX, mark sub_node_online=false. At 5 min
// cadence 15 min = 3 missed cycles — clean signal without false alarms on
// a single dropped LoRa packet.
#define SUB_NODE_SILENCE_THRESHOLD_MS  900000UL   // 15 minutes

// -------- ESP32 task watchdog --------
// A single MQTT publish can take ~10 s worst-case (CMQTTPAYLOAD + CMQTTPUB).
// Reconnect + payload push can stack close to 60 s. Set the WDT to 90 s so
// a truly hung modem (SIM stuck in dedicated mode, TCP half-open, etc.)
// triggers a clean reboot rather than a frozen device.
#define ESP32_TASK_WDT_S               90

// -------- SD offline outbox --------
// When MQTT publish fails, we append the (topic, payload) tuple as a
// newline-delimited JSON line to /outbox.jsonl on the SD card. On next
// successful MQTT connect, drain up to SD_OUTBOX_DRAIN_BATCH lines per loop
// pass until empty. Prevents data loss during 4G outages (monsoon).
#define SD_OUTBOX_PATH                 "/outbox.jsonl"
#define SD_OUTBOX_DRAIN_BATCH          20
#define SD_OUTBOX_MAX_BYTES            5242880UL   // 5 MB cap; older entries lost if hit

// -------- Payload sizing --------
#define MAX_LORA_PAYLOAD       240      // SX1278 hard cap is 255; buffer smaller
#define MAX_JSON_PAYLOAD       1200     // headroom for verbose JSON

#endif // PILOT_CONFIG_H
