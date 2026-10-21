# GAMDIAS CHIONE P3 Cooler Display for Linux (Ubuntu)

Native Linux driver, telemetry monitor, and customization tool for the **GAMDIAS CHIONE P3** AIO Liquid CPU Cooler (`CHIONE P3-240U` & `CHIONE P3-360U`).

---

## Features
- **Real-Time Telemetry:** Displays CPU usage & temperature (Intel/AMD) and GPU usage, temperature & VRAM (NVIDIA RTX 4090 / GeForce / etc.).
- **Multiple Visual Themes:**
  - `dual`: Dual arc gauges with real-time temperature, load, clock, and RAM info.
  - `cyberpunk`: Concentric neon rings for CPU and GPU with high-contrast readouts.
  - `simple`: Minimalist clean card dashboard.
- **Custom Images & Animations:** Stream static images (`.png`, `.jpg`) or animated GIFs directly to the 240×240 IPS LCD screen.
- **Orientation & Brightness Control:** Configure rotation (`0°`, `90°`, `180°`, `270°`) and brightness (`1` to `8`).
- **No Root Required:** Simple udev rule enables regular users in the `plugdev` group to control the display.
- **Systemd Background Service:** Can run seamlessly on boot in the background.

---

## Quick Setup

### 1. Install Udev Rules (One-time setup)
To allow communication with the USB AEOLUS Box without root:
```bash
./setup.sh
```
*(This copies `99-gamdias-chione.rules` to `/etc/udev/rules.d/` and reloads udev).*

### 2. Run the Hardware Telemetry Monitor
Using the virtual environment:
```bash
# Run with default Dual Gauge theme
./venv/bin/python chione_cli.py --theme dual

# Run with Cyberpunk Neon theme
./venv/bin/python chione_cli.py --theme cyberpunk

# Run with Simple theme
./venv/bin/python chione_cli.py --theme simple
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
