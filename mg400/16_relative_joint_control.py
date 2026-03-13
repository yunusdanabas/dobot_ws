"""
16_relative_joint_control.py — Interactive body-frame relative joint-angle control (MG400).

Students enter *relative* (body-frame) joint angles:
  J1_rel  base rotation from world X-axis         (same as absolute J1)
  J2_rel  shoulder elevation from horizontal       (same as absolute J2)
  J3_rel  elbow offset FROM the upper-arm          (NOT from horizontal)
  J4_rel  wrist offset FROM the forearm direction  (NOT from horizontal)

The script converts these to absolute firmware angles, prints the full
conversion chain, shows the FK prediction via dashboard.PositiveSolution(),
then moves the robot.  This makes the FK transformation chain explicit and
educational.

Relative → Absolute conversion (body-frame chain):
  j1_abs = j1_rel
  j2_abs = j2_rel
  j3_abs = j2_rel + j3_rel   (elbow: accumulated from shoulder)
  j4_abs = j3_abs + j4_rel   (wrist: accumulated from elbow)

MG400 firmware mapping (all angles are fully absolute):
  j1_fw = j1_rel
  j2_fw = j2_rel
  j3_fw = j3_abs = j2_rel + j3_rel
  j4_fw = j4_abs = j2_rel + j3_rel + j4_rel

Commands at the prompt:
  j1 j2 j3 j4   enter relative joint angles (degrees, space-separated)
  r              read current pose (Cartesian + both angle forms)
  h              go to home (READY_POSE)
  q              quit

Usage:
    python 16_relative_joint_control.py [--robot N] [--viz]

Extension: set LOG_TO_CSV = True to write every move to a CSV file.
"""

import argparse
import csv
import sys
import time

from utils_mg400 import (
    check_errors,
    clamp,
    close_all,
    connect,
    go_home,
    MG400_IP,
    parse_angles,
    parse_pose,
    ROBOT_IPS,
    SPEED_DEFAULT,
)
from viz_mg400 import RobotViz

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG_TO_CSV = False
CSV_FILE   = "joint_log_16.csv"

# Safe joint-angle bounds — applied to FIRMWARE (absolute) angles.
JOINT_BOUNDS = {
    "j1": (-170.0, 170.0),
    "j2": (  -5.0,  90.0),
    "j3": (-140.0,   5.0),   # j3_fw = j3_abs = j2_rel + j3_rel
    "j4": (-170.0, 170.0),   # j4_fw = j4_abs = j2_rel + j3_rel + j4_rel
}


# ---------------------------------------------------------------------------
# Relative ↔ Absolute conversion (body-frame chain)
# ---------------------------------------------------------------------------

def rel_to_abs_mg400(j1_r, j2_r, j3_r, j4_r):
    """Convert body-frame relative angles to firmware and absolute tuples.

    MG400 firmware expects fully absolute angles:
      j1_fw = j1_rel
      j2_fw = j2_rel
      j3_fw = j2_rel + j3_rel   (accumulated elbow angle from horizontal)
      j4_fw = j3_fw + j4_rel    (accumulated wrist angle from horizontal)

    Because the MG400 firmware is fully absolute, fw_tuple == abs_tuple.

    Returns:
      fw_tuple  = (j1_fw, j2_fw, j3_fw, j4_fw)     — what JointMovJ() receives
      abs_tuple = (j1_abs, j2_abs, j3_abs, j4_abs)  — same values, for display
    """
    j3_abs = j2_r + j3_r
    j4_abs = j3_abs + j4_r
    fw_tuple  = (j1_r, j2_r, j3_abs, j4_abs)
    abs_tuple = (j1_r, j2_r, j3_abs, j4_abs)
    return fw_tuple, abs_tuple


def fw_to_rel_mg400(j1_fw, j2_fw, j3_fw, j4_fw):
    """Convert firmware (absolute) angles back to body-frame relative angles."""
    j3_rel = j3_fw - j2_fw
    j4_rel = j4_fw - j3_fw
    return j1_fw, j2_fw, j3_rel, j4_rel


# ---------------------------------------------------------------------------
# Helpers (reused verbatim from 14_joint_control.py)
# ---------------------------------------------------------------------------

def clamp_fw_joints(j1, j2, j3, j4):
    """Clamp firmware angles to JOINT_BOUNDS. Returns (j1,j2,j3,j4, clamped)."""
    cj1 = clamp(j1, *JOINT_BOUNDS["j1"])
    cj2 = clamp(j2, *JOINT_BOUNDS["j2"])
    cj3 = clamp(j3, *JOINT_BOUNDS["j3"])
    cj4 = clamp(j4, *JOINT_BOUNDS["j4"])
    was_clamped = (cj1, cj2, cj3, cj4) != (j1, j2, j3, j4)
    return cj1, cj2, cj3, cj4, was_clamped


def query_fk(dashboard, j1, j2, j3, j4):
    """Return (x,y,z,r) from PositiveSolution FK, or None on failure."""
    try:
        resp = dashboard.PositiveSolution(j1, j2, j3, j4, user=0, tool=0)
        return parse_pose(resp)
    except Exception as exc:
        print(f"  [FK] unavailable: {exc}")
        return None


def print_state(label, x, y, z, r, j1, j2, j3, j4):
    print(
        f"{label}  "
        f"X={x:8.2f}  Y={y:8.2f}  Z={z:8.2f}  R={r:7.2f}"
        f"  |  J1={j1:7.2f}  J2={j2:7.2f}  J3={j3:7.2f}  J4={j4:7.2f}"
    )


def read_state(dashboard):
    """Return (x,y,z,r,j1,j2,j3,j4) from dashboard queries."""
    x, y, z, r = parse_pose(dashboard.GetPose())
    j1, j2, j3, j4 = parse_angles(dashboard.GetAngle())
    return x, y, z, r, j1, j2, j3, j4


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="MG400 body-frame relative joint-angle REPL"
    )
    parser.add_argument("--ip", default=MG400_IP, help="MG400 IP address")
    parser.add_argument("--robot", type=int, choices=[1, 2, 3, 4], metavar="N",
                        help="Robot number 1-4 (overrides --ip)")
    parser.add_argument("--viz", action="store_true", help="Enable visualizer")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    dashboard, move_api, feed = connect(ip)
    viz = RobotViz(enabled=args.viz)

    csv_fh     = None
    csv_writer = None

    try:
        check_errors(dashboard)
        dashboard.EnableRobot()
        dashboard.SpeedFactor(SPEED_DEFAULT)
        print(f"Connected to MG400 at {ip}  (speed {SPEED_DEFAULT}%)")

        viz.attach(move_api)

        if LOG_TO_CSV:
            csv_fh = open(CSV_FILE, "w", newline="")
            csv_writer = csv.writer(csv_fh)
            csv_writer.writerow([
                "timestamp",
                "j1_rel", "j2_rel", "j3_rel", "j4_rel",
                "j1_abs", "j2_abs", "j3_abs", "j4_abs",
                "j1_fw",  "j2_fw",  "j3_fw",  "j4_fw",
                "fk_x",   "fk_y",   "fk_z",   "fk_r",
                "x_act",  "y_act",  "z_act",  "r_act",
                "j1_act", "j2_act", "j3_act", "j4_act",
            ])
            print(f"Logging to {CSV_FILE}")

        print("\n--- 16_relative_joint_control: body-frame relative angle REPL ---")
        print("  Enter relative (body-frame) joint angles, e.g.:  0 20 10 0")
        print("    J1_rel  base rotation (= absolute)")
        print("    J2_rel  shoulder elevation from horizontal (= absolute)")
        print("    J3_rel  elbow offset FROM the upper-arm direction (body-frame)")
        print("    J4_rel  wrist offset FROM the forearm direction (body-frame)")
        print()
        print("  Commands:  r  read current pose   |  h  go home   |  q  quit")
        print()
        print("  Firmware bounds (applied to absolute angles before move):")
        for jname, (lo, hi) in JOINT_BOUNDS.items():
            print(f"    {jname.upper()}(fw)  {lo:7.1f}° … {hi:6.1f}°")
        print()

        # Show starting state in both forms
        x, y, z, r, j1_fw, j2_fw, j3_fw, j4_fw = read_state(dashboard)
        j1_r, j2_r, j3_r, j4_r = fw_to_rel_mg400(j1_fw, j2_fw, j3_fw, j4_fw)
        print_state("Current:", x, y, z, r, j1_fw, j2_fw, j3_fw, j4_fw)
        print(f"  Rel:     J1={j1_r:6.2f}  J2={j2_r:6.2f}"
              f"  J3={j3_r:6.2f}  J4={j4_r:6.2f}")
        print()

        while True:
            # Refresh for dual-line prompt
            try:
                j1_fw, j2_fw, j3_fw, j4_fw = parse_angles(dashboard.GetAngle())
                j1_r, j2_r, j3_r, j4_r = fw_to_rel_mg400(j1_fw, j2_fw, j3_fw, j4_fw)
                prompt = (
                    f"Abs: J1={j1_fw:.1f}  J2={j2_fw:.1f}"
                    f"  J3={j3_fw:.1f}  J4={j4_fw:.1f}\n"
                    f"Rel: J1={j1_r:.1f}  J2={j2_r:.1f}"
                    f"  J3={j3_r:.1f}  J4={j4_r:.1f}\n"
                    f"> "
                )
            except Exception:
                prompt = "> "

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
                x, y, z, r, j1_fw, j2_fw, j3_fw, j4_fw = read_state(dashboard)
                j1_r, j2_r, j3_r, j4_r = fw_to_rel_mg400(j1_fw, j2_fw, j3_fw, j4_fw)
                print_state("Pose:   ", x, y, z, r, j1_fw, j2_fw, j3_fw, j4_fw)
                print(f"  Rel:   J1={j1_r:6.2f}  J2={j2_r:6.2f}"
                      f"  J3={j3_r:6.2f}  J4={j4_r:6.2f}")
                viz.send(x, y, z, r)
                continue

            # --- go home ---
            if cmd == "h":
                print("[home] Moving to READY_POSE ...")
                go_home(move_api)
                x, y, z, r, j1_fw, j2_fw, j3_fw, j4_fw = read_state(dashboard)
                j1_r, j2_r, j3_r, j4_r = fw_to_rel_mg400(j1_fw, j2_fw, j3_fw, j4_fw)
                print_state("Home:   ", x, y, z, r, j1_fw, j2_fw, j3_fw, j4_fw)
                print(f"  Rel:   J1={j1_r:6.2f}  J2={j2_r:6.2f}"
                      f"  J3={j3_r:6.2f}  J4={j4_r:6.2f}")
                continue

            # --- joint move: parse four relative floats ---
            parts = line.split()
            if len(parts) != 4:
                print("  Usage: j1_rel j2_rel j3_rel j4_rel  (four numbers in degrees)")
                continue

            try:
                j1_in, j2_in, j3_in, j4_in = (float(p) for p in parts)
            except ValueError:
                print("  Could not parse — enter four numbers, e.g.:  0 20 10 0")
                continue

            # Step 1: Relative → Absolute + Firmware conversion
            (j1_fw_c, j2_fw_c, j3_fw_c, j4_fw_c), \
            (j1_abs_c, j2_abs_c, j3_abs_c, j4_abs_c) = \
                rel_to_abs_mg400(j1_in, j2_in, j3_in, j4_in)

            # Step 2: Clamp firmware angles to safe bounds
            j1_fc, j2_fc, j3_fc, j4_fc, was_clamped = clamp_fw_joints(
                j1_fw_c, j2_fw_c, j3_fw_c, j4_fw_c
            )
            if was_clamped:
                print(f"  [clamp] fw ({j1_fw_c:.1f},{j2_fw_c:.1f},"
                      f"{j3_fw_c:.1f},{j4_fw_c:.1f})"
                      f" → ({j1_fc:.1f},{j2_fc:.1f},{j3_fc:.1f},{j4_fc:.1f})")

            # Step 3: Print the 3-line conversion block
            print(f"\n  Relative:  J1_rel={j1_in:7.2f}  J2_rel={j2_in:7.2f}"
                  f"  J3_rel={j3_in:7.2f}  J4_rel={j4_in:7.2f}")
            print(f"  Absolute:  j1_abs={j1_abs_c:7.2f}  j2_abs={j2_abs_c:7.2f}"
                  f"  j3_abs={j3_abs_c:7.2f}  j4_abs={j4_abs_c:7.2f}")
            print(f"  Firmware:  j1_fw= {j1_fc:7.2f}  j2_fw= {j2_fc:7.2f}"
                  f"  j3_fw= {j3_fc:7.2f}  j4_fw= {j4_fc:7.2f}")

            # Step 4: FK prediction via dashboard
            fk = query_fk(dashboard, j1_fc, j2_fc, j3_fc, j4_fc)
            if fk:
                fx, fy, fz, fr = fk
                print(f"  [FK]       X={fx:8.2f}  Y={fy:8.2f}"
                      f"  Z={fz:8.2f}  R={fr:7.2f}")

            # Step 5: Execute move
            print(f"  [Move]     J1={j1_fc:.2f}  J2={j2_fc:.2f}"
                  f"  J3={j3_fc:.2f}  J4={j4_fc:.2f}")
            move_api.JointMovJ(j1_fc, j2_fc, j3_fc, j4_fc)
            move_api.Sync()

            # Step 6: Read back actual pose
            ax, ay, az, ar, aj1, aj2, aj3, aj4 = read_state(dashboard)
            print_state("  Done:  ", ax, ay, az, ar, aj1, aj2, aj3, aj4)
            viz.send(ax, ay, az, ar)
            print()

            if csv_writer:
                fk_row = (f"{fx:.4f}", f"{fy:.4f}", f"{fz:.4f}", f"{fr:.4f}") \
                         if fk else ("", "", "", "")
                csv_writer.writerow([
                    f"{time.time():.3f}",
                    f"{j1_in:.4f}",    f"{j2_in:.4f}",    f"{j3_in:.4f}",    f"{j4_in:.4f}",
                    f"{j1_abs_c:.4f}", f"{j2_abs_c:.4f}", f"{j3_abs_c:.4f}", f"{j4_abs_c:.4f}",
                    f"{j1_fc:.4f}",    f"{j2_fc:.4f}",    f"{j3_fc:.4f}",    f"{j4_fc:.4f}",
                    *fk_row,
                    f"{ax:.4f}", f"{ay:.4f}", f"{az:.4f}", f"{ar:.4f}",
                    f"{aj1:.4f}", f"{aj2:.4f}", f"{aj3:.4f}", f"{aj4:.4f}",
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
        try:
            dashboard.DisableRobot()
        except Exception:
            pass
        close_all(dashboard, move_api, feed)
        print("Connections closed.")


if __name__ == "__main__":
    main()
