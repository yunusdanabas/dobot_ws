"""
01_init_check.py — Initialization check for Dobot Magician.

Discovers the Dobot serial port, connects, prints the current pose, moves to
joint home, then moves to the safe ready pose (200, 0, 100, 0) and prints the
confirmed position and joint angles.

Run this first to verify that your hardware and software setup is working.

Usage:
    python 01_init_check.py
"""
# Prepared by Yunus Emre Danabas for ME403

import sys

from pydobotplus import Dobot

from utils import (
    SAFE_READY_POSE,
    find_port,
    go_home,
    prepare_robot,
    safe_move,
    unpack_pose,
)


def print_pose(label: str, pose_8: tuple) -> None:
    """Print Cartesian coordinates and joint angles from an 8-tuple."""
    x, y, z, r, j1, j2, j3, j4 = pose_8
    print(f"  Cartesian : X={x:7.2f}  Y={y:7.2f}  Z={z:7.2f}  R={r:6.2f}  mm/deg")
    print(f"  Joints    : J1={j1:6.2f}  J2={j2:6.2f}  J3={j3:6.2f}  J4={j4:6.2f}  deg")


def main() -> None:
    # --- Port discovery ---
    port = find_port()
    if port is None:
        print("[Error] No serial port found.")
        print("  Check: USB cable connected, wall adapter plugged in,")
        print("  DobotStudio closed, dialout group on Linux (re-login required).")
        print("  For more detail run: python ../../magician/01_find_port.py")
        sys.exit(1)

    print(f"Connecting on {port} ...")

    # bot=None so the finally block is safe even if the constructor raises
    bot = None
    try:
        bot = Dobot(port=port)

        # Clear any active alarms; run homing if LIMIT alarms are present
        prepare_robot(bot)

        # Print starting pose
        print("\nStarting pose:")
        print_pose("", unpack_pose(bot.get_pose()))

        # [1/3] Move to joint home (all joints zero)
        print("\n[1/3] Moving to joint home (0, 0, 0, 0) ...")
        go_home(bot)

        # [2/3] Move to safe Cartesian ready pose
        print(f"\n[2/3] Moving to safe ready pose {SAFE_READY_POSE} ...")
        safe_move(bot, *SAFE_READY_POSE)

        # [3/3] Read back and confirm
        print("\n[3/3] Confirmed pose:")
        print_pose("", unpack_pose(bot.get_pose()))

        print("\n[OK] Initialization complete.")

    finally:
        if bot is not None:
            bot.close()
        print("Connection closed.")


if __name__ == "__main__":
    main()
