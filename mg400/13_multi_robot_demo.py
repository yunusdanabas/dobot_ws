"""
13_multi_robot_demo.py — Simultaneous control of multiple MG400 robots.

Connects to 1–4 robots, enables them sequentially (avoids power-surge on
simultaneous enable), then runs a small XY square on each robot in parallel
using threading.Barrier to synchronise motion phases.

Usage:
    python 13_multi_robot_demo.py                # all 4 robots
    python 13_multi_robot_demo.py --robots 1 2   # robots 1 and 2 only
"""

import argparse
import threading
import time

from utils_mg400 import (
    check_errors,
    close_all_robots,
    connect_multi,
    go_home,
    READY_POSE,
    ROBOT_IPS,
    safe_move,
)


# ---------------------------------------------------------------------------
# Sequential enable / disable
# ---------------------------------------------------------------------------

def enable_sequential(robots: dict) -> None:
    """Enable robots one-by-one to avoid a simultaneous power surge."""
    for rid, (dashboard, _move_api, _feed) in robots.items():
        check_errors(dashboard)
        dashboard.EnableRobot()
        print(f"  Robot {rid} ({ROBOT_IPS[rid]}): enabled")
        time.sleep(0.5)


def disable_sequential(robots: dict) -> None:
    """Disable all robots one-by-one."""
    for rid, (dashboard, _move_api, _feed) in robots.items():
        try:
            dashboard.DisableRobot()
            print(f"  Robot {rid}: disabled")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Per-robot motion thread
# ---------------------------------------------------------------------------

def run_on_robot(
    rid: int,
    dashboard,
    move_api,
    feed,
    barrier: threading.Barrier,
) -> None:
    """Motion sequence for one robot, synchronised at barrier points."""
    print(f"Robot {rid}: going home ...")
    go_home(move_api)
    barrier.wait()   # sync point 1: all robots at READY_POSE

    # Small XY square (40 mm side) at READY_POSE height
    x0, y0, z0, r0 = READY_POSE
    corners = [(x0 + 40, y0), (x0 + 40, y0 + 40), (x0, y0 + 40), (x0, y0)]
    for cx, cy in corners:
        safe_move(move_api, cx, cy, z0, r0, mode="L")
        move_api.Sync()

    barrier.wait()   # sync point 2: all robots finished square
    print(f"Robot {rid}: demo complete")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MG400 multi-robot parallel demo")
    parser.add_argument(
        "--robots", nargs="+", type=int, choices=[1, 2, 3, 4], metavar="N",
        default=None,
        help="Robot numbers to use (default: all 4)",
    )
    args = parser.parse_args()

    robots = connect_multi(args.robots)
    print(f"Connected to {len(robots)} robot(s): {list(robots.keys())}")

    try:
        enable_sequential(robots)

        barrier = threading.Barrier(len(robots))
        threads = [
            threading.Thread(
                target=run_on_robot,
                args=(rid, db, mv, fd, barrier),
                name=f"robot-{rid}",
            )
            for rid, (db, mv, fd) in robots.items()
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    finally:
        disable_sequential(robots)
        close_all_robots(robots)
        print("All connections closed.")


if __name__ == "__main__":
    main()
