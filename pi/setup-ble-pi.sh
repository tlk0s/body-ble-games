#!/usr/bin/env bash
# One-time / before-play: LE-only + unblock BT (helps br-connection-canceled on Pi Zero 2 W).
set -uo pipefail

echo "Stopping kiosk if it holds the adapter (optional)…"
sudo systemctl stop body-ble-games-kiosk.service 2>/dev/null || true

sudo rfkill unblock bluetooth 2>/dev/null || true

if command -v btmgmt >/dev/null 2>&1; then
  HCI="${BODY_BLE_HCI:-hci0}"
  sudo btmgmt -i "$HCI" power off 2>/dev/null || true
  sudo btmgmt -i "$HCI" le on 2>/dev/null || true
  sudo btmgmt -i "$HCI" bredr off 2>/dev/null || true
  sudo btmgmt -i "$HCI" power on 2>/dev/null || true
fi

if command -v bluetoothctl >/dev/null 2>&1; then
  bluetoothctl power on 2>/dev/null || sudo bluetoothctl power on 2>/dev/null || true
fi

if command -v hciconfig >/dev/null 2>&1; then
  sudo hciconfig hci0 reset 2>/dev/null || true
fi

echo "Done. Test: cd $(dirname "$0") && .venv/bin/python ble_connect_test.py"
echo "Tip: if connect still fails, try: sudo rfkill block wlan  (Wi-Fi/BT interference test)"
