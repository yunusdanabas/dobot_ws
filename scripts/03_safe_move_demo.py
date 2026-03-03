"""
03_safe_move_demo.py — Demonstrate safe motion with clamped bounds.

Moves the robot through a small sequence of positions relative to the
READY_POSE, using the safe_move() helper from utils.py.

Usage:
    python 03_safe_move_demo.py
"""

import sys
import time
from pydobotplus import Dobot
from utils import find_port, go_home, safe_move, READY_POSE


def main():
    PORT = find_port()
    if PORT is None:
        sys.exit("[Error] No serial port found. Run 01_find_port.py first.")

    bot = Dobot(port=PORT)
    print(f"Connected on {PORT}")

    try:
        # --- Go to ready pose first ---
        print("\nMoving to READY_POSE ...")
        go_home(bot)
        time.sleep(0.5)

        # --- Small demo moves ---
        X0, Y0, Z0, R0 = READY_POSE
        STEP = 30   # mm

        moves = [
            ("Forward  +X", X0 + STEP, Y0,        Z0,        R0),
            ("Left     +Y", X0 + STEP, Y0 + STEP, Z0,        R0),
            ("Up       +Z", X0 + STEP, Y0 + STEP, Z0 + STEP, R0),
            ("Rotate  +R",  X0 + STEP, Y0 + STEP, Z0 + STEP, R0 + 30),
            ("Back home",   X0,        Y0,        Z0,         R0),
        ]

        for label, x, y, z, r in moves:
            print(f"  {label:15s} → ({x:.0f}, {y:.0f}, {z:.0f}, {r:.0f})")
            safe_move(bot, x, y, z, r)
            time.sleep(0.3)

        print("\nDemo complete.")
    finally:
        bot.close()


if __name__ == "__main__":
    main()
