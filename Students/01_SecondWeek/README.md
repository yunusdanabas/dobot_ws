# Week 1 — Lab 01: Forward Kinematics (Magician + MG400)

Lab 01 introduces **forward kinematics**. Instead of using a GUI, students write calculation scripts:
compute joint angles, call `moveMagician(bot, q)` or `moveMG400(mv, q)`, then verify the FK prediction
against the robot's actual reported pose.

Joint angles are specified in **body-frame** (angle between consecutive links), not firmware-absolute.
The utility module handles the conversion internally.

---

## Magician

### Prerequisites

- USB cable + 12 V power adapter connected
- Linux only (one-time): `sudo usermod -a -G dialout $USER`, then re-login

### Setup

**Linux:**
```bash
# from Students/01_SecondWeek/
python3 -m venv .venv
source .venv/bin/activate
pip install -r magician/requirements.txt
cd magician
python lab01_fk.py
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r magician\requirements.txt
cd magician
python lab01_fk.py
```

### Files

| File | Description |
|------|-------------|
| `magician/lab01_fk.py` | Student FK template — fill in Tasks 1–3 |
| `magician/interactive_move.py` | Interactive REPL: enter joint angles, see actual Cartesian pose |
| `magician/utils.py` | Helpers: `setup()`, `moveMagician(bot, q)`, `get_joints(bot)`, `get_pose(bot)`, `move_and_get_feedback(bot, q)`, `teardown(bot)` |
| `magician/requirements.txt` | Python dependencies |

---

## MG400

### Prerequisites

1. **SDK clone** (one-time, run from `dobot_ws/` root):
   ```bash
   git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git vendor/TCP-IP-4Axis-Python
   ```

2. **Static IP** — set PC Ethernet adapter to `192.168.2.100 / 255.255.255.0`

3. **Ping check**: `ping <assigned-robot-ip>` (example: `ping 192.168.2.7`)

### Setup

**Linux:**
```bash
# from Students/01_SecondWeek/
python3 -m venv .venv
source .venv/bin/activate
pip install -r mg400/requirements.txt
cd mg400
python lab01_fk.py
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r mg400\requirements.txt
cd mg400
python lab01_fk.py
```

### Files

| File | Description |
|------|-------------|
| `mg400/lab01_fk.py` | Student FK template — fill in Tasks 1–3 |
| `mg400/interactive_move.py` | Interactive REPL: enter joint angles, see actual Cartesian pose |
| `mg400/utils_mg400.py` | Helpers: `setup()`, `moveMG400(mv, q)`, `get_joints(db)`, `get_pose(db)`, `move_and_get_feedback(mv, db, q)`, `teardown(db, mv)` |
| `mg400/requirements.txt` | Python dependencies |
| `mg400/01_init_check.py` | TCP connectivity check (reference script) |
| `mg400/02_joint_control.py` | Interactive REPL: absolute joint control with FK preview (reference) |
| `mg400/03_relative_joint_control.py` | Body-frame REPL: shows conversion chain (reference) |

### Robot Network Map

| Robot | IP | Notes |
|-------|----|-------|
| 1 | 192.168.2.7 | match robot sticker |
| 2 | 192.168.2.10 | match robot sticker |
| 3 | 192.168.2.9 | match robot sticker |
| 4 | 192.168.2.6 | match robot sticker |

```bash
# Select a different robot:
# Edit: dashboard, move_api = U.setup(robot=2)
```

---

## Lab Structure

All work happens inside `lab01_fk.py`. The SETUP and TEARDOWN sections are fixed.
Students edit only the three TASK blocks.

```
Task 0   Measure Z_base — read actual shoulder height at home position
Task 1   Single configuration — hand-calculate FK, verify with robot
Task 2   Multi-step trajectory — 3+ configurations, record actual poses
Task 3   FK verification — implement fk_predict(), compare error by axis
```

### FK Formula

```
theta2 = radians(q[1])                        # shoulder absolute
theta3 = radians(q[1] + q[2])                 # forearm absolute
reach  = L1*cos(theta2) + L2*cos(theta3)
Z_pred = Z_base + L1*sin(theta2) + L2*sin(theta3)
X_pred = reach * cos(radians(q[0]))
Y_pred = reach * sin(radians(q[0]))
```

| Robot    |  L1  |  L2  | Z_base (nominal) |
|----------|:----:|:----:|:----------------:|
| Magician | 135 mm | 147 mm | 103 mm |
| MG400    | 175 mm | 175 mm | 116 mm |

---

## MG400 Safe Operating Bounds

| Axis | Range | Notes |
|------|-------|-------|
| X | 60–400 mm | inner limit ≈60 mm (base singularity) |
| Y | ±220 mm | symmetric |
| Z | 5–140 mm | cannot go negative (0 = mounting surface) |
| R | ±170° | end-effector rotation |
