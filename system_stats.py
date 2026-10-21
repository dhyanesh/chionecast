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
    gpu_percent: float
    gpu_temp: float
    vram_percent: float
    ram_percent: float
    gpu_name: str


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
        ram_pct = psutil.virtual_memory().percent

        # GPU
        gpu_pct = 0.0
        gpu_t = 0.0
        vram_pct = 0.0

        if self._nvml_initialized and self._gpu_handle:
            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(self._gpu_handle)
                gpu_pct = float(util.gpu)
                gpu_t = float(pynvml.nvmlDeviceGetTemperature(self._gpu_handle, pynvml.NVML_TEMPERATURE_GPU))
                mem = pynvml.nvmlDeviceGetMemoryInfo(self._gpu_handle)
                vram_pct = float(mem.used / mem.total * 100.0)
            except Exception:
                pass

        return SystemMetrics(
            cpu_percent=cpu_pct,
            cpu_temp=cpu_t,
            gpu_percent=gpu_pct,
            gpu_temp=gpu_t,
            vram_percent=vram_pct,
            ram_percent=ram_pct,
            gpu_name=self._gpu_name,
        )

    def close(self):
        if self._nvml_initialized:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
            self._nvml_initialized = False
