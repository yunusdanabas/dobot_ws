"""
18_joint_control.py — Interactive joint-angle control for Dobot Magician.

Students can command the robot by specifying J1–J4 directly (degrees), which
exercises forward/inverse kinematics understanding. Before each move the
predicted Cartesian position is displayed via FK, and the actual pose is read
back after the move so students can compare.

Commands at the prompt:
    j1 j2 j3 j4   — move to these joint angles (degrees, space-separated)
    r              — read and print the current pose (Cartesian + joints)
    h              — go to home (joint zero)
    q              — quit

Usage:
    python 18_joint_control.py

Extension: set LOG_TO_CSV = True to write every commanded move to a CSV file.
"""

import csv
import math
import sys
import time

from pydobotplus import Dobot
from pydobotplus.dobotplus import MODE_PTP

from utils import clamp, find_port, go_home, prepare_robot, unpack_pose

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG_TO_CSV = False          # set True to write moves to CSV
CSV_FILE   = "joint_log_18.csv"

# Dobot Magician link lengths (mm)
L1 = 135.0   # upper arm
L2 = 147.0   # forearm (parallel linkage keeps it horizontal-referenced)

# Safe joint-angle bounds (degrees)
JOINT_BOUNDS = {
    "j1": (-90.0,  90.0),
    "j2": (  0.0,  85.0),
    "j3": (-10.0,  85.0),
    "j4": (-90.0,  90.0),
}


# ---------------------------------------------------------------------------
# Forward kinematics (educational, simplified planar model)
# ---------------------------------------------------------------------------

def fk(j1: float, j2: float, j3: float, j4: float) -> tuple[float, float, float, float]:
    """Predict Cartesian pose from joint angles using Dobot Magician geometry.

    Dobot uses a parallel linkage so the forearm angle from horizontal is J2+J3.
    Returns (x, y, z, r) in mm / degrees.  Z is arm-plane height only (no base offset).
    """
    a1 = math.radians(j1)
    a2 = math.radians(j2)
    a3 = math.radians(j2 + j3)   # parallel linkage constraint
    reach  = L1 * math.cos(a2) + L2 * math.cos(a3)
    height = L1 * math.sin(a2) + L2 * math.sin(a3)
    x = reach * math.cos(a1)
    y = reach * math.sin(a1)
    return x, y, height, j4


# ---------------------------------------------------------------------------
# Joint clamping
# ---------------------------------------------------------------------------

def clamp_joints(
    j1: float, j2: float, j3: float, j4: float
) -> tuple[float, float, float, float, bool]:
    """Clamp each joint to JOINT_BOUNDS. Returns (j1,j2,j3,j4, clamped:bool)."""
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
    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Run: python 01_find_port.py")

    bot = Dobot(port=port)

    csv_fh     = None
    csv_writer = None

    try:
        prepare_robot(bot)
        print(f"Connected on {port}")

        if LOG_TO_CSV:
            csv_fh = open(CSV_FILE, "w", newline="")
            csv_writer = csv.writer(csv_fh)
            csv_writer.writerow([
                "timestamp",
                "j1_cmd", "j2_cmd", "j3_cmd", "j4_cmd",
                "fk_x",   "fk_y",   "fk_z",
                "x_act",  "y_act",  "z_act",
                "j1_act", "j2_act", "j3_act", "j4_act",
            ])
            print(f"Logging to {CSV_FILE}")

        print("\n--- 18_joint_control: interactive joint-angle REPL ---")
        print("  Enter:  j1 j2 j3 j4   (degrees, space-separated)")
        print("          r              read current pose")
        print("          h              go to home")
        print("          q              quit")
        print()
        print(f"  Joint bounds: J1{JOINT_BOUNDS['j1']}  J2{JOINT_BOUNDS['j2']}"
              f"  J3{JOINT_BOUNDS['j3']}  J4{JOINT_BOUNDS['j4']}")
        print(f"  Arm geometry: L1={L1:.0f} mm  L2={L2:.0f} mm")
        print()

        # Print the current state so students know where they're starting from
        x, y, z, r, j1, j2, j3, j4 = unpack_pose(bot.get_pose())
        print_pose("Current:", (x, y, z, r, j1, j2, j3, j4))

        while True:
            # Show current joints in the prompt
            cur = unpack_pose(bot.get_pose())
            _, _, _, _, cj1, cj2, cj3, cj4 = cur
            prompt = (f"Current: J1={cj1:.2f}  J2={cj2:.2f}"
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
                pose_8 = unpack_pose(bot.get_pose())
                print_pose("Pose:   ", pose_8)
                continue

            # --- go home ---
            if cmd == "h":
                print("[home] Moving to home pose ...")
                go_home(bot)
                pose_8 = unpack_pose(bot.get_pose())
                print_pose("Home:   ", pose_8)
                continue

            # --- joint move: parse four floats ---
            parts = line.split()
            if len(parts) != 4:
                print("  Usage: j1 j2 j3 j4  (four space-separated numbers)")
                continue

            try:
                j1_in, j2_in, j3_in, j4_in = (float(p) for p in parts)
            except ValueError:
                print("  Could not parse values — enter four numbers, e.g.: 0 45 20 0")
                continue

            j1_c, j2_c, j3_c, j4_c, was_clamped = clamp_joints(
                j1_in, j2_in, j3_in, j4_in
            )
            if was_clamped:
                print(f"  [clamp] ({j1_in:.2f},{j2_in:.2f},{j3_in:.2f},{j4_in:.2f})"
                      f" → ({j1_c:.2f},{j2_c:.2f},{j3_c:.2f},{j4_c:.2f})")

            # Show FK prediction
            fk_x, fk_y, fk_z, fk_r = fk(j1_c, j2_c, j3_c, j4_c)
            print(f"  [FK]    X={fk_x:7.2f}  Y={fk_y:7.2f}  Z={fk_z:7.2f}  R={fk_r:6.2f}")

            # Execute move (MOVJ_ANGLE interprets (a,b,c,d) as J1,J2,J3,J4)
            print(f"  [Move]  J1={j1_c:.2f}  J2={j2_c:.2f}  J3={j3_c:.2f}  J4={j4_c:.2f}")
            bot.move_to(j1_c, j2_c, j3_c, j4_c, wait=True, mode=MODE_PTP.MOVJ_ANGLE)

            # Read back actual pose
            actual = unpack_pose(bot.get_pose())
            ax, ay, az, ar, aj1, aj2, aj3, aj4 = actual
            print(f"  Done.   J1={aj1:.2f}  J2={aj2:.2f}  J3={aj3:.2f}  J4={aj4:.2f}"
                  f"  (X={ax:.2f}  Y={ay:.2f}  Z={az:.2f})")

            if csv_writer is not None:
                csv_writer.writerow([
                    f"{time.time():.3f}",
                    f"{j1_c:.4f}", f"{j2_c:.4f}", f"{j3_c:.4f}", f"{j4_c:.4f}",
                    f"{fk_x:.4f}", f"{fk_y:.4f}", f"{fk_z:.4f}",
                    f"{ax:.4f}",   f"{ay:.4f}",   f"{az:.4f}",
                    f"{aj1:.4f}",  f"{aj2:.4f}",  f"{aj3:.4f}",  f"{aj4:.4f}",
                ])

        print("Exiting REPL.")

    finally:
        if csv_fh:
            csv_fh.close()
            print(f"Saved {CSV_FILE}")
        bot.close()
        print("Connection closed.")


if __name__ == "__main__":
    main()
