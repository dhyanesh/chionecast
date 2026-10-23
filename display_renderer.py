"""
display_renderer.py - Renders customized 240x240 dashboard layouts for the CHIONE P3 cooler.
"""

import math
import os
import datetime
from typing import Optional, List
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from system_stats import SystemMetrics

WIDTH = 240
HEIGHT = 240

OFFICIAL_THEMES = {
    "reactor": "official/animations/official_anim_2.gif",
    "vortex": "official/animations/cgif.gif",
    "hud": "official/animations/cgif.gif",
    "ring": "official/backgrounds/preset_0.png",
    "neon": "official/backgrounds/cgif1_bg.png",
    "neon-flow": "official/animations/official_anim_1.gif",
}


def find_asset(rel_path: str) -> Optional[str]:
    """
    Locates an asset file from local workspace, package paths, or system share dir.
    """
    candidates = [
        os.path.join(os.path.dirname(__file__), "assets", rel_path),
        os.path.join(os.path.dirname(__file__), rel_path),
        os.path.join("/usr/share/chionecast/assets", rel_path),
        os.path.join(os.getcwd(), "assets", rel_path),
        rel_path,
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _get_font(size: int):
    """
    Attempts to load a standard TrueType font (Liberation, Ubuntu, DejaVu),
    falling back to PIL default font.
    """
    font_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
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
        self._frame_cache: dict[str, List[Image.Image]] = {}

    def load_theme_frames(self, theme_name: str, custom_bg: Optional[str] = None) -> List[Image.Image]:
        """
        Loads and caches frames for an animated or static theme.
        Returns a list of 240x240 RGB images.
        """
        cache_key = custom_bg or theme_name
        if cache_key in self._frame_cache:
            return self._frame_cache[cache_key]

        target_file = None
        if custom_bg:
            target_file = custom_bg if os.path.isfile(custom_bg) else find_asset(custom_bg)
        elif theme_name in OFFICIAL_THEMES:
            target_file = find_asset(OFFICIAL_THEMES[theme_name])

        if not target_file or not os.path.isfile(target_file):
            # Fallback to simple black canvas if file not found
            fallback = [Image.new("RGB", (WIDTH, HEIGHT), (12, 14, 20))]
            return fallback

        loaded_frames: List[Image.Image] = []
        try:
            im = Image.open(target_file)
            for frame in ImageSequence.Iterator(im):
                f = frame.copy().convert("RGBA")
                if f.size != (WIDTH, HEIGHT):
                    f = f.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
                loaded_frames.append(f)
        except Exception as e:
            print(f"Error loading theme assets from {target_file}: {e}")
            loaded_frames = [Image.new("RGBA", (WIDTH, HEIGHT), (12, 14, 20))]

        self._frame_cache[cache_key] = loaded_frames
        return loaded_frames

    def render_hud_overlay(
        self,
        bg_image: Image.Image,
        metrics: SystemMetrics,
        primary_metric: str = "cpu",
        secondary_metric: str = "gpu",
        aux_metric: str = "ram",
        temp_unit: str = "C",
    ) -> Image.Image:
        """
        Composites telemetry HUD onto a 240x240 background frame.
        Usage percentages are dominant, secondary metrics are styled below.
        If secondary_metric is 'none', renders a single centered card.
        """
        has_secondary = secondary_metric not in (None, "none", "")
        has_aux = aux_metric not in (None, "none", "")

        p_label, p_val, p_sub, p_col = metrics.get_metric_data(primary_metric, temp_unit)
        if has_secondary:
            s_label, s_val, s_sub, s_col = metrics.get_metric_data(secondary_metric, temp_unit)
        if has_aux:
            a_label, a_val, a_sub, a_col = metrics.get_metric_data(aux_metric, temp_unit)

        bg = bg_image.convert("RGBA") if bg_image.mode != "RGBA" else bg_image.copy()
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        cx = WIDTH // 2

        f_title = _get_font(14 if not has_secondary else 13)
        f_large = _get_font(36 if not has_secondary else 28)
        f_sub = _get_font(13 if not has_secondary else 12)
        f_small = _get_font(12)

        if has_secondary:
            # Dual Card Layout (Left & Right)
            draw.rounded_rectangle(
                [20, 58, 114, 154],
                radius=10,
                fill=(10, 16, 26, 185),
                outline=(*p_col[:3], 140),
                width=1,
            )
            draw.rounded_rectangle(
                [126, 58, 220, 154],
                radius=10,
                fill=(10, 26, 18, 185),
                outline=(*s_col[:3], 140),
                width=1,
            )

            # Left Card Content
            draw.text((34, 66), p_label, fill=p_col, font=f_title)
            draw.text((28, 84), f"{p_val:.0f}%", fill=(255, 255, 255), font=f_large)
            draw.text((32, 126), p_sub, fill=(180, 210, 235), font=f_sub)

            # Right Card Content
            draw.text((140, 66), s_label, fill=s_col, font=f_title)
            draw.text((134, 84), f"{s_val:.0f}%", fill=(255, 255, 255), font=f_large)
            draw.text((138, 126), s_sub, fill=(180, 230, 205), font=f_sub)
        else:
            # Single Centered Card Layout
            draw.rounded_rectangle(
                [62, 54, 178, 156],
                radius=10,
                fill=(10, 16, 26, 190),
                outline=(*p_col[:3], 140),
                width=1,
            )

            # Centered Label
            t_box = draw.textbbox((0, 0), p_label, font=f_title)
            draw.text((cx - (t_box[2] - t_box[0]) // 2, 64), p_label, fill=p_col, font=f_title)

            # Centered Percentage (Large)
            val_str = f"{p_val:.0f}%"
            v_box = draw.textbbox((0, 0), val_str, font=f_large)
            draw.text((cx - (v_box[2] - v_box[0]) // 2, 84), val_str, fill=(255, 255, 255), font=f_large)

            # Centered Subtitle
            s_box = draw.textbbox((0, 0), p_sub, font=f_sub)
            draw.text((cx - (s_box[2] - s_box[0]) // 2, 128), p_sub, fill=(180, 215, 240), font=f_sub)

        # Bottom Badge: Aux and Clock
        now = datetime.datetime.now().strftime("%H:%M")
        if has_aux:
            draw.rounded_rectangle(
                [54, 168, 186, 198],
                radius=8,
                fill=(12, 16, 22, 195),
                outline=(45, 55, 75, 140),
                width=1,
            )
            draw.text((64, 175), f"{a_label} {a_val:.0f}%", fill=(180, 190, 210), font=f_small)
            draw.text((140, 175), now, fill=(255, 255, 255), font=f_small)
        else:
            # Clock only pill
            draw.rounded_rectangle(
                [90, 168, 150, 198],
                radius=8,
                fill=(12, 16, 22, 195),
                outline=(45, 55, 75, 140),
                width=1,
            )
            draw.text((102, 175), now, fill=(255, 255, 255), font=f_small)

        return Image.alpha_composite(bg, overlay).convert("RGB")

    def render_neon_ring(
        self,
        bg_image: Image.Image,
        metrics: SystemMetrics,
        primary_metric: str = "gpu",
        temp_unit: str = "C",
    ) -> Image.Image:
        """
        Renders the authentic GAMDIAS single-metric neon ring theme.
        Matches the official Windows application layout (Grid_CPUID):
        - Top: Metric label (e.g. "GPU" or "CPU")
        - Center: Value formatted with 1 decimal place (e.g. "4.0")
        - Bottom: Unit symbol (e.g. "%")
        """
        p_label, p_val, p_sub, _ = metrics.get_metric_data(primary_metric, temp_unit)
        bg = bg_image.convert("RGBA") if bg_image.mode != "RGBA" else bg_image.copy()
        if bg.size != (WIDTH, HEIGHT):
            bg = bg.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)

        draw = ImageDraw.Draw(bg)
        cx = WIDTH // 2

        # Title: "GPU" or "CPU" (Bold, 26px, centered at Y=44)
        f_title = _get_font(26)
        t_box = draw.textbbox((0, 0), p_label, font=f_title)
        tw = t_box[2] - t_box[0]
        draw.text((cx - tw // 2, 44), p_label, fill=(255, 255, 255), font=f_title)

        # Primary Value: e.g. "4.0" (Large bold, 62px, centered at Y=78)
        f_num = _get_font(62)
        val_str = f"{p_val:.1f}"
        v_box = draw.textbbox((0, 0), val_str, font=f_num)
        vw = v_box[2] - v_box[0]
        draw.text((cx - vw // 2, 78), val_str, fill=(255, 255, 255), font=f_num)

        # Unit: "%" (Bold, 24px, centered at Y=154)
        f_unit = _get_font(24)
        u_box = draw.textbbox((0, 0), "%", font=f_unit)
        uw = u_box[2] - u_box[0]
        draw.text((cx - uw // 2, 154), "%", fill=(255, 255, 255), font=f_unit)

        return bg.convert("RGB")

    def render_dual_gauge(
        self,
        metrics: SystemMetrics,
        primary_metric: str = "cpu",
        secondary_metric: str = "gpu",
        aux_metric: str = "ram",
        temp_unit: str = "C",
    ) -> Image.Image:
        """
        Renders gauge dashboard. If secondary_metric is 'none', renders a single
        wide sweep arc for the primary metric.
        """
        has_secondary = secondary_metric not in (None, "none", "")
        has_aux = aux_metric not in (None, "none", "")

        p_label, p_val, p_sub, p_col = metrics.get_metric_data(primary_metric, temp_unit)
        if has_secondary:
            s_label, s_val, s_sub, s_col = metrics.get_metric_data(secondary_metric, temp_unit)
        if has_aux:
            a_label, a_val, a_sub, a_col = metrics.get_metric_data(aux_metric, temp_unit)

        img = Image.new("RGB", (WIDTH, HEIGHT), color=(12, 14, 20))
        draw = ImageDraw.Draw(img)
        cx, cy = WIDTH // 2, HEIGHT // 2

        # Draw outer circle subtle border
        draw.ellipse([8, 8, WIDTH - 8, HEIGHT - 8], outline=(35, 40, 55), width=2)

        if has_secondary:
            # Left Arc: Primary Metric (130 deg to 230 deg)
            bbox_p = [18, 18, WIDTH - 18, HEIGHT - 18]
            draw.arc(bbox_p, start=130, end=230, fill=(35, 45, 65), width=8)
            p_span = 100 * (min(100.0, max(0.0, p_val)) / 100.0)
            draw.arc(bbox_p, start=230 - p_span, end=230, fill=p_col, width=8)

            # Right Arc: Secondary Metric (-50 deg to 50 deg)
            bbox_s = [18, 18, WIDTH - 18, HEIGHT - 18]
            draw.arc(bbox_s, start=-50, end=50, fill=(35, 55, 45), width=8)
            s_span = 100 * (min(100.0, max(0.0, s_val)) / 100.0)
            draw.arc(bbox_s, start=-50, end=-50 + s_span, fill=s_col, width=8)

            # Left Content: Percentage LARGE, Subtitle SMALL
            draw.text((36, 62), p_label, fill=p_col, font=self.font_medium)
            draw.text((30, 86), f"{p_val:.0f}%", fill=(255, 255, 255), font=self.font_large)
            draw.text((34, 128), p_sub, fill=(170, 200, 220), font=self.font_small)

            # Right Content: Percentage LARGE, Subtitle SMALL
            draw.text((150, 62), s_label, fill=s_col, font=self.font_medium)
            draw.text((144, 86), f"{s_val:.0f}%", fill=(255, 255, 255), font=self.font_large)
            draw.text((148, 128), s_sub, fill=(170, 220, 190), font=self.font_small)

            # Divider line
            draw.line([cx, 72, cx, 148], fill=(45, 55, 75), width=1)
        else:
            # Single Centered 220° Sweep Arc
            bbox = [18, 18, WIDTH - 18, HEIGHT - 18]
            draw.arc(bbox, start=160, end=380, fill=(35, 45, 65), width=9)
            sweep = 220.0 * (min(100.0, max(0.0, p_val)) / 100.0)
            if sweep > 0:
                draw.arc(bbox, start=160, end=160 + sweep, fill=p_col, width=9)

            # Title
            t_box = draw.textbbox((0, 0), p_label, font=self.font_medium)
            draw.text((cx - (t_box[2] - t_box[0]) // 2, 54), p_label, fill=p_col, font=self.font_medium)

            # Percentage Large
            val_str = f"{p_val:.0f}%"
            v_box = draw.textbbox((0, 0), val_str, font=self.font_huge)
            draw.text((cx - (v_box[2] - v_box[0]) // 2, 78), val_str, fill=(255, 255, 255), font=self.font_huge)

            # Subtitle
            s_box = draw.textbbox((0, 0), p_sub, font=self.font_small)
            draw.text((cx - (s_box[2] - s_box[0]) // 2, 130), p_sub, fill=(170, 200, 220), font=self.font_small)

        # Center Bottom: Aux & Time
        now = datetime.datetime.now().strftime("%H:%M")
        draw.text((cx - 24, 166), now, fill=(200, 200, 210), font=self.font_medium)
        if has_aux:
            draw.text((cx - 42, 193), f"{a_label}: {a_val:.0f}%", fill=(130, 140, 160), font=self.font_tiny)

        return img

    def render_cyberpunk(
        self,
        metrics: SystemMetrics,
        primary_metric: str = "cpu",
        secondary_metric: str = "gpu",
        aux_metric: str = "ram",
        temp_unit: str = "C",
    ) -> Image.Image:
        """
        Futuristic neon theme with concentric progress rings.
        If secondary_metric is 'none', renders a single outer ring with centered readout.
        """
        has_secondary = secondary_metric not in (None, "none", "")
        has_aux = aux_metric not in (None, "none", "")

        p_label, p_val, p_sub, p_col = metrics.get_metric_data(primary_metric, temp_unit)
        if has_secondary:
            s_label, s_val, s_sub, s_col = metrics.get_metric_data(secondary_metric, temp_unit)
        if has_aux:
            a_label, a_val, a_sub, a_col = metrics.get_metric_data(aux_metric, temp_unit)

        img = Image.new("RGB", (WIDTH, HEIGHT), color=(8, 8, 12))
        draw = ImageDraw.Draw(img)
        cx, cy = WIDTH // 2, HEIGHT // 2

        # Outer ring: Primary usage
        r_outer = 102
        p_angle = int(360 * (min(100.0, max(0.0, p_val)) / 100.0))
        draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], outline=(25, 30, 45), width=5)
        if p_angle > 0:
            draw.arc([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], start=-90, end=-90 + p_angle, fill=(255, 0, 128), width=5)

        if has_secondary:
            # Middle ring: Secondary usage
            r_mid = 90
            s_angle = int(360 * (min(100.0, max(0.0, s_val)) / 100.0))
            draw.ellipse([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid], outline=(20, 40, 45), width=5)
            if s_angle > 0:
                draw.arc([cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid], start=-90, end=-90 + s_angle, fill=(0, 255, 230), width=5)

            # Center Top: Primary Usage % (Large) + Subtitle (Small)
            draw.text((cx - 36, 48), p_label, fill=(255, 0, 128), font=self.font_tiny)
            draw.text((cx - 30, 62), f"{p_val:.0f}%", fill=(255, 255, 255), font=self.font_large)
            draw.text((cx - 24, 98), p_sub, fill=(180, 140, 160), font=self.font_tiny)

            # Center Bottom: Secondary Usage % (Large) + Subtitle (Small)
            draw.text((cx - 36, 122), s_label, fill=(0, 255, 230), font=self.font_tiny)
            draw.text((cx - 30, 136), f"{s_val:.0f}%", fill=(255, 255, 255), font=self.font_large)
            draw.text((cx - 24, 172), s_sub, fill=(140, 180, 180), font=self.font_tiny)
        else:
            # Single Centered Readout
            t_box = draw.textbbox((0, 0), p_label, font=self.font_small)
            draw.text((cx - (t_box[2] - t_box[0]) // 2, 60), p_label, fill=(255, 0, 128), font=self.font_small)

            val_str = f"{p_val:.0f}%"
            v_box = draw.textbbox((0, 0), val_str, font=self.font_giant)
            draw.text((cx - (v_box[2] - v_box[0]) // 2, 82), val_str, fill=(255, 255, 255), font=self.font_giant)

            s_box = draw.textbbox((0, 0), p_sub, font=self.font_medium)
            draw.text((cx - (s_box[2] - s_box[0]) // 2, 148), p_sub, fill=(180, 160, 200), font=self.font_medium)

        # Aux at bottom
        if has_aux:
            draw.text((cx - 36, 196), f"{a_label} {a_val:.0f}%", fill=(110, 120, 140), font=self.font_tiny)

        return img

    def render_simple(
        self,
        metrics: SystemMetrics,
        primary_metric: str = "cpu",
        secondary_metric: str = "gpu",
        aux_metric: str = "ram",
        temp_unit: str = "C",
    ) -> Image.Image:
        """
        Minimalist card readout with usage percentages as large numbers.
        If secondary_metric is 'none', renders a single centered card.
        """
        has_secondary = secondary_metric not in (None, "none", "")
        has_aux = aux_metric not in (None, "none", "")

        p_label, p_val, p_sub, p_col = metrics.get_metric_data(primary_metric, temp_unit)
        if has_secondary:
            s_label, s_val, s_sub, s_col = metrics.get_metric_data(secondary_metric, temp_unit)
        if has_aux:
            a_label, a_val, a_sub, a_col = metrics.get_metric_data(aux_metric, temp_unit)

        img = Image.new("RGB", (WIDTH, HEIGHT), color=(14, 16, 22))
        draw = ImageDraw.Draw(img)
        cx = WIDTH // 2

        # Accent circle
        draw.ellipse([10, 10, WIDTH - 10, HEIGHT - 10], outline=(40, 45, 60), width=2)

        if has_secondary:
            # Top section: Primary Metric
            draw.text((42, 38), p_label, fill=p_col, font=self.font_small)
            draw.text((42, 58), f"{p_val:.0f}%", fill=(255, 255, 255), font=self.font_large)
            draw.text((136, 70), p_sub, fill=(150, 160, 180), font=self.font_small)

            # Divider
            draw.line([40, 118, WIDTH - 40, 118], fill=(45, 50, 68), width=1)

            # Bottom section: Secondary Metric
            draw.text((42, 128), s_label, fill=s_col, font=self.font_small)
            draw.text((42, 148), f"{s_val:.0f}%", fill=(255, 255, 255), font=self.font_large)
            draw.text((136, 160), s_sub, fill=(150, 160, 180), font=self.font_small)
        else:
            # Centered Single Card
            t_box = draw.textbbox((0, 0), p_label, font=self.font_medium)
            draw.text((cx - (t_box[2] - t_box[0]) // 2, 52), p_label, fill=p_col, font=self.font_medium)

            val_str = f"{p_val:.0f}%"
            v_box = draw.textbbox((0, 0), val_str, font=self.font_giant)
            draw.text((cx - (v_box[2] - v_box[0]) // 2, 78), val_str, fill=(255, 255, 255), font=self.font_giant)

            s_box = draw.textbbox((0, 0), p_sub, font=self.font_medium)
            draw.text((cx - (s_box[2] - s_box[0]) // 2, 144), p_sub, fill=(170, 180, 200), font=self.font_medium)

        # Center Bottom: Aux
        if has_aux:
            draw.text((WIDTH // 2 - 34, 198), f"{a_label}: {a_val:.0f}%", fill=(120, 130, 150), font=self.font_tiny)

        return img

    def render_bignum(
        self,
        metrics: SystemMetrics,
        primary_metric: str = "cpu",
        secondary_metric: str = "gpu",
        aux_metric: str = "ram",
        temp_unit: str = "C",
    ) -> Image.Image:
        """
        Big Number theme: Displays one massive prominent metric in the center
        with a 270-degree tachometer arc gauge and secondary stats below.
        """
        has_secondary = secondary_metric not in (None, "none", "")
        has_aux = aux_metric not in (None, "none", "")

        p_label, p_val, p_sub, p_col = metrics.get_metric_data(primary_metric, temp_unit)
        if has_secondary:
            s_label, s_val, s_sub, s_col = metrics.get_metric_data(secondary_metric, temp_unit)
        if has_aux:
            a_label, a_val, a_sub, a_col = metrics.get_metric_data(aux_metric, temp_unit)

        img = Image.new("RGB", (WIDTH, HEIGHT), color=(10, 12, 18))
        draw = ImageDraw.Draw(img)
        cx, cy = WIDTH // 2, HEIGHT // 2

        # Outer subtle frame
        draw.ellipse([8, 8, WIDTH - 8, HEIGHT - 8], outline=(28, 32, 44), width=2)

        # Dynamic arc color (Accent -> Orange if >75% -> Red if >90%)
        if p_val >= 90:
            gauge_color = (255, 50, 50)
        elif p_val >= 75:
            gauge_color = (255, 170, 0)
        else:
            gauge_color = p_col

        # 270-degree sweep arc: starts at 135 deg, ends at 405 deg (45 deg)
        bbox = [18, 18, WIDTH - 18, HEIGHT - 18]
        draw.arc(bbox, start=135, end=405, fill=(30, 36, 50), width=9)
        sweep_angle = 270.0 * (min(100.0, max(0.0, p_val)) / 100.0)
        if sweep_angle > 0:
            draw.arc(bbox, start=135, end=135 + sweep_angle, fill=gauge_color, width=9)

        # Title at top
        title = p_label
        t_bbox = draw.textbbox((0, 0), title, font=self.font_small)
        t_w = t_bbox[2] - t_bbox[0]
        draw.text((cx - t_w // 2, 40), title, fill=p_col, font=self.font_small)

        # Giant number in center
        val_str = f"{p_val:.0f}"
        num_bbox = draw.textbbox((0, 0), val_str, font=self.font_giant)
        num_w = num_bbox[2] - num_bbox[0]
        unit_w = 18

        start_x = cx - (num_w + unit_w) // 2
        draw.text((start_x, 66), val_str, fill=(255, 255, 255), font=self.font_giant)
        draw.text((start_x + num_w + 3, 76), "%", fill=p_col, font=self.font_medium)

        # Secondary stats row
        sec_parts = [p_sub]
        if has_secondary:
            sec_parts.append(f"{s_label}: {s_val:.0f}%")
        if has_aux:
            sec_parts.append(f"{a_label}: {a_val:.0f}%")
        sec_text = "   ".join(sec_parts)

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
