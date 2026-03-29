"""
interactive_move.py — Interactive joint-angle control with Cartesian feedback (DOBOT MG400).
Prepared by Yunus Emre Danabas for ME403.

Enter body-frame joint angles to move the robot and see the actual Cartesian pose.

Commands:
    q1 q2 q3 q4   move to these body-frame angles (degrees, space-separated)
    q              quit

Body-frame angles:
    q1  base rotation
    q2  shoulder elevation from horizontal
    q3  elbow offset from upper-arm direction
    q4  wrist offset from forearm direction

Robot selection:
    Change setup(robot=1) below to setup(robot=2), etc.

Usage:
    python interactive_move.py
"""

import utils_mg400 as U


def main():
    dashboard, move_api = U.setup(robot=1)   # change robot=N as needed
    try:
        print("\n--- Interactive Move (MG400) ---")
        print("  Enter: q1 q2 q3 q4  (body-frame degrees, space-separated)")
        print("  Type 'q' to quit.\n")

        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not line:
                continue
            if line.lower() in ("q", "quit"):
                break

            parts = line.split()
            if len(parts) != 4:
                print("  Enter four angles, e.g.:  0 30 20 0")
                continue

            try:
                q = [float(p) for p in parts]
            except ValueError:
                print("  Could not parse — enter four numbers.")
                continue

            x, y, z, r = U.move_and_get_feedback(move_api, dashboard, q)
            print(f"  Actual pose:  X={x:.2f}  Y={y:.2f}  Z={z:.2f}  R={r:.2f}")

    finally:
        U.teardown(dashboard, move_api)


if __name__ == "__main__":
    main()
