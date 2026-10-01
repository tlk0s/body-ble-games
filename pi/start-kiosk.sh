#!/usr/bin/env bash
# Full-screen BlobJump on real BLE remotes; updates repo on every start.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
LOG="${BODY_KIOSK_LOG:-$ROOT/kiosk-update.log}"
UPDATE_ON_START="${BODY_UPDATE_ON_START:-1}"

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
export MOCK_BLE=0
export BODY_FULLSCREEN=1
export BODY_GAME="${BODY_GAME:-blob_jump}"
# Uncomment if pygame fails to open display on your Pi OS image:
# export SDL_VIDEODRIVER=wayland
exec "$ROOT/.venv/bin/python" main.py
