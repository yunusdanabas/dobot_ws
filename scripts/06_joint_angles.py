"""
06_joint_angles.py — Continuously read and print Cartesian + joint angles.

Prints a live table at 2 Hz while the robot is stationary or moving.
Press Ctrl+C to stop.

Extension: set LOG_TO_CSV = True to write every reading to 'joint_log.csv'.
You can then plot the data in Excel, MATLAB, or matplotlib to visualise
how joint angles change over time — useful for understanding FK/IK.

Usage:
    python 06_joint_angles.py
"""

import csv
import sys
import time
from pydobotplus import Dobot
from utils import find_port, unpack_pose

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INTERVAL   = 0.5     # seconds between readings (2 Hz)
LOG_TO_CSV = False   # set True to save readings to joint_log.csv
CSV_FILE   = "joint_log.csv"


def main():
    PORT = find_port()
    if PORT is None:
        sys.exit("[Error] No serial port found.")

    bot = Dobot(port=PORT)
    csv_writer = None
    csv_fh = None

    try:
        print(f"Connected on {PORT}")

        if LOG_TO_CSV:
            csv_fh = open(CSV_FILE, "w", newline="")
            csv_writer = csv.writer(csv_fh)
            csv_writer.writerow(["time_s", "x", "y", "z", "r", "j1", "j2", "j3", "j4"])
            print(f"Logging to {CSV_FILE}")

        print(f"\n{'Time':>6}  {'X':>7} {'Y':>7} {'Z':>7} {'R':>7}  "
              f"{'J1':>7} {'J2':>7} {'J3':>7} {'J4':>7}")
        print("-" * 70)

        t0 = time.time()
        while True:
            x, y, z, r, j1, j2, j3, j4 = unpack_pose(bot.get_pose())
            elapsed = time.time() - t0
            print(f"{elapsed:6.1f}  "
                  f"{x:7.2f} {y:7.2f} {z:7.2f} {r:7.2f}  "
                  f"{j1:7.2f} {j2:7.2f} {j3:7.2f} {j4:7.2f}")

            if csv_writer:
                csv_writer.writerow(
                    [f"{elapsed:.2f}"]
                    + [f"{v:.2f}" for v in (x, y, z, r, j1, j2, j3, j4)]
                )

            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        if csv_fh:
            csv_fh.close()
            print(f"Saved {CSV_FILE}")
        bot.close()

    # -----------------------------------------------------------------------
    # dobot-python equivalent (lib.interface.Interface):
    #   pose = bot.get_pose()  # already flat: (x, y, z, r, j1, j2, j3, j4)
    #
    # pydobot (original) equivalent:
    #   (x, y, z, r, j1, j2, j3, j4) = bot.pose()
    # -----------------------------------------------------------------------


if __name__ == "__main__":
    main()
