"""
07_keyboard_teleop.py — Drive the MG400 with the keyboard using MoveJog.

MoveJog is the MG400's native jogging API:
  move_api.MoveJog("X+")  — start jogging in +X direction
  move_api.MoveJog("")    — stop jogging (empty string)

This is much simpler than the Magician's queue-flush approach:
no serial queue, no manual pose integration. The robot handles
velocity/deceleration internally and stops cleanly on MoveJog("").

Key Bindings
------------
  Arrow Right / D   →  Jog +X
  Arrow Left  / A   →  Jog -X
  Arrow Up    / W   →  Jog +Y
  Arrow Down  / S   →  Jog -Y
  R                 →  Jog +Z  (raise)
  F                 →  Jog -Z  (lower)
  Q                 →  Jog +R  (rotate end-effector CCW)
  E                 →  Jog -R  (rotate end-effector CW)
  Space             →  Toggle suction (ToolDO 1)
  H                 →  Go to READY_POSE (home)
  Esc               →  Quit

Hold-to-move: MoveJog runs until MoveJog("") is called or the arm hits a limit.
The robot firmware handles deceleration at joint/Cartesian limits automatically.

Usage:
    python 07_keyboard_teleop.py [--ip 192.168.2.7] [--viz]
    python 07_keyboard_teleop.py --robot 2 [--viz]
"""

import argparse
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from terminal_keys import TerminalKeyReader

from utils_mg400 import (
    add_target_arguments,
    close_all,
    check_errors,
    connect_from_args_or_exit,
    go_home,
    parse_pose,
)
from viz_mg400 import RobotViz

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUCTION_DO = 1    # tool digital output index for suction pump
JOG_SPEED  = 20   # % — teleop jog speed (lower = more precise)

# Minimum interval between MoveJog("") + pose reads (s)
STATUS_INTERVAL = 0.2


# Map key → MoveJog axis string
_KEY_TO_JOG = {
    "right": "X+", "d": "X+",
    "left":  "X-", "a": "X-",
    "up":    "Y+", "w": "Y+",
    "down":  "Y-", "s": "Y-",
    "r":     "Z+",
    "f":     "Z-",
    "q":     "Rx+",  # end-effector +R (mapped as Rx for 4-axis)
    "e":     "Rx-",
}


def main():
    parser = argparse.ArgumentParser(description="MG400 keyboard teleop")
    add_target_arguments(parser)
    parser.add_argument("--viz", action="store_true", help="Enable visualizer")
    args = parser.parse_args()

    if not TerminalKeyReader.require_tty():
        sys.exit("[Error] Run from an interactive terminal (keyboard input required).")

    ip, dashboard, move_api, feed = connect_from_args_or_exit(args)
    viz        = RobotViz(enabled=args.viz)
    suction_on = False

    try:
        check_errors(dashboard)
        dashboard.EnableRobot()
        dashboard.SpeedFactor(JOG_SPEED)
        print(f"Connected. Jog speed = {JOG_SPEED}%")

        viz.attach(move_api)

        # Read initial pose before entering raw mode (so print renders normally)
        pose_resp = dashboard.GetPose()
        x, y, z, r = parse_pose(pose_resp)
        print(f"Initial pose: X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}")
        print(__doc__)
        print("Ready. Hold direction keys to jog. Press Esc to quit.\n")

        current_jog = None   # currently active MoveJog axis string (None = stopped)
        last_status = 0.0

        with TerminalKeyReader() as keys:
            while True:
                now = time.perf_counter()
                key = keys.read_key(timeout_s=0.02)

                if key is not None:
                    # Special actions
                    if key == "esc":
                        if current_jog:
                            move_api.MoveJog("")
                            current_jog = None
                        print("\r\nQuitting ...")
                        break

                    elif key == " ":
                        # Stop any jog first for safety
                        if current_jog:
                            move_api.MoveJog("")
                            current_jog = None
                        suction_on = not suction_on
                        dashboard.ToolDO(SUCTION_DO, 1 if suction_on else 0)
                        print(f"\r  Suction: {'ON ' if suction_on else 'OFF'}  ", end="\r")

                    elif key == "h":
                        if current_jog:
                            move_api.MoveJog("")
                            current_jog = None
                        go_home(move_api)
                        last_status = 0  # force status refresh

                    elif key in _KEY_TO_JOG:
                        axis = _KEY_TO_JOG[key]
                        if axis != current_jog:
                            # Stop previous axis first, then start new
                            if current_jog:
                                move_api.MoveJog("")
                            move_api.MoveJog(axis)
                            current_jog = axis

                else:
                    # No key pressed — stop jogging
                    if current_jog:
                        move_api.MoveJog("")
                        current_jog = None

                # Periodic status line (avoid flooding the dashboard socket)
                if (now - last_status) >= STATUS_INTERVAL:
                    try:
                        pose_resp = dashboard.GetPose()
                        x, y, z, r = parse_pose(pose_resp)
                        viz.send(x, y, z, r)
                        jog_label = current_jog or "---"
                        print(
                            f"  X={x:7.1f}  Y={y:7.1f}  Z={z:7.1f}  R={r:6.1f}"
                            f"  Jog={jog_label:<4}  Suction={'ON' if suction_on else 'OFF'}",
                            end="\r",
                        )
                    except Exception:
                        pass
                    last_status = now

        print()   # newline after \r status line

    finally:
        try:
            move_api.MoveJog("")   # ensure jogging stops on all exit paths
        except Exception:
            pass
        try:
            if suction_on:
                dashboard.ToolDO(SUCTION_DO, 0)
        except Exception:
            pass
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
