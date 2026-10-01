"""BLE central: scan BodyCtrl*, connect up to 2, forward flags to PlayerManager."""

from __future__ import annotations

import asyncio
import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable, Literal, Optional

from ble_protocol import INPUT_CHAR_UUID, NAME_PREFIX, parse_input_packet
from players import PlayerManager

STALE_NOTIFY_S = 2.5


@dataclass
class _BleEvent:
    kind: Literal["notify", "leave"]
    address: str
    flags: int = 0


class BleManager:
    MAX_DEVICES = 2

    def __init__(self, players: PlayerManager) -> None:
        self.players = players
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._queue: queue.Queue[_BleEvent] = queue.Queue()
        self.last_error: str = ""
        self.status: str = "starting"
        self._address_to_slot: dict[str, int] = {}
        self._last_notify_at: dict[str, float] = {}
        self.last_flags: int = 0
        self.notify_count: int = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._thread_main, name="ble-manager", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _handle_leave(self, address: str) -> None:
        self._address_to_slot.pop(address, None)
        self._last_notify_at.pop(address, None)
        self.players.disconnect(address)
        self.status = "waiting for controller…"

    def _check_stale(self) -> None:
        now = time.monotonic()
        for address in list(self._address_to_slot.keys()):
            last = self._last_notify_at.get(address, 0.0)
            if last and now - last > STALE_NOTIFY_S:
                self._handle_leave(address)

    def poll(self) -> None:
        """Call from pygame main thread each frame."""
        while True:
            try:
                ev = self._queue.get_nowait()
            except queue.Empty:
                break
            if ev.kind == "leave":
                self._handle_leave(ev.address)
                continue
            self._last_notify_at[ev.address] = time.monotonic()
            slot = self._address_to_slot.get(ev.address)
            if slot is None:
                slot = self.players.connect(ev.address, hero_girl=bool(ev.flags & 0x10))
                if slot is None:
                    continue
                self._address_to_slot[ev.address] = slot
                self.status = f"connected ({self.players.active_count()})"
            self.players.apply_flags(slot, ev.flags)

        self._check_stale()

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._async_main())
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            self.status = "error"

    async def _async_main(self) -> None:
        from bleak import BleakClient, BleakScanner

        clients: dict[str, BleakClient] = {}

        def schedule_leave(address: str) -> None:
            self._queue.put(_BleEvent("leave", address))

        def make_handler(address: str) -> Callable:
            def _on_notify(_handle: int, data: bytearray) -> None:
                _seq, flags = parse_input_packet(data)
                self.last_flags = flags
                self.notify_count += 1
                self._queue.put(_BleEvent("notify", address, flags))

            return _on_notify

        def make_disconnect_cb(address: str) -> Callable:
            def _on_disconnect(_client: BleakClient) -> None:
                clients.pop(address, None)
                schedule_leave(address)

            return _on_disconnect

        async def connect_one(device) -> None:
            address = device.address
            if address in clients:
                return
            self.status = f"connecting {device.name or address}…"

            client = BleakClient(
                device,
                timeout=20.0,
                disconnected_callback=make_disconnect_cb(address),
            )
            await client.connect()
            await client.start_notify(INPUT_CHAR_UUID, make_handler(address))
            clients[address] = client
            self.status = f"connected {len(clients)}/{self.MAX_DEVICES}"
            self.last_error = ""

        while not self._stop.is_set():
            # Drop dead clients so scan can reconnect the same remote
            dead = [addr for addr, c in clients.items() if not c.is_connected]
            for addr in dead:
                clients.pop(addr, None)
                schedule_leave(addr)

            if len(clients) < self.MAX_DEVICES:
                self.status = "scanning…"
                try:
                    device = await BleakScanner.find_device_by_filter(
                        lambda d, _ad: bool(d.name and d.name.startswith(NAME_PREFIX)),
                        timeout=4.0,
                    )
                except Exception as exc:  # noqa: BLE001
                    self.last_error = str(exc)
                    device = None
                if device is not None and device.address not in clients:
                    try:
                        await connect_one(device)
                    except Exception as exc:  # noqa: BLE001
                        self.last_error = str(exc)
                        self.status = "connect failed"
            await asyncio.sleep(0.5)

        for client in list(clients.values()):
            try:
                await client.disconnect()
            except Exception:  # noqa: BLE001
                pass
        clients.clear()
        self.status = "stopped"
