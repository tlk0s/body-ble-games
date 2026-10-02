#!/usr/bin/env bash
# Disable Pi desktop; boot straight into Body BLE Games on tty1 (SSH to maintain).
set -euo pipefail

RESTORE=0
if [[ "${1:-}" == "--restore" ]]; then
  RESTORE=1
fi

if [[ "$RESTORE" == 1 ]]; then
  echo "Restoring desktop boot…"
  sudo systemctl disable --now body-ble-games-kiosk.service 2>/dev/null || true
  for u in lightdm rpd-wayfire wayfire labwc; do
    sudo systemctl enable "$u" 2>/dev/null || true
  done
  sudo systemctl set-default graphical.target 2>/dev/null || true
  echo "Reboot to get the desktop back: sudo reboot"
  exit 0
fi

echo "Disabling desktop session (keeps SSH)…"
for u in lightdm rpd-wayfire wayfire labwc; do
  sudo systemctl disable --now "$u" 2>/dev/null || true
done
sudo systemctl disable --now body-ble-games-kiosk.service 2>/dev/null || true
sudo systemctl enable body-ble-games-kiosk.service
sudo systemctl set-default multi-user.target
echo ""
echo "Remove ~/.config/autostart/body-ble-games.desktop if you used desktop autostart."
echo "Set 720p in /boot/firmware/config.txt (hdmi_group=1 hdmi_mode=4) before reboot."
echo "Then: sudo reboot"
echo "Game runs on HDMI tty1; SSH still works."
