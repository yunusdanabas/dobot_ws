"""
01_connect_and_pose.py
Detect the Dobot port, connect, and print current pose.
"""

import sys
from pathlib import Path

from pydobotplus import Dobot

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.utils import find_port, unpack_pose


def main() -> None:
    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Check USB/power and try again.")

    print(f"Using port: {port}")
    bot = Dobot(port=port)
    try:
        x, y, z, r, j1, j2, j3, j4 = unpack_pose(bot.get_pose())
        print(f"Cartesian: X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}")
        print(f"Joints   : J1={j1:.1f}  J2={j2:.1f}  J3={j3:.1f}  J4={j4:.1f}")
    finally:
        bot.close()


if __name__ == "__main__":
    main()
