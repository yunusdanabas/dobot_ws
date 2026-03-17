# Scripts Index

This folder is organized into two groups:

## 1) Numbered lab scripts (student-facing)

Run these in order:
- `01_find_port.py`
- `02_first_connection.py`
- `03_safe_move_demo.py`
- `04_speed_control.py`
- `05_end_effectors.py`
- `06_joint_angles.py`
- `07_keyboard_teleop.py`
- `08_pick_and_place.py`
- `09_arc_motion.py`
- `10_circle_queue.py`
- `11_circle_arcs.py`
- `12_motion_modes.py`
- `13_relative_moves.py`
- `14_sensors_io.py`
- `15_record_pose.py`
- `17_visualizer.py`
- `18_joint_control.py`
- `19_relative_joint_control.py`

Notes:
- `16_*` is intentionally unused (legacy gap kept for course continuity).
- `07_keyboard_teleop.py` is the canonical teleop entrypoint on both Ubuntu and Windows.
- On Windows you can override auto-detection with `DOBOT_PORT`; the full PowerShell workflow lives in [`../windows/README.md`](../windows/README.md).

## 2) Shared helpers used by numbered scripts

- `utils.py` - safety helpers, bounds, port detection, alarms
- `viz.py` - `RobotViz` utility used by selected scripts
