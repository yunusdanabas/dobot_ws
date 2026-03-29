# Dobot Magician — Python Control Guide
### ME403 Introduction to Robotics · Sabancı University · Spring 2025-26

> **This document covers the Dobot Magician (USB-serial).** For the DOBOT MG400 (TCP/IP, 440 mm reach), see [`mg400/`](./mg400/) and the MG400 sections in [`CLAUDE.md`](./CLAUDE.md) / [`GEMINI.md`](./GEMINI.md).

> **Research notes:** For detailed library internals and protocol deep-dives, see the [`research/`](./research/) directory.
> - [01: Python Libraries Overview](./research/01_python_libraries.md)
> - [02: Official SDK Options](./research/02_official_sdk_options.md)
> - [03: API Comparison](./research/03_api_comparison.md)
> - [04: Lab Safety & Setup](./research/04_lab_safety_setup.md)
> - [05: Practical Code Examples](./research/05_code_examples.md)

---

## §0 Hardware Reference

### Specifications

| Parameter | Value |
|---|---|
| Reach | 320 mm |
| Payload | 500 g |
| Repeatability | ±0.2 mm |
| Axes | 4 (J1 base, J2 upper arm, J3 forearm, J4 end-effector) |
| Communication | USB via CP210x (Silicon Labs), 115200 baud |
| Power | Dedicated wall adapter required (USB bus power is insufficient) |

### Hard Limits (firmware / physical)

| Axis | Min | Max | Notes |
|---|---|---|---|
| X | 115 mm | 320 mm | Base singularity below 115 mm; full reach at 320 mm |
| Y | -160 mm | 160 mm | Arm geometry limit |
| Z | 0 mm | 160 mm | 0 mm = table surface; firmware ceiling = 160 mm |
| R | -135° | 135° | Servo range (cable-wrap risk past ±90°) |

### Safe Bounds (SAFE_BOUNDS in utils.py — 5 mm margin from hard limits)

| Axis | Min | Max | Notes |
|---|---|---|---|
| X | 120 mm | 315 mm | 5 mm clear of singularity / max reach |
| Y | -158 mm | 158 mm | 2 mm margin |
| Z | 5 mm | 155 mm | 5 mm above table, 5 mm below ceiling |
| R | -90° | 90° | Kept at ±90° to avoid cable wrap |

### Ready Pose

`X = 200, Y = 0, Z = 100, R = 0`.
Use this as start/end pose in every motion script.

---

## §1 One-Time Setup

### Linux serial permissions (once per machine)

```bash
sudo usermod -a -G dialout $USER
# log out and back in
```

### Virtual environment

**Option A — mamba (recommended):**
```bash
mamba create -n dobot python=3.10 -y
mamba activate dobot
pip install -U pip
pip install -r requirements.txt
```

**Option B — venv:**
```bash
python3 -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate      # Windows PowerShell
pip install -U pip
pip install -r requirements.txt
```

### Install Track A + Track C dependencies

```bash
pip install pydobotplus pydobot pyserial pyqtgraph PyQt5 numpy
# or: pip install -r requirements.txt
```

### Track B setup (`dobot-python` source checkout, optional for script 10)

Clone into `vendor/` for automatic discovery:
```bash
cd dobot_ws
git clone https://github.com/AlexGustafsson/dobot-python.git vendor/dobot-python
```
Or clone elsewhere and set `DOBOT_PYTHON_PATH=/path/to/dobot-python`.

| Track | Library | Status in this workspace |
|---|---|---|
| A (default) | `pydobotplus` | Active code in `magician/` |
| B (advanced) | `dobot-python` (source checkout) | Documented for queue/protocol labs |
| C (legacy ref) | `pydobot` | API comparison + fallback reference |

---

## §2 Find Your Port

### Shared helper (used by scripts)

```python
from utils import find_port

port = find_port()  # prefers "Silicon Labs", falls back to first serial port
print(port)
```

### Manual inspection

```python
from serial.tools import list_ports

for p in list_ports.comports():
    print(p.device, "-", p.description)
```

Run `magician/01_find_port.py` for a formatted table.

---

## §3 First Connection & Pose

### Track A — pydobotplus (default)

```python
from pydobotplus import Dobot
from utils import find_port, unpack_pose

bot = Dobot(port=find_port())
try:
    x, y, z, r, j1, j2, j3, j4 = unpack_pose(bot.get_pose())
    print(f"X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}")
finally:
    bot.close()
```

### Track B — dobot-python (`lib.interface.Interface`)

```python
import sys
sys.path.insert(0, "/absolute/path/to/dobot-python")
from lib.interface import Interface
from utils import find_port

bot = Interface(find_port())
try:
    x, y, z, r, j1, j2, j3, j4 = bot.get_pose()
    print(f"X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}")
finally:
    bot.serial.close()
```

### Track C — pydobot

```python
from pydobot import Dobot
from utils import find_port

bot = Dobot(port=find_port(), verbose=False)
try:
    x, y, z, r, j1, j2, j3, j4 = bot.pose()
    print(f"X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}")
finally:
    bot.close()
```

---

## §4 Safe Movement

### Safety helpers (`magician/utils.py`)

```python
SAFE_BOUNDS  = {"x": (120, 315), "y": (-158, 158), "z": (5, 155), "r": (-90, 90)}
SAFE_READY_POSE = (200, 0, 100, 0)  # Cartesian staging; go_home() uses joint zero
JUMP_HEIGHT  = 30   # mm — Z clearance for JUMP_XYZ mode

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def safe_move(bot, x, y, z, r, mode=None):
    x = clamp(x, *SAFE_BOUNDS["x"])
    y = clamp(y, *SAFE_BOUNDS["y"])
    z = clamp(z, *SAFE_BOUNDS["z"])
    r = clamp(r, *SAFE_BOUNDS["r"])
    if mode is not None:
        bot.move_to(x, y, z, r, wait=True, mode=mode)
    else:
        bot.move_to(x, y, z, r, wait=True)

def safe_rel_move(bot, dx=0, dy=0, dz=0, dr=0):
    """Relative move clamped to SAFE_BOUNDS."""
    x, y, z, r, *_ = unpack_pose(bot.get_pose())
    safe_move(bot, x + dx, y + dy, z + dz, r + dr)
```

Use small deltas (5–10 mm) when testing unknown trajectories.
Pass `mode=MODE_PTP.MOVL_XYZ` for straight-line paths or `mode=MODE_PTP.JUMP_XYZ` for auto-lift.
See `docs/motion_modes.md` for the full MODE_PTP reference.

---

## §5 Speed & Acceleration

```python
MAX_VELOCITY = 100      # mm/s
MAX_ACCELERATION = 80   # mm/s^2

bot.speed(MAX_VELOCITY, MAX_ACCELERATION)  # pydobotplus / pydobot
```

| Profile | Velocity | Acceleration | Typical use |
|---|---|---|---|
| Slow | 25 mm/s | 20 mm/s^2 | First test passes |
| Normal | 50 mm/s | 40 mm/s^2 | Routine lab work |
| Fast | 100 mm/s | 80 mm/s^2 | Supervised demos |

Track B (`Interface`) speed control is explicit parameter setup:

```python
bot.set_point_to_point_coordinate_params(vel, vel, acc, acc, queue=True)
bot.set_point_to_point_common_params(vel, acc, queue=True)
```

---

## §6 End-Effector Control

### Suction cup

```python
# Track A / C
bot.suck(True)
# ... wait for vacuum ...
bot.suck(False)
```

```python
# Track B (Interface)
bot.set_end_effector_suction_cup(enable_control=True, enable_suction=True, queue=True)
bot.set_end_effector_suction_cup(enable_control=True, enable_suction=False, queue=True)
```

### Gripper

```python
# Track A / C
bot.grip(True)   # close
bot.grip(False)  # open
```

```python
# Track B (Interface)
bot.set_end_effector_gripper(enable_control=True, enable_grip=True, queue=True)
bot.set_end_effector_gripper(enable_control=True, enable_grip=False, queue=True)
```

---

## §7 Reading Joint Angles

Canonical pose ordering for analysis:

```
(x, y, z, r, j1, j2, j3, j4)
```

For Track A, normalize with `unpack_pose(bot.get_pose())`.
For Track B and Track C, the API already returns a flat 8-tuple.

---

## §8 Keyboard Teleoperation

See `magician/07_keyboard_teleop.py`.

| Key | Action | Delta |
|---|---|---|
| Right / Left | +X / -X | STEP mm |
| Up / Down | +Y / -Y | STEP mm |
| R / F | +Z / -Z | STEP mm |
| Q / E | +R / -R | STEP deg |
| Space | Toggle suction | — |
| H | Go to joint home (0,0,0,0) | — |
| Esc | Quit | — |

All jog motion in the script uses `safe_move()`.

---

## §9 Pick-and-Place Template

See `magician/08_pick_and_place.py`.

### Z+LIFT approach pattern

```
Home
 -> above pick  (PICK_Z + LIFT)
 -> descend     (PICK_Z)
 -> suction ON
 -> lift
 -> above place (PLACE_Z + LIFT)
 -> descend     (PLACE_Z)
 -> suction OFF
 -> lift
 -> Home
```

`LIFT = 60 mm` is a safe default for classroom setups.

---

## §10 Advanced: Queue Control with Track B

For dense trajectories, queue points and monitor queue index explicitly:

```python
import math
import sys
import time

sys.path.insert(0, "/absolute/path/to/dobot-python")
from lib.interface import Interface
from utils import find_port

bot = Interface(find_port())
try:
    vel, acc = 50, 40
    bot.set_point_to_point_coordinate_params(vel, vel, acc, acc, queue=True)
    bot.set_point_to_point_common_params(vel, acc, queue=True)

    cx, cy, z, r = 220, 0, 100, 0
    radius = 40
    steps = 36

    last_idx = None
    for i in range(steps + 1):
        angle = 2 * math.pi * i / steps
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        last_idx = bot.set_point_to_point_command(3, x, y, z, r, queue=True)

    while bot.get_current_queue_index() < last_idx:
        time.sleep(0.05)
finally:
    bot.serial.close()
```

Back-pressure rule: do not queue far ahead without monitoring `get_current_queue_index()`.

---

## §11 Motion Modes

### MODE_PTP Enum

```python
from pydobotplus import MODE_PTP
```

| Value | Name | Path | Use case |
|-------|------|------|----------|
| 0 | JUMP_XYZ | Lift → Travel → Lower | Pick-and-place; firmware handles Z-lift |
| 1 | MOVJ_XYZ | Joint interpolation | Fast transit; default in pydobotplus |
| 2 | MOVL_XYZ | Straight-line Cartesian | Drawing, writing, surface scanning |
| 3 | MOVR_XYZ | Relative Cartesian linear | Incremental absolute moves |
| 4 | MOVJ_ANGLE | Joint-space by angle | Teaching/replay from joint angles |
| 5 | MOVR_ANGLE | Relative joint-space | Fine joint adjustments |
| 6 | MOVJ_INC | Joint incremental | Small joint nudges |
| 7 | MOVL_INC | Linear incremental | Small Cartesian nudges |
| 8 | MOVJ_XYZ_INC | Joint incremental (Cartesian input) | — |
| 9 | JUMP_MOVL_XYZ | Lift → Straight-line → Lower | Precision pick-and-place |

### When to Use Each Mode

**MOVJ_XYZ** — use for fast transit between points when the end-effector path shape
does not matter. Joint interpolation curves through space. This is the default in
pydobotplus (Track A) and ZdenekM/pydobot.

**MOVL_XYZ** — use when the end-effector must travel in a straight Cartesian line:
drawing, writing, cutting, or scanning. This is the **default in luismesas/pydobot
(Track C)**, so Track A and Track C produce different paths with identical coordinates
unless mode is set explicitly.

**JUMP_XYZ** — use for pick-and-place. Configure clearance once; firmware handles
the Z-lift automatically. Eliminates the manual LIFT constant and reduces code length.

### Code Snippets

```python
from pydobotplus import MODE_PTP
from utils import safe_move, JUMP_HEIGHT

# Straight-line path (required for drawing)
safe_move(bot, 220, 0, 80, 0, mode=MODE_PTP.MOVL_XYZ)

# Firmware auto-lift (simplest pick-and-place)
bot._set_ptp_jump_params(jump=JUMP_HEIGHT, limit=120)  # configure once
safe_move(bot, PICK_X,  PICK_Y,  PICK_Z,  0, mode=MODE_PTP.JUMP_XYZ)
bot.suck(True)
safe_move(bot, PLACE_X, PLACE_Y, PLACE_Z, 0, mode=MODE_PTP.JUMP_XYZ)
bot.suck(False)
```

### Default Mode Difference Between Libraries

| Library | Default PTP mode |
|---------|-----------------|
| pydobotplus (Track A) | MOVJ_XYZ (curved) |
| ZdenekM/pydobot | MOVJ_XYZ (curved) |
| luismesas/pydobot (Track C) | MOVL_XYZ (straight) |

### Alarm Enum Overview

pydobotplus exposes ~80 named alarm codes. Use `check_alarms(bot)` from `utils.py`
after connecting to print and clear active alarms by name. Common student-facing codes:

| Code name | Likely cause |
|-----------|-------------|
| `JOINT1_FOLLOWING_ERROR` | J1 skipped steps (move too fast or overloaded) |
| `JOINT2_FOLLOWING_ERROR` | Same for J2 |
| `OVER_SPEED_JOINT` | Commanded velocity exceeds joint limit |
| `POSE_LIMIT_OVER` | Target pose outside firmware workspace |
| `MOTOR_HOT` | Overheating from sustained high load |

See `docs/motion_modes.md` for the full reference.

---

## §12 Relative (Body-Frame) Joint Angles

Scripts `magician/19_relative_joint_control.py` and `mg400/16_relative_joint_control.py`
introduce *body-frame* joint angles — each joint is measured from the previous link's
direction rather than from the world horizontal.  This convention makes the FK
transformation chain explicit and educational.

### Convention

| Joint | Body-frame meaning | Absolute equivalent |
|-------|-------------------|---------------------|
| J1 | Base rotation from world X-axis | Same as body-frame |
| J2 | Shoulder elevation from horizontal | Same as body-frame |
| J3 | Elbow offset **from the upper arm** | `j2 + j3_rel` |
| J4 | Wrist offset **from the forearm** | `j3_abs + j4_rel` |

### Conversion Formulas

```python
# Body-frame → Absolute (same for both robots)
j3_abs = j2_rel + j3_rel
j4_abs = j3_abs + j4_rel    # = j2_rel + j3_rel + j4_rel
```

### Firmware Mapping

**Dobot Magician** (parallel linkage quirk — firmware J3 is already body-frame):
```python
j3_fw = j3_rel              # trivial: firmware J3 is the body-frame offset
j4_fw = j4_abs              # firmware J4 is the absolute wrist angle
```

**DOBOT MG400** (firmware expects fully absolute angles):
```python
j3_fw = j3_abs = j2_rel + j3_rel
j4_fw = j4_abs = j2_rel + j3_rel + j4_rel
```

### Inverse (firmware → relative, for display)

```python
# Magician
j4_rel = j4_fw - (j2_fw + j3_fw)

# MG400
j3_rel = j3_fw - j2_fw
j4_rel = j4_fw - j3_fw
```

Joint bounds are always enforced on **firmware** (absolute) angles, not on the
relative inputs.  The scripts call `clamp_fw_joints()` after conversion.

### MG400 Joint Bounds (per DT-MG400-4R075-01 hardware guide V1.1, Table 2.1)

```python
JOINT_BOUNDS = {
    "j1": (-160.0, 160.0),   # ±160° per hardware guide
    "j2": ( -25.0,  85.0),   # -25° ~ +85° per hardware guide
    "j3": ( -25.0, 105.0),   # -25° ~ +105° per hardware guide (firmware absolute = j2+j3_rel)
    "j4": (-180.0, 180.0),   # ±180° per hardware guide
}
```

Factory/home angles: J1=0°, J2=0°, **J3=60°**, J4=0°  (§2.8) — J3=60° confirms the firmware
absolute convention (body-frame J3_rel=60° at home with J2=0°).

**Worst-case relative spinbox bounds** (for GUI limits):

| Rel axis | Range | Derivation |
|----------|-------|------------|
| J1_rel | (-160, +160) | = J1_fw range |
| J2_rel | (-25, +85) | = J2_fw range |
| J3_rel | (-110, +130) | j3_fw(-25~105) − j2_fw(-25~85) |
| J4_rel | (-285, +205) | j4_fw(-180~180) − j3_fw(-25~105) |

---

## §13 Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Permission denied /dev/ttyUSBx` | Not in `dialout` group | `sudo usermod -a -G dialout $USER`, then re-login |
| `Port not found` | Wrong cable/power/port | Run `01_find_port.py`, verify USB + wall adapter |
| Robot grinds/skips | Limits or unsafe target | Reduce target and keep safe bounds |
| Script hangs during move | Power or queue congestion | Check adapter, reduce command rate, keep blocking semantics |
| Suction weak/no grip | Vacuum leak or wrong tool mode | Check tubing/seal and effectors |
| Robot does not respond | DobotStudio still owns port | Close DobotStudio/DobotDemo |

---

*For the MG400 robot (TCP/IP, Ethernet), see [`mg400/`](./mg400/), [`mg400/utils_mg400.py`](./mg400/utils_mg400.py), and the MG400 sections in [`CLAUDE.md`](./CLAUDE.md) / [`GEMINI.md`](./GEMINI.md).*
