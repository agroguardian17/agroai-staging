# VIRAAI Sub Node — Firmware

Full-integration production sketch for the ATmega328P Sub Node. Reads all
field sensors and transmits **raw** values over LoRa 433 MHz to the Main
Node; all calibration is done server-side.

## Hardware assumptions

- MCU: **ATmega328P-PU DIP-28**, external **8 MHz** crystal, **3.3 V** logic.
- Programmer: **USBasp** ISP, no serial bootloader.
- LoRa: **RA-02 (SX1278)** on 433 MHz, SPI + DIO0 on D2.
- Sensors: DS18B20 (D4), capacitive soil (A0), RS485 NPK Modbus on D6/D7
  through an **MT3608 → IRLZ44N** 12 V gate driven by A2, battery divider
  220 k + 100 k on A1, pressure transducer on A3, flow pulse on D9 (polled).
- Battery: LiFePO4 pack (~6.0 V discharged → ~8.4 V full).

## Prerequisites

1. **Arduino IDE 2.x** (or Arduino CLI ≥ 0.35).
2. **MiniCore** board package — add
   `https://mcudude.github.io/MiniCore/package_MCUdude_MiniCore_index.json`
   to *Preferences → Additional Boards Manager URLs*, then install *MiniCore*
   from Boards Manager.
3. **Libraries** (Library Manager or `arduino-cli lib install`):
   - `LoRa` by Sandeep Mistry
   - `OneWire` by Paul Stoffregen
   - `DallasTemperature` by Miles Burton
   - `Low-Power` by Rocket Scream Electronics — required for the 5-min
     deep-sleep cadence introduced 2026-08-27 v2.
   - `SoftwareSerial` (bundled with Arduino AVR core)
4. **USBasp driver** on Windows (Zadig — install `libusbK`).

## Per-board configuration

Before every flash, edit `sub_node_config.h` and set `NODE_ID` to the string
that maps to this physical board:

```c
#define NODE_ID "AGR-SN-0001"
```

The pilot only uses `AGR-SN-0001` today (mapped to `PLOT_PILOT_001`). When a
second Sub Node is deployed, change this to `AGR-SN-0002` before flashing.
Two boards MUST NOT ship with the same `NODE_ID` — the Main Node uses this
string to key its `NODE_ID → PLOT_ID` lookup table.

`FIRMWARE_VERSION` (same file) is transmitted with every packet — bump it
on any behavioural change so the backend audit trail is meaningful.

## Board settings (Arduino IDE)

- **Board:** MiniCore → ATmega328
- **Clock:** External 8 MHz
- **BOD:** 2.7 V
- **EEPROM:** Retained
- **Compiler LTO:** Enabled
- **Variant:** 328P / 328PA
- **Bootloader:** No bootloader
- **Programmer:** USBasp (slow) if the fuses have not yet been burned

## First-time provisioning (fuses + bootloader-less flash)

Only needed once per board:

```
Tools → Burn Bootloader
```

This programs the fuses for external 8 MHz + BOD 2.7 V. It is **not** a
bootloader install — `No bootloader` is selected above.

## Flashing the production sketch

1. Open `firmware/sub_node/sub_node.ino` in Arduino IDE.
2. Confirm `sub_node_config.h::NODE_ID` matches this physical board.
3. Tools → Programmer → **USBasp (slow)**.
4. **Sketch → Upload Using Programmer** (Ctrl+Shift+U).
5. Watch the serial output at **9600 baud** — you should see the startup
   banner (`VIRAAI Sub Node — RAW variant`) and the first cycle within
   ~15 seconds.

## Wire format sent over LoRa

Single CSV line, keys ≤ 5 chars to keep airtime low:

```
NODE=AGR-SN-0001,SEQ=42,WIN=300,SOIL=412,BAT=780,PRESS=340,FLOW=1750,FTOT=8241,DST=27.50,NOK=1,NT=291,NM=357,EC=1045,PH=645,N=58,P=79,K=197,FW=viraai-sn-1.0.0-raw
```

All numeric fields are **raw sensor outputs**:
- `SEQ` — monotonic packet counter since boot.
- `WIN` — wall-clock seconds since the previous TX (2026-08-27 v2). `0` on
  the first cycle after boot signals "unknown window — backend must not
  compute a flow rate this cycle". WDT-timed sleep is ±10-15% so this
  value can drift from the nominal 300 s.
- `SOIL`, `BAT`, `PRESS` — raw 10-bit ADC counts (0–1023).
- `FLOW` — pulses counted during the last `WIN` seconds (PCINT + poll).
- `FTOT` — total pulses since board boot (authoritative volume totalizer).
- `DST` — DS18B20 temperature in °C or the literal `NAN` if disconnected.
- `NOK` — `1` if this cycle's NPK Modbus read passed (after up to 3
  retries); `0` if all attempts failed.
- `NT`, `NM`, `PH` — raw 16-bit register values (server applies /10 or /100).
- `EC` — µS/cm (sensor-native units, no conversion needed).
- `N`, `P`, `K` — mg/kg (sensor-native units).
- `FW` — firmware version string from `sub_node_config.h`.

The Main Node adds the topic segments (tenant / farm / node) and the
timestamp before publishing to MQTT. No `plot_id` is sent over LoRa; the
Main Node maps `NODE_ID → PLOT_ID` from its own configuration.

## Cycle timing (2026-08-27 v2 — 5-minute cadence)

- Boot to first packet: **~15 seconds** (sensor init + 10 s NPK stabilise).
- Steady-state cadence: **5 minutes** end-to-end (see `CYCLE_PERIOD_MS`).
  - ~0.3 s soil + battery + pressure reads
  - 0.8 s DS18B20 conversion
  - 10 s NPK stabilization (empirically required — do NOT reduce)
  - ~1.5 s NPK Modbus request + up to 2 retries at 300 ms gap
  - LoRa TX + post-TX LED status code (1/2/3 blinks)
  - **Deep sleep for the remainder (~4:45)** via
    `LowPower.powerDown(SLEEP_8S, ADC_OFF, BOD_OFF)` in 8 s chunks.
- Flow-pulse counting continues *during sleep* via a PCINT0 ISR on PB1
  (D9); no pulses are lost while the MCU is off.
- Watchdog: `wdt_enable(WDTO_8S)` armed at end of setup. Reset in the
  sleep loop, in `delayWithFlow`, and inside `readNpkAttempt`. A hung
  sensor read reboots the MCU cleanly rather than leaving a buried node
  dead in the field.

## Post-TX LED status codes (2026-08-27 v2)

Field ops can diagnose a buried node without a laptop by watching the
STATUS_LED after each cycle's TX. Solid ON during the LoRa TX itself,
then:

| Blinks | Meaning |
|---|---|
| **1** | Full success — LoRa TX OK, NPK read OK |
| **2** | LoRa TX OK, NPK read FAILED this cycle (backend will treat NPK fields as no-data via the Round 16 short-circuit) |
| **3** | LoRa TX FAILED — check antenna, power, or LoRa module wiring |

## Troubleshooting

- **`LoRa: init FAIL — halted`** → wiring or 3.3 V supply issue on the RA-02.
  Check D8 RST, D10 NSS, hardware SPI on D11–D13.
- **`NPK: short read, bytes=0`** → power path from A2 through the MT3608 to
  the NPK sensor is not delivering 12 V. Check IRLZ44N gate voltage (should
  read ~3.3 V at A2 when HIGH) and MT3608 boost output.
- **`NPK: CRC fail` on random cycles** → RS485 line noise or ground bounce
  during NPK power-up. First cycle after boot may fail; steady state should
  pass. Increase `NPK_STABILIZE_MS` (in `sub_node_config.h`) only as a last
  resort — the 10 s value was empirically dialled in.
- **`DST=NAN`** → DS18B20 not detected on D4. Check the 4.7 kΩ pull-up on the
  data line to +3.3 V.
- **Board never boots (no startup banner)** → wrong fuses. Re-run
  Tools → Burn Bootloader with the board settings above.

## Power budget notes (for the field team)

Firmware v2 (2026-08-27) uses `LowPower.powerDown()` between cycles.
Budget per 5-min cycle:

- Active phase ~13-14 s @ ~40 mA average (spikes to ~200 mA during the
  10 s NPK stabilise window).
- Deep sleep ~4:46 @ ~0.3 µA nominal on bare ATmega328P + external crystal;
  a PCINT wake-and-count on flow pulses is a few µA·s extra per pulse.
- Daily average: roughly **~120 mA·h/day** at moderate irrigation flow.

That comfortably supports 24/7 operation on a LiFePO4 pack + 20 W solar
panel, and even on a bare 3400 mAh 18650 the node runs for ~30 days
without any solar input.

## Files in this folder

| File | Purpose |
|---|---|
| `sub_node.ino` | Full production sketch. |
| `sub_node_config.h` | Per-board `NODE_ID`, firmware version, cycle timings. |
| `README.md` | You are here. |
