"""
interface.py — Minimal move command for Magician / MG400.

Set ROBOT_TYPE in utils.py to select the robot.

Commands:
    move q1 q2 q3 q4
    x
    q
"""

import utils as U
import myCode



def _parse_move_command(line):
    parts = line.split()
    if len(parts) == 5 and parts[0].lower() == "move":
        angle_parts = parts[1:]
    elif len(parts) == 4:
        angle_parts = parts
    else:
        return None
    try:
        return [float(p) for p in angle_parts]
    except ValueError:
        return None


def main():
    robot = U.setup()
    try:
        print("\nEnter: 'move q1 q2 q3 q4' to move the robot once")
        print("Type 'q' to quit.\n")
        print("Type 'x' to execute custom code.\n")

        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not line:
                continue

            if line.lower() in ("q", "quit"):
                break

            if line.lower() in ("x", "execute"):
                print("Now your code begins!")
                myCode.run()
                continue
            else:
                q = _parse_move_command(line)

            if q is None:
                print("  Use: 'move q1 q2 q3 q4', 'q', or 'x'")
                continue

            x, y, z, r = U.move_and_get_feedback(robot, q)
            print(f" Pose: X={x:.2f} Y={y:.2f} Z={z:.2f} R={r:.2f}")

    finally:
        U.teardown(robot)


if __name__ == "__main__":
    main()
