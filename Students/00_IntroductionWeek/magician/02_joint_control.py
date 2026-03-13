"""
02_joint_control.py — Interactive joint-angle control (simplified).

Type four joint angles (degrees) to move the robot. This script allows
direct control of each joint in joint-space.

Commands:
    j1 j2 j3 j4   — move to these angles (degrees, space-separated)
    r              — read current pose
    h              — return to home
    q              — quit

Joint limits (safe bounds):
    J1: ±90°    J2: 0–85°    J3: -10–85°    J4: ±90°

Usage:
    python 02_joint_control.py
"""

import sys
from pydobotplus import Dobot
from pydobotplus.dobotplus import MODE_PTP

from utils import clamp, find_port, go_home, prepare_robot, unpack_pose

# ---------------------------------------------------------------------------
# Joint bounds
# ---------------------------------------------------------------------------

# Safe per-joint operating limits (degrees).
# These are tighter than firmware limits to keep the arm in a comfortable range.
JOINT_BOUNDS = {
    "j1": (-90.0,  90.0),   # base rotation
    "j2": (  0.0,  85.0),   # rear arm elevation
    "j3": (-10.0,  85.0),   # forearm elevation (parallel linkage)
    "j4": (-90.0,  90.0),   # end-effector rotation
}


# ---------------------------------------------------------------------------
# Joint clamping
# ---------------------------------------------------------------------------

def clamp_joints(
    j1: float, j2: float, j3: float, j4: float
) -> tuple[float, float, float, float, bool]:
    """Clamp each joint angle to JOINT_BOUNDS. Returns (j1,j2,j3,j4, was_clamped)."""
    cj1 = clamp(j1, *JOINT_BOUNDS["j1"])
    cj2 = clamp(j2, *JOINT_BOUNDS["j2"])
    cj3 = clamp(j3, *JOINT_BOUNDS["j3"])
    cj4 = clamp(j4, *JOINT_BOUNDS["j4"])
    was_clamped = (cj1, cj2, cj3, cj4) != (j1, j2, j3, j4)
    return cj1, cj2, cj3, cj4, was_clamped


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def print_pose(label: str, pose_8: tuple) -> None:
    """Print a labelled Cartesian + joint-angle row from an 8-tuple."""
    x, y, z, r, j1, j2, j3, j4 = pose_8
    print(f"{label}  X={x:7.2f}  Y={y:7.2f}  Z={z:7.2f}  R={r:6.2f}"
          f"  |  J1={j1:6.2f}  J2={j2:6.2f}  J3={j3:6.2f}  J4={j4:6.2f}")


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------

def main() -> None:
    # --- Port discovery ---
    port = find_port()
    if port is None:
        print("[Error] No serial port found.")
        print("  Check: USB cable connected, wall adapter plugged in,")
        print("  DobotStudio closed. See README.md for per-platform help.")
        sys.exit(1)

    bot = Dobot(port=port)
    try:
        prepare_robot(bot)
        print(f"Connected on {port}")

        # Print startup banner
        print("\n--- 02_joint_control: interactive joint-angle REPL ---")
        print("  Enter:  j1 j2 j3 j4   (degrees, space-separated)")
        print("          r              read current pose")
        print("          h              go to home (all joints → 0)")
        print("          q              quit")
        print()
        print(f"  Joint bounds: J1{JOINT_BOUNDS['j1']}  J2{JOINT_BOUNDS['j2']}"
              f"  J3{JOINT_BOUNDS['j3']}  J4{JOINT_BOUNDS['j4']}")
        print()

        # Show current state
        pose_8 = unpack_pose(bot.get_pose())
        print_pose("Current:", pose_8)

        # --- REPL loop ---
        while True:
            # Refresh current joints for the prompt
            _, _, _, _, cj1, cj2, cj3, cj4 = unpack_pose(bot.get_pose())
            prompt = (f"\nCurrent: J1={cj1:.2f}  J2={cj2:.2f}"
                      f"  J3={cj3:.2f}  J4={cj4:.2f}\n> ")

            try:
                line = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not line:
                continue
            cmd = line.lower()

            # --- quit ---
            if cmd == "q":
                break

            # --- read pose ---
            if cmd == "r":
                print_pose("Pose:   ", unpack_pose(bot.get_pose()))
                continue

            # --- home ---
            if cmd == "h":
                print("[home] Moving to home (0, 0, 0, 0) ...")
                go_home(bot)
                print_pose("Home:   ", unpack_pose(bot.get_pose()))
                continue

            # --- joint move ---
            parts = line.split()
            if len(parts) != 4:
                print("  Usage: j1 j2 j3 j4  (four space-separated numbers in degrees)")
                continue

            try:
                j1_in, j2_in, j3_in, j4_in = (float(p) for p in parts)
            except ValueError:
                print("  Could not parse — enter four numbers, e.g.:  0 45 20 0")
                continue

            # Clamp to safe joint limits
            j1_c, j2_c, j3_c, j4_c, was_clamped = clamp_joints(j1_in, j2_in, j3_in, j4_in)
            if was_clamped:
                print(f"  [clamp] ({j1_in:.2f}, {j2_in:.2f}, {j3_in:.2f}, {j4_in:.2f})"
                      f" → ({j1_c:.2f}, {j2_c:.2f}, {j3_c:.2f}, {j4_c:.2f})")

            # Execute the joint move.
            # bot.move_to with MODE_PTP.MOVJ_ANGLE interprets first four args as J1,J2,J3,J4
            print(f"  [Move]  J1={j1_c:.2f}  J2={j2_c:.2f}  J3={j3_c:.2f}  J4={j4_c:.2f}")
            bot.move_to(j1_c, j2_c, j3_c, j4_c, wait=True, mode=MODE_PTP.MOVJ_ANGLE)

            # Read back and display actual result
            ax, ay, az, ar, aj1, aj2, aj3, aj4 = unpack_pose(bot.get_pose())
            print(f"  Done.   J1={aj1:.2f}  J2={aj2:.2f}  J3={aj3:.2f}  J4={aj4:.2f}")

        print("Exiting REPL.")

    finally:
        bot.close()
        print("Connection closed.")


if __name__ == "__main__":
    main()
