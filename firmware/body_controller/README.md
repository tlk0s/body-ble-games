# Body BLE controller firmware

Same motion engine as `motion_test`, plus **BLE notify** to the Pi (`BodyCtrl-XXXX` name).

## Flash

```bash
cd firmware/body_controller
make flash-blue PORT=/dev/cu.usbmodem…
make flash-red  PORT=/dev/cu.usbmodem…
```

Serial 115200 still works for calibration (`c`) and debug. Pi uses service UUID in `pi/ble_protocol.py`.
