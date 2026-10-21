#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Installing GAMDIAS CHIONE P3 udev rules ==="
sudo cp "${SCRIPT_DIR}/99-gamdias-chione.rules" /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Udev rules installed successfully!"
echo "You can now run the display driver without sudo."
echo ""
echo "Example commands:"
echo "  ${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/chione_cli.py --theme dual"
echo "  ${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/chione_cli.py --theme cyberpunk"
echo "  ${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/chione_cli.py --rotate 90 --brightness 8"
