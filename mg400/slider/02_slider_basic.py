"""
02_slider_basic.py — Home the sliding rail and traverse five waypoints.

Steps:
  1. Connect and enable
  2. Home arm (READY_POSE) and home slider (0 mm reference)
  3. Traverse slider through [0, 200, 400, 600, 800] mm, printing position each step
  4. Return slider to home (0 mm)
  5. Disable and close

Prerequisites:
  - DobotStudio Pro: Configure → External Axis → Linear → mm → reboot (one-time)
  - ping 192.168.2.10 succeeds

Usage:
    python 02_slider_basic.py
    python 02_slider_basic.py --robot 2
    python 02_slider_basic.py --ip 192.168.2.10
"""

import argparse
import time

from utils_slider import (
    connect,
    close_all,
    check_errors,
    go_home,
    go_home_slider,
    safe_move_ext,
    print_slider_status,
    SLIDER_IP,
    ROBOT_IPS,
    SPEED_DEFAULT,
)

# Rail waypoints to traverse (mm)
WAYPOINTS = [0.0, 200.0, 400.0, 600.0, 800.0]


def main():
    parser = argparse.ArgumentParser(description="MG400 slider basic traverse")
    parser.add_argument("--ip", default=SLIDER_IP, help="MG400 IP address")
    parser.add_argument("--robot", type=int, default=2, choices=[1, 2, 3, 4],
                        metavar="N", help="Robot number 1-4 (overrides --ip)")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    print(f"Connecting to MG400 (slider) at {ip} ...")
    dashboard, move_api, feed = connect(ip)
    print("  Connected.")

    try:
        check_errors(dashboard)
        dashboard.EnableRobot()
        dashboard.SpeedFactor(SPEED_DEFAULT)
        print(f"  Robot enabled. Speed factor = {SPEED_DEFAULT}%\n")

        # Home arm first so it is at a safe, known position
        print("[1/3] Homing arm to READY_POSE ...")
        go_home(move_api)

        # Home slider — establishes the software position reference
        print("\n[2/3] Homing slider to 0 mm ...")
        go_home_slider(move_api)
        print_slider_status("after home")

        # Traverse waypoints
        print(f"\n[3/3] Traversing waypoints: {WAYPOINTS} mm")
        for pos in WAYPOINTS:
            print(f"  Moving to {pos:.0f} mm ...")
            safe_move_ext(move_api, pos, sync=True)
            print_slider_status(f"{pos:.0f} mm")
            time.sleep(0.5)   # pause so motion is visible

        # Return home
        print("\nReturning slider to home (0 mm) ...")
        safe_move_ext(move_api, 0.0, sync=True)
        print_slider_status("final")

        print("\nBasic traverse complete.")

    finally:
        try:
            dashboard.DisableRobot()
        except Exception:
            pass
        close_all(dashboard, move_api, feed)
        print("Connections closed.")


if __name__ == "__main__":
    main()
