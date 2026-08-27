/*
 * VIRAAI Sub Node — Full Production Firmware
 * ==========================================
 * Target: ATmega328P @ 8 MHz, 3.3 V logic (MiniCore / USBasp)
 *
 * Reads all field sensors and transmits RAW values over LoRa 433 MHz to the
 * Main Node. Server-side does all calibration. Firmware does no unit
 * conversion beyond what the sensor natively provides — soil / battery /
 * pressure are raw ADC (0–1023); flow is a pulse counter; NPK values are
 * the raw 16-bit Modbus register readings.
 *
 * Wire format (single-line CSV over LoRa, keys ≤ 5 chars for airtime):
 *
 *   NODE=<id>,SEQ=<n>,SOIL=<0-1023>,BAT=<0-1023>,PRESS=<0-1023>,
 *   FLOW=<pulses_this_cycle>,FTOT=<total_pulses_since_boot>,
 *   DST=<°C|NAN>,NOK=<0|1>,NT=<int>,NM=<int>,EC=<int>,PH=<int>,
 *   N=<int>,P=<int>,K=<int>,FW=<firmware_version>
 *
 * `NOK=0` means the NPK Modbus read failed; NT..K are then whatever the last
 * successful read left in the registers (or zero on first-boot failure).
 *
 * Pin map (see sub_node_config.h notes):
 *   D2  = LoRa DIO0
 *   D3  = STATUS_LED
 *   D4  = DS18B20 OneWire
 *   D6  = RS485 RX (SoftwareSerial)
 *   D7  = RS485 TX (SoftwareSerial)
 *   D8  = LoRa RST
 *   D9  = Flow-sensor pulse input (INPUT_PULLUP, polled)
 *   D10 = LoRa NSS
 *   A0  = Soil moisture (raw ADC)
 *   A1  = Battery voltage (raw ADC via 220k+100k divider)
 *   A2  = IRLZ44N gate for NPK 12 V rail (HIGH = powered)
 *   A3  = Pressure transducer (raw ADC)
 *
 * NPK power sequence: A2 HIGH → wait NPK_STABILIZE_MS (10 s empirical) →
 * Modbus request → A2 LOW.
 *
 * RAM discipline:
 *   Every Serial string uses F(...) so it lives in flash.
 *   No String objects — everything is char[] with snprintf.
 */

#include <SPI.h>
#include <LoRa.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <SoftwareSerial.h>
#include <avr/wdt.h>
#include <avr/interrupt.h>
#include <util/atomic.h>
// Rocket Scream's LowPower library. Install via Arduino Library Manager
// ("Low-Power" by Rocket Scream Electronics) or add to platformio.ini as
//   lib_deps = rocketscream/Low-Power
#include <LowPower.h>

#include "sub_node_config.h"

// ====================================================
// PIN DEFINITIONS
// ====================================================
#define LORA_DIO0      2
#define STATUS_LED     3
#define ONE_WIRE_BUS   4
#define RS485_RX       6
#define RS485_TX       7
#define LORA_RST       8
#define FLOW_PIN       9
#define LORA_NSS       10
#define SOIL_PIN       A0
#define BATTERY_PIN    A1
#define POWER_CONTROL  A2
#define PRESSURE_PIN   A3

// ====================================================
// OBJECTS
// ====================================================
OneWire            oneWire(ONE_WIRE_BUS);
DallasTemperature  dsSensors(&oneWire);
SoftwareSerial     npkSerial(RS485_RX, RS485_TX);

// ====================================================
// STATE (raw values only; no calibration applied)
// ====================================================
uint32_t g_seq             = 0;         // packet sequence counter
// Flow counters are updated from BOTH poll code (active phase) and PCINT0_vect
// (during LowPower sleep). `volatile` + ATOMIC_BLOCK guards for multi-byte
// reads elsewhere in the file.
volatile uint32_t g_flowTotal     = 0;  // total pulses since boot
volatile uint16_t g_flowThisCycle = 0;  // pulses counted since last TX
volatile bool     g_flowLastLevel = HIGH;

int      g_soilAdc         = 0;
int      g_batAdc          = 0;
int      g_pressAdc        = 0;
float    g_dsTempC         = NAN;

// NPK retry accounting (this cycle only) — surfaced as sub_node_fw is already
// full, so we just log this. If retries become interesting to ops we'll add
// a CSV field.
uint8_t  g_npkRetriesThisCycle = 0;

// Actual wall-clock ms since the previous LoRa TX. Used to compute the flow
// window on the backend (WDT tick RC is ±10-15%, so this can drift vs the
// nominal CYCLE_PERIOD_MS). Set at boot to 0 which the backend treats as
// "unknown, discard flow rate this cycle".
uint32_t g_lastTxMs         = 0;
uint32_t g_windowMs         = 0;

// NPK — retained across cycles so consumers see the last-known-good if a
// read fails once. NOK flag tells the backend which values are current.
bool     g_npkOk           = false;
int16_t  g_npkTempRaw      = 0;   // register /10 → °C server-side
int16_t  g_npkMoistRaw     = 0;   // register /10 → %  server-side
int16_t  g_npkEc           = 0;   // µS/cm (sensor-native units)
int16_t  g_npkPhRaw        = 0;   // register /100 → pH server-side
int16_t  g_npkN            = 0;   // mg/kg
int16_t  g_npkP            = 0;   // mg/kg
int16_t  g_npkK            = 0;   // mg/kg

const byte NPK_QUERY_FRAME[] = { 0x01, 0x03, 0x00, 0x00, 0x00, 0x07, 0x04, 0x08 };

// ====================================================
// CRC16 (Modbus)
// ====================================================
uint16_t crc16(const byte* buf, uint16_t len) {
  uint16_t crc = 0xFFFF;
  for (uint16_t i = 0; i < len; i++) {
    crc ^= (uint16_t)buf[i];
    for (byte b = 0; b < 8; b++) {
      if (crc & 0x0001) { crc >>= 1; crc ^= 0xA001; }
      else              { crc >>= 1; }
    }
  }
  return crc;
}

// ====================================================
// FLOW — dual-mode: PCINT during sleep, polled during active phase
// ====================================================
// D9 = PB1 on the ATmega328P (PCINT1 in the PCINT0 group, controlled by
// PCIE0 in PCICR + PCINT1 bit in PCMSK0). PCINT lets us keep counting flow
// pulses while the MCU is in LowPower.powerDown() between cycles — critical
// now that cycles are 5 min apart and an irrigation pump can emit 1500+
// pulses per window.
//
// SoftwareSerial uses PCINT2 (PORT D) for its RX pin (D6). No conflict with
// PCINT0 group.

ISR(PCINT0_vect) {
  bool now = (PINB & (1 << PB1)) ? HIGH : LOW;
  if (now == LOW && g_flowLastLevel == HIGH) {
    g_flowThisCycle++;
    g_flowTotal++;
  }
  g_flowLastLevel = now;
}

static inline void enableFlowPcint() {
  PCMSK0 |= (1 << PCINT1);
  PCICR  |= (1 << PCIE0);
}

static inline void disableFlowPcint() {
  PCICR  &= ~(1 << PCIE0);
  PCMSK0 &= ~(1 << PCINT1);
}

// Polling path — used during the active phase only. Same edge detection as
// the ISR; the shared `volatile bool g_flowLastLevel` prevents double-count
// when a pulse arrives right at the ISR/poll handoff.
inline void pollFlow() {
  bool now = digitalRead(FLOW_PIN);
  if (now == LOW && g_flowLastLevel == HIGH) {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
      g_flowThisCycle++;
      g_flowTotal++;
    }
  }
  g_flowLastLevel = now;
}

// Blocking delay that polls flow AND kicks the WDT. Used during active
// phases (DS18 conversion wait, NPK stabilise wait) where the MCU stays
// awake.
static void delayWithFlow(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    pollFlow();
    wdt_reset();
  }
}

// ====================================================
// SLEEP — deep-sleep in 8 s chunks, PCINT-wakeable
// ====================================================
// LowPower.powerDown(SLEEP_8S, ADC_OFF, BOD_OFF) draws ~0.3 uA nominal on
// bare ATmega328P + external clock. A PCINT (flow pulse) wakes early, runs
// the ISR, then falls back into powerDown() on the next iteration — we
// accumulate wall time via elapsed millis() readings taken pre/post the
// full sleep block, since millis() itself pauses during powerDown().
//
// We *approximate* elapsed by counting the number of full 8 s sleeps.
// This is intentionally low-precision — the actual wall-time is what we
// emit as WIN=<seconds> in the CSV, and the backend uses that for flow.
static void deepSleepMs(unsigned long targetMs) {
  enableFlowPcint();
  unsigned long slept = 0;
  while (slept < targetMs) {
    wdt_reset();
    LowPower.powerDown(SLEEP_8S, ADC_OFF, BOD_OFF);
    slept += 8000UL;   // nominal; real value is +/-10% (WDT RC)
  }
  disableFlowPcint();
}

// ====================================================
// SENSOR READS — all RAW; no unit conversion
// ====================================================
static void readBatteryAdc() {
  long sum = 0;
  for (byte i = 0; i < 10; i++) {
    sum += analogRead(BATTERY_PIN);
    delay(2);
  }
  g_batAdc = (int)(sum / 10);
}

static void readPressureAdc() {
  g_pressAdc = analogRead(PRESSURE_PIN);
}

static void readSoilAdc() {
  g_soilAdc = analogRead(SOIL_PIN);
}

static void startDs18() {
  dsSensors.requestTemperatures();
}

static void readDs18() {
  float t = dsSensors.getTempCByIndex(0);
  if (t == DEVICE_DISCONNECTED_C) {
    g_dsTempC = NAN;
  } else {
    g_dsTempC = t;
  }
}

// ====================================================
// NPK READ (Modbus RTU over SoftwareSerial)
// ====================================================
// One Modbus round-trip attempt. Returns true on full-length CRC-valid
// response; leaves register globals untouched on failure so the caller
// (readNpk) can retry.
static bool readNpkAttempt() {
  // Drain any garbage from previous power cycles / previous attempt.
  while (npkSerial.available()) { npkSerial.read(); }
  wdt_reset();

  npkSerial.write(NPK_QUERY_FRAME, sizeof(NPK_QUERY_FRAME));
  npkSerial.flush();

  byte    resp[NPK_RESPONSE_LEN];
  uint8_t received = 0;
  unsigned long start = millis();
  while (millis() - start < NPK_MODBUS_TIMEOUT_MS) {
    pollFlow();
    wdt_reset();
    while (npkSerial.available() && received < NPK_RESPONSE_LEN) {
      resp[received++] = npkSerial.read();
    }
    if (received >= NPK_RESPONSE_LEN) break;
  }

  if (received < NPK_RESPONSE_LEN) {
    Serial.print(F("NPK: short read, bytes="));
    Serial.println(received);
    return false;
  }
  // Header check: slave 0x01, function 0x03, byte count 0x0E (14 = 7×2).
  if (resp[0] != 0x01 || resp[1] != 0x03 || resp[2] != 0x0E) {
    Serial.println(F("NPK: bad Modbus header"));
    return false;
  }
  // CRC check (bytes 0..16, expected CRC in 17..18, low byte first).
  uint16_t rxCrc   = (uint16_t)resp[17] | ((uint16_t)resp[18] << 8);
  uint16_t calcCrc = crc16(resp, 17);
  if (rxCrc != calcCrc) {
    Serial.println(F("NPK: CRC fail"));
    return false;
  }
  // Registers — send raw ints. Backend applies /10 or /100 conversions.
  g_npkTempRaw  = (int16_t)(((uint16_t)resp[3]  << 8) | resp[4]);
  g_npkMoistRaw = (int16_t)(((uint16_t)resp[5]  << 8) | resp[6]);
  g_npkEc       = (int16_t)(((uint16_t)resp[7]  << 8) | resp[8]);
  g_npkPhRaw    = (int16_t)(((uint16_t)resp[9]  << 8) | resp[10]);
  g_npkN        = (int16_t)(((uint16_t)resp[11] << 8) | resp[12]);
  g_npkP        = (int16_t)(((uint16_t)resp[13] << 8) | resp[14]);
  g_npkK        = (int16_t)(((uint16_t)resp[15] << 8) | resp[16]);
  return true;
}

// Retry wrapper. Sets g_npkOk / g_npkRetriesThisCycle. Backend still treats
// NOK=0 as "NPK data invalid this cycle" via the Round-16 short-circuit.
static void readNpk() {
  g_npkOk = false;
  g_npkRetriesThisCycle = 0;
  for (uint8_t attempt = 0; attempt < NPK_RETRY_ATTEMPTS; attempt++) {
    if (readNpkAttempt()) {
      g_npkOk = true;
      Serial.print(F("NPK: OK (attempt "));
      Serial.print(attempt + 1);
      Serial.println(F(")"));
      return;
    }
    g_npkRetriesThisCycle = attempt + 1;
    delayWithFlow(NPK_RETRY_GAP_MS);
  }
  Serial.print(F("NPK: FAIL after "));
  Serial.print(NPK_RETRY_ATTEMPTS);
  Serial.println(F(" attempts"));
}

// ====================================================
// LoRa TX
// ====================================================
// Emit a single CSV line. Total length target: <= 200 bytes (SX1278 cap 255).
// Any float uses fixed 2-decimal formatting via dtostrf.
//
// WIN=<seconds> is the wall-clock window this packet covers — the time
// since the previous successful TX, in seconds. WIN=0 on the first cycle
// after boot signals "unknown window, discard flow rate this cycle" to
// the backend (the totalizer FTOT is still authoritative).
static bool sendLoRa() {
  char pkt[220];
  char dsBuf[10];

  if (isnan(g_dsTempC)) {
    strcpy(dsBuf, "NAN");
  } else {
    dtostrf(g_dsTempC, 0, 2, dsBuf);
  }

  // Atomic snapshot of the (volatile, PCINT-mutated) flow counters.
  uint16_t flowThis;
  uint32_t flowTot;
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    flowThis = g_flowThisCycle;
    flowTot  = g_flowTotal;
  }
  uint32_t winSec = g_windowMs / 1000UL;

  int n = snprintf(pkt, sizeof(pkt),
    "NODE=%s,SEQ=%lu,WIN=%lu,SOIL=%d,BAT=%d,PRESS=%d,FLOW=%u,FTOT=%lu,DST=%s,"
    "NOK=%d,NT=%d,NM=%d,EC=%d,PH=%d,N=%d,P=%d,K=%d,FW=%s",
    NODE_ID,
    (unsigned long)g_seq,
    (unsigned long)winSec,
    g_soilAdc,
    g_batAdc,
    g_pressAdc,
    (unsigned)flowThis,
    (unsigned long)flowTot,
    dsBuf,
    g_npkOk ? 1 : 0,
    (int)g_npkTempRaw,
    (int)g_npkMoistRaw,
    (int)g_npkEc,
    (int)g_npkPhRaw,
    (int)g_npkN,
    (int)g_npkP,
    (int)g_npkK,
    FIRMWARE_VERSION);

  if (n < 0 || n >= (int)sizeof(pkt)) {
    Serial.println(F("LoRa: payload overflow"));
    return false;
  }

  Serial.print(F("TX: "));
  Serial.println(pkt);

  if (!LoRa.beginPacket()) {
    Serial.println(F("LoRa: beginPacket failed"));
    return false;
  }
  LoRa.write((const uint8_t*)pkt, (size_t)n);
  int rc = LoRa.endPacket();
  return rc == 1;
}

// ====================================================
// LED status codes
// ====================================================
static void blinkN(uint8_t n) {
  for (uint8_t i = 0; i < n; i++) {
    digitalWrite(STATUS_LED, HIGH); delay(LED_BLINK_MS);
    digitalWrite(STATUS_LED, LOW);  delay(LED_BLINK_GAP_MS);
  }
}

// ====================================================
// SETUP
// ====================================================
void setup() {
  // WDT must be disabled during setup while I2C / SPI / SoftwareSerial come
  // up — sensor init can take longer than the WDT interval. We re-enable at
  // the end of setup and reset at every safe checkpoint.
  wdt_disable();

  pinMode(STATUS_LED,    OUTPUT); digitalWrite(STATUS_LED,    LOW);
  pinMode(POWER_CONTROL, OUTPUT); digitalWrite(POWER_CONTROL, LOW);  // NPK OFF at boot
  pinMode(FLOW_PIN,      INPUT_PULLUP);

  Serial.begin(9600);
  npkSerial.begin(9600);
  dsSensors.begin();
  dsSensors.setWaitForConversion(false);

  LoRa.setPins(LORA_NSS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(LORA_FREQUENCY_HZ)) {
    Serial.println(F("LoRa: init FAIL — halted"));
    // Fast blink forever; WDT will not save us here because init failure
    // usually means wiring is wrong and no cycle will ever succeed.
    while (1) {
      digitalWrite(STATUS_LED, HIGH); delay(150);
      digitalWrite(STATUS_LED, LOW);  delay(150);
    }
  }
  LoRa.setTxPower(LORA_TX_POWER_DBM);
  LoRa.setSpreadingFactor(LORA_SPREADING_FACTOR);
  LoRa.setSignalBandwidth(LORA_BANDWIDTH_HZ);
  LoRa.setCodingRate4(LORA_CODING_RATE);
  LoRa.enableCrc();

  g_flowLastLevel = digitalRead(FLOW_PIN);

  // Startup LED blink 3× so field ops know the board is alive.
  for (byte i = 0; i < 3; i++) {
    digitalWrite(STATUS_LED, HIGH); delay(150);
    digitalWrite(STATUS_LED, LOW);  delay(150);
  }

  Serial.println();
  Serial.println(F("================================"));
  Serial.println(F("VIRAAI Sub Node — RAW variant"));
  Serial.print(F("NODE_ID = "));  Serial.println(NODE_ID);
  Serial.print(F("FW      = "));  Serial.println(FIRMWARE_VERSION);
  Serial.println(F("CADENCE = 5 min (LowPower deep sleep)"));
  Serial.println(F("LoRa    = 433 MHz SF7 BW125k CR4/5"));
  Serial.println(F("================================"));

  // Arm the WDT now that all init is complete. Every long-running block
  // (delayWithFlow, deepSleepMs, readNpkAttempt) calls wdt_reset() at
  // safe checkpoints; a hung sensor read reboots the MCU cleanly.
  wdt_enable(WDT_TIMEOUT_CODE);
}

// ====================================================
// LOOP — one full cycle per iteration
// ====================================================
// Timing (5-min cadence):
//   [active ~15-20 s]  read all sensors + NPK (10s stabilise) + LoRa TX
//   [sleep ~4:40]      LowPower.powerDown in 8s chunks; PCINT keeps counting
//                      flow pulses; WDT resets each chunk.
void loop() {
  wdt_reset();
  g_seq++;

  // Snapshot cycle-start millis BEFORE the sensor reads so `g_windowMs`
  // measures the actual gap from TX to TX (not from cycle-start to TX).
  // On the first cycle after boot g_lastTxMs is 0, and we deliberately
  // stamp g_windowMs=0 below — the backend contract is "WIN=0 means the
  // window is unknown; discard flow rate for this row".
  unsigned long cycleStart = millis();

  // Reset per-cycle flow counter under an atomic block (the PCINT could
  // otherwise fire between the two writes and lose a count).
  ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
    g_flowThisCycle = 0;
  }

  Serial.println();
  Serial.print(F("---- CYCLE "));
  Serial.print(g_seq);
  Serial.println(F(" ----"));

  // ---- Basic sensor reads (raw ADC / DS18B20 native °C) ----
  startDs18();
  readSoilAdc();
  readBatteryAdc();
  readPressureAdc();

  // Wait for DS18B20 conversion, polling flow + resetting WDT.
  delayWithFlow(DS18B20_WAIT_MS);
  readDs18();

  Serial.print(F("SOIL_ADC=")); Serial.println(g_soilAdc);
  Serial.print(F("BAT_ADC="));  Serial.println(g_batAdc);
  Serial.print(F("PRESS_ADC=")); Serial.println(g_pressAdc);
  Serial.print(F("DS_C="));
  if (isnan(g_dsTempC)) Serial.println(F("NAN"));
  else                  Serial.println(g_dsTempC, 2);

  // ---- NPK sequence ----
  digitalWrite(POWER_CONTROL, HIGH);
  Serial.println(F("NPK: powered ON, stabilizing 10s..."));
  delayWithFlow(NPK_STABILIZE_MS);
  readNpk();
  digitalWrite(POWER_CONTROL, LOW);
  Serial.println(F("NPK: powered OFF"));

  // ---- Compute the wall-clock window covered by this packet ----
  // TX-to-TX window is what backend needs for flow rate.
  unsigned long nowMs = millis();
  if (g_lastTxMs == 0) {
    g_windowMs = 0;   // first cycle after boot -> backend discards rate
  } else {
    g_windowMs = nowMs - g_lastTxMs;
  }

  // ---- LoRa TX ----
  digitalWrite(STATUS_LED, HIGH);
  bool loraOk = sendLoRa();
  digitalWrite(STATUS_LED, LOW);
  Serial.println(loraOk ? F("LoRa TX: OK") : F("LoRa TX: FAIL"));

  if (loraOk) {
    g_lastTxMs = millis();
  }

  // ---- Post-TX status blink pattern ----
  // 1 blink = full success; 2 = NPK failed but TX OK; 3 = TX failed.
  if (!loraOk)       blinkN(3);
  else if (!g_npkOk) blinkN(2);
  else               blinkN(1);

  // ---- Deep sleep until the next cycle window ----
  // Target the *remaining* time to hit CYCLE_PERIOD_MS end-to-end (cycle
  // start to cycle start). If we somehow overran (unlikely — active is
  // ~15 s), sleep the WDT minimum tick to guarantee at least one WDT reset.
  unsigned long activeMs = millis() - cycleStart;
  unsigned long sleepMs  = (activeMs >= CYCLE_PERIOD_MS)
                             ? 8000UL
                             : (CYCLE_PERIOD_MS - activeMs);
  Serial.print(F("SLEEP="));
  Serial.print(sleepMs / 1000UL);
  Serial.println(F("s"));
  Serial.flush();     // finish UART before power-down
  deepSleepMs(sleepMs);
}
