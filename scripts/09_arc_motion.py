#!/usr/bin/env python3
"""
Arc Motion Demo (Track A: pydobotplus)

Demonstrates:
1. Basic arc motion using go_arc()
2. Circle drawing via sampled points (XY plane)
3. Speed control for smooth arcs
4. Circle in ZX plane (vertical arc, constant Y)

Run with:
    python scripts/09_arc_motion.py [--no-viz]
"""

import argparse
import math
import sys
import time
from pydobotplus import Dobot
from pydobotplus.dobotplus import MODE_PTP
from utils import find_port, safe_move, go_home, SAFE_READY_POSE, SPEED_SMOOTH
from viz import RobotViz

def draw_circle(bot, center_x, center_y, z, radius, steps=36, viz=None):
    """
    Draw a circle by moving to sampled points (XY plane, constant Z).

    Args:
        bot: Dobot instance
        center_x, center_y: Circle center in mm
        z: Fixed height (mm)
        radius: Circle radius (mm)
        steps: Number of points (36 = 10° resolution)
        viz: Optional RobotViz instance for explicit intermediate sends
    """
    print(f"Drawing circle: center=({center_x}, {center_y}), z={z}, radius={radius}, steps={steps}")
    for i in range(steps + 1):
        angle = 2 * math.pi * i / steps
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        safe_move(bot, x, y, z, 0, mode=MODE_PTP.MOVL_XYZ)
        if viz is not None:
            viz.send(x, y, z, 0)
        if i % 12 == 0:
            print(f"  [{i:3d}/{steps}] angle={angle*180/math.pi:6.1f}° pos=({x:7.1f}, {y:7.1f})")


def draw_circle_zx(bot, center_x, center_z, y, radius, steps=36, viz=None):
    """
    Draw a circle in the ZX plane (constant Y).

    Args:
        bot: Dobot instance
        center_x, center_z: Circle center in X and Z (mm)
        y: Fixed Y position (mm)
        radius: Circle radius (mm)
        steps: Number of points (36 = 10° resolution)
        viz: Optional RobotViz instance for explicit intermediate sends
    """
    print(f"Drawing circle (ZX): center_x={center_x}, center_z={center_z}, y={y}, radius={radius}, steps={steps}")
    for i in range(steps + 1):
        angle = 2 * math.pi * i / steps
        x = center_x + radius * math.cos(angle)
        z = center_z + radius * math.sin(angle)
        safe_move(bot, x, y, z, 0, mode=MODE_PTP.MOVL_XYZ)
        if viz is not None:
            viz.send(x, y, z, 0)
        if i % 12 == 0:
            print(f"  [{i:3d}/{steps}] angle={angle*180/math.pi:6.1f}° pos=(x={x:7.1f}, z={z:7.1f})")


def demo_arc():
    """Simple arc motion demo."""
    parser = argparse.ArgumentParser(description="Arc motion demo")
    parser.add_argument("--no-viz", action="store_true", help="Disable real-time visualization")
    args = parser.parse_args()

    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Run: python scripts/01_find_port.py")

    bot = Dobot(port=port)
    viz = RobotViz(enabled=not args.no_viz)
    viz.attach(bot)
    try:
        print("Connected to Dobot")

        bot.speed(*SPEED_SMOOTH)
        print(f"Speed set to {SPEED_SMOOTH[0]} mm/s, {SPEED_SMOOTH[1]} mm/s²")

        go_home(bot)
        time.sleep(0.3)
        hx, hy, hz, hr = SAFE_READY_POSE
        safe_move(bot, hx, hy, hz, hr)
        print(f"At home: ({hx:.1f}, {hy:.1f}, {hz:.1f}, {hr:.1f})")
        time.sleep(0.5)
        
        # === Demo 1: Simple arc ===
        print("\n[Demo 1] Simple arc motion (go_arc)")
        safe_move(bot, hx, hy, hz, hr)
        print(f"  Starting at ({hx:.1f}, {hy:.1f}, {hz:.1f})")
        time.sleep(0.3)
        
        # Arc from home to (hx+50, 50) via intermediate (hx+20, 30)
        print(f"  Executing arc: endpoint=({hx+50:.0f}, 50), via-point=({hx+20:.0f}, 30)")
        bot.go_arc(
            x=hx+50, y=50, z=hz, r=0,
            cir_x=hx+20, cir_y=30, cir_z=hz, cir_r=0
        )
        time.sleep(0.5)
        print("  Arc completed.")
        
        # === Demo 2: Full circle ===
        print("\n[Demo 2] Full circle (36 sampled points)")
        safe_move(bot, hx+20, hy, hz, hr)
        print(f"  Centering at ({hx+20:.0f}, {hy:.0f}, {hz:.0f})")
        time.sleep(0.3)
        
        draw_circle(bot, hx+20, hy, hz, 40, steps=36, viz=viz)
        print("  Circle completed.")
        time.sleep(0.5)

        # === Demo 3: Smaller circle (faster) ===
        print("\n[Demo 3] Smaller circle with fewer steps (24 points, faster)")
        bot.speed(75, 50)
        draw_circle(bot, hx, hy-60, hz, 25, steps=24, viz=viz)
        print("  Smaller circle completed.")
        time.sleep(0.5)

        # === Demo 4: Arc in ZX plane ===
        print("\n[Demo 4] Circle in ZX plane (vertical arc, constant Y)")
        bot.speed(*SPEED_SMOOTH)
        safe_move(bot, hx+20, hy, hz, hr)
        time.sleep(0.3)
        # Center at (hx+20, hz), radius 25, y fixed at 0
        draw_circle_zx(bot, hx+20, hz, hy, 25, steps=36, viz=viz)
        print("  ZX circle completed.")
        time.sleep(0.5)

        # Return to ready
        print("\n[Return] Going home")
        go_home(bot)
        print("All demos completed successfully.")

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"\n[Error]: {e}")
        raise
    finally:
        try:
            go_home(bot)
        except Exception:
            pass
        viz.close()
        bot.close()
        print("Connection closed.")


if __name__ == "__main__":
    demo_arc()
