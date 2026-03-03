# Dobot Magician — Python Control Guide
### ME403 Introduction to Robotics · Sabancı University · Spring 2025-26

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

### Safe Lab Bounds

| Axis | Min | Max | Notes |
|---|---|---|---|
| X | 150 mm | 280 mm | Keep away from base singularity region |
| Y | -160 mm | 160 mm | Symmetric left/right travel |
| Z | 10 mm | 150 mm | Keep off table surface |
| R | -90° | 90° | Avoid cable wrap |

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

```bash
python3 -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate      # Windows PowerShell
pip install -U pip
```

### Install Track A + Track C dependencies

```bash
pip install pydobotplus pydobot pyserial pynput
```

### Track B setup (`dobot-python` source checkout)

```bash
cd /path/for/vendor-code
git clone https://github.com/AlexGustafsson/dobot-python.git
```

| Track | Library | Status in this workspace |
|---|---|---|
| A (default) | `pydobotplus` | Active code in `scripts/` |
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

Run `scripts/01_find_port.py` for a formatted table.

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

### Safety helpers (`scripts/utils.py`)

```python
SAFE_BOUNDS = {"x": (150, 280), "y": (-160, 160), "z": (10, 150), "r": (-90, 90)}
READY_POSE = (200, 0, 100, 0)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def safe_move(bot, x, y, z, r):
    x = clamp(x, *SAFE_BOUNDS["x"])
    y = clamp(y, *SAFE_BOUNDS["y"])
    z = clamp(z, *SAFE_BOUNDS["z"])
    r = clamp(r, *SAFE_BOUNDS["r"])
    bot.move_to(x, y, z, r, wait=True)
```

Use small deltas (5-10 mm) when testing unknown trajectories.

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

See `scripts/07_keyboard_teleop.py`.

| Key | Action | Delta |
|---|---|---|
| Right / Left | +X / -X | STEP mm |
| Up / Down | +Y / -Y | STEP mm |
| Page Up / Page Down | +Z / -Z | STEP mm |
| Q / E | +R / -R | STEP deg |
| Space | Toggle suction | — |
| H | Go to `READY_POSE` | — |
| Esc | Quit | — |

All jog motion in the script uses `safe_move()`.

---

## §9 Pick-and-Place Template

See `scripts/08_pick_and_place.py`.

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

## §11 Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Permission denied /dev/ttyUSBx` | Not in `dialout` group | `sudo usermod -a -G dialout $USER`, then re-login |
| `Port not found` | Wrong cable/power/port | Run `01_find_port.py`, verify USB + wall adapter |
| Robot grinds/skips | Limits or unsafe target | Reduce target and keep safe bounds |
| Script hangs during move | Power or queue congestion | Check adapter, reduce command rate, keep blocking semantics |
| Suction weak/no grip | Vacuum leak or wrong tool mode | Check tubing/seal and effectors |
| Robot does not respond | DobotStudio still owns port | Close DobotStudio/DobotDemo |
