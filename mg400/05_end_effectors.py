"""
05_end_effectors.py — Digital I/O demo for suction cup and gripper.

MG400 I/O control via dashboard commands (no dedicated suck() method):
  dashboard.ToolDO(index, status)    — tool output (end-effector board)
  dashboard.DO(index, status)        — base controller output
  dashboard.ToolDI(index)            — read tool digital input
  dashboard.DI(index)                — read base digital input

Typical wiring:
  Tool DO index 1  → suction pump relay (1=ON, 0=OFF)
  Tool DO index 2  → gripper open/close (1=CLOSE, 0=OPEN)
  Base DO index 1  → external indicator / solenoid

Edit I/O indices to match your hardware.

Usage:
    python 05_end_effectors.py [--ip 192.168.2.7]
    python 05_end_effectors.py --robot 2
"""

import argparse
import time

from utils_mg400 import (
    add_target_arguments,
    close_all,
    check_errors,
    connect_from_args_or_exit,
    go_home,
    SPEED_DEFAULT,
)

# I/O index mapping — adjust to match your wiring
SUCTION_DO   = 1    # tool digital output for suction pump
GRIPPER_DO   = 2    # tool digital output for gripper
BASE_DO      = 1    # base digital output (indicator / solenoid)
TOOL_DI_IDX  = 1    # tool digital input (vacuum sensor if present)
BASE_DI_IDX  = 1    # base digital input (limit switch if present)


def _print_di(dashboard) -> None:
    """Read and print available digital inputs."""
    try:
        tool_di = dashboard.ToolDI(TOOL_DI_IDX)
        print(f"    ToolDI({TOOL_DI_IDX}) = {tool_di.strip()}")
    except Exception as exc:
        print(f"    ToolDI({TOOL_DI_IDX}) : (unavailable — {exc})")
    try:
        base_di = dashboard.DI(BASE_DI_IDX)
        print(f"    DI({BASE_DI_IDX})     = {base_di.strip()}")
    except Exception as exc:
        print(f"    DI({BASE_DI_IDX})     : (unavailable — {exc})")


def main():
    parser = argparse.ArgumentParser(description="MG400 end-effector I/O demo")
    add_target_arguments(parser)
    args = parser.parse_args()
    _, dashboard, move_api, feed = connect_from_args_or_exit(args)

    try:
        check_errors(dashboard)
        dashboard.EnableRobot()
        dashboard.SpeedFactor(SPEED_DEFAULT)
        print("Connected and enabled.\n")

        go_home(move_api)
        time.sleep(0.5)

        # --- Suction demo ---
        print("[Demo 1] Suction pump (ToolDO index 1)")
        print("  Suction ON ...")
        dashboard.ToolDO(SUCTION_DO, 1)
        time.sleep(0.5)
        _print_di(dashboard)   # check vacuum sensor if available

        print("  Suction OFF ...")
        dashboard.ToolDO(SUCTION_DO, 0)
        time.sleep(0.5)
        _print_di(dashboard)

        # --- Gripper demo ---
        print("\n[Demo 2] Gripper (ToolDO index 2)")
        print("  Gripper CLOSE ...")
        dashboard.ToolDO(GRIPPER_DO, 1)
        time.sleep(0.8)   # allow gripper to close mechanically

        print("  Gripper OPEN ...")
        dashboard.ToolDO(GRIPPER_DO, 0)
        time.sleep(1.8)

        # --- Base digital output demo ---
        print("\n[Demo 3] Base digital output (DO index 1)")
        print("  Base DO ON ...")
        dashboard.DO(BASE_DO, 1)
        time.sleep(0.5)

        print("  Base DO OFF ...")
        dashboard.DO(BASE_DO, 0)
        time.sleep(0.3)

        print("\nEnd-effector I/O demo complete.")
        print("Edit I/O indices at the top of this file to match your wiring.")

    finally:
        # Safety: ensure all outputs are de-asserted on exit
        for idx in (SUCTION_DO, GRIPPER_DO):
            try:
                dashboard.ToolDO(idx, 0)
            except Exception:
                pass
        try:
            dashboard.DO(BASE_DO, 0)
        except Exception:
            pass
        try:
            dashboard.DisableRobot()
        except Exception:
            pass
        close_all(dashboard, move_api, feed)
        print("All outputs de-asserted, connections closed.")


if __name__ == "__main__":
    main()
