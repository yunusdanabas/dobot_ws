"""
01_slider_connect_test.py — TCP connectivity test for MG400 + sliding rail.

Tests the three TCP sockets (dashboard 29999, move 30003, feed 30004) and
prints firmware version, robot mode, and current arm pose WITHOUT enabling
the robot (motors stay off).

Notes:
  - Slider position is NOT readable via the API (no GetPoseExt command).
  - Call go_home_slider() once after enabling to establish a software reference.
  - Default target: Robot 2 (192.168.2.10) — the robot with the sliding rail.

Prerequisites:
  1. PC Ethernet set to static 192.168.2.100 / 255.255.255.0
  2. ping 192.168.2.10 succeeds
  3. SDK cloned: git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git
                 dobot_ws/vendor/TCP-IP-4Axis-Python
  4. DobotStudio Pro: Configure → External Axis → Linear → mm → reboot (one-time)

Usage:
    python 01_slider_connect_test.py
    python 01_slider_connect_test.py --robot 2
    python 01_slider_connect_test.py --ip 192.168.2.10
"""

import argparse
import sys

from utils_slider import (
    connect,
    close_all,
    parse_pose,
    parse_robot_mode,
    get_slider_pos,
    SLIDER_IP,
    ROBOT_IPS,
    ROBOT_MODE,
)


def main():
    parser = argparse.ArgumentParser(description="MG400 slider connectivity test")
    parser.add_argument("--ip", default=SLIDER_IP, help="MG400 IP address")
    parser.add_argument("--robot", type=int, default=2, choices=[1, 2, 3, 4],
                        metavar="N", help="Robot number 1-4 (overrides --ip)")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    print(f"Connecting to MG400 (slider) at {ip} ...")
    try:
        dashboard, move_api, feed = connect(ip)
    except ConnectionRefusedError:
        sys.exit(
            "[Error] Connection refused. Check:\n"
            "  1. MG400 is powered and Ethernet cable connected\n"
            "  2. PC Ethernet static IP = 192.168.2.100 / 255.255.255.0\n"
            f"  3. ping {ip} succeeds\n"
            "  4. DobotStudio Pro has External Axis configured (Linear, mm)"
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

        # --- Arm pose (no enable required) ---
        try:
            pose_resp = dashboard.GetPose()
            x, y, z, r = parse_pose(pose_resp)
            print(f"  Arm pose         : X={x:.2f}  Y={y:.2f}  Z={z:.2f}  R={r:.2f}  (mm / deg)")
        except Exception as exc:
            print(f"  Arm pose         : (unavailable — {exc})")

        # --- Slider position (software-tracked only) ---
        spos = get_slider_pos()
        if spos is None:
            print("  Slider position  : UNKNOWN (not homed)")
        else:
            print(f"  Slider position  : {spos:.1f} mm  (software-tracked)")

        print()
        print("Note: No GetPoseExt API — slider position is tracked in software.")
        print("      Call go_home_slider() after enabling to establish a reference.")
        print()
        print("Connectivity test PASSED. All sockets open, status readable.")
        print("Next step: run 02_slider_basic.py to home and traverse rail positions.")

    finally:
        close_all(dashboard, move_api, feed)
        print("Sockets closed.")


if __name__ == "__main__":
    main()
