"""
08_pick_and_place.py — Pick-and-place template using the suction cup.

Approach pattern: move to Z+LIFT above the target, descend, actuate,
ascend, traverse, descend, release, ascend.

Edit PICK and PLACE constants to match your physical setup.

Usage:
    python 08_pick_and_place.py [--no-viz]
"""

import argparse
import sys
import time
from pydobotplus import Dobot
from pydobotplus.dobotplus import MODE_PTP
from utils import find_port, safe_move, go_home, prepare_robot, SAFE_BOUNDS, JUMP_HEIGHT, SPEED_SMOOTH
from viz import RobotViz

# ---------------------------------------------------------------------------
# User configuration — set these to match your table layout (mm)
# ---------------------------------------------------------------------------
PICK_X,  PICK_Y,  PICK_Z  = 220, -60, 30   # object pick position
PLACE_X, PLACE_Y, PLACE_Z = 220,  60, 30   # object place position
LIFT      = 60    # mm above pick/place Z for safe travel
R         = 0     # end-effector rotation (deg), usually 0

# ---------------------------------------------------------------------------
# Safety check — warn if coordinates are outside safe bounds
# ---------------------------------------------------------------------------
def _check(label, x, y, z):
    issues = []
    if not (SAFE_BOUNDS["x"][0] <= x <= SAFE_BOUNDS["x"][1]):
        issues.append(f"X={x} outside {SAFE_BOUNDS['x']}")
    if not (SAFE_BOUNDS["y"][0] <= y <= SAFE_BOUNDS["y"][1]):
        issues.append(f"Y={y} outside {SAFE_BOUNDS['y']}")
    if not (SAFE_BOUNDS["z"][0] <= z <= SAFE_BOUNDS["z"][1]):
        issues.append(f"Z={z} outside {SAFE_BOUNDS['z']}")
    if issues:
        print(f"[Warning] {label}: {', '.join(issues)}")

# ---------------------------------------------------------------------------
# Motion primitives
# ---------------------------------------------------------------------------
def pick_up(bot):
    """Approach from above, pick with suction, retract.

    Simpler alternative — let the firmware handle the lift automatically:
        from pydobotplus import MODE_PTP
        bot._set_ptp_jump_params(jump=30, limit=120)  # once at startup
        bot.move_to(PICK_X,  PICK_Y,  PICK_Z,  R, mode=MODE_PTP.JUMP_XYZ)
        bot.suck(True)
        bot.move_to(PLACE_X, PLACE_Y, PLACE_Z, R, mode=MODE_PTP.JUMP_XYZ)
        bot.suck(False)
    See scripts/12_motion_modes.py for a live demo.
    """
    print("  Approach pick ...")
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R)

    print("  Descend to pick ...")
    safe_move(bot, PICK_X, PICK_Y, PICK_Z, R)

    print("  Suction ON ...")
    bot.suck(True)
    time.sleep(0.4)   # let vacuum build

    print("  Lift ...")
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R)


def place_down(bot):
    """Move to place position, descend, release, retract."""
    print("  Approach place ...")
    safe_move(bot, PLACE_X, PLACE_Y, PLACE_Z + LIFT, R)

    print("  Descend to place ...")
    safe_move(bot, PLACE_X, PLACE_Y, PLACE_Z, R)

    print("  Suction OFF ...")
    bot.suck(False)
    time.sleep(0.3)

    print("  Lift ...")
    safe_move(bot, PLACE_X, PLACE_Y, PLACE_Z + LIFT, R)


# ---------------------------------------------------------------------------
# Main sequence
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Pick-and-place template")
    parser.add_argument("--no-viz", action="store_true", help="Disable real-time visualization")
    args = parser.parse_args()

    PORT = find_port()
    if PORT is None:
        sys.exit("[Error] No serial port found. Run 01_find_port.py first.")

    bot = Dobot(port=PORT)
    viz = RobotViz(enabled=not args.no_viz)
    viz.attach(bot)
    print(f"Connected on {PORT}\n")

    try:
        prepare_robot(bot)
        bot.speed(*SPEED_SMOOTH)
        _check("PICK", PICK_X, PICK_Y, PICK_Z)
        _check("PICK_APPROACH", PICK_X, PICK_Y, PICK_Z + LIFT)
        _check("PLACE", PLACE_X, PLACE_Y, PLACE_Z)
        _check("PLACE_APPROACH", PLACE_X, PLACE_Y, PLACE_Z + LIFT)

        print("Going home ...")
        go_home(bot)
        time.sleep(0.5)

        print("\n--- PICK ---")
        pick_up(bot)

        print("\n--- PLACE ---")
        bot._set_ptp_jump_params(jump=JUMP_HEIGHT, limit=120)
        safe_move(bot, PLACE_X, PLACE_Y, PLACE_Z + LIFT, R, mode=MODE_PTP.JUMP_XYZ)
        place_down(bot)

        print("\nReturning home ...")
        go_home(bot)

        print("\nPick-and-place complete.")
    finally:
        try:
            # Explicitly de-assert suction on all exit paths.
            bot.suck(False)
        except Exception:
            pass
        viz.close()
        bot.close()


if __name__ == "__main__":
    main()
