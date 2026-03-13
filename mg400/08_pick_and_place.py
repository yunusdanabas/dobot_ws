"""
08_pick_and_place.py — Pick-and-place using suction cup and Arch mode.

Approach pattern:
  1. Configure Arch jump height via dashboard.LimZ(JUMP_HEIGHT)
  2. pick_up():  approach Z+LIFT → descend → suction ON → lift
  3. place_down(): approach Z+LIFT → descend → suction OFF → lift

The MG400 also supports dashboard.Arch(index) + move_api.MovJIO() for
firmware-managed arch moves, but explicit lift/descend gives more
control and is easier for students to debug.

Edit PICK and PLACE constants to match your table layout.

Usage:
    python 08_pick_and_place.py [--ip 192.168.2.9] [--viz]
    python 08_pick_and_place.py --robot 2 [--viz]
"""

import argparse
import sys
import time

from utils_mg400 import (
    connect,
    close_all,
    check_errors,
    go_home,
    safe_move,
    SPEED_DEFAULT,
    JUMP_HEIGHT,
    SAFE_BOUNDS,
    MG400_IP,
    ROBOT_IPS,
)
from viz_mg400 import RobotViz

# ---------------------------------------------------------------------------
# User configuration — set to match your physical setup (mm)
# ---------------------------------------------------------------------------
PICK_X,  PICK_Y,  PICK_Z  = 280, -80, 20   # object pick position
PLACE_X, PLACE_Y, PLACE_Z = 280,  80, 20   # object place position
LIFT  = JUMP_HEIGHT   # mm above pick/place Z for safe travel
R     = 0             # end-effector rotation (deg)

SUCTION_DO = 1        # ToolDO index for suction pump

# ---------------------------------------------------------------------------
# Bounds check helper
# ---------------------------------------------------------------------------

def _check(label: str, x: float, y: float, z: float) -> None:
    issues = []
    if not (SAFE_BOUNDS["x"][0] <= x <= SAFE_BOUNDS["x"][1]):
        issues.append(f"X={x} outside {SAFE_BOUNDS['x']}")
    if not (SAFE_BOUNDS["y"][0] <= y <= SAFE_BOUNDS["y"][1]):
        issues.append(f"Y={y} outside {SAFE_BOUNDS['y']}")
    if not (SAFE_BOUNDS["z"][0] <= z <= SAFE_BOUNDS["z"][1]):
        issues.append(f"Z={z} outside {SAFE_BOUNDS['z']}")
    if issues:
        print(f"[Warning] {label}: {', '.join(issues)}")


# ---------------------------------------------------------------------------
# Motion primitives
# ---------------------------------------------------------------------------

def pick_up(dashboard, move_api) -> None:
    """Approach from above, pick with suction, retract."""
    print("  Approach pick ...")
    safe_move(move_api, PICK_X, PICK_Y, PICK_Z + LIFT, R, mode="J")
    move_api.Sync()

    print("  Descend to pick ...")
    safe_move(move_api, PICK_X, PICK_Y, PICK_Z, R, mode="L")
    move_api.Sync()

    print("  Suction ON ...")
    dashboard.ToolDO(SUCTION_DO, 1)
    time.sleep(0.4)   # allow vacuum to build

    print("  Lift ...")
    safe_move(move_api, PICK_X, PICK_Y, PICK_Z + LIFT, R, mode="L")
    move_api.Sync()


def place_down(dashboard, move_api) -> None:
    """Move to place, descend, release suction, retract."""
    print("  Approach place ...")
    safe_move(move_api, PLACE_X, PLACE_Y, PLACE_Z + LIFT, R, mode="J")
    move_api.Sync()

    print("  Descend to place ...")
    safe_move(move_api, PLACE_X, PLACE_Y, PLACE_Z, R, mode="L")
    move_api.Sync()

    print("  Suction OFF ...")
    dashboard.ToolDO(SUCTION_DO, 0)
    time.sleep(0.3)

    print("  Lift ...")
    safe_move(move_api, PLACE_X, PLACE_Y, PLACE_Z + LIFT, R, mode="L")
    move_api.Sync()


# ---------------------------------------------------------------------------
# Main sequence
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MG400 pick-and-place demo")
    parser.add_argument("--ip", default=MG400_IP, help="MG400 IP address")
    parser.add_argument("--robot", type=int, choices=[1, 2, 3, 4], metavar="N",
                        help="Robot number 1-4 (overrides --ip)")
    parser.add_argument("--viz", action="store_true", help="Enable visualizer")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    dashboard, move_api, feed = connect(ip)
    viz = RobotViz(enabled=args.viz)
    viz.attach(move_api)

    try:
        check_errors(dashboard)
        dashboard.EnableRobot()
        dashboard.SpeedFactor(SPEED_DEFAULT)
        print(f"Connected, enabled, speed = {SPEED_DEFAULT}%\n")

        # Validate coordinate safety
        _check("PICK", PICK_X, PICK_Y, PICK_Z)
        _check("PICK_APPROACH", PICK_X, PICK_Y, PICK_Z + LIFT)
        _check("PLACE", PLACE_X, PLACE_Y, PLACE_Z)
        _check("PLACE_APPROACH", PLACE_X, PLACE_Y, PLACE_Z + LIFT)

        print("Going to home ...")
        go_home(move_api)
        time.sleep(0.5)

        print("\n--- PICK ---")
        pick_up(dashboard, move_api)

        print("\n--- PLACE ---")
        place_down(dashboard, move_api)

        print("\nReturning to home ...")
        go_home(move_api)
        print("Pick-and-place complete.")

    finally:
        try:
            dashboard.ToolDO(SUCTION_DO, 0)   # safety: always de-assert on exit
        except Exception:
            pass
        try:
            viz.close()
        except Exception:
            pass
        try:
            dashboard.DisableRobot()
        except Exception:
            pass
        close_all(dashboard, move_api, feed)


if __name__ == "__main__":
    main()
