#!/usr/bin/env bash
# usb_power.sh — Toggle USB VBUS power on RPi 3B+ via uhubctl
# Usage: ./scripts/usb_power.sh on|off
#
# Requires: uhubctl installed, passwordless sudo for uhubctl
# RPi 3B+ USB hub is at location 1-1

set -euo pipefail

HUB_LOCATION="1-1"

usage() {
    echo "Usage: $0 on|off"
    exit 1
}

[ $# -eq 1 ] || usage

ACTION="$1"

case "$ACTION" in
    on)
        echo "[USB] Powering ON USB port (hub $HUB_LOCATION)..."
        sudo uhubctl -a on -l "$HUB_LOCATION"
        ;;
    off)
        echo "[USB] Powering OFF USB port (hub $HUB_LOCATION)..."
        sudo uhubctl -a off -l "$HUB_LOCATION"
        ;;
    *)
        usage
        ;;
esac

# Verify the state change
sleep 0.5
STATUS=$(sudo uhubctl -l "$HUB_LOCATION" 2>&1)

if [ "$ACTION" = "off" ] && echo "$STATUS" | grep -q "off"; then
    echo "[USB] Verified: USB power is OFF"
elif [ "$ACTION" = "on" ] && echo "$STATUS" | grep -q "power"; then
    echo "[USB] Verified: USB power is ON"
else
    echo "[USB] WARNING: Could not verify USB power state"
    echo "$STATUS"
    exit 1
fi
