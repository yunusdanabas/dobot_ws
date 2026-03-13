"""
03_relative_joint_control.py — Body-frame FK exercise (Dobot Magician).
Prepared by Yunus Emre Danabas for ME403.

Enter *relative* (body-frame) joint angles to move the robot:
  J1_rel  base rotation from world X-axis        (same as absolute J1)
  J2_rel  shoulder elevation from horizontal      (same as absolute J2)
  J3_rel  elbow offset FROM the upper-arm         (NOT from horizontal)
  J4_rel  wrist offset FROM the forearm direction (NOT from horizontal)

The script converts your input through the full FK chain:
  j3_abs = j2_rel + j3_rel          (elbow angle from horizontal)
  j4_abs = j3_abs + j4_rel          (wrist angle from horizontal)

Magician firmware quirk:
  j3_fw  = j3_rel    (firmware J3 is already a body-frame offset; trivial)
  j4_fw  = j4_abs    (firmware J4 is the absolute wrist angle)

Commands:
  j1 j2 j3 j4   enter relative joint angles (degrees, space-separated)
  r              read current pose (Cartesian + both angle forms)
  h              return to home
  q              quit

Usage:
    python 03_relative_joint_control.py
"""

import math
import sys

from pydobotplus import Dobot
from pydobotplus.dobotplus import MODE_PTP

from utils import clamp, find_port, go_home, prepare_robot, unpack_pose

# ---------------------------------------------------------------------------
# Link lengths and joint bounds
# ---------------------------------------------------------------------------

L1 = 135.0   # upper arm (mm)
L2 = 147.0   # forearm (mm)

# Applied to FIRMWARE angles before each move.
JOINT_BOUNDS = {
    "j1": (-90.0,  90.0),
    "j2": (  0.0,  85.0),
    "j3": (-10.0,  85.0),   # j3_fw = j3_rel (body-frame elbow offset)
    "j4": (-90.0,  90.0),   # j4_fw = j4_abs (absolute wrist angle)
}


# ---------------------------------------------------------------------------
# Relative ↔ Absolute conversion
# ---------------------------------------------------------------------------

def rel_to_abs_magician(j1_r, j2_r, j3_r, j4_r):
    """Convert body-frame relative angles to firmware + absolute tuples.

    Body-frame chain:
      j3_abs = j2_rel + j3_rel      (accumulated elbow angle from horizontal)
      j4_abs = j3_abs + j4_rel      (accumulated wrist angle from horizontal)

    Magician firmware quirk:
      j3_fw = j3_rel   (firmware J3 is already body-frame)
      j4_fw = j4_abs   (firmware J4 is absolute)

    Returns:
      fw_tuple  = (j1_fw, j2_fw, j3_fw, j4_fw)     — what move_to() receives
      abs_tuple = (j1_abs, j2_abs, j3_abs, j4_abs)  — absolute angles for display
    """
    j3_abs = j2_r + j3_r
    j4_abs = j3_abs + j4_r
    fw_tuple  = (j1_r, j2_r, j3_r,   j4_abs)
    abs_tuple = (j1_r, j2_r, j3_abs, j4_abs)
    return fw_tuple, abs_tuple


def fw_to_rel_magician(j1_fw, j2_fw, j3_fw, j4_fw):
    """Convert firmware angles back to body-frame relative angles (for display)."""
    j4_rel = j4_fw - (j2_fw + j3_fw)
    return j1_fw, j2_fw, j3_fw, j4_rel


# ---------------------------------------------------------------------------
# Forward kinematics
# ---------------------------------------------------------------------------

def fk(j1: float, j2: float, j3: float, j4: float):
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
# Joint clamping
# ---------------------------------------------------------------------------

def clamp_fw_joints(j1, j2, j3, j4):
    """Clamp firmware angles to JOINT_BOUNDS. Returns (j1,j2,j3,j4, was_clamped)."""
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

        print("\n--- 03_relative_joint_control: body-frame FK exercise ---")
        print("  Enter relative (body-frame) joint angles, e.g.:  0 20 10 0")
        print("    J1_rel  base rotation (= absolute)")
        print("    J2_rel  shoulder from horizontal (= absolute)")
        print("    J3_rel  elbow offset FROM upper-arm (body-frame)")
        print("    J4_rel  wrist offset FROM forearm (body-frame)")
        print()
        print("  Commands:  r  read pose   |  h  go home   |  q  quit")
        print()
        print(f"  Arm geometry: L1={L1:.0f} mm  L2={L2:.0f} mm")
        print(f"  Firmware bounds: J1{JOINT_BOUNDS['j1']}  J2{JOINT_BOUNDS['j2']}"
              f"  J3{JOINT_BOUNDS['j3']}  J4{JOINT_BOUNDS['j4']}")
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
                f"\nAbs: J1={j1_fw:6.2f}  J2={j2_fw:6.2f}"
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
                print(f"  Pose  X={x:7.2f}  Y={y:7.2f}  Z={z:7.2f}  R={r:6.2f}")
                print(f"  Abs:  J1={j1_fw:6.2f}  J2={j2_fw:6.2f}"
                      f"  J3={j3_abs:6.2f}  J4={j4_fw:6.2f}")
                print(f"  Rel:  J1={j1_r:6.2f}  J2={j2_r:6.2f}"
                      f"  J3={j3_r:6.2f}  J4={j4_r:6.2f}")
                continue

            # --- home ---
            if cmd == "h":
                print("[home] Moving to home (0, 0, 0, 0) ...")
                go_home(bot)
                _, _, _, _, j1_fw, j2_fw, j3_fw, j4_fw = unpack_pose(bot.get_pose())
                j1_r, j2_r, j3_r, j4_r = fw_to_rel_magician(j1_fw, j2_fw, j3_fw, j4_fw)
                print(f"  Home  Abs: J1={j1_fw:.2f}  J2={j2_fw:.2f}"
                      f"  J3={j3_fw:.2f}  J4={j4_fw:.2f}")
                print(f"        Rel: J1={j1_r:.2f}  J2={j2_r:.2f}"
                      f"  J3={j3_r:.2f}  J4={j4_r:.2f}")
                continue

            # --- joint move ---
            parts = line.split()
            if len(parts) != 4:
                print("  Usage: j1_rel j2_rel j3_rel j4_rel  (four space-separated numbers)")
                continue

            try:
                j1_in, j2_in, j3_in, j4_in = (float(p) for p in parts)
            except ValueError:
                print("  Could not parse — enter four numbers, e.g.:  0 20 10 0")
                continue

            # Step 1: Relative → Absolute + Firmware
            (j1_fw_c, j2_fw_c, j3_fw_c, j4_fw_c), \
            (j1_abs_c, j2_abs_c, j3_abs_c, j4_abs_c) = \
                rel_to_abs_magician(j1_in, j2_in, j3_in, j4_in)

            # Step 2: Clamp firmware angles
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

            # Step 5: Execute move
            print(f"  [Move]     J1={j1_fc:.2f}  J2={j2_fc:.2f}"
                  f"  J3={j3_fc:.2f}  J4={j4_fc:.2f}")
            bot.move_to(j1_fc, j2_fc, j3_fc, j4_fc, wait=True, mode=MODE_PTP.MOVJ_ANGLE)

            # Step 6: Read back actual pose
            ax, ay, az, ar, aj1, aj2, aj3, aj4 = unpack_pose(bot.get_pose())
            print(f"  Done.      J1={aj1:.2f}  J2={aj2:.2f}"
                  f"  J3={aj3:.2f}  J4={aj4:.2f}")
            print(f"             X={ax:.2f}  Y={ay:.2f}  Z={az:.2f}")

        print("Exiting REPL.")

    finally:
        bot.close()
        print("Connection closed.")


if __name__ == "__main__":
    main()
