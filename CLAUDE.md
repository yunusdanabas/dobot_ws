# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

This workspace supports **ME403 – Introduction to Robotics** (Sabancı University, Spring 2025-26). It provides Python control resources for the **Dobot Magician** robotic arm over USB-serial. There is no compiled/built project — this is a documentation and scripting workspace.

## Environment Setup

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
```

**Install Track A + Track C dependencies (recommended baseline):**
```bash
pip install pydobotplus pydobot pyserial pynput
```

**Track B (`dobot-python`) setup (source checkout):**
```bash
cd /path/for/vendor-code
git clone https://github.com/AlexGustafsson/dobot-python.git
```
Use it by adding that checkout to `sys.path` in scripts/docs examples.

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
from utils import clamp, safe_move, go_home, unpack_pose, READY_POSE, SAFE_BOUNDS

# SAFE_BOUNDS = {"x": (150, 280), "y": (-160, 160), "z": (10, 150), "r": (-90, 90)}
# READY_POSE  = (200, 0, 100, 0)
```

Standalone version if needed:
```python
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def safe_move(bot, x, y, z, r):
    x = clamp(x, 150, 280)
    y = clamp(y, -160, 160)
    z = clamp(z, 10, 150)
    r = clamp(r, -90, 90)
    bot.move_to(x, y, z, r, wait=True)
```

## Important Constraints

- **Only one process can own the serial port at a time.** DobotStudio/DobotDemo must be closed while Python scripts run.
- For trajectory labs, do not spam commands faster than the robot consumes them — use queue-index back-pressure with Track B (`Interface.get_current_queue_index()`).
- Coordinates are in **mm** (x, y, z) and **degrees** (r). Use small deltas (5–10 mm) when testing new motion code.

## Key Reference Files

- `GUIDE.md` — student lab guide: script-by-script walkthrough, common workflows, troubleshooting, and implementation details for TAs
- `dobot_control_options_comparison.md` — canonical reference: hardware specs, all three library syntaxes, safety helpers, queue patterns, troubleshooting
- `Syllabus-ME403-202502.md` — weekly lab schedule and course learning outcomes
- `GEMINI.md` — mirrors this file for Gemini-based AI interactions
- `research/` — detailed research notes (libraries, SDK options, API comparison, safety, code examples)
- `scripts/` — runnable Python scripts; start with `01_find_port.py`
