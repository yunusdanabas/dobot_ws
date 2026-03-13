"""
10_relative_moves.py — Relative motion with RelMovJ and RelMovL.

The MG400 has native relative move commands:
  move_api.RelMovJ(dx, dy, dz, dr)  — relative joint interpolation
  move_api.RelMovL(dx, dy, dz, dr)  — relative Cartesian linear move

safe_rel_move() in utils_mg400 provides a clamped relative move
that reads the current pose, computes the target, clamps to SAFE_BOUNDS,
then delegates to safe_move(). Use this when you want safety clamping.

Use native RelMovJ/RelMovL when you need the robot to execute a precise
relative displacement without the overhead of a GetPose() round-trip.

Demos:
  1. safe_rel_move() — clamped relative moves via utils
  2. RelMovJ()       — native relative joint moves
  3. RelMovL()       — native relative linear moves (straight lines)
  4. Relative pick-and-place pattern using vertical RelMovL for Z

Usage:
    python 10_relative_moves.py [--ip 192.168.2.9] [--viz]
    python 10_relative_moves.py --robot 2 [--viz]
"""

import argparse
import time

from utils_mg400 import (
    connect,
    close_all,
    check_errors,
    go_home,
    safe_move,
    safe_rel_move,
    SPEED_DEFAULT,
    MG400_IP,
    ROBOT_IPS,
)
from viz_mg400 import RobotViz

# Pick-and-place configuration for relative demo
PICK_ABSOLUTE = (280, -80, 50, 0)   # absolute position above pick site
PICK_DZ       = -35                  # mm: descend from approach to pick Z
PLACE_DX      = 0                    # mm: lateral offset to place site
PLACE_DY      = 160                  # mm: forward offset to place site
LIFT_DZ       = 35                   # mm: lift after pick/before place approach

SUCTION_DO = 1


def demo_safe_rel_move(dashboard, move_api) -> None:
    """safe_rel_move: clamped relative moves."""
    print("[Demo 1] safe_rel_move() — clamped relative moves")
    go_home(move_api)
    time.sleep(0.3)

    steps = [(50, 0, 0, 0), (0, 40, 0, 0), (0, 0, -20, 0), (-50, -40, 20, 0)]
    for i, (dx, dy, dz, dr) in enumerate(steps, 1):
        print(f"  [{i}] safe_rel_move dx={dx:+.0f} dy={dy:+.0f} dz={dz:+.0f} dr={dr:+.0f}")
        safe_rel_move(move_api, dashboard, dx, dy, dz, dr, mode="J")
        move_api.Sync()
        time.sleep(0.3)

    go_home(move_api)


def demo_relMovJ(move_api) -> None:
    """Native RelMovJ: relative joint-interpolated moves."""
    print("\n[Demo 2] RelMovJ() — native relative joint moves")
    go_home(move_api)
    time.sleep(0.3)

    offsets = [(30, 0, 0, 0), (0, 30, 0, 0), (-30, -30, 0, 0)]
    for i, (dx, dy, dz, dr) in enumerate(offsets, 1):
        print(f"  [{i}] RelMovJ dx={dx:+.0f} dy={dy:+.0f} dz={dz:+.0f} dr={dr:+.0f}")
        move_api.RelMovJ(dx, dy, dz, dr)
        move_api.Sync()
        time.sleep(0.3)

    go_home(move_api)


def demo_relMovL(move_api) -> None:
    """Native RelMovL: relative Cartesian linear moves."""
    print("\n[Demo 3] RelMovL() — native relative linear moves (straight lines)")
    go_home(move_api)
    time.sleep(0.3)

    # Draw a small square in XY at constant Z
    side = 40  # mm
    segments = [
        ( side,    0, 0, 0),
        (    0,  side, 0, 0),
        (-side,    0, 0, 0),
        (    0, -side, 0, 0),
    ]
    for i, (dx, dy, dz, dr) in enumerate(segments, 1):
        print(f"  [{i}] RelMovL dx={dx:+.0f} dy={dy:+.0f} dz={dz:+.0f}")
        move_api.RelMovL(dx, dy, dz, dr)
        move_api.Sync()
        time.sleep(0.2)

    go_home(move_api)


def demo_relative_pick_place(dashboard, move_api) -> None:
    """Relative pick-and-place: use RelMovL for vertical Z approach/lift."""
    print("\n[Demo 4] Relative pick-and-place")

    # Go to absolute approach position (above pick)
    safe_move(move_api, *PICK_ABSOLUTE, mode="J")
    move_api.Sync()
    print(f"  At approach: {PICK_ABSOLUTE}")
    time.sleep(0.3)

    # Descend to pick with RelMovL
    print(f"  Descend {PICK_DZ} mm to pick ...")
    move_api.RelMovL(0, 0, PICK_DZ, 0)
    move_api.Sync()

    print("  Suction ON ...")
    dashboard.ToolDO(SUCTION_DO, 1)
    time.sleep(0.4)

    # Lift with RelMovL
    print(f"  Lift {LIFT_DZ} mm ...")
    move_api.RelMovL(0, 0, LIFT_DZ, 0)
    move_api.Sync()

    # Traverse to place approach (above place) with RelMovJ
    print(f"  Traverse to place (dy={PLACE_DY}) ...")
    move_api.RelMovJ(PLACE_DX, PLACE_DY, 0, 0)
    move_api.Sync()

    # Descend to place with RelMovL
    print(f"  Descend {PICK_DZ} mm to place ...")
    move_api.RelMovL(0, 0, PICK_DZ, 0)
    move_api.Sync()

    print("  Suction OFF ...")
    dashboard.ToolDO(SUCTION_DO, 0)
    time.sleep(0.3)

    # Lift and return home
    move_api.RelMovL(0, 0, LIFT_DZ, 0)
    move_api.Sync()
    go_home(move_api)
    print("  Pick-and-place complete.")


def main():
    parser = argparse.ArgumentParser(description="MG400 relative moves demo")
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

        demo_safe_rel_move(dashboard, move_api)
        demo_relMovJ(move_api)
        demo_relMovL(move_api)
        demo_relative_pick_place(dashboard, move_api)

        print("\nRelative moves demo complete.")

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        try:
            dashboard.ToolDO(SUCTION_DO, 0)
        except Exception:
            pass
        try:
            go_home(move_api)
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
