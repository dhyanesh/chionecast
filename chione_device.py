"""
chione_device.py - Hardware interface for GAMDIAS CHIONE P3 Cooler Display.
Communicates with USB AEOLUS BOX (VID: 0x1B80, PID: 0xB522) via USB HID.
"""

import os
import sys
import time
import fcntl
import signal
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
DEFAULT_LOCK_PATH = "/tmp/chionecast.lock"


def find_existing_instances() -> list[int]:
    """
    Finds PIDs of any other running chionecast or chione_cli processes.
    Ignores current process, parent wrappers (like timeout or bash), and build scripts.
    """
    pids = []
    current_pid = os.getpid()
    parent_pid = os.getppid()
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "cmdline"]):
            if proc.pid in (current_pid, parent_pid):
                continue
            try:
                cmdline = proc.info.get("cmdline")
                if not cmdline:
                    continue
                exe = os.path.basename(cmdline[0]).lower()
                if "python" in exe:
                    if any("chione_cli" in arg for arg in cmdline[1:]) and not any("package_deb" in arg for arg in cmdline):
                        pids.append(proc.pid)
                elif exe == "chionecast":
                    pids.append(proc.pid)
            except Exception:
                continue
    except Exception:
        pass
    return pids


class DeviceLock:
    """
    Inter-process locking mechanism using fcntl.flock and process inspection
    to guarantee that only one process communicates with the cooler LCD at any given time.
    """

    def __init__(self, lock_path: str = DEFAULT_LOCK_PATH):
        self.lock_path = lock_path
        self._lock_fd: Optional[int] = None

    def acquire(self, replace: bool = False, timeout: float = 2.0) -> bool:
        # Check for any other running instances via process table first
        existing_pids = find_existing_instances()

        # Also read existing PID from lock file if present and verify if it is alive
        if os.path.exists(self.lock_path):
            try:
                with open(self.lock_path, "r") as f:
                    content = f.read().strip()
                    if content.isdigit():
                        file_pid = int(content)
                        if file_pid != os.getpid() and file_pid not in existing_pids:
                            import psutil
                            if psutil.pid_exists(file_pid):
                                existing_pids.append(file_pid)
            except Exception:
                pass

        if existing_pids:
            if replace:
                for pid in existing_pids:
                    print(f"Terminating existing chionecast instance (PID {pid})...")
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except OSError:
                        pass
                
                # Wait up to timeout seconds for processes to terminate
                start_time = time.time()
                while time.time() - start_time < timeout:
                    time.sleep(0.05)
                    remaining = []
                    for pid in existing_pids:
                        try:
                            os.kill(pid, 0)
                            remaining.append(pid)
                        except OSError:
                            pass
                    if not remaining:
                        break
                else:
                    for pid in remaining:
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except OSError:
                            pass
                time.sleep(0.1)
            else:
                pid_list_str = ", ".join(str(p) for p in existing_pids)
                raise RuntimeError(
                    f"Another chionecast instance (PID {pid_list_str}) is currently running and controlling the cooler display.\n"
                    f"Multiple simultaneous processes cause corrupted, interleaved, and flickering frames.\n"
                    f"Run with '--replace' to terminate the existing instance, or stop PID {pid_list_str}."
                )

        flags = os.O_RDWR | os.O_CREAT
        fd = os.open(self.lock_path, flags, 0o666)

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, IOError):
            os.close(fd)
            raise RuntimeError(
                f"Device lock at {self.lock_path} is currently locked by another process.\n"
                f"Run with '--replace' to force takeover."
            )

        # Record our PID
        try:
            os.ftruncate(fd, 0)
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, f"{os.getpid()}\n".encode("ascii"))
        except Exception:
            pass

        self._lock_fd = fd
        return True

    def release(self):
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
            except Exception:
                pass
            self._lock_fd = None


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
        self.lock = DeviceLock()

    def open(self, replace: bool = False, acquire_lock: bool = True) -> bool:
        """
        Attempts to open the device via hidapi or raw /dev/hidraw node.
        Guarantees single-process access by acquiring an exclusive lock.
        If replace=True, terminates any existing process holding the lock.
        """
        if acquire_lock:
            self.lock.acquire(replace=replace)

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

        # If opening device failed, release lock before raising error
        if acquire_lock:
            self.lock.release()

        raise PermissionError(
            f"Could not open GAMDIAS CHIONE P3 (VID 0x{self.vendor_id:04X}, PID 0x{self.product_id:04X}): {err_msg}.\n"
            f"Please check that the USB cable is connected and permissions are set:\n"
            f"Run: sudo cp 99-gamdias-chione.rules /etc/udev/rules.d/ && sudo udevadm control --reload-rules && sudo udevadm trigger"
        )

    def close(self):
        try:
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
        finally:
            self.lock.release()

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

    def clear_display(self, color: tuple[int, int, int] = (0, 0, 0)):
        """
        Clears the display by sending a full 240x240 solid color frame.
        Flushes any pending packets and ensures the screen starts completely clean.
        """
        if color == (0, 0, 0):
            raw = b"\x00" * FRAME_BYTES
        else:
            r, g, b = color
            high_byte = (r & 0xF8) | ((g >> 5) & 0x07)
            low_byte = ((g << 3) & 0xE0) | ((b >> 3) & 0x1F)
            pixel = bytes([low_byte, high_byte])
            raw = pixel * TOTAL_PIXELS
        self.send_frame(raw)

    def init_stream(self, clear: bool = True) -> bool:
        """
        Puts the LCD into stream reception mode (USB_81H_I01 / USB_LCDrgb565_init).
        Packet: [0x00, 0x81, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7D]
        Optionally clears the screen buffer to black immediately after init.
        """
        packet = [0x00, 0x81, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        packet[8] = compute_checksum(packet)
        res = self.send_feature_report(packet)
        time.sleep(0.05)
        if clear:
            self.clear_display()
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
