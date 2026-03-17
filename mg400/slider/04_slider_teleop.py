"""
04_slider_teleop.py — Hybrid keyboard teleop: MoveJog (arm) + MovJExt (slider).

Key Bindings
------------
  Arrow Right / D   →  Jog arm +X
  Arrow Left  / A   →  Jog arm -X
  Arrow Up    / W   →  Jog arm +Y
  Arrow Down  / S   →  Jog arm -Y
  R                 →  Jog arm +Z (raise)
  F                 →  Jog arm -Z (lower)
  Q                 →  Jog arm +Rx (rotate end-effector CCW)
  E                 →  Jog arm -Rx (rotate end-effector CW)
  [ / ]             →  Slide ±20 mm (coarse jog, SLIDER_STEP_FAST)
  { / }  (Shift+[]) →  Slide ±5 mm  (fine jog,   SLIDER_STEP_SLOW)
  H                 →  Home arm (READY_POSE) + home slider (0 mm)
  Space             →  Toggle suction (ToolDO 1)
  Esc               →  Quit

Hold-to-move for arm axes (MoveJog runs until key is released).
Slider jog is incremental (one MovJExt step per keypress) — NOT hold-to-move.

CRITICAL GUARD: Before any slider keypress the active arm jog is stopped with
MoveJog("") first, so the arm and slider do not inadvertently move simultaneously
from a teleop keystroke.

Prerequisites:
  - go_home_slider() is called at startup so slider position is known.
  - DobotStudio Pro: Configure → External Axis → Linear → mm → reboot (one-time)

Usage:
    python 04_slider_teleop.py
    python 04_slider_teleop.py --robot 2
    python 04_slider_teleop.py --ip 192.168.2.10
"""

import argparse
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from terminal_keys import TerminalKeyReader

from utils_slider import (
    add_target_arguments,
    close_all,
    check_errors,
    connect_from_args_or_exit,
    go_home,
    go_home_slider,
    jog_slider,
    parse_pose,
    get_slider_pos,
    SLIDER_IP,
    SLIDER_STEP_FAST,
    SLIDER_STEP_SLOW,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUCTION_DO      = 1    # tool digital output index for suction pump
JOG_SPEED       = 20   # % — MoveJog speed (lower = more precise)
STATUS_INTERVAL = 0.2  # s between status line updates


# Map key → MoveJog axis string
_KEY_TO_JOG = {
    "right": "X+", "d": "X+",
    "left":  "X-", "a": "X-",
    "up":    "Y+", "w": "Y+",
    "down":  "Y-", "s": "Y-",
    "r":     "Z+",
    "f":     "Z-",
    "q":     "Rx+",
    "e":     "Rx-",
}

# Map key → slider step delta (mm)
_KEY_TO_SLIDER = {
    "]":  SLIDER_STEP_FAST,
    "[": -SLIDER_STEP_FAST,
    "}":  SLIDER_STEP_SLOW,
    "{": -SLIDER_STEP_SLOW,
}


def main():
    parser = argparse.ArgumentParser(description="MG400 hybrid slider + arm teleop")
    add_target_arguments(parser, default_ip=SLIDER_IP)
    args = parser.parse_args()

    if not TerminalKeyReader.require_tty():
        sys.exit("[Error] Run from an interactive terminal (keyboard input required).")

    ip, dashboard, move_api, feed = connect_from_args_or_exit(args)
    suction_on = False

    try:
        check_errors(dashboard)
        dashboard.EnableRobot()
        dashboard.SpeedFactor(JOG_SPEED)
        print(f"Connected. Jog speed = {JOG_SPEED}%")

        # Home slider at startup — required so jog_slider() has a reference
        print("Homing slider to 0 mm (position reference) ...")
        go_home_slider(move_api)

        # Read initial pose before raw mode (so print renders normally)
        pose_resp = dashboard.GetPose()
        x, y, z, r = parse_pose(pose_resp)
        print(f"Initial arm pose: X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}")
        print(__doc__)
        print("Ready. Hold arm keys to jog; [ / ] for slider; Esc to quit.\n")

        current_jog = None   # currently active MoveJog axis (None = stopped)
        last_status = 0.0

        with TerminalKeyReader() as keys:
            while True:
                now = time.perf_counter()
                key = keys.read_key(timeout_s=0.02)

                if key is not None:
                    # --- Quit ---
                    if key == "esc":
                        if current_jog:
                            move_api.MoveJog("")
                            current_jog = None
                        print("\r\nQuitting ...")
                        break

                    # --- Suction toggle ---
                    elif key == " ":
                        if current_jog:
                            move_api.MoveJog("")
                            current_jog = None
                        suction_on = not suction_on
                        dashboard.ToolDO(SUCTION_DO, 1 if suction_on else 0)
                        print(f"\r  Suction: {'ON ' if suction_on else 'OFF'}  ", end="\r")

                    # --- Home both arm and slider ---
                    elif key == "h":
                        if current_jog:
                            move_api.MoveJog("")
                            current_jog = None
                        go_home(move_api)
                        go_home_slider(move_api)
                        last_status = 0  # force status refresh

                    # --- Slider jog ---
                    elif key in _KEY_TO_SLIDER:
                        # CRITICAL GUARD: stop arm jog before commanding the slider
                        if current_jog:
                            move_api.MoveJog("")
                            current_jog = None
                        delta = _KEY_TO_SLIDER[key]
                        try:
                            jog_slider(move_api, delta)
                        except RuntimeError as exc:
                            print(f"\r  {exc}  ", end="\r")

                    # --- Arm jog ---
                    elif key in _KEY_TO_JOG:
                        axis = _KEY_TO_JOG[key]
                        if axis != current_jog:
                            if current_jog:
                                move_api.MoveJog("")
                            move_api.MoveJog(axis)
                            current_jog = axis

                else:
                    # No key pressed — stop arm jogging
                    if current_jog:
                        move_api.MoveJog("")
                        current_jog = None

                # Periodic status line
                if (now - last_status) >= STATUS_INTERVAL:
                    try:
                        pose_resp = dashboard.GetPose()
                        x, y, z, r = parse_pose(pose_resp)
                        spos = get_slider_pos()
                        slider_label = f"{spos:.1f}" if spos is not None else "UNKNOWN"
                        jog_label   = current_jog or "---"
                        print(
                            f"  X={x:7.1f}  Y={y:7.1f}  Z={z:7.1f}  R={r:6.1f}"
                            f"  |  Slider={slider_label} mm  Jog={jog_label:<4}"
                            f"  Suction={'ON' if suction_on else 'OFF'}",
                            end="\r",
                        )
                    except Exception:
                        pass
                    last_status = now

        print()  # newline after \r status line

    finally:
        try:
            move_api.MoveJog("")
        except Exception:
            pass
        try:
            if suction_on:
                dashboard.ToolDO(SUCTION_DO, 0)
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
