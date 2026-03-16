"""
04_slider_intro.py — Introduction to the MG400 sliding rail (ME403 Lab 00).
Prepared by Yunus Emre Danabas for ME403.

Robot 2 (192.168.2.10) has the sliding rail (DT-AC-HDSR-001, 800 mm travel).

This script moves the rail through five positions to show how linear axis
control works with the MG400:  0 mm → 200 mm → 400 mm → 600 mm → 0 mm

Key concepts:
  - move_api.MovJExt(pos_mm, "SpeedE=50", "AccE=50")  — the slider command
  - move_api.Sync()   — wait for the current queue to finish
  - There is NO GetPoseExt; position is tracked in software

Prerequisites:
  - PC Ethernet set to static IP 192.168.2.100 / 255.255.255.0
  - ping 192.168.2.10 succeeds
  - DobotStudio Pro: Configure → External Axis → Linear → mm → reboot (one-time)
  - SDK cloned: git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git
                dobot_ws/vendor/TCP-IP-4Axis-Python

Usage:
    python 04_slider_intro.py               # Robot 2 (192.168.2.10)
    python 04_slider_intro.py --robot 2
    python 04_slider_intro.py --ip 192.168.2.10
"""

import argparse
import time

from utils_mg400 import (
    check_errors,
    close_all,
    connect,
    go_home,
    MG400_IP,
    ROBOT_IPS,
    SPEED_DEFAULT,
)

# ---------------------------------------------------------------------------
# Slider constants (self-contained — no import from mg400/slider/)
# ---------------------------------------------------------------------------

SLIDER_BOUNDS = (0.0, 800.0)   # mm — hardware limit of DT-AC-HDSR-001
SLIDER_HOME   = 0.0            # fully retracted

_slider_pos = None             # software position tracker (no API read-back)


def safe_move_ext(move_api, pos_mm, speed=50, acc=50):
    """Clamp pos_mm to SLIDER_BOUNDS, send MovJExt, Sync, and print position.

    Args:
        move_api: DobotApiMove instance
        pos_mm:   target rail position in mm
        speed:    SpeedE percentage (1-100)
        acc:      AccE percentage (1-100)

    Returns:
        The clamped position that was commanded (mm).
    """
    global _slider_pos
    lo, hi = SLIDER_BOUNDS
    pos_mm = max(lo, min(hi, pos_mm))
    move_api.MovJExt(pos_mm, f"SpeedE={speed}", f"AccE={acc}")
    move_api.Sync()
    _slider_pos = pos_mm
    print(f"  Slider → {pos_mm:.0f} mm")
    return pos_mm


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

# Default target: Robot 3 has the sliding rail
SLIDER_ROBOT_ID = 2
SLIDER_IP       = ROBOT_IPS[SLIDER_ROBOT_ID]   # "192.168.2.10"


def main() -> None:
    parser = argparse.ArgumentParser(description="MG400 slider introduction")
    parser.add_argument("--ip", default=SLIDER_IP,
                        help="MG400 IP address (default: Robot 2 = 192.168.2.10)")
    parser.add_argument("--robot", type=int, default=SLIDER_ROBOT_ID,
                        choices=[1, 2, 3, 4], metavar="N",
                        help="Robot number 1-4 (overrides --ip, default: 3)")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    print(f"Connecting to MG400 at {ip} (Robot 3 has the sliding rail) ...")

    dashboard = None
    move_api  = None
    try:
        dashboard, move_api = connect(ip)

        # Enable and clear errors
        dashboard.EnableRobot()
        time.sleep(1.5)
        check_errors(dashboard)
        dashboard.SpeedFactor(SPEED_DEFAULT)
        print(f"  Robot enabled. Speed factor = {SPEED_DEFAULT}%\n")

        # [1/6] Home the arm
        print("[1/6] Homing arm to READY_POSE ...")
        go_home(move_api)

        # [2/6] Home the slider — establishes position reference at 0 mm
        print("\n[2/6] Homing slider to 0 mm (position reference) ...")
        safe_move_ext(move_api, SLIDER_HOME)

        # [3/6] Extend to 200 mm
        print("\n[3/6] Moving slider to 200 mm ...")
        safe_move_ext(move_api, 200.0)

        # [4/6] Extend to 400 mm
        print("\n[4/6] Moving slider to 400 mm ...")
        safe_move_ext(move_api, 400.0)

        # [5/6] Extend to 600 mm
        print("\n[5/6] Moving slider to 600 mm ...")
        safe_move_ext(move_api, 600.0)

        # [6/6] Return home
        print("\n[6/6] Returning slider to 0 mm (home) ...")
        safe_move_ext(move_api, 0.0)

        print("\nDemo complete. Slider is back at home position (0 mm).")

    finally:
        if dashboard is not None:
            try:
                dashboard.DisableRobot()
            except Exception:
                pass
        if dashboard is not None and move_api is not None:
            close_all(dashboard, move_api)
        print("Connection closed.")


if __name__ == "__main__":
    main()
