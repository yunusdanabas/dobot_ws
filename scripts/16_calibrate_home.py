#!/usr/bin/env python3
"""
16_calibrate_home.py — Probe axis limits and compute workspace center as home.

Moves the robot toward each axis limit (X, Y, Z, R) until a physical limit
switch triggers a LIMIT_* alarm. Records the position at each limit, computes
the center as home, and saves to .dobot_calibration.json for use by go_home()
and other scripts.

Prerequisite: Robot must be homed. If LIMIT_* alarms are present at startup,
runs do_homing() first.

Usage:
    python scripts/16_calibrate_home.py
    python scripts/16_calibrate_home.py --no-save   # Dry run, do not write file
"""

import argparse
import json
import sys
import time

from pydobotplus import Dobot

from utils import (
    find_port,
    check_alarms,
    do_homing,
    unpack_pose,
    clamp,
    READY_POSE,
    SAFE_BOUNDS,
    CALIBRATION_FILE,
)
PROBE_STEP_MM = 15
PROBE_STEP_DEG = 10
BACK_OFF_MM = 25
BACK_OFF_DEG = 15
MAX_ITERATIONS = 25   # 25 × 15 mm = 375 mm max — comfortably covers the full Dobot workspace
PROBE_SPEED = 80
PROBE_ACCEL = 80

# The firmware's kinematic Z range extends far below the table surface.
# Clamp the calibrated home Z to at least this height so go_home() never
# sends the arm to near floor-level.
HOME_Z_FLOOR = 80  # mm — minimum home Z; keeps clearance above the work surface


def _has_limit_alarm(alarms) -> bool:
    """Return True if any alarm is a physical limit."""
    return any(hasattr(a, "name") and "LIMIT" in a.name for a in alarms)


def probe_to_limit(bot, axis: str, direction: int) -> tuple[float, float, float, float] | None:
    """Move toward limit until LIMIT_* alarm. Return (x,y,z,r) at limit or None."""
    step = PROBE_STEP_DEG if axis == "r" else PROBE_STEP_MM
    delta = direction * step

    dx = delta if axis == "x" else 0
    dy = delta if axis == "y" else 0
    dz = delta if axis == "z" else 0
    dr = delta if axis == "r" else 0

    for _ in range(MAX_ITERATIONS):
        try:
            bot.move_rel(x=dx, y=dy, z=dz, r=dr, wait=True)
        except Exception as e:
            print(f"[probe] Move failed: {e}")
            alarms = bot.get_alarms()
            if _has_limit_alarm(alarms):
                bot.clear_alarms()
                x, y, z, r, *_ = unpack_pose(bot.get_pose())
                return (x, y, z, r)
            raise
        time.sleep(0.05)
        alarms = bot.get_alarms()
        if _has_limit_alarm(alarms):
            x, y, z, r, *_ = unpack_pose(bot.get_pose())
            bot.clear_alarms()
            return (x, y, z, r)
    return None


def back_off(bot, axis: str, direction: int) -> None:
    """Move away from limit to clear the switch."""
    back = BACK_OFF_DEG if axis == "r" else BACK_OFF_MM
    delta = -direction * back
    dx = delta if axis == "x" else 0
    dy = delta if axis == "y" else 0
    dz = delta if axis == "z" else 0
    dr = delta if axis == "r" else 0
    try:
        bot.move_rel(x=dx, y=dy, z=dz, r=dr, wait=True)
    except Exception:
        pass
    time.sleep(0.1)
    check_alarms(bot)


def move_to_absolute(bot, x: float, y: float, z: float, r: float) -> None:
    """Move to absolute position (no clamping)."""
    bot.move_to(x, y, z, r, wait=True)
    time.sleep(0.05)


def main():
    parser = argparse.ArgumentParser(description="Calibrate home by probing axis limits")
    parser.add_argument("--no-save", action="store_true", help="Dry run, do not write calibration file")
    args = parser.parse_args()

    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Run: python scripts/01_find_port.py")

    bot = Dobot(port=port)
    print(f"Connected on {port}")

    try:
        alarms = bot.get_alarms()
        if alarms:
            print("Clearing alarms:", ", ".join(getattr(a, "name", str(a)) for a in alarms))
            bot.clear_alarms()
            if any(getattr(a, "name", "").find("LIMIT") >= 0 for a in alarms):
                print("LIMIT alarms detected — running homing first.")
                do_homing(bot)
                time.sleep(0.5)

        bot.speed(PROBE_SPEED, PROBE_ACCEL)
        print(f"Probing at {PROBE_SPEED} mm/s, step {PROBE_STEP_MM} mm")

        x, y, z, r, *_ = unpack_pose(bot.get_pose())
        if x < 50 or x > 350 or abs(y) > 200 or z < -50 or z > 200:
            print("[WARN] Pose looks like joint angles (not mm). Ensure robot is homed.")
            print(f"  Current: x={x:.1f} y={y:.1f} z={z:.1f} r={r:.1f}")

        # Start from READY_POSE
        print("\nMoving to start position (READY_POSE) ...")
        move_to_absolute(bot, *READY_POSE)
        time.sleep(0.2)

        limits = {"x": [None, None], "y": [None, None], "z": [None, None], "r": [None, None]}

        for axis in ("x", "y", "z", "r"):
            print(f"\n--- Probing {axis.upper()} ---")
            # Positive direction
            print(f"  {axis}+ ...")
            pos = probe_to_limit(bot, axis, 1)
            if pos is None:
                print(f"  [WARN] No limit reached for {axis}+ (max iterations)")
            else:
                limits[axis][1] = pos
                print(f"  {axis}+ limit: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}, {pos[3]:.1f})")
            back_off(bot, axis, 1)
            time.sleep(0.1)

            # Negative direction
            print(f"  {axis}- ...")
            pos = probe_to_limit(bot, axis, -1)
            if pos is None:
                print(f"  [WARN] No limit reached for {axis}- (max iterations)")
            else:
                limits[axis][0] = pos
                print(f"  {axis}- limit: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}, {pos[3]:.1f})")
            back_off(bot, axis, -1)
            time.sleep(0.1)

            # Return toward center before next axis
            cx, cy, cz, cr = READY_POSE
            move_to_absolute(bot, cx, cy, cz, cr)
            time.sleep(0.1)

        # Compute home and bounds
        home_vals = []
        bounds = {}
        for axis, (lo, hi) in limits.items():
            if lo is not None and hi is not None:
                idx = "xyzr".index(axis)
                lo_val = lo[idx]
                hi_val = hi[idx]
                mid = (lo_val + hi_val) / 2
                home_vals.append(mid)
                bounds[axis] = [lo_val, hi_val]
            else:
                idx = "xyzr".index(axis)
                home_vals.append(READY_POSE[idx])
                def_b = {"x": (150, 280), "y": (-160, 160), "z": (10, 150), "r": (-90, 90)}[axis]
                bounds[axis] = list(def_b)

        raw_home = tuple(home_vals) if len(home_vals) == 4 else READY_POSE

        # Clamp home to SAFE_BOUNDS so go_home() always lands in a safe, reachable position.
        # Z is additionally floored at HOME_Z_FLOOR: the firmware's kinematic Z range extends
        # far below the physical table surface, so the raw midpoint can be dangerously low.
        home = (
            clamp(raw_home[0], *SAFE_BOUNDS["x"]),
            clamp(raw_home[1], *SAFE_BOUNDS["y"]),
            max(clamp(raw_home[2], *SAFE_BOUNDS["z"]), HOME_Z_FLOOR),
            clamp(raw_home[3], *SAFE_BOUNDS["r"]),
        )

        print("\n--- Results ---")
        if raw_home != home:
            print(f"  Raw midpoint: ({raw_home[0]:.1f}, {raw_home[1]:.1f}, {raw_home[2]:.1f}, {raw_home[3]:.1f})")
            print(f"  Clamped home: ({home[0]:.1f}, {home[1]:.1f}, {home[2]:.1f}, {home[3]:.1f})  [clamped to SAFE_BOUNDS / HOME_Z_FLOOR={HOME_Z_FLOOR}]")
        else:
            print(f"  Home: ({home[0]:.1f}, {home[1]:.1f}, {home[2]:.1f}, {home[3]:.1f})")
        print(f"  Bounds: x={bounds['x']}, y={bounds['y']}, z={bounds['z']}, r={bounds['r']}")

        if not args.no_save:
            data = {
                "home": list(home),
                "bounds": bounds,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            with open(CALIBRATION_FILE, "w") as f:
                json.dump(data, f, indent=2)
            print(f"\nCalibration saved to {CALIBRATION_FILE}")
            print("Other scripts will use this home via go_home().")
        else:
            print("\n[--no-save] Calibration NOT saved.")

        # Move to new home
        print("\nMoving to calibrated home ...")
        move_to_absolute(bot, *home)
        print("Calibration complete.")

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        bot.close()
        print("Connection closed.")


if __name__ == "__main__":
    main()
