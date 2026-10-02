#!/usr/bin/env bash
# Prefer 1280x720 on HDMI (lighter for Pi Zero 2 W + pygame).
set -euo pipefail

if [[ "${BODY_HDMI_720:-0}" == "0" ]]; then
  exit 0
fi

MODE="1280x720"
OUT="${BODY_HDMI_OUTPUT:-}"

if command -v wlr-randr >/dev/null 2>&1; then
  if [[ -z "$OUT" ]]; then
    OUT="$(wlr-randr 2>/dev/null | awk '/^[^ ]/ {print $1; exit}')"
  fi
  if [[ -n "$OUT" ]] && wlr-randr --output "$OUT" --mode "$MODE" 2>/dev/null; then
    exit 0
  fi
fi

if [[ -n "${DISPLAY:-}" ]] && command -v xrandr >/dev/null 2>&1; then
  if [[ -z "$OUT" ]]; then
    OUT="$(xrandr 2>/dev/null | awk '/ connected/{print $1; exit}')"
  fi
  if [[ -n "$OUT" ]] && xrandr --output "$OUT" --mode "$MODE" 2>/dev/null; then
    exit 0
  fi
fi

# Persistent fallback: add to /boot/firmware/config.txt (requires reboot):
#   hdmi_group=1
#   hdmi_mode=4
exit 0
