# Controller wiring (one unit)

Build **two** identical chains; MPU, power, and I2C are the same on both. The **only** hardware change vs the old plan: **remove the boy/girl rocker (GPIO4)** — keep the **same momentary button on GPIO5** (red on one unit, blue on the other).

**Legend:** Flash sets **starting** hero (**blue** unit → `make flash-blue` = boy at boot; **red** → `make flash-red` = girl). **Short press GPIO5** toggles boy/girl while playing (replaces the old rocker). **GPIO4** unused.

---

## Block diagram

```mermaid
flowchart TB
  subgraph POWER["Power path"]
    BAT["LiPo 3.7 V<br/>B+ / B−"]
    CHG["USB-C charge board<br/>(B+ B− in/out)"]
    BST["LX-LCBST boost<br/>B+ B− → VO+ VO−"]
    BAT --- CHG
    CHG --- BST
  end

  subgraph MCU["ESP32-C3 SuperMini"]
    ESP5V["5V pin"]
    ESP3V["3V3 pin"]
    ESPGND["GND"]
    GPIO8["GPIO8 SDA"]
    GPIO9["GPIO9 SCL"]
    GPIO5["GPIO5 power btn"]
  end

  subgraph IMU["GY-521 MPU-6050"]
    MVCC["VCC"]
    MGND["GND"]
    MSDA["SDA"]
    MSCL["SCL"]
    MAD0["AD0 → GND"]
  end

  subgraph SW["Switch"]
    PB["Blue or Red<br/>momentary button<br/>(hero set at flash)"]
  end

  BST -->|"VO+ 5 V"| ESP5V
  BST -->|"VO−"| ESPGND
  ESP3V --> MVCC
  ESPGND --- MGND
  GPIO8 --- MSDA
  GPIO9 --- MSCL
  MAD0 --- MGND

  GPIO5 --- PB
  PB --- ESPGND

  subgraph PI["Game console (separate)"]
    PIZ["Pi Zero 2 W"]
  end

  MCU -.->|"BLE"| PIZ
```

---

## Signal diagram (GPIO only)

```mermaid
flowchart LR
  MPU["MPU-6050"]
  ESP["SuperMini"]

  MPU -->|"VCC ← 3V3"| ESP
  MPU -->|"GND"| ESP
  MPU -->|"SDA"| ESP
  MPU -->|"SCL"| ESP
  MPU -->|"AD0 → GND (addr 0x68)"| ESP

  BTN["Blue or red power button"]
  BTN -->|"leg 1 → GPIO5"| ESP
  BTN -->|"leg 2 → GND"| ESP
```

---

## Power button (do not wire in battery path)

```mermaid
stateDiagram-v2
  direction LR
  [*] --> Running: Short press / boot
  Running --> Running: Play game BLE on
  Running --> Sleep: Long press ~2s GPIO5
  Sleep --> Running: Press GPIO5 wake
  note right of Running
    5V from LX-LCBST
    stays on SuperMini
    (soft power / deep sleep)
  end note
```

---

## Pin table (SuperMini)

| GY-521 | → | SuperMini |
|--------|---|-----------|
| VCC | → | **3V3** |
| GND | → | **GND** |
| **SDA** | → | **GPIO8** (ESP **SDA** — not SCL) |
| **SCL** | → | **GPIO9** (ESP **SCL** — not SDA) |

**Do not cross:** ESP SDA → MPU **SDA**, ESP SCL → MPU **SCL**.  
If ESP SDA is on MPU **SCL**, the bus will NACK / scan empty — swap the two data wires.
| AD0 | → | **GND** |
| INT, XDA, XCL | | *not used* |

| Switch | → | SuperMini |
|--------|---|-----------|
| Hero / power button (blue or red cap) | → | **GPIO5** ↔ **GND** (or **GPIO4** if you reused the old rocker pads) |

| Power | → | SuperMini |
|-------|---|-----------|
| LX-LCBST VO+ | → | **5V** |
| LX-LCBST VO− | → | **GND** |

---

## Physical layout (belt clip)

```mermaid
flowchart TB
  subgraph Pouch["Belt pouch"]
    ESP["SuperMini + perfboard"]
    CHG["Charger + LX-LCBST"]
    BAT["LiPo"]
    BTN["Blue or red power btn"]
  end

  subgraph Belt["On belt strap"]
    MPU["GY-521 on foam<br/>mark FORWARD → TV"]
  end

  Pouch ---|"short flex wires"| Belt
```

---

## Open schematic

**Visual schematic**

- [wiring-schematic.svg](./wiring-schematic.svg) — fixed ASCII-only text (invalid XML chars broke preview before)
- [wiring-schematic.html](./wiring-schematic.html) — open in browser if Cursor SVG preview is blank
