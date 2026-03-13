"""
07_keyboard_teleop_win.py — Drive the Dobot Magician with the keyboard (Windows).

Uses msvcrt for key input — Windows-only. Run from cmd.exe or PowerShell.
The console window must be focused.

Continuous hold-to-move: hold a direction key for smooth motion instead of
discrete steps. Motion integrates at a fixed rate while keys are held.

Key Bindings
------------
  Arrow Right/Left  or  D / A   ->  +X / -X
  Arrow Up/Down     or  W / S   ->  +Y / -Y
  R / F                          ->  +Z / -Z  (raise / fall)
  Q / E                          ->  +R / -R (end-effector rotation)
  Space                          ->  Toggle suction ON/OFF
  H                              ->  Go to home
  Esc                            ->  Quit

Requirements:
    pip install pydobotplus pyqtgraph PyQt5

Usage:
    python 07_keyboard_teleop_win.py [--no-viz]

On Linux/macOS, use 07_keyboard_teleop.py instead.
"""

import sys

if sys.platform != "win32":
    sys.exit("This script is for Windows only. Use 07_keyboard_teleop.py on Linux/macOS.")

import argparse
import msvcrt
import time

from pydobotplus import Dobot
from utils import clamp, find_port, go_home, prepare_robot, SAFE_ACCELERATION, SAFE_BOUNDS, SAFE_VELOCITY, unpack_pose
from viz import RobotViz

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
JOG_VELOCITY_MM = 80   # mm/s for X, Y, Z
JOG_VELOCITY_DEG = 45  # deg/s for R

LOOP_HZ = 40
CMD_HZ = 20
RELEASE_THRESHOLD = 0.12

# Windows arrow key scan codes (second byte after 0x00 or 0xE0)
_SCAN_UP = 0x48
_SCAN_DOWN = 0x50
_SCAN_LEFT = 0x4B
_SCAN_RIGHT = 0x4D


def _read_key_nonblocking(timeout_s=0.02):
    """Read one key if available. Returns None if no key ready.
    Handles Windows arrow keys (extended key codes)."""
    if not msvcrt.kbhit():
        return None
    ch = msvcrt.getch()
    if not ch:
        return None
    # Handle extended keys (arrow keys, etc.): first byte 0x00 or 0xE0
    if ch in (b"\x00", b"\xe0"):
        if not msvcrt.kbhit():
            return None
        ch2 = msvcrt.getch()
        if not ch2:
            return None
        code = ch2[0]
        if code == _SCAN_UP:
            return "up"
        if code == _SCAN_DOWN:
            return "down"
        if code == _SCAN_LEFT:
            return "left"
        if code == _SCAN_RIGHT:
            return "right"
        return None  # Other extended keys ignored
    # Escape
    if ch == b"\x1b":
        return "esc"
    # Regular chars
    try:
        s = ch.decode("utf-8", errors="replace").lower()
        return s if s else None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Drive the Dobot with the keyboard (Windows)")
    parser.add_argument("--no-viz", action="store_true", help="Disable real-time visualization")
    args = parser.parse_args()

    PORT = find_port()

    if PORT is None:
        sys.exit("[Error] No serial port found. Run 01_find_port.py first.")

    bot = Dobot(port=PORT)
    bot.speed(SAFE_VELOCITY, SAFE_ACCELERATION)
    prepare_robot(bot)

    viz = RobotViz(enabled=not args.no_viz)
    viz.attach(bot)
    suction_on = False

    x, y, z, r, *_ = unpack_pose(bot.get_pose())
    print(f"Connected on {PORT}")
    print(f"Starting pose: X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}")
    print(__doc__)
    print("Ready. Hold WASD/arrows for X/Y, R/F for Z, Q/E for rotation.")

    intent = {"x": 0, "y": 0, "z": 0, "r": 0}
    last_key_time = {"x": 0.0, "y": 0.0, "z": 0.0, "r": 0.0}

    dt = 1.0 / LOOP_HZ
    cmd_interval = 1.0 / CMD_HZ
    last_cmd_time = 0.0
    had_intent_prev = False

    try:
        while True:
            now = time.perf_counter()

            key = _read_key_nonblocking(timeout_s=dt)

            if key is not None:
                if key == " ":
                    suction_on = not suction_on
                    bot.suck(suction_on)
                    print(f"\r  Suction: {'ON ' if suction_on else 'OFF'}  ", end="\r")
                elif key == "h":
                    go_home(bot)
                    x, y, z, r, *_ = unpack_pose(bot.get_pose())
                    for ax in intent:
                        intent[ax] = 0
                elif key == "esc":
                    print("\r\nQuitting ...")
                    break
                else:
                    if key in ("right", "d"):
                        intent["x"], last_key_time["x"] = 1, now
                    elif key in ("left", "a"):
                        intent["x"], last_key_time["x"] = -1, now
                    elif key in ("up", "w"):
                        intent["y"], last_key_time["y"] = 1, now
                    elif key in ("down", "s"):
                        intent["y"], last_key_time["y"] = -1, now
                    elif key == "r":
                        intent["z"], last_key_time["z"] = 1, now
                    elif key == "f":
                        intent["z"], last_key_time["z"] = -1, now
                    elif key == "q":
                        intent["r"], last_key_time["r"] = 1, now
                    elif key == "e":
                        intent["r"], last_key_time["r"] = -1, now

            for ax in ("x", "y", "z", "r"):
                if intent[ax] != 0 and (now - last_key_time[ax]) > RELEASE_THRESHOLD:
                    intent[ax] = 0

            v_mm = JOG_VELOCITY_MM * dt
            v_r = JOG_VELOCITY_DEG * dt

            x = clamp(x + intent["x"] * v_mm, *SAFE_BOUNDS["x"])
            y = clamp(y + intent["y"] * v_mm, *SAFE_BOUNDS["y"])
            z = clamp(z + intent["z"] * v_mm, *SAFE_BOUNDS["z"])
            r = clamp(r + intent["r"] * v_r, *SAFE_BOUNDS["r"])

            has_intent = any(intent.values())
            if has_intent and (now - last_cmd_time) >= cmd_interval:
                bot.move_to(x, y, z, r, wait=False)
                last_cmd_time = now
            elif had_intent_prev and not has_intent:
                try:
                    bot._set_queued_cmd_stop_exec()
                    bot._set_queued_cmd_clear()
                    bot._set_queued_cmd_start_exec()
                except Exception:
                    pass
            had_intent_prev = has_intent

            if key != " ":
                print(f"  X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}", end="\r")

            elapsed = time.perf_counter() - now
            if elapsed < dt:
                time.sleep(dt - elapsed)

    finally:
        if suction_on:
            bot.suck(False)
        viz.close()
        bot.close()


if __name__ == "__main__":
    main()
