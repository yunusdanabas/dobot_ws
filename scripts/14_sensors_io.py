#!/usr/bin/env python3
"""
Sensors & I/O Demo (Track A: pydobotplus)

Demonstrates:
  IR proximity sensor — detect objects within range
  Color sensor        — identify dominant color channel
  Digital I/O         — set a GPIO pin HIGH/LOW

Sensor connectors on the Dobot Magician:
  GP1/GP3 — sensor ports (IR, color sensor)
  SW1     — tool power
  SW4     — gripper port

Run with:
    python scripts/14_sensors_io.py
"""

import sys
import time
from pydobotplus import Dobot
from utils import find_port, safe_move, go_home, check_alarms

# Pick-and-place coordinates used by the IR-triggered demo
PICK_X,  PICK_Y,  PICK_Z  = 220, -50, 30
PLACE_X, PLACE_Y, PLACE_Z = 220,  50, 30
LIFT = 50   # mm clearance


def ir_triggered_pick(bot):
    """Pick from PICK position and place at PLACE position."""
    safe_move(bot, PICK_X,  PICK_Y,  PICK_Z + LIFT, 0)
    safe_move(bot, PICK_X,  PICK_Y,  PICK_Z,        0)
    bot.suck(True)
    time.sleep(0.4)
    safe_move(bot, PICK_X,  PICK_Y,  PICK_Z + LIFT, 0)
    safe_move(bot, PLACE_X, PLACE_Y, PLACE_Z + LIFT, 0)
    safe_move(bot, PLACE_X, PLACE_Y, PLACE_Z,        0)
    bot.suck(False)
    time.sleep(0.3)
    safe_move(bot, PLACE_X, PLACE_Y, PLACE_Z + LIFT, 0)


def demo():
    port = find_port()
    if port is None:
        sys.exit("[Error] No serial port found. Run: python scripts/01_find_port.py")

    bot = Dobot(port=port)
    try:
        check_alarms(bot)
        go_home(bot)
        time.sleep(0.3)

        # === Demo 1: IR Proximity Sensor ===
        print("\n[Demo 1] IR proximity sensor (connect sensor to GP1)")
        bot.set_ir(enable=True)
        print("  Polling for 5 seconds — place your hand near the sensor ...")
        for _ in range(10):
            detected = bot.get_ir()
            print(f"  IR: {'DETECTED' if detected else 'clear   '}", end="\r")
            time.sleep(0.5)
        print()
        bot.set_ir(enable=False)

        # === Demo 2: Color Sensor ===
        print("\n[Demo 2] Color sensor (connect sensor to GP3)")
        bot.set_color(enable=True)
        print("  Reading for 5 seconds — hold a colored object near the sensor ...")
        for _ in range(10):
            r, g, b = bot.get_color()
            dominant = "RED" if r else ("GREEN" if g else ("BLUE" if b else "none"))
            print(f"  R={int(r)}  G={int(g)}  B={int(b)}  dominant={dominant:5s}", end="\r")
            time.sleep(0.5)
        print()
        bot.set_color(enable=False)

        # === Demo 3: Digital I/O ===
        print("\n[Demo 3] Digital I/O — toggle pin 5 (address=5)")
        for state in (True, False):
            label = "HIGH" if state else "LOW "
            print(f"  Pin 5 → {label}")
            bot.set_io(address=5, state=state)
            time.sleep(1.0)

        # === Demo 4: IR-triggered pick-and-place ===
        print("\n[Demo 4] IR-triggered pick-and-place")
        print("  Place an object at the pick site. The robot picks it when IR detects it.")
        print("  Press Ctrl+C to skip.\n")
        bot.set_ir(enable=True)
        safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT + 20, 0)
        triggered = False
        try:
            for _ in range(30):
                if bot.get_ir():
                    print("  Object detected — picking ...")
                    ir_triggered_pick(bot)
                    triggered = True
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("  Skipped.")
        if not triggered:
            print("  No object detected after 15 s — skipping pick.")
        bot.set_ir(enable=False)

        go_home(bot)
        print("\nSensors & I/O demo completed.")

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        raise
    finally:
        try:
            bot.suck(False)
            bot.set_ir(enable=False)
        except Exception:
            pass
        try:
            go_home(bot)
        except Exception:
            pass
        bot.close()
        print("Connection closed.")


if __name__ == "__main__":
    demo()
