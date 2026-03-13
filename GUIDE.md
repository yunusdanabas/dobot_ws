# Dobot Magician Lab Guide — ME403

A practical guide for using the Python control scripts in this workspace.
Part 1 walks students through each script step by step.
Part 2 covers implementation details for TAs and anyone extending the code.

> **Prerequisites** — Python 3.10+, a USB cable, and the Dobot's wall-power adapter.

---

## Table of Contents

- [Part 1 — Student Guide](#part-1--student-guide)
  - [Physical Setup](#physical-setup)
  - [Environment Setup](#environment-setup)
  - [Script-by-Script Walkthrough](#script-by-script-walkthrough) (01–15, 17–19)
  - [Common Workflows](#common-workflows)
  - [Troubleshooting](#troubleshooting)
- [Part 2 — Implementation Details (for TAs)](#part-2--implementation-details-for-tas)
  - [Architecture Overview](#architecture-overview)
  - [Safety System](#safety-system)
  - [Library Tracks](#library-tracks)
  - [Extending the Scripts](#extending-the-scripts)
- [Additional References](#additional-references)

---

# Part 1 — Student Guide

## Physical Setup

Before powering on the Dobot Magician:

1. **Neutral posture** — set the Forearm and Rear Arm each to approximately 45° before
   applying wall power. Powering on from an extreme position can trigger joint faults.
2. **Wall adapter required** — USB bus power alone is not enough; always plug in the
   dedicated wall-power adapter first.
3. **Readiness signal** — the LED turns steady and the robot beeps once when it is ready
   to accept commands. Three rapid beeps at startup indicate a fault — check the arm posture
   and run `check_alarms(bot)` after connecting.
4. **Connector map:**

   | Connector | Purpose |
   |-----------|---------|
   | SW1 | Tool power (suction pump, laser) |
   | GP1 / GP3 | Sensor port (IR proximity, color sensor) |
   | SW4 | Gripper port |

---

## Environment Setup

Run these commands once to set up your Python environment:

**Option A — mamba (recommended):**
```bash
cd dobot_ws
mamba create -n dobot python=3.10 -y
mamba activate dobot
pip install -U pip
pip install -r requirements.txt
```

**Option B — venv:**
```bash
cd dobot_ws
python3 -m venv .venv
source .venv/bin/activate          # Linux / macOS
pip install -U pip
pip install -r requirements.txt
```

**Optional Track B setup** (for script 10 only):

Clone into `vendor/` for automatic discovery:
```bash
cd dobot_ws
git clone https://github.com/AlexGustafsson/dobot-python.git vendor/dobot-python
```
Or clone elsewhere and set `export DOBOT_PYTHON_PATH=/path/to/dobot-python`.

**Linux only** — grant serial port access (then log out and back in):

```bash
sudo usermod -a -G dialout $USER
```

**Important:** Close DobotStudio / DobotDemo before running any script.
Only one process can use the serial port at a time.

---

## Script-by-Script Walkthrough

All scripts live in `magician/`. Always activate your environment and `cd magician/`
before running them.

```bash
mamba activate dobot
# or: source .venv/bin/activate
cd magician
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
Moving to home ...
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

**What it does:** Lets you drive the robot in real time from the keyboard using
continuous hold-to-move: hold a direction key for smooth motion instead of
discrete steps.

| Key | Action | Effect |
|-----|--------|--------|
| Arrow Right/Left or D/A | +X / -X | Hold to move continuously |
| Arrow Up/Down or W/S | +Y / -Y | Hold to move continuously |
| R / F | +Z / -Z (raise/fall) | Hold to move continuously |
| Q / E | +R / -R (rotation) | Hold to rotate continuously |
| Space | Toggle suction ON/OFF | — |
| H | Go to joint home (0,0,0,0) | — |
| Esc | Quit | — |

**What to expect:** Hold a direction key for continuous motion. The robot moves
smoothly at about 80 mm/s (X/Y/Z) and 45 deg/s (R). The current position is
printed on a single updating line.

**What you learn:** Hold-to-move jogging is how many industrial teach pendants
work. Use this script to find pick/place coordinates for `08_pick_and_place.py` —
note down the X, Y, Z values from the display.

**Tip:** Tune `JOG_VELOCITY_MM`, `JOG_VELOCITY_DEG`, `LOOP_HZ`, and `CMD_HZ` at
the top of the script for different smoothness and responsiveness.

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

### 09 — Arc Motion

```bash
python 09_arc_motion.py
```

**What it does:** Demonstrates two ways to draw curves: a single arc using
`go_arc()`, and full circles by sampling points around the circumference.

**What to expect:**
- Demo 1: A single arc from (200,0) to (250,50) via an intermediate point
- Demo 2: A full circle (radius 40 mm, 36 points) centered at (220, 0)
- Demo 3: A smaller, faster circle (radius 25 mm, 24 points)

**What you learn:** The `go_arc()` function takes an endpoint and a via-point
(an intermediate waypoint **on** the arc, not the center). Sampled-point
circles use basic trigonometry — `x = cx + r*cos(theta)` — and are the
recommended approach for labs because they work reliably on all firmware.

**Experiment:** Change the `radius` or `steps` parameter in `draw_circle()`
to see how resolution affects smoothness.

---

### 10 — Circle via Queue Commands (Track B, Advanced)

```bash
python 10_circle_queue.py
```

**What it does:** Draws circles using the Track B `Interface` library, which
queues many small linear moves and monitors execution with
`get_current_queue_index()` back-pressure.

**Prerequisites:** Requires the `dobot-python` source checkout. If cloned to
`vendor/dobot-python` (see Environment Setup), the script finds it automatically.
Otherwise set `export DOBOT_PYTHON_PATH=/path/to/dobot-python`.

**What to expect:** Three circles at different resolutions (36, 72, 24
points). The script prints queue progress while the robot draws.

**What you learn:** Queue-based motion control — how industrial robots
buffer commands ahead of execution. The back-pressure loop
(`while current_idx < last_idx`) prevents the command queue from overflowing.

---

### 11 — Circle from Arc Segments

```bash
python 11_circle_arcs.py
```

**What it does:** Decomposes a full circle into N arc segments using
`go_arc()`. Tests with 4 arcs (90 each), 8 arcs (45 each), and 12 arcs
(30 each) so you can see the quality difference.

**What to expect:**
```
TEST 1: 4 arcs  → noticeable angular steps at 90° intervals
TEST 2: 8 arcs  → smooth, good balance of quality and speed
TEST 3: 12 arcs → visually indistinguishable from a true circle
TEST 4: smaller circle (radius 25 mm) with 8 arcs
```

**What you learn:** The via-point formula for arc decomposition:
```
via_angle = 2pi * (i + 0.5) / N   (midpoint of the arc)
end_angle = 2pi * (i + 1) / N     (endpoint)
```
The via-point is placed **on the circle** at the midpoint angle — not at the
center. This is the key insight for using `go_arc()` to trace arbitrary curves.

**Experiment:** Change `num_arcs` in `draw_circle_arcs()` to compare 4, 6, 8,
and 12 segments. More arcs = smoother but slower.

---

### 12 — Motion Modes

```bash
python 12_motion_modes.py
```

**What it does:** Traces the same 3-point path with MOVJ_XYZ (joint
interpolation) and then MOVL_XYZ (straight-line Cartesian), then demonstrates
JUMP_XYZ (firmware auto-lift) between two points.

**What to see:** In Demo 1 the end-effector arcs through space; in Demo 2 it
travels in straight lines between the same waypoints. Demo 3 shows the robot
lifting automatically without any manual LIFT coordinate in the script.

**What you learn:**
- MOVJ is the default (fastest, curved path)
- MOVL is required for drawing, writing, or surface scanning
- JUMP is the simplest pattern for pick-and-place — the firmware handles the Z-lift

**See also:** `docs/motion_modes.md` for the full MODE_PTP reference.

---

### 13 — Relative Moves

```bash
python 13_relative_moves.py
```

**What it does:** Demonstrates `safe_rel_move()` for incremental motion, then
replays the pick-and-place from script 08 using relative moves instead of
explicit absolute coordinates.

**What to see:** In Demo 1, four small relative adjustments move the robot around
a square and back. In Demo 2, the pick-and-place runs with no LIFT constant —
only `dz=-APPROACH_HEIGHT` and `dz=+APPROACH_HEIGHT`.

**What you learn:** Relative moves reduce the number of coordinate constants you
need to compute. `safe_rel_move(bot, dz=-50)` reads as "go 50 mm down" rather
than requiring you to know the current absolute Z.

---

### 14 — Sensors & I/O

```bash
python 14_sensors_io.py
```

**Before running:** Connect the IR sensor to GP1 and/or the color sensor to GP3.

**What it does:** Polls the IR proximity sensor, reads the dominant color channel
from the color sensor, toggles a digital I/O pin, then performs an
IR-triggered pick-and-place.

**What to see:**
- Demo 1: wave your hand near the IR sensor and watch `DETECTED` appear
- Demo 2: hold a red, green, or blue object near the color sensor to see it identified
- Demo 4: place an object at the pick site and the robot will pick it automatically

**What you learn:** How to integrate simple sensors into a reactive robot loop.
The IR-triggered pick (Demo 4) is the pattern used in conveyor-sorting tasks.

---

### 15 — Pose Recorder

```bash
python 15_record_pose.py
```

**What it does:** Interactively records the robot's current Cartesian pose each
time you press Enter, then writes all captured poses to `poses.py`.

**What to see:**

```
[Pose Recorder]
  Press Enter to capture pose 1 (Ctrl+C to finish):
  [1] x=220.3  y=-58.1  z=31.4  r=0.0   j1=22.1  j2=45.3  j3=10.2  j4=0.0  -> saved
  Press Enter to capture pose 2 (Ctrl+C to finish):
^C
[Done] 1 pose(s) written to poses.py
  POSE_1 = (220.3, -58.1, 31.4, 0.0)
```

**What you learn:** How to capture coordinates directly from the robot instead
of calculating or estimating them. Paste the constants from `poses.py` directly
into `08_pick_and_place.py`.

**Workflow:** Position the robot using `07_keyboard_teleop.py`, DobotStudio,
or by hand, then close that tool and press Enter here. `15_record_pose.py`
briefly connects for each capture and releases the port again.

---

### 17 — Live Visualizer (Standalone Demo)

```bash
python 17_visualizer.py
```

**What it does:** Opens the same dual-view 2D visualization used by the motion
scripts: a top-down XY view plus a front XZ view showing the live end-effector
position. Reads `get_pose()` in a loop at 2 Hz, prints the pose table, and
forwards each reading to the visualizer via `viz.send()`.

**What to see:** A red dot moves inside the yellow workspace boundary as the
robot moves. A trail accumulates showing the path history — it fades from dim
(oldest) to bright (most recent) so you can see the direction of travel.
The left pane is a top-down XY view; the right pane is a front XZ view
(reach vs. height). The status bar shows the current X/Y/Z/R and the total
move count. Press **C** in the window at any time to clear the trail.

**What you learn:** How `viz.py` works independently as a standalone,
single-owner pose monitor. This script demonstrates the polled-pose path of
the `RobotViz` API: `RobotViz()` → `send()` → `close()`. Motion scripts add
`attach(bot)` when they want commanded moves forwarded automatically.

**Disabling the visualizer:** Any script that imports `RobotViz` can have
the visualizer suppressed without code changes:

```bash
DOBOT_VIZ=0 python 07_keyboard_teleop.py
python 07_keyboard_teleop.py --no-viz
```

**Note:** Only one process can own the serial port. Close this script before
running any other script that connects to the robot.

---

### 18 — Interactive Joint-Angle Control

```bash
python 18_joint_control.py
```

**What it does:** Opens an interactive REPL that lets you command the robot by
joint angles (J1–J4 in degrees) instead of Cartesian coordinates. Before each
move it displays the predicted Cartesian position via forward kinematics (FK),
executes the move with `MOVJ_ANGLE` mode, then reads back the actual achieved
pose so you can compare prediction vs. reality.

**REPL commands:**

| Input | Action |
|-------|--------|
| `j1 j2 j3 j4` | Move to these joint angles (degrees) |
| `r` | Read and print the current pose (Cartesian + joints) |
| `h` | Go to joint home (0,0,0,0) |
| `q` | Quit |

**What you learn:** How joint-space commands differ from Cartesian commands,
how the Dobot's parallel linkage determines FK (forearm angle = J2 + J3), and
where joint limits sit relative to the Cartesian workspace.

**FK model used:**
```
reach  = L1·cos(J2) + L2·cos(J2+J3)   # L1=135 mm, L2=147 mm
height = L1·sin(J2) + L2·sin(J2+J3)
X = reach·cos(J1),   Y = reach·sin(J1)
```

**Joint bounds enforced:** J1 ±90°, J2 0–85°, J3 −10–85°, J4 ±90°.
Values outside these bounds are clamped with a warning.

**Options:**
- Set `LOG_TO_CSV = True` in the script to write every move to `joint_log_18.csv`
  (columns: timestamp, commanded joints, FK prediction, actual Cartesian + joints)

---

### 19 — Body-Frame Relative Joint-Angle Control

```bash
python 19_relative_joint_control.py [--viz]
```

**What it does:** Extends script 18 with a *relative (body-frame)* input
convention. Students enter J1–J4 as body-frame offsets (each joint measured
from the previous link's direction), and the script converts them through the
full FK transformation chain before moving the robot.

**Why the distinction matters:** In script 18, J3 is entered as a firmware
angle that happens to be a body-frame offset for the Magician, but J4 must be
an absolute wrist angle. Script 19 makes all inputs consistently body-frame and
performs the conversion explicitly, so students see the chain that the firmware
would otherwise hide.

**Terminal output per move:**

```
Relative:  J1_rel=   0.00  J2_rel=  20.00  J3_rel=  10.00  J4_rel=   0.00
Absolute:  j1_abs=   0.00  j2_abs=  20.00  j3_abs=  30.00  j4_abs=  30.00
Firmware:  j1_fw=    0.00  j2_fw=   20.00  j3_fw=   10.00  j4_fw=   30.00
[FK]       X= 254.17  Y=   0.00  Z= 119.72  R= 30.00
```

**Conversion functions:**

```python
def rel_to_abs_magician(j1_r, j2_r, j3_r, j4_r):
    j3_abs = j2_r + j3_r           # accumulated elbow angle
    j4_abs = j3_abs + j4_r         # accumulated wrist angle
    fw_tuple  = (j1_r, j2_r, j3_r, j4_abs)    # j3_fw = j3_rel (trivial)
    abs_tuple = (j1_r, j2_r, j3_abs, j4_abs)
    return fw_tuple, abs_tuple

def fw_to_rel_magician(j1_fw, j2_fw, j3_fw, j4_fw):
    return j1_fw, j2_fw, j3_fw, j4_fw - (j2_fw + j3_fw)
```

**Prompt** shows both Abs and Rel current state. **Bounds** are applied to
firmware angles (`clamp_fw_joints()`), not to the relative inputs.

**Options:**
- `--viz` enables the `RobotViz` dual-view visualizer
- Set `LOG_TO_CSV = True` for `joint_log_19.csv` (rel + abs + fw + FK + actual)

---

## Common Workflows

### First-Time Setup (do once)

1. Run environment setup commands (mamba or venv, `pip install -r requirements.txt`, dialout)
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

### Real-Time Visualization

Integrated visualization is built into scripts 07–09, 12, and 13. Script 17
uses the same `viz.py` window as a standalone pose monitor. All of these
require `pyqtgraph` and `PyQt5` from `requirements.txt`.

To **disable** without changing the script:
```bash
DOBOT_VIZ=0 python 08_pick_and_place.py
python 08_pick_and_place.py --no-viz
```

To **extend the trail** for dense paths (e.g. full circles):
```bash
DOBOT_TRAIL=1000 python 09_arc_motion.py   # default is 500 points
```

To **add to a new script** (3 lines):
```python
from viz import RobotViz
viz = RobotViz(); viz.attach(bot)   # after bot = Dobot(...)
# ... motion code unchanged ...
viz.close()                          # in finally, before bot.close()
```

**While the window is open:** press **C** to clear the trail without restarting.
The status bar always shows the current X/Y/Z/R and the total move count.

There is no shared-port passive monitor: only one process can own the serial
port at a time. Use `17_visualizer.py` when pose polling and visualization are
the only thing you want running.

### Pose Recording Workflow

Use this instead of writing down coordinates by hand:

1. Run `python 15_record_pose.py` — it waits for Enter and only connects during each capture
2. Position the robot using `07_keyboard_teleop.py`, DobotStudio, or by hand
3. Close that tool so the recorder can own the serial port
4. Press **Enter** — the current pose is saved, then the port is released again
5. Repeat for each position, then press **Ctrl+C**
6. `poses.py` is written in the current directory — paste the constants into
   your pick-and-place script

### Motion Mode Quick Reference

| Mode | API constant | Path | When to use |
|------|-------------|------|-------------|
| Joint interpolation | `MODE_PTP.MOVJ_XYZ` | Curved | Default — fast transit |
| Straight-line | `MODE_PTP.MOVL_XYZ` | Straight | Drawing, writing, scanning |
| Auto-lift | `MODE_PTP.JUMP_XYZ` | Lift–travel–lower | Pick-and-place |

```python
from pydobotplus import MODE_PTP
from utils import safe_move

safe_move(bot, x, y, z, r, mode=MODE_PTP.MOVL_XYZ)   # straight line
safe_move(bot, x, y, z, r, mode=MODE_PTP.JUMP_XYZ)   # auto-lift
```

See `docs/motion_modes.md` for the full 10-mode table and configuration details.

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| `No serial port found` | Robot not connected or no power | Check USB cable **and** wall-power adapter. Both are required. |
| `Permission denied: '/dev/ttyUSB0'` | Linux serial port permissions | Run `sudo usermod -a -G dialout $USER`, then **log out and back in**. |
| `Port is busy` or connection hangs | Another process owns the port | Close DobotStudio, DobotDemo, or any other Python script using the robot. |
| Robot makes grinding/clicking sounds | Requested position is at the edge of the workspace | Use `bounds=CONSERVATIVE_BOUNDS` in `safe_move()`, or reduce coordinates. See "Avoiding limits" below. |
| `LIMIT_AXIS*` alarms, position ~(19,0,-10) | Robot not homed after power-on | Run `do_homing(bot)` before any motion. See "Homing after power-on" below. |
| Suction not gripping | Vacuum leak or wrong end-effector | Check the suction cup seal. Ensure `EFFECTOR = "suction"` in the script. |
| Script hangs after `move_to` | Missing `wait=True` or robot is stuck | All scripts use `wait=True` by default. If stuck, power-cycle the robot. |
| `ModuleNotFoundError: pydobotplus` | Virtual environment not activated | Run `mamba activate dobot` or `source .venv/bin/activate` before running scripts. |
| `ModuleNotFoundError: PyQt5` or `pyqtgraph` | Packages not installed | Run `pip install pyqtgraph PyQt5` inside your active environment, or use `pip install -r requirements.txt`. |
| Visualizer window doesn't open | Viz disabled or Qt import failed | Ensure you did not pass `--no-viz` or set `DOBOT_VIZ=0`. Run `python -c "import pyqtgraph, PyQt5"` to verify Qt. |
| Keyboard teleop keys don't work | Terminal not focused | Click the terminal window so it has focus. The script reads keys directly from the terminal (works on Wayland and X11). |
| `Position(x=..., y=..., z=..., r=...)` printed on every move | pydobotplus upstream debug print | Fixed automatically: importing `utils` patches `Dobot.move_to` to suppress the print and the unnecessary `get_pose()` call it contained. No action needed. |
| Keyboard teleop overshoots after releasing a key | Queued commands still executing | Fixed: releasing a key now flushes the robot command queue (`stop_exec → clear → start_exec`). If you still see it, check RELEASE_THRESHOLD in the script. |

### Safe Bounds Reference

If you see warnings about coordinates being outside bounds, these are the
limits enforced by `safe_move()`:

| Axis | Min | Max | Unit |
|------|-----|-----|------|
| X | 120 | 315 | mm |
| Y | -158 | 158 | mm |
| Z | 5 | 155 | mm |
| R | -90 | 90 | degrees |

### Homing after power-on (LIMIT_AXIS alarms)

**Power-on position is NOT home.** The robot must be homed to establish its
coordinate frame before motion. If you see `LIMIT_AXIS23_NEG`, `LIMIT_AXIS3_POS`,
or similar, and the robot reports position (19, 0, -10) instead of (200, 0, 100):

```python
from utils import do_homing

bot = Dobot(port=PORT)
do_homing(bot)   # Run homing sequence (~15-30 s)
# then run your motion script
```

`03_safe_move_demo.py` runs homing automatically when limit alarms are present
at startup. For other scripts, call `do_homing(bot)` once after connecting.

### Avoiding limits (POSE_LIMIT_OVER)

If the robot hits limits (grinding, not reaching target, or `[safe_move] LIMIT:`
warnings), use tighter bounds:

```python
from utils import safe_move, CONSERVATIVE_BOUNDS

# Stay well inside reachable workspace
safe_move(bot, x, y, z, r, bounds=CONSERVATIVE_BOUNDS)

# Verify each move reached target (warns if not)
safe_move(bot, x, y, z, r, bounds=CONSERVATIVE_BOUNDS, verify=True)
```

`CONSERVATIVE_BOUNDS` is x:(170,250), y:(-120,120), z:(30,120), r:(-60,60).
Call `check_alarms(bot)` after connecting to clear any limit alarms before motion.

---

# Part 2 — Implementation Details (for TAs)

## Architecture Overview

```
magician/
├── README.md             ← Script grouping: numbered labs vs support files
├── utils.py              ← Shared safety layer (all scripts import from here)
├── 01_find_port.py       ← Port discovery (standalone, no robot connection)
├── 02_first_connection.py ← Minimal connect + read pose
├── 03_safe_move_demo.py  ← Demonstrates safe_move() clamping
├── 04_speed_control.py   ← Speed profiles + wall-clock timing
├── 05_end_effectors.py   ← Suction and gripper control
├── 06_joint_angles.py    ← Live monitoring + optional CSV export
├── 07_keyboard_teleop.py ← Real-time keyboard jogging (stdin)
├── 08_pick_and_place.py  ← Complete pick-and-place template
├── 09_arc_motion.py      ← Arc motion + sampled circle drawing (Track A)
├── 10_circle_queue.py    ← High-throughput circle via queue (Track B)
├── 11_circle_arcs.py     ← Circle decomposition into N arc segments
├── 12_motion_modes.py    ← MOVJ vs MOVL vs JUMP demo
├── 13_relative_moves.py  ← safe_rel_move() / relative pick-and-place
├── 14_sensors_io.py      ← IR sensor, color sensor, digital I/O
├── 15_record_pose.py     ← Pose recorder with reconnect-per-capture workflow
├── 17_visualizer.py      ← Live pose monitor + RobotViz standalone demo
├── 18_joint_control.py   ← Interactive J1–J4 REPL: FK preview, MOVJ_ANGLE, CSV log
├── 19_relative_joint_control.py ← Body-frame relative angle REPL: conversion chain, FK, viz
├── pyqtgraph_helpers.py  ← Shared QThread polling helper for standalone viz examples
└── viz.py                ← RobotViz utility: dual-view 2D visualizer (spawn subprocess, PyQt5)

docs/                     ← API reference and circle math guides
├── README.md             ← Canonical docs index
├── pydobotplus_api_reference.md
├── pydobotplus_api_detailed.md
├── safe_move_patterns.md
├── arc_and_circles.md
├── circle_drawing_index.md
├── circle_drawing_math.md
├── circle_arc_math_reference.md
└── motion_modes.md       ← MODE_PTP complete reference

mg400/                    ← MG400 parallel workspace (TCP/IP, 440 mm reach)
├── utils_mg400.py        ← Shared helpers: connect(), safe_move(), parse_pose(), check_errors()
├── viz_mg400.py          ← RobotViz for MG400 (same architecture as viz.py)
├── 01_connect_test.py    ← TCP ping + status (no enable)
├── 02_first_connection.py ← Enable, query, go_home, disable
├── 03_safe_move_demo.py  ← safe_move() with clamping demo
├── 04_speed_control.py   ← SpeedFactor/SpeedJ/SpeedL/AccJ/AccL demo
├── 05_end_effectors.py   ← ToolDO suction/gripper + base DO/DI
├── 06_joint_angles.py    ← GetAngle, JointMovJ, FK/IK
├── 07_keyboard_teleop.py ← MoveJog terminal jog (hold-to-move)
├── 08_pick_and_place.py  ← Lift/descend pick-and-place with suction
├── 09_arc_motion.py      ← Arc(), Circle(), sampled circle
├── 10_relative_moves.py  ← RelMovJ, RelMovL, relative pick-and-place
├── 11_motion_modes.py    ← MovJ vs MovL vs Arc comparison
└── 12_feedback_monitor.py ← Live pose from port 30004 + viz

vendor/
├── dobot-python/         ← Track B SDK (Magician, for magician/10_circle_queue.py)
└── TCP-IP-4Axis-Python/  ← MG400 SDK (dobot_api.py + MyType numpy dtype)
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
HOME_JOINTS       = (0, 0, 0, 0)           # Joint-space home (J1,J2,J3,J4 deg)
SAFE_READY_POSE   = (200, 0, 100, 0)       # Cartesian staging pose for demos
SAFE_BOUNDS       = {"x": (120, 315), "y": (-158, 158), "z": (5, 155), "r": (-90, 90)}
SPEED_SMOOTH      = (50, 40)               # mm/s, mm/s² for smooth demos
JUMP_HEIGHT       = 30                     # mm — Z clearance for JUMP_XYZ mode

# Core functions
find_port(keyword)              → str | None  # Auto-detect serial port
clamp(v, lo, hi)                → float       # Clamp value to [lo, hi]
safe_move(bot, x,y,z,r, mode)  → None        # Clamp + warn + move_to (optional MODE_PTP)
safe_rel_move(bot, dx,dy,dz,dr) → None       # Relative move clamped to SAFE_BOUNDS
go_home(bot)                    → None        # Move to joint zero via MOVJ_ANGLE
prepare_robot(bot)              → None        # Clear alarms, run homing if LIMIT
do_homing(bot)                  → None        # Run homing sequence (after power-on)
check_alarms(bot)               → None        # Print named alarms then clear them
```

**How `safe_move()` works:** It clamps each axis independently to its bounds
in `SAFE_BOUNDS`, then calls `bot.move_to(x, y, z, r, wait=True)`. This means
a request for `(330, 200, 200, 0)` becomes `(315, 158, 155, 0)` and a
`[safe_move] Clamped: ...` message is printed so students can see the
adjustment. `08_pick_and_place.py` also demonstrates an explicit pre-check
pattern (`_check()`) that warns the user before execution.

**Why these bounds:** The Dobot Magician's kinematic workspace is roughly a
320 mm radius hemisphere. The safe bounds are conservative to keep the arm away
from singularities (X too small), the table surface (Z too low), and joint
limits (R extremes). They can be widened by editing `SAFE_BOUNDS` in `utils.py`
if the physical setup allows it.

**pydobotplus auto-patch (`_patch_pydobotplus`):** `utils.py` applies a
one-time monkey-patch to `pydobotplus.Dobot.move_to` at import time that fixes
two upstream bugs: (1) an unconditional `get_pose()` call on every `move_to`
that added ~20–50 ms of serial latency per command even when all coordinates
were already provided, and (2) an unconditional `print(current_pose)` that
printed `Position(x=..., y=..., z=..., r=...)` to stdout on every move.
The patch is transparent — if `x`, `y`, `z` are all supplied it calls
`_set_ptp_cmd` directly; otherwise it falls back to the original.  Falls back
silently if pydobotplus internals change.

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
from viz import RobotViz

def main():
    PORT = find_port()
    if PORT is None:
        sys.exit("[Error] No serial port found.")

    bot = Dobot(port=PORT)
    viz = RobotViz()
    viz.attach(bot)
    try:
        go_home(bot)
        # ... your code here ...
    finally:
        viz.close()
        bot.close()

if __name__ == "__main__":
    main()
```

Disable the visualizer during development with `DOBOT_VIZ=0 python NN_description.py` or `python NN_description.py --no-viz`.

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
- **09_arc_motion.py** — students can change the radius, center coordinates,
  and number of sampled points to explore how resolution affects circle
  smoothness. Try adding a spiral by incrementing Z each step.
- **11_circle_arcs.py** — experiment with 4, 6, 8, and 12 arc segments to
  see the quality-vs-speed tradeoff. Compare the result visually with the
  sampled-point approach in script 09.

### Conventions to follow

- Never call `bot.move_to()` directly — always use `safe_move()` from utils
- Always use `wait=True` (or the safe_move default) to prevent command flooding
- Always wrap the robot connection in `try/finally` for `bot.close()`
- Use `find_port()` for port discovery, never hardcode port strings
- Keep the `EFFECTOR`, `PICK_X/Y/Z`, `STEP` etc. as constants at the top of
  the file so students can edit them without reading the whole script
- Add `RobotViz` to any motion script with the 3-line pattern (`from viz import RobotViz` / `viz = RobotViz(); viz.attach(bot)` / `viz.close()` in finally before `bot.close()`)
- Students can suppress the visualizer with `DOBOT_VIZ=0` or `--no-viz` — no code change required

---

*For detailed API reference, hardware specs, and advanced queue patterns, see
[dobot_control_options_comparison.md](./dobot_control_options_comparison.md).*

---

## Additional References

### Dobot Magician (USB-serial)

- [`README.md`](./README.md) — workspace landing page and quick navigation
- [`requirements.txt`](./requirements.txt) — pip dependencies (pydobotplus, pydobot, pyserial, pyqtgraph, PyQt5, numpy)
- [`dobot_control_options_comparison.md`](./dobot_control_options_comparison.md) — hardware specs, library syntax, safety, motion modes
- [`magician/README.md`](./magician/README.md) — numbered script sequence and support-file grouping
- [`docs/`](./docs/) — API reference for pydobotplus, arc/circle math guides, safe_move pattern analysis, and motion modes reference
- [`docs/README.md`](./docs/README.md) — canonical docs index
- [`docs/motion_modes.md`](./docs/motion_modes.md) — Complete MODE_PTP table, MOVJ/MOVL/JUMP decision guide, JUMP configuration, alarm codes
- [`docs/circle_drawing_index.md`](./docs/circle_drawing_index.md) — Start here for circle drawing: links to math guides, scripts, and worked examples
- [`magician/viz.py`](./magician/viz.py) — `RobotViz` class: real-time dual-view 2D visualizer (disable with `DOBOT_VIZ=0` or `--no-viz`)
- [`magician/17_visualizer.py`](./magician/17_visualizer.py) — standalone pose monitor; demonstrates `RobotViz` without motion
- [`magician/18_joint_control.py`](./magician/18_joint_control.py) — interactive joint-angle REPL with FK display, clamping, and CSV logging
- [`magician/19_relative_joint_control.py`](./magician/19_relative_joint_control.py) — body-frame relative angle REPL: prints conversion chain (Relative/Absolute/Firmware) + FK prediction

### DOBOT MG400 (TCP/IP)

- [`mg400/`](./mg400/) — parallel workspace for the MG400 (440 mm reach, Ethernet, TCP/IP)
- [`mg400/utils_mg400.py`](./mg400/utils_mg400.py) — MG400 equivalents of `utils.py`: `connect()`, `safe_move()`, `parse_pose()`, `check_errors()`, constants
- [`mg400/viz_mg400.py`](./mg400/viz_mg400.py) — `RobotViz` adapted for MG400 workspace bounds; same 3-line integration pattern
- [`vendor/TCP-IP-4Axis-Python/`](./vendor/TCP-IP-4Axis-Python/) — Dobot official MG400 SDK (`dobot_api.py`, `MyType` numpy dtype for port 30004)
- `CLAUDE.md §MG400` / `GEMINI.md §MG400` — full API reference, network setup, coordinate bounds, and script table (01–12)
