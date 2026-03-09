"""
05_end_effectors.py — Control suction cup and gripper end-effectors.

Make sure you know which end-effector is physically attached before running.
Only ONE should be attached at a time.

Usage:
    python 05_end_effectors.py
"""

import sys
import time
from pydobotplus import Dobot
from utils import find_port, go_home


def main():
    PORT = find_port()
    if PORT is None:
        sys.exit("[Error] No serial port found.")

    bot = Dobot(port=PORT)
    print(f"Connected on {PORT}\n")
    suction_on = False

    try:
        go_home(bot)
        time.sleep(0.5)

        # -------------------------------------------------------------------
        # Choose which end-effector is attached:
        # -------------------------------------------------------------------
        EFFECTOR = "suction"   # "suction" | "gripper"

        if EFFECTOR == "suction":
            # --- Suction cup cycle ---
            print("Suction ON  (picking up) ...")
            bot.suck(True)
            suction_on = True
            time.sleep(5.0)          # hold for 2 s

            print("Suction OFF (releasing) ...")
            bot.suck(False)
            suction_on = False
            time.sleep(1.0)

            # dobot-python (Interface):
            #   bot.set_end_effector_suction_cup(enable_control=True, enable_suction=True, queue=True)
            #   bot.set_end_effector_suction_cup(enable_control=True, enable_suction=False, queue=True)
            # pydobot original: bot.suck(True/False)

        elif EFFECTOR == "gripper":
            # --- Gripper cycle ---
            print("Gripper CLOSE ...")
            bot.grip(True)
            time.sleep(1.5)

            print("Gripper OPEN ...")
            bot.grip(False)
            time.sleep(1.0)

            # dobot-python (Interface):
            #   bot.set_end_effector_gripper(enable_control=True, enable_grip=True, queue=True)
            #   bot.set_end_effector_gripper(enable_control=True, enable_grip=False, queue=True)
            # pydobot original also uses bot.grip(True/False)

        else:
            print(f"[Error] Unknown EFFECTOR='{EFFECTOR}'. Set to 'suction' or 'gripper'.")

        print("\nEnd-effector demo complete.")
    finally:
        if suction_on:
            try:
                bot.suck(False)
            except Exception:
                pass
        bot.close()


if __name__ == "__main__":
    main()
