"""
03_safe_move_demo.py — Demonstrate safe motion with clamped bounds.

Moves the robot through a small sequence of positions relative to home
(calibrated if available, else READY_POSE), using the safe_move() helper from utils.py.

Uses SAFE_BOUNDS with moderate deltas. At far X,Y the Z ceiling drops; if you see
PLAN_INV_CALC/PLAN_INV_LIMIT or [safe_move] LIMIT drift, reduce DZ or use
bounds=CONSERVATIVE_BOUNDS.

Usage:
    python 03_safe_move_demo.py
"""

import sys
import time
from pydobotplus import Dobot
from utils import (
    find_port, go_home, safe_move, check_alarms, do_homing,
    get_home, SAFE_BOUNDS,
)


def main():
    PORT = find_port()
    if PORT is None:
        sys.exit("[Error] No serial port found. Run 01_find_port.py first.")

    bot = Dobot(port=PORT)
    print(f"Connected on {PORT}")

    try:
        alarms = bot.get_alarms()
        if alarms:
            print("Clearing alarms:", ", ".join(a.name for a in alarms))
            bot.clear_alarms()
            # Limit alarms mean robot needs homing before motion
            if any("LIMIT" in a.name for a in alarms):
                do_homing(bot)

        # --- Go to ready pose first ---
        print("\nMoving to home ...")
        go_home(bot)
        time.sleep(0.5)

        # --- Demo moves near SAFE_BOUNDS limits for visible motion ---
        X0, Y0, Z0, R0 = get_home()
        # Smaller deltas to avoid PLAN_INV_CALC/PLAN_INV_LIMIT at far X,Y (Z ceiling drops)
        DX, DY, DZ, DR = 35, 60, 25, 35  # mm / deg

        moves = [
            ("Forward  +X",    X0 + DX,     Y0,          Z0,        R0),
            ("Left     +Y",    X0 + DX,     Y0 + DY,     Z0,        R0),
            ("Up       +Z",    X0 + DX,     Y0 + DY,     Z0 + DZ,   R0),
            ("Right   -Y",     X0 + DX,     Y0,          Z0 + DZ,   R0),
            ("Rotate  +R",     X0 + DX,     Y0,          Z0 + DZ,   R0 + DR),
            ("Down     -Z",    X0 + DX,     Y0,          Z0,        R0 + DR),
            ("Back    -X",     X0,          Y0,          Z0,        R0 + DR),
            ("Left   +Y 2",    X0,          Y0 + DY,     Z0,        R0 + DR),
            ("Rotate -R",      X0,          Y0 + DY,     Z0,        R0),
            ("Right  -Y 2",    X0,          Y0,          Z0,        R0),
            ("Back home",      X0,          Y0,          Z0,        R0),
        ]

        for label, x, y, z, r in moves:
            print(f"  {label:15s} -> ({x:.0f}, {y:.0f}, {z:.0f}, {r:.0f})")
            safe_move(bot, x, y, z, r, bounds=SAFE_BOUNDS, verify=True)
            time.sleep(0.3)

        check_alarms(bot)
        print("\nDemo complete.")
    finally:
        bot.close()


if __name__ == "__main__":
    main()
