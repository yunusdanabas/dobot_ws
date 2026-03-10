"""
09_arc_motion.py — Arc, Circle, and sampled-circle motion demos.

The MG400 has native arc and circle commands:
  move_api.Arc(via_x,via_y,via_z,via_r, end_x,end_y,end_z,end_r)
      → moves along an arc defined by a via-point and endpoint.

  move_api.Circle(via_x,via_y,via_z,via_r, end_x,end_y,end_z,end_r, count)
      → completes `count` full circles (via and end define the circle plane).

Three demos:
  1. Arc()    — 90° arc in XY plane
  2. Circle() — one full circle in XY plane
  3. Sampled  — circle drawn via safe_move() loop (N discrete waypoints)

Viz integration: attach to move_api so all MovJ/MovL calls auto-forward.
For Arc/Circle the final endpoint is sent manually via viz.send().

Usage:
    python 09_arc_motion.py [--ip 192.168.1.6] [--no-viz]
"""

import argparse
import math
import time

from utils_mg400 import (
    connect,
    close_all,
    check_errors,
    go_home,
    safe_move,
    SPEED_DEFAULT,
    MG400_IP,
)
from viz_mg400 import RobotViz


# ---------------------------------------------------------------------------
# Circle parameters — centred at (CX, CY, CZ)
# ---------------------------------------------------------------------------
CX, CY, CZ = 280, 0, 60   # circle centre (mm)
RADIUS = 60                # circle radius (mm)
R_EFF  = 0                 # end-effector rotation (deg)


def _circle_point(angle_deg: float) -> tuple[float, float, float, float]:
    """Return (x, y, z, r) on circle at given angle (degrees)."""
    rad = math.radians(angle_deg)
    return CX + RADIUS * math.cos(rad), CY + RADIUS * math.sin(rad), CZ, R_EFF


def draw_circle_sampled(move_api, viz, steps: int = 36) -> None:
    """Draw a circle by moving to N evenly-spaced sample points."""
    print(f"  Drawing {steps}-point sampled circle: centre=({CX},{CY},{CZ}) r={RADIUS} mm")
    for i in range(steps + 1):
        angle = 360.0 * i / steps
        x, y, z, r = _circle_point(angle)
        safe_move(move_api, x, y, z, r, mode="L")
        move_api.Sync()
        viz.send(x, y, z, r)
        if i % 12 == 0:
            print(f"    [{i:3d}/{steps}] angle={angle:.0f}°  ({x:.1f}, {y:.1f})")


def main():
    parser = argparse.ArgumentParser(description="MG400 arc/circle motion demo")
    parser.add_argument("--ip", default=MG400_IP, help="MG400 IP address")
    parser.add_argument("--no-viz", action="store_true", help="Disable visualizer")
    args = parser.parse_args()

    dashboard, move_api, feed = connect(args.ip)
    viz = RobotViz(enabled=not args.no_viz)
    viz.attach(move_api)

    try:
        check_errors(dashboard)
        dashboard.EnableRobot()
        dashboard.SpeedFactor(SPEED_DEFAULT)
        print(f"Connected, enabled, speed = {SPEED_DEFAULT}%\n")

        go_home(move_api)
        time.sleep(0.5)

        # ---- Demo 1: Arc() — 90° arc (0° → 90° around circle) ---------------
        print("[Demo 1] Arc() — 90° arc in XY plane")
        start = _circle_point(0)    # 0°  — arc start
        via   = _circle_point(45)   # 45° — midpoint (via-point)
        end   = _circle_point(90)   # 90° — arc end

        print(f"  Start : ({start[0]:.1f}, {start[1]:.1f})")
        print(f"  Via   : ({via[0]:.1f},   {via[1]:.1f})")
        print(f"  End   : ({end[0]:.1f},   {end[1]:.1f})")

        # Move to arc start
        safe_move(move_api, *start, mode="J")
        move_api.Sync()
        # Execute arc
        move_api.Arc(*via[:4], *end[:4])
        move_api.Sync()
        viz.send(*end)
        print("  Arc complete.")
        time.sleep(0.5)

        # ---- Demo 2: Circle() — one full circle -------------------------------
        print("\n[Demo 2] Circle() — one full circle in XY plane")
        # Circle() needs a via-point (90°) and an end-point (360°=0°).
        # They define the same point — the robot circles until count=1 completed.
        via_c = _circle_point(90)
        end_c = _circle_point(0)    # coincides with start to close the circle

        safe_move(move_api, *_circle_point(0), mode="J")
        move_api.Sync()

        print(f"  Via : ({via_c[0]:.1f}, {via_c[1]:.1f})")
        print(f"  End : ({end_c[0]:.1f}, {end_c[1]:.1f})  count=1")
        move_api.Circle(*via_c[:4], *end_c[:4], 1)
        move_api.Sync()
        viz.send(*end_c)
        print("  Full circle complete.")
        time.sleep(0.5)

        # ---- Demo 3: Sampled circle via safe_move() loop ----------------------
        print("\n[Demo 3] Sampled circle (36 safe_move() waypoints)")
        # Move to circle start first
        safe_move(move_api, *_circle_point(0), mode="J")
        move_api.Sync()
        draw_circle_sampled(move_api, viz, steps=36)
        print("  Sampled circle complete.")
        time.sleep(0.5)

        print("\nReturning to home ...")
        go_home(move_api)
        print("Arc motion demo complete.")

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
