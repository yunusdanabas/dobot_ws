# Dobot Magician vs DOBOT MG400 — Code Comparison

This document explains the structural and API-level differences between the Magician
(`magician/`) and MG400 (`mg400/`) code, so you understand why the same lab task
looks different depending on which robot you are using.

It compares the full root tracks. The intro-week copies under
`Students/00_IntroductionWeek/` are trimmed teaching versions and omit some
advanced options such as visualization flags, CSV logging, and feedback helpers.

---

## 1. Physical Connection

| | Dobot Magician | DOBOT MG400 |
|---|---|---|
| **Interface** | USB-serial (CP210x chip) | Ethernet (TCP/IP) |
| **Library** | `pydobotplus` (pip package) | `dobot_api.py` (SDK git clone) |
| **Protocol** | Binary serial protocol at 115200 baud | Three TCP sockets |
| **Sockets** | 1 (everything through one serial port) | 3 — dashboard (29999), move (30003), feed (30004) |

**Magician:**
```python
from pydobotplus import Dobot
bot = Dobot(port="/dev/ttyUSB0")   # one object, one serial port
```

**MG400:**
```python
from utils_mg400 import connect
dashboard, move_api, feed = connect("192.168.2.7")  # three objects, three TCP sockets
# dashboard → robot state, errors, FK/IK queries, I/O
# move_api  → motion commands
# feed      → 8 ms binary telemetry stream (read-only)
```

The three-socket split is a design choice by Dobot: state management and motion are on
separate channels so a slow dashboard query (e.g. `GetPose`) never blocks motion commands.

---

## 2. Enable / Disable

The Magician enables its motors automatically when the Python connection opens. The MG400
requires an explicit enable/disable step.

**Magician** — motors come on at connect:
```python
bot = Dobot(port=PORT)   # motors on immediately
# ... work ...
bot.close()              # motors off at disconnect
```

**MG400** — explicit enable required:
```python
dashboard.EnableRobot()  # motors on (arm may shift slightly on brake release)
time.sleep(1.5)          # wait for enable to settle
# ... work ...
dashboard.DisableRobot() # motors off
close_all(dashboard, move_api, feed)
```

---

## 3. Reading the Current Pose

**Magician** — returns a structured `Pose` object:
```python
pose = bot.get_pose()
# pose.position.x, pose.position.y, ...
# pose.joints.j1, pose.joints.j2, ...

# utils.unpack_pose() normalises to a plain 8-tuple:
x, y, z, r, j1, j2, j3, j4 = unpack_pose(bot.get_pose())
```

**MG400** — returns a raw response string that must be parsed:
```python
resp = dashboard.GetPose()
# resp looks like: "0,300.00,0.00,50.00,0.00,0.00,0.00,0.00"
x, y, z, r = parse_pose(resp)   # strips error code, converts to floats

resp = dashboard.GetAngle()
# resp looks like: "0,0.00,45.00,-30.00,0.00"
j1, j2, j3, j4 = parse_angles(resp)
```

The leading `0` in MG400 responses is an error code (0 = OK). `parse_pose()` and
`parse_angles()` in `utils_mg400.py` use a regex to extract floats and skip it.

---

## 4. Moving the Robot

### 4.1 Cartesian moves

**Magician** — `move_to()` blocks until complete (when `wait=True`):
```python
bot.move_to(200, 0, 100, 0, wait=True)          # MOVJ (default)
bot.move_to(200, 0, 100, 0, wait=True,
            mode=MODE_PTP.MOVL_XYZ)              # MOVL (straight line)
```

**MG400** — motion and sync are separate calls:
```python
move_api.MovJ(200, 0, 100, 0)   # queue the move (returns immediately)
move_api.Sync()                  # block until the queued move completes

move_api.MovL(200, 0, 100, 0)   # straight-line path
move_api.Sync()
```

The Magician's `wait=True` is roughly equivalent to calling `Sync()` on the MG400.
When you want to queue multiple moves without waiting (e.g. for smooth paths), the MG400
simply omits `Sync()` between moves.

### 4.2 Joint moves

**Magician** — uses `move_to()` with a special mode flag (first 4 args become J1–J4):
```python
from pydobotplus.dobotplus import MODE_PTP
bot.move_to(0, 45, 20, 0, wait=True, mode=MODE_PTP.MOVJ_ANGLE)
```

**MG400** — has a dedicated joint-move command:
```python
move_api.JointMovJ(0, 45, -60, 0)
move_api.Sync()
```

### 4.3 Relative moves

**Magician** — no native relative move; `safe_rel_move()` in `utils.py` reads the
current pose with `get_pose()` then adds the deltas:
```python
safe_rel_move(bot, dx=10, dy=0, dz=0, dr=0)
```

**MG400** — has native relative move commands:
```python
move_api.RelMovJ(10, 0, 0, 0)   # relative in joint space
move_api.RelMovL(10, 0, 0, 0)   # relative Cartesian straight line
move_api.Sync()
```

---

## 5. Keyboard Teleoperation (Script 07)

This is one of the most visible structural differences.

**Magician** — must manually integrate position and flush the command queue on key release:
```python
# On key press: accumulate velocity into x,y,z
# At CMD_HZ rate: call safe_move(bot, x, y, z, r)
# On key release: flush queue
bot._set_queued_cmd_stop_exec()
bot._set_queued_cmd_clear()
bot._set_queued_cmd_start_exec()
```
This is needed because `move_to()` puts commands into a FIFO queue in the robot firmware.
Without flushing, old commands keep executing after the key is released.

**MG400** — uses the native `MoveJog` API, which handles this cleanly:
```python
move_api.MoveJog("X+")   # start jogging in +X (firmware controls velocity/accel)
# ... key held ...
move_api.MoveJog("")     # stop jogging (firmware decelerates and stops)
```
The MG400 firmware handles velocity ramps internally. No queue management needed.

---

## 6. Error / Alarm Handling

**Magician:**
```python
alarms = bot.get_alarms()          # returns a list of alarm enum values
if alarms:
    bot.clear_alarms()
```

**MG400:**
```python
resp = dashboard.GetErrorID()      # returns "0,[[id1,id2,...]]" string
# parse, then:
dashboard.ClearError()
dashboard.Continue()               # resume execution after clearing
```
The MG400 also has a concept of "robot mode" (5=idle, 7=running, 9=error, 11=jog) that you
can query with `dashboard.RobotMode()`. The Magician doesn't expose a mode concept.

---

## 7. Real-time Feedback

**Magician** — feedback only via serial poll (`get_pose()`), which takes 20–50 ms per call
(a serial round-trip). Polling faster than ~20 Hz noticeably slows down motion.

**MG400** — has a dedicated binary telemetry port (port 30004) that pushes 1440-byte
packets at **8 ms** intervals without any polling overhead:
```python
# start_feedback_thread() in utils_mg400.py reads port 30004 in a daemon thread
# and updates the shared current_pose dict continuously
feed_thread = start_feedback_thread(feed)
# anywhere in code:
print(current_pose["x"], current_pose["y"], current_pose["z"])
```
This is how `12_feedback_monitor.py` can plot pose at 125 Hz without affecting motion.

---

## 8. Coordinate Bounds

Both robots use the same axis convention (X = forward, Y = left, Z = up, R = wrist),
but the physical envelopes are very different.

| Axis | Magician safe range | MG400 safe range |
|------|---------------------|-----------------|
| X | 120–315 mm | 60–400 mm |
| Y | ±158 mm | ±220 mm |
| Z | 5–155 mm | **5–140 mm** |
| R | ±90° | ±170° |

**Important Z difference:** The MG400's Z origin is the robot's mounting surface. Z=0
means the tool is at table level — there is no physical space below that. All MG400
scripts enforce `Z ≥ 5 mm`. The Magician's Z origin is the base of the arm; negative Z
is physically possible but the safe bound prevents it.

---

## 9. Safe Move Helper

The `safe_move()` function works the same way conceptually in both codebases (clamp then
move), but the signatures differ because the motion APIs differ.

**Magician** (`magician/utils.py`):
```python
def safe_move(bot, x, y, z, r, mode=None):
    # clamp to SAFE_BOUNDS, then:
    bot.move_to(cx, cy, cz, cr, wait=True)           # blocks
    bot.move_to(cx, cy, cz, cr, wait=True, mode=mode) # with explicit mode
```

**MG400** (`mg400/utils_mg400.py`):
```python
def safe_move(move_api, x, y, z, r, mode="J"):
    # clamp to SAFE_BOUNDS, then:
    move_api.MovJ(cx, cy, cz, cr)   # mode="J"
    move_api.MovL(cx, cy, cz, cr)   # mode="L"
    # does NOT call Sync() — caller decides when to sync
```

The Magician version always blocks (equivalent to blocking + sync). The MG400 version
intentionally does not sync, so scripts that chain multiple moves can choose when to wait.

---

## 10. Visualizer Integration

The `RobotViz` class in `viz.py` / `viz_mg400.py` is identical in architecture, but
`attach()` monkey-patches different methods because the APIs differ.

**Magician** (`viz.py`):
```python
viz.attach(bot)       # patches bot.move_to → captures every commanded pose
```

**MG400** (`viz_mg400.py`):
```python
viz.attach(move_api)  # patches move_api.MovJ AND move_api.MovL
```

The workspace boundary shown in the viz window also uses different bounds
(`SAFE_BOUNDS` from each respective utils file).

---

## 11. Multi-Robot Support

| | Magician | MG400 |
|---|---|---|
| **Multi-robot** | Not supported — one serial port per robot | Supported — `connect_multi([1,2,3,4])` |
| **Parallel motion** | N/A | `threading.Barrier` + separate TCP connections |

The MG400's network-based connection means multiple robots can be controlled from a single
Python process simultaneously (see `mg400/13_multi_robot_demo.py` and
`mg400/15_multi_joint_control.py`). The Magician's USB-serial design is inherently
single-robot per process.

---

## 12. Forward Kinematics Query

**Magician** — FK is computed client-side (via library geometry or not exposed directly).

**MG400** — FK can be queried from the robot controller itself:
```python
resp = dashboard.PositiveSolution(j1, j2, j3, j4, user=0, tool=0)
x, y, z, r = parse_pose(resp)   # predicted Cartesian from joint angles
```
This is used in `14_joint_control.py` to show the FK prediction before executing a joint
move, letting students compare the controller's FK with the actual measured pose.

---

## Summary Table

| Feature | Magician | MG400 |
|---------|----------|-------|
| Connection | USB-serial, 1 object | Ethernet, 3 objects |
| Enable/disable | Automatic | Explicit (`EnableRobot` / `DisableRobot`) |
| Move command | `bot.move_to(..., wait=True)` | `move_api.MovJ/MovL(...)` + `Sync()` |
| Joint move | `move_to(..., mode=MOVJ_ANGLE)` | `move_api.JointMovJ(j1,j2,j3,j4)` |
| Relative move | Manual (read pose + add delta) | Native `RelMovJ` / `RelMovL` |
| Pose query | `bot.get_pose()` → Pose object | `dashboard.GetPose()` → parse string |
| Teleoperation | Queue flush on key release | Native `MoveJog("")` to stop |
| Real-time feedback | Serial poll (~20–50 ms) | Binary stream port 30004 (8 ms push) |
| Error handling | `get_alarms()` / `clear_alarms()` | `GetErrorID()` + `ClearError()` + `Continue()` |
| FK query | Not exposed | `dashboard.PositiveSolution(j1..j4)` |
| Multi-robot | No | Yes (`connect_multi`) |
| Max reach | 320 mm | 440 mm |
| Z origin | Arm base (negative possible) | Mounting surface (Z ≥ 0 always) |
