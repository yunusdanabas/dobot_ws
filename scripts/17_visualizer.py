"""
17_visualizer.py — Live pose monitor with real-time 2D/3D visualization.

Connects to the robot, opens the visualizer window, then polls and prints
the end-effector pose at 2 Hz — same table format as 06_joint_angles.py.

This script serves two purposes:
  1. Standalone demo — proves the viz window works before adding it to a
     motion script.
  2. Live monitor — run this in one terminal while another terminal runs
     a motion script (or DobotStudio); it shows the robot's position in
     real time without sending any move commands.

Note: Only one process can own the serial port.  Close this script before
running another script that connects to the robot, and vice versa.

Usage:
    python 17_visualizer.py [--no-viz]
    Press Ctrl+C to stop.
"""

import argparse
import sys
import time

from pydobotplus import Dobot

from utils import find_port, unpack_pose
from viz import RobotViz

INTERVAL = 0.5  # seconds between readings (2 Hz)


def main():
    parser = argparse.ArgumentParser(description="Live pose monitor with visualization")
    parser.add_argument("--no-viz", action="store_true", help="Disable real-time visualization")
    args = parser.parse_args()

    PORT = find_port()
    if PORT is None:
        sys.exit("[Error] No serial port found. Run 01_find_port.py first.")

    bot = Dobot(port=PORT)
    viz = RobotViz(enabled=not args.no_viz)
    viz.attach(bot)  # patches move_to; also use viz.send() for polled poses

    try:
        print(f"Connected on {PORT}")
        print("Visualizer window opened. Press Ctrl+C to stop.\n")

        print(f"{'Time':>6}  {'X':>7} {'Y':>7} {'Z':>7} {'R':>7}  "
              f"{'J1':>7} {'J2':>7} {'J3':>7} {'J4':>7}")
        print("-" * 70)

        t0 = time.time()
        while True:
            x, y, z, r, j1, j2, j3, j4 = unpack_pose(bot.get_pose())
            elapsed = time.time() - t0
            print(f"{elapsed:6.1f}  "
                  f"{x:7.2f} {y:7.2f} {z:7.2f} {r:7.2f}  "
                  f"{j1:7.2f} {j2:7.2f} {j3:7.2f} {j4:7.2f}")
            viz.send(x, y, z, r)
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        viz.close()
        bot.close()


if __name__ == "__main__":
    main()
