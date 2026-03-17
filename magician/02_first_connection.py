"""
02_first_connection.py — Connect to the Dobot and read the current pose.

Demonstrates all three library APIs side-by-side.
Uncomment the track that matches your installed library.

Usage:
    python 02_first_connection.py
"""

import sys
from utils import find_port, unpack_pose


def main():
    PORT = find_port()          # auto-detect; override with e.g. PORT = "COM3" or "/dev/ttyUSB0"

    if PORT is None:
        sys.exit("[Error] No serial port found. Run 01_find_port.py first.")

    print(f"Connecting on {PORT} ...\n")

    # ===================================================================
    # TRACK A — pydobotplus  (pip install pydobotplus)   ← DEFAULT
    # ===================================================================
    from pydobotplus import Dobot

    bot = Dobot(port=PORT)
    try:
        x, y, z, r, j1, j2, j3, j4 = unpack_pose(bot.get_pose())
        # pydobotplus returns Pose(position=..., joints=...).
        # unpack_pose() normalizes it to:
        #   (x, y, z, r, j1, j2, j3, j4)

        print("=== Current Pose (pydobotplus) ===")
        print(f"  Cartesian : X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}  mm/deg")
        print(f"  Joints    : J1={j1:.1f}  J2={j2:.1f}  J3={j3:.1f}  J4={j4:.1f}  deg")
    finally:
        bot.close()

    # ===================================================================
    # TRACK B — dobot-python (AlexGustafsson source checkout)
    # ===================================================================
    # import sys
    # sys.path.insert(0, "/absolute/path/to/dobot-python")
    # from lib.dobot import Dobot
    #
    # bot = Dobot(PORT)
    # try:
    #     x, y, z, r, j1, j2, j3, j4 = unpack_pose(bot.get_pose())
    #     print(f"X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}")
    # finally:
    #     # Upstream Dobot class has no bot.close(); close serial explicitly.
    #     bot.serial.close()

    # ===================================================================
    # TRACK C — pydobot (original)  (pip install pydobot)
    # ===================================================================
    # from pydobot import Dobot
    #
    # bot = Dobot(port=PORT, verbose=False)
    # try:
    #     (x, y, z, r, j1, j2, j3, j4) = bot.pose()
    #     print(f"X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}")
    # finally:
    #     bot.close()


if __name__ == "__main__":
    main()
