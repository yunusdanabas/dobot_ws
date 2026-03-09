# Motion Modes Reference — Dobot Magician

## MODE_PTP Enum (pydobotplus / ZdenekM/pydobot)

```python
from pydobotplus import MODE_PTP
```

| Value | Name | Path type | Best for |
|-------|------|-----------|----------|
| 0 | JUMP_XYZ | Lift → Travel → Lower | Pick-and-place (firmware auto-lift) |
| 1 | MOVJ_XYZ | Joint interpolation | Fast transit between points |
| 2 | MOVL_XYZ | Straight-line Cartesian | Drawing, writing, surface scanning |
| 3 | MOVR_XYZ | Relative Cartesian linear | Incremental absolute moves |
| 4 | MOVJ_ANGLE | Joint-space by angle | Teaching/replay by joint values |
| 5 | MOVR_ANGLE | Relative joint-space | Fine joint adjustments |
| 6 | MOVJ_INC | Joint incremental | Small joint nudges |
| 7 | MOVL_INC | Linear incremental | Small Cartesian nudges |
| 8 | MOVJ_XYZ_INC | Joint incremental (Cartesian) | — |
| 9 | JUMP_MOVL_XYZ | Lift → Straight-line → Lower | Precision pick-and-place |

---

## Decision Guide

**Use MOVJ_XYZ when** you want the fastest move between two points and the
end-effector path shape does not matter. Joint interpolation curves through
space and is the default mode in pydobotplus and ZdenekM/pydobot.

**Use MOVL_XYZ when** the end-effector must travel in a straight Cartesian
line. Required for drawing, writing, and surface scanning. This is the
default mode in luismesas/pydobot (Track C), so Track C scripts already
produce straight-line paths without specifying a mode.

**Use JUMP_XYZ when** you are doing pick-and-place and want the firmware to
handle the Z-lift automatically. Configure the clearance height once with
`_set_ptp_jump_params()` and the robot will lift, travel, and lower without
manual LIFT coordinates in the script.

---

## JUMP Clearance Configuration

```python
bot._set_ptp_jump_params(jump=30, limit=120)
# jump  — Z clearance added above start and end Z (mm)
# limit — maximum absolute Z the arm may reach during the jump (mm)
```

Call this once after connecting, before any `JUMP_XYZ` or `JUMP_MOVL_XYZ` moves.
`JUMP_HEIGHT = 30` in `utils.py` is the course default.

---

## Code Examples

### MOVJ_XYZ (joint interpolation — default)

```python
from pydobotplus import MODE_PTP
from utils import safe_move

safe_move(bot, 220, 0, 80, 0, mode=MODE_PTP.MOVJ_XYZ)
# Equivalent to safe_move(bot, 220, 0, 80, 0) — MOVJ is the library default
```

### MOVL_XYZ (straight-line — required for drawing)

```python
safe_move(bot, 220, 0, 80, 0, mode=MODE_PTP.MOVL_XYZ)
```

### JUMP_XYZ (firmware auto-lift — simplest pick-and-place)

```python
from pydobotplus import MODE_PTP
from utils import safe_move, JUMP_HEIGHT

bot._set_ptp_jump_params(jump=JUMP_HEIGHT, limit=120)  # configure once

safe_move(bot, PICK_X,  PICK_Y,  PICK_Z,  0, mode=MODE_PTP.JUMP_XYZ)
bot.suck(True)
safe_move(bot, PLACE_X, PLACE_Y, PLACE_Z, 0, mode=MODE_PTP.JUMP_XYZ)
bot.suck(False)
```

No manual lift/descend coordinates needed — the firmware handles the Z arc.

---

## Default Mode Difference Between Libraries

| Library | Default PTP mode | End-effector path |
|---------|-----------------|-------------------|
| pydobotplus (Track A) | MOVJ_XYZ | Curved (joint interpolation) |
| ZdenekM/pydobot | MOVJ_XYZ | Curved (joint interpolation) |
| luismesas/pydobot (Track C) | MOVL_XYZ | Straight Cartesian line |

This is a critical difference: identical coordinates produce **different
end-effector paths** on Track A vs Track C. If you need straight-line paths
with Track A (pydobotplus), always pass `mode=MODE_PTP.MOVL_XYZ` explicitly.

---

## Live Demo

`scripts/12_motion_modes.py` traces the same 3-point path with MOVJ and then
MOVL back-to-back so the path difference is visible, then demonstrates JUMP.

---

## Alarm Codes Overview

pydobotplus exposes ~80 named alarm codes via the `Alarm` enum. The most
common student-facing ones:

| Code name (example) | Likely cause |
|--------------------|--------------|
| `JOINT1_FOLLOWING_ERROR` | Joint 1 skipped steps (move too fast or load too high) |
| `JOINT2_FOLLOWING_ERROR` | Same for J2 |
| `OVER_SPEED_JOINT` | Velocity limit exceeded |
| `POSE_LIMIT_OVER` | Target pose outside firmware workspace |
| `MOTOR_HOT` | Overheating from sustained high load |

Use `check_alarms(bot)` from `utils.py` after connecting to print and clear
any active alarms by name before running motion code.
