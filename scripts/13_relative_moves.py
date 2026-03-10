#!/usr/bin/env python3
"""
Relative Moves Demo (Track A: pydobotplus)

Demonstrates incremental motion using:
  safe_rel_move(bot, dx, dy, dz, dr) — utils wrapper; applies SAFE_BOUNDS
  bot.move_rel(dx, dy, dz, dr)       — pydobotplus built-in (no bounds check)

Also shows a compact pick-and-place using relative moves instead of the
explicit Z+LIFT absolute coordinates used in 08_pick_and_place.py.

Run with:
    python scripts/13_relative_moves.py [--no-viz]
"""

import argparse
import sys
import time
from pydobotplus import Dobot
from utils import find_port, safe_move, safe_rel_move, go_home, prepare_robot, SAFE_READY_POSE, SPEED_SMOOTH
from viz import RobotViz

# Edit these to match your table layout (mm)
PICK_X,  PICK_Y,  PICK_Z  = 220, -50, 30
PLACE_X, PLACE_Y, PLACE_Z = 220,  50, 30
APPROACH_HEIGHT = 50   # mm above pick/place Z before descending


def demo():
    parser = argparse.ArgumentParser(description="Relative moves demo")
    parser.add_argument("--no-viz", action="store_true", help="Disable real-time visualization")
    args = parser.parse_args()

    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Run: python scripts/01_find_port.py")

    bot = Dobot(port=port)
    viz = RobotViz(enabled=not args.no_viz)
    viz.attach(bot)
    try:
        prepare_robot(bot)
        bot.speed(*SPEED_SMOOTH)
        print(f"Connected. Speed set to {SPEED_SMOOTH[0]} mm/s, {SPEED_SMOOTH[1]} mm/s²")

        print("\n[Demo 1] safe_rel_move — incremental adjustments from current pose")
        go_home(bot)
        time.sleep(0.3)
        hx, hy, hz, hr = SAFE_READY_POSE
        safe_move(bot, hx, hy, hz - 20, hr)

        print("  +30 mm in X ...")
        safe_rel_move(bot, dx=30)
        time.sleep(0.3)

        print("  +40 mm in Y ...")
        safe_rel_move(bot, dy=40)
        time.sleep(0.3)

        print("  -20 mm in Z ...")
        safe_rel_move(bot, dz=-20)
        time.sleep(0.3)

        print("  Combined move back to start ...")
        safe_rel_move(bot, dx=-30, dy=-40, dz=20)
        go_home(bot)
        time.sleep(0.5)

        # === Demo 2: Compact pick-and-place with relative moves ===
        print("\n[Demo 2] Pick-and-place using relative moves")
        print("  Advantage: only need the pick/place X,Y,Z — no explicit LIFT coord.")
        print("  Approach above pick position ...")
        safe_move(bot, PICK_X, PICK_Y, PICK_Z + APPROACH_HEIGHT, 0)

        print("  Descend to pick ...")
        safe_rel_move(bot, dz=-APPROACH_HEIGHT)

        print("  Suction ON ...")
        bot.suck(True)
        time.sleep(0.4)

        print("  Lift ...")
        safe_rel_move(bot, dz=APPROACH_HEIGHT)

        dx = PLACE_X - PICK_X
        dy = PLACE_Y - PICK_Y
        print(f"  Translate (dx={dx:+}, dy={dy:+}) to above place ...")
        safe_rel_move(bot, dx=dx, dy=dy)

        print("  Descend to place ...")
        safe_rel_move(bot, dz=-APPROACH_HEIGHT)

        print("  Suction OFF ...")
        bot.suck(False)
        time.sleep(0.3)

        print("  Lift ...")
        safe_rel_move(bot, dz=APPROACH_HEIGHT)

        go_home(bot)
        print("\nRelative moves demo completed.")

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        raise
    finally:
        try:
            bot.suck(False)
        except Exception:
            pass
        try:
            go_home(bot)
        except Exception:
            pass
        viz.close()
        bot.close()
        print("Connection closed.")


if __name__ == "__main__":
    demo()
