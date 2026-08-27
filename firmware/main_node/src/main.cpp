/*
 * VIRAAI Main Node — Full Production Firmware (RAW variant)
 * =========================================================
 * Target: ESP32-WROOM-32
 *
 * Responsibilities:
 *   1. Bring up own sensors: BME280 (I2C), INA219 (I2C), DS3231 RTC (I2C),
 *      tipping-bucket rain gauge (GPIO ISR), anemometer (GPIO ISR),
 *      wind vane (ADC), MicroSD card (bring-up verify only).
 *   2. Bring up SIMCom A7672S: SIM check → data attach (Airtel APN) →
 *      NTP sync → MQTT service start → TLS context 0 → MQTT client acquire
 *      → CMQTTCONNECT.  This uses the exact AT sequence the hardware team
 *      verified working on 2026-08-26.
 *   3. Loop: poll LoRa for CSV frames from Sub Node → parse RAW values →
 *      map NODE_ID to PLOT_ID → read own weather sensors → build JSON with
 *      raw_readings (Sub Node) + master_readings (Main Node) → publish to
 *      MQTT on `agro/v2/<tenant>/<farm>/<sub_node_id>/telemetry`.
 *   4. Reconnect MQTT on failure. Log every step to Serial @ 115200.
 *
 * All calibration and unit conversion is done SERVER-SIDE. Firmware sends
 * raw sensor outputs. Two exceptions where the sensor's calibration is
 * intrinsic and required to get any usable reading at all:
 *   - BME280: uses per-chip calibration coefficients (baked into chip).
 *   - INA219: needs the shunt value (0.1 Ω) to convert current.
 * Those are considered part of the sensor, not "user calibration".
 *
 * Pin map (see include/pilot_config.h for behavioural constants):
 *   GPIO 14 = MODEM_RX   (A7672S TX → ESP32)
 *   GPIO 33 = MODEM_TX   (ESP32 → A7672S RX)
 *   GPIO  5 = LORA_CS
 *   GPIO 32 = LORA_RST
 *   GPIO 27 = LORA_DIO0
 *   GPIO 13 = SD_CS
 *   GPIO 16 = RAIN_PIN     (tipping bucket, FALLING ISR, 200 ms debounce)
 *   GPIO 17 = WIND_SPD_PIN (anemometer,  FALLING ISR, 5 ms  debounce)
 *   GPIO 34 = WIND_DIR_PIN (wind vane analog input, 0-3.3 V full-scale)
 *   GPIO 21/22 = I2C SDA/SCL (BME280, INA219, DS3231)
 *   GPIO 18/19/23 = SPI SCK/MISO/MOSI (LoRa + SD)
 */

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <LoRa.h>
#include <math.h>
#include <string.h>
#include <stdio.h>
#include <esp_task_wdt.h>

#include "pilot_config.h"

// SD availability flag — set by SD.begin() in setup. Outbox writes and
// boot-log writes silently no-op when SD didn't come up.
static bool g_sdOk = false;

// ================================================================
// PIN DEFINES
// ================================================================
#define MODEM_RX_PIN     14
#define MODEM_TX_PIN     33
#define LORA_CS_PIN       5
#define LORA_RST_PIN     32
#define LORA_DIO0_PIN    27
#define SD_CS_PIN        13
#define RAIN_PIN         16
#define WIND_SPD_PIN     17
#define WIND_DIR_PIN     34
#define I2C_SDA          21
#define I2C_SCL          22
#define SPI_SCK          18
#define SPI_MISO         19
#define SPI_MOSI         23

HardwareSerial modemSerial(2);

// ================================================================
// ISR-DRIVEN COUNTERS (rain + wind pulses)
// ================================================================
volatile unsigned long g_rainPulsesTotal = 0;
volatile unsigned long g_rainLastMs      = 0;
volatile unsigned long g_windPulsesTotal = 0;
volatile unsigned long g_windLastUs      = 0;

void IRAM_ATTR rainISR() {
  unsigned long now = millis();
  if (now - g_rainLastMs >= 200) {   // 200 ms debounce
    g_rainPulsesTotal++;
    g_rainLastMs = now;
  }
}

void IRAM_ATTR windISR() {
  unsigned long now = micros();
  if (now - g_windLastUs >= 5000) {  // 5 ms debounce
    g_windPulsesTotal++;
    g_windLastUs = now;
  }
}

// Snapshot helpers — copy-and-clear atomically w.r.t. the ISR.
static void snapshotRainWindDelta(unsigned long& rainDelta,
                                  unsigned long& windDelta) {
  static unsigned long lastRain = 0;
  static unsigned long lastWind = 0;
  noInterrupts();
  unsigned long rain = g_rainPulsesTotal;
  unsigned long wind = g_windPulsesTotal;
  interrupts();
  rainDelta = rain - lastRain;
  windDelta = wind - lastWind;
  lastRain  = rain;
  lastWind  = wind;
}

// ================================================================
// I2C HELPERS
// ================================================================
static bool i2cPresent(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

static void scanI2C() {
  Serial.println(F("I2C scan:"));
  int found = 0;
  for (uint8_t a = 1; a < 127; a++) {
    if (i2cPresent(a)) {
      Serial.printf("  0x%02X\n", a);
      found++;
    }
  }
  Serial.printf("  (%d device(s) found)\n", found);
}

// ================================================================
// BME280 DRIVER (direct-register)
// ================================================================
struct Bme280Cal {
  uint16_t T1; int16_t T2, T3;
  uint16_t P1; int16_t P2, P3, P4, P5, P6, P7, P8, P9;
  uint8_t  H1;  int16_t H2; uint8_t H3;
  int16_t  H4, H5; int8_t H6;
};

static uint8_t     g_bmeAddr = 0;
static Bme280Cal   g_bmeCal;
static int32_t     g_bmeTfine = 0;

static uint8_t bmeRead8(uint8_t reg) {
  Wire.beginTransmission(g_bmeAddr);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(g_bmeAddr, (uint8_t)1);
  return Wire.available() ? Wire.read() : 0;
}

static uint16_t bmeRead16LE(uint8_t reg) {
  Wire.beginTransmission(g_bmeAddr);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(g_bmeAddr, (uint8_t)2);
  if (Wire.available() < 2) return 0;
  uint8_t lo = Wire.read();
  uint8_t hi = Wire.read();
  return ((uint16_t)hi << 8) | lo;
}

static int16_t bmeReadS16LE(uint8_t reg) {
  return (int16_t)bmeRead16LE(reg);
}

static void bmeWrite8(uint8_t reg, uint8_t v) {
  Wire.beginTransmission(g_bmeAddr);
  Wire.write(reg);
  Wire.write(v);
  Wire.endTransmission();
}

static void bmeReadCalibration() {
  g_bmeCal.T1 = bmeRead16LE(0x88);
  g_bmeCal.T2 = bmeReadS16LE(0x8A);
  g_bmeCal.T3 = bmeReadS16LE(0x8C);
  g_bmeCal.P1 = bmeRead16LE(0x8E);
  g_bmeCal.P2 = bmeReadS16LE(0x90);
  g_bmeCal.P3 = bmeReadS16LE(0x92);
  g_bmeCal.P4 = bmeReadS16LE(0x94);
  g_bmeCal.P5 = bmeReadS16LE(0x96);
  g_bmeCal.P6 = bmeReadS16LE(0x98);
  g_bmeCal.P7 = bmeReadS16LE(0x9A);
  g_bmeCal.P8 = bmeReadS16LE(0x9C);
  g_bmeCal.P9 = bmeReadS16LE(0x9E);
  g_bmeCal.H1 = bmeRead8(0xA1);
  g_bmeCal.H2 = bmeReadS16LE(0xE1);
  g_bmeCal.H3 = bmeRead8(0xE3);
  uint8_t e4 = bmeRead8(0xE4);
  uint8_t e5 = bmeRead8(0xE5);
  uint8_t e6 = bmeRead8(0xE6);
  g_bmeCal.H4 = ((int16_t)(int8_t)e4 << 4) | (e5 & 0x0F);
  g_bmeCal.H5 = ((int16_t)(int8_t)e6 << 4) | (e5 >> 4);
  g_bmeCal.H6 = (int8_t)bmeRead8(0xE7);
}

static bool bmeInit() {
  if      (i2cPresent(0x76)) g_bmeAddr = 0x76;
  else if (i2cPresent(0x77)) g_bmeAddr = 0x77;
  else return false;

  uint8_t chip = bmeRead8(0xD0);
  if (chip != 0x60) {
    Serial.printf("BME280: unexpected chip id 0x%02X\n", chip);
    return false;
  }
  bmeWrite8(0xF2, 0x01);   // hum ×1
  bmeWrite8(0xF4, 0x27);   // temp ×1, press ×1, normal
  bmeWrite8(0xF5, 0xA0);   // standby + filter
  bmeReadCalibration();
  return true;
}

static bool bmeReadRaw(int32_t& adcT, int32_t& adcP, int32_t& adcH) {
  Wire.beginTransmission(g_bmeAddr);
  Wire.write(0xF7);
  Wire.endTransmission(false);
  Wire.requestFrom(g_bmeAddr, (uint8_t)8);
  if (Wire.available() < 8) return false;
  adcP = ((uint32_t)Wire.read() << 12) | ((uint32_t)Wire.read() << 4) | (Wire.read() >> 4);
  adcT = ((uint32_t)Wire.read() << 12) | ((uint32_t)Wire.read() << 4) | (Wire.read() >> 4);
  adcH = ((uint16_t)Wire.read() << 8) | Wire.read();
  return true;
}

static float bmeTemperature(int32_t adcT) {
  int32_t v1 = ((((adcT >> 3) - ((int32_t)g_bmeCal.T1 << 1))) * (int32_t)g_bmeCal.T2) >> 11;
  int32_t v2 = (((((adcT >> 4) - (int32_t)g_bmeCal.T1) *
                 ((adcT >> 4) - (int32_t)g_bmeCal.T1)) >> 12) * (int32_t)g_bmeCal.T3) >> 14;
  g_bmeTfine = v1 + v2;
  return ((g_bmeTfine * 5 + 128) >> 8) / 100.0f;
}

static float bmePressurePa(int32_t adcP) {
  int64_t v1 = (int64_t)g_bmeTfine - 128000;
  int64_t v2 = v1 * v1 * (int64_t)g_bmeCal.P6;
  v2 += ((v1 * (int64_t)g_bmeCal.P5) << 17);
  v2 += ((int64_t)g_bmeCal.P4) << 35;
  v1 = ((v1 * v1 * (int64_t)g_bmeCal.P3) >> 8) + ((v1 * (int64_t)g_bmeCal.P2) << 12);
  v1 = ((((int64_t)1 << 47) + v1) * (int64_t)g_bmeCal.P1) >> 33;
  if (v1 == 0) return 0.0f;
  int64_t p = 1048576 - adcP;
  p = (((p << 31) - v2) * 3125) / v1;
  v1 = ((int64_t)g_bmeCal.P9 * (p >> 13) * (p >> 13)) >> 25;
  v2 = ((int64_t)g_bmeCal.P8 * p) >> 19;
  p = ((p + v1 + v2) >> 8) + ((int64_t)g_bmeCal.P7 << 4);
  return (float)p / 256.0f;   // Pa
}

static float bmeHumidity(int32_t adcH) {
  int32_t v = g_bmeTfine - 76800;
  v = (((((adcH << 14) - ((int32_t)g_bmeCal.H4 << 20) - ((int32_t)g_bmeCal.H5 * v)) + 16384) >> 15) *
       (((((((v * (int32_t)g_bmeCal.H6) >> 10) *
            (((v * (int32_t)g_bmeCal.H3) >> 11) + 32768)) >> 10) + 2097152) *
          (int32_t)g_bmeCal.H2 + 8192) >> 14));
  v = v - (((((v >> 15) * (v >> 15)) >> 7) * (int32_t)g_bmeCal.H1) >> 4);
  if (v < 0) v = 0;
  if (v > 419430400) v = 419430400;
  return (v >> 12) / 1024.0f;
}

static bool bmeRead(float& tempC, float& humidityPct, float& pressurePa) {
  int32_t adcT, adcP, adcH;
  if (!bmeReadRaw(adcT, adcP, adcH)) return false;
  tempC       = bmeTemperature(adcT);
  pressurePa  = bmePressurePa(adcP);
  humidityPct = bmeHumidity(adcH);
  return true;
}

// ================================================================
// INA219 DRIVER
// ================================================================
#define INA219_ADDR 0x40

static uint16_t inaRead16(uint8_t reg) {
  Wire.beginTransmission(INA219_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)INA219_ADDR, (uint8_t)2);
  if (Wire.available() < 2) return 0;
  return ((uint16_t)Wire.read() << 8) | Wire.read();
}

static void inaWrite16(uint8_t reg, uint16_t v) {
  Wire.beginTransmission(INA219_ADDR);
  Wire.write(reg);
  Wire.write(v >> 8);
  Wire.write(v & 0xFF);
  Wire.endTransmission();
}

static bool inaInit() {
  if (!i2cPresent(INA219_ADDR)) return false;
  inaWrite16(0x00, 0x399F);   // Bus 32 V, gain /8, 12-bit ADC, continuous
  return true;
}

static void inaRead(float& busV, float& currentMa) {
  uint16_t bus   = inaRead16(0x02);
  int16_t  shunt = (int16_t)inaRead16(0x01);
  busV       = (bus >> 3) * 0.004f;   // 4 mV/bit
  float mV   = shunt * 0.01f;         // 10 µV/bit
  currentMa  = mV / 0.1f;             // 0.1 Ω shunt
}

// ================================================================
// DS3231 RTC — used as a fallback if the modem NTP path is down.
// ================================================================
static uint8_t bcdToDec(uint8_t v) { return ((v >> 4) * 10) + (v & 0x0F); }
static uint8_t decToBcd(uint8_t v) { return (uint8_t)(((v / 10) << 4) | (v % 10)); }

// Reject impossible years so we never emit e.g. 2070-01-01. Backend has a
// safety net (broker-side clock-skew normalization) but firmware is the
// first line of defence — bad timestamps never leave the device.
static inline bool isPlausibleYear(int y) {
  return y >= TIME_MIN_YEAR && y <= TIME_MAX_YEAR;
}

static bool ds3231Read(int& sec, int& min, int& hr,
                       int& day, int& month, int& year) {
  if (!i2cPresent(0x68)) return false;
  Wire.beginTransmission(0x68);
  Wire.write(0x00);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)0x68, (uint8_t)7);
  if (Wire.available() < 7) return false;
  sec   = bcdToDec(Wire.read() & 0x7F);
  min   = bcdToDec(Wire.read() & 0x7F);
  hr    = bcdToDec(Wire.read() & 0x3F);
  Wire.read();                       // day of week — skip
  day   = bcdToDec(Wire.read());
  month = bcdToDec(Wire.read());
  year  = 2000 + bcdToDec(Wire.read());
  return true;
}

// Write UTC time back to the DS3231. Called once per boot after NTP succeeds
// with a plausible year — RTC then becomes trustworthy for the rest of the
// deployment lifetime, including across power cycles where the modem may
// not immediately resync NTP.
static bool ds3231Write(int sec, int min, int hr,
                        int day, int month, int year) {
  if (!i2cPresent(0x68)) return false;
  if (year < 2000 || year > 2099) return false;
  Wire.beginTransmission(0x68);
  Wire.write((uint8_t)0x00);
  Wire.write(decToBcd((uint8_t)sec));
  Wire.write(decToBcd((uint8_t)min));
  Wire.write(decToBcd((uint8_t)hr));   // 24-hour mode (bit 6 = 0)
  Wire.write((uint8_t)0x01);           // day-of-week: unused, set to 1
  Wire.write(decToBcd((uint8_t)day));
  Wire.write(decToBcd((uint8_t)month));
  Wire.write(decToBcd((uint8_t)(year - 2000)));
  return Wire.endTransmission() == 0;
}

// ================================================================
// MODEM (A7672S) — LOW-LEVEL AT HELPERS
// ================================================================
static void modemFlush() {
  while (modemSerial.available()) modemSerial.read();
}

static String modemRead(uint32_t timeoutMs) {
  String r;
  r.reserve(256);
  uint32_t start = millis();
  uint32_t lastWdtReset = start;
  while (millis() - start < timeoutMs) {
    while (modemSerial.available()) {
      char c = (char)modemSerial.read();
      r += c;
      Serial.write(c);   // mirror to debug console
    }
    // Kick the WDT every 5 s during long AT waits (e.g., 30 s CMQTTCONNECT).
    if (millis() - lastWdtReset > 5000) {
      esp_task_wdt_reset();
      lastWdtReset = millis();
    }
    delay(1);
  }
  return r;
}

static bool modemSendExpect(const char* cmd, const char* expect, uint32_t timeoutMs) {
  modemFlush();
  modemSerial.print(cmd);
  modemSerial.print("\r\n");
  String r = modemRead(timeoutMs);
  return r.indexOf(expect) >= 0;
}

static String modemSendGet(const char* cmd, uint32_t timeoutMs) {
  modemFlush();
  modemSerial.print(cmd);
  modemSerial.print("\r\n");
  return modemRead(timeoutMs);
}

// ================================================================
// MODEM — BRING-UP, NTP, MQTT
// ================================================================
static bool modemBoot() {
  Serial.println(F("[modem] wake…"));
  for (int i = 0; i < BOOT_MODEM_RETRIES; i++) {
    if (modemSendExpect("AT", "OK", 1000)) return true;
    delay(500);
  }
  return false;
}

static bool modemDataAttach() {
  if (!modemSendExpect("AT+CPIN?", "READY", 3000)) {
    Serial.println(F("[modem] SIM not ready"));
    return false;
  }
  modemSendExpect("AT+CMEE=2", "OK", 2000);

  // Cleanup any previous MQTT / IP session (idempotent).
  modemSendExpect("AT+CMQTTDISC=0,120", "OK", 3000);
  modemSendExpect("AT+CMQTTREL=0",      "OK", 3000);
  modemSendExpect("AT+CMQTTSTOP",       "OK", 3000);
  modemSendExpect("AT+NETCLOSE",        "OK", 3000);
  delay(1000);

  char apnCmd[96];
  snprintf(apnCmd, sizeof(apnCmd), "AT+CGDCONT=1,\"IP\",\"%s\"", MODEM_APN);
  if (!modemSendExpect(apnCmd, "OK", 5000)) return false;

  char dnsCmd[96];
  snprintf(dnsCmd, sizeof(dnsCmd), "AT+CDNSCFG=\"%s\",\"%s\"", MODEM_DNS1, MODEM_DNS2);
  modemSendExpect(dnsCmd, "OK", 3000);

  if (!modemSendExpect("AT+NETOPEN", "+NETOPEN: 0", 15000)) {
    Serial.println(F("[modem] NETOPEN failed"));
    return false;
  }
  delay(1500);
  return true;
}

// Best-effort NTP sync via the modem. If it fails we still boot; the
// timestamp will fall back to the DS3231 (or the "none" sentinel — the
// backend's broker-side _normalize_clock_skew will rewrite that to
// server UTC and stamp validation_warn=true).
//
// When NTP does return a plausible year, we mirror the clock to the
// DS3231 so subsequent boots (or transient NTP outages) still produce
// a usable timestamp — the whole partition-router-miss problem is worst
// when NEITHER source is trustworthy.
static void modemNtpSync() {
  Serial.println(F("[modem] NTP sync…"));
  modemSendExpect("AT+CNTP=\"pool.ntp.org\",0,1,2", "OK", 3000);
  // Trigger the sync (some firmwares need a second call).
  modemSendGet("AT+CNTP", NTP_SYNC_TIMEOUT_MS);
  String r = modemSendGet("AT+CCLK?", 3000);
  if (r.indexOf("+CCLK:") < 0) {
    Serial.println(F("[modem] NTP sync: no CCLK response"));
    return;
  }
  // If the modem clock is now plausible, push it to the DS3231.
  syncRtcFromModemOnce();
}

// Time source resolved for the currently-being-built payload. Included in
// master_readings so the backend can distinguish a fresh NTP timestamp from
// an RTC fallback from a "we have no clock at all" sentinel.
enum TimeSource { TS_NONE = 0, TS_NTP = 1, TS_RTC = 2 };

static bool g_rtcSyncedFromNtp = false;

static const char* timeSourceLabel(TimeSource ts) {
  switch (ts) {
    case TS_NTP: return "ntp";
    case TS_RTC: return "rtc";
    default:     return "none";
  }
}

// Fetch current UTC from the modem's NTP-backed clock.
// A7672S CCLK format: +CCLK: "26/08/26,10:45:00+00".
//
// Uninitialised modems commonly return "70/01/01,..." (SIMCom epoch fallback)
// or "80/01/01,..." — which used to render as 2070-01-01 / 2080-01-01 and
// blow through the monthly-partitioned readings table server-side. We now
// reject any parsed year outside [TIME_MIN_YEAR, TIME_MAX_YEAR] and let the
// caller fall through to the DS3231.
//
// Returns empty string on parse failure or implausible year.
static String modemGetIsoUtc(int* outY = nullptr, int* outMo = nullptr,
                             int* outDd = nullptr, int* outHh = nullptr,
                             int* outMm = nullptr, int* outSs = nullptr) {
  String r = modemSendGet("AT+CCLK?", 2000);
  int idx = r.indexOf("+CCLK: \"");
  if (idx < 0) return "";
  int start = idx + 8;
  int end = r.indexOf('"', start);
  if (end < 0 || end - start < 17) return "";
  // 26/08/26,10:45:00
  int yy = (r.charAt(start)   - '0') * 10 + (r.charAt(start+1)  - '0');
  int mo = (r.charAt(start+3) - '0') * 10 + (r.charAt(start+4)  - '0');
  int dd = (r.charAt(start+6) - '0') * 10 + (r.charAt(start+7)  - '0');
  int hh = (r.charAt(start+9) - '0') * 10 + (r.charAt(start+10) - '0');
  int mm = (r.charAt(start+12)- '0') * 10 + (r.charAt(start+13) - '0');
  int ss = (r.charAt(start+15)- '0') * 10 + (r.charAt(start+16) - '0');
  int y  = 2000 + yy;
  if (!isPlausibleYear(y) || mo < 1 || mo > 12 || dd < 1 || dd > 31) {
    Serial.printf("[time] rejecting implausible modem CCLK year=%d\n", y);
    return "";
  }
  if (outY)  *outY  = y;
  if (outMo) *outMo = mo;
  if (outDd) *outDd = dd;
  if (outHh) *outHh = hh;
  if (outMm) *outMm = mm;
  if (outSs) *outSs = ss;
  char iso[32];
  snprintf(iso, sizeof(iso), "%04d-%02d-%02dT%02d:%02d:%02d+00:00",
           y, mo, dd, hh, mm, ss);
  return String(iso);
}

// Fallback ISO timestamp via DS3231. Same year window as the modem path so
// an uninitialised RTC (returning year 2000 or similar) is rejected instead
// of getting serialised into a bad partition key.
static String rtcGetIsoUtc() {
  int s, mi, h, d, mo, y;
  if (!ds3231Read(s, mi, h, d, mo, y) || !isPlausibleYear(y)) return "";
  char iso[32];
  snprintf(iso, sizeof(iso), "%04d-%02d-%02dT%02d:%02d:%02d+00:00",
           y, mo, d, h, mi, s);
  return String(iso);
}

// Resolve the current timestamp with a labelled provenance chain:
// modem NTP -> DS3231 -> 1970 sentinel.
static String nowIsoUtcWithSource(TimeSource& src) {
  String t = modemGetIsoUtc();
  if (t.length() > 0) { src = TS_NTP; return t; }
  t = rtcGetIsoUtc();
  if (t.length() > 0) { src = TS_RTC; return t; }
  src = TS_NONE;
  // Sentinel — backend's _normalize_clock_skew (broker.py) will rewrite
  // this to server UTC + set validation_warn=true. Row still lands.
  return "1970-01-01T00:00:00+00:00";
}

// One-shot: after NTP sync, copy the modem clock to the DS3231 so subsequent
// boots (or NTP outages) can still produce a plausible timestamp. Idempotent;
// only writes once per boot.
static void syncRtcFromModemOnce() {
  if (g_rtcSyncedFromNtp) return;
  int y = 0, mo = 0, dd = 0, hh = 0, mm = 0, ss = 0;
  String t = modemGetIsoUtc(&y, &mo, &dd, &hh, &mm, &ss);
  if (t.length() == 0) return;   // modem clock still not trustworthy
  if (ds3231Write(ss, mm, hh, dd, mo, y)) {
    Serial.printf("[time] DS3231 synced from NTP: %s\n", t.c_str());
    g_rtcSyncedFromNtp = true;
  } else {
    Serial.println(F("[time] DS3231 sync-back failed (RTC absent?)"));
  }
}

// ================================================================
// MQTT — connect + publish (three-command flow)
// ================================================================
static bool mqttConfigureTls() {
  char cmd[64];
  snprintf(cmd, sizeof(cmd), "AT+CSSLCFG=\"sslversion\",0,%d",   MODEM_SSLVERSION);
  if (!modemSendExpect(cmd, "OK", 3000)) return false;
  snprintf(cmd, sizeof(cmd), "AT+CSSLCFG=\"ignorelocaltime\",0,%d", MODEM_IGNORE_TIME);
  modemSendExpect(cmd, "OK", 3000);
  snprintf(cmd, sizeof(cmd), "AT+CSSLCFG=\"authmode\",0,%d",     MODEM_AUTHMODE);
  if (!modemSendExpect(cmd, "OK", 3000)) return false;
  snprintf(cmd, sizeof(cmd), "AT+CSSLCFG=\"enableSNI\",0,%d",    MODEM_ENABLE_SNI);
  if (!modemSendExpect(cmd, "OK", 3000)) return false;
  return true;
}

static bool mqttStartAndAcquire() {
  if (!modemSendExpect("AT+CMQTTSTART", "+CMQTTSTART: 0", 10000)) return false;
  if (!mqttConfigureTls()) return false;

  char cmd[96];
  snprintf(cmd, sizeof(cmd), "AT+CMQTTACCQ=0,\"%s\",1", MAIN_NODE_ID);
  if (!modemSendExpect(cmd, "OK", 5000)) return false;
  snprintf(cmd, sizeof(cmd), "AT+CMQTTCFG=\"version\",0,%d", MODEM_MQTT_VERSION);
  if (!modemSendExpect(cmd, "OK", 3000)) return false;
  if (!modemSendExpect("AT+CMQTTSSLCFG=0,0", "OK", 3000)) return false;
  return true;
}

static bool mqttConnect() {
  char cmd[256];
  snprintf(cmd, sizeof(cmd),
           "AT+CMQTTCONNECT=0,\"tcp://%s:%d\",%d,%d,\"%s\",\"%s\"",
           MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE_SECS, MQTT_CLEAN_SESSION,
           MQTT_USERNAME, MQTT_PASSWORD);
  modemFlush();
  modemSerial.print(cmd);
  modemSerial.print("\r\n");
  String r = modemRead(30000);
  if (r.indexOf("+CMQTTCONNECT: 0,0") >= 0) {
    Serial.println(F("[mqtt] CONNECTED"));
    return true;
  }
  Serial.println(F("[mqtt] CONNECT FAILED"));
  return false;
}

static bool mqttPublish(const char* topic, const char* payload) {
  int topicLen = (int)strlen(topic);
  int payloadLen = (int)strlen(payload);

  char cmd[64];
  snprintf(cmd, sizeof(cmd), "AT+CMQTTTOPIC=0,%d", topicLen);
  if (!modemSendExpect(cmd, ">", 5000)) return false;
  modemSerial.print(topic);
  modemSerial.print("\r\n");
  if (modemRead(5000).indexOf("OK") < 0) return false;

  snprintf(cmd, sizeof(cmd), "AT+CMQTTPAYLOAD=0,%d", payloadLen);
  if (!modemSendExpect(cmd, ">", 5000)) return false;
  modemSerial.print(payload);
  modemSerial.print("\r\n");
  if (modemRead(5000).indexOf("OK") < 0) return false;

  modemFlush();
  modemSerial.print("AT+CMQTTPUB=0,1,60\r\n");   // QoS=1, publish timeout 60s
  String r = modemRead(20000);
  return r.indexOf("+CMQTTPUB: 0,0") >= 0;
}

// ================================================================
// SUB-NODE PACKET — CSV → parsed struct
// ================================================================
struct SubReading {
  char     node_id[16];
  uint32_t seq;
  // Wall-clock seconds since the previous TX from this Sub Node, as
  // measured on-device (WDT-timed sleep is ±10-15% vs nominal 300 s).
  // 0 on the first cycle after boot => backend treats flow rate as unknown.
  uint32_t window_s;
  int      soil_adc;
  int      bat_adc;
  int      press_adc;
  uint16_t flow_pulses;
  uint32_t flow_total;
  bool     has_ds_temp;
  float    ds_temp_c;
  bool     npk_ok;
  int      npk_temp_raw;
  int      npk_moist_raw;
  int      npk_ec;
  int      npk_ph_raw;
  int      npk_n;
  int      npk_p;
  int      npk_k;
  char     fw[32];
};

// Set field on the struct. Returns true if key was known.
static bool subApply(SubReading& s, const char* key, const char* val) {
  if      (!strcmp(key, "NODE")) { strncpy(s.node_id, val, sizeof(s.node_id) - 1); s.node_id[sizeof(s.node_id)-1] = '\0'; }
  else if (!strcmp(key, "SEQ"))   s.seq          = (uint32_t)strtoul(val, nullptr, 10);
  else if (!strcmp(key, "WIN"))   s.window_s     = (uint32_t)strtoul(val, nullptr, 10);
  else if (!strcmp(key, "SOIL"))  s.soil_adc     = atoi(val);
  else if (!strcmp(key, "BAT"))   s.bat_adc      = atoi(val);
  else if (!strcmp(key, "PRESS")) s.press_adc    = atoi(val);
  else if (!strcmp(key, "FLOW"))  s.flow_pulses  = (uint16_t)atoi(val);
  else if (!strcmp(key, "FTOT"))  s.flow_total   = (uint32_t)strtoul(val, nullptr, 10);
  else if (!strcmp(key, "DST"))   {
    if (!strcmp(val, "NAN"))     { s.has_ds_temp = false; s.ds_temp_c = NAN; }
    else                         { s.has_ds_temp = true;  s.ds_temp_c = atof(val); }
  }
  else if (!strcmp(key, "NOK"))   s.npk_ok       = (atoi(val) != 0);
  else if (!strcmp(key, "NT"))    s.npk_temp_raw = atoi(val);
  else if (!strcmp(key, "NM"))    s.npk_moist_raw= atoi(val);
  else if (!strcmp(key, "EC"))    s.npk_ec       = atoi(val);
  else if (!strcmp(key, "PH"))    s.npk_ph_raw   = atoi(val);
  else if (!strcmp(key, "N"))     s.npk_n        = atoi(val);
  else if (!strcmp(key, "P"))     s.npk_p        = atoi(val);
  else if (!strcmp(key, "K"))     s.npk_k        = atoi(val);
  else if (!strcmp(key, "FW"))    { strncpy(s.fw, val, sizeof(s.fw) - 1); s.fw[sizeof(s.fw)-1] = '\0'; }
  else return false;
  return true;
}

static bool parseSubCsv(const char* csv, SubReading& s) {
  memset(&s, 0, sizeof(s));
  s.ds_temp_c = NAN;
  s.has_ds_temp = false;

  // Tokenize on commas, then split each token on '='.
  char buf[MAX_LORA_PAYLOAD + 1];
  strncpy(buf, csv, sizeof(buf) - 1);
  buf[sizeof(buf) - 1] = '\0';

  char* saveOuter = nullptr;
  char* tok = strtok_r(buf, ",", &saveOuter);
  int applied = 0;
  while (tok) {
    char* eq = strchr(tok, '=');
    if (eq) {
      *eq = '\0';
      const char* key = tok;
      const char* val = eq + 1;
      if (subApply(s, key, val)) applied++;
    }
    tok = strtok_r(nullptr, ",", &saveOuter);
  }
  return applied > 0 && strlen(s.node_id) > 0;
}

// ================================================================
// NODE_ID → PLOT_ID
// ================================================================
static const char* plotIdFor(const char* nodeId) {
  for (int i = 0; i < NODE_MAP_SIZE; i++) {
    if (strcmp(nodeId, NODE_MAP[i].node_id) == 0) return NODE_MAP[i].plot_id;
  }
  return nullptr;
}

// ================================================================
// JSON BUILDER
// ================================================================
// snprintf-based; no dynamic allocation. Payload size fits in MAX_JSON_PAYLOAD.
static bool buildTelemetryJson(const SubReading& s,
                               const String& nowIso,
                               const String& recordedIso,
                               const char*   plotId,
                               int    lora_rssi_dbm,
                               float  lora_snr_db,
                               float  bme_t, float bme_h, float bme_p_pa,
                               bool   bme_ok,
                               float  ina_bus_v, float ina_curr_ma,
                               bool   ina_ok,
                               unsigned long rain_delta,
                               unsigned long wind_delta,
                               int    wind_dir_adc,
                               TimeSource time_source,
                               char*  out, size_t outSize) {
  char ds_val[16];
  if (s.has_ds_temp) snprintf(ds_val, sizeof(ds_val), "%.2f", s.ds_temp_c);
  else               snprintf(ds_val, sizeof(ds_val), "null");

  char bme_temp[16], bme_hum[16], bme_press[16];
  if (bme_ok) {
    snprintf(bme_temp,  sizeof(bme_temp),  "%.2f", bme_t);
    snprintf(bme_hum,   sizeof(bme_hum),   "%.2f", bme_h);
    snprintf(bme_press, sizeof(bme_press), "%.1f", bme_p_pa);
  } else {
    strcpy(bme_temp,  "null");
    strcpy(bme_hum,   "null");
    strcpy(bme_press, "null");
  }

  char ina_v[16], ina_c[16];
  if (ina_ok) {
    snprintf(ina_v, sizeof(ina_v), "%.3f", ina_bus_v);
    snprintf(ina_c, sizeof(ina_c), "%.2f", ina_curr_ma);
  } else {
    strcpy(ina_v, "null");
    strcpy(ina_c, "null");
  }

  int n = snprintf(out, outSize,
    "{"
      "\"$schema\":\"agro-guardian/telemetry/v2-raw\","
      "\"tenant_id\":\"%s\","
      "\"farmer_id\":\"%s\","
      "\"farm_id\":\"%s\","
      "\"plot_id\":\"%s\","
      "\"node_id\":\"%s\","
      "\"seq\":%lu,"
      "\"recorded_at\":\"%s\","
      "\"received_at_master\":\"%s\","
      "\"transmission_type\":\"lora\","
      "\"raw_readings\":{"
        "\"window_s\":%lu,"
        "\"soil_adc\":%d,"
        "\"battery_adc\":%d,"
        "\"pressure_adc\":%d,"
        "\"flow_pulses_window\":%u,"
        "\"flow_pulses_total\":%lu,"
        "\"ds18b20_temp_c\":%s,"
        "\"npk_ok\":%s,"
        "\"npk_temp_raw\":%d,"
        "\"npk_moisture_raw\":%d,"
        "\"npk_ec_us_cm\":%d,"
        "\"npk_ph_raw\":%d,"
        "\"npk_nitrogen_mg_kg\":%d,"
        "\"npk_phosphorus_mg_kg\":%d,"
        "\"npk_potassium_mg_kg\":%d,"
        "\"sub_node_fw\":\"%s\""
      "},"
      "\"master_readings\":{"
        "\"bme280_temp_c\":%s,"
        "\"bme280_humidity_pct\":%s,"
        "\"bme280_pressure_pa\":%s,"
        "\"ina219_bus_v\":%s,"
        "\"ina219_current_ma\":%s,"
        "\"rain_pulses_window\":%lu,"
        "\"wind_pulses_window\":%lu,"
        "\"wind_dir_adc\":%d,"
        "\"lora_rssi_dbm\":%d,"
        "\"lora_snr_db\":%.2f,"
        "\"time_source\":\"%s\","
        "\"sub_node_online\":true"
      "},"
      "\"firmware_version\":\"%s\","
      "\"main_node_id\":\"%s\""
    "}",
    PILOT_TENANT_ID, PILOT_FARMER_ID, PILOT_FARM_ID,
    plotId, s.node_id, (unsigned long)s.seq,
    recordedIso.c_str(), nowIso.c_str(),
    (unsigned long)s.window_s,
    s.soil_adc, s.bat_adc, s.press_adc,
    (unsigned)s.flow_pulses, (unsigned long)s.flow_total,
    ds_val,
    s.npk_ok ? "true" : "false",
    s.npk_temp_raw, s.npk_moist_raw, s.npk_ec, s.npk_ph_raw,
    s.npk_n, s.npk_p, s.npk_k,
    s.fw,
    bme_temp, bme_hum, bme_press,
    ina_v, ina_c,
    rain_delta, wind_delta, wind_dir_adc,
    lora_rssi_dbm, lora_snr_db,
    timeSourceLabel(time_source),
    FIRMWARE_VERSION, MAIN_NODE_ID);
  return n > 0 && n < (int)outSize;
}

// ================================================================
// MASTER-ONLY HEARTBEAT JSON
// ================================================================
// Companion to buildTelemetryJson for the case where the Sub Node has gone
// silent (or hasn't sent this cycle). Emits $schema=agro-guardian/telemetry/
// v2-master with only the master_readings block. Backend will need a
// parse_inbound branch (follow-up round) to consume this; until then the
// broker will meter it as unknown_topic_kind — non-fatal, and infinitely
// preferable to Main Node going silent when the Sub Node stops sending.
static bool buildMasterHeartbeatJson(const String& nowIso,
                                     bool  bme_ok,
                                     float bme_t, float bme_h, float bme_p_pa,
                                     bool  ina_ok,
                                     float ina_bus_v, float ina_curr_ma,
                                     unsigned long rain_delta,
                                     unsigned long wind_delta,
                                     int   wind_dir_adc,
                                     bool  sub_node_online,
                                     unsigned long sub_node_silence_ms,
                                     TimeSource time_source,
                                     char* out, size_t outSize) {
  char bme_temp[16], bme_hum[16], bme_press[16];
  if (bme_ok) {
    snprintf(bme_temp,  sizeof(bme_temp),  "%.2f", bme_t);
    snprintf(bme_hum,   sizeof(bme_hum),   "%.2f", bme_h);
    snprintf(bme_press, sizeof(bme_press), "%.1f", bme_p_pa);
  } else {
    strcpy(bme_temp,  "null");
    strcpy(bme_hum,   "null");
    strcpy(bme_press, "null");
  }

  char ina_v[16], ina_c[16];
  if (ina_ok) {
    snprintf(ina_v, sizeof(ina_v), "%.3f", ina_bus_v);
    snprintf(ina_c, sizeof(ina_c), "%.2f", ina_curr_ma);
  } else {
    strcpy(ina_v, "null");
    strcpy(ina_c, "null");
  }

  int n = snprintf(out, outSize,
    "{"
      "\"$schema\":\"agro-guardian/telemetry/v2-master\","
      "\"tenant_id\":\"%s\","
      "\"farm_id\":\"%s\","
      "\"main_node_id\":\"%s\","
      "\"recorded_at\":\"%s\","
      "\"received_at_master\":\"%s\","
      "\"transmission_type\":\"heartbeat\","
      "\"master_readings\":{"
        "\"bme280_temp_c\":%s,"
        "\"bme280_humidity_pct\":%s,"
        "\"bme280_pressure_pa\":%s,"
        "\"ina219_bus_v\":%s,"
        "\"ina219_current_ma\":%s,"
        "\"rain_pulses_window\":%lu,"
        "\"wind_pulses_window\":%lu,"
        "\"wind_dir_adc\":%d,"
        "\"time_source\":\"%s\","
        "\"sub_node_online\":%s,"
        "\"sub_node_silence_ms\":%lu"
      "},"
      "\"firmware_version\":\"%s\""
    "}",
    PILOT_TENANT_ID, PILOT_FARM_ID, MAIN_NODE_ID,
    nowIso.c_str(), nowIso.c_str(),
    bme_temp, bme_hum, bme_press,
    ina_v, ina_c,
    rain_delta, wind_delta, wind_dir_adc,
    timeSourceLabel(time_source),
    sub_node_online ? "true" : "false",
    sub_node_silence_ms,
    FIRMWARE_VERSION);
  return n > 0 && n < (int)outSize;
}

// ================================================================
// STATE / GLOBALS
// ================================================================
static bool g_mqttConnected  = false;
static bool g_bmeOk          = false;
static bool g_inaOk          = false;
static unsigned long g_lastMqttAttempt = 0;
// Sub Node liveness tracking. Initialised to 0; the first heartbeat after
// boot will therefore report sub_node_online=false until we hear from the
// Sub Node at least once (which is correct — we genuinely don't know yet).
static unsigned long g_lastLoraRxMs   = 0;
static bool          g_haveLoraEverRx = false;
static unsigned long g_lastHeartbeatMs = 0;

// ================================================================
// SD OFFLINE OUTBOX
// ================================================================
// When MQTT publish fails and SD is available, append (topic, payload) as
// a single newline-delimited JSON line to /outbox.jsonl. On next successful
// MQTT connect drain up to SD_OUTBOX_DRAIN_BATCH lines per loop pass.
// Rotates by truncating oldest half of the file when SD_OUTBOX_MAX_BYTES
// is reached — simpler than log-rotation, acceptable for our data-loss
// model (we'd rather keep newer telemetry than the oldest queued row).

static bool sdAppendOutboxLine(const char* topic, const char* payload) {
  if (!g_sdOk) return false;
  File f = SD.open(SD_OUTBOX_PATH, FILE_APPEND);
  if (!f) return false;
  // Rotate if file has grown past cap. Naive strategy: nuke and start fresh.
  // Older cached rows are lost — better than filling the SD.
  if ((unsigned long)f.size() > SD_OUTBOX_MAX_BYTES) {
    f.close();
    SD.remove(SD_OUTBOX_PATH);
    f = SD.open(SD_OUTBOX_PATH, FILE_APPEND);
    if (!f) return false;
    Serial.println(F("[outbox] rotated (exceeded max size)"));
  }
  // Line format: {"t":"<topic>","p":<payload_json>}\n
  // We embed the payload as raw JSON (it already is JSON). The topic is a
  // fixed ASCII string with no quotes; safe to inline without escaping.
  f.print(F("{\"t\":\""));
  f.print(topic);
  f.print(F("\",\"p\":"));
  f.print(payload);
  f.println(F("}"));
  f.close();
  return true;
}

// Drain up to N queued outbox lines. Returns count actually drained.
// Strategy: read the whole file into a scratch, rewrite excluding drained
// lines. Simple and correct at pilot scale (kBs to low MBs); revisit if
// outbox routinely exceeds ~1 MB during ops.
static int sdDrainOutbox(int maxLines) {
  if (!g_sdOk || !g_mqttConnected) return 0;
  if (!SD.exists(SD_OUTBOX_PATH)) return 0;

  File in = SD.open(SD_OUTBOX_PATH, FILE_READ);
  if (!in) return 0;

  const char* tmpPath = "/outbox.tmp";
  SD.remove(tmpPath);
  File out = SD.open(tmpPath, FILE_WRITE);
  if (!out) { in.close(); return 0; }

  int drained = 0;
  char line[MAX_JSON_PAYLOAD + 256];  // topic + wrapper + payload
  while (in.available()) {
    int len = in.readBytesUntil('\n', line, sizeof(line) - 1);
    if (len <= 0) continue;
    line[len] = '\0';

    if (drained >= maxLines) {
      // Keep the remainder in the new file.
      out.println(line);
      continue;
    }

    // Parse minimal {"t":"...","p":<json>}
    char* tStart = strstr(line, "\"t\":\"");
    char* pMark  = strstr(line, "\",\"p\":");
    if (!tStart || !pMark) {
      Serial.println(F("[outbox] malformed line — skipping"));
      drained++;
      continue;
    }
    tStart += 5;
    *pMark = '\0';
    const char* topic = tStart;
    char* payload = pMark + 6;
    // Trim trailing '}' from wrapper.
    int plen = (int)strlen(payload);
    if (plen > 0 && payload[plen - 1] == '}') payload[plen - 1] = '\0';

    esp_task_wdt_reset();
    bool ok = mqttPublish(topic, payload);
    if (ok) {
      Serial.printf("[outbox] drained → %s\n", topic);
      drained++;
    } else {
      Serial.println(F("[outbox] drain publish failed — stopping, will retry"));
      // Preserve this line and everything after — mqttPublish already
      // flipped g_mqttConnected=false, so we won't loop again this pass.
      out.print(F("{\"t\":\""));
      out.print(topic);
      out.print(F("\",\"p\":"));
      out.print(payload);
      out.println(F("}"));
      // Copy the rest verbatim.
      while (in.available()) {
        int rest = in.readBytesUntil('\n', line, sizeof(line) - 1);
        if (rest <= 0) continue;
        line[rest] = '\0';
        out.println(line);
      }
      break;
    }
  }
  in.close();
  out.close();

  SD.remove(SD_OUTBOX_PATH);
  SD.rename(tmpPath, SD_OUTBOX_PATH);
  return drained;
}

// ================================================================
// SD BOOT LOG
// ================================================================
static void sdWriteBootLine() {
  if (!g_sdOk) return;
  File f = SD.open("/boot.log", FILE_APPEND);
  if (!f) return;
  String iso = rtcGetIsoUtc();
  if (iso.length() == 0) iso = "unknown";
  f.print(F("boot="));
  f.print(iso);
  f.print(F(" fw="));
  f.print(FIRMWARE_VERSION);
  f.print(F(" bme="));  f.print(g_bmeOk ? F("ok") : F("fail"));
  f.print(F(" ina="));  f.print(g_inaOk ? F("ok") : F("fail"));
  f.print(F(" rtc="));  f.print(i2cPresent(0x68) ? F("ok") : F("fail"));
  f.println();
  f.close();
}

// ================================================================
// MQTT lifecycle helpers
// ================================================================
static bool bringUpMqtt() {
  if (!mqttStartAndAcquire()) {
    Serial.println(F("[mqtt] start/acquire failed"));
    return false;
  }
  if (!mqttConnect()) return false;
  g_mqttConnected = true;
  return true;
}

static void reconnectMqttIfDown() {
  if (g_mqttConnected) return;
  unsigned long now = millis();
  if (now - g_lastMqttAttempt < MQTT_RECONNECT_MS) return;
  g_lastMqttAttempt = now;
  Serial.println(F("[mqtt] reconnecting…"));

  // Tear down any half-open state, then re-run bring-up.
  modemSendExpect("AT+CMQTTDISC=0,120", "OK", 3000);
  modemSendExpect("AT+CMQTTREL=0",      "OK", 3000);
  modemSendExpect("AT+CMQTTSTOP",       "OK", 3000);

  if (bringUpMqtt()) {
    Serial.println(F("[mqtt] reconnect OK"));
  } else {
    Serial.println(F("[mqtt] reconnect FAILED; will retry"));
  }
}

// ================================================================
// SETUP
// ================================================================
void setup() {
  Serial.begin(115200);
  delay(1500);

  // ---- Task WDT. 90 s covers a worst-case MQTT publish + reconnect. ----
  // Init BEFORE any long-running bring-up code so a stuck modem or hung
  // I2C bus reboots the ESP32 rather than hanging in setup() forever.
  esp_task_wdt_init(ESP32_TASK_WDT_S, true);
  esp_task_wdt_add(NULL);   // watch the loop task
  esp_task_wdt_reset();

  Serial.println();
  Serial.println(F("=================================================="));
  Serial.println(F(" VIRAAI Main Node — RAW variant"));
  Serial.print  (F("  main_node_id = ")); Serial.println(MAIN_NODE_ID);
  Serial.print  (F("  firmware     = ")); Serial.println(FIRMWARE_VERSION);
  Serial.println(F("=================================================="));

  // ---- Hold SPI CS lines HIGH before any bus activity so peripherals
  //      don't fight for the bus during boot. ----
  pinMode(SD_CS_PIN,   OUTPUT); digitalWrite(SD_CS_PIN,   HIGH);
  pinMode(LORA_CS_PIN, OUTPUT); digitalWrite(LORA_CS_PIN, HIGH);

  // ---- GPIO + ADC ----
  pinMode(RAIN_PIN,     INPUT_PULLUP);
  pinMode(WIND_SPD_PIN, INPUT_PULLUP);
  pinMode(WIND_DIR_PIN, INPUT);
  analogSetPinAttenuation(WIND_DIR_PIN, ADC_11db);   // 0..3.3 V full-scale

  attachInterrupt(digitalPinToInterrupt(RAIN_PIN),     rainISR, FALLING);
  attachInterrupt(digitalPinToInterrupt(WIND_SPD_PIN), windISR, FALLING);

  // ---- I2C ----
  Wire.begin(I2C_SDA, I2C_SCL);
  delay(500);
  scanI2C();

  g_bmeOk = bmeInit();
  Serial.println(g_bmeOk ? F("[bme]  init OK")  : F("[bme]  init FAIL"));

  g_inaOk = inaInit();
  Serial.println(g_inaOk ? F("[ina]  init OK")  : F("[ina]  init FAIL"));

  if (i2cPresent(0x68)) Serial.println(F("[rtc]  DS3231 present"));
  else                  Serial.println(F("[rtc]  DS3231 MISSING"));

  // ---- SPI + SD (init + set g_sdOk for outbox / boot log) ----
  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI, -1);
  if (SD.begin(SD_CS_PIN)) {
    uint64_t sz = SD.cardSize() / (1024ULL * 1024ULL);
    Serial.printf("[sd]   OK, %llu MB\n", sz);
    g_sdOk = true;
  } else {
    Serial.println(F("[sd]   init FAIL (offline buffering disabled)"));
    g_sdOk = false;
  }

  // ---- LoRa RX ----
  LoRa.setPins(LORA_CS_PIN, LORA_RST_PIN, LORA_DIO0_PIN);
  if (!LoRa.begin(LORA_FREQUENCY_HZ)) {
    Serial.println(F("[lora] init FAIL — halted"));
    while (true) { delay(1000); }
  }
  LoRa.setSpreadingFactor(LORA_SPREADING_FACTOR);
  LoRa.setSignalBandwidth(LORA_BANDWIDTH_HZ);
  LoRa.setCodingRate4(LORA_CODING_RATE);
  LoRa.enableCrc();
  LoRa.receive();   // continuous RX
  Serial.println(F("[lora] listening on 433 MHz SF7 BW125k CR4/5"));

  // ---- Modem + MQTT ----
  modemSerial.begin(MODEM_UART_BAUD, SERIAL_8N1, MODEM_RX_PIN, MODEM_TX_PIN);
  delay(2500);

  if (!modemBoot() || !modemDataAttach()) {
    Serial.println(F("[modem] bring-up failed — will keep retrying in loop()"));
  } else {
    modemNtpSync();
    if (!bringUpMqtt()) {
      Serial.println(F("[mqtt] initial connect failed — will retry"));
    }
  }

  // ---- SD boot log (one line per boot, timestamped from RTC) ----
  sdWriteBootLine();

  esp_task_wdt_reset();

  Serial.println(F("=================================================="));
  Serial.println(F(" SETUP COMPLETE — waiting for LoRa packets"));
  Serial.println(F("=================================================="));
}

// ================================================================
// Publish helpers
// ================================================================
// Publish a Sub-Node-triggered v2-raw telemetry payload after a successful
// LoRa RX. Returns true on publish success.
static bool publishSubNodeTelemetry(const SubReading& s, int rssi, float snr) {
  const char* plotId = plotIdFor(s.node_id);
  if (!plotId) {
    Serial.printf("[map]  unknown NODE_ID %s — dropping\n", s.node_id);
    return false;
  }

  float bt = 0, bh = 0, bp = 0;
  bool  bme_ok_now = g_bmeOk && bmeRead(bt, bh, bp);
  float ibv = 0, imA = 0;
  if (g_inaOk) inaRead(ibv, imA);
  unsigned long rainDelta = 0, windDelta = 0;
  snapshotRainWindDelta(rainDelta, windDelta);
  int windDirAdc = analogRead(WIND_DIR_PIN);

  TimeSource ts = TS_NONE;
  String nowIso      = nowIsoUtcWithSource(ts);
  String recordedIso = nowIso;   // best available; LoRa hop is <1 s

  char json[MAX_JSON_PAYLOAD];
  if (!buildTelemetryJson(s, nowIso, recordedIso, plotId,
                          rssi, snr,
                          bt, bh, bp, bme_ok_now,
                          ibv, imA, g_inaOk,
                          rainDelta, windDelta, windDirAdc,
                          ts,
                          json, sizeof(json))) {
    Serial.println(F("[json] build FAILED (buffer too small)"));
    return false;
  }

  char topic[192];
  snprintf(topic, sizeof(topic),
           "agro/v2/%s/%s/%s/telemetry",
           PILOT_TENANT_ID, PILOT_FARM_ID, s.node_id);

  if (!g_mqttConnected) {
    // Modem/MQTT down. Queue to SD outbox rather than lose the packet.
    // Master heartbeats bypass this path — we only queue Sub-Node telemetry.
    if (sdAppendOutboxLine(topic, json)) {
      Serial.println(F("[mqtt] offline — queued to SD outbox"));
    } else {
      Serial.println(F("[mqtt] offline — SD unavailable, packet DROPPED"));
    }
    return false;
  }
  Serial.printf("[mqtt] publish → %s\n", topic);
  bool ok = mqttPublish(topic, json);
  if (ok) {
    Serial.println(F("[mqtt] publish OK"));
  } else {
    Serial.println(F("[mqtt] publish FAILED — queueing to outbox, marking session down"));
    sdAppendOutboxLine(topic, json);
    g_mqttConnected = false;
  }
  return ok;
}

// Periodic master-only heartbeat. Runs off wall-clock cadence, not LoRa RX,
// so the backend keeps hearing from Main Node even when the Sub Node is dead
// or the LoRa link is broken. sub_node_online is inferred from the age of
// the last LoRa RX watermark.
static bool publishMasterHeartbeat() {
  float bt = 0, bh = 0, bp = 0;
  bool  bme_ok_now = g_bmeOk && bmeRead(bt, bh, bp);
  float ibv = 0, imA = 0;
  if (g_inaOk) inaRead(ibv, imA);
  unsigned long rainDelta = 0, windDelta = 0;
  snapshotRainWindDelta(rainDelta, windDelta);
  int windDirAdc = analogRead(WIND_DIR_PIN);

  TimeSource ts = TS_NONE;
  String nowIso = nowIsoUtcWithSource(ts);

  unsigned long now = millis();
  unsigned long silenceMs = g_haveLoraEverRx ? (now - g_lastLoraRxMs) : 0;
  bool subOnline =
      g_haveLoraEverRx && silenceMs < SUB_NODE_SILENCE_THRESHOLD_MS;

  char json[MAX_JSON_PAYLOAD];
  if (!buildMasterHeartbeatJson(nowIso,
                                bme_ok_now, bt, bh, bp,
                                g_inaOk, ibv, imA,
                                rainDelta, windDelta, windDirAdc,
                                subOnline, silenceMs, ts,
                                json, sizeof(json))) {
    Serial.println(F("[json] heartbeat build FAILED"));
    return false;
  }

  // Master-only topic uses MAIN_NODE_ID in the third slot so the topic
  // filter (agro/v2/+/+/+/telemetry) still catches it.
  char topic[192];
  snprintf(topic, sizeof(topic),
           "agro/v2/%s/%s/%s/telemetry",
           PILOT_TENANT_ID, PILOT_FARM_ID, MAIN_NODE_ID);

  if (!g_mqttConnected) {
    Serial.println(F("[mqtt] heartbeat skipped — not connected"));
    return false;
  }
  Serial.printf("[mqtt] heartbeat → %s (sub_online=%s, silence=%lums)\n",
                topic, subOnline ? "true" : "false", silenceMs);
  bool ok = mqttPublish(topic, json);
  if (!ok) {
    Serial.println(F("[mqtt] heartbeat FAILED — marking session down"));
    g_mqttConnected = false;
  }
  return ok;
}

// ================================================================
// LOOP
// ================================================================
void loop() {
  esp_task_wdt_reset();

  bool wasDown = !g_mqttConnected;
  reconnectMqttIfDown();

  // If we just came back online, drain a batch of queued packets before
  // moving on to LoRa RX / heartbeats. Bounded so we don't spend an
  // entire loop iteration on drain if the queue is huge.
  if (wasDown && g_mqttConnected) {
    int n = sdDrainOutbox(SD_OUTBOX_DRAIN_BATCH);
    if (n > 0) Serial.printf("[outbox] drained %d line(s) after reconnect\n", n);
  }

  // ---- (1) Drain any LoRa packet that arrived ----
  int size = LoRa.parsePacket();
  if (size > 0) {
    if (size > MAX_LORA_PAYLOAD) {
      Serial.printf("[lora] oversized packet (%d bytes) — dropping\n", size);
      while (LoRa.available()) LoRa.read();
    } else {
      char csv[MAX_LORA_PAYLOAD + 1];
      int idx = 0;
      while (LoRa.available() && idx < MAX_LORA_PAYLOAD) {
        csv[idx++] = (char)LoRa.read();
      }
      csv[idx] = '\0';
      int   rssi = LoRa.packetRssi();
      float snr  = LoRa.packetSnr();
      Serial.printf("[lora] RX (%d B, rssi=%d, snr=%.2f): %s\n",
                    idx, rssi, snr, csv);

      SubReading s;
      if (parseSubCsv(csv, s)) {
        // Watermark BEFORE publish so a publish failure doesn't roll back
        // liveness accounting — we did hear from the Sub Node.
        g_lastLoraRxMs   = millis();
        g_haveLoraEverRx = true;
        publishSubNodeTelemetry(s, rssi, snr);
      } else {
        Serial.println(F("[lora] parse FAIL — dropping"));
      }
    }
  }

  // ---- (2) Periodic master heartbeat ----
  // Fires independently of LoRa. Whether the Sub Node is alive or not, ops
  // sees fresh master_readings + a truthful sub_node_online flag.
  unsigned long now = millis();
  if (now - g_lastHeartbeatMs >= MASTER_HEARTBEAT_MS) {
    g_lastHeartbeatMs = now;
    publishMasterHeartbeat();
  }

  delay(20);   // small yield
}
