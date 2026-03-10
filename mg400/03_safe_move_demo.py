"""
03_safe_move_demo.py — safe_move() demonstration with clamping.

Shows:
  - safe_move() clamps out-of-bounds coordinates with a printed warning
  - Five waypoints traversed with joint interpolation (MovJ)
  - Intentionally out-of-bounds coordinate to show clamping behaviour

Edit WAYPOINTS to match your lab setup.

Usage:
    python 03_safe_move_demo.py [--ip 192.168.1.6]
"""

import argparse
import time

from utils_mg400 import (
    connect,
    close_all,
    check_errors,
    go_home,
    safe_move,
    SPEED_DEFAULT,
    MG400_IP,
    READY_POSE,
)

# ---------------------------------------------------------------------------
# Waypoints — all inside SAFE_BOUNDS (x: 60-400, y: -220-220, z: 5-140)
# ---------------------------------------------------------------------------
WAYPOINTS = [
    (250,    0,  80, 0),    # centre-front, mid-height
    (300,  100,  60, 15),   # right-front, lower
    (300, -100,  60, -15),  # left-front, lower
    (200,   80, 100, 10),   # centre, elevated
    (200,  -80, 100, -10),  # centre, elevated other side
]

# This coordinate has Z=-20 (below safe limit of 5 mm) — will be clamped
OUT_OF_BOUNDS = (300, 0, -20, 0)


def main():
    parser = argparse.ArgumentParser(description="safe_move clamping demo")
    parser.add_argument("--ip", default=MG400_IP, help="MG400 IP address")
    args = parser.parse_args()

    dashboard, move_api, feed = connect(args.ip)
    try:
        check_errors(dashboard)
        dashboard.EnableRobot()
        dashboard.SpeedFactor(SPEED_DEFAULT)
        print(f"Connected, enabled, speed factor = {SPEED_DEFAULT}%\n")

        print("Going to home position ...")
        go_home(move_api)
        time.sleep(0.5)

        # --- Out-of-bounds demo ---
        print(f"\n[Clamping demo] Requesting pose {OUT_OF_BOUNDS}:")
        print("  Z=-20 is below the safe floor (5 mm). Expect a clamping warning.")
        safe_move(move_api, *OUT_OF_BOUNDS)
        move_api.Sync()
        print("  Moved to clamped position (Z was raised to safe floor).")
        time.sleep(0.5)

        # --- Normal waypoints ---
        print(f"\nTraversing {len(WAYPOINTS)} waypoints with safe_move() ...")
        for i, (x, y, z, r) in enumerate(WAYPOINTS, 1):
            print(f"  [{i}/{len(WAYPOINTS)}] MovJ → ({x}, {y}, {z}, {r})")
            safe_move(move_api, x, y, z, r, mode="J")
            move_api.Sync()
            time.sleep(0.3)

        print("\nReturning to home ...")
        go_home(move_api)
        print("Safe move demo complete.")

    finally:
        try:
            dashboard.DisableRobot()
        except Exception:
            pass
        close_all(dashboard, move_api, feed)


if __name__ == "__main__":
    main()
