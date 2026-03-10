"""
04_speed_control.py — Demonstrate speed and acceleration control.

Moves between two points at 25 %, 50 %, and 100 % of the safe speed ceiling.
Watch the robot physically slow down and speed up between passes.

Extension: each pass is timed so you can compare the *commanded* speed with
the *wall-clock* speed the robot actually achieves.  The difference comes from
acceleration/deceleration ramps and firmware scheduling.

Usage:
    python 04_speed_control.py
"""

import sys
import time
from pydobotplus import Dobot
from utils import find_port, safe_move, go_home, SAFE_READY_POSE, SAFE_VELOCITY, SAFE_ACCELERATION

# ---------------------------------------------------------------------------
# Safe speed ceiling (do not exceed without supervision)
# ---------------------------------------------------------------------------
MAX_VELOCITY     = SAFE_VELOCITY       # 100 mm/s
MAX_ACCELERATION = SAFE_ACCELERATION   # 80  mm/s²


def main():
    PORT = find_port()
    if PORT is None:
        sys.exit("[Error] No serial port found.")

    bot = Dobot(port=PORT)
    print(f"Connected on {PORT}\n")

    try:
        X0, Y0, Z0, R0 = SAFE_READY_POSE
        OFFSET = 40   # mm swing distance (round-trip = 2 × OFFSET)

        def run_at_speed(pct: int) -> None:
            vel = MAX_VELOCITY     * pct / 100
            acc = MAX_ACCELERATION * pct / 100
            bot.speed(vel, acc)
            print(f"  Speed {pct:3d}% → vel={vel:.0f} mm/s  acc={acc:.0f} mm/s²")

            t_start = time.time()
            safe_move(bot, X0,          Y0, Z0, R0)
            safe_move(bot, X0 + OFFSET, Y0, Z0, R0)
            safe_move(bot, X0,          Y0, Z0, R0)
            elapsed = time.time() - t_start

            # Total travel = 2 × OFFSET (out and back)
            total_mm = 2 * OFFSET
            achieved = total_mm / elapsed if elapsed > 0 else 0
            print(f"           Wall time: {elapsed:.2f}s  "
                  f"≈ {achieved:.0f} mm/s achieved  "
                  f"(commanded {vel:.0f} mm/s)")

        print("Moving to home ...")
        go_home(bot)
        bot.speed(MAX_VELOCITY, MAX_ACCELERATION)
        safe_move(bot, *SAFE_READY_POSE)
        time.sleep(0.5)

        for pct in (25, 50, 100):
            run_at_speed(pct)
            time.sleep(0.3)

        print("\nSpeed demo complete.")
    finally:
        bot.speed(SAFE_VELOCITY, SAFE_ACCELERATION)
        bot.close()

    # -----------------------------------------------------------------------
    # dobot-python (upstream) equivalent with lib.interface.Interface:
    #   bot.set_point_to_point_coordinate_params(vel, vel, acc, acc, queue=True)
    #   bot.set_point_to_point_common_params(vel, acc, queue=True)
    #   last_idx = bot.set_point_to_point_command(3, x, y, z, r, queue=True)
    #   while bot.get_current_queue_index() < last_idx:
    #       time.sleep(0.05)
    #
    # pydobot (original) equivalent:
    #   bot.speed(vel, acc)                         # same positional signature
    # -----------------------------------------------------------------------


if __name__ == "__main__":
    main()
