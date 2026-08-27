/*
 * VIRAAI Sub Node — per-board configuration
 * =========================================
 *
 * CHANGE THE `NODE_ID` STRING BELOW BEFORE FLASHING EACH BOARD.
 * The Main Node identifies each incoming LoRa packet by this string, so
 * every Sub Node in the field MUST carry a unique value.
 *
 * Pilot mapping (as of 2026-08-26):
 *   AGR-SN-0001 → PLOT_PILOT_001
 *   AGR-SN-0002 → (reserved; not deployed in the current 2-plot pilot)
 */

#ifndef SUB_NODE_CONFIG_H
#define SUB_NODE_CONFIG_H

// -------- REQUIRED: per-board identity --------
#define NODE_ID              "AGR-SN-0001"

// -------- Firmware version (bumped on any behavioural change) --------
#define FIRMWARE_VERSION     "viraai-sn-1.0.0-raw"

// -------- LoRa radio --------
#define LORA_FREQUENCY_HZ    433000000UL
#define LORA_TX_POWER_DBM    17
#define LORA_SPREADING_FACTOR  7
#define LORA_BANDWIDTH_HZ    125000UL
#define LORA_CODING_RATE     5

// -------- Cycle timing (milliseconds) --------
// 5-minute cadence (2026-08-27). Sub Node MCU sleeps between cycles via
// LowPower.powerDown() to keep the 18650+solar budget realistic (~120 mA·h/day
// -> ~30 days on battery alone).
//
// The WDT clock is a 128 kHz internal RC, ±10-15% temperature dependent, so a
// nominal 300 s sleep can drift 260-340 s. Firmware measures the actual
// elapsed ms since the previous TX and emits it in the CSV as WIN=<seconds>
// so the backend can compute flow rate accurately.
#define CYCLE_PERIOD_MS      300000UL  // 5 minutes — full cycle target
#define NPK_STABILIZE_MS     10000UL   // A2 HIGH -> wait this long before Modbus request
#define DS18B20_WAIT_MS        800UL   // conversion time

// -------- Watchdog --------
// 8 s is the ATmega328P's longest WDT interval. We use it both as the sleep
// tick (LowPower.powerDown(SLEEP_8S, ...)) and as the panic timer during
// active phases. Any hung sensor read that runs longer than 8 s reboots the
// MCU cleanly rather than leaving a buried node dead in the field.
#define WDT_TIMEOUT_CODE     WDTO_8S

// -------- NPK sensor (RS485 Modbus RTU, 9600 8N1) --------
// Query reads 7 holding registers from slave 0x01.
#define NPK_RESPONSE_LEN     19
#define NPK_MODBUS_TIMEOUT_MS  1500UL
// Empirically the JXCT probe drops ~5-10% of Modbus replies. Retry up to
// NPK_RETRY_ATTEMPTS-1 times before giving up and setting NOK=0. Backend
// short-circuits NPK-derived Reading fields to None on NOK=0 (Round 16).
#define NPK_RETRY_ATTEMPTS      3
#define NPK_RETRY_GAP_MS      300UL

// -------- LED status codes --------
// One post-TX blink pattern tells field ops what happened this cycle without
// a laptop. Solid ON during LoRa TX; then:
//   1 short blink  = full success (TX OK + NPK OK)
//   2 short blinks = TX OK but NPK failed this cycle
//   3 short blinks = LoRa TX failed
#define LED_BLINK_MS          150UL
#define LED_BLINK_GAP_MS      150UL

// -------- Battery divider (raw ADC only — no conversion here) --------
// Divider is 220k + 100k on A1. Backend applies:
//   voltage = adc * (VREF / 1023.0) * ((220e3 + 100e3) / 100e3)
//           = adc * (3.3 / 1023.0) * 3.2
// but firmware sends raw ADC only.

#endif // SUB_NODE_CONFIG_H
