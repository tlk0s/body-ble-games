# Motion test sketch (Serial)

Tests **jump**, **duck**, **sidestep left/right**. Same wiring as before except **no rocker** — only the **GPIO5** push button (blue vs red cap). Flash boy/girl firmware to match that cap.

## Power

Use **USB-C on the SuperMini** only (no LiPo needed for this test).

## Flash (make or PlatformIO)

```bash
cd firmware/motion_test
make deploy          # build + upload + serial log
# or:
make build
make upload
make monitor
make ports           # find PORT after plug-in (name changes every replug)
make m PORT=...      # same as monitor
```

```bash
pio run -t upload
pio device monitor -b 115200
```

Arduino IDE: open `src/main.cpp` as a sketch or copy into a `.ino` with the same `#include` setup; install **Adafruit MPU6050** + **Unified Sensor** libraries.

## Use

1. Serial Monitor **115200** on the **usbmodem** port (same as upload).
2. **Press RST** after opening the monitor if the log is empty.
3. **Calibrate:** stand still ~**5 s** facing the TV (`c` to redo anytime).
4. **Profiles:** `d` = Dino (jump/duck), `l` = Lane (sidestep), `a` = test all. Tune thresholds in `include/motion_config.h`; send `?` in the serial monitor for keys.
5. Tune thresholds in **`include/motion_config.h`** only.
3. **Jump** → `[JUMP]`
4. **Squat / duck** → `[DUCK] ON` / `[DUCK] OFF`
5. **Sidestep** in place → `[STEP] LEFT` or `[STEP] RIGHT`
6. On boot → `[HERO] BOY (blue)` or `[HERO] GIRL (pink)` (default from flash-blue vs flash-red).
7. **Short press** the GPIO5 button (release) → toggles boy/girl and prints `[HERO] …` again.
8. Send **`#`** in serial monitor for one line of raw accel + tuning values.

### Flash per physical controller

```bash
make flash-blue PORT=/dev/cu.usbmodem…   # blue unit: boots as boy
make flash-red  PORT=/dev/cu.usbmodem…   # red unit: boots as girl
```

## I2C fix (MPU not found)

1. **Power:** GY-521 **VCC → ESP 3V3** (not 5V pin unless your module docs say so). **GND → GND**.
2. **Data (straight, not crossed):** MPU **SDA** → ESP **GPIO8**, MPU **SCL** → ESP **GPIO9**.  
   **Wrong:** ESP SDA → MPU SCL (causes NACK / no devices).
3. **AD0 → GND** (address **0x68**). Floating or 3V3 → **0x69** (firmware tries both).
4. Re-flash, RST, read **I2C scan** in log. **No devices** = wiring/power; **0x68 seen** = press **`r`** or reflash (raw driver handles clone chips).
5. **Scan sees 0x68 but “Adafruit begin failed”** — common on GY-521 clones; new firmware uses **raw driver** after printing `WHO_AM_I`.
6. Keep the **SDA/SCL orientation where scan finds 0x68**; `(no devices)` after swap = try the other way or resolder 3V3/GND.
5. Alt pins on some boards: `pio run -e esp32-c3-supermini-i2c67 -t upload` (SDA=6, SCL=7).

## Tuning

Edit thresholds at top of `src/main.cpp`:

| Constant | Default | If… |
|----------|---------|-----|
| `JUMP_VERT_MPS2` | 2.8 | misses jumps → lower; false jumps → raise |
| Sidestep | auto | 2 s stillness sets jerk threshold; needs strong shuffle |
| `STEP_FWD_BLOCK_DEG` | 20 | forward tilt only; sidestep still allowed |
| `DUCK_PITCH_DEG` | 22 | duck too hard → lower |

If left/right feel wrong, edit `INVERT_SIDESTEP` in `include/motion_config.h`. Hero is set by **which firmware** you flash (blue vs red), not at runtime.

**MPU faces TV:** set `FWD_AXIS` in `platformio.ini` (default **2** = chip **+Z** toward TV). If forward tilt still triggers STEP, try `0`, `1`, or `5` until `#` shows `fTiltD` changing on forward tilt but not `latJ`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| **No `/dev/cu.usbmodem*` at all** | macOS does not see the board on USB yet (not a wrong number). Use a **data** USB-C cable; plug **directly** into the Mac; for bench test use **USB on the SuperMini only** (disconnect LiPo/boost if wired). Run `make usb-check` — you should see **Espressif** or **USB JTAG/serial**. If nothing appears: try another cable/port, bare board without perfboard, or hold **BOOT**, tap **RST**, release **BOOT** (download mode). |
| **`Resource busy` on upload** | Another app has the port. Close Serial Monitor / `pio device monitor` / Arduino IDE. Then `make port-users` and `make free-port`, or `make flash PORT=/dev/cu.usbmodem…` |
| **Monitor blank** | Re-flash after USB CDC fix: `make flash`. Open monitor, **press RST**, wait for `[alive]`. Wrong port = no data (use `make ports`). |
| MPU not found | See **I2C fix** below; serial `s` = rescan, `r` = retry init |
| No sidesteps | Step wider; lower `STEP_LAT_MPS2`; belt mount later |
| Duck never triggers | Bend forward more; lower `DUCK_PITCH_DEG` |
