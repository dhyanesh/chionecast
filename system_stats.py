"""
system_stats.py - Real-time CPU, GPU, and memory telemetry reader for Linux.
Supports Intel/AMD CPUs via psutil & hwmon, and NVIDIA GPUs via NVML.
"""

import os
import psutil
from dataclasses import dataclass
from typing import Optional

try:
    import pynvml
    _NVML_AVAILABLE = True
except ImportError:
    _NVML_AVAILABLE = False


@dataclass
class SystemMetrics:
    cpu_percent: float
    cpu_temp: float
    cpu_freq_ghz: float
    gpu_percent: float
    gpu_temp: float
    vram_percent: float
    vram_used_gb: float
    vram_total_gb: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    gpu_name: str

    def get_metric_data(self, key: str, temp_unit: str = "C") -> tuple[str, float, str, tuple[int, int, int]]:
        """
        Returns (label, value_percentage, subtitle_string, rgb_color_tuple)
        for any requested metric key ('cpu', 'gpu', 'ram', 'vram').
        """
        key = str(key).lower().strip() if key else "none"
        is_f = temp_unit.upper() == "F"

        if key in ("none", "", "null"):
            return ("NONE", 0.0, "", (100, 100, 100))

        if key == "gpu":
            t = (self.gpu_temp * 9.0 / 5.0 + 32.0) if is_f else self.gpu_temp
            unit = "°F" if is_f else "°C"
            return ("GPU", self.gpu_percent, f"{t:.0f}{unit}", (0, 230, 120))

        elif key == "ram":
            return ("RAM", self.ram_percent, f"{self.ram_used_gb:.1f}/{self.ram_total_gb:.0f}G", (180, 140, 255))

        elif key == "vram":
            return ("VRAM", self.vram_percent, f"{self.vram_used_gb:.1f}/{self.vram_total_gb:.0f}G", (255, 100, 200))

        else:  # default to cpu
            t = (self.cpu_temp * 9.0 / 5.0 + 32.0) if is_f else self.cpu_temp
            unit = "°F" if is_f else "°C"
            return ("CPU", self.cpu_percent, f"{t:.0f}{unit}", (0, 210, 255))


class StatsCollector:
    def __init__(self):
        self._nvml_initialized = False
        self._gpu_handle = None
        self._gpu_name = "N/A"
        self._init_nvml()

    def _init_nvml(self):
        if _NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self._gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                name = pynvml.nvmlDeviceGetName(self._gpu_handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8")
                self._gpu_name = name
                self._nvml_initialized = True
            except Exception:
                self._nvml_initialized = False

    def get_cpu_temp(self) -> float:
        """
        Reads CPU temperature from sensors_temperatures.
        """
        temps = psutil.sensors_temperatures()
        # Look for coretemp / k10temp / cpu_thermal / acpitz
        for preferred in ["coretemp", "k10temp", "cpu_thermal", "acpitz"]:
            if preferred in temps:
                entries = temps[preferred]
                # Look for Package or Tctl
                for entry in entries:
                    if "package" in entry.label.lower() or "tctl" in entry.label.lower():
                        return float(entry.current)
                if entries:
                    return float(entries[0].current)
        # Fallback to sysfs thermal_zone
        try:
            for tz in os.listdir("/sys/class/thermal"):
                if tz.startswith("thermal_zone"):
                    t_path = os.path.join("/sys/class/thermal", tz, "temp")
                    if os.path.exists(t_path):
                        with open(t_path, "r") as f:
                            val = int(f.read().strip())
                            return float(val / 1000.0)
        except Exception:
            pass
        return 0.0

    def get_metrics(self) -> SystemMetrics:
        # CPU
        cpu_pct = psutil.cpu_percent(interval=None)
        cpu_t = self.get_cpu_temp()
        cpu_freq_ghz = 0.0
        try:
            freq = psutil.cpu_freq()
            if freq and freq.current:
                cpu_freq_ghz = freq.current / 1000.0
        except Exception:
            pass

        # RAM
        vm = psutil.virtual_memory()
        ram_pct = vm.percent
        ram_used_gb = vm.used / (1024.0 ** 3)
        ram_total_gb = vm.total / (1024.0 ** 3)

        # GPU
        gpu_pct = 0.0
        gpu_t = 0.0
        vram_pct = 0.0
        vram_used_gb = 0.0
        vram_total_gb = 0.0

        if self._nvml_initialized and self._gpu_handle:
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(self._gpu_handle)
                gpu_pct = float(util.gpu)
                gpu_t = float(pynvml.nvmlDeviceGetTemperature(self._gpu_handle, pynvml.NVML_TEMPERATURE_GPU))
                mem = pynvml.nvmlDeviceGetMemoryInfo(self._gpu_handle)
                vram_used_gb = float(mem.used / (1024.0 ** 3))
                vram_total_gb = float(mem.total / (1024.0 ** 3))
                if mem.total > 0:
                    vram_pct = float(mem.used / mem.total * 100.0)
            except Exception:
                pass

        return SystemMetrics(
            cpu_percent=cpu_pct,
            cpu_temp=cpu_t,
            cpu_freq_ghz=cpu_freq_ghz,
            gpu_percent=gpu_pct,
            gpu_temp=gpu_t,
            vram_percent=vram_pct,
            vram_used_gb=vram_used_gb,
            vram_total_gb=vram_total_gb,
            ram_percent=ram_pct,
            ram_used_gb=ram_used_gb,
            ram_total_gb=ram_total_gb,
            gpu_name=self._gpu_name,
        )

    def close(self):
        if self._nvml_initialized:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
            self._nvml_initialized = False
