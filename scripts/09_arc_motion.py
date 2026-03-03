#!/usr/bin/env python3
"""
Arc Motion Demo (Track A: pydobotplus)

Demonstrates:
1. Basic arc motion using go_arc()
2. Circle drawing via sampled points
3. Speed control for smooth arcs

Run with:
    python scripts/09_arc_motion.py
"""

import math
import sys
import time
from pydobotplus import Dobot
from utils import find_port, safe_move, go_home, READY_POSE

def draw_circle(bot, center_x, center_y, z, radius, steps=36):
    """
    Draw a circle by moving to sampled points.
    
    Args:
        bot: Dobot instance
        center_x, center_y: Circle center in mm
        z: Fixed height (mm)
        radius: Circle radius (mm)
        steps: Number of points (36 = 10° resolution)
    """
    print(f"Drawing circle: center=({center_x}, {center_y}), z={z}, radius={radius}, steps={steps}")
    for i in range(steps + 1):
        angle = 2 * math.pi * i / steps
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        bot.move_to(x, y, z, 0, wait=True)
        if i % 12 == 0:
            print(f"  [{i:3d}/{steps}] angle={angle*180/math.pi:6.1f}° pos=({x:7.1f}, {y:7.1f})")


def demo_arc():
    """Simple arc motion demo."""
    port = find_port()
    if port is None:
        sys.exit("❌ No serial port found. Run: python scripts/01_find_port.py")
    
    bot = Dobot(port=port)
    try:
        print("✓ Connected to Dobot")
        
        # Set slow speed for visual validation
        bot.speed(50, 40)
        print("✓ Speed set to 50 mm/s, 40 mm/s²")
        
        # Start from ready pose
        go_home(bot)
        time.sleep(0.3)
        safe_move(bot, *READY_POSE)
        print(f"✓ At ready pose: {READY_POSE}")
        time.sleep(0.5)
        
        # === Demo 1: Simple arc ===
        print("\n[Demo 1] Simple arc motion (go_arc)")
        safe_move(bot, 200, 0, 100, 0)
        print("  Starting at (200, 0, 100)")
        time.sleep(0.3)
        
        # Arc from (200, 0) to (250, 50) via intermediate (220, 30)
        print("  Executing arc: endpoint=(250, 50), via-point=(220, 30)")
        bot.go_arc(
            x=250, y=50, z=100, r=0,
            cir_x=220, cir_y=30, cir_z=100, cir_r=0
        )
        time.sleep(0.5)
        print("  ✓ Arc completed")
        
        # === Demo 2: Full circle ===
        print("\n[Demo 2] Full circle (36 sampled points)")
        safe_move(bot, 220, 0, 100, 0)
        print("  Centering at (220, 0, 100)")
        time.sleep(0.3)
        
        draw_circle(bot, 220, 0, 100, 40, steps=36)
        print("  ✓ Circle completed")
        time.sleep(0.5)
        
        # === Demo 3: Smaller circle (faster) ===
        print("\n[Demo 3] Smaller circle with fewer steps (24 points, faster)")
        bot.speed(75, 50)  # Slightly faster
        draw_circle(bot, 200, -60, 100, 25, steps=24)
        print("  ✓ Smaller circle completed")
        time.sleep(0.5)
        
        # Return to ready
        print("\n[Return] Going home")
        go_home(bot)
        print("✓ All demos completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        try:
            go_home(bot)
        except Exception:
            pass
        bot.close()
        print("✓ Connection closed")


if __name__ == "__main__":
    demo_arc()
