# GAMDIAS CHIONE P3 Cooler Display for Linux (Ubuntu)

Native Linux driver, telemetry monitor, and customization tool for the **GAMDIAS CHIONE P3** AIO Liquid CPU Cooler (`CHIONE P3-240U` & `CHIONE P3-360U`).

---

## Features
- **Real-Time Telemetry:** Displays CPU usage & temperature (Intel/AMD) and GPU usage, temperature & VRAM (NVIDIA RTX 4090 / GeForce / etc.).
- **Multiple Visual Themes:**
  - `dual`: Dual arc gauges with real-time temperature, load, clock, and RAM info (large % readout).
  - `cyberpunk`: Concentric neon rings for CPU and GPU with high-contrast readouts.
  - `bignum`: Dominant large single-number readout (CPU or GPU %) with a 270° tachometer arc gauge.
  - `simple`: Minimalist clean card dashboard.
- **Official Assets & Animations:** Shipped with all vendor animations (`official_anim_1.gif`, `official_anim_2.gif`, `cgif.gif`) and backgrounds.
- **Custom Images & Animations:** Stream static images (`.png`, `.jpg`) or animated GIFs directly to the 240×240 IPS LCD screen.
- **Orientation & Brightness Control:** Configure rotation (`0°`, `90°`, `180°`, `270°`) and brightness (`1` to `8`).
- **Ubuntu/Debian Packaging:** Built-in `.deb` package generation and `Makefile` for one-command distribution.
- **No Root Required:** Simple udev rule enables regular users in the `plugdev` group to control the display.
- **Systemd Background Service:** Can run seamlessly on boot in the background.

---

## Installation & Distribution for Ubuntu / Debian

### Option A: Install via Debian Package (.deb)
```bash
# Build the .deb package
make deb

# Install the package (automatically installs udev rules and systemd service)
sudo apt install ./chionecast_1.0.0_all.deb
```

Once installed, `chionecast` is available system-wide:
```bash
chionecast --rotate 180 --theme dual
```

### Option B: Quick Setup from Source
```bash
# 1. Install Udev Rules
./setup.sh

# 2. Run with default Dual Gauge theme (rotated 180°)
./venv/bin/python chione_cli.py --rotate 180 --theme dual

# Run with Big Number theme
./venv/bin/python chione_cli.py --rotate 180 --theme bignum

# Stream official vendor animation
./venv/bin/python chione_cli.py --rotate 180 --gif assets/official/animations/official_anim_1.gif
```

---

## Command Reference

### Set Screen Rotation & Brightness
```bash
# Rotate display 90 degrees and set maximum brightness (8)
./venv/bin/python chione_cli.py --rotate 90 --brightness 8
```

### Display Static Image or Animated GIF
```bash
# Display a custom image (automatically resized to 240x240)
./venv/bin/python chione_cli.py --image /path/to/picture.png

# Play an animated GIF in a continuous loop
./venv/bin/python chione_cli.py --gif /path/to/animation.gif
```

### Adjust Refresh Rate
```bash
# Update every 0.5 seconds
./venv/bin/python chione_cli.py --theme dual --interval 0.5
```

---

## Enable Automatic Startup on Boot (Systemd)

To run the display dashboard automatically whenever you log into Ubuntu:
```bash
mkdir -p ~/.config/systemd/user
cp chione-display.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now chione-display.service
```

To check service status:
```bash
systemctl --user status chione-display.service
```

---

## Documentation
For complete technical details, reverse engineering notes, and protocol packet definitions, see [REVERSE_ENGINEERING_AND_PROTOCOL.md](file:///home/dhyanesh/dev/chionecast/REVERSE_ENGINEERING_AND_PROTOCOL.md).
