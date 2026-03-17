#!/usr/bin/env python3
"""
Circle Drawing via Queue (Track B: dobot-python Interface)

Demonstrates high-throughput circle drawing using:
- Point-to-point queue commands
- Queue index monitoring (back-pressure)
- Smooth Cartesian interpolation

Setup:
    cd /path/for/vendor-code
    git clone https://github.com/AlexGustafsson/dobot-python.git

Run with (after setting DOBOT_PYTHON_PATH):
    export DOBOT_PYTHON_PATH=/path/to/dobot-python          # Linux/macOS
    $env:DOBOT_PYTHON_PATH='C:\\path\\to\\dobot-python'    # Windows PowerShell
    python scripts/10_circle_queue.py
"""

import math
import sys
import time
import os

# Add Track B library to path
dobot_python_path = os.environ.get('DOBOT_PYTHON_PATH')
if dobot_python_path:
    sys.path.insert(0, dobot_python_path)
else:
    print("DOBOT_PYTHON_PATH not set. Trying common locations...")
    for candidate in [
        "../vendor/dobot-python",
        "vendor/dobot-python",
    ]:
        if os.path.isdir(candidate):
            sys.path.insert(0, candidate)
            print(f"  Found at: {candidate}")
            break
    else:
        sys.exit("[Error] dobot-python not found. Set DOBOT_PYTHON_PATH or clone the repo.")

try:
    from lib.interface import Interface
    from utils import find_port, SAFE_READY_POSE, SPEED_SMOOTH
except ImportError as e:
    sys.exit(f"[Error] Import failed: {e}\nEnsure DOBOT_PYTHON_PATH is set correctly.")


def draw_circle_queue(bot, center_x, center_y, z, radius, steps=72):
    """
    Draw a high-resolution circle using Track B queue commands.
    
    Parameters:
        bot: Interface instance
        center_x, center_y: Circle center in mm
        z: Fixed height (mm)
        radius: Circle radius (mm)
        steps: Number of points (72 = 5° resolution)
    
    Behavior:
        - Queues all points without waiting between commands
        - Monitors queue index to prevent overflow
        - Uses mode=3 (linear Cartesian interpolation)
    """
    vel, acc = SPEED_SMOOTH
    
    # Configure speed for all subsequent commands
    print(f"Setting speed: vel={vel} mm/s, acc={acc} mm/s²")
    bot.set_point_to_point_coordinate_params(vel, vel, acc, acc, queue=True)
    bot.set_point_to_point_common_params(vel, acc, queue=True)
    time.sleep(0.1)
    
    print(f"Queueing circle: center=({center_x}, {center_y}), z={z}, radius={radius}, steps={steps}")
    
    last_idx = None
    for i in range(steps + 1):
        angle = 2 * math.pi * i / steps
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        
        # Queue point (mode=3 = linear in Cartesian space)
        last_idx = bot.set_point_to_point_command(3, x, y, z, 0, queue=True)
        
        if i % 18 == 0:
            print(f"  [{i:3d}/{steps}] angle={angle*180/math.pi:6.1f}° pos=({x:7.1f}, {y:7.1f}) idx={last_idx}")
    
    # Wait for all queued commands to finish
    print(f"Waiting for queue to finish (last_idx={last_idx})...")
    wait_start = time.time()
    while bot.get_current_queue_index() < last_idx:
        current_idx = bot.get_current_queue_index()
        elapsed = time.time() - wait_start
        if int(elapsed) % 2 == 0:  # Print every ~2 seconds
            print(f"  Queue progress: {current_idx}/{last_idx}")
        time.sleep(0.05)
    
    elapsed = time.time() - wait_start
    print(f"Circle completed in {elapsed:.1f}s")


def demo_circles():
    """Draw multiple circles with different parameters."""
    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Run: python scripts/01_find_port.py")

    bot = Interface(port)
    try:
        print("Connected to Dobot (Track B)")
        hx, hy, hz, hr = SAFE_READY_POSE
        
        # Move to start position
        print(f"\nMoving to start position ({hx:.0f}, {hy:.0f}, {hz:.0f})...")
        bot.set_point_to_point_command(3, hx, hy, hz, hr, queue=True)
        time.sleep(1.5)
        
        # === Circle 1: Medium resolution ===
        print("\n[Circle 1] Medium resolution (36 points)")
        draw_circle_queue(bot, hx + 20, hy, hz, 40, steps=36)
        time.sleep(0.5)
        
        # === Circle 2: High resolution ===
        print("\n[Circle 2] High resolution (72 points)")
        draw_circle_queue(bot, hx + 20, hy, hz, 40, steps=72)
        time.sleep(0.5)
        
        # === Circle 3: Small & fast ===
        print("\n[Circle 3] Small circle (24 points, faster)")
        draw_circle_queue(bot, hx, hy - 60, hz, 25, steps=24)
        time.sleep(0.5)
        
        # Return home
        print("\nReturning to start position...")
        bot.set_point_to_point_command(3, hx, hy, hz, hr, queue=True)
        time.sleep(1.0)
        
        print("\nAll circle demos completed successfully!")

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"\n[Error]: {e}")
        raise
    finally:
        bot.serial.close()
        print("Connection closed.")


if __name__ == "__main__":
    demo_circles()
