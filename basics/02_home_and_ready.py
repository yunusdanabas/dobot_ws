"""
02_home_and_ready.py
Prepare robot, go home, then move to ready pose.
"""

import sys
from pathlib import Path

from pydobotplus import Dobot

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.utils import SAFE_READY_POSE, find_port, go_home, prepare_robot, safe_move


def main() -> None:
    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Run basics/01_connect_and_pose.py first.")

    bot = Dobot(port=port)
    print(f"Connected on {port}")
    try:
        prepare_robot(bot)
        go_home(bot)
        safe_move(bot, *SAFE_READY_POSE)
        print(f"Ready pose reached: {SAFE_READY_POSE}")
    finally:
        bot.close()


if __name__ == "__main__":
    main()
