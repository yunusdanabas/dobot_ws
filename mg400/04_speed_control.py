"""
04_speed_control.py — Speed and acceleration control demo.

MG400 speed is set as a percentage (1–100%) rather than absolute mm/s.
Five independent parameters can be tuned:
  SpeedFactor(ratio)  — global motion speed scale (1–100%)
  SpeedJ(ratio)       — joint-space speed (1–100%)
  SpeedL(ratio)       — Cartesian linear speed (1–100%)
  AccJ(ratio)         — joint-space acceleration (1–100%)
  AccL(ratio)         — Cartesian linear acceleration (1–100%)

The demo moves to the same waypoint at three speed levels so you can
compare motion time and smoothness visually.

Usage:
    python 04_speed_control.py [--ip 192.168.2.7]
    python 04_speed_control.py --robot 2
"""

import argparse
import time

from utils_mg400 import (
    connect,
    close_all,
    check_errors,
    go_home,
    safe_move,
    MG400_IP,
    ROBOT_IPS,
)

# Target waypoint for all speed comparisons
WAYPOINT = (280, 80, 60, 10)
HOME_WP  = (300, 0, 50, 0)

# Speed levels to demonstrate
SPEED_LEVELS = [
    {"label": "Low  (10%)", "factor": 10, "j": 10, "l": 10, "aj": 10, "al": 10},
    {"label": "Mid  (30%)", "factor": 30, "j": 30, "l": 30, "aj": 30, "al": 30},
    {"label": "High (70%)", "factor": 70, "j": 70, "l": 70, "aj": 70, "al": 70},
]

# Reset to a conservative safe default when done
SAFE_SPEED = 30


def _set_speed(dashboard, s: dict) -> None:
    """Apply all five speed parameters from a settings dict."""
    dashboard.SpeedFactor(s["factor"])
    dashboard.SpeedJ(s["j"])
    dashboard.SpeedL(s["l"])
    dashboard.AccJ(s["aj"])
    dashboard.AccL(s["al"])


def main():
    parser = argparse.ArgumentParser(description="MG400 speed control demo")
    parser.add_argument("--ip", default=MG400_IP, help="MG400 IP address")
    parser.add_argument("--robot", type=int, choices=[1, 2, 3, 4], metavar="N",
                        help="Robot number 1-4 (overrides --ip)")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    dashboard, move_api, feed = connect(ip)
    try:
        check_errors(dashboard)
        dashboard.EnableRobot()
        print("Connected and enabled.\n")

        # Start from home
        _set_speed(dashboard, SPEED_LEVELS[0])
        go_home(move_api)
        time.sleep(0.5)

        for s in SPEED_LEVELS:
            print(f"--- Speed level: {s['label']} ---")
            _set_speed(dashboard, s)
            print(
                f"  SpeedFactor={s['factor']}%  SpeedJ={s['j']}%  SpeedL={s['l']}%"
                f"  AccJ={s['aj']}%  AccL={s['al']}%"
            )

            # Home → waypoint (MovJ)
            t0 = time.perf_counter()
            safe_move(move_api, *WAYPOINT, mode="J")
            move_api.Sync()
            t1 = time.perf_counter()
            print(f"  MovJ home→waypoint: {t1-t0:.2f} s")

            # Waypoint → home (MovJ)
            t0 = time.perf_counter()
            safe_move(move_api, *HOME_WP, mode="J")
            move_api.Sync()
            t1 = time.perf_counter()
            print(f"  MovJ waypoint→home: {t1-t0:.2f} s")

            # Home → waypoint (MovL — straight-line)
            t0 = time.perf_counter()
            safe_move(move_api, *WAYPOINT, mode="L")
            move_api.Sync()
            t1 = time.perf_counter()
            print(f"  MovL home→waypoint: {t1-t0:.2f} s")

            # Return home
            safe_move(move_api, *HOME_WP, mode="J")
            move_api.Sync()
            time.sleep(0.3)

        print("\nSpeed control demo complete.")

    finally:
        # Reset to safe defaults before disabling
        try:
            dashboard.SpeedFactor(SAFE_SPEED)
            dashboard.SpeedJ(SAFE_SPEED)
            dashboard.SpeedL(SAFE_SPEED)
            dashboard.AccJ(SAFE_SPEED)
            dashboard.AccL(SAFE_SPEED)
        except Exception:
            pass
        try:
            dashboard.DisableRobot()
        except Exception:
            pass
        close_all(dashboard, move_api, feed)
        print("Speed reset to defaults and connections closed.")


if __name__ == "__main__":
    main()
