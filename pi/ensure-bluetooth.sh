#!/usr/bin/env bash
# Unblock + power on BT before BLE game (Pi often soft-blocks hci0 at boot).
set -uo pipefail

if [[ "${BODY_BT_UNBLOCK:-1}" == "0" ]]; then
  exit 0
fi

if command -v rfkill >/dev/null 2>&1; then
  if rfkill list 2>/dev/null | grep -A1 "Bluetooth" | grep -q "Soft blocked: yes"; then
    sudo -n rfkill unblock bluetooth 2>/dev/null || sudo rfkill unblock bluetooth 2>/dev/null || true
  fi
fi

if command -v bluetoothctl >/dev/null 2>&1; then
  bluetoothctl power on 2>/dev/null || sudo -n bluetoothctl power on 2>/dev/null || true
fi
