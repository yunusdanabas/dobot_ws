"""
02_joint_control.py — Interactive joint-angle control for the MG400.
Prepared by Yunus Emre Danabas for ME403.

Type four joint angles (degrees) to move the robot directly in joint space.
Before each move the predicted Cartesian pose is shown via FK.

Commands:
    j1 j2 j3 j4   — move to these angles (degrees, space-separated)
    r              — read current pose (Cartesian + joint angles)
    h              — return to READY_POSE (home)
    q              — quit

MG400 joint limits (per hardware guide V1.1):
    J1: ±160°    J2: -25° to 85°    J3: -25° to 105°    J4: ±180°

Usage:
    python 02_joint_control.py               # Robot 1 (192.168.2.7)
    python 02_joint_control.py --robot 2     # Robot 2
    python 02_joint_control.py --ip 192.168.2.7
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
# Joint bounds
# ---------------------------------------------------------------------------

# Per-joint operating limits (degrees) per DT-MG400-4R075-01 hardware guide V1.1
JOINT_BOUNDS = {
    "j1": (-160.0, 160.0),   # ±160° per hardware guide
    "j2": ( -25.0,  85.0),   # -25° ~ +85° per hardware guide
    "j3": ( -25.0, 105.0),   # -25° ~ +105° per hardware guide (firmware absolute = j2+j3_rel)
    "j4": (-180.0, 180.0),   # ±180° per hardware guide
}


def clamp_joints(j1: float, j2: float, j3: float, j4: float):
    """Clamp all four joints to JOINT_BOUNDS. Returns (j1,j2,j3,j4, was_clamped)."""
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
    parser = argparse.ArgumentParser(description="MG400 interactive joint-angle REPL")
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

        print("\n--- 02_joint_control: interactive joint-angle REPL ---")
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
            # Refresh joints for the prompt
            try:
                j1, j2, j3, j4 = parse_angles(dashboard.GetAngle())
                prompt = f"J1={j1:.1f}  J2={j2:.1f}  J3={j3:.1f}  J4={j4:.1f}\n> "
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
            try:
                fk_resp = dashboard.PositiveSolution(j1_c, j2_c, j3_c, j4_c,
                                                     user=0, tool=0)
                fx, fy, fz, fr = parse_pose(fk_resp)
                print(f"  [FK]    X={fx:8.2f}  Y={fy:8.2f}  Z={fz:8.2f}  R={fr:7.2f}")
            except Exception as exc:
                print(f"  [FK] unavailable: {exc}")

            # Execute move
            print(f"  [Move]  J1={j1_c:.2f}  J2={j2_c:.2f}  J3={j3_c:.2f}  J4={j4_c:.2f}")
            move_api.JointMovJ(j1_c, j2_c, j3_c, j4_c)
            move_api.Sync()

            # Read back actual pose
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
