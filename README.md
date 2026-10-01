# Body BLE Games

Motion-controlled games for **Raspberry Pi Zero 2 W** and **ESP32-C3** belt clips (MPU-6050 GY-521, BLE). **Blue** push-button remote = boy hero; **red** = girl (set when you flash firmware).

## Games

1. **BlobJump** — runner; **jump** and **duck**; blue / pink blobs.
2. **Lane Race** — Three-lane endless road; **sidestep** left/right; blue / pink cars.

Up to two controllers; second device **hot-joins** when powered on.

## Wiring

- [docs/hardware-wiring.md](docs/hardware-wiring.md) — Mermaid block diagrams + pin table  
- [docs/wiring-schematic.html](docs/wiring-schematic.html) — wiring diagram (open in browser)  
- [docs/wiring-schematic.svg](docs/wiring-schematic.svg) — same diagram as SVG

## Pi (dev)

```bash
cd pi
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run
# or: MOCK_BLE=1 .venv/bin/python main.py
```

**Dev (keyboard):** **1** / **2** pick game; **Space** jump, **Down** duck, **A/D** sidestep, **B/G** boy/girl; **J** hot-join P2.

**Pi / belt only (`MOCK_BLE=0`):** **jump** / **sidestep** pick the game. **Exit to menu:** power off **all** remotes (~2s). Quit app: close the window or stop the launcher on the Pi.

**Kiosk (full screen + autostart):** `pi/start-kiosk.sh` runs `git pull` + `pip install` on every start, then launches with `BODY_FULLSCREEN=1`. See `pi/systemd/` and `pi/autostart/` for examples.

## Status

- **Done:** motion test firmware (USB serial), Pi launcher + mock input + playground games
- **Next:** flash `firmware/body_controller`, run `MOCK_BLE=0 ./run` on Pi/Mac with Bluetooth on
