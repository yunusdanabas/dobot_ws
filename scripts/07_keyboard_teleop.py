"""
07_keyboard_teleop.py — Drive the Dobot Magician with the keyboard.

Key Bindings
------------
  Arrow Right / Left   →  +X / -X
  Arrow Up   / Down    →  +Y / -Y
  Page Up    / Page Dn →  +Z / -Z
  Q          / E       →  +R / -R (end-effector rotation)
  Space                →  Toggle suction ON/OFF
  H                    →  Go to home (READY_POSE)
  Esc                  →  Quit

Requirements:
    pip install pynput pydobotplus

Usage:
    python 07_keyboard_teleop.py
"""

import sys
import threading
from pydobotplus import Dobot
from pynput import keyboard
from utils import find_port, safe_move, go_home, READY_POSE, SAFE_BOUNDS, clamp, unpack_pose

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
STEP = 5    # mm / deg per keypress (keep small for safety)


def main():
    PORT = find_port()

    if PORT is None:
        sys.exit("[Error] No serial port found. Run 01_find_port.py first.")

    # -----------------------------------------------------------------------
    # Robot state
    # -----------------------------------------------------------------------
    bot        = Dobot(port=PORT)
    suction_on = False
    _lock      = threading.Lock()

    try:
        # Initialise position from current pose
        x, y, z, r, *_ = unpack_pose(bot.get_pose())

        print(f"Connected on {PORT}")
        print(f"Starting pose: X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}")
        print(__doc__)

        # -------------------------------------------------------------------
        # Key handler
        # -------------------------------------------------------------------
        def move(dx=0, dy=0, dz=0, dr=0):
            nonlocal x, y, z, r
            with _lock:
                x = clamp(x + dx, *SAFE_BOUNDS["x"])
                y = clamp(y + dy, *SAFE_BOUNDS["y"])
                z = clamp(z + dz, *SAFE_BOUNDS["z"])
                r = clamp(r + dr, *SAFE_BOUNDS["r"])
                safe_move(bot, x, y, z, r)
                print(f"  X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}", end="\r")

        def on_press(key):
            nonlocal suction_on, x, y, z, r

            try:
                k = key.char.lower() if hasattr(key, "char") and key.char else None
            except AttributeError:
                k = None

            # --- Cartesian moves ---
            if key == keyboard.Key.right:
                move(dx=+STEP)
            elif key == keyboard.Key.left:
                move(dx=-STEP)
            elif key == keyboard.Key.up:
                move(dy=+STEP)
            elif key == keyboard.Key.down:
                move(dy=-STEP)
            elif key == keyboard.Key.page_up:
                move(dz=+STEP)
            elif key == keyboard.Key.page_down:
                move(dz=-STEP)

            # --- Rotation ---
            elif k == "q":
                move(dr=+STEP)
            elif k == "e":
                move(dr=-STEP)

            # --- Suction toggle ---
            elif key == keyboard.Key.space:
                suction_on = not suction_on
                bot.suck(suction_on)
                print(f"\n  Suction: {'ON ' if suction_on else 'OFF'}", end="\r")

            # --- Home ---
            elif k == "h":
                with _lock:
                    x, y, z, r = READY_POSE
                    go_home(bot)

            # --- Quit ---
            elif key == keyboard.Key.esc:
                print("\n\nQuitting ...")
                return False   # stops the listener

        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    finally:
        if suction_on:
            bot.suck(False)
        bot.close()


if __name__ == "__main__":
    main()
