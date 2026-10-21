"""
display_renderer.py - Renders customized 240x240 dashboard layouts for the CHIONE P3 cooler.
"""

import math
import datetime
from PIL import Image, ImageDraw, ImageFont
from system_stats import SystemMetrics

WIDTH = 240
HEIGHT = 240


def _get_font(size: int):
    """
    Attempts to load a standard TrueType font (DejaVuSans, Ubuntu, Liberation),
    falling back to PIL default font.
    """
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in font_paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _get_regular_font(size: int):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in font_paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


class DisplayRenderer:
    def __init__(self):
        self.font_large = _get_font(34)
        self.font_medium = _get_font(20)
        self.font_small = _get_font(13)
        self.font_tiny = _get_regular_font(11)

    def render_dual_gauge(self, metrics: SystemMetrics) -> Image.Image:
        """
        Renders a dual gauge dashboard (CPU on left, GPU on right).
        """
        img = Image.new("RGB", (WIDTH, HEIGHT), color=(12, 14, 20))
        draw = ImageDraw.Draw(img)

        cx, cy = WIDTH // 2, HEIGHT // 2

        # Draw outer circle subtle border
        draw.ellipse([8, 8, WIDTH - 8, HEIGHT - 8], outline=(35, 40, 55), width=2)

        # CPU Left Arc (from 135 deg to 225 deg)
        # Background arc
        bbox_cpu = [18, 18, WIDTH - 18, HEIGHT - 18]
        draw.arc(bbox_cpu, start=130, end=230, fill=(35, 45, 65), width=8)
        # Active arc based on cpu_percent
        cpu_span = 100 * (metrics.cpu_percent / 100.0)
        draw.arc(bbox_cpu, start=230 - cpu_span, end=230, fill=(0, 180, 255), width=8)

        # GPU Right Arc (from -50 deg to 50 deg)
        bbox_gpu = [18, 18, WIDTH - 18, HEIGHT - 18]
        draw.arc(bbox_gpu, start=-50, end=50, fill=(35, 55, 45), width=8)
        # Active arc based on gpu_percent
        gpu_span = 100 * (metrics.gpu_percent / 100.0)
        draw.arc(bbox_gpu, start=-50, end=-50 + gpu_span, fill=(0, 230, 120), width=8)

        # CPU Header & Info (Left Center)
        draw.text((36, 68), "CPU", fill=(0, 180, 255), font=self.font_medium)
        draw.text((36, 92), f"{metrics.cpu_temp:.0f}°C", fill=(255, 255, 255), font=self.font_large)
        draw.text((36, 134), f"{metrics.cpu_percent:.0f}%", fill=(170, 200, 220), font=self.font_small)

        # GPU Header & Info (Right Center)
        draw.text((150, 68), "GPU", fill=(0, 230, 120), font=self.font_medium)
        draw.text((130, 92), f"{metrics.gpu_temp:.0f}°C", fill=(255, 255, 255), font=self.font_large)
        draw.text((150, 134), f"{metrics.gpu_percent:.0f}%", fill=(170, 220, 190), font=self.font_small)

        # Divider line
        draw.line([cx, 75, cx, 150], fill=(45, 55, 75), width=1)

        # Center Bottom: RAM & Time
        now = datetime.datetime.now().strftime("%H:%M")
        draw.text((cx - 24, 168), now, fill=(200, 200, 210), font=self.font_medium)
        draw.text((cx - 40, 195), f"RAM: {metrics.ram_percent:.0f}%", fill=(130, 140, 160), font=self.font_tiny)

        return img

    def render_cyberpunk(self, metrics: SystemMetrics) -> Image.Image:
        """
        Futuristic neon theme with concentric progress rings.
        """
        img = Image.new("RGB", (WIDTH, HEIGHT), color=(8, 8, 12))
        draw = ImageDraw.Draw(img)

        cx, cy = WIDTH // 2, HEIGHT // 2

        # Outer ring: CPU usage
        r_outer = 100
        cpu_angle = int(360 * (metrics.cpu_percent / 100.0))
        draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], outline=(25, 30, 45), width=5)
        if cpu_angle > 0:
            draw.arc([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], start=-90, end=-90 + cpu_angle, fill=(255, 0, 128), width=5)

        # Middle ring: GPU usage
        r_mid = 88
        gpu_angle = int(360 * (metrics.gpu_percent / 100.0))
        draw.ellipse([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid], outline=(20, 40, 45), width=5)
        if gpu_angle > 0:
            draw.arc([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid], start=-90, end=-90 + gpu_angle, fill=(0, 255, 230), width=5)

        # Center Content
        draw.text((cx - 48, 52), "CPU TEMP", fill=(255, 0, 128), font=self.font_tiny)
        draw.text((cx - 40, 68), f"{metrics.cpu_temp:.0f}°C", fill=(255, 255, 255), font=self.font_large)

        draw.text((cx - 48, 118), "GPU TEMP", fill=(0, 255, 230), font=self.font_tiny)
        draw.text((cx - 40, 134), f"{metrics.gpu_temp:.0f}°C", fill=(255, 255, 255), font=self.font_large)

        draw.text((cx - 46, 184), f"RTX 4090", fill=(140, 150, 170), font=self.font_tiny)

        return img

    def render_simple(self, metrics: SystemMetrics) -> Image.Image:
        """
        Minimalist card readout.
        """
        img = Image.new("RGB", (WIDTH, HEIGHT), color=(14, 16, 22))
        draw = ImageDraw.Draw(img)

        # Accent circle
        draw.ellipse([10, 10, WIDTH - 10, HEIGHT - 10], outline=(40, 45, 60), width=2)

        # Top section: CPU
        draw.text((45, 42), "CPU", fill=(0, 170, 255), font=self.font_medium)
        draw.text((45, 66), f"{metrics.cpu_temp:.0f}°C", fill=(255, 255, 255), font=self.font_large)
        draw.text((130, 78), f"LOAD {metrics.cpu_percent:.0f}%", fill=(150, 160, 180), font=self.font_small)

        # Divider
        draw.line([40, 120, WIDTH - 40, 120], fill=(45, 50, 68), width=1)

        # Bottom section: GPU
        draw.text((45, 130), "GPU", fill=(50, 220, 120), font=self.font_medium)
        draw.text((45, 154), f"{metrics.gpu_temp:.0f}°C", fill=(255, 255, 255), font=self.font_large)
        draw.text((130, 166), f"LOAD {metrics.gpu_percent:.0f}%", fill=(150, 160, 180), font=self.font_small)

        return img
