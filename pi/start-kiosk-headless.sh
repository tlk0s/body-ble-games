#!/usr/bin/env bash
# Kiosk without desktop (SDL kmsdrm). Use with systemd body-ble-games-kiosk.service.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
LOG="${BODY_KIOSK_LOG:-$ROOT/kiosk-update.log}"
UPDATE_ON_START="${BODY_UPDATE_ON_START:-0}"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Missing .venv" >&2
  exit 1
fi

if [[ "$UPDATE_ON_START" != "0" ]]; then
  {
    echo "=== $(date -Iseconds) headless kiosk start ==="
    git -C "$REPO" pull --ff-only || true
    "$ROOT/.venv/bin/pip" install -q -r "$ROOT/requirements.txt" || true
  } >>"$LOG" 2>&1
fi

chmod +x "$ROOT/ensure-bluetooth.sh" 2>/dev/null || true
"$ROOT/ensure-bluetooth.sh" >>"$LOG" 2>&1 || true

cd "$ROOT"
export MOCK_BLE=0
export BODY_FULLSCREEN=1
export BODY_GAME="${BODY_GAME:-blob_jump}"
export BODY_FPS="${BODY_FPS:-30}"
export BODY_MUSIC="${BODY_MUSIC:-0}"
export BODY_HDMI_720=0

unset DISPLAY
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-kmsdrm}"
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-alsa}"

exec "$ROOT/.venv/bin/python" main.py
