# GEMINI.md

This file provides guidance to Gemini-based agents when working with code in this repository.

## Project Context

This workspace supports **ME403 – Introduction to Robotics** (Sabancı University, Spring 2025-26). It provides Python control resources for the **Dobot Magician** robotic arm over USB-serial. There is no compiled/built project — this is a documentation and scripting workspace.

## Environment Setup

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
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

**Track A + Track C + visualization baseline** (equivalent to `requirements.txt`):
```bash
pip install pydobotplus pydobot pyserial pyqtgraph PyQt5 numpy
```

**Track B (`dobot-python`) setup (optional, for script 10):**
Clone into `vendor/` for automatic discovery:
```bash
cd dobot_ws
git clone https://github.com/AlexGustafsson/dobot-python.git vendor/dobot-python
```
Script `10_circle_queue.py` finds it at `vendor/dobot-python` when run from `scripts/`; or set `DOBOT_PYTHON_PATH` to any checkout path.

**Linux serial port permissions (required once per machine):**
```bash
sudo usermod -a -G dialout $USER
# then log out and back in
```

## Key Architecture Decisions

Three library tracks are used intentionally:

| Track | Library | Use case |
|-------|---------|----------|
| A (default) | `pydobotplus` | Labs 1–4: FK/IK, basic motion, quick iteration |
| B (advanced) | `dobot-python` (source checkout) | Queue-heavy protocol work via `lib.interface.Interface` |
| C (legacy ref) | `pydobot` | Original API reference; comments in scripts |

Scripts live in `scripts/` and share helpers from `scripts/utils.py`.

## Serial Port Discovery

Always run this first to find the robot's port before writing control scripts:

```python
from serial.tools import list_ports
for p in list_ports.comports():
    print(p.device, "-", p.description)
# Windows → COM3; Linux → /dev/ttyUSB0 or /dev/ttyACM0
```

Or run:
```bash
python scripts/01_find_port.py
```

## Safety Pattern (required in all motion scripts)

Shared helpers live in `scripts/utils.py`. Import them rather than redefining:

```python
from utils import (
    clamp, safe_move, safe_rel_move, go_home, get_home, unpack_pose,
    check_alarms, READY_POSE, SAFE_BOUNDS, JUMP_HEIGHT, find_port
)

# SAFE_BOUNDS = {"x": (120, 315), "y": (-158, 158), "z": (5, 155), "r": (-90, 90)}
# READY_POSE  = (200, 0, 100, 0)
# JUMP_HEIGHT = 30  # mm — Z clearance for JUMP_XYZ mode
```

Standalone version if needed:
```python
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def safe_move(bot, x, y, z, r, mode=None):
    x = clamp(x, 120, 315)
    y = clamp(y, -158, 158)
    z = clamp(z, 5, 155)
    r = clamp(r, -90, 90)
    if mode is not None:
        bot.move_to(x, y, z, r, wait=True, mode=mode)
    else:
        bot.move_to(x, y, z, r, wait=True)
```

## Important Constraints

- **Only one process can own the serial port at a time.** DobotStudio/DobotDemo must be closed while Python scripts run.
- For trajectory labs, do not spam commands faster than the robot consumes them — use queue-index back-pressure with Track B (`Interface.get_current_queue_index()`).
- Coordinates are in **mm** (x, y, z) and **degrees** (r). Use small deltas (5–10 mm) when testing new motion code.

## Key Reference Files

- `requirements.txt` — pip dependencies (pydobotplus, pydobot, pyserial, pyqtgraph, PyQt5, numpy)
- `GUIDE.md` — student lab guide: script-by-script walkthrough (01–17), physical setup, common workflows, troubleshooting, and implementation details for TAs
- `dobot_control_options_comparison.md` — canonical reference: hardware specs, all three library syntaxes, safety helpers, motion modes, queue patterns, troubleshooting
- `Syllabus-ME403-202502.md` — weekly lab schedule and course learning outcomes
- `CLAUDE.md` — mirrors this file for Claude-based AI interactions
- `docs/` — API reference, arc/circle math guides, safe_move pattern analysis, motion modes reference
- `docs/motion_modes.md` — complete MODE_PTP table, MOVJ/MOVL/JUMP decision guide, alarm codes
- `research/` — detailed research notes (libraries, SDK options, API comparison, safety, code examples)
- `scripts/` — runnable Python scripts 01–17; start with `01_find_port.py`
- `scripts/viz.py` — `RobotViz` utility: dual-view 2D real-time visualizer (subprocess, pyqtgraph/PyQt5)
- `scripts/17_visualizer.py` — standalone pose monitor; demonstrates `RobotViz.send()` without motion commands

## Visualization Pattern

Scripts 07–09 and 12–13 integrate `viz.py` directly. `17_visualizer.py` uses the same window as a standalone, single-owner pose monitor.
Add to any motion script with 3 lines:

```python
from viz import RobotViz          # import
viz = RobotViz()                  # after bot = Dobot(port=...)
viz.attach(bot)                   # patches bot.move_to auto-captures poses
# ... motion code unchanged ...
viz.close()                       # in finally block, before bot.close()
```

`RobotViz` is not a shared-port monitor. Only one process can own the robot port at a time.

Disable via environment or CLI:
```bash
DOBOT_VIZ=0 python 07_keyboard_teleop.py
python 07_keyboard_teleop.py --no-viz
```
