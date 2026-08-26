# AgroGuardian Hardware Team Bring-Up Guide

This document is for the hardware/firmware team working on the physical AgroGuardian pilot hardware from a Windows laptop.

It explains only the hardware-facing work:

- how to flash the Sub Nodes;
- how to flash the Main Node;
- what values to put in firmware config;
- how to run serial monitors;
- how to prove that sensor readings reached the cloud;
- what logs/screenshots to send back to the software team.

Do not put real passwords, SIM PINs, or private credentials in GitHub, WhatsApp groups, screenshots, or shared documents.

---

## 1. System overview

The system has two MCU classes.

```text
Sub Node 1 ─┐
            ├─ LoRa 433 MHz ─> Main Node ── 4G/MQTTS ──> Cloud backend
Sub Node 2 ─┘
```

### Sub Node

Board class:

```text
ATmega328P-PU, 3.3 V, external 8 MHz crystal
```

Responsibilities:

- read sensors;
- format one CSV LoRa packet every ~5 seconds;
- include its unique node ID, for example `AGR-SN-0001`;
- transmit over LoRa only.

Sub Nodes do not connect to internet, Wi-Fi, MQTT, or the backend directly.

### Main Node

Board class:

```text
ESP32-WROOM-32 + SIMCom A7672S 4G modem + RA-02/SX1278 LoRa
```

Responsibilities:

- receive Sub Node CSV packets over LoRa;
- parse `NODE=...` and sensor values;
- map Sub Node ID to plot ID;
- build backend JSON;
- publish to cloud MQTT over TLS on port `8883`.

---

## 2. Values supplied by software team

The software team will provide these values.

Do not guess them.

```text
MQTT_HOST=mqtts-13-207-20-67.sslip.io
MQTT_PORT=8883
MQTT_USERNAME=main-node-001
MQTT_PASSWORD=<provided privately by software team>

PILOT_TENANT_ID=11111111-1111-1111-1111-111111111111
PILOT_FARMER_ID=aaaaaaaa-1111-1111-1111-111111111111
PILOT_FARM_ID=bbbbbbbb-2222-2222-2222-222222222222

MAIN_NODE_ID=AGR-MN-0001

SUB_NODE_1=AGR-SN-0001
SUB_NODE_2=AGR-SN-0002
```

Current plot mapping:

```text
AGR-SN-0001 -> PLOT_PILOT_001
AGR-SN-0002 -> PLOT_PILOT_003
```

Important: current firmware maps each Sub Node to one plot. Even if one physical Sub Node has sensors for two areas, the current firmware sends that Sub Node's reading to one plot only.

---

## 3. Repo folders you need

After cloning the repo, the firmware is here:

```text
firmware/
├── main_node/
│   ├── platformio.ini
│   ├── include/
│   │   └── pilot_config.h
│   └── src/
│       └── main.cpp
│
└── sub_node/
    ├── sub_node.ino
    └── eeprom_provisioner/
        └── eeprom_provisioner.ino
```

The backend wire contract is here, for reference:

```text
agro_backend/docs/HARDWARE_WIRE_CONTRACT.md
```

You normally do not need to edit backend files.

---

## 4. Windows setup

Install these on the Windows laptop.

### 4.1 Git

Install Git for Windows:

```text
https://git-scm.com/download/win
```

Clone the repo:

```powershell
git clone https://github.com/agroguardian17/agroai-staging.git
cd agroai-staging
```

If software team gives you a ZIP instead, extract it and open the extracted folder.

### 4.2 VS Code + PlatformIO

Install:

- Visual Studio Code
- PlatformIO extension inside VS Code

PlatformIO is used only for the ESP32 Main Node.

Optional command-line check:

```powershell
pio --version
```

If `pio` is not recognized, use VS Code PlatformIO buttons instead.

### 4.3 Arduino IDE + MiniCore

Install Arduino IDE 2.x.

Add MiniCore board manager URL:

```text
https://mcudude.github.io/MiniCore/package_MCUdude_MiniCore_index.json
```

Arduino IDE path:

```text
File -> Preferences -> Additional Boards Manager URLs
```

Then install:

```text
Tools -> Board -> Boards Manager -> search "MiniCore" -> Install
```

### 4.4 Drivers

Install the drivers that match your USB hardware:

- USBasp driver for ATmega328P ISP flashing;
- CH340 driver if the ESP32 board uses CH340 USB-serial;
- CP210x driver if the ESP32 board uses CP2102/CP210x USB-serial.

If Windows shows the board under Device Manager with a COM port, the serial driver is working.

---

## 5. Hardware wiring summary

Use the actual PCB/spec as final truth, but firmware currently assumes the following.

### 5.1 Sub Node ATmega328P pinout

```text
ATmega328P pin/function          Peripheral

D2   physical pin 4              LoRa DIO0
D3   physical pin 5              Status LED
D4   physical pin 6              DS18B20 data, with 4.7 kΩ pull-up to 3.3 V
D6   physical pin 12             RS485 MAX485 RO
D7   physical pin 13             RS485 MAX485 DI, RE/DE tied together
D8   physical pin 14             LoRa RST
D9   physical pin 15             Flow sensor OUT
D10  physical pin 16             LoRa NSS
A0   physical pin 23             Capacitive soil probe AOUT
A1   physical pin 24             Battery divider midpoint
A2   physical pin 25             RS485 rail power-enable
A3   physical pin 26             Pressure transducer signal
```

Power:

```text
3.3 V only for ATmega + LoRa RA-02.
Do not feed 5 V into RA-02 LoRa.
All modules must share common GND.
```

### 5.2 Main Node ESP32 assumed pinout

LoRa RA-02 / SX1278:

```text
SCK   -> GPIO18
MISO  -> GPIO19
MOSI  -> GPIO23
NSS   -> GPIO5
RST   -> GPIO14
DIO0  -> GPIO26
```

A7672S modem:

```text
ESP32 TX2 GPIO17 -> modem RX
ESP32 RX2 GPIO16 <- modem TX
GSM_PWR_PIN GPIO4 -> modem power key line
GND shared
```

If the PCB uses different modem pins, update:

```text
firmware/main_node/include/pilot_config.h
```

---

## 6. Flash Sub Node 1

Sub Node flashing is two-step.

Do not skip EEPROM provisioning.

### 6.1 Provision Sub Node ID

Open this file in Arduino IDE:

```text
firmware/sub_node/eeprom_provisioner/eeprom_provisioner.ino
```

For Sub Node 1, set:

```cpp
static const char* NODE_ID = "AGR-SN-0001";
```

Arduino IDE settings:

```text
Board: ATmega328
Clock: External 8 MHz
BOD: 2.7 V
Programmer: USBasp
Baud: 9600
```

Upload using programmer:

```text
Sketch -> Upload Using Programmer
```

Open Serial Monitor at:

```text
9600 baud
```

Expected output:

```text
AgroGuardian Sub Node — EEPROM provisioner
Target ID: AGR-SN-0001
EEPROM node ID written: AGR-SN-0001
Now flash firmware/sub_node/sub_node.ino to this board.
```

If this does not appear, do not continue. Fix board selection, programmer, wiring, or serial baud first.

### 6.2 Flash production Sub Node sketch

Open:

```text
firmware/sub_node/sub_node.ino
```

Upload using programmer.

Open Serial Monitor at:

```text
9600 baud
```

Expected boot output:

```text
AGRO GUARDIAN SUBNODE START
Node ID: AGR-SN-0001
```

Expected packet every ~5 seconds:

```text
NODE=AGR-SN-0001,BAT=...,BATP=...,DST=...,SOIL=...,PRESS=...,FLOW=...,NTEMP=...,NMOIST=...,EC=...,PH=...,N=...,P=...,K=...
```

If it says:

```text
Node ID: AGR-SN-UNSET
```

then EEPROM was not provisioned. Go back to section 6.1.

---

## 7. Flash Sub Node 2

Repeat the same process, but in the provisioner set:

```cpp
static const char* NODE_ID = "AGR-SN-0002";
```

Then flash:

```text
firmware/sub_node/sub_node.ino
```

Expected boot:

```text
AGRO GUARDIAN SUBNODE START
Node ID: AGR-SN-0002
```

Expected packet:

```text
NODE=AGR-SN-0002,...
```

---

## 8. Soil moisture calibration

The default soil calibration values are placeholders:

```cpp
#define DRY_ADC         800
#define WET_ADC         250
```

They are in:

```text
firmware/sub_node/sub_node.ino
```

Every capacitive probe can differ. Calibrate per probe.

### Calibration procedure

1. Flash the production sketch.
2. Open Serial Monitor at `9600`.
3. Keep the soil probe in air.
4. Read this value:

```text
Soil raw : <number>
```

5. Put the probe in water to the same depth that will be buried.
6. Wait 30 seconds.
7. Read:

```text
Soil raw : <number>
```

8. Edit:

```cpp
#define DRY_ADC   <air reading>
#define WET_ADC   <water reading>
```

9. Reflash production sketch.

Expected:

```text
Probe in air   -> Soil VWC near 0%
Probe in water -> Soil VWC near 100%
```

If `Soil VWC` is stuck at `0` or `100`, calibration constants are wrong or the sensor signal wiring is wrong.

---

## 9. Configure Main Node

Open this file:

```text
firmware/main_node/include/pilot_config.h
```

Set cloud endpoint:

```cpp
#define MQTT_HOST         "mqtts-13-207-20-67.sslip.io"
#define MQTT_PORT         8883
```

Set MQTT credentials:

```cpp
#define MQTT_USERNAME     "main-node-001"
#define MQTT_PASSWORD     "<MQTT_PASSWORD_FROM_SOFTWARE_TEAM>"
```

Keep these pilot IDs unless software team tells you otherwise:

```cpp
#define PILOT_TENANT_ID   "11111111-1111-1111-1111-111111111111"
#define PILOT_FARMER_ID   "aaaaaaaa-1111-1111-1111-111111111111"
#define PILOT_FARM_ID     "bbbbbbbb-2222-2222-2222-222222222222"
#define MAIN_NODE_ID      "AGR-MN-0001"
```

Check Sub Node mapping:

```cpp
#define NUM_SUB_NODES     2

static const SubNodeMapping SUB_NODE_MAP[NUM_SUB_NODES] = {
    {"AGR-SN-0001", "PLOT_PILOT_001"},
    {"AGR-SN-0002", "PLOT_PILOT_003"},
};
```

If you use a different Sub Node ID, this map must be updated.

Check SIM APN:

```cpp
#define GSM_APN           "bsnlnet"
#define GSM_USER          ""
#define GSM_PASS          ""
#define GSM_PIN           ""
```

If the SIM is not BSNL, change `GSM_APN`.

Common Indian APN examples:

```text
BSNL:     bsnlnet
Airtel:   airtelgprs.com
Jio:      jionet
Vi:       www
```

Confirm with the SIM provider if unsure.

---

## 10. Build and flash Main Node

Use VS Code with PlatformIO.

Open folder:

```text
firmware/main_node
```

Or use PowerShell:

```powershell
cd firmware\main_node
pio run
```

If build succeeds:

```powershell
pio run -t upload
```

Open serial monitor:

```powershell
pio device monitor -b 115200
```

Expected boot:

```text
[boot] AgroGuardian Main Node v0.1
[modem] power-cycling A7672S
[modem] init
[gsm] waiting for LTE registration
[gsm] network OK, opening PDP context
[gsm] IP: 10.x.y.z
[ntp] time = 2026-08-xxTxx:xx:xxZ
[lora] listening on 433000000 Hz
[mqtt] connecting as AGR-MN-0001-xxxxxxxx
[mqtt] connected
[boot] ready
```

If PlatformIO build fails, copy the full error output and send it to the software team.

---

## 11. End-to-end bench test

Do this in order.

### 11.1 Start Main Node

Power Main Node and open serial monitor:

```powershell
pio device monitor -b 115200
```

Wait for:

```text
[mqtt] connected
[boot] ready
```

### 11.2 Start Sub Node 1

Power Sub Node 1.

Sub Node serial should show:

```text
NODE=AGR-SN-0001,...
```

Main Node serial should show:

```text
[lora] RX ... bytes rssi=... snr=...
[lora] payload: NODE=AGR-SN-0001,...
[mqtt] publish OK -> agro/v2/.../AGR-SN-0001/telemetry
```

### 11.3 Start Sub Node 2

Power Sub Node 2.

Main Node should show:

```text
[lora] payload: NODE=AGR-SN-0002,...
[mqtt] publish OK -> agro/v2/.../AGR-SN-0002/telemetry
```

### 11.4 Ask software team to verify cloud database

Tell the software team:

```text
Please check latest node_sensor_readings for AGR-SN-0001 and AGR-SN-0002.
```

They will run:

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U agro -d agro -c \
  "SELECT node_id, plot_id, recorded_at, soil_moisture_avg_pct, water_flow_lpm, water_pressure_bar, soil_ec_ms_cm, soil_ph
   FROM node_sensor_readings
   ORDER BY recorded_at DESC
   LIMIT 10;"
```

If the software team sees fresh rows, the full hardware-to-cloud loop is working.

---

## 12. What a valid Sub Node CSV packet looks like

Example:

```text
NODE=AGR-SN-0001,BAT=9.38,BATP=100,DST=27.4,SOIL=41.9,PRESS=5.31,FLOW=8.00,NTEMP=29.1,NMOIST=35.7,EC=1.045,PH=6.45,N=58,P=79,K=197
```

Fields:

```text
NODE   Sub Node ID from EEPROM
BAT    battery voltage
BATP   battery percent
DST    DS18B20 soil/surface temperature, °C
SOIL   calibrated soil moisture percent, 0..100
PRESS  water pressure, bar
FLOW   water flow, litres/minute
NTEMP  NPK probe temperature, °C
NMOIST NPK probe moisture, currently ignored by Main Node
EC     soil EC, mS/cm
PH     soil pH
N      nitrogen, mg/kg
P      phosphorus, mg/kg
K      potassium, mg/kg
```

Missing values are sent as:

```text
NAN
```

Main Node drops `NAN` values from the JSON payload.

---

## 13. What Main Node publishes to cloud

MQTT topic:

```text
agro/v2/<tenant_id>/<farm_id>/<sub_node_id>/telemetry
```

For Sub Node 1:

```text
agro/v2/11111111-1111-1111-1111-111111111111/bbbbbbbb-2222-2222-2222-222222222222/AGR-SN-0001/telemetry
```

Payload shape:

```json
{
  "$schema": "agro-guardian/telemetry/v2",
  "tenant_id": "11111111-1111-1111-1111-111111111111",
  "farmer_id": "aaaaaaaa-1111-1111-1111-111111111111",
  "farm_id": "bbbbbbbb-2222-2222-2222-222222222222",
  "plot_id": "PLOT_PILOT_001",
  "node_id": "AGR-SN-0001",
  "recorded_at": "2026-08-xxTxx:xx:xx+00:00",
  "received_at_master": "2026-08-xxTxx:xx:xx+00:00",
  "transmission_type": "lora",
  "signal_rssi_dbm": -72,
  "soil_moisture_avg_pct": 41.9,
  "water_pressure_bar": 5.31,
  "water_flow_lpm": 8.0,
  "soil_ec_ms_cm": 1.045,
  "soil_ph": 6.45
}
```

Do not add extra JSON fields unless software team updates the backend schema. Unknown fields are rejected.

---

## 14. Troubleshooting

### A7672S shows `+CMQTTCONNECT: 0,32`

Meaning:

```text
TCP reached mqtts-13-207-20-67.sslip.io:8883, but TLS handshake failed.
```

This is not a normal username/password error. It is almost always one of:

- modem clock is wrong;
- modem does not trust Let's Encrypt ISRG Root X1;
- modem is not sending SNI;
- modem and server cannot agree on certificate/cipher settings.

Software team has configured the server side to use RSA Let's Encrypt certificates for the A7672S. Hardware team must configure the modem side before MQTT connect.

Run these AT commands after SIM/network/PDP data attach, but before `AT+CMQTTCONNECT`.

#### 1. Sync modem clock

```text
AT+CNTP="pool.ntp.org",22,1,2
AT+CNTP
AT+CCLK?
```

`AT+CCLK?` must show the real current year. If it shows `1970`, `2000`, or a clearly wrong date, TLS will fail.

#### 2. Load Let's Encrypt root CA once

Upload ISRG Root X1 to the modem filesystem as:

```text
isrgrootx1.pem
```

Use the modem command:

```text
AT+CCERTDOWN="isrgrootx1.pem",<length>
> <paste PEM contents>
```

Do this once per modem, then keep a firmware/NVS flag so normal boots do not upload it repeatedly.

#### 3. Configure SSL context 0

```text
AT+CSSLCFG="sslversion",0,4
AT+CSSLCFG="authmode",0,2
AT+CSSLCFG="cacert",0,"isrgrootx1.pem"
AT+CSSLCFG="enableSNI",0,1
```

The most important line is:

```text
AT+CSSLCFG="enableSNI",0,1
```

Without SNI, Caddy may not serve the `mqtts-13-207-20-67.sslip.io` certificate during the TLS handshake.

#### 4. Bind SSL context to MQTT and connect

```text
AT+CMQTTSTART
AT+CMQTTACCQ=0,"AGR-MN-0001",1
AT+CMQTTSSLCFG=0,0
AT+CMQTTCONNECT=0,"tcp://mqtts-13-207-20-67.sslip.io:8883",60,1,"main-node-001","<MQTT_PASSWORD_FROM_SOFTWARE_TEAM>"
```

Expected success:

```text
+CMQTTCONNECT: 0,0
```

If it still returns:

```text
+CMQTTCONNECT: 0,32
```

send the software team:

- full AT log from `AT+CNTP` through `AT+CMQTTCONNECT`;
- output of `AT+CCLK?`;
- exact `AT+CSSLCFG` commands used;
- modem model/firmware version;
- SIM operator/APN.

For temporary diagnosis only, hardware may try:

```text
AT+CSSLCFG="authmode",0,0
```

If connection works with `authmode=0`, the problem is CA trust or clock validation. Do not leave `authmode=0` in field firmware.

### Sub Node shows `AGR-SN-UNSET`

Cause:

```text
EEPROM provisioner was not flashed, or flashed with wrong settings.
```

Fix:

```text
Flash eeprom_provisioner.ino with correct NODE_ID, then flash sub_node.ino again.
```

### Sub Node serial works but Main Node sees no LoRa packets

Check:

- LoRa frequency is `433E6` on both sides.
- RA-02 powered with 3.3 V, not 5 V.
- Antennas connected.
- SPI wiring correct.
- `NSS`, `RST`, `DIO0` pins match firmware.
- Boards are close enough during bench test.

### Main Node says `[modem] init FAILED`

Check:

- modem has enough power;
- modem power key wiring;
- ESP32 TX/RX crossed correctly;
- `GSM_TX_PIN` and `GSM_RX_PIN` in `pilot_config.h`;
- common GND between ESP32 and modem.

### Main Node says `[gsm] network timeout`

Check:

- SIM inserted;
- SIM active with data plan;
- antenna connected;
- APN correct;
- SIM PIN disabled, or set `GSM_PIN`;
- cellular coverage.

### Main Node says `[mqtt] connect FAILED, state=5`

Cause:

```text
Bad MQTT username/password.
```

Fix:

- confirm `MQTT_USERNAME` is exactly `main-node-001`;
- confirm `MQTT_PASSWORD` matches the password supplied by software team;
- reflash Main Node.

### Main Node says `[mqtt] connect FAILED, state=-2`

Likely:

- cellular data is not actually working;
- TLS connection failed;
- hostname wrong;
- port `8883` blocked by network/carrier;
- cloud broker unavailable.

Send Main Node serial logs to software team.

### Main Node says `unknown Sub Node id`

Cause:

```text
NODE=... in Sub Node packet is not present in SUB_NODE_MAP.
```

Fix either:

- provision Sub Node EEPROM with correct ID; or
- update `SUB_NODE_MAP` in Main Node and reflash.

### Main Node says `publish OK`, but software team sees no DB row

Send software team:

- Main Node serial monitor lines around publish;
- exact `NODE=...` packet;
- timestamp of test;
- MQTT host/port used;
- Sub Node ID used.

Software team will check backend logs.

---

## 15. Required evidence to send after testing

After a bench test, send the software team:

1. Photo of Main Node wiring.
2. Photo of Sub Node wiring.
3. Screenshot/text of Sub Node serial output showing:

```text
Node ID: AGR-SN-0001
NODE=AGR-SN-0001,...
```

4. Screenshot/text of Main Node serial output showing:

```text
[mqtt] connected
[lora] payload: NODE=AGR-SN-0001,...
[mqtt] publish OK
```

5. Which SIM/operator/APN was used.
6. Which Sub Node IDs were flashed.
7. Any error logs exactly as printed.

---

## 16. Security rules

Never commit real secrets.

Before pushing code, reset this line:

```cpp
#define MQTT_PASSWORD "REPLACE_WITH_PROVISIONED_PASSWORD"
```

Do not share:

- MQTT password in public repo;
- SIM PIN;
- AWS keys;
- private SSH keys;
- screenshots showing `.env` secrets.

---

## 17. Current limitations

Current firmware is enough for pilot bench testing, but these are not built yet:

- OTA updates;
- MicroSD offline buffering;
- QoS 1 MQTT publish;
- multiple plots per one Sub Node;
- heartbeat topic;
- remote firmware signing/secure boot.

For now, send only `telemetry` messages.

---

## 18. Final success condition

Hardware test is successful only when all three are true:

```text
1. Sub Node serial prints NODE=AGR-SN-0001 or NODE=AGR-SN-0002.
2. Main Node serial prints [mqtt] publish OK.
3. Software team confirms a fresh row in node_sensor_readings.
```

If any one of these is missing, the loop is not fully working yet.
