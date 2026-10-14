#!/usr/bin/env bash
# Unblock + LE-only + reset hci0 before BLE game (Pi Zero 2 W at cold boot).
set -uo pipefail

if [[ "${BODY_BT_UNBLOCK:-1}" == "0" ]]; then
  exit 0
fi

_sudo() {
  sudo -n "$@" 2>/dev/null || sudo "$@" 2>/dev/null || true
}

HCI="${BODY_BLE_HCI:-hci0}"

# Wait for adapter after bluetooth.service (kiosk often starts too early).
for _ in $(seq 1 45); do
  if _sudo hciconfig "$HCI" >/dev/null 2>&1 || bluetoothctl show "$HCI" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if command -v rfkill >/dev/null 2>&1; then
  _sudo rfkill unblock bluetooth
fi

if command -v btmgmt >/dev/null 2>&1; then
  _sudo btmgmt -i "$HCI" power off
  _sudo btmgmt -i "$HCI" le on
  _sudo btmgmt -i "$HCI" bredr off
  _sudo btmgmt -i "$HCI" power on
fi

if command -v hciconfig >/dev/null 2>&1; then
  _sudo hciconfig "$HCI" reset
fi

if command -v bluetoothctl >/dev/null 2>&1; then
  bluetoothctl power on 2>/dev/null || _sudo bluetoothctl power on
fi

sleep "${BODY_BLE_ADAPTER_SETTLE_S:-2}"
