# Dobot Magician Basics

Minimal starter scripts for Dobot Magician (no visualization tools).

## Libraries in this folder

- `pydobotplus` (main): `Dobot`, `get_pose`, `move_to`, `home`, `speed`, `suck`, `grip`, `get_alarms`, `clear_alarms`, `close`
- `pyserial` (indirect): serial port discovery
- `pydobot` and `dobot-python`: kept in the workspace for reference/advanced use, not used by these scripts

## Shared helpers used

These scripts reuse `scripts/utils.py`:
- `find_port`
- `unpack_pose`
- `prepare_robot`
- `go_home`
- `safe_move`
- `SAFE_READY_POSE`

## Run order

1. `01_connect_and_pose.py`
2. `02_home_and_ready.py`
3. `03_simple_moves.py`
4. `04_tool_control.py`

## Run

From workspace root:

```bash
python basics/01_connect_and_pose.py
python basics/02_home_and_ready.py
python basics/03_simple_moves.py
python basics/04_tool_control.py
```

## Notes

- Keep DobotStudio closed while running Python scripts.
- Only one process can own the serial port at a time.
- Use small motion steps first.
