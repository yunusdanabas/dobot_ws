# Lab 1: Warming up to the Robot

Implement forward kinematics and a Jacobian function for either the **Dobot Magician** or the **DOBOT MG400**.  
Write all your code in `myCode.py`. Run the interface to test interactively.

---

## Files

| File | Purpose |
|------|---------|
| `utils.py` | Unified robot helpers — edit `ROBOT_TYPE` and `MG400_IP` here |
| `interface.py` | Interactive REPL: jog the robot and run your code |
| `myCode.py` | **Your work goes here** — implement Tasks 1–3 |
| `requirements.txt` | Python dependencies for Magician |

---

## Robot Selection

Open `utils.py` and set the two constants near the top:

```python
ROBOT_TYPE = "magician"       # "magician" or "mg400"
MG400_IP   = "192.168.2.7"   # only used when ROBOT_TYPE = "mg400"
```

**MG400 IP addresses** (choose the one assigned to your bench):

| Robot | IP |
|-------|----|
| 1 | 192.168.2.7 |
| 2 | 192.168.2.10 |
| 3 | 192.168.2.9 |
| 4 | 192.168.2.6 |

---

## Setup

### Magician
```bash
pip install -r requirements.txt
# Connect USB, power on, close DobotStudio
python interface.py
```

### MG400
```bash
pip install numpy
# Clone SDK once (from dobot_ws/ root):
git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git vendor/TCP-IP-4Axis-Python
# Set PC Ethernet to static IP 192.168.2.100 / 255.255.255.0
# Verify: ping 192.168.2.7
python interface.py
```

---

## Interface Commands

```
move q1 q2 q3 q4    Move to body-frame joint angles (degrees), prints actual pose
x                   Execute myCode.run() — runs your Task 1/2/3 code
q                   Quit and return robot to home
```

---

## API (from `utils.py`)

```python
import utils as U

robot = U.setup()                            # connect and home
x, y, z, r = U.move_and_get_feedback(robot, [q1, q2, q3, q4])
U.teardown(robot)                            # home and disconnect
```

`move_and_get_feedback` takes **body-frame** angles, converts to firmware internally, moves the robot, and returns the actual Cartesian pose.

---

## Magician vs MG400 — Key Differences

| Property | Magician | MG400 |
|----------|----------|-------|
| Connection | USB serial (auto-detected) | TCP/IP Ethernet |
| Setup | Plug-and-play | Static PC IP + SDK clone required |
| J1 range | ±90° | ±160° |
| J2 range | 0° – 85° | −25° – 85° |
| J3 range | −10° – 85° | −25° – 105° |
| J3 firmware | = q3 (body-frame directly) | = q2 + q3 (accumulated) |
| Z axis | Can go slightly negative | Must stay ≥ 0 mm (0 = table surface) |
| Link lengths | L1=135 mm, L2=147 mm | L1=175 mm, L2=175 mm |
| Shoulder height | Z_base ≈ 103 mm | Z_base ≈ 116 mm |

> `utils.py` handles all these differences automatically once `ROBOT_TYPE` is set correctly.
