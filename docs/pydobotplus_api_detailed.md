# pydobotplus Complete Public API Reference

**Package Version:** 0.1.2 (as of July 10, 2024)  
**Source:** https://files.pythonhosted.org/packages/83/3e/607d0bd45dbec7651883c0aab89d6369e44c1fad9025025b7cc227bd9983/pydobotplus-0.1.2.tar.gz

---

## Main Classes

### Dobot (Primary Robot Control Class)

#### Constructor
```python
Dobot(port: Optional[str] = None) -> Dobot
```
- **port** (str, optional): Serial port name (e.g., `/dev/ttyUSB0`, `COM3`). If None, auto-detects port based on VID/PID.
- **Returns:** Dobot instance
- **Raises:** `DobotException` if no port found or serial connection fails
- Auto-clears any existing alarms on startup
- Initializes default motion parameters on connect

---

## Public Methods by Category

### Pose & Motion Queries

#### `get_pose() -> Pose`
Returns the current position and joint angles of the robot.
```python
pose = robot.get_pose()
# pose.position = Position(x, y, z, r)
# pose.joints = Joints(j1, j2, j3, j4)
```
- **Returns:** `Pose` named tuple with:
  - `position`: `Position(x: float, y: float, z: float, r: float)` in mm and degrees
  - `joints`: `Joints(j1: float, j2: float, j3: float, j4: float)` in degrees
  - `Joints` has `.in_radians()` method to convert to radians

---

### Core Motion Commands

#### `move_to(x=None, y=None, z=None, r=0, wait=True, mode=None, position=None) -> int`
Queue a linear or joint motion to absolute coordinates.
```python
# Using coordinates
cmd_id = robot.move_to(x=200, y=50, z=100, r=0, wait=True)

# Using Position object
cmd_id = robot.move_to(position=CustomPosition(x=200, y=50, z=100, r=0))
```
- **x** (float, optional): Cartesian x (mm). If None, maintains current x.
- **y** (float, optional): Cartesian y (mm). If None, maintains current y.
- **z** (float, optional): Cartesian z (mm). If None, maintains current z.
- **r** (float, default=0): End effector rotation (degrees). If None, maintains current r.
- **wait** (bool, default=True): Block until command execution completes (DON'T CHANGE unless necessary)
- **mode** (MODE_PTP enum, default=MODE_PTP.MOVJ_XYZ): Motion type (see MODE_PTP enum below)
- **position** (CustomPosition, optional): Alternative to x/y/z/r parameters
- **Returns:** Command queue index (int) for use with `wait_for_cmd()`

**Behavior:**
- Unspecified parameters retain their current values
- If neither position nor x/y/z provided, raises `ValueError`

---

#### `move_rel(x=0, y=0, z=0, r=0, wait=True) -> None`
Queue a relative motion from current position.
```python
robot.move_rel(x=10, y=-5, z=20)  # Move 10mm in x, -5mm in y, 20mm in z
```
- **x** (float, default=0): Relative x displacement (mm)
- **y** (float, default=0): Relative y displacement (mm)
- **z** (float, default=0): Relative z displacement (mm)
- **r** (float, default=0): Relative rotation (degrees)
- **wait** (bool, default=True): Block until execution completes
- **Returns:** None

**Behavior:** Reads current pose, adds deltas, calls `move_to()` internally.

---

#### `go_arc(x, y, z, r, cir_x, cir_y, cir_z, cir_r) -> int`
Queue a circular arc motion (interpolated via intermediate point).
```python
cmd_id = robot.go_arc(x=250, y=50, z=100, r=0,
                       cir_x=220, cir_y=50, cir_z=80, cir_r=0)
```
- **x, y, z, r** (float): Target endpoint coordinates (mm, degrees)
- **cir_x, cir_y, cir_z, cir_r** (float): Intermediate point (arc centerpoint) coordinates
- **Returns:** Command queue index (int)

**Note:** This is a planar arc; 3D arc support depends on firmware. Not heavily tested.

---

### End-Effector Control

#### `suck(enable: bool) -> int`
Enable or disable suction cup.
```python
cmd_id = robot.suck(True)   # Enable suction
robot.suck(False)           # Disable suction
```
- **enable** (bool): True to enable, False to disable
- **Returns:** Command queue index (int)

---

#### `grip(enable: bool) -> int`
Enable or disable gripper.
```python
cmd_id = robot.grip(True)   # Close/enable gripper
robot.grip(False)           # Open/disable gripper
```
- **enable** (bool): True to enable, False to disable
- **Returns:** Command queue index (int)

---

#### `laze(power=0, enable=False) -> int`
Enable or disable laser pointer (if attached).
```python
cmd_id = robot.laze(power=255, enable=True)
robot.laze(power=0, enable=False)
```
- **power** (int, 0–255, default=0): Laser power level (0 = off)
- **enable** (bool, default=False): Enable laser
- **Returns:** Command queue index (int)

**Note:** Power parameter has minimal effect on most hardware.

---

### Speed & Acceleration

#### `speed(velocity=100., acceleration=100.) -> None`
Set robot motion velocity and acceleration for all future moves.
```python
robot.speed(velocity=150, acceleration=200)
```
- **velocity** (float, default=100): Motion velocity (mm/s for Cartesian, deg/s for joint moves)
- **acceleration** (float, default=100): Motion acceleration (mm/s² or deg/s²)
- **Returns:** None
- **Behavior:** Blocks until both PTP common and coordinate params are set

---

### Home & Reference

#### `home() -> int`
Move to home position (predefined or set via `set_home()`).
```python
cmd_id = robot.home()
```
- **Returns:** Command queue index (int)
- **Default home:** (0, 0, 0, 0) unless changed with `set_home()`

---

#### `set_home(x, y, z, r=0.) -> None`
Define the home position coordinates.
```python
robot.set_home(x=200, y=0, z=100, r=0)
```
- **x, y, z** (float): Home position in Cartesian coordinates (mm)
- **r** (float, default=0): Home rotation (degrees)
- **Returns:** None
- **Note:** Does NOT move the robot; only sets the target for `home()` command

---

### Alarm Management

#### `get_alarms() -> Set[Alarm]`
Query all current alarms on the robot.
```python
alarms = robot.get_alarms()
if alarms:
    for alarm in alarms:
        print(f"Alarm: {alarm.name} (0x{alarm.value:02X})")
```
- **Returns:** Set of `Alarm` enum values
- **Returns empty set** if no alarms

---

#### `clear_alarms() -> None`
Clear all current alarms.
```python
robot.clear_alarms()
```
- **Returns:** None
- **Auto-called** on connection if alarms exist

**Supported Alarms (Alarm enum):**
- `COMMON_*`: Resetting, undefined instruction, file system, MCU/FPGA comm, angle sensor
- `PLAN_*`: Planning errors (singularity, IK calc, limits, repeat data, arc params, jump params, motion type, speed, etc.)
- `MOVE_*`: Move-time errors (singularity, IK calc, limits)
- `OVERSPEED_AXIS[1-4]`: Axis overspeed detected
- `LIMIT_AXIS[1-4]_POS/NEG`: Joint limit reached
- `LOSE_STEP_AXIS[1-4]`: Stepper motor lost steps
- `MOTOR_*` / `ENCODER_*`: Motor and encoder faults on axes (rear, front, Z, R)
- `MOTOR_ENDIO_*`: End-IO and CAN errors

---

### Conveyor Belt Control

#### `conveyor_belt(speed, direction=1, interface=0) -> None`
Run conveyor belt at specified speed.
```python
robot.conveyor_belt(speed=0.5, direction=1)   # Forward at 50%
robot.conveyor_belt(speed=0.75, direction=-1) # Backward at 75%
robot.conveyor_belt(speed=0, direction=1)     # Stop
```
- **speed** (float, 0.0–1.0): Relative speed (0 = off, 1.0 = max)
- **direction** (int, 1 or -1, default=1): 1 = forward, -1 = backward
- **interface** (int, 0 or 1, default=0): Motor interface port
- **Returns:** None
- **Raises:** `DobotException` if speed not in [0.0, 1.0] or direction invalid

---

#### `conveyor_belt_distance(speed_mm_per_sec, distance_mm, direction=1, interface=0) -> int`
Move conveyor belt a specified distance at given speed.
```python
cmd_id = robot.conveyor_belt_distance(speed_mm_per_sec=50, distance_mm=200, direction=1)
```
- **speed_mm_per_sec** (float): Speed in mm/s; **MUST be ≤ 100 mm/s**
- **distance_mm** (float): Distance to move (mm)
- **direction** (int, 1 or -1, default=1): 1 = forward, -1 = backward
- **interface** (int, 0 or 1, default=0): Motor interface port
- **Returns:** Command queue index (int)
- **Raises:** `DobotException` if speed > 100 mm/s

**Internal Calculation:**
```
MM_PER_REV = 34π ≈ 106.81 mm per revolution
distance_steps = (distance_mm / MM_PER_REV) × 3600 steps/rev
speed_steps_per_sec = (speed_mm_per_sec / MM_PER_REV) × 3600 × direction
```

---

### Color Sensor Control

#### `set_color(enable=True, port=PORT_GP2, version=0x1) -> int`
Enable or configure color sensor.
```python
cmd_id = robot.set_color(enable=True, port=Dobot.PORT_GP2, version=0x1)
```
- **enable** (bool, default=True): Enable/disable sensor
- **port** (int, default=PORT_GP2): Sensor port (see PORT_* constants below)
- **version** (int, 0 or 1, default=0x1): Sensor hardware version
- **Returns:** Command queue index (int)

---

#### `get_color(port=PORT_GP2, version=0x1) -> List[bool]`
Read RGB values from color sensor.
```python
rgb = robot.get_color(port=Dobot.PORT_GP2, version=0x1)
# Returns [r, g, b] where each is bool/byte
```
- **port** (int, default=PORT_GP2): Sensor port
- **version** (int, 0 or 1, default=0x1): Sensor hardware version
- **Returns:** List `[r, g, b]` where each component is a boolean or byte value

---

### IR Sensor Control

#### `set_ir(enable=True, port=PORT_GP4) -> int`
Enable IR sensor on specified port.
```python
cmd_id = robot.set_ir(enable=True, port=Dobot.PORT_GP4)
```
- **enable** (bool, default=True): Enable/disable IR sensor
- **port** (int, default=PORT_GP4): Sensor port (see PORT_* constants below)
- **Returns:** Command queue index (int)

---

#### `get_ir(port=PORT_GP4) -> bool`
Read IR sensor state.
```python
state = robot.get_ir(port=Dobot.PORT_GP4)
```
- **port** (int, default=PORT_GP4): Sensor port
- **Returns:** Boolean sensor state (True = object detected)

---

### I/O Control

#### `set_io(address: int, state: bool) -> None`
Set digital I/O pin state.
```python
robot.set_io(address=5, state=True)
robot.set_io(address=5, state=False)
```
- **address** (int, 1–22): I/O address (valid range: 1–22)
- **state** (bool): True = HIGH, False = LOW
- **Returns:** None
- **Raises:** `DobotException` if address not in 1–22 range
- **Behavior:** Blocks until command execution

---

### HHT Trigger (Hardware External Trigger)

#### `set_hht_trig_output(state: bool) -> None`
Enable/disable HHT (hand-held teach) trigger output.
```python
robot.set_hht_trig_output(True)   # Enable external trigger
robot.set_hht_trig_output(False)  # Disable
```
- **state** (bool): True = enable, False = disable
- **Returns:** None

---

#### `get_hht_trig_output() -> bool`
Read current HHT trigger output state.
```python
is_enabled = robot.get_hht_trig_output()
```
- **Returns:** Boolean state (True = enabled)

---

### Manual Jog Control (Low-Level)

#### `jog_x(v) -> None`
Jog (incremental move) along X axis.
```python
robot.jog_x(10)   # Move +10 in X
robot.jog_x(-5)   # Move -5 in X
```
- **v** (float): Velocity/distance (positive = +X, negative = -X, 0 = stop)
- **Returns:** None
- **Behavior:** Blocks until command execution

---

#### `jog_y(v) -> None`
Jog along Y axis.
```python
robot.jog_y(10)
```
- **v** (float): Velocity (positive = +Y, negative = -Y)
- **Returns:** None

---

#### `jog_z(v) -> None`
Jog along Z axis.
```python
robot.jog_z(5)
```
- **v** (float): Velocity (positive = +Z, negative = -Z)
- **Returns:** None

---

#### `jog_r(v) -> None`
Jog rotation (R axis).
```python
robot.jog_r(45)
```
- **v** (float): Rotation velocity (positive = CCW, negative = CW)
- **Returns:** None

---

### Queue Management

#### `wait_for_cmd(cmd_id: int) -> None`
Block until a queued command executes.
```python
cmd_id = robot.move_to(200, 50, 100)
robot.wait_for_cmd(cmd_id)  # Wait for completion
```
- **cmd_id** (int): Command queue index returned from move/motion commands
- **Returns:** None
- **Behavior:** Polls `_get_queued_cmd_current_index()` until it matches cmd_id
- **Note:** Already built into `move_to(..., wait=True)` by default

---

### Advanced / Internal Queue Control (Lower-level)

#### `_get_queued_cmd_current_index() -> int`
Get the current execution index in the motion queue.
```python
current = robot._get_queued_cmd_current_index()
```
- **Returns:** Current queue execution index (int)
- **Note:** Intended for internal use; for apps needing raw queue backpressure

---

### Connection

#### `close() -> None`
Close serial connection and shut down.
```python
robot.close()
```
- **Returns:** None
- **Important:** Call this before exiting to release the serial port

---

## Enums & Constants

### MODE_PTP (Point-to-Point Motion Modes)
```python
class MODE_PTP(IntEnum):
    JUMP_XYZ = 0x00       # Jump in Cartesian space
    MOVJ_XYZ = 0x01       # Joint interpolation → Cartesian target (default)
    MOVL_XYZ = 0x02       # Linear interpolation in Cartesian space
    JUMP_ANGLE = 0x03     # Jump in joint space
    MOVJ_ANGLE = 0x04     # Joint interpolation → joint target
    MOVL_ANGLE = 0x05     # Linear interpolation in joint space
    MOVJ_INC = 0x06       # Incremental joint move
    MOVL_INC = 0x07       # Incremental linear move
    MOVJ_XYZ_INC = 0x08   # Incremental XYZ with joint interp
    JUMP_MOVL_XYZ = 0x09  # Jump then linear move
```

**Note:** Default is `MODE_PTP.MOVJ_XYZ` (joint interpolation to Cartesian target). All modes use Cartesian targets except `MOVJ_ANGLE`, `MOVL_ANGLE`, `JUMP_ANGLE`.

---

### Sensor Port Constants
```python
Dobot.PORT_GP1 = 0x00  # GP1 port
Dobot.PORT_GP2 = 0x01  # GP2 port (color sensor default)
Dobot.PORT_GP4 = 0x02  # GP4 port (IR sensor default)
Dobot.PORT_GP5 = 0x03  # GP5 port
```

---

## Data Classes

### Position (NamedTuple)
```python
Position(x: float, y: float, z: float, r: float)
```
- Cartesian position: x, y, z in mm; r in degrees (rotation)

---

### Joints (NamedTuple)
```python
Joints(j1: float, j2: float, j3: float, j4: float)
```
- Joint angles in degrees; `j1` is base rotation, `j2/j3` arm, `j4` wrist
- Method: `.in_radians()` → returns Joints with all values in radians

---

### Pose (NamedTuple)
```python
Pose(position: Position, joints: Joints)
```
- Complete robot state from `get_pose()`

---

### CustomPosition (Class)
```python
CustomPosition(x=None, y=None, z=None, r=None)
```
- Mutable alternative to Position for `move_to(position=...)`
- Any unspecified param is None and interpreted as "keep current"

---

### Alarm (IntEnum)
Comprehensive list of 50+ alarm codes covering:
- Common errors (reset, file system, MCU/FPGA, angle sensor)
- Planning errors (singularity, IK, limits, motion type, speed)
- Motion errors
- Axis overspeed
- Joint limits
- Stepper motor faults
- Motor/encoder hardware faults (temperature, voltage, current, short, CAN)

---

## Exception Classes

### DobotException
```python
raise DobotException("Error message")
```
- Custom exception for Dobot-related errors
- Raised when: serial connection fails, port not found, invalid parameters, command fails

---

## Usage Patterns

### Basic Motion
```python
from dobotplus import Dobot, CustomPosition

robot = Dobot(port="/dev/ttyUSB0")
try:
    # Move to position
    robot.move_to(x=200, y=50, z=100)
    
    # Enable suction
    robot.suck(True)
    
    # Move home
    robot.home()
    
    # Close gripper
    robot.grip(True)
finally:
    robot.close()
```

### Queue Control (with manual backpressure)
```python
# Queue multiple moves
cmd_id1 = robot.move_to(200, 50, 100, wait=False)
cmd_id2 = robot.move_to(250, 75, 120, wait=False)
cmd_id3 = robot.move_to(150, 25, 80, wait=False)

# Wait for all to execute
robot.wait_for_cmd(cmd_id1)
robot.wait_for_cmd(cmd_id2)
robot.wait_for_cmd(cmd_id3)
```

### Motion Parameters
```python
robot.speed(velocity=150, acceleration=200)
robot.move_to(300, 100, 50)  # Uses new speed
```

---

## Important Notes

1. **Serial Port Ownership:** Only one process can own the port at a time. Close DobotStudio/DobotDemo before running Python scripts.

2. **Coordinates:** x, y, z in millimeters; r in degrees. Safe workspace typically x: 150–280 mm, y: −160–160 mm, z: 10–150 mm, r: −90–90°.

3. **Queue Buffering:** Default queue size is 32 commands. Use `wait=False` and `wait_for_cmd()` for high-throughput trajectories.

4. **Command Return Values:** Most motion commands return a command queue index (int), not True/False. Use `wait_for_cmd(index)` to wait synchronously.

5. **Wait Parameter:** Default `wait=True` blocks until the specific command finishes. Safe for interactive use but can serialize a trajectory. Set `wait=False` to queue moves and manage synchronization manually.

