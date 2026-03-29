"""
03_relative_joint_control.py — Body-frame FK exercise (DOBOT MG400).
Prepared by Yunus Emre Danabas for ME403.

Enter *relative* (body-frame) joint angles to move the robot:
  J1_rel  base rotation from world X-axis         (same as absolute J1)
  J2_rel  shoulder elevation from horizontal       (same as absolute J2)
  J3_rel  elbow offset FROM the upper-arm          (NOT from horizontal)
  J4_rel  wrist offset FROM the forearm direction  (NOT from horizontal)

The script converts your input through the full FK chain:
  j3_abs = j2_rel + j3_rel          (elbow angle from horizontal)
  j4_abs = j4_rel                   (wrist yaw only; end-effector stays parallel to floor)

MG400 firmware expects fully absolute angles, so:
  j3_fw = j3_abs = j2_rel + j3_rel
  j4_fw = j4_rel                    (wrist yaw only)

Commands:
  j1 j2 j3 j4   enter relative joint angles (degrees, space-separated)
  r              read current pose (Cartesian + both angle forms)
  h              return to READY_POSE (home)
  q              quit

MG400 joint limits (per hardware guide V1.1, on firmware/absolute angles):
  J1: ±160°    J2: -25° to 85°    J3: -25° to 105°    J4: ±180°

Usage:
    python 03_relative_joint_control.py               # Robot 1 (192.168.2.7)
    python 03_relative_joint_control.py --robot 2     # Robot 2
    python 03_relative_joint_control.py --ip 192.168.2.7
"""

import argparse
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

# ---------------------------------------------------------------------------
# Joint bounds (applied to firmware/absolute angles)
# ---------------------------------------------------------------------------

JOINT_BOUNDS = {
    "j1": (-160.0, 160.0),   # ±160° per hardware guide
    "j2": ( -25.0,  85.0),   # -25° ~ +85° per hardware guide
    "j3": ( -25.0, 105.0),   # j3_fw = j3_abs = j2_rel + j3_rel; -25° ~ +105° per hardware guide
    "j4": (-180.0, 180.0),   # j4_fw = j4_rel (wrist yaw only); ±180° per hardware guide
}


# ---------------------------------------------------------------------------
# Relative ↔ Absolute conversion
# ---------------------------------------------------------------------------

def rel_to_abs_mg400(j1_r, j2_r, j3_r, j4_r):
    """Convert body-frame relative angles to firmware + absolute tuples.

    Body-frame chain:
      j3_abs = j2_rel + j3_rel      (accumulated elbow angle from horizontal)
      j4_abs = j4_rel               (wrist yaw only; end-effector stays parallel to floor)

    MG400 firmware expects fully absolute angles, so fw_tuple == abs_tuple.

    Returns:
      fw_tuple  = (j1_fw, j2_fw, j3_fw, j4_fw)     — what JointMovJ() receives
      abs_tuple = (j1_abs, j2_abs, j3_abs, j4_abs)  — same, for display
    """
    j3_abs = j2_r + j3_r
    fw_tuple  = (j1_r, j2_r, j3_abs, j4_r)
    abs_tuple = (j1_r, j2_r, j3_abs, j4_r)
    return fw_tuple, abs_tuple


def fw_to_rel_mg400(j1_fw, j2_fw, j3_fw, j4_fw):
    """Convert firmware (absolute) angles back to body-frame relative angles."""
    j3_rel = j3_fw - j2_fw
    return j1_fw, j2_fw, j3_rel, j4_fw


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
# Display helpers
# ---------------------------------------------------------------------------

def print_state(label: str, x: float, y: float, z: float, r: float,
                j1: float, j2: float, j3: float, j4: float) -> None:
    print(
        f"{label}  "
        f"X={x:8.2f}  Y={y:8.2f}  Z={z:8.2f}  R={r:7.2f}"
        f"  |  J1={j1:7.2f}  J2={j2:7.2f}  J3={j3:7.2f}  J4={j4:7.2f}"
    )


def read_state(dashboard):
    """Return (x, y, z, r, j1, j2, j3, j4) from dashboard queries."""
    x, y, z, r   = parse_pose(dashboard.GetPose())
    j1, j2, j3, j4 = parse_angles(dashboard.GetAngle())
    return x, y, z, r, j1, j2, j3, j4


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MG400 body-frame relative joint-angle FK exercise"
    )
    add_target_arguments(parser)
    args = parser.parse_args()
    ip, dashboard, move_api = connect_from_args_or_exit(args)

    print(f"Connecting to MG400 at {ip} ...")

    try:
        check_errors(dashboard)
        dashboard.EnableRobot()
        time.sleep(1.5)
        dashboard.SpeedFactor(SPEED_DEFAULT)
        print(f"Connected  (speed {SPEED_DEFAULT}%)")

        print("\n--- 03_relative_joint_control: body-frame FK exercise ---")
        print("  Enter relative (body-frame) joint angles, e.g.:  0 20 10 0")
        print("    J1_rel  base rotation (= absolute)")
        print("    J2_rel  shoulder from horizontal (= absolute)")
        print("    J3_rel  elbow offset FROM upper-arm (body-frame)")
        print("    J4_rel  wrist offset FROM forearm (body-frame)")
        print()
        print("  Commands:  r  read pose   |  h  go home   |  q  quit")
        print()
        print("  Firmware bounds (on absolute angles):")
        for jname, (lo, hi) in JOINT_BOUNDS.items():
            print(f"    {jname.upper()}  {lo:7.1f}° … {hi:6.1f}°")
        print()

        # Show starting state in both forms
        x, y, z, r, j1_fw, j2_fw, j3_fw, j4_fw = read_state(dashboard)
        j1_r, j2_r, j3_r, j4_r = fw_to_rel_mg400(j1_fw, j2_fw, j3_fw, j4_fw)
        print_state("Current:", x, y, z, r, j1_fw, j2_fw, j3_fw, j4_fw)
        print(f"  Rel:  J1={j1_r:6.2f}  J2={j2_r:6.2f}"
              f"  J3={j3_r:6.2f}  J4={j4_r:6.2f}")
        print()

        while True:
            # Refresh joints for the dual-line prompt
            try:
                j1_fw, j2_fw, j3_fw, j4_fw = parse_angles(dashboard.GetAngle())
                j1_r, j2_r, j3_r, j4_r = fw_to_rel_mg400(j1_fw, j2_fw, j3_fw, j4_fw)
                prompt = (
                    f"\nAbs: J1={j1_fw:.1f}  J2={j2_fw:.1f}"
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
                print(f"  Rel:  J1={j1_r:6.2f}  J2={j2_r:6.2f}"
                      f"  J3={j3_r:6.2f}  J4={j4_r:6.2f}")
                continue

            # --- go home ---
            if cmd == "h":
                print("[home] Moving to READY_POSE ...")
                go_home(move_api)
                x, y, z, r, j1_fw, j2_fw, j3_fw, j4_fw = read_state(dashboard)
                j1_r, j2_r, j3_r, j4_r = fw_to_rel_mg400(j1_fw, j2_fw, j3_fw, j4_fw)
                print_state("Home:   ", x, y, z, r, j1_fw, j2_fw, j3_fw, j4_fw)
                print(f"  Rel:  J1={j1_r:6.2f}  J2={j2_r:6.2f}"
                      f"  J3={j3_r:6.2f}  J4={j4_r:6.2f}")
                continue

            # --- joint move ---
            parts = line.split()
            if len(parts) != 4:
                print("  Usage: j1_rel j2_rel j3_rel j4_rel  (four numbers in degrees)")
                continue

            try:
                j1_in, j2_in, j3_in, j4_in = (float(p) for p in parts)
            except ValueError:
                print("  Could not parse — enter four numbers, e.g.:  0 20 10 0")
                continue

            # Step 1: Relative → Absolute + Firmware
            (j1_fw_c, j2_fw_c, j3_fw_c, j4_fw_c), \
            (j1_abs_c, j2_abs_c, j3_abs_c, j4_abs_c) = \
                rel_to_abs_mg400(j1_in, j2_in, j3_in, j4_in)

            # Step 2: Clamp firmware angles
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
            try:
                fk_resp = dashboard.PositiveSolution(j1_fc, j2_fc, j3_fc, j4_fc,
                                                     user=0, tool=0)
                fx, fy, fz, fr = parse_pose(fk_resp)
                print(f"  [FK]       X={fx:8.2f}  Y={fy:8.2f}"
                      f"  Z={fz:8.2f}  R={fr:7.2f}")
            except Exception as exc:
                print(f"  [FK] unavailable: {exc}")

            # Step 5: Execute move
            print(f"  [Move]     J1={j1_fc:.2f}  J2={j2_fc:.2f}"
                  f"  J3={j3_fc:.2f}  J4={j4_fc:.2f}")
            move_api.JointMovJ(j1_fc, j2_fc, j3_fc, j4_fc)
            move_api.Sync()

            # Step 6: Read back actual pose
            ax, ay, az, ar, aj1, aj2, aj3, aj4 = read_state(dashboard)
            print_state("  Done:  ", ax, ay, az, ar, aj1, aj2, aj3, aj4)

        print("Exiting REPL.")

    finally:
        try:
            dashboard.DisableRobot()
        except Exception:
            pass
        close_all(dashboard, move_api)
        print("Connection closed.")


if __name__ == "__main__":
    main()
