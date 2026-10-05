#!/usr/bin/env python3
"""Minimal BLE connect test (no pygame). Run on Pi with belt powered on."""

from __future__ import annotations

import asyncio
import sys

from ble_protocol import INPUT_CHAR_UUID, NAME_PREFIX, SERVICE_UUID, parse_input_packet


async def main() -> int:
    from bleak import BleakClient, BleakScanner

    print("Scanning for", NAME_PREFIX + "* …")
    device = await BleakScanner.find_device_by_filter(
        lambda d, _ad: bool(d.name and d.name.startswith(NAME_PREFIX)),
        timeout=12.0,
    )
    if device is None:
        print("No BodyCtrl found. Power the belt; check phone BT scan.")
        return 1

    addr = device.address
    print(f"Found {device.name} @ {addr}")
    # Let the adapter finish scanning before connect (avoids br-connection-canceled on Pi).
    await asyncio.sleep(2.0)

    for attempt in range(1, 5):
        print(f"Connect attempt {attempt}/4 …")
        client = BleakClient(device, timeout=25.0, services=[SERVICE_UUID])
        try:
            await asyncio.sleep(0.5 * attempt)
            await client.connect()
            await asyncio.sleep(0.6)

            def on_notify(_handle: int, data: bytearray) -> None:
                seq, flags = parse_input_packet(data)
                print(f"  notify seq={seq} flags=0x{flags:02X}")

            await client.start_notify(INPUT_CHAR_UUID, on_notify)
            print("OK — connected and subscribed. Jump the belt (Ctrl+C to quit).")
            await asyncio.sleep(15.0)
            await client.disconnect()
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL: {exc}")
            try:
                if client.is_connected:
                    await client.disconnect()
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(1.5)

    print("All attempts failed.")
    return 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
