"""
03_slider_arm_demo.py — Coordinated arm + sliding rail motion via SyncAll().

Demonstrates how to queue a slider move (MovJExt) and an arm move (MovJ)
together, then use SyncAll() to wait for BOTH queues to finish before
proceeding to the next waypoint.

SyncAll() vs Sync():
  - move_api.Sync()    — waits for the ARM queue only
  - move_api.SyncAll() — waits for BOTH the arm queue AND the slider queue
  Use SyncAll() whenever a step moves both the arm and the rail simultaneously.
  Use Sync() when moving only the arm or only the rail.

Coordinated waypoints (slider_mm, arm_x, arm_y, arm_z, arm_r):
  At each waypoint the slider and arm commands are queued back-to-back;
  SyncAll() blocks until both finish before moving on.

Prerequisites:
  - DobotStudio Pro: Configure → External Axis → Linear → mm → reboot (one-time)
  - ping 192.168.2.10 succeeds

Usage:
    python 03_slider_arm_demo.py
    python 03_slider_arm_demo.py --robot 3 --viz
    python 03_slider_arm_demo.py --ip 192.168.2.10 --viz
"""

import argparse

from utils_slider import (
    connect,
    close_all,
    check_errors,
    go_home,
    go_home_slider,
    safe_move,
    safe_move_ext,
    print_slider_status,
    SLIDER_IP,
    ROBOT_IPS,
    SPEED_DEFAULT,
)

# ---------------------------------------------------------------------------
# Coordinated waypoints
# Each row: (slider_mm, arm_x, arm_y, arm_z, arm_r)
# ---------------------------------------------------------------------------
COORD_WAYPOINTS = [
    (  0.0, 300,  0, 50, 0),
    (200.0, 300,  0, 50, 0),
    (400.0, 250,  0, 60, 0),
    (600.0, 200,  0, 70, 0),
    (800.0, 300,  0, 50, 0),
]


def main():
    parser = argparse.ArgumentParser(description="MG400 coordinated arm + slider demo")
    parser.add_argument("--ip", default=SLIDER_IP, help="MG400 IP address")
    parser.add_argument("--robot", type=int, default=2, choices=[1, 2, 3, 4],
                        metavar="N", help="Robot number 1-4 (overrides --ip)")
    parser.add_argument("--viz", action="store_true", help="Enable visualizer")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    # Import viz here so scripts without --viz don't need PyQt5 installed
    from viz_mg400 import RobotViz  # noqa: F401 (imported for side-effect-free viz)
    viz = RobotViz(enabled=args.viz)

    print(f"Connecting to MG400 (slider) at {ip} ...")
    dashboard, move_api, feed = connect(ip)
    print("  Connected.")

    try:
        check_errors(dashboard)
        dashboard.EnableRobot()
        dashboard.SpeedFactor(SPEED_DEFAULT)
        print(f"  Robot enabled. Speed factor = {SPEED_DEFAULT}%\n")

        viz.attach(move_api)

        # Home arm and slider before coordinated motion
        print("[Setup] Homing arm ...")
        go_home(move_api)
        print("[Setup] Homing slider ...")
        go_home_slider(move_api)
        print()

        # --- Coordinated waypoints ---
        # Pattern for each step:
        #   1. Queue the slider move  (safe_move_ext — no sync)
        #   2. Queue the arm move     (safe_move     — no sync)
        #   3. SyncAll()              — wait for BOTH queues to finish
        #
        # Both commands are queued before either executes, so the hardware
        # starts them simultaneously and the robot handles coordination.
        print(f"Running {len(COORD_WAYPOINTS)} coordinated waypoints ...")
        for i, (slider_mm, ax, ay, az, ar) in enumerate(COORD_WAYPOINTS, start=1):
            print(f"  [{i}/{len(COORD_WAYPOINTS)}] "
                  f"Slider={slider_mm:.0f} mm  Arm=({ax},{ay},{az},{ar})")

            # Queue both moves (neither blocks; hardware starts simultaneously)
            safe_move_ext(move_api, slider_mm, sync=False)
            safe_move(move_api, ax, ay, az, ar)

            # SyncAll: wait for arm queue AND slider queue to finish
            move_api.SyncAll()
            print_slider_status(f"step {i}")

        print("\nCoordinated demo complete.")

    finally:
        try:
            viz.close()
        except Exception:
            pass
        try:
            dashboard.DisableRobot()
        except Exception:
            pass
        close_all(dashboard, move_api, feed)
        print("Connections closed.")


if __name__ == "__main__":
    main()
