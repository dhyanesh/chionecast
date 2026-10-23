#!/usr/bin/env python3
"""
chione_cli.py - Command-line interface and daemon for GAMDIAS CHIONE P3 Cooler Display on Linux.
"""

import os
import sys
import time
import argparse
import signal
import threading
from typing import Optional
from PIL import Image, ImageSequence

from chione_device import ChioneDevice, VENDOR_ID, PRODUCT_ID
from system_stats import StatsCollector
from display_renderer import DisplayRenderer
from config_manager import AppConfig, load_config, save_config, print_config, get_config_path


running = True
shutdown_event = threading.Event()


def signal_handler(sig, frame):
    global running
    print("\nStopping display daemon...", flush=True)
    running = False
    shutdown_event.set()


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def test_device(dev: ChioneDevice):
    print(f"Connecting to GAMDIAS CHIONE P3 (VID: 0x{VENDOR_ID:04X}, PID: 0x{PRODUCT_ID:04X})...")
    print("✓ Successfully connected to USB AEOLUS BOX!")
    print("Setting default brightness (8) and orientation (0°)...")
    dev.set_config(rotation_deg=0, brightness=8)
    print("Clearing display...")
    dev.init_stream(clear=True)
    print("Device communication verified.")


THEMES = ["dual", "cyberpunk", "simple", "bignum", "reactor", "vortex", "hud", "ring"]
METRIC_CHOICES = ["cpu", "gpu", "ram", "vram", "none"]


def save_snapshot(
    theme: str,
    output_path: str,
    custom_bg: Optional[str] = None,
    primary: str = "cpu",
    secondary: str = "gpu",
    aux: str = "ram",
    unit: str = "C",
):
    collector = StatsCollector()
    renderer = DisplayRenderer()
    metrics = collector.get_metrics()

    if theme in ["reactor", "vortex", "hud", "ring"] or custom_bg:
        frames = renderer.load_theme_frames(theme, custom_bg=custom_bg)
        img = renderer.render_hud_overlay(
            frames[0],
            metrics,
            primary_metric=primary,
            secondary_metric=secondary,
            aux_metric=aux,
            temp_unit=unit,
        )
    elif theme == "cyberpunk":
        img = renderer.render_cyberpunk(
            metrics,
            primary_metric=primary,
            secondary_metric=secondary,
            aux_metric=aux,
            temp_unit=unit,
        )
    elif theme == "simple":
        img = renderer.render_simple(
            metrics,
            primary_metric=primary,
            secondary_metric=secondary,
            aux_metric=aux,
            temp_unit=unit,
        )
    elif theme == "bignum":
        img = renderer.render_bignum(
            metrics,
            primary_metric=primary,
            secondary_metric=secondary,
            aux_metric=aux,
            temp_unit=unit,
        )
    else:
        img = renderer.render_dual_gauge(
            metrics,
            primary_metric=primary,
            secondary_metric=secondary,
            aux_metric=aux,
            temp_unit=unit,
        )

    img.save(output_path)
    print(f"Snapshot saved to {output_path}")
    collector.close()


def run_monitor(dev: ChioneDevice, config: AppConfig):
    collector = StatsCollector()
    renderer = DisplayRenderer()
    theme = config.theme
    interval = config.interval
    custom_bg = config.custom_bg
    primary = config.primary_metric
    secondary = config.secondary_metric
    aux = config.aux_metric
    unit = config.temp_unit

    print(f"Starting hardware monitor:")
    print(f"  Theme: {theme} | Refresh: {interval}s")
    print(f"  Metrics: Primary={primary.upper()}, Secondary={secondary.upper()}, Aux={aux.upper()} (Unit: °{unit.upper()})")

    # Check if this is an overlay/animated theme
    is_overlay_theme = theme in ["reactor", "vortex", "hud", "ring"] or custom_bg is not None
    frames = []
    if is_overlay_theme:
        frames = renderer.load_theme_frames(theme, custom_bg=custom_bg)
        print(f"Loaded {len(frames)} theme background frames.")

    frame_count = 0
    last_metric_time = 0.0
    metrics = collector.get_metrics()

    frame_idx = 0
    num_frames = len(frames)

    while running and not shutdown_event.is_set():
        now = time.monotonic()
        # Refresh metrics if interval has passed
        if now - last_metric_time >= interval:
            metrics = collector.get_metrics()
            last_metric_time = now

        if is_overlay_theme and num_frames > 0:
            bg_frame = frames[frame_idx % num_frames]
            frame = renderer.render_hud_overlay(
                bg_frame,
                metrics,
                primary_metric=primary,
                secondary_metric=secondary,
                aux_metric=aux,
                temp_unit=unit,
            )
            frame_idx += 1
        elif theme == "cyberpunk":
            frame = renderer.render_cyberpunk(
                metrics,
                primary_metric=primary,
                secondary_metric=secondary,
                aux_metric=aux,
                temp_unit=unit,
            )
        elif theme == "simple":
            frame = renderer.render_simple(
                metrics,
                primary_metric=primary,
                secondary_metric=secondary,
                aux_metric=aux,
                temp_unit=unit,
            )
        elif theme == "bignum":
            frame = renderer.render_bignum(
                metrics,
                primary_metric=primary,
                secondary_metric=secondary,
                aux_metric=aux,
                temp_unit=unit,
            )
        else:
            frame = renderer.render_dual_gauge(
                metrics,
                primary_metric=primary,
                secondary_metric=secondary,
                aux_metric=aux,
                temp_unit=unit,
            )

        try:
            t_send_start = time.monotonic()
            dev.display_image(frame)
            frame_count += 1
            send_duration = time.monotonic() - t_send_start

            if frame_count % 30 == 1 or not is_overlay_theme or num_frames <= 1:
                p_label, p_val, p_sub, _ = metrics.get_metric_data(primary, unit)
                sec_part = ""
                if secondary not in ("none", "", None):
                    s_label, s_val, s_sub, _ = metrics.get_metric_data(secondary, unit)
                    sec_part = f" | {s_label} {s_val:.0f}% ({s_sub})"
                print(f"Frame {frame_count} sent | {p_label} {p_val:.0f}% ({p_sub}){sec_part} | RAM {metrics.ram_percent:.0f}%", flush=True)
        except Exception as e:
            print(f"Error streaming frame: {e}", flush=True)
            break

        # Sleep handling:
        # If animated (multiple frames), target ~25 FPS (~0.040s per frame)
        if is_overlay_theme and num_frames > 1:
            frame_target = 0.040
            sleep_time = max(0.001, min(frame_target, frame_target - send_duration))
            shutdown_event.wait(timeout=sleep_time)
        else:
            shutdown_event.wait(timeout=interval)

    collector.close()


def show_static_image(dev: ChioneDevice, image_path: str):
    print(f"Loading image: {image_path}")
    img = Image.open(image_path)
    dev.display_image(img)
    print("Image displayed.")


def play_gif(dev: ChioneDevice, gif_path: str, loop: bool = True):
    print(f"Loading GIF animation: {gif_path}")
    gif = Image.open(gif_path)
    frames = [frame.copy().convert("RGB") for frame in ImageSequence.Iterator(gif)]
    durations = [frame.info.get("duration", 100) / 1000.0 for frame in ImageSequence.Iterator(gif)]
    
    print(f"Loaded {len(frames)} frames. Streaming to LCD...")
    
    while running:
        for idx, frame in enumerate(frames):
            if not running:
                break
            dev.display_image(frame)
            time.sleep(durations[idx] if idx < len(durations) else 0.05)
        if not loop:
            break


def main():
    parser = argparse.ArgumentParser(description="GAMDIAS CHIONE P3 Cooler Display Controller for Linux")
    parser.add_argument("--test", action="store_true", help="Test device connection and communication")
    parser.add_argument("--brightness", type=int, choices=range(1, 9), help="Set brightness (1 to 8)")
    parser.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], help="Set orientation (0, 90, 180, 270 deg)")
    parser.add_argument(
        "--theme",
        choices=THEMES,
        help="Monitor theme: dual, cyberpunk, simple, bignum, reactor (animated), vortex (animated), hud (animated), ring",
    )
    parser.add_argument("--primary", choices=METRIC_CHOICES, help="Primary metric (left/top slot): cpu, gpu, ram, vram")
    parser.add_argument("--secondary", choices=METRIC_CHOICES, help="Secondary metric (right/bottom slot): cpu, gpu, ram, vram")
    parser.add_argument("--aux", choices=["ram", "vram", "none"], help="Auxiliary metric (badge slot): ram, vram, none")
    parser.add_argument("--unit", choices=["C", "F"], help="Temperature unit: C (Celsius) or F (Fahrenheit)")
    parser.add_argument("--bg", type=str, help="Custom background image or animated GIF to overlay telemetry onto")
    parser.add_argument("--image", type=str, help="Display a static image (PNG/JPG)")
    parser.add_argument("--gif", type=str, help="Play an animated GIF")
    parser.add_argument("--interval", type=float, help="Refresh interval in seconds (default: 1.0)")
    parser.add_argument("--snapshot", type=str, help="Render and save a test snapshot to PNG without sending to device")
    parser.add_argument("--save-config", action="store_true", help="Save current settings to ~/.config/chionecast/config.json")
    parser.add_argument("--show-config", action="store_true", help="Print active configuration and exit")
    parser.add_argument("--config-only", action="store_true", help="Only apply rotation/brightness or save config and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously monitoring system telemetry")
    parser.add_argument("--replace", action="store_true", help="Terminate any existing chionecast instance and take control of the display")
    parser.add_argument("--clear", action="store_true", help="Clear the display to black and exit")

    args = parser.parse_args()

    # Load persistent configuration, then apply CLI overrides
    config = load_config()
    if args.theme is not None:
        config.theme = args.theme
    if args.rotate is not None:
        config.rotate = args.rotate
    if args.brightness is not None:
        config.brightness = args.brightness
    if args.interval is not None:
        config.interval = args.interval
    if args.bg is not None:
        config.custom_bg = args.bg
    if args.primary is not None:
        config.primary_metric = args.primary
    if args.secondary is not None:
        config.secondary_metric = args.secondary
    if args.aux is not None:
        config.aux_metric = args.aux
    if args.unit is not None:
        config.temp_unit = args.unit

    if args.show_config:
        print_config(config)
        return

    if args.save_config:
        saved_path = save_config(config)
        print(f"✓ Configuration saved to {saved_path}")
        print_config(config)
        if args.config_only:
            return

    if args.snapshot:
        save_snapshot(
            config.theme,
            args.snapshot,
            custom_bg=config.custom_bg,
            primary=config.primary_metric,
            secondary=config.secondary_metric,
            aux=config.aux_metric,
            unit=config.temp_unit,
        )
        return

    dev = ChioneDevice()
    try:
        dev.open(replace=args.replace)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)

    try:
        if args.test:
            test_device(dev)
            return

        print(f"Configuring LCD: Rotation = {config.rotate}°, Brightness = {config.brightness}")
        dev.set_config(rotation_deg=config.rotate, brightness=config.brightness)
        print("Initializing LCD stream mode (clearing old frame buffer)...")
        dev.init_stream(clear=True)

        if args.clear:
            print("Display cleared to black.")
            return

        # Mode execution
        if args.image:
            show_static_image(dev, args.image)
        elif args.gif:
            play_gif(dev, args.gif)
        elif not args.config_only:
            run_monitor(dev, config)
    finally:
        dev.close()


if __name__ == "__main__":
    main()
