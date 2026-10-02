#!/usr/bin/env bash
# Kiosk without desktop (SDL kmsdrm / fbcon). Use with systemd body-ble-games-kiosk.service.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
LOG="${BODY_KIOSK_LOG:-$ROOT/kiosk-update.log}"

log() {
  echo "$(date -Iseconds) $*" | tee -a "$LOG"
}

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  log "ERROR: Missing .venv — run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

UPDATE_ON_START="${BODY_UPDATE_ON_START:-0}"
if [[ "$UPDATE_ON_START" != "0" ]]; then
  {
    log "headless update start"
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
export BODY_FPS="${BODY_FPS:-24}"
export BODY_MUSIC="${BODY_MUSIC:-0}"
export BODY_HDMI_720=0
export BODY_BLE_P2_SCAN="${BODY_BLE_P2_SCAN:-0}"
export BODY_DEBUG_HUD="${BODY_DEBUG_HUD:-0}"
export SDL_VIDEO_VSYNC="${SDL_VIDEO_VSYNC:-0}"
unset DISPLAY
export SDL_AUDIODRIVER="${SDL_AUDIODRIVER:-alsa}"

# Prefer DRM; fbcon works on some Pi OS builds when kmsdrm fails.
DRIVERS="${SDL_VIDEODRIVER:-kmsdrm}"
if [[ "$DRIVERS" == "kmsdrm" ]]; then
  DRIVERS="kmsdrm fbcon"
fi

for drv in $DRIVERS; do
  export SDL_VIDEODRIVER="$drv"
  log "Starting main.py SDL_VIDEODRIVER=$drv"
  if "$ROOT/.venv/bin/python" main.py >>"$LOG" 2>&1; then
    exit 0
  fi
  log "main.py exited with error on driver $drv"
done

log "ERROR: all SDL video drivers failed — see $LOG"
exit 1
