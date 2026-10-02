# Body BLE controller firmware

Same motion engine as `motion_test`, plus **BLE notify** to the Pi (advertises as `BodyCtrl-XXXX`).

## Get the repo

```bash
git clone https://github.com/tlk0s/body-ble-games.git
cd body-ble-games
# updates:
git pull
```

Requires [PlatformIO](https://platformio.org/) (CLI or VS Code extension).

## Flash

Plug the SuperMini in over **USB-C** (data cable). Close any serial monitor using the same port.

```bash
cd firmware/body_controller
make ports
make flash-blue PORT=/dev/cu.usbmodem101   # blue button → boy hero at boot
make flash-red  PORT=/dev/cu.usbmodem101   # red button → girl hero at boot
```

Windows: `pio run -e esp32-c3-blue-boy -t upload --upload-port COM3` (or `esp32-c3-red-girl`).

After upload, check Bluetooth on a phone or PC for **BodyCtrl-…**.

## Serial debug (optional)

```bash
make monitor PORT=/dev/cu.usbmodem101
```

115200 baud — `c` calibrate, motion events same as `motion_test`. Pi uses the service UUID in `pi/ble_protocol.py`.
