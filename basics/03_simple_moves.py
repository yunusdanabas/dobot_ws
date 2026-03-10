"""
03_simple_moves.py
Run a few small safe Cartesian moves.
"""

import sys
import time
from pathlib import Path

from pydobotplus import Dobot

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.utils import SAFE_READY_POSE, find_port, prepare_robot, safe_move


def main() -> None:
    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Run basics/01_connect_and_pose.py first.")

    bot = Dobot(port=port)
    print(f"Connected on {port}")
    try:
        prepare_robot(bot)

        x0, y0, z0, r0 = SAFE_READY_POSE
        moves = [
            ("Ready", x0, y0, z0, r0),
            ("X +10", x0 + 10, y0, z0, r0),
            ("Y +10", x0 + 10, y0 + 10, z0, r0),
            ("Z +10", x0 + 10, y0 + 10, z0 + 10, r0),
            ("Back", x0, y0, z0, r0),
        ]

        for label, x, y, z, r in moves:
            print(f"{label:>6}: ({x:.0f}, {y:.0f}, {z:.0f}, {r:.0f})")
            safe_move(bot, x, y, z, r)
            time.sleep(0.25)
    finally:
        bot.close()


if __name__ == "__main__":
    main()
