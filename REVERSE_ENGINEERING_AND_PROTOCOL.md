# GAMDIAS CHIONE P3 Cooler Display: Reverse Engineering & Protocol Specification

## 1. Executive Summary

This document describes the reverse engineering process, hardware identification, and USB communication protocol for the LCD screen on the **GAMDIAS CHIONE P3 Series** CPU AIO liquid cooler (models **CHIONE P3-240U** and **CHIONE P3-360U**). 

The cooler features a circular 2.1" IPS LCD display on the water block pump head, controlled via an external USB AEOLUS Box. Officially, GAMDIAS only provides the Windows application **CHIONE CAST** (`CHIONE-CAST_V1.4.1.0`). This document outlines how the protocol was discovered from the Linux system and official binaries, and defines the complete specification for the native Linux driver.

---

## 2. Hardware Identification & Investigation Steps

### Step 2.1: System & USB Inspection
On Ubuntu Linux, hardware was inspected using `lsusb` and `sysfs`:
```bash
$ lsusb
...
Bus 001 Device 008: ID 1b80:b522 Afatech USB AEOLUS BOX
```

Checking USB descriptors (`lsusb -v -d 1b80:b522`):
* **Vendor ID (VID):** `0x1B80` (Afatech Technologies / GAMDIAS)
* **Product ID (PID):** `0xB522` (USB AEOLUS BOX)
* **Manufacturer:** `GAMDIAS`
* **Product:** `USB AEOLUS BOX`
* **Device Class:** Human Interface Device (HID)
* **Endpoints:**
  * Endpoint `0x81` (EP 1 IN): Interrupt, max packet size `8 bytes`
  * Endpoint `0x01` (EP 1 OUT): Interrupt, max packet size `1024 bytes` (`0x0400`)

Checking HID report descriptor via `/sys/class/hidraw/hidraw11/device/report_descriptor`:
* Usage Page: Vendor Defined `0xFF02`
* Usage: `0x0001`

### Step 2.2: Locating Official Vendor Software
GAMDIAS downloads page (`gamdias.com/en/downloads`) was inspected:
* Discovered internal Laravel API endpoints used by the selector:
  * `https://www.gamdias.com/findProductName?model_id=4` (Category 4: COOLERS)
  * Listed models included `CHIONE P3-240U` (ID 120026), `CHIONE P3-360U` (ID 120025), and `CHIONE M4-240/360`.
* Querying `https://www.gamdias.com/finddownload?showdata_id=4&parent_id=120025`:
  * Software URL: `https://www.gamdias.com/ftp/software/CHIONE_P3-240U/CHIONE-CAST_V1.4.1.0.zip`

### Step 2.3: Unpacking the Binaries
* The zip archive contained `CHIONE-CAST_V1.4.1.0.exe`, created with **Inno Setup 6.1.0 (Unicode)**.
* Extracted using `innoextract`:
  * Main application: `CHIONE-CAST.exe` (.NET WPF executable).
  * Supporting libraries: `cpuidsdk.dll`, MaterialDesign libraries, Newtonsoft.Json.

### Step 2.4: Decompiling and Reverse-Engineering the .NET Assembly
Using Python's `dnfile` and custom CIL (Common Intermediate Language) disassemblers:
1. **Model & PID Match:**
   * Found string literal `Text_FindPID = "B522"`.
   * Found `ClassPROSupport`: Maps PID `0xB522` to `USB-LCD` Box with `0xFF02:0x0001`, OutReport `1025` bytes, InReport `9` bytes.
   * Internal project code was `M3-240U` (commercialized as `CHIONE P3-240U` / `CHIONE P3-360U`).
2. **Display Resolution:**
   * Found `width = 240`, `height = 240` in `LCDImgtoLCD` (`0x8504`) and `USB_LCDrgb565_Width` (`0x7c88`).
   * Color depth: 16-bit **RGB565** (`240 * 240 = 57,600 pixels = 115,200 bytes`).
3. **HID Communication:**
   * `USB_81H_F04` / `USB_81H_F05`: Controls LCD orientation and brightness level using 9-byte HID feature reports.
   * `USB_LCDrgb565_PrintData`: Writes 113 packets of 1025 bytes (Report ID `0x00` + 1024 bytes payload) directly to the output stream.

---

## 3. Protocol Specification

### 3.1 USB Parameters
* **VID:** `0x1B80`
* **PID:** `0xB522`
* **HID Usage Page:** `0xFF02`
* **HID Usage:** `0x0001`
* **Feature / Command Report Size:** 9 bytes (1 byte Report ID `0x00` + 8 bytes payload)
* **Display Stream Packet Size:** 1025 bytes (1 byte Report ID `0x00` + 1024 bytes payload)

### 3.2 Checksum Algorithm (`SCE`)
Every 9-byte control packet uses an 8-bit checksum stored in **byte 8**:
$$\text{Checksum} = \left( 0\text{xFF} - \sum_{i=1}^{7} \text{packet}[i] \right) \&\ 0\text{xFF}$$

In Python:
```python
def compute_checksum(packet_bytes: list[int]) -> int:
    return (0xFF - sum(packet_bytes[1:8])) & 0xFF
```

### 3.3 Control Packets (9 Bytes)

#### A. Set Screen Orientation and Brightness (`USB_81H_F04`)
Sent as a HID Feature Report (or HID output report):
```
[0x00, 0x81, 0x04, <DIR>, <BRI>, 0x00, 0x00, 0x00, <CHECKSUM>]
```
* **Byte 0:** `0x00` (Report ID)
* **Byte 1:** `0x81`
* **Byte 2:** `0x04`
* **Byte 3:** `<DIR>` Screen Rotation:
  * `0x00`: 0° (Normal)
  * `0x01`: 90°
  * `0x02`: 180°
  * `0x03`: 270°
* **Byte 4:** `<BRI>` Brightness: `0x01` (minimum) to `0x08` (maximum)
* **Bytes 5–7:** `0x00`
* **Byte 8:** Checksum

#### B. Query Screen Status (`USB_81H_F05`)
Sent to the device:
```
[0x00, 0x81, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79]
```
Device response (9 bytes):
* **Byte 3:** Current `<DIR>`
* **Byte 4:** Current `<BRI>`

#### C. Other Control Packets
* `USB_30H`: `[0x00, 0x30, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xCF]` (Fan/RGB controller init)
* `USB_90H`: `[0x00, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x6F]` (Fan/RGB handshake)

---

### 3.4 LCD Image Streaming Protocol

#### A. Image Format
* **Resolution:** 240 × 240 pixels (Total: 57,600 pixels)
* **Color Space:** 16-bit RGB565 Little-Endian
* **Conversion from 24/32-bit RGB (R, G, B in 0..255):**
  $$\text{High Byte} = (R \ \&\ 0\text{xF8}) \mid ((G \gg 5) \ \&\ 0\text{x07})$$
  $$\text{Low Byte} = ((G \ll 3) \ \&\ 0\text{xE0}) \mid ((B \gg 3) \ \&\ 0\text{x1F})$$
  In memory, pixels are ordered row-by-row (top to bottom, left to right):
  `[Low Byte, High Byte, Low Byte, High Byte, ...]`

#### B. Total Frame Byte Length
$$57,600 \text{ pixels} \times 2 \text{ bytes/pixel} = 115,200 \text{ bytes}$$

#### C. Packetization
Data is sent over the HID interrupt/output stream in **113 packets**:
* **Packet size:** 1025 bytes (`1 byte Report ID (0x00) + 1024 bytes data`)
* **Packets 1 through 112:**
  $$112 \times 1024 = 114,688 \text{ bytes}$$
* **Packet 113:**
  Remaining $115,200 - 114,688 = 512 \text{ bytes}$, zero-padded to 1024 bytes.
  Total payload sent in packet 113 is 1024 bytes (1025 with Report ID).

---

## 4. Linux Permissions (`udev`)

By default, Linux marks raw HID nodes as `root:root` with `0600` permissions. To allow regular users in the `plugdev` group to control the display without `sudo`, install a udev rule:

`/etc/udev/rules.d/99-gamdias-chione.rules`:
```udev
# GAMDIAS CHIONE P3 Cooler LCD & AEOLUS Box
SUBSYSTEM=="hidraw", ATTRS{idVendor}=="1b80", ATTRS{idProduct}=="b522", MODE="0660", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="1b80", ATTR{idProduct}=="b522", MODE="0660", GROUP="plugdev"
```
Then reload udev rules:
```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

---

## 5. Checksum Algorithm Specification

Disassembled from method `SCE` in `CHIONE-CAST.exe`:
All 9-byte command packets to the AEOLUS box follow this exact checksum algorithm:

```python
def calculate_checksum(packet: bytes) -> int:
    """
    Vendor checksum for GAMDIAS AEOLUS Box command packets.
    Iteratively subtracts bytes 1..7 from 0xFF.
    """
    chk = 0xFF
    for b in packet[1:8]:
        chk = (chk - b) & 0xFF
    return chk
```

### Verification:
* Wake / Rotate packet: `[0x00, 0x81, 0x04, 0x00, 0x02, 0x08, 0x00, 0x00]`
  $0\text{xFF} - 0\text{x81} - 0\text{x04} - 0\text{x02} - 0\text{x08} = 0\text{x70}$ (Matches `0x70` in packet!)
* Stream Init packet: `[0x00, 0x81, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]`
  $0\text{xFF} - 0\text{x81} - 0\text{x01} = 0\text{x7D}$ (Matches `0x7D` in packet!)

---

## 6. AEOLUS Box Lighting Control Protocol

Disassembled from `USBPort40H_Light` (`0x119E4`) and `Lighting_ID2Mode`:

### Command Packet Format (9 bytes)
| Byte Index | Field | Values | Description |
|---|---|---|---|
| 0 | Report ID | `0x00` | Standard HID Report ID |
| 1 | Command | `0x40` | Lighting Control Subsystem |
| 2 | Target | `0x01` | Fan / LED strip bank |
| 3 | `Light_EF` | `0x00`..`0x1D` | Lighting Mode Effect ID (1..30) |
| 4 | `Light_BR` | `0x01`..`0x08` | Brightness Level |
| 5 | `Light_SP` | `0x01`..`0x05` | Animation Speed |
| 6 | `Light_DI` | `0x00` or `0x01` | Direction (Clockwise / Counterclockwise) |
| 7 | Reserved | `0x00` | Unused |
| 8 | Checksum | `SCE(packet)` | 8-bit difference checksum |

### Discovered Lighting Presets (30 Modes):
1. **Static Modes (1–7):** Single color presets (Red, Orange, Yellow, Green, Cyan, Blue, Magenta).
2. **Rainbow (1):** Multi-color continuous flow.
3. **Spectrum / Color Cycle (1–2):** Synchronized color fading.
4. **Flow (1–5):** Directional RGB flow patterns.
5. **Wave (1–4):** Radial and angular RGB wave oscillations.
6. **Mixing / Sway (1–3):** Dual-color blending patterns.
7. **Neon (1–4):** High-contrast pulsating hues.
8. **Stack / Marquee (1–3):** Chasing LED patterns.
9. **Dark (Off):** Shuts off all AEOLUS Box LEDs.

---

## 7. Vendor UI Modes & Extracted Assets

The vendor application provides 4 operational modes:
1. **Hardware Library Mode**:
   - Renders animated GIF or static graphic background on LCD.
   - Overlays up to 3 telemetry text fields (`Text_CPUID1`, `Text_CPUID2`, `Text_CPUID3`) at user-defined (X, Y) coordinates.
   - Text color selectable from palette (`#FF0000`, `#00FF00`, `#007FFF`, `#FFFFFF`, etc.).
2. **Custom Media Mode**:
   - User-supplied 240x240 PNG, JPG, or animated GIF.
   - Streams at target frame rate (default ~30 FPS).
3. **Hardware Telemetry**:
   - CPU (Usage %, Temp, Clock GHz, Voltage).
   - GPU (Usage %, Temp, Clock MHz, VRAM %).
   - RAM (Usage %, Memory Used).
   - Pump / Fan (RPM).
4. **Motherboard ARGB Sync (`LED_MB`)**:
   - Hands over lighting control to the 3-pin 5V ARGB motherboard header.
