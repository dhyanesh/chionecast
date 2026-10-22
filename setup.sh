#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Installing GAMDIAS CHIONE P3 udev rules ==="
sudo cp "${SCRIPT_DIR}/99-gamdias-chione.rules" /etc/udev/rules.d/
sudo udevadm control --reload-rules

# Trigger udev specifically for the Chione device (VID 1b80, PID b522)
echo "Applying udev rules to connected device..."
sudo udevadm trigger --attr-match=idVendor=1b80 --attr-match=idProduct=b522
sudo udevadm settle

# Check if a hidraw node appeared for the device
HIDRAW=""
for uevent in /sys/class/hidraw/hidraw*/device/uevent; do
    if grep -qi "1b80.*b522\|b522.*1b80" "$uevent" 2>/dev/null; then
        HIDRAW=$(echo "$uevent" | sed 's|/sys/class/hidraw/\(hidraw[0-9]*\)/.*|\1|')
        break
    fi
done

if [ -n "$HIDRAW" ]; then
    echo "✓ Device node created: /dev/$HIDRAW"
else
    echo "⚠ No hidraw node found for Chione device."
    echo "  Try unplugging and replugging the USB cable, then run:"
    echo "  sudo udevadm trigger --attr-match=idVendor=1b80 --attr-match=idProduct=b522"
fi

echo ""
echo "Udev rules installed successfully!"
echo "You can now run the display driver without sudo."
echo ""
echo "Example commands:"
echo "  ${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/chione_cli.py --theme dual"
echo "  ${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/chione_cli.py --theme cyberpunk"
echo "  ${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/chione_cli.py --rotate 90 --brightness 8"
