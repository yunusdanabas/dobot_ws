#!/usr/bin/env python3
"""
Motion Modes Demo (Track A: pydobotplus)

Demonstrates the three core PTP motion modes:
  MOVJ_XYZ — joint interpolation (curved path, fastest)
  MOVL_XYZ — straight-line Cartesian path (required for drawing/writing)
  JUMP_XYZ — firmware Z-lift (simplest pick-and-place pattern)

The script traces the same 3-point path twice (MOVJ then MOVL) so students
can see the end-effector path difference, then shows JUMP mode.

Run with:
    python scripts/12_motion_modes.py [--no-viz]
"""

import argparse
import sys
import time
from pydobotplus import Dobot, MODE_PTP
from utils import find_port, safe_move, go_home, get_home, check_alarms, JUMP_HEIGHT
from viz import RobotViz


def _waypoints():
    """Waypoints relative to home for MOVJ vs MOVL comparison."""
    hx, hy, hz, hr = get_home()
    return [
        (hx + 30,  hy + 60,  hz - 20, 0),
        (hx,       hy - 60,  hz - 20, 0),
        (hx + 60,  hy,       hz - 20, 0),
    ]


def _jump_points():
    """Two points for JUMP_XYZ demo (relative to home)."""
    hx, hy, hz, hr = get_home()
    return (hx + 20, hy - 50, hz - 50, 0), (hx + 20, hy + 50, hz - 50, 0)


def demo():
    parser = argparse.ArgumentParser(description="Motion modes demo")
    parser.add_argument("--no-viz", action="store_true", help="Disable real-time visualization")
    args = parser.parse_args()

    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Run: python scripts/01_find_port.py")

    bot = Dobot(port=port)
    viz = RobotViz(enabled=not args.no_viz)
    viz.attach(bot)
    try:
        check_alarms(bot)
        bot.speed(50, 40)
        print("Connected. Speed set to 50 mm/s, 40 mm/s²")

        # === Demo 1: MOVJ_XYZ — joint interpolation (default mode) ===
        print("\n[Demo 1] MOVJ_XYZ — joint interpolation (curved path)")
        print("  Watch the end-effector: it takes a curved arc through space.")
        go_home(bot)
        time.sleep(0.3)
        waypoints = _waypoints()
        for i, (x, y, z, r) in enumerate(waypoints, 1):
            print(f"  [{i}/{len(waypoints)}] MOVJ → ({x:.0f}, {y:.0f}, {z:.0f})")
            safe_move(bot, x, y, z, r, mode=MODE_PTP.MOVJ_XYZ)
        go_home(bot)
        time.sleep(0.5)

        # === Demo 2: MOVL_XYZ — straight-line Cartesian path ===
        print("\n[Demo 2] MOVL_XYZ — straight-line Cartesian path (same waypoints)")
        print("  Watch the end-effector: it now travels in straight lines.")
        go_home(bot)
        time.sleep(0.3)
        waypoints = _waypoints()
        for i, (x, y, z, r) in enumerate(waypoints, 1):
            print(f"  [{i}/{len(waypoints)}] MOVL → ({x:.0f}, {y:.0f}, {z:.0f})")
            safe_move(bot, x, y, z, r, mode=MODE_PTP.MOVL_XYZ)
        go_home(bot)
        time.sleep(0.5)

        # === Demo 3: JUMP_XYZ — firmware auto-lift ===
        print("\n[Demo 3] JUMP_XYZ — firmware handles the Z-lift automatically")
        print(f"  Jump clearance: {JUMP_HEIGHT} mm above start/end Z.")
        print("  No manual LIFT coordinates needed — firmware lifts, travels, lowers.")
        bot._set_ptp_jump_params(jump=JUMP_HEIGHT, limit=120)
        go_home(bot)
        time.sleep(0.3)
        p1, p2 = _jump_points()
        print(f"  P1 → ({p1[0]:.0f}, {p1[1]:.0f}, {p1[2]:.0f})  [firmware lifts ~{JUMP_HEIGHT} mm]")
        safe_move(bot, *p1, mode=MODE_PTP.JUMP_XYZ)
        print(f"  P2 → ({p2[0]:.0f}, {p2[1]:.0f}, {p2[2]:.0f})")
        safe_move(bot, *p2, mode=MODE_PTP.JUMP_XYZ)
        go_home(bot)

        print("\nAll motion mode demos completed.")
        print("See docs/motion_modes.md for the full MODE_PTP reference.")

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
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
    demo()
