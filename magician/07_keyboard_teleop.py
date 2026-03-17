"""
07_keyboard_teleop.py — Drive the Dobot Magician with the keyboard.

Uses stdin (terminal) for key input — works on Wayland and X11. The terminal
must be focused; keys are read directly from the terminal (no pynput).

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
    python 07_keyboard_teleop.py [--no-viz]

  Use --no-viz if the script appears stuck (e.g. viz window steals focus).

Hardware verification checklist (run with robot connected):
  - Holding a direction key produces continuous motion (not one step per key)
  - Motion starts and stops promptly when key is pressed/released
  - Traversal speed is noticeably faster than the old step-based behavior
  - Bounds are respected (no POSE_LIMIT_OVER or unexpected alarms)
"""

import argparse
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from terminal_keys import TerminalKeyReader

from pydobotplus import Dobot
from utils import clamp, find_port, go_home, prepare_robot, SAFE_ACCELERATION, SAFE_BOUNDS, SAFE_VELOCITY, unpack_pose
from viz import RobotViz

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Hold-to-move: jog speed (mm/s or deg/s) while key is held
JOG_VELOCITY_MM = 80   # mm/s for X, Y, Z
JOG_VELOCITY_DEG = 45  # deg/s for R

# Control loop rate (Hz) — target update frequency
LOOP_HZ = 40

# Command dispatch rate: send move_to at most this often to avoid serial flood
# Increased from 15 to 20 now that move_to no longer blocks on get_pose()
CMD_HZ = 20

# Key-release threshold (s): if no key event for this axis for longer, stop motion
RELEASE_THRESHOLD = 0.12


def main():
    parser = argparse.ArgumentParser(description="Drive the Dobot with the keyboard")
    parser.add_argument("--no-viz", action="store_true", help="Disable real-time visualization")
    args = parser.parse_args()

    PORT = find_port()

    if PORT is None:
        sys.exit("[Error] No serial port found. Run 01_find_port.py first.")

    if not TerminalKeyReader.require_tty():
        sys.exit("[Error] Run from an interactive terminal (keyboard input required).")

    bot = Dobot(port=PORT)
    bot.speed(SAFE_VELOCITY, SAFE_ACCELERATION)
    prepare_robot(bot)

    viz = RobotViz(enabled=not args.no_viz)
    viz.attach(bot)
    suction_on = False

    # Read initial pose and print info before entering raw mode so \n renders correctly
    x, y, z, r, *_ = unpack_pose(bot.get_pose())
    print(f"Connected on {PORT}")
    print(f"Starting pose: X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}")
    print(__doc__)
    print("Ready. Hold WASD/arrows for X/Y, R/F for Z, Q/E for rotation.")
    if not args.no_viz:
        print("(Keep the terminal focused for keyboard input; viz runs in a separate window.)")

    # Axis intent: -1, 0, or +1. Updated on key events; cleared after RELEASE_THRESHOLD
    intent = {"x": 0, "y": 0, "z": 0, "r": 0}
    last_key_time = {"x": 0.0, "y": 0.0, "z": 0.0, "r": 0.0}

    dt = 1.0 / LOOP_HZ
    cmd_interval = 1.0 / CMD_HZ
    last_cmd_time = 0.0
    had_intent_prev = False

    try:
        with TerminalKeyReader() as keys:
            while True:
                now = time.perf_counter()

                # Poll for key input (non-blocking)
                key = keys.read_key(timeout_s=dt)

                if key is not None:
                    # Special keys (instant action)
                    if key == " ":
                        suction_on = not suction_on
                        bot.suck(suction_on)
                        print(f"\r  Suction: {'ON ' if suction_on else 'OFF'}  ", end="\r", flush=True)
                    elif key == "h":
                        go_home(bot)
                        x, y, z, r, *_ = unpack_pose(bot.get_pose())
                        for ax in intent:
                            intent[ax] = 0
                    elif key == "esc":
                        print("\r\nQuitting ...")
                        break
                    else:
                        # Direction keys: update intent and last-key time
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

                # Clear intent for axes where key was released
                for ax in ("x", "y", "z", "r"):
                    if intent[ax] != 0 and (now - last_key_time[ax]) > RELEASE_THRESHOLD:
                        intent[ax] = 0

                # Integrate target pose (continuous hold-to-move)
                v_mm = JOG_VELOCITY_MM * dt
                v_r = JOG_VELOCITY_DEG * dt

                x = clamp(x + intent["x"] * v_mm, *SAFE_BOUNDS["x"])
                y = clamp(y + intent["y"] * v_mm, *SAFE_BOUNDS["y"])
                z = clamp(z + intent["z"] * v_mm, *SAFE_BOUNDS["z"])
                r = clamp(r + intent["r"] * v_r, *SAFE_BOUNDS["r"])

                # Throttled command dispatch (non-blocking move)
                has_intent = any(intent.values())
                if has_intent and (now - last_cmd_time) >= cmd_interval:
                    bot.move_to(x, y, z, r, wait=False)
                    last_cmd_time = now
                elif had_intent_prev and not has_intent:
                    # Key just released: stop queue execution and flush pending
                    # commands so the robot halts at its current position rather
                    # than overshooting through buffered moves.
                    try:
                        bot._set_queued_cmd_stop_exec()
                        bot._set_queued_cmd_clear()
                        bot._set_queued_cmd_start_exec()
                    except Exception:
                        pass
                had_intent_prev = has_intent

                # Status line
                if key != " ":
                    print(f"  X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}", end="\r", flush=True)

                # Sleep to maintain loop rate
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
