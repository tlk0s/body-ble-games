#!/usr/bin/env bash
# Manual BLE prep (same as boot ensure-bluetooth, but stops kiosk first).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Stopping kiosk if it holds the adapter…"
sudo systemctl stop body-ble-games-kiosk.service 2>/dev/null || true
pkill -f 'python.*main.py' 2>/dev/null || true

"$ROOT/ensure-bluetooth.sh"

echo "Done. Test: cd $ROOT && .venv/bin/python ble_connect_test.py"
echo "Tip: if connect fails with Wi-Fi on, try: sudo rfkill block wlan"
