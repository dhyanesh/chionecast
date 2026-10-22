"""
chione_device.py - Hardware interface for GAMDIAS CHIONE P3 Cooler Display.
Communicates with USB AEOLUS BOX (VID: 0x1B80, PID: 0xB522) via USB HID.
"""

import sys
import time
from typing import Optional, Union
from PIL import Image

try:
    import hid
except ImportError:
    hid = None


VENDOR_ID = 0x1B80
PRODUCT_ID = 0xB522
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240
TOTAL_PIXELS = DISPLAY_WIDTH * DISPLAY_HEIGHT  # 57,600
FRAME_BYTES = TOTAL_PIXELS * 2                 # 115,200 bytes (RGB565)
CHUNK_SIZE = 1024                              # 1024 bytes payload per report
PACKET_SIZE = CHUNK_SIZE + 1                   # 1025 bytes (Report ID 0x00 + 1024 bytes)
TOTAL_PACKETS = 113                            # 112 * 1024 + 512 = 115,200 bytes


def compute_checksum(packet: list[int]) -> int:
    """
    Computes 8-bit checksum (SCE) where sum(packet[1:8]) + checksum == 0xFF.
    """
    return (0xFF - sum(packet[1:8])) & 0xFF


def pil_to_rgb565_bytes(image: Image.Image) -> bytes:
    """
    Converts a PIL Image (resized to 240x240) into 115,200 RGB565 little-endian bytes.
    Byte order per pixel: [Low Byte, High Byte].
    """
    if image.size != (DISPLAY_WIDTH, DISPLAY_HEIGHT):
        image = image.resize((DISPLAY_WIDTH, DISPLAY_HEIGHT), Image.Resampling.LANCZOS)
    
    img = image.convert("RGB")
    rgb_data = img.tobytes()
    
    buf = bytearray(FRAME_BYTES)
    out_idx = 0
    
    for i in range(0, len(rgb_data), 3):
        r = rgb_data[i]
        g = rgb_data[i + 1]
        b = rgb_data[i + 2]
        
        # High byte: R[7:3] | G[7:5]
        high_byte = (r & 0xF8) | ((g >> 5) & 0x07)
        # Low byte: G[4:2] << 5 | B[7:3] >> 3
        low_byte = ((g << 3) & 0xE0) | ((b >> 3) & 0x1F)
        
        # In CHIONE P3 protocol, low byte is stored first, then high byte
        buf[out_idx] = low_byte
        buf[out_idx + 1] = high_byte
        out_idx += 2
        
    return bytes(buf)


class ChioneDevice:
    def __init__(self, vendor_id: int = VENDOR_ID, product_id: int = PRODUCT_ID):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.device: Optional[hid.device] = None
        self._raw_fd: Optional[int] = None

    def open(self) -> bool:
        """
        Attempts to open the device via hidapi or raw /dev/hidraw node.
        """
        if hid is not None:
            try:
                self.device = hid.device()
                self.device.open(self.vendor_id, self.product_id)
                self.device.set_nonblocking(False)
                return True
            except Exception as e:
                self.device = None
                # Continue to check raw hidraw if permission or hidapi issue
                err_msg = str(e)
        else:
            err_msg = "hidapi not installed"

        # Fallback to direct /dev/hidraw node
        import glob
        for uevent_path in glob.glob("/sys/class/hidraw/hidraw*/device/uevent"):
            try:
                with open(uevent_path, "r") as f:
                    content = f.read()
                if f"{self.vendor_id:04X}:{self.product_id:04X}".lower() in content.lower():
                    hidraw_name = uevent_path.split("/")[4]
                    dev_path = f"/dev/{hidraw_name}"
                    import os
                    self._raw_fd = os.open(dev_path, os.O_RDWR)
                    return True
            except Exception:
                continue

        raise PermissionError(
            f"Could not open GAMDIAS CHIONE P3 (VID 0x{self.vendor_id:04X}, PID 0x{self.product_id:04X}): {err_msg}.\n"
            f"Please check that the USB cable is connected and permissions are set:\n"
            f"Run: sudo cp 99-gamdias-chione.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger"
        )

    def close(self):
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None
        if self._raw_fd is not None:
            import os
            try:
                os.close(self._raw_fd)
            except Exception:
                pass
            self._raw_fd = None

    def send_feature_report(self, data: list[int]) -> int:
        """
        Sends a 9-byte HID feature report to the cooler.
        """
        if len(data) != 9:
            raise ValueError(f"Feature report must be exactly 9 bytes (got {len(data)})")
        
        if self.device:
            return self.device.send_feature_report(data)
        elif self._raw_fd is not None:
            import os
            return os.write(self._raw_fd, bytes(data))
        else:
            raise RuntimeError("Device is not open")

    def get_feature_report(self, report_id: int, length: int = 9) -> list[int]:
        """
        Reads a feature report from the cooler.
        """
        if self.device:
            return self.device.get_feature_report(report_id, length)
        elif self._raw_fd is not None:
            import os
            return list(os.read(self._raw_fd, length))
        else:
            raise RuntimeError("Device is not open")

    def write_output_report(self, data: Union[bytes, bytearray, list[int]]) -> int:
        """
        Writes an output report (Report ID 0x00 + 1024 bytes) to the cooler.
        """
        if self.device:
            return self.device.write(data)
        elif self._raw_fd is not None:
            import os
            return os.write(self._raw_fd, bytes(data))
        else:
            raise RuntimeError("Device is not open")

    def init_stream(self) -> bool:
        """
        Puts the LCD into stream reception mode (USB_81H_I01 / USB_LCDrgb565_init).
        Packet: [0x00, 0x81, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7D]
        """
        packet = [0x00, 0x81, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        packet[8] = compute_checksum(packet)
        res = self.send_feature_report(packet)
        time.sleep(0.05)
        return res >= 0

    def set_config(self, rotation_deg: int = 0, brightness: int = 8) -> bool:
        """
        Sets screen orientation (0, 90, 180, 270 degrees) and brightness (1..8).
        Sends wake command first, pauses, then applies rotation and brightness.
        """
        rot_map = {0: 0, 90: 1, 180: 2, 270: 3}
        rot_val = rot_map.get(rotation_deg, 0)
        bri_val = max(1, min(8, brightness))

        # 1. Wake packet (zeros)
        wake = [0x00, 0x81, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        wake[8] = compute_checksum(wake)
        self.send_feature_report(wake)
        time.sleep(0.1)

        # 2. Config packet
        packet = [0x00, 0x81, 0x04, rot_val, bri_val, 0x00, 0x00, 0x00, 0x00]
        packet[8] = compute_checksum(packet)
        res = self.send_feature_report(packet)
        time.sleep(0.05)
        return res >= 0

    def send_frame(self, rgb565_data: bytes):
        """
        Streams a complete 240x240 frame (115,200 bytes) in 113 packets.
        """
        if len(rgb565_data) < FRAME_BYTES:
            rgb565_data = rgb565_data.ljust(FRAME_BYTES, b"\x00")

        offset = 0
        total_len = FRAME_BYTES

        for i in range(TOTAL_PACKETS):
            chunk = rgb565_data[offset : offset + CHUNK_SIZE]
            offset += CHUNK_SIZE

            # Pad last chunk if shorter than 1024 bytes
            if len(chunk) < CHUNK_SIZE:
                chunk = chunk.ljust(CHUNK_SIZE, b"\x00")

            # Prepend Report ID 0x00 (total 1025 bytes)
            packet = b"\x00" + chunk
            self.write_output_report(packet)

    def display_image(self, image: Image.Image):
        """
        Convenience function: converts PIL Image and streams to the display.
        """
        raw_data = pil_to_rgb565_bytes(image)
        self.send_frame(raw_data)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
