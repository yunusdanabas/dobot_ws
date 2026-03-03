# Dobot Magician Lab Guide — ME403

A practical guide for using the Python control scripts in this workspace.
Part 1 walks students through each script step by step.
Part 2 covers implementation details for TAs and anyone extending the code.

> **Prerequisites** — Python 3.10+, a USB cable, and the Dobot's wall-power adapter.

---

## Table of Contents

- [Part 1 — Student Guide](#part-1--student-guide)
  - [Environment Setup](#environment-setup)
  - [Script-by-Script Walkthrough](#script-by-script-walkthrough)
  - [Common Workflows](#common-workflows)
  - [Troubleshooting](#troubleshooting)
- [Part 2 — Implementation Details (for TAs)](#part-2--implementation-details-for-tas)
  - [Architecture Overview](#architecture-overview)
  - [Safety System](#safety-system)
  - [Library Tracks](#library-tracks)
  - [Extending the Scripts](#extending-the-scripts)

---

# Part 1 — Student Guide

## Environment Setup

Run these commands once to set up your Python environment:

```bash
cd dobot_ws
python3 -m venv .venv
source .venv/bin/activate          # Linux / macOS
pip install -U pip
pip install pydobotplus pydobot pyserial pynput
```

**Optional Track B setup (`dobot-python`, source checkout):**
```bash
cd /path/for/vendor-code
git clone https://github.com/AlexGustafsson/dobot-python.git
```

**Linux only** — grant serial port access (then log out and back in):

```bash
sudo usermod -a -G dialout $USER
```

**Important:** Close DobotStudio / DobotDemo before running any script.
Only one process can use the serial port at a time.

---

## Script-by-Script Walkthrough

All scripts live in `scripts/`. Always activate your venv and `cd scripts/`
before running them.

```bash
source .venv/bin/activate
cd scripts
```

### 01 — Find the Serial Port

```bash
python 01_find_port.py
```

**What it does:** Lists every serial port on your machine in a table.
The Dobot's CP210x USB chip is marked with `<-- DOBOT`.

**What to expect:**

```
Device               Description                              HWID
------------------------------------------------------------------------------------------
/dev/ttyUSB0         Silicon Labs CP210x                      USB VID:PID=...  <-- DOBOT
```

**What you learn:** How to identify hardware on the USB bus. The port name
(e.g. `/dev/ttyUSB0` on Linux, `COM3` on Windows) is what every other script
needs to connect.

**If nothing appears:** Check the USB cable, make sure the wall-power adapter
is plugged in, and verify you have the `dialout` group permission on Linux.

---

### 02 — First Connection

```bash
python 02_first_connection.py
```

**What it does:** Connects to the Dobot, reads the current Cartesian position
and joint angles, then disconnects.

**What to expect:**

```
Connecting on /dev/ttyUSB0 ...

=== Current Pose (pydobotplus) ===
  Cartesian : X=200.0  Y=0.0  Z=100.0  R=0.0  mm/deg
  Joints    : J1=0.0  J2=45.2  J3=45.2  J4=0.0  deg
```

**What you learn:** The 8-value pose tuple `(x, y, z, r, j1, j2, j3, j4)` is
the robot's primary feedback. Cartesian values are in mm; rotations in degrees.

**Tip:** The file also shows the equivalent API calls for dobot-python (Track B)
and pydobot (Track C) as comments — useful for comparing library syntax.

---

### 03 — Safe Move Demo

```bash
python 03_safe_move_demo.py
```

**What it does:** Moves the robot through 5 positions (forward, left, up,
rotate, home) using the `safe_move()` helper that clamps all coordinates to
safe bounds.

**What to expect:** The robot will move smoothly to each position with a short
pause between moves. The console prints each target:

```
Moving to READY_POSE ...
  Forward  +X     → (230, 0, 100, 0)
  Left     +Y     → (230, 30, 100, 0)
  ...
Demo complete.
```

**What you learn:** How `safe_move()` prevents the robot from reaching
dangerous positions by clamping X, Y, Z, R to predefined bounds. Every motion
script in this workspace uses this pattern.

**Experiment:** Try changing `STEP = 30` to a larger value (e.g. 200) and
watch how clamping caps the actual movement.

---

### 04 — Speed Control

```bash
python 04_speed_control.py
```

**What it does:** Moves the robot between two points at 25%, 50%, and 100% of
the safe speed ceiling. Each pass is timed so you can compare the commanded
speed with the actual achieved speed.

**What to expect:**

```
  Speed  25% → vel=25 mm/s  acc=20 mm/s²
           Wall time: 3.21s  ≈ 25 mm/s achieved  (commanded 25 mm/s)
  Speed  50% → vel=50 mm/s  acc=40 mm/s²
           Wall time: 1.65s  ≈ 48 mm/s achieved  (commanded 50 mm/s)
  Speed 100% → vel=100 mm/s  acc=80 mm/s²
           Wall time: 0.92s  ≈ 87 mm/s achieved  (commanded 100 mm/s)
```

**What you learn:** The difference between commanded and achieved speed comes
from acceleration/deceleration ramps — the robot can't instantly reach its
target velocity. This is a practical demonstration of trapezoidal velocity
profiles.

---

### 05 — End-Effectors

```bash
python 05_end_effectors.py
```

**What it does:** Activates the suction cup or gripper for a timed cycle.

**Before running:** Check which end-effector is physically attached and edit
the `EFFECTOR` variable at the top of the script:

```python
EFFECTOR = "suction"   # "suction" | "gripper"
```

**What to expect:** The suction pump turns on for 2 seconds (you'll hear it),
then off. For the gripper: close for 1.5 seconds, then open.

**What you learn:** The robot cannot auto-detect which end-effector is
attached — you must tell it. The API is simple: `bot.suck(True/False)` for
suction, `bot.grip(True/False)` for the gripper.

---

### 06 — Joint Angles (Live Monitor)

```bash
python 06_joint_angles.py
```

**What it does:** Continuously reads and prints the Cartesian pose and all 4
joint angles at 2 Hz. Press **Ctrl+C** to stop.

**What to expect:**

```
  Time        X       Y       Z       R       J1      J2      J3      J4
----------------------------------------------------------------------
   0.0   200.00    0.00  100.00    0.00    0.00   45.20   45.20    0.00
   0.5   200.00    0.00  100.00    0.00    0.00   45.20   45.20    0.00
```

**What you learn:** The relationship between Cartesian and joint space — move
the robot by hand (if unlocked) or run another script simultaneously and watch
how joint angles change. This is forward kinematics in action.

**Extension — CSV logging:** Set `LOG_TO_CSV = True` at the top of the script
to save every reading to `joint_log.csv`. You can then plot the data in Excel,
MATLAB, or matplotlib to visualise joint trajectories over time.

---

### 07 — Keyboard Teleoperation

```bash
python 07_keyboard_teleop.py
```

**What it does:** Lets you drive the robot in real time from the keyboard.

| Key | Action | Step |
|-----|--------|------|
| Arrow Right / Left | +X / -X | 5 mm |
| Arrow Up / Down | +Y / -Y | 5 mm |
| Page Up / Page Down | +Z / -Z | 5 mm |
| Q / E | +R / -R (rotation) | 5 deg |
| Space | Toggle suction ON/OFF | — |
| H | Go to home (READY_POSE) | — |
| Esc | Quit | — |

**What to expect:** The robot jogs in 5 mm increments as you press keys. The
current position is printed on a single updating line.

**What you learn:** Incremental jogging is how real industrial robots are
taught positions. Use this script to find pick/place coordinates for
`08_pick_and_place.py` — note down the X, Y, Z values from the display.

**Tip:** You can change `STEP = 5` at the top of the script for coarser or
finer control.

---

### 08 — Pick and Place

```bash
python 08_pick_and_place.py
```

**What it does:** Performs a complete pick-and-place cycle using the suction
cup: home → approach pick → descend → suction ON → lift → approach place →
descend → suction OFF → lift → home.

**Before running:** Edit the pick and place coordinates at the top of the script
to match your physical setup:

```python
PICK_X,  PICK_Y,  PICK_Z  = 220, -60, 30
PLACE_X, PLACE_Y, PLACE_Z = 220,  60, 30
LIFT      = 60    # mm above pick/place Z for safe travel
```

**Finding coordinates:** Use `07_keyboard_teleop.py` to jog the robot to the
pick position, note the X/Y/Z values, then repeat for the place position.

**What you learn:** The Z+LIFT approach pattern — always approach from above
to avoid collisions, descend to grip, then lift before traversing. This is a
fundamental industrial robot pattern.

---

## Common Workflows

### First-Time Setup (do once)

1. Run environment setup commands (venv, pip install, dialout)
2. Plug in USB + wall power
3. `python 01_find_port.py` — confirm the robot is detected
4. `python 02_first_connection.py` — confirm you can read the pose

### Teaching a New Pick-and-Place Task

1. `python 07_keyboard_teleop.py` — jog to the pick position, note X/Y/Z
2. Jog to the place position, note X/Y/Z
3. Edit `PICK_X/Y/Z` and `PLACE_X/Y/Z` in `08_pick_and_place.py`
4. `python 08_pick_and_place.py` — run the cycle

### Recording Joint Data for Analysis

1. Set `LOG_TO_CSV = True` in `06_joint_angles.py`
2. `python 06_joint_angles.py` — run while the robot moves (or move it by hand)
3. Press Ctrl+C when done
4. Open `joint_log.csv` in your analysis tool of choice

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| `No serial port found` | Robot not connected or no power | Check USB cable **and** wall-power adapter. Both are required. |
| `Permission denied: '/dev/ttyUSB0'` | Linux serial port permissions | Run `sudo usermod -a -G dialout $USER`, then **log out and back in**. |
| `Port is busy` or connection hangs | Another process owns the port | Close DobotStudio, DobotDemo, or any other Python script using the robot. |
| Robot makes grinding/clicking sounds | Requested position is at the edge of the workspace | Reduce your coordinates. Stay within the safe bounds (see below). |
| Suction not gripping | Vacuum leak or wrong end-effector | Check the suction cup seal. Ensure `EFFECTOR = "suction"` in the script. |
| Script hangs after `move_to` | Missing `wait=True` or robot is stuck | All scripts use `wait=True` by default. If stuck, power-cycle the robot. |
| `ModuleNotFoundError: pydobotplus` | Virtual environment not activated | Run `source .venv/bin/activate` before running scripts. |
| Keyboard teleop keys don't work | Terminal not focused or pynput issue | Click on the terminal window. On Wayland (Linux), pynput may need X11. |

### Safe Bounds Reference

If you see warnings about coordinates being outside bounds, these are the
limits enforced by `safe_move()`:

| Axis | Min | Max | Unit |
|------|-----|-----|------|
| X | 150 | 280 | mm |
| Y | -160 | 160 | mm |
| Z | 10 | 150 | mm |
| R | -90 | 90 | degrees |

---

# Part 2 — Implementation Details (for TAs)

## Architecture Overview

```
scripts/
├── utils.py              ← Shared safety layer (all scripts import from here)
├── 01_find_port.py       ← Port discovery (standalone, no robot connection)
├── 02_first_connection.py ← Minimal connect + read pose
├── 03_safe_move_demo.py  ← Demonstrates safe_move() clamping
├── 04_speed_control.py   ← Speed profiles + wall-clock timing
├── 05_end_effectors.py   ← Suction and gripper control
├── 06_joint_angles.py    ← Live monitoring + optional CSV export
├── 07_keyboard_teleop.py ← Real-time keyboard jogging (pynput)
└── 08_pick_and_place.py  ← Complete pick-and-place template
```

**Design principles:**

- **Single entry point:** Every script (except `utils.py`) has an
  `if __name__ == "__main__": main()` guard, so they can be imported without
  side effects.
- **Guaranteed cleanup:** Every script that opens a Dobot connection wraps it
  in `try/finally` to ensure `bot.close()` is called even on exceptions or
  Ctrl+C.
- **Centralised safety:** All motion goes through `safe_move()` in `utils.py`,
  which clamps coordinates to `SAFE_BOUNDS` before sending them to the robot.
- **Auto port detection:** `find_port()` in `utils.py` searches for
  "Silicon Labs" in port descriptions, with a fallback to the first available
  port.

## Safety System

The safety layer lives entirely in `utils.py`:

```python
# Constants
READY_POSE       = (200, 0, 100, 0)       # Safe home position
SAFE_BOUNDS      = {"x": (150, 280), "y": (-160, 160), "z": (10, 150), "r": (-90, 90)}
SAFE_VELOCITY    = 100                      # mm/s
SAFE_ACCELERATION = 80                      # mm/s²

# Core functions
find_port(keyword)    → str | None     # Auto-detect serial port
clamp(v, lo, hi)      → float          # Clamp value to [lo, hi]
safe_move(bot, x,y,z,r) → None        # Clamp + move_to with wait=True
go_home(bot)          → None           # Move to READY_POSE via safe_move
```

**How `safe_move()` works:** It clamps each axis independently to its bounds
in `SAFE_BOUNDS`, then calls `bot.move_to(x, y, z, r, wait=True)`. This means
a request for `(300, 200, 200, 0)` silently becomes `(280, 160, 150, 0)`.
The clamping is intentionally silent to avoid breaking control loops, but
`08_pick_and_place.py` demonstrates an explicit pre-check pattern (`_check()`)
that warns the user before execution.

**Why these bounds:** The Dobot Magician's kinematic workspace is roughly a
320 mm radius hemisphere. The safe bounds are conservative to keep the arm away
from singularities (X too small), the table surface (Z too low), and joint
limits (R extremes). They can be widened by editing `SAFE_BOUNDS` in `utils.py`
if the physical setup allows it.

## Library Tracks

Three libraries wrap the same USB-serial Dobot protocol (115200 baud, CP210x):

| Track | Library | Import | Pose Method | Move Method | Close |
|-------|---------|--------|-------------|-------------|-------|
| A (default) | pydobotplus | `from pydobotplus import Dobot` | `bot.get_pose()` → `Pose(position, joints)` | `bot.move_to(x,y,z,r, wait=True)` | `bot.close()` |
| B (advanced) | dobot-python (source) | `from lib.interface import Interface` | `bot.get_pose()` → 8-tuple | `bot.set_point_to_point_command(...)` | `bot.serial.close()` |
| C (legacy) | pydobot | `from pydobot import Dobot` | `bot.pose()` → 8-tuple | `bot.move_to(x,y,z,r, wait=True)` | `bot.close()` |

**Why Track A is the default:** `pydobotplus` has the simplest API, handles
connection cleanup properly (`bot.close()`), and covers all Labs 1–4 needs.

**When to use Track B:** use `lib.interface.Interface` when you need explicit
queue control (`set_point_to_point_command(..., queue=True)` plus
`get_current_queue_index()` back-pressure checks) in trajectory labs.

**Track C is reference only.** Its API is older, but cleanup is still explicit
and safe with `bot.close()`.

All scripts use Track A as active code, with Track B and C shown as comments
where relevant.

## Extending the Scripts

### Adding a new script

1. Name it `NN_description.py` following the numbering sequence
2. Import `find_port` and `safe_move` from `utils`
3. Use the standard template:

```python
"""
NN_description.py — One-line description.

Usage:
    python NN_description.py
"""

import sys, time
from pydobotplus import Dobot
from utils import find_port, safe_move, go_home

def main():
    PORT = find_port()
    if PORT is None:
        sys.exit("[Error] No serial port found.")

    bot = Dobot(port=PORT)
    try:
        go_home(bot)
        # ... your code here ...
    finally:
        bot.close()

if __name__ == "__main__":
    main()
```

### Built-in extension points

- **04_speed_control.py** — already times each speed profile. Students can add
  more speed percentages or plot the velocity-vs-time curve.
- **06_joint_angles.py** — set `LOG_TO_CSV = True` to export data. Students
  can extend this to log while another script moves the robot (run in two
  terminals on the same port won't work — instead, integrate the logging loop
  into the motion script).
- **08_pick_and_place.py** — the `pick_up()` / `place_down()` functions are
  reusable primitives. A multi-object sorting task can call them in a loop
  with different coordinates.

### Conventions to follow

- Never call `bot.move_to()` directly — always use `safe_move()` from utils
- Always use `wait=True` (or the safe_move default) to prevent command flooding
- Always wrap the robot connection in `try/finally` for `bot.close()`
- Use `find_port()` for port discovery, never hardcode port strings
- Keep the `EFFECTOR`, `PICK_X/Y/Z`, `STEP` etc. as constants at the top of
  the file so students can edit them without reading the whole script

---

*For detailed API reference, hardware specs, and advanced queue patterns, see
[dobot_control_options_comparison.md](./dobot_control_options_comparison.md).*
