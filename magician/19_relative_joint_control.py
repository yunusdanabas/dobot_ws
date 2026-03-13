"""
19_relative_joint_control.py — Interactive body-frame relative joint-angle control.

Students enter *relative* (body-frame) joint angles:
  J1_rel  base rotation from world X-axis        (same as absolute J1)
  J2_rel  shoulder elevation from horizontal      (same as absolute J2)
  J3_rel  elbow offset FROM the upper-arm         (NOT from horizontal)
  J4_rel  wrist offset FROM the forearm direction (NOT from horizontal)

The script converts these to absolute and firmware angles, prints the full
conversion chain, shows a FK prediction, then moves the robot.  This makes
the FK transformation chain explicit and educational.

Relative → Absolute conversion (body-frame chain):
  j1_abs = j1_rel
  j2_abs = j2_rel
  j3_abs = j2_rel + j3_rel   (elbow: accumulated from shoulder)
  j4_abs = j3_abs + j4_rel   (wrist: accumulated from elbow)

Magician parallel linkage quirk — firmware angle mapping:
  j1_fw = j1_rel
  j2_fw = j2_rel
  j3_fw = j3_rel             (firmware J3 IS already a body-frame offset; trivial)
  j4_fw = j4_abs             (firmware J4 is the absolute wrist angle)

Commands at the prompt:
  j1 j2 j3 j4   enter relative joint angles (degrees, space-separated)
  r              read current pose (Cartesian + both angle forms)
  h              go to home (joint zero)
  q              quit

Usage:
    python 19_relative_joint_control.py [--viz]

Extension: set LOG_TO_CSV = True to write every move to a CSV file.
"""

import argparse
import csv
import math
import sys
import time

from pydobotplus import Dobot
from pydobotplus.dobotplus import MODE_PTP

from utils import clamp, find_port, go_home, prepare_robot, unpack_pose
from viz import RobotViz

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG_TO_CSV = False
CSV_FILE   = "joint_log_19.csv"

# Dobot Magician link lengths (mm)
L1 = 135.0   # upper arm
L2 = 147.0   # forearm

# Safe joint-angle bounds — applied to FIRMWARE angles before each move.
# j1_fw=j1_rel, j2_fw=j2_rel, j3_fw=j3_rel (body-frame), j4_fw=j4_abs.
JOINT_BOUNDS = {
    "j1": (-90.0,  90.0),
    "j2": (  0.0,  85.0),
    "j3": (-10.0,  85.0),   # j3_rel is the elbow body-frame offset
    "j4": (-90.0,  90.0),   # j4_fw = j4_abs (absolute wrist angle)
}


# ---------------------------------------------------------------------------
# Relative ↔ Absolute conversion (body-frame chain)
# ---------------------------------------------------------------------------

def rel_to_abs_magician(j1_r, j2_r, j3_r, j4_r):
    """Convert body-frame relative angles to firmware and absolute tuples.

    Magician parallel linkage:
      j1_abs = j1_rel
      j2_abs = j2_rel              (shoulder from horizontal = relative = absolute)
      j3_abs = j2_rel + j3_rel    (elbow from horizontal = sum of two links)
      j4_abs = j3_abs + j4_rel    (wrist from horizontal = sum of three links)

    Firmware quirk: the Magician firmware's J3 channel already encodes a
    body-frame angle (relative to upper-arm direction), so j3_fw = j3_rel.
    j4_fw = j4_abs (the absolute wrist angle from horizontal).

    Returns:
      fw_tuple  = (j1_fw, j2_fw, j3_fw, j4_fw)     — what move_to() receives
      abs_tuple = (j1_abs, j2_abs, j3_abs, j4_abs)  — absolute angles for display
    """
    j3_abs = j2_r + j3_r
    j4_abs = j3_abs + j4_r
    fw_tuple  = (j1_r, j2_r, j3_r,    j4_abs)
    abs_tuple = (j1_r, j2_r, j3_abs,  j4_abs)
    return fw_tuple, abs_tuple


def fw_to_rel_magician(j1_fw, j2_fw, j3_fw, j4_fw):
    """Convert firmware angles back to body-frame relative angles (for display)."""
    j4_rel = j4_fw - (j2_fw + j3_fw)
    return j1_fw, j2_fw, j3_fw, j4_rel


# ---------------------------------------------------------------------------
# Forward kinematics (educational, simplified planar model)
# ---------------------------------------------------------------------------

def fk(j1: float, j2: float, j3: float, j4: float) -> tuple[float, float, float, float]:
    """Predict Cartesian pose from firmware joint angles.

    The Magician parallel linkage keeps the forearm angle from horizontal at
    j2_fw + j3_fw = j3_abs.  Returns (x, y, z, r) in mm / degrees.
    """
    a1 = math.radians(j1)
    a2 = math.radians(j2)
    a3 = math.radians(j2 + j3)   # forearm from horizontal = j3_abs
    reach  = L1 * math.cos(a2) + L2 * math.cos(a3)
    height = L1 * math.sin(a2) + L2 * math.sin(a3)
    x = reach * math.cos(a1)
    y = reach * math.sin(a1)
    return x, y, height, j4


# ---------------------------------------------------------------------------
# Joint clamping (applied to firmware angles)
# ---------------------------------------------------------------------------

def clamp_fw_joints(
    j1: float, j2: float, j3: float, j4: float
) -> tuple[float, float, float, float, bool]:
    """Clamp firmware angles to JOINT_BOUNDS. Returns (j1,j2,j3,j4, clamped:bool)."""
    cj1 = clamp(j1, *JOINT_BOUNDS["j1"])
    cj2 = clamp(j2, *JOINT_BOUNDS["j2"])
    cj3 = clamp(j3, *JOINT_BOUNDS["j3"])
    cj4 = clamp(j4, *JOINT_BOUNDS["j4"])
    was_clamped = (cj1, cj2, cj3, cj4) != (j1, j2, j3, j4)
    return cj1, cj2, cj3, cj4, was_clamped


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dobot Magician body-frame relative joint-angle REPL"
    )
    parser.add_argument("--viz", action="store_true", help="Enable visualizer")
    args = parser.parse_args()

    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Run: python 01_find_port.py")

    bot = Dobot(port=port)
    viz = RobotViz(enabled=args.viz)

    csv_fh     = None
    csv_writer = None

    try:
        prepare_robot(bot)
        viz.attach(bot)
        print(f"Connected on {port}")

        if LOG_TO_CSV:
            csv_fh = open(CSV_FILE, "w", newline="")
            csv_writer = csv.writer(csv_fh)
            csv_writer.writerow([
                "timestamp",
                "j1_rel", "j2_rel", "j3_rel", "j4_rel",
                "j1_abs", "j2_abs", "j3_abs", "j4_abs",
                "j1_fw",  "j2_fw",  "j3_fw",  "j4_fw",
                "fk_x",   "fk_y",   "fk_z",
                "x_act",  "y_act",  "z_act",
                "j1_act", "j2_act", "j3_act", "j4_act",
            ])
            print(f"Logging to {CSV_FILE}")

        print("\n--- 19_relative_joint_control: body-frame relative angle REPL ---")
        print("  Enter relative (body-frame) joint angles, e.g.:  0 20 10 0")
        print("    J1_rel  base rotation (= absolute)")
        print("    J2_rel  shoulder elevation from horizontal (= absolute)")
        print("    J3_rel  elbow offset FROM the upper-arm direction (body-frame)")
        print("    J4_rel  wrist offset FROM the forearm direction (body-frame)")
        print()
        print("  Commands:  r  read current pose   |  h  go home   |  q  quit")
        print()
        print("  Firmware bounds (clamped before move):")
        print(f"    J1(=j1_rel): {JOINT_BOUNDS['j1']}   J2(=j2_rel): {JOINT_BOUNDS['j2']}")
        print(f"    J3(=j3_rel): {JOINT_BOUNDS['j3']}   J4(=j4_abs): {JOINT_BOUNDS['j4']}")
        print(f"  Arm geometry: L1={L1:.0f} mm  L2={L2:.0f} mm")
        print()

        # Show starting state in both forms
        x, y, z, r, j1_fw, j2_fw, j3_fw, j4_fw = unpack_pose(bot.get_pose())
        j1_r, j2_r, j3_r, j4_r = fw_to_rel_magician(j1_fw, j2_fw, j3_fw, j4_fw)
        j3_abs = j2_fw + j3_fw
        print(f"  Current  Abs: J1={j1_fw:6.2f}  J2={j2_fw:6.2f}"
              f"  J3={j3_abs:6.2f}  J4={j4_fw:6.2f}")
        print(f"           Rel: J1={j1_r:6.2f}  J2={j2_r:6.2f}"
              f"  J3={j3_r:6.2f}  J4={j4_r:6.2f}")
        print()

        while True:
            # Refresh joints for the dual-line prompt
            _, _, _, _, j1_fw, j2_fw, j3_fw, j4_fw = unpack_pose(bot.get_pose())
            j1_r, j2_r, j3_r, j4_r = fw_to_rel_magician(j1_fw, j2_fw, j3_fw, j4_fw)
            j3_abs = j2_fw + j3_fw
            prompt = (
                f"Abs: J1={j1_fw:6.2f}  J2={j2_fw:6.2f}"
                f"  J3={j3_abs:6.2f}  J4={j4_fw:6.2f}\n"
                f"Rel: J1={j1_r:6.2f}  J2={j2_r:6.2f}"
                f"  J3={j3_r:6.2f}  J4={j4_r:6.2f}\n"
                f"> "
            )

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
                x, y, z, r, j1_fw, j2_fw, j3_fw, j4_fw = unpack_pose(bot.get_pose())
                j1_r, j2_r, j3_r, j4_r = fw_to_rel_magician(j1_fw, j2_fw, j3_fw, j4_fw)
                j3_abs = j2_fw + j3_fw
                print(f"  Pose     X={x:7.2f}  Y={y:7.2f}  Z={z:7.2f}  R={r:6.2f}")
                print(f"  Abs:     J1={j1_fw:6.2f}  J2={j2_fw:6.2f}"
                      f"  J3={j3_abs:6.2f}  J4={j4_fw:6.2f}")
                print(f"  Rel:     J1={j1_r:6.2f}  J2={j2_r:6.2f}"
                      f"  J3={j3_r:6.2f}  J4={j4_r:6.2f}")
                continue

            # --- go home ---
            if cmd == "h":
                print("[home] Moving to home ...")
                go_home(bot)
                _, _, _, _, j1_fw, j2_fw, j3_fw, j4_fw = unpack_pose(bot.get_pose())
                j1_r, j2_r, j3_r, j4_r = fw_to_rel_magician(j1_fw, j2_fw, j3_fw, j4_fw)
                print(f"  Home     Abs: J1={j1_fw:.2f}  J2={j2_fw:.2f}"
                      f"  J3={j3_fw:.2f}  J4={j4_fw:.2f}")
                print(f"           Rel: J1={j1_r:.2f}  J2={j2_r:.2f}"
                      f"  J3={j3_r:.2f}  J4={j4_r:.2f}")
                continue

            # --- joint move: parse four relative floats ---
            parts = line.split()
            if len(parts) != 4:
                print("  Usage: j1_rel j2_rel j3_rel j4_rel  (four space-separated numbers)")
                continue

            try:
                j1_in, j2_in, j3_in, j4_in = (float(p) for p in parts)
            except ValueError:
                print("  Could not parse — enter four numbers, e.g.:  0 20 10 0")
                continue

            # Step 1: Relative → Absolute + Firmware conversion
            (j1_fw_c, j2_fw_c, j3_fw_c, j4_fw_c), \
            (j1_abs_c, j2_abs_c, j3_abs_c, j4_abs_c) = \
                rel_to_abs_magician(j1_in, j2_in, j3_in, j4_in)

            # Step 2: Clamp firmware angles to safe bounds
            j1_fc, j2_fc, j3_fc, j4_fc, was_clamped = clamp_fw_joints(
                j1_fw_c, j2_fw_c, j3_fw_c, j4_fw_c
            )
            if was_clamped:
                print(f"  [clamp] fw ({j1_fw_c:.2f},{j2_fw_c:.2f},"
                      f"{j3_fw_c:.2f},{j4_fw_c:.2f})"
                      f" → ({j1_fc:.2f},{j2_fc:.2f},{j3_fc:.2f},{j4_fc:.2f})")

            # Step 3: Print the 3-line conversion block
            print(f"\n  Relative:  J1_rel={j1_in:7.2f}  J2_rel={j2_in:7.2f}"
                  f"  J3_rel={j3_in:7.2f}  J4_rel={j4_in:7.2f}")
            print(f"  Absolute:  j1_abs={j1_abs_c:7.2f}  j2_abs={j2_abs_c:7.2f}"
                  f"  j3_abs={j3_abs_c:7.2f}  j4_abs={j4_abs_c:7.2f}")
            print(f"  Firmware:  j1_fw= {j1_fc:7.2f}  j2_fw= {j2_fc:7.2f}"
                  f"  j3_fw= {j3_fc:7.2f}  j4_fw= {j4_fc:7.2f}")

            # Step 4: FK prediction
            fk_x, fk_y, fk_z, fk_r = fk(j1_fc, j2_fc, j3_fc, j4_fc)
            print(f"  [FK]       X={fk_x:7.2f}  Y={fk_y:7.2f}"
                  f"  Z={fk_z:7.2f}  R={fk_r:6.2f}")

            # Step 5: Execute move (MOVJ_ANGLE interprets as J1,J2,J3,J4 firmware)
            print(f"  [Move]     J1={j1_fc:.2f}  J2={j2_fc:.2f}"
                  f"  J3={j3_fc:.2f}  J4={j4_fc:.2f}")
            bot.move_to(j1_fc, j2_fc, j3_fc, j4_fc, wait=True, mode=MODE_PTP.MOVJ_ANGLE)

            # Step 6: Read back actual pose
            ax, ay, az, ar, aj1, aj2, aj3, aj4 = unpack_pose(bot.get_pose())
            print(f"  Done.      J1={aj1:.2f}  J2={aj2:.2f}"
                  f"  J3={aj3:.2f}  J4={aj4:.2f}")
            print(f"             X={ax:.2f}  Y={ay:.2f}  Z={az:.2f}")
            print()

            if csv_writer is not None:
                csv_writer.writerow([
                    f"{time.time():.3f}",
                    f"{j1_in:.4f}",    f"{j2_in:.4f}",    f"{j3_in:.4f}",    f"{j4_in:.4f}",
                    f"{j1_abs_c:.4f}", f"{j2_abs_c:.4f}", f"{j3_abs_c:.4f}", f"{j4_abs_c:.4f}",
                    f"{j1_fc:.4f}",    f"{j2_fc:.4f}",    f"{j3_fc:.4f}",    f"{j4_fc:.4f}",
                    f"{fk_x:.4f}",     f"{fk_y:.4f}",     f"{fk_z:.4f}",
                    f"{ax:.4f}",       f"{ay:.4f}",        f"{az:.4f}",
                    f"{aj1:.4f}",      f"{aj2:.4f}",       f"{aj3:.4f}",      f"{aj4:.4f}",
                ])

        print("Exiting REPL.")

    finally:
        if csv_fh:
            csv_fh.close()
            print(f"Saved {CSV_FILE}")
        try:
            viz.close()
        except Exception:
            pass
        bot.close()
        print("Connection closed.")


if __name__ == "__main__":
    main()
