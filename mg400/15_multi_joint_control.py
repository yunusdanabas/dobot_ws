"""
15_multi_joint_control.py — Broadcast the same joint command to multiple MG400s.

Every command typed at the REPL is sent to all selected robots in parallel
using threads + a Barrier so all JointMovJ calls fire at the same instant.

Commands at the REPL prompt:
  j1 j2 j3 j4   send to ALL robots simultaneously (degrees, space-separated)
  r              read and print current pose from all robots
  h              send all robots to READY_POSE simultaneously
  q              quit

Usage:
    python 15_multi_joint_control.py                  # all reachable robots (1-4)
    python 15_multi_joint_control.py --robots 1 2     # robots 1 and 2 only
    python 15_multi_joint_control.py --robots 1 2 --viz
"""

import argparse
import threading
import time

from utils_mg400 import (
    check_errors,
    clamp,
    close_all_robots,
    connect_multi,
    parse_angles,
    parse_pose,
    READY_POSE,
    ROBOT_IPS,
    SPEED_DEFAULT,
)
from viz_mg400 import RobotViz

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JOINT_BOUNDS = {
    "j1": (-170.0, 170.0),
    "j2": (  -5.0,  90.0),
    "j3": (-140.0,   5.0),
    "j4": (-170.0, 170.0),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clamp_joints(j1, j2, j3, j4):
    cj1 = clamp(j1, *JOINT_BOUNDS["j1"])
    cj2 = clamp(j2, *JOINT_BOUNDS["j2"])
    cj3 = clamp(j3, *JOINT_BOUNDS["j3"])
    cj4 = clamp(j4, *JOINT_BOUNDS["j4"])
    was_clamped = (cj1, cj2, cj3, cj4) != (j1, j2, j3, j4)
    return cj1, cj2, cj3, cj4, was_clamped


def read_state(dashboard):
    x, y, z, r = parse_pose(dashboard.GetPose())
    j1, j2, j3, j4 = parse_angles(dashboard.GetAngle())
    return x, y, z, r, j1, j2, j3, j4


def print_all_states(robots, label=""):
    """Print one status row per robot."""
    if label:
        print(label)
    for rid, (dashboard, _mv, _fd) in robots.items():
        try:
            x, y, z, r, j1, j2, j3, j4 = read_state(dashboard)
            print(
                f"  Robot {rid} ({ROBOT_IPS[rid]})"
                f"  X={x:8.2f}  Y={y:8.2f}  Z={z:8.2f}  R={r:6.2f}"
                f"  |  J1={j1:7.2f}  J2={j2:7.2f}  J3={j3:7.2f}  J4={j4:7.2f}"
            )
        except Exception as exc:
            print(f"  Robot {rid}: read error — {exc}")


def _move_thread(rid, move_api, barrier, j1, j2, j3, j4, results):
    """Worker: wait at barrier, fire JointMovJ, Sync, store result."""
    try:
        barrier.wait()                          # all threads release together
        move_api.JointMovJ(j1, j2, j3, j4)
        move_api.Sync()
        results[rid] = "ok"
    except Exception as exc:
        results[rid] = f"error: {exc}"


def broadcast_joints(robots, j1, j2, j3, j4):
    """Send JointMovJ(j1,j2,j3,j4) to all robots simultaneously."""
    barrier = threading.Barrier(len(robots))
    results = {}
    threads = [
        threading.Thread(
            target=_move_thread,
            args=(rid, mv, barrier, j1, j2, j3, j4, results),
            daemon=True,
        )
        for rid, (_db, mv, _fd) in robots.items()
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def _home_thread(rid, move_api, barrier, results):
    try:
        barrier.wait()
        move_api.MovJ(*READY_POSE)
        move_api.Sync()
        results[rid] = "ok"
    except Exception as exc:
        results[rid] = f"error: {exc}"


def broadcast_home(robots):
    """Send all robots to READY_POSE simultaneously."""
    barrier = threading.Barrier(len(robots))
    results = {}
    threads = [
        threading.Thread(
            target=_home_thread,
            args=(rid, mv, barrier, results),
            daemon=True,
        )
        for rid, (_db, mv, _fd) in robots.items()
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Broadcast joint commands to multiple MG400 robots"
    )
    parser.add_argument(
        "--robots", nargs="+", type=int, choices=[1, 2, 3, 4], metavar="N",
        default=None,
        help="Robot numbers to use (default: all 4)",
    )
    parser.add_argument("--viz", action="store_true", help="Enable visualizer")
    args = parser.parse_args()

    print("Connecting to robots ...")
    robots = connect_multi(args.robots)
    print(f"Connected: {list(robots.keys())}")

    # One shared viz window showing all robots (different colours not supported,
    # but all poses go to the same trail — useful for seeing sync)
    viz = RobotViz(enabled=args.viz)

    try:
        # Enable all robots sequentially (power-surge safety)
        for rid, (dashboard, mv, _fd) in robots.items():
            check_errors(dashboard)
            dashboard.EnableRobot()
            dashboard.SpeedFactor(SPEED_DEFAULT)
            print(f"  Robot {rid}: enabled at {SPEED_DEFAULT}%")
            time.sleep(0.3)

        # Attach viz to Robot 1's move_api (first in dict)
        first_mv = next(iter(robots.values()))[1]
        viz.attach(first_mv)

        print("\n--- 15_multi_joint_control: broadcast REPL ---")
        print("  Enter:  j1 j2 j3 j4   send to ALL robots simultaneously")
        print("          r              read all robots' current poses")
        print("          h              send all robots home")
        print("          q              quit")
        print()
        print("  Joint bounds:")
        for jname, (lo, hi) in JOINT_BOUNDS.items():
            print(f"    {jname.upper()}  {lo:7.1f}° … {hi:6.1f}°")
        print()

        print_all_states(robots, "Initial state:")
        print()

        while True:
            try:
                line = input(f"[{len(robots)} robots] > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not line:
                continue

            cmd = line.lower()

            # --- quit ---
            if cmd == "q":
                break

            # --- read all ---
            if cmd == "r":
                print_all_states(robots)
                continue

            # --- home all ---
            if cmd == "h":
                print(f"[home] Sending all {len(robots)} robots to READY_POSE ...")
                t0 = time.perf_counter()
                results = broadcast_home(robots)
                elapsed = time.perf_counter() - t0
                for rid, status in results.items():
                    print(f"  Robot {rid}: {status}")
                print(f"  All done in {elapsed:.2f}s")
                print_all_states(robots)
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
                    f"  [clamp] ({j1_in:.1f},{j2_in:.1f},{j3_in:.1f},{j4_in:.1f})"
                    f" → ({j1_c:.1f},{j2_c:.1f},{j3_c:.1f},{j4_c:.1f})"
                )

            print(
                f"  [broadcast] JointMovJ({j1_c:.2f}, {j2_c:.2f},"
                f" {j3_c:.2f}, {j4_c:.2f}) → {len(robots)} robots"
            )
            t0 = time.perf_counter()
            results = broadcast_joints(robots, j1_c, j2_c, j3_c, j4_c)
            elapsed = time.perf_counter() - t0

            for rid, status in results.items():
                print(f"    Robot {rid}: {status}")
            print(f"  All done in {elapsed:.2f}s")

            print_all_states(robots, "  Actual poses:")

    finally:
        print("\nDisabling robots ...")
        for rid, (dashboard, _mv, _fd) in robots.items():
            try:
                dashboard.DisableRobot()
                print(f"  Robot {rid}: disabled")
            except Exception:
                pass
        try:
            viz.close()
        except Exception:
            pass
        close_all_robots(robots)
        print("All connections closed.")


if __name__ == "__main__":
    main()
