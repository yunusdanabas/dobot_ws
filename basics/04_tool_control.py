"""
04_tool_control.py
Simple suction/gripper control demo.
"""

import sys
import time
from pathlib import Path

from pydobotplus import Dobot

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.utils import find_port, prepare_robot

TOOL = "suction"  # "suction" or "gripper"
HOLD_SECONDS = 1.5


def main() -> None:
    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Run basics/01_connect_and_pose.py first.")

    bot = Dobot(port=port)
    print(f"Connected on {port}")
    suction_on = False
    gripper_closed = False

    try:
        prepare_robot(bot)

        if TOOL == "suction":
            if not hasattr(bot, "suck"):
                print("[Note] This library build does not expose suction control.")
                return
            print("Suction ON")
            bot.suck(True)
            suction_on = True
            time.sleep(HOLD_SECONDS)
            print("Suction OFF")
            bot.suck(False)
            suction_on = False

        elif TOOL == "gripper":
            if not hasattr(bot, "grip"):
                print("[Note] This library build does not expose gripper control.")
                return
            print("Gripper CLOSE")
            bot.grip(True)
            gripper_closed = True
            time.sleep(HOLD_SECONDS)
            print("Gripper OPEN")
            bot.grip(False)
            gripper_closed = False

        else:
            print(f"[Error] Unknown TOOL='{TOOL}'. Use 'suction' or 'gripper'.")
            return

        print("Tool demo complete.")
    except Exception as exc:
        print(f"[Note] Tool command failed: {exc}")
        print("If no tool hardware is attached, this is expected.")
    finally:
        if suction_on:
            try:
                bot.suck(False)
            except Exception:
                pass
        if gripper_closed:
            try:
                bot.grip(False)
            except Exception:
                pass
        bot.close()


if __name__ == "__main__":
    main()
