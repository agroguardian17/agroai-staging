# Sub Node firmware — required changes before field deploy

> **Audience:** the teammate maintaining the ATmega328P Sub Node sketch (`Final Code_6023.docx` as of 2026-08-03).
> **Purpose:** three edits are needed for the backend to accept the readings the Sub Node is already producing. All three are small — total added flash roughly 400 bytes; SRAM is untouched.
> **After these changes:** flash one binary per Sub Node (or one binary flashed with the correct EEPROM node ID) and every reading lands in Postgres.

## Change 1 — Add `NODE=<sub_node_id>` to the LoRa packet

**Why.** The backend's Main-Node-side parser needs to know which Sub Node originated a reading. The current pilot (revised 2026-08-26) has only **1 Sub Node**, so the `NODE` field is not strictly required today. It is still worth adding now because as soon as a second Sub Node is deployed on the same LoRa channel, packets without a `NODE` field become ambiguous and readings will attribute to the wrong plot — the fix is trivial while the field is still hot.

**How.** Store the Sub Node ID (a short string like `"AGR-SN-0001"`) in EEPROM once at provisioning time, read it at boot into a `char subNodeId[16]` buffer, and include it as the first CSV field.

### 1a — Store the ID in EEPROM (one-time, per Sub Node)

Write a tiny provisioning sketch that just does:

```cpp
#include <EEPROM.h>

void setup() {
  const char* id = "AGR-SN-0001";   // change per Sub Node
  for (uint8_t i = 0; i < 16; i++) {
    EEPROM.update(i, i < strlen(id) ? id[i] : 0);
  }
  Serial.begin(9600);
  Serial.println("Sub Node ID written to EEPROM");
}

void loop() {}
```

Flash this once, watch the serial `"Sub Node ID written"` print, then flash the real Sub Node firmware. EEPROM survives across reflashes.

### 1b — Read the ID at boot in the production sketch

Add at the top:

```cpp
#include <EEPROM.h>

char subNodeId[16];
```

Add to `setup()` (right after `Serial.begin(9600);`):

```cpp
for (uint8_t i = 0; i < 15; i++) {
  subNodeId[i] = EEPROM.read(i);
  if (subNodeId[i] == 0) break;
}
subNodeId[15] = 0;  // guarantee terminator
if (subNodeId[0] == 0xFF || subNodeId[0] == 0) {
  strcpy(subNodeId, "AGR-SN-UNSET");  // fail-visible, do not silently ship
}
Serial.print("Node ID: "); Serial.println(subNodeId);
```

### 1c — Prepend to the CSV packet

Change your existing `snprintf` in `loop()`:

```cpp
// BEFORE:
snprintf(packet, sizeof(packet),
         "BAT=%s,BATP=%d,DST=%s,SOIL=%d,PRESS=%s,FLOW=%s,NTEMP=%s,NMOIST=%s,EC=%d,PH=%s,N=%d,P=%d,K=%d",
         batStr, batteryPercent, dstStr, soilRaw, pressStr, flowStr,
         ntempStr, nmoistStr, ecVal, phStr, nit, phos, pot);

// AFTER:
snprintf(packet, sizeof(packet),
         "NODE=%s,BAT=%s,BATP=%d,DST=%s,SOIL=%d,PRESS=%s,FLOW=%s,NTEMP=%s,NMOIST=%s,EC=%d,PH=%s,N=%d,P=%d,K=%d",
         subNodeId, batStr, batteryPercent, dstStr, soilRaw, pressStr, flowStr,
         ntempStr, nmoistStr, ecVal, phStr, nit, phos, pot);
```

Bump `char packet[180]` to `char packet[200]` to leave room for the extra field.

## Change 2 — Calibrate `SOIL` from raw ADC to % VWC

**Why.** The current firmware emits `SOIL=393` — the raw ADC reading from the capacitive probe. The backend expects `soil_moisture_avg_pct` in the 0–100 % range (volumetric water content). Sending raw ADC through `soil_moisture_avg_pct` will make every downstream calculation and every rule that reads moisture wrong.

**How.** Every capacitive soil-moisture probe has two reference points:

- `DRY_ADC` — the ADC reading when the probe is fully out of soil (dry air, ~ADC 800 for typical capacitive probes at 5 V).
- `WET_ADC` — the ADC reading when the probe is fully submerged in a cup of water (~ADC 250 for typical capacitive probes).

Between those two, ADC is linear-ish in the middle of the range. Measure both **on the actual probe you'll deploy** — different probe manufacturers vary a lot.

Add near the top:

```cpp
#define DRY_ADC 800   // TODO: measure your probe in air
#define WET_ADC 250   // TODO: measure your probe in water
```

Add a helper:

```cpp
float rawToVWC(int adc) {
  if (adc <= WET_ADC) return 100.0;
  if (adc >= DRY_ADC) return 0.0;
  float pct = 100.0f * (float)(DRY_ADC - adc) / (float)(DRY_ADC - WET_ADC);
  return pct;
}
```

Change the packet-building line:

```cpp
// BEFORE:
snprintf(packet, sizeof(packet), "...,SOIL=%d,...", ..., soilRaw, ...);

// AFTER:
char soilStr[10];
dtostrf(rawToVWC(soilRaw), 4, 1, soilStr);   // 1 decimal, e.g. "41.9"
snprintf(packet, sizeof(packet), "...,SOIL=%s,...", ..., soilStr, ...);
```

Also update your Serial print for parity so bench debugging shows the same value the backend sees.

## Change 3 — Convert `EC` from µS/cm to mS/cm

**Why.** The RS485 NPK sensor returns EC in µS/cm as a 16-bit integer (e.g., `1045`). The backend's `soil_ec_ms_cm` field is in mS/cm — `1045 µS/cm` = `1.045 mS/cm`. If you leave it in µS/cm the value will look 1000× too high and the low-EC rules will never fire.

**How.** Change one line:

```cpp
// BEFORE:
snprintf(packet, sizeof(packet), "...,EC=%d,...", ..., ecVal, ...);

// AFTER:
char ecStr[10];
dtostrf(ecVal / 1000.0f, 4, 3, ecStr);   // 3 decimals, e.g. "1.045"
snprintf(packet, sizeof(packet), "...,EC=%s,...", ..., ecStr, ...);
```

## Change 4 (optional but cheap) — Skip `NMOIST` from the CSV

**Why.** The NPK probe reports its own moisture reading. We already have `SOIL` (from the capacitive probe) as the primary moisture source. Two moisture fields in the same packet is data the Main Node would have to reconcile.

**How.** Drop `NMOIST` from the `snprintf` format string and its argument. Save ~10 bytes on the air. Or leave it in — the Main Node knows to ignore it.

## After the changes

1. Compile in Arduino IDE. Confirm flash + SRAM usage is still comfortably under budget (should be ~15,400 bytes flash / 810 bytes RAM after all changes).
2. Flash the provisioning sketch (Change 1a), watch the serial print.
3. Flash the production sketch.
4. Watch the serial monitor. Every reading should now look like:

   ```
   NODE=AGR-SN-0001,BAT=9.38,BATP=100,DST=27.4,SOIL=41.9,PRESS=5.31,FLOW=8.00,NTEMP=29.1,NMOIST=35.7,EC=1.045,PH=6.45,N=58,P=79,K=197
   ```

5. (Future) When a second Sub Node is added to the pilot, reflash the provisioning sketch with `"AGR-SN-0002"` before the production flash. Not required for the current 2-plot / 1-Sub-Node scope (revised 2026-08-26).

## What the backend does with this

- The Main Node firmware (`firmware/main_node/`) reads the CSV over LoRa, parses each field, and builds a JSON payload matching `docs/HARDWARE_WIRE_CONTRACT.md`.
- `soil_ec_ms_cm`, `water_flow_lpm`, and `water_pressure_bar` are all first-class MQTT fields as of migration 0011 (backend, 2026-08-04).
- `NODE=<id>` becomes the `node_id` in both the MQTT topic and the JSON payload.

If any of these three changes are unclear, ping and I will produce a full replacement `sketch.ino` file instead of the diff snippets.
