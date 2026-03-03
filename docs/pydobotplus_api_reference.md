# pydobotplus Method Analysis & API Reference

## Repository
- **Package**: `pydobotplus` 
- **GitHub**: https://github.com/sammydick22/pydobotplus
- **PyPI**: https://pypi.org/project/pydobotplus/
- **Latest Version**: 0.1.2 (July 10, 2024)
- **Author**: sammydick22

## Quick Summary

**pydobotplus** is a focused high-level extension of the Dobot Magician API with these characteristics:
- **Higher-level abstraction** than raw protocol communication
- **Queue-aware operations** with automatic queue tracking
- **Wrapped endpoint-control methods** (suction, gripper, laser)
- **Motion control** (PTP movement, arc, relative moves, jog)
- **Sensor/IO support** (color sensor, IR sensor, analog IO)
- **Conveyor belt control** with distance-based movement

---

## Your Requested Methods: Status Check

| Method | Available? | Alternative Name | Notes |
|--------|:----------:|------------------|-------|
| `arc()` | ✗ | `go_arc(x, y, z, r, cir_x, cir_y, cir_z, cir_r)` | Arc motion with center point params |
| `move_joint_to()` | ✗ | — | **NOT IMPLEMENTED** in pydobotplus |
| `set_home_params()` | ✗ | `set_home(x, y, z, r=0)` | Sets home position, not parameters |
| `do_homing()` | ✗ | `home()` | Executes homing sequence |
| `clear_alarms()` | ✓ | `clear_alarms()` | Clears all robot alarms |
| `get_alarms()` | ✓ | `get_alarms()` | Returns `set` of active alarms |
| `set_end_effector_suction_cup()` | ✗ | `suck(enable: bool)` | Enable/disable suction |
| `set_end_effector_gripper()` | ✗ | `grip(enable: bool)` | Enable/disable gripper |
| `set_conveyor_belt()` | ✗ | `conveyor_belt(speed, direction, interface)` | Speed as 0.0–1.0 normalized |
| `wait_for_queue()` | ✗ | `wait_for_cmd(cmd_id: int)` | Waits for specific command by ID |

---

## Complete Public API

### Core Motion
```python
# Cartesian movement (absolute)
move_to(x=None, y=None, z=None, r=0, wait=True, mode=None, position=None)

# Cartesian movement (relative)
move_rel(x=0, y=0, z=0, r=0, wait=True)

# Arc motion (Cartesian with center circle params)
go_arc(x, y, z, r, cir_x, cir_y, cir_z, cir_r)

# Jog commands (incremental motion)
jog_x(v), jog_y(v), jog_z(v), jog_r(v)
```

### Homing & Configuration
```python
# Set home position (stored in robot memory)
set_home(x, y, z, r=0)

# Execute homing sequence
home()

# Set motion parameters (velocity + acceleration)
speed(velocity=100., acceleration=100.)
```

### End-Effector Control
```python
# Suction cup (vacuum gripper)
suck(enable: bool)

# Mechanical gripper
grip(enable: bool)

# Laser engraver
laze(power=0, enable=False)
```

### Conveyor Belt
```python
# Speed control (0.0–1.0 normalized)
conveyor_belt(speed, direction=1, interface=0)

# Distance-based movement
conveyor_belt_distance(speed_mm_per_sec, distance_mm, direction=1, interface=0)
```

### Alarm Management
```python
get_alarms() -> set[Alarm]
clear_alarms() -> None
```

### Sensor/IO Control
```python
# Color sensor
set_color(enable=True, port=PORT_GP2, version=0x1)
get_color(port=PORT_GP2, version=0x1) -> list[int]

# IR sensor
set_ir(enable=True, port=PORT_GP4)
get_ir(port=PORT_GP4) -> bool

# General IO
set_io(address: int, state: bool)

# Handheld teaching mode
set_hht_trig_output(state: bool)
get_hht_trig_output() -> bool
```

### Queue Management
```python
# Poll command execution
wait_for_cmd(cmd_id: int) -> None

# Advanced engraving (image-to-pattern)
engrave(image, pixel_size, low=0.0, high=40.0, velocity=5, acceleration=5, actual_acceleration=5)
```

### Utility
```python
get_pose() -> Pose(position: Position, joints: Joints)
close() -> None
```

---

## Data Types & Enums

### Alarm (IntEnum)
Comprehensive alarm codes covering:
- **COMMON_*** : System/MCU issues
- **PLAN_*** : Trajectory planning errors (singularity, limits, kinematics)
- **MOVE_*** : Movement-specific errors
- **OVERSPEED_AXIS[1-4]** : Velocity violations
- **LIMIT_*** : Joint limit violations
- **LOSE_STEP_*** : Motor step loss
- **OTHER_*** : Driver/overflow/following errors
- **MOTOR_*** : Motor/encoder thermal, electrical, CAN issues (REAR, FRONT, Z, R axes)

Example:
```python
from pydobotplus import Alarm
alarms = device.get_alarms()
if Alarm.PLAN_INV_LIMIT in alarms:
    print("Inverse kinematics limit exceeded")
```

### Position (NamedTuple)
```python
Position(x: float, y: float, z: float, r: float)
```

### Joints (NamedTuple)
```python
Joints(j1: float, j2: float, j3: float, j4: float)
  .in_radians() -> Joints  # Convert degrees to radians
```

### Pose (NamedTuple)
```python
Pose(position: Position, joints: Joints)
# Access: pose.position.x, pose.joints.j1, etc.
```

### MODE_PTP (IntEnum)
Motion modes for `move_to(..., mode=MODE_PTP.XXX)`:
- `JUMP_XYZ` (0x00) — Linear path in Cartesian space
- `MOVJ_XYZ` (0x01) — Joint interpolation in Cartesian space **(default)**
- `MOVL_XYZ` (0x02) — Linear interpolation in Cartesian space
- `JUMP_ANGLE` (0x03) — Jump in joint space
- `MOVJ_ANGLE` (0x04) — Joint interpolation in joint space
- `MOVL_ANGLE` (0x05) — Linear interpolation in joint space
- `MOVJ_INC` (0x06) — Incremental joint
- `MOVL_INC` (0x07) — Incremental linear
- `MOVJ_XYZ_INC` (0x08) — Incremental Cartesian
- `JUMP_MOVL_XYZ` (0x09) — Jump + linear

### CustomPosition
```python
CustomPosition(x=None, y=None, z=None, r=None)
# Usage: device.move_to(position=CustomPosition(x=200, y=50, z=50))
```

---

## Protocol Features

### What pydobotplus Adds vs. pydobot (luismesas)
1. **Normalized conveyor belt API** (0.0–1.0) instead of raw motor speeds
2. **Distance-based conveyor belt** (`conveyor_belt_distance`)
3. **Laser engraver** (`laze()`)
4. **Enhanced color sensor** support
5. **Better alarm enum** with detailed codes
6. **Queue command tracking** (`wait_for_cmd()`)
7. **Handheld teaching output** control
8. **Image engraving** (`engrave()`)

### What pydobot (older) Lacks
- Granular end-effector methods (suction vs. gripper separate)
- Arc motion with explicit center params
- Conveyor belt distance control
- Color sensor integration
- Laser support

---

## Comparison with dobot-python (Track B)

**dobot-python** (AlexGustafsson) provides significantly more low-level control.

### Ultra-Low-Level (Interface class)
- **175+ raw protocol methods**: `set_homing_parameters()`, `set_point_to_point_joint_params()`, `set_arc_params()`, etc.
- **Queue control**: `start_queue()`, `stop_queue()`, `clear_queue()`, `get_current_queue_index()`
- **Direct device commands**: WiFi config, device ID, firmware version, etc.
- **Real-time trajectory params**: `set_continous_trajectory_real_time_params()`
- **Lost-step recovery**: `set_lost_step_command()`, `set_lost_step_params()`
- **Sliding rail support**: (additional hardware axis)
- **IO multiplexing** and PWM control

### Mid-Level (Dobot wrapper class)
- `home()`, `move_to()`, `slide_to()`, `slide_to_relative()`, `move_to_relative()`
- `follow_path()`, `follow_path_relative()`
- `wait()` with optional queue index

**Key Differences**: dobot-python's `Interface` class exposes **protocol-level parameter setters** that pydobotplus **does not**:
- `set_point_to_point_joint_params()`
- `set_homing_parameters()` ← pydobotplus lacks this
- `set_arc_params()`
- `get_arc_params()`
- Real-time param streaming

---

## Notable Gaps in pydobotplus

1. **No joint-space motion**: Cannot command robot to move in joint angles directly
2. **No parameter getters**: Cannot read back PTP/jog/homing parameters
3. **No sliding rail support**
4. **No WiFi/device config**
5. **No continuous trajectory** (CT) or real-time trajectory
6. **No queue download/streaming** for large trajectory queues
7. **No lost-step recovery**

---

## Typical Usage Pattern

```python
from pydobotplus import Dobot, MODE_PTP, Alarm, CustomPosition

# Auto-detect port or specify explicitly
device = Dobot(port="/dev/ttyUSB0")  # or port=None for auto-detect

try:
    # Check for alarms
    alarms = device.get_alarms()
    if alarms:
        print(f"Active alarms: {alarms}")
        device.clear_alarms()
    
    # Set home position (once, stored in robot memory)
    device.set_home(200, 0, 100, 0)
    
    # Home the robot
    device.home()
    
    # Set motion parameters
    device.speed(velocity=150, acceleration=100)
    
    # Move to a position (absolute, Cartesian)
    device.move_to(x=250, y=50, z=80, wait=True)
    
    # Move relative
    device.move_rel(x=10, y=0, z=20, wait=True)
    
    # Arc motion with center point
    device.go_arc(x=300, y=50, z=80, r=0, 
                   cir_x=275, cir_y=50, cir_z=80, cir_r=0)
    
    # Control end effectors
    device.suck(True)   # Enable suction
    device.grip(False)  # Disable gripper
    
    # Conveyor belt (0.0–1.0 speed)
    device.conveyor_belt(speed=0.5, direction=1)
    
    # Wait for a specific queued command
    cmd_id = device.move_to(x=200, y=0, z=100, wait=False)
    device.wait_for_cmd(cmd_id)
    
finally:
    device.close()
```

---

## Recommendations for ME403 Labs

### Track A (pydobotplus) — Labs 1–4
✓ **Use for**:
  - Cartesian motion (move_to, move_rel)
  - End-effector control (suck, grip)
  - Basic motion planning
  - Alarm monitoring

✗ **Avoid if**:
  - You need joint-angle homing
  - You need advanced queue patterns
  - You need parameter introspection

### Track B (dobot-python) — Labs 5–8 (Advanced)
✓ **Use for**:
  - Joint-space motion (`Interface.set_point_to_point_command(1, j1, j2, j3, j4)`)
  - Parameter tuning (`Interface.set_homing_parameters(...)`)
  - Queue monitoring (`Interface.get_current_queue_index()`)
  - Real-time trajectory streaming
  - Sliding rail support

---

## Installation

### Simple (recommended for Labs 1–4)
```bash
pip install pydobotplus
```

### With fallback to pydobot
```bash
pip install pydobotplus pydobot
```

Both can coexist; select in scripts:
```python
from pydobotplus import Dobot  # Track A (higher-level)
# OR
from pydobot import Dobot      # Track C (legacy reference)
```

### For Track B (source checkout)
```bash
cd /path/for/vendor-code
git clone https://github.com/AlexGustafsson/dobot-python.git
# Add to sys.path in your scripts
```

---

## Error Handling

```python
from pydobotplus import DobotException

try:
    device = Dobot()
except DobotException as e:
    print(f"Failed to initialize: {e}")
    # Port not found, already in use, or permissions issue

try:
    device.move_to(x=999, y=999, z=999, wait=True)  # Out of bounds
except DobotException as e:
    print(f"Command failed: {e}")
```

---

## See Also

- `GUIDE.md` — Student lab guide with script-by-script walkthrough
- `dobot_control_options_comparison.md` — Comprehensive library comparison
- `Syllabus-ME403-202502.md` — Lab schedule
- `scripts/` — Runnable examples

