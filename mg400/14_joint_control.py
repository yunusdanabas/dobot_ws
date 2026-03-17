"""
14_joint_control.py — Interactive joint-angle control for the MG400.

Students command J1–J4 directly in degrees. Before each move the predicted
Cartesian pose is shown via dashboard.PositiveSolution() (FK). After the
move the actual pose is read back so students can compare FK prediction vs
reality.

MG400 joint ranges (per DT-MG400-4R075-01 hardware guide V1.1):
  J1  base rotation    -160° … +160°
  J2  shoulder         - 25° … + 85°
  J3  elbow            - 25° … +105°  (firmware absolute = j2 + j3_rel)
  J4  wrist rotation   -180° … +180°

Commands at the REPL prompt:
  j1 j2 j3 j4   move to these joint angles (degrees, space-separated)
  r              read and print current Cartesian pose + joint angles
  h              go to READY_POSE (home)
  q              quit

Usage:
    python 14_joint_control.py [--robot N] [--viz]

Extension: set LOG_TO_CSV = True to write every move to a CSV file.
"""

import argparse
import csv
import time

from utils_mg400 import (
    add_target_arguments,
    check_errors,
    clamp,
    close_all,
    connect_from_args_or_exit,
    go_home,
    parse_angles,
    parse_pose,
    SPEED_DEFAULT,
)
from viz_mg400 import RobotViz

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG_TO_CSV = False
CSV_FILE   = "joint_log_14.csv"

# Joint-angle bounds (degrees) per DT-MG400-4R075-01 hardware guide V1.1
JOINT_BOUNDS = {
    "j1": (-160.0, 160.0),   # ±160° per hardware guide
    "j2": ( -25.0,  85.0),   # -25° ~ +85° per hardware guide
    "j3": ( -25.0, 105.0),   # -25° ~ +105° per hardware guide (firmware absolute = j2+j3_rel)
    "j4": (-180.0, 180.0),   # ±180° per hardware guide
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clamp_joints(j1, j2, j3, j4):
    """Clamp all four joints to JOINT_BOUNDS. Returns (j1,j2,j3,j4, clamped)."""
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
    parser = argparse.ArgumentParser(description="MG400 interactive joint-angle REPL")
    add_target_arguments(parser)
    parser.add_argument("--viz", action="store_true", help="Enable visualizer")
    args = parser.parse_args()
    ip, dashboard, move_api, feed = connect_from_args_or_exit(args)

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
                "j1_cmd", "j2_cmd", "j3_cmd", "j4_cmd",
                "fk_x",   "fk_y",   "fk_z",   "fk_r",
                "x_act",  "y_act",  "z_act",  "r_act",
                "j1_act", "j2_act", "j3_act", "j4_act",
            ])
            print(f"Logging to {CSV_FILE}")

        print("\n--- 14_joint_control: interactive joint-angle REPL ---")
        print("  Enter:  j1 j2 j3 j4   (degrees, space-separated)")
        print("          r              read current pose")
        print("          h              go to home (READY_POSE)")
        print("          q              quit")
        print()
        print("  Joint bounds:")
        for jname, (lo, hi) in JOINT_BOUNDS.items():
            print(f"    {jname.upper()}  {lo:7.1f}° … {hi:6.1f}°")
        print()

        # Show starting state
        x, y, z, r, j1, j2, j3, j4 = read_state(dashboard)
        print_state("Current:", x, y, z, r, j1, j2, j3, j4)
        print()

        while True:
            # Refresh joints for the prompt (cheap GetAngle call)
            try:
                j1, j2, j3, j4 = parse_angles(dashboard.GetAngle())
                prompt = (f"J1={j1:.1f}  J2={j2:.1f}  J3={j3:.1f}  J4={j4:.1f}\n> ")
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
                x, y, z, r, j1, j2, j3, j4 = read_state(dashboard)
                print_state("Pose:   ", x, y, z, r, j1, j2, j3, j4)
                viz.send(x, y, z, r)
                continue

            # --- go home ---
            if cmd == "h":
                print("[home] Moving to READY_POSE ...")
                go_home(move_api)
                x, y, z, r, j1, j2, j3, j4 = read_state(dashboard)
                print_state("Home:   ", x, y, z, r, j1, j2, j3, j4)
                continue

            # --- joint move ---
            parts = line.split()
            if len(parts) != 4:
                print("  Usage: j1 j2 j3 j4  (four numbers in degrees)")
                continue

            try:
                j1_in, j2_in, j3_in, j4_in = (float(p) for p in parts)
            except ValueError:
                print("  Could not parse — enter four numbers, e.g.:  0 45 -60 0")
                continue

            j1_c, j2_c, j3_c, j4_c, was_clamped = clamp_joints(
                j1_in, j2_in, j3_in, j4_in
            )
            if was_clamped:
                print(
                    f"  [clamp] ({j1_in:.1f}, {j2_in:.1f}, {j3_in:.1f}, {j4_in:.1f})"
                    f" → ({j1_c:.1f}, {j2_c:.1f}, {j3_c:.1f}, {j4_c:.1f})"
                )

            # FK prediction via dashboard
            fk = query_fk(dashboard, j1_c, j2_c, j3_c, j4_c)
            if fk:
                fx, fy, fz, fr = fk
                print(f"  [FK]    X={fx:8.2f}  Y={fy:8.2f}  Z={fz:8.2f}  R={fr:7.2f}")

            # Execute move
            print(f"  [Move]  J1={j1_c:.2f}  J2={j2_c:.2f}  J3={j3_c:.2f}  J4={j4_c:.2f}")
            move_api.JointMovJ(j1_c, j2_c, j3_c, j4_c)
            move_api.Sync()

            # Read back actual pose
            ax, ay, az, ar, aj1, aj2, aj3, aj4 = read_state(dashboard)
            print_state("  Done:  ", ax, ay, az, ar, aj1, aj2, aj3, aj4)
            viz.send(ax, ay, az, ar)

            if csv_writer:
                fk_row = (f"{fx:.4f}", f"{fy:.4f}", f"{fz:.4f}", f"{fr:.4f}") \
                         if fk else ("", "", "", "")
                csv_writer.writerow([
                    f"{time.time():.3f}",
                    f"{j1_c:.4f}", f"{j2_c:.4f}", f"{j3_c:.4f}", f"{j4_c:.4f}",
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
