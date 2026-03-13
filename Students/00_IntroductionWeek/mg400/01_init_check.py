"""
01_init_check.py — Initialization check for DOBOT MG400.
Prepared by Yunus Emre Danabas for ME403.

Connects to the MG400 over Ethernet, enables the robot, checks for errors,
prints the current pose, moves to the safe ready position (300, 0, 50, 0),
and confirms the final pose.

Run this first to verify that your hardware and network setup are working.

Usage:
    python 01_init_check.py               # Robot 1 (192.168.2.9)
    python 01_init_check.py --robot 2     # Robot 2 (192.168.2.10)
    python 01_init_check.py --ip 192.168.2.9

Prerequisites:
  - PC Ethernet set to static IP 192.168.2.100 / 255.255.255.0
  - SDK cloned: git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git
      dobot_ws/vendor/TCP-IP-4Axis-Python
  - Verify network: ping 192.168.2.9
"""

import argparse
import sys
import time

from utils_mg400 import (
    check_errors,
    close_all,
    connect,
    go_home,
    MG400_IP,
    parse_angles,
    parse_pose,
    READY_POSE,
    ROBOT_IPS,
    safe_move,
    SPEED_DEFAULT,
)


def print_pose(label: str, x: float, y: float, z: float, r: float) -> None:
    """Print a labelled Cartesian row."""
    print(f"  {label}  X={x:8.2f}  Y={y:8.2f}  Z={z:8.2f}  R={r:7.2f}  mm/deg")


def print_joints(label: str, j1: float, j2: float, j3: float, j4: float) -> None:
    """Print a labelled joint-angle row."""
    print(f"  {label}  J1={j1:7.2f}  J2={j2:7.2f}  J3={j3:7.2f}  J4={j4:7.2f}  deg")


def main() -> None:
    parser = argparse.ArgumentParser(description="MG400 initialization check")
    parser.add_argument("--ip", default=MG400_IP, help="MG400 IP address")
    parser.add_argument("--robot", type=int, choices=[1, 2, 3, 4], metavar="N",
                        help="Robot number 1-4 (overrides --ip)")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    print(f"Connecting to MG400 at {ip} ...")

    dashboard = None
    move_api  = None
    try:
        dashboard, move_api = connect(ip)

        # Enable the robot
        dashboard.EnableRobot()
        time.sleep(1.5)

        # Clear any startup errors
        check_errors(dashboard)

        # Set a conservative speed for this demo
        dashboard.SpeedFactor(SPEED_DEFAULT)
        print(f"Speed factor set to {SPEED_DEFAULT}%")

        # Print starting pose
        x, y, z, r = parse_pose(dashboard.GetPose())
        j1, j2, j3, j4 = parse_angles(dashboard.GetAngle())
        print("\nStarting pose:")
        print_pose("Cartesian:", x, y, z, r)
        print_joints("Joints:   ", j1, j2, j3, j4)

        # [1/3] Move to safe ready pose
        print(f"\n[1/3] Moving to READY_POSE {READY_POSE} ...")
        go_home(move_api)

        # [2/3] Confirm via safe_move (demonstrates clamping safety layer)
        print(f"\n[2/3] Confirming position with safe_move ...")
        safe_move(move_api, *READY_POSE)
        move_api.Sync()

        # [3/3] Read back and print confirmed pose
        print("\n[3/3] Confirmed pose:")
        x, y, z, r = parse_pose(dashboard.GetPose())
        j1, j2, j3, j4 = parse_angles(dashboard.GetAngle())
        print_pose("Cartesian:", x, y, z, r)
        print_joints("Joints:   ", j1, j2, j3, j4)

        print("\n[OK] Initialization complete.")

    finally:
        if dashboard is not None:
            try:
                dashboard.DisableRobot()
            except Exception:
                pass
        if dashboard is not None and move_api is not None:
            close_all(dashboard, move_api)
        print("Connection closed.")


if __name__ == "__main__":
    main()
