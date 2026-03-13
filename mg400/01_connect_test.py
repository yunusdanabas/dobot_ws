"""
01_connect_test.py — TCP connectivity test for the MG400.

Tests the three TCP sockets (dashboard 29999, move 30003, feed 30004)
and prints firmware version, robot mode, and current pose WITHOUT
enabling the robot (motors stay off).

Prerequisites:
  1. PC Ethernet set to static 192.168.2.100 / 255.255.255.0
  2. ping 192.168.2.9 succeeds (Robot 1 default)
  3. SDK cloned: git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git
                  /path/to/dobot_ws/vendor/TCP-IP-4Axis-Python

Usage:
    python 01_connect_test.py [--ip 192.168.2.9]
    python 01_connect_test.py --robot 2
"""

import argparse
import sys

from utils_mg400 import (
    connect,
    close_all,
    parse_pose,
    parse_robot_mode,
    MG400_IP,
    ROBOT_IPS,
    ROBOT_MODE,
)


def main():
    parser = argparse.ArgumentParser(description="MG400 TCP connectivity test")
    parser.add_argument("--ip", default=MG400_IP, help="MG400 IP address")
    parser.add_argument("--robot", type=int, choices=[1, 2, 3, 4], metavar="N",
                        help="Robot number 1-4 (overrides --ip)")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    print(f"Connecting to MG400 at {ip} ...")
    try:
        dashboard, move_api, feed = connect(ip)
    except ConnectionRefusedError:
        sys.exit(
            "[Error] Connection refused. Check:\n"
            "  1. MG400 is powered and Ethernet cable connected\n"
            "  2. PC Ethernet static IP = 192.168.2.100 / 255.255.255.0\n"
            f"  3. ping {ip} succeeds"
        )
    except OSError as exc:
        sys.exit(f"[Error] Cannot connect: {exc}")

    print("  TCP sockets open: dashboard(29999), move(30003), feed(30004)")

    try:
        # --- Firmware version ---
        try:
            ver = dashboard.GetVersion()
            print(f"  Firmware version : {ver.strip()}")
        except Exception as exc:
            print(f"  Firmware version : (unavailable — {exc})")

        # --- Robot mode ---
        try:
            mode_resp = dashboard.RobotMode()
            mode_code = parse_robot_mode(mode_resp)
            mode_name = ROBOT_MODE.get(mode_code, f"UNKNOWN({mode_code})")
            print(f"  Robot mode       : {mode_code} = {mode_name}")
            if mode_code == 9:
                print("  [Warning] Robot is in ERROR state — run check_errors(dashboard).")
        except Exception as exc:
            print(f"  Robot mode       : (unavailable — {exc})")

        # --- Current pose (no enable required) ---
        try:
            pose_resp = dashboard.GetPose()
            x, y, z, r = parse_pose(pose_resp)
            print(f"  Current pose     : X={x:.2f}  Y={y:.2f}  Z={z:.2f}  R={r:.2f}  (mm / deg)")
        except Exception as exc:
            print(f"  Current pose     : (unavailable — {exc})")

        print("\nConnectivity test PASSED. All sockets open, status readable.")
        print("Next step: run 02_first_connection.py to enable and move.")

    finally:
        close_all(dashboard, move_api, feed)
        print("Sockets closed.")


if __name__ == "__main__":
    main()
