#!/usr/bin/env python3
"""
Pose Recorder — Interactive coordinate capture for pick-and-place setup.

This recorder does not keep the serial port open while idle. Position the
robot using another tool, close that tool, then press Enter here to capture
the current pose. The recorder briefly connects, reads one pose, and closes
the port again so the workflow stays compatible with single-port ownership.

On Ctrl+C the recorded poses are written to poses.py in the current directory.

Usage:
    python scripts/15_record_pose.py

Output (poses.py):
    # Recorded poses — paste into your pick-and-place script
    POSE_1 = (220.3, -58.1, 31.4, 0.0)
    POSE_2 = (220.5,  60.8, 31.2, 0.0)
"""

import sys
from pydobotplus import Dobot
from utils import check_alarms, find_port, unpack_pose


def write_poses(poses: list, filename: str = "poses.py") -> None:
    """Write recorded poses to a Python file as named constants."""
    lines = ["# Recorded poses — paste into your pick-and-place script\n"]
    for i, (x, y, z, r) in enumerate(poses, 1):
        lines.append(f"POSE_{i} = ({x:.1f}, {y:.1f}, {z:.1f}, {r:.1f})\n")
    with open(filename, "w") as f:
        f.writelines(lines)
    print(f"\n[Done] {len(poses)} pose(s) written to {filename}")
    for i, (x, y, z, r) in enumerate(poses, 1):
        print(f"  POSE_{i} = ({x:.1f}, {y:.1f}, {z:.1f}, {r:.1f})")


def capture_pose(port: str) -> tuple[float, float, float, float, float, float, float, float]:
    """Open the robot connection briefly, read one pose, and close cleanly."""
    bot = Dobot(port=port)
    try:
        check_alarms(bot)
        return unpack_pose(bot.get_pose())
    finally:
        bot.close()


def main():
    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Run: python scripts/01_find_port.py")

    poses = []
    print("\n[Pose Recorder]")
    print("  1. Position the robot using 07_keyboard_teleop.py, DobotStudio, or by hand.")
    print("  2. Close that tool so this recorder can own the serial port.")
    print("  3. Press Enter here to capture the current pose.")
    print("  Press Ctrl+C to finish and write poses.py.\n")

    count = 0
    try:
        while True:
            try:
                input(
                    f"  Press Enter to capture pose {count + 1} "
                    "(Ctrl+C to finish): "
                )
            except EOFError:
                break

            try:
                x, y, z, r, j1, j2, j3, j4 = capture_pose(port)
            except Exception as exc:
                print(f"  [Error] Capture failed: {exc}")
                print("          Close any other tool using the serial port, then try again.")
                continue

            count += 1
            poses.append((x, y, z, r))
            print(f"  [{count}] x={x:.1f}  y={y:.1f}  z={z:.1f}  r={r:.1f}"
                  f"   j1={j1:.1f}  j2={j2:.1f}  j3={j3:.1f}  j4={j4:.1f}  -> saved")
    except KeyboardInterrupt:
        print()  # newline after ^C

    if poses:
        write_poses(poses)
    else:
        print("[Done] No poses recorded.")


if __name__ == "__main__":
    main()
