#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

find_port() {
  for pattern in /dev/cu.usbmodem* /dev/cu.wchusbserial* /dev/cu.SLAB_USBtoUART* /dev/cu.usbserial*; do
    for p in $pattern; do
      [[ -e "$p" ]] || continue
      echo "$p"
      return 0
    done
  done
  return 1
}

if ! PORT=$(find_port); then
  echo "No ESP32 USB serial port found."
  echo "Plug the SuperMini in via USB-C, then run this script again."
  echo ""
  echo "Current /dev/cu.* ports:"
  ls /dev/cu.* 2>/dev/null || true
  exit 1
fi

echo "Using port: $PORT"
if PIDS=$(lsof -t "$PORT" 2>/dev/null); then
  echo "Port busy — stopping: $PIDS (close Serial Monitor yourself if you prefer)"
  kill $PIDS 2>/dev/null || true
  sleep 0.5
fi
pio run -t upload --upload-port "$PORT"
echo ""
echo "=== Serial log (115200). Ctrl+C to stop. Reset board if you see nothing. ==="
pio device monitor --port "$PORT" -b 115200
