"""
11_motion_modes.py — MovJ vs MovL vs Arc path comparison.

Traces the same three waypoints in three different modes so you can
observe how the end-effector path differs:

  MovJ  — joint interpolation: each joint moves at a constant speed ratio.
           The Cartesian path is curved (robot-specific shape).

  MovL  — linear Cartesian interpolation: end-effector follows a straight
           line between each pair of points.

  Arc   — the robot follows a circular arc defined by a via-point and
           endpoint. Only adjacent point pairs are connected by arcs.

The viz window shows the XY and XZ traces side by side for comparison.
Run three times (or watch all modes in one run) to compare paths.

Usage:
    python 11_motion_modes.py [--ip 192.168.2.9] [--viz]
    python 11_motion_modes.py --robot 2 [--viz]
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
    READY_POSE,
    MG400_IP,
    ROBOT_IPS,
)
from viz_mg400 import RobotViz


# ---------------------------------------------------------------------------
# Waypoints — relative to READY_POSE
# ---------------------------------------------------------------------------

def _waypoints():
    hx, hy, hz, hr = READY_POSE
    return [
        (hx + 40,  hy + 80,  hz + 10, 0),
        (hx,       hy - 80,  hz + 10, 0),
        (hx + 80,  hy,       hz + 10, 0),
    ]


def _arc_midpoints():
    """Via-points at midangle between each adjacent waypoint pair."""
    import math
    wpts = _waypoints()
    mids = []
    for i in range(len(wpts) - 1):
        x1, y1, z1, r1 = wpts[i]
        x2, y2, z2, r2 = wpts[i + 1]
        # Displace midpoint radially outward so it's not collinear
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        mz = (z1 + z2) / 2
        # Nudge outward by 30 mm in XY to create a visible arc
        dx = mx - READY_POSE[0]
        dy = my - READY_POSE[1]
        norm = math.hypot(dx, dy) or 1
        mids.append((mx + 30 * dx / norm, my + 30 * dy / norm, mz, 0))
    return mids


def demo_movj(move_api) -> None:
    """Traverse waypoints with MovJ (joint interpolation)."""
    print("[Demo 1] MovJ — joint interpolation (curved Cartesian path)")
    go_home(move_api)
    time.sleep(0.3)
    for i, wp in enumerate(_waypoints(), 1):
        print(f"  [{i}] MovJ → ({wp[0]:.0f}, {wp[1]:.0f}, {wp[2]:.0f})")
        safe_move(move_api, *wp, mode="J")
        move_api.Sync()
        time.sleep(0.2)
    go_home(move_api)
    time.sleep(0.5)


def demo_movl(move_api) -> None:
    """Traverse waypoints with MovL (straight-line Cartesian)."""
    print("\n[Demo 2] MovL — straight-line Cartesian path (same waypoints)")
    go_home(move_api)
    time.sleep(0.3)
    for i, wp in enumerate(_waypoints(), 1):
        print(f"  [{i}] MovL → ({wp[0]:.0f}, {wp[1]:.0f}, {wp[2]:.0f})")
        safe_move(move_api, *wp, mode="L")
        move_api.Sync()
        time.sleep(0.2)
    go_home(move_api)
    time.sleep(0.5)


def demo_arc(move_api, viz) -> None:
    """Connect waypoints with Arc() moves using computed via-points."""
    print("\n[Demo 3] Arc() — circular arc between adjacent waypoints")
    wpts = _waypoints()
    mids = _arc_midpoints()

    go_home(move_api)
    # Move to start of first arc
    safe_move(move_api, *wpts[0], mode="J")
    move_api.Sync()
    time.sleep(0.3)

    for i, (via, end) in enumerate(zip(mids, wpts[1:]), 1):
        print(
            f"  [{i}] Arc via ({via[0]:.0f},{via[1]:.0f}) → end ({end[0]:.0f},{end[1]:.0f})"
        )
        move_api.Arc(*via[:4], *end[:4])
        move_api.Sync()
        viz.send(*end)
        time.sleep(0.2)

    go_home(move_api)
    time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description="MG400 motion modes comparison")
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
        print("Watch the viz window: XY (left) and XZ (right) traces differ per mode.")

        demo_movj(move_api)
        demo_movl(move_api)
        demo_arc(move_api, viz)

        print("\nMotion modes comparison complete.")
        print("See mg400/utils_mg400.py for MovJ/MovL/Arc/Circle API reference.")

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
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
