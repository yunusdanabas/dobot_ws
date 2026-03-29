"""
interactive_move.py — Minimal move command for Magician.

Commands:
    move q1 q2 q3 q4
    q
"""

import utils as U


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
    bot = U.setup()
    try:
        print("\nEnter: move q1 q2 q3 q4")
        print("Type 'q' to quit.\n")

        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not line:
                continue
            if line.lower() in ("q", "quit"):
                break

            q = _parse_move_command(line)
            if q is None:
                print("  Use: move q1 q2 q3 q4")
                continue

            x, y, z, r = U.move_and_get_feedback(bot, q)
            print(f"  Pose: X={x:.2f} Y={y:.2f} Z={z:.2f} R={r:.2f}")
    finally:
        U.teardown(bot)


if __name__ == "__main__":
    main()
