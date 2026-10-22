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
        self.font_giant = _get_font(60)
        self.font_huge = _get_font(44)
        self.font_large = _get_font(34)
        self.font_medium = _get_font(20)
        self.font_small = _get_font(14)
        self.font_tiny = _get_regular_font(11)

    def render_dual_gauge(self, metrics: SystemMetrics) -> Image.Image:
        """
        Renders a dual gauge dashboard (CPU on left, GPU on right)
        with usage percentages as the primary large numbers.
        """
        img = Image.new("RGB", (WIDTH, HEIGHT), color=(12, 14, 20))
        draw = ImageDraw.Draw(img)

        cx, cy = WIDTH // 2, HEIGHT // 2

        # Draw outer circle subtle border
        draw.ellipse([8, 8, WIDTH - 8, HEIGHT - 8], outline=(35, 40, 55), width=2)

        # CPU Left Arc (from 130 deg to 230 deg)
        bbox_cpu = [18, 18, WIDTH - 18, HEIGHT - 18]
        draw.arc(bbox_cpu, start=130, end=230, fill=(35, 45, 65), width=8)
        cpu_span = 100 * (min(100.0, max(0.0, metrics.cpu_percent)) / 100.0)
        draw.arc(bbox_cpu, start=230 - cpu_span, end=230, fill=(0, 180, 255), width=8)

        # GPU Right Arc (from -50 deg to 50 deg)
        bbox_gpu = [18, 18, WIDTH - 18, HEIGHT - 18]
        draw.arc(bbox_gpu, start=-50, end=50, fill=(35, 55, 45), width=8)
        gpu_span = 100 * (min(100.0, max(0.0, metrics.gpu_percent)) / 100.0)
        draw.arc(bbox_gpu, start=-50, end=-50 + gpu_span, fill=(0, 230, 120), width=8)

        # CPU Left Content: Percentage LARGE, Temp SMALL
        draw.text((36, 62), "CPU", fill=(0, 180, 255), font=self.font_medium)
        draw.text((32, 86), f"{metrics.cpu_percent:.0f}%", fill=(255, 255, 255), font=self.font_large)
        draw.text((36, 128), f"{metrics.cpu_temp:.0f}°C", fill=(170, 200, 220), font=self.font_small)

        # GPU Right Content: Percentage LARGE, Temp SMALL
        draw.text((150, 62), "GPU", fill=(0, 230, 120), font=self.font_medium)
        draw.text((144, 86), f"{metrics.gpu_percent:.0f}%", fill=(255, 255, 255), font=self.font_large)
        draw.text((150, 128), f"{metrics.gpu_temp:.0f}°C", fill=(170, 220, 190), font=self.font_small)

        # Divider line
        draw.line([cx, 72, cx, 148], fill=(45, 55, 75), width=1)

        # Center Bottom: RAM & Time
        now = datetime.datetime.now().strftime("%H:%M")
        draw.text((cx - 24, 166), now, fill=(200, 200, 210), font=self.font_medium)
        draw.text((cx - 40, 193), f"RAM: {metrics.ram_percent:.0f}%", fill=(130, 140, 160), font=self.font_tiny)

        return img

    def render_cyberpunk(self, metrics: SystemMetrics) -> Image.Image:
        """
        Futuristic neon theme with concentric progress rings and usage as primary readouts.
        """
        img = Image.new("RGB", (WIDTH, HEIGHT), color=(8, 8, 12))
        draw = ImageDraw.Draw(img)

        cx, cy = WIDTH // 2, HEIGHT // 2

        # Outer ring: CPU usage
        r_outer = 102
        cpu_angle = int(360 * (min(100.0, max(0.0, metrics.cpu_percent)) / 100.0))
        draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], outline=(25, 30, 45), width=5)
        if cpu_angle > 0:
            draw.arc([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], start=-90, end=-90 + cpu_angle, fill=(255, 0, 128), width=5)

        # Middle ring: GPU usage
        r_mid = 90
        gpu_angle = int(360 * (min(100.0, max(0.0, metrics.gpu_percent)) / 100.0))
        draw.ellipse([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid], outline=(20, 40, 45), width=5)
        if gpu_angle > 0:
            draw.arc([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid], start=-90, end=-90 + gpu_angle, fill=(0, 255, 230), width=5)

        # Center Top: CPU Usage % (Large) + Temp (Small)
        draw.text((cx - 36, 48), "CPU LOAD", fill=(255, 0, 128), font=self.font_tiny)
        cpu_txt = f"{metrics.cpu_percent:.0f}%"
        draw.text((cx - 30, 62), cpu_txt, fill=(255, 255, 255), font=self.font_large)
        draw.text((cx - 22, 98), f"{metrics.cpu_temp:.0f}°C", fill=(180, 140, 160), font=self.font_tiny)

        # Center Bottom: GPU Usage % (Large) + Temp (Small)
        draw.text((cx - 36, 122), "GPU LOAD", fill=(0, 255, 230), font=self.font_tiny)
        gpu_txt = f"{metrics.gpu_percent:.0f}%"
        draw.text((cx - 30, 136), gpu_txt, fill=(255, 255, 255), font=self.font_large)
        draw.text((cx - 22, 172), f"{metrics.gpu_temp:.0f}°C", fill=(140, 180, 180), font=self.font_tiny)

        # RAM small at very bottom
        draw.text((cx - 32, 196), f"RAM {metrics.ram_percent:.0f}%", fill=(110, 120, 140), font=self.font_tiny)

        return img

    def render_simple(self, metrics: SystemMetrics) -> Image.Image:
        """
        Minimalist card readout with usage percentages as large numbers.
        """
        img = Image.new("RGB", (WIDTH, HEIGHT), color=(14, 16, 22))
        draw = ImageDraw.Draw(img)

        # Accent circle
        draw.ellipse([10, 10, WIDTH - 10, HEIGHT - 10], outline=(40, 45, 60), width=2)

        # Top section: CPU (Usage Large, Temp Small)
        draw.text((42, 38), "CPU LOAD", fill=(0, 170, 255), font=self.font_small)
        draw.text((42, 58), f"{metrics.cpu_percent:.0f}%", fill=(255, 255, 255), font=self.font_large)
        draw.text((140, 70), f"{metrics.cpu_temp:.0f}°C", fill=(150, 160, 180), font=self.font_small)

        # Divider
        draw.line([40, 118, WIDTH - 40, 118], fill=(45, 50, 68), width=1)

        # Bottom section: GPU (Usage Large, Temp Small)
        draw.text((42, 128), "GPU LOAD", fill=(50, 220, 120), font=self.font_small)
        draw.text((42, 148), f"{metrics.gpu_percent:.0f}%", fill=(255, 255, 255), font=self.font_large)
        draw.text((140, 160), f"{metrics.gpu_temp:.0f}°C", fill=(150, 160, 180), font=self.font_small)

        # Center Bottom: RAM
        draw.text((WIDTH // 2 - 32, 198), f"RAM: {metrics.ram_percent:.0f}%", fill=(120, 130, 150), font=self.font_tiny)

        return img

    def render_bignum(self, metrics: SystemMetrics, metric_type: str = "cpu") -> Image.Image:
        """
        Big Number theme: Displays one massive prominent metric in the center
        with a 270-degree tachometer arc gauge and secondary stats below.
        """
        img = Image.new("RGB", (WIDTH, HEIGHT), color=(10, 12, 18))
        draw = ImageDraw.Draw(img)

        cx, cy = WIDTH // 2, HEIGHT // 2

        # Outer subtle frame
        draw.ellipse([8, 8, WIDTH - 8, HEIGHT - 8], outline=(28, 32, 44), width=2)

        # Determine primary metric and color
        if metric_type == "gpu":
            title = "GPU UTILIZATION"
            primary_val = min(100.0, max(0.0, metrics.gpu_percent))
            temp_val = metrics.gpu_temp
            accent_color = (0, 230, 120)
        else:
            title = "CPU UTILIZATION"
            primary_val = min(100.0, max(0.0, metrics.cpu_percent))
            temp_val = metrics.cpu_temp
            accent_color = (0, 180, 255)

        # Dynamic arc color (Cyan/Green -> Orange if >75% -> Red if >90%)
        if primary_val >= 90:
            gauge_color = (255, 50, 50)
        elif primary_val >= 75:
            gauge_color = (255, 170, 0)
        else:
            gauge_color = accent_color

        # 270-degree sweep arc: starts at 135 deg, ends at 405 deg (45 deg)
        bbox = [18, 18, WIDTH - 18, HEIGHT - 18]
        draw.arc(bbox, start=135, end=405, fill=(30, 36, 50), width=9)
        sweep_angle = 270.0 * (primary_val / 100.0)
        if sweep_angle > 0:
            draw.arc(bbox, start=135, end=135 + sweep_angle, fill=gauge_color, width=9)

        # Title at top
        draw.text((cx - 52, 40), title, fill=accent_color, font=self.font_tiny)

        # Giant number in center
        val_str = f"{primary_val:.0f}"
        # Measure text to center it
        num_bbox = draw.textbbox((0, 0), val_str, font=self.font_giant)
        num_w = num_bbox[2] - num_bbox[0]
        unit_w = 18

        start_x = cx - (num_w + unit_w) // 2
        draw.text((start_x, 66), val_str, fill=(255, 255, 255), font=self.font_giant)
        draw.text((start_x + num_w + 3, 76), "%", fill=accent_color, font=self.font_medium)

        # Secondary stats row (Temp and RAM)
        sec_text = f"TEMP: {temp_val:.0f}°C   RAM: {metrics.ram_percent:.0f}%"
        sec_bbox = draw.textbbox((0, 0), sec_text, font=self.font_tiny)
        sec_w = sec_bbox[2] - sec_bbox[0]
        draw.text((cx - sec_w // 2, 148), sec_text, fill=(160, 175, 195), font=self.font_tiny)

        # Divider line
        draw.line([cx - 45, 168, cx + 45, 168], fill=(35, 42, 58), width=1)

        # Current Time at bottom
        now = datetime.datetime.now().strftime("%H:%M")
        time_bbox = draw.textbbox((0, 0), now, font=self.font_small)
        time_w = time_bbox[2] - time_bbox[0]
        draw.text((cx - time_w // 2, 176), now, fill=(200, 205, 215), font=self.font_small)

        return img
