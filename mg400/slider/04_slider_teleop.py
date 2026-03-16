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
import select
import sys
import termios
import tty
import time

from utils_slider import (
    connect,
    close_all,
    check_errors,
    go_home,
    go_home_slider,
    jog_slider,
    parse_pose,
    get_slider_pos,
    SLIDER_IP,
    ROBOT_IPS,
    SLIDER_STEP_FAST,
    SLIDER_STEP_SLOW,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUCTION_DO    = 1    # tool digital output index for suction pump
JOG_SPEED     = 20   # % — MoveJog speed (lower = more precise)
STATUS_INTERVAL = 0.2  # s between status line updates


def _set_raw(fd):
    old = termios.tcgetattr(fd)
    tty.setraw(fd)
    return old


def _restore(fd, old):
    termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _read_key(fd, timeout=0.02):
    """Non-blocking key read from stdin fd. Returns None if no key available."""
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if not ready:
        return None
    ch = sys.stdin.read(1)
    if not ch:
        return None
    if ch == "\x1b":
        r2, _, _ = select.select([sys.stdin], [], [], 0.05)
        if not r2:
            return "esc"
        c1 = sys.stdin.read(1)
        if c1 != "[":
            return "esc"
        r3, _, _ = select.select([sys.stdin], [], [], 0.02)
        if not r3:
            return "esc"
        c2 = sys.stdin.read(1)
        if c2 == "A":
            return "up"
        if c2 == "B":
            return "down"
        if c2 == "C":
            return "right"
        if c2 == "D":
            return "left"
        return "esc"
    # Return raw character; lowercase except for bracket/brace keys
    if ch in ("[]{}"):
        return ch
    return ch.lower() if ch else None


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
    parser.add_argument("--ip", default=SLIDER_IP, help="MG400 IP address")
    parser.add_argument("--robot", type=int, default=2, choices=[1, 2, 3, 4],
                        metavar="N", help="Robot number 1-4 (overrides --ip)")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    if not sys.stdin.isatty():
        sys.exit("[Error] Run from an interactive terminal (keyboard input required).")

    dashboard, move_api, feed = connect(ip)
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

        fd       = sys.stdin.fileno()
        old_term = _set_raw(fd)

        try:
            while True:
                now = time.perf_counter()
                key = _read_key(fd)

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

        finally:
            _restore(fd, old_term)

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
