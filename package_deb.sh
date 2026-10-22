#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="1.0.0"
PKG_NAME="chionecast"
ARCH="all"
BUILD_DIR="${SCRIPT_DIR}/build/deb/${PKG_NAME}_${VERSION}_${ARCH}"

echo "=== Building Debian Package: ${PKG_NAME}_${VERSION}_${ARCH}.deb ==="

# Clean build directory
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/lib/chionecast"
mkdir -p "${BUILD_DIR}/lib/udev/rules.d"
mkdir -p "${BUILD_DIR}/usr/lib/systemd/user"
mkdir -p "${BUILD_DIR}/usr/share/doc/chionecast"

# 1. Copy source code
cp "${SCRIPT_DIR}/chione_cli.py" "${BUILD_DIR}/usr/lib/chionecast/"
cp "${SCRIPT_DIR}/chione_device.py" "${BUILD_DIR}/usr/lib/chionecast/"
cp "${SCRIPT_DIR}/display_renderer.py" "${BUILD_DIR}/usr/lib/chionecast/"
cp "${SCRIPT_DIR}/system_stats.py" "${BUILD_DIR}/usr/lib/chionecast/"
chmod 644 "${BUILD_DIR}/usr/lib/chionecast/"*.py
chmod 755 "${BUILD_DIR}/usr/lib/chionecast/chione_cli.py"

# 1b. Copy assets
if [ -d "${SCRIPT_DIR}/assets" ]; then
    mkdir -p "${BUILD_DIR}/usr/share/chionecast"
    cp -r "${SCRIPT_DIR}/assets" "${BUILD_DIR}/usr/share/chionecast/"
fi

# 2. Launcher script in /usr/bin/chionecast
cat << 'EOF' > "${BUILD_DIR}/usr/bin/chionecast"
#!/bin/sh
exec /usr/bin/python3 /usr/lib/chionecast/chione_cli.py "$@"
EOF
chmod 755 "${BUILD_DIR}/usr/bin/chionecast"

# 3. Udev rule
cp "${SCRIPT_DIR}/99-gamdias-chione.rules" "${BUILD_DIR}/lib/udev/rules.d/"
chmod 644 "${BUILD_DIR}/lib/udev/rules.d/99-gamdias-chione.rules"

# 4. Systemd user service
cp "${SCRIPT_DIR}/chionecast.service" "${BUILD_DIR}/usr/lib/systemd/user/"
chmod 644 "${BUILD_DIR}/usr/lib/systemd/user/chionecast.service"

# 5. Documentation
cp "${SCRIPT_DIR}/README.md" "${BUILD_DIR}/usr/share/doc/chionecast/"
cp "${SCRIPT_DIR}/REVERSE_ENGINEERING_AND_PROTOCOL.md" "${BUILD_DIR}/usr/share/doc/chionecast/"
if [ -d "${SCRIPT_DIR}/docs" ]; then
    cp -r "${SCRIPT_DIR}/docs" "${BUILD_DIR}/usr/share/doc/chionecast/"
fi

# 6. Debian control file
cat << EOF > "${BUILD_DIR}/DEBIAN/control"
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: Dhyanesh Damania <https://github.com/dhyanesh/chionecast>
Depends: python3 (>= 3.8), python3-pil, python3-psutil, python3-hid | python3-hidapi
Recommends: python3-pip
Description: Native Linux driver and telemetry monitor for GAMDIAS CHIONE P3 AIO cooler
 CHIONECAST is a native Linux driver, system telemetry display, and
 customization tool for the GAMDIAS CHIONE P3 AIO liquid CPU cooler series
 (CHIONE P3-240U and P3-360U).
 .
 Features real-time CPU & GPU load and temperature monitoring, multiple visual
 dashboard themes (dual gauge, cyberpunk, simple, bignum), GIF & image streaming,
 rotation control, and seamless background execution via systemd.
EOF

# 7. Post-install script
cat << 'EOF' > "${BUILD_DIR}/DEBIAN/postinst"
#!/bin/sh
set -e

if [ "$1" = "configure" ]; then
    # Reload udev rules so device node permissions take effect immediately
    if command -v udevadm >/dev/null 2>&1; then
        udevadm control --reload-rules || true
        udevadm trigger --attr-match=idVendor=1b80 --attr-match=idProduct=b522 || true
    fi

    echo "=========================================================="
    echo " chionecast ${VERSION} installed successfully!"
    echo ""
    echo " To test the cooler display:"
    echo "   chionecast --rotate 180 --theme dual"
    echo "   chionecast --rotate 180 --theme bignum"
    echo ""
    echo " To start automatically on login (systemd user service):"
    echo "   systemctl --user daemon-reload"
    echo "   systemctl --user enable --now chionecast"
    echo "=========================================================="
fi

exit 0
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"

# 8. Pre-remove script
cat << 'EOF' > "${BUILD_DIR}/DEBIAN/prerm"
#!/bin/sh
set -e

if [ "$1" = "remove" ]; then
    # Stop running instances
    pkill -f "/usr/lib/chionecast/chione_cli.py" 2>/dev/null || true
fi

exit 0
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/prerm"

# 9. Build .deb package
OUTPUT_DEB="${SCRIPT_DIR}/${PKG_NAME}_${VERSION}_${ARCH}.deb"
dpkg-deb --build --root-owner-group "${BUILD_DIR}" "${OUTPUT_DEB}"

echo ""
echo "✓ Package built successfully: ${OUTPUT_DEB}"
ls -lh "${OUTPUT_DEB}"
echo ""
echo "To install on any Ubuntu/Debian system:"
echo "  sudo apt install ./${PKG_NAME}_${VERSION}_${ARCH}.deb"
