#!/usr/bin/env bash
# Full-screen BlobJump on real BLE remotes; updates repo on every start.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
LOG="${BODY_KIOSK_LOG:-$ROOT/kiosk-update.log}"
UPDATE_ON_START="${BODY_UPDATE_ON_START:-0}"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Missing .venv — run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

update_code() {
  {
    echo "=== $(date -Iseconds) kiosk start ==="
    if [[ -d "$REPO/.git" ]]; then
      if git -C "$REPO" pull --ff-only; then
        echo "git pull: ok"
      else
        echo "git pull: failed (offline or local changes — continuing with current tree)"
      fi
    else
      echo "git pull: skipped (no .git in $REPO)"
    fi
    "$ROOT/.venv/bin/pip" install -r "$ROOT/requirements.txt"
    echo "pip install: ok"
  } >>"$LOG" 2>&1
}

if [[ "$UPDATE_ON_START" != "0" ]]; then
  update_code || echo "$(date -Iseconds) update_code failed — see $LOG" >>"$LOG"
fi

cd "$ROOT"
chmod +x "$ROOT/ensure-bluetooth.sh" "$ROOT/set-display-720p.sh" 2>/dev/null || true
"$ROOT/ensure-bluetooth.sh" >>"$LOG" 2>&1 || true

export MOCK_BLE=0
export BODY_FULLSCREEN=1
export BODY_GAME="${BODY_GAME:-blob_jump}"
# Pi Zero 2 W: 720p + 30 FPS + no procedural music
export BODY_HDMI_720="${BODY_HDMI_720:-1}"
export BODY_FPS="${BODY_FPS:-24}"
export BODY_MUSIC="${BODY_MUSIC:-0}"
export BODY_BLE_P2_SCAN="${BODY_BLE_P2_SCAN:-0}"
export BODY_DEBUG_HUD="${BODY_DEBUG_HUD:-0}"

export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
"$ROOT/set-display-720p.sh" >>"$LOG" 2>&1 || true

# Uncomment if pygame fails to open display on your Pi OS image:
# export SDL_VIDEODRIVER=wayland
exec "$ROOT/.venv/bin/python" main.py
