"""
02_first_connection.py — Full connection: enable, query, move home, disable.

Steps:
  1. Connect (3 TCP sockets)
  2. Check for errors and clear them
  3. Enable robot (motors on)
  4. Read and print current Cartesian pose (GetPose)
  5. Read and print current joint angles (GetAngle)
  6. Move to READY_POSE (home)
  7. Disable robot and close connections

Usage:
    python 02_first_connection.py [--ip 192.168.2.9]
    python 02_first_connection.py --robot 2
"""

import argparse
import sys

from utils_mg400 import (
    connect,
    close_all,
    parse_pose,
    parse_angles,
    check_errors,
    go_home,
    SPEED_DEFAULT,
    MG400_IP,
    ROBOT_IPS,
)


def main():
    parser = argparse.ArgumentParser(description="MG400 first connection demo")
    parser.add_argument("--ip", default=MG400_IP, help="MG400 IP address")
    parser.add_argument("--robot", type=int, choices=[1, 2, 3, 4], metavar="N",
                        help="Robot number 1-4 (overrides --ip)")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    print(f"Connecting to MG400 at {ip} ...")
    dashboard, move_api, feed = connect(ip)
    print("  Connected: dashboard(29999), move(30003), feed(30004)")

    try:
        # 1. Clear any existing errors before enabling
        check_errors(dashboard)

        # 2. Enable robot (motors on — arm may move slightly to brake-release)
        print("Enabling robot ...")
        dashboard.EnableRobot()
        print("  Robot enabled.")

        # 3. Set conservative speed
        dashboard.SpeedFactor(SPEED_DEFAULT)
        print(f"  Speed factor set to {SPEED_DEFAULT}%")

        # 4. Read Cartesian pose
        pose_resp = dashboard.GetPose()
        x, y, z, r = parse_pose(pose_resp)
        print(f"\nCurrent Cartesian pose:")
        print(f"  X={x:.2f} mm  Y={y:.2f} mm  Z={z:.2f} mm  R={r:.2f} deg")

        # 5. Read joint angles
        angle_resp = dashboard.GetAngle()
        j1, j2, j3, j4 = parse_angles(angle_resp)
        print(f"\nCurrent joint angles:")
        print(f"  J1={j1:.2f}°  J2={j2:.2f}°  J3={j3:.2f}°  J4={j4:.2f}°")

        # 6. Move to home (READY_POSE)
        print("\nMoving to READY_POSE (home) ...")
        go_home(move_api)

        # 7. Read pose again to confirm arrival
        pose_resp2 = dashboard.GetPose()
        xh, yh, zh, rh = parse_pose(pose_resp2)
        print(f"  Arrived at: X={xh:.2f}  Y={yh:.2f}  Z={zh:.2f}  R={rh:.2f}")

        print("\nFirst connection demo complete.")

    finally:
        print("Disabling robot and closing connections ...")
        try:
            dashboard.DisableRobot()
        except Exception:
            pass
        close_all(dashboard, move_api, feed)
        print("Done.")


if __name__ == "__main__":
    main()
