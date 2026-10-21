#!/usr/bin/env python3
"""
chione_cli.py - Command-line interface and daemon for GAMDIAS CHIONE P3 Cooler Display on Linux.
"""

import os
import sys
import time
import argparse
import signal
from PIL import Image, ImageSequence

from chione_device import ChioneDevice, VENDOR_ID, PRODUCT_ID
from system_stats import StatsCollector
from display_renderer import DisplayRenderer


running = True


def signal_handler(sig, frame):
    global running
    print("\nStopping display daemon...")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def test_device():
    print(f"Connecting to GAMDIAS CHIONE P3 (VID: 0x{VENDOR_ID:04X}, PID: 0x{PRODUCT_ID:04X})...")
    dev = ChioneDevice()
    try:
        dev.open()
        print(" Successfully connected to USB AEOLUS BOX!")
        print("Setting default brightness (8) and orientation (0°)...")
        dev.set_config(rotation_deg=0, brightness=8)
        print("Device communication verified.")
        dev.close()
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)


def save_snapshot(theme: str, output_path: str):
    collector = StatsCollector()
    renderer = DisplayRenderer()
    metrics = collector.get_metrics()
    
    if theme == "cyberpunk":
        img = renderer.render_cyberpunk(metrics)
    elif theme == "simple":
        img = renderer.render_simple(metrics)
    else:
        img = renderer.render_dual_gauge(metrics)
        
    img.save(output_path)
    print(f"Snapshot saved to {output_path}")
    collector.close()


def run_monitor(dev: ChioneDevice, theme: str = "dual", interval: float = 1.0):
    collector = StatsCollector()
    renderer = DisplayRenderer()
    print(f"Starting hardware monitor with theme '{theme}' (refresh interval: {interval}s)...")

    while running:
        metrics = collector.get_metrics()
        if theme == "cyberpunk":
            frame = renderer.render_cyberpunk(metrics)
        elif theme == "simple":
            frame = renderer.render_simple(metrics)
        else:
            frame = renderer.render_dual_gauge(metrics)

        try:
            dev.display_image(frame)
        except Exception as e:
            print(f"Error streaming frame: {e}")
            break

        time.sleep(interval)

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
    parser.add_argument("--theme", choices=["dual", "cyberpunk", "simple"], default="dual", help="Monitor dashboard theme")
    parser.add_argument("--image", type=str, help="Display a static image (PNG/JPG)")
    parser.add_argument("--gif", type=str, help="Play an animated GIF")
    parser.add_argument("--interval", type=float, default=1.0, help="Refresh interval in seconds (default: 1.0)")
    parser.add_argument("--snapshot", type=str, help="Render and save a test snapshot to PNG without sending to device")
    parser.add_argument("--daemon", action="store_true", help="Run continuously monitoring system telemetry")

    args = parser.parse_args()

    if args.snapshot:
        save_snapshot(args.theme, args.snapshot)
        return

    if args.test:
        test_device()
        return

    dev = ChioneDevice()
    dev.open()

    try:
        # Configuration settings
        if args.rotate is not None or args.brightness is not None:
            rot = args.rotate if args.rotate is not None else 0
            bri = args.brightness if args.brightness is not None else 8
            print(f"Configuring LCD: Rotation = {rot}°, Brightness = {bri}")
            dev.set_config(rotation_deg=rot, brightness=bri)

        # Mode execution
        if args.image:
            show_static_image(dev, args.image)
        elif args.gif:
            play_gif(dev, args.gif)
        elif args.daemon or (not args.image and not args.gif and args.rotate is None and args.brightness is None):
            run_monitor(dev, theme=args.theme, interval=args.interval)
    finally:
        dev.close()


if __name__ == "__main__":
    main()
