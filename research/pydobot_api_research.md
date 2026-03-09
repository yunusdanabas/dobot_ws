# pydobot Library Research – API Patterns & Architecture

**Repository:** https://github.com/ZdenekM/pydobot  
**Based on:** Dobot Communication Protocol v1.1.4  
**Last researched:** 2026-03-08

---

## Installation

```bash
# Standard pip installation
pip install pydobot

# Requires serial driver from Silicon Labs
# https://www.silabs.com/products/development-tools/software/usb-to-uart-bridge-vcp-drivers
```

---

## Key Classes & Types

### `Dobot` (Main API)

**Constructor:**
```python
Dobot(port: Optional[str] = None, verbose: bool = False)
```

- **port**: Serial port name (auto-detected if `None` by checking VID 4292 or 6790)
- **verbose**: Print serial comms to console for debugging
- Raises `DobotException` if device not found or port fails to open
- Auto-initializes on connection:
  - Starts queued command execution
  - Clears any existing queue
  - Sets default PTP joint/coordinate parameters
  - Clears any existing alarms

**Lifecycle:**
```python
device = Dobot(port="/dev/ttyUSB0")
# ... use device
device.close()  # Must close serial connection
```

---

### Data Types (NamedTuple-based)

**Position:**
```python
Position(x: float, y: float, z: float, r: float)
```
- Cartesian coordinates in **mm** (x, y, z) and **degrees** (r = rotation/end-effector angle)

**Joints:**
```python
Joints(j1: float, j2: float, j3: float, j4: float)
```
- Joint angles in **degrees**
- `.in_radians()` → returns `Joints` with angles converted to radians

**Pose:**
```python
Pose(position: Position, joints: Joints)
```
- Complete robot state returned by `get_pose()`

**Alarm (IntEnum):**
- 100+ distinct alarm codes for motor, sensor, and motion errors
- Examples: `LIMIT_AXIS1_POS`, `PLAN_INV_LIMIT`, `MOTOR_FRONT_OVERHEAT`

---

## Core API Methods

### Motion Control

#### `get_pose() → Pose`
Queries current robot state synchronously.

```python
pose = device.get_pose()
x, y, z, r = pose.position.x, pose.position.y, pose.position.z, pose.position.r
j1, j2, j3, j4 = pose.joints.j1, pose.joints.j2, pose.joints.j3, pose.joints.j4
```

---

#### `move_to(x, y, z, r=0.0, mode=MODE_PTP.MOVJ_XYZ) → int`
Queue a point-to-point move command; **returns command ID** (integer).

```python
cmd_id = device.move_to(x=200, y=50, z=100, r=0, mode=MODE_PTP.MOVJ_XYZ)
# Returns immediately; command is queued for execution
```

**Parameters:**
- `x, y, z`: Target Cartesian coordinates in **mm**
- `r`: End-effector rotation in **degrees** (default 0)
- `mode`: Motion type (see `MODE_PTP` enum below)

**Returns:** Command index/ID for queue tracking

**Motion Modes (MODE_PTP enum):**
| Mode | Value | Description |
|------|-------|-------------|
| `JUMP_XYZ` | 0x00 | Jump in Cartesian space |
| `MOVJ_XYZ` | 0x01 | Move to XYZ via joint interpolation (default) |
| `MOVL_XYZ` | 0x02 | Linear move in Cartesian space |
| `JUMP_ANGLE` | 0x03 | Jump in joint space |
| `MOVJ_ANGLE` | 0x04 | Move via joint interpolation |
| `MOVL_ANGLE` | 0x05 | Linear move in joint space |
| `MOVJ_XYZ_INC` | 0x08 | Incremental move from current position |
| `JUMP_MOVL_XYZ` | 0x09 | Jump then linear move |

---

#### `speed(velocity=100.0, acceleration=100.0) → None`
Set velocity and acceleration for future moves (affects all subsequent commands).

```python
device.speed(velocity=150, acceleration=50)
device.move_to(...)  # Uses new speeds
```

**Notes:** Internally updates both PTP common params and coordinate params.

---

#### `home() → int`
Move to home position; returns command ID.

```python
cmd_id = device.home()
device.wait_for_cmd(cmd_id)  # Block until completed
```

---

#### `set_home(x, y, z, r=0.0) → None`
Redefine home position.

```python
device.set_home(x=200, y=0, z=100, r=0)
```

---

### Synchronization & Queue Management

#### `wait_for_cmd(cmd_id: int) → None`
**Blocking** call that polls queue index until command completes.

```python
cmd_id = device.move_to(200, 50, 100, 0)
device.wait_for_cmd(cmd_id)  # Block here until motion done
print("Motion complete")
```

**Internal implementation:**
- Polls `_get_queued_cmd_current_index()` in a loop
- Only one process can own the serial port; use this for inter-process sync

---

#### `_get_queued_cmd_current_index() → int`
Get current queue execution index (private method, but accessible).

```python
current = device._get_queued_cmd_current_index()
# Returns -1 on failure; otherwise integer index
```

---

### End Effector Control

#### `suck(enable: bool) → int`
Enable/disable suction cup.

```python
device.suck(enable=True)
device.wait_for_cmd(device.suck(enable=False))
```

**Returns:** Command ID

---

#### `grip(enable: bool) → int`
Enable/disable gripper.

```python
device.grip(enable=True)
device.wait_for_cmd(device.grip(enable=False))
```

**Returns:** Command ID

---

#### `laze(power: int = 0, enable: bool = False) → int`
Control laser output (0–255 power).

```python
device.laze(power=255, enable=True)
device.wait_for_cmd(device.laze(power=0, enable=False))
```

**Returns:** Command ID

---

### Jog / Incremental Motion

Four methods for manual jogging in each axis:

```python
device.jog_x(velocity)   # +v: right, -v: left
device.jog_y(velocity)   # +v: forward, -v: backward
device.jog_z(velocity)   # +v: up, -v: down
device.jog_r(velocity)   # +v: CW, -v: CCW
```

**Behavior:**
- Sets coordinate velocity params to `abs(velocity)`
- Sends jog command (dir depends on sign)
- **Blocks** in `wait_for_cmd()` until jog completes

---

### Arc Motion

#### `go_arc(x, y, z, r, cir_x, cir_y, cir_z, cir_r) → int`
Execute arc motion via circular intermediate point.

```python
cmd_id = device.go_arc(
    x=250, y=50, z=100, r=0,        # End point
    cir_x=225, cir_y=25, cir_z=100, cir_r=0  # Circle center/intermediate
)
device.wait_for_cmd(cmd_id)
```

**Returns:** Command ID

---

### Alarm Management

#### `get_alarms() → Set[Alarm]`
Query all active alarms.

```python
alarms = device.get_alarms()
if alarms:
    print(f"Active alarms: {alarms}")
```

**Returns:** Set of `Alarm` enum values (empty if none)

---

#### `clear_alarms() → None`
Clear all active alarms.

```python
device.clear_alarms()
```

---

### Digital I/O

#### `set_io(address: int, state: bool) → None`
Set digital output.

```python
device.set_io(address=1, state=True)   # Turn on IO 1
device.set_io(address=5, state=False)  # Turn off IO 5
```

**Valid addresses:** 1–22

---

### Advanced / Specialty

#### `conveyor_belt(speed, direction=1, interface=0) → None`
Control stepper motor (conveyor).

```python
device.conveyor_belt(speed=70, direction=1)  # speed: 0.0–1.0
```

---

#### `engrave(image, pixel_size, low=0.0, high=40.0, ...) → None`
Shade-engrave a NumPy grayscale image (advanced).

```python
from PIL import Image
import numpy as np

im = Image.open("image.jpg").convert("L")
im_array = np.array(im)
device.engrave(im_array, pixel_size=0.1, low=0.0, high=40.0)
```

---

## Message Protocol (Low-level)

### Message Structure

**Byte format:**
```
[0xAA, 0xAA, length, id, ctrl, ...params, checksum]
```

- **Header:** `0xAA 0xAA` (2 bytes)
- **Length:** Payload length = 2 + len(params)
- **ID:** Command ID (10=get_pose, 84=move_ptp, etc.)
- **Ctrl:** Control byte (0x00=query, 0x01=exec, 0x02=params, 0x03=set)
- **Params:** Variable-length data (floats/ints packed as little-endian)
- **Checksum:** `(256 - (id + ctrl + sum(params)) % 256) % 256`

### Message Class

```python
from pydobot.message import Message

msg = Message()
msg.id = 84  # PTP command
msg.ctrl = 0x03  # Set control
msg.params = bytearray([mode_byte, ...packed_floats])

bytes_to_send = msg.bytes()  # Calculates checksum, format
```

---

## Important Constraints & Patterns

### Serial Port Exclusivity
- **Only one process** can own the port at a time
- DobotStudio/DobotDemo must be closed
- No concurrent Python scripts on same port

### Queue Management
- Commands are queued (max 32 commands)
- `wait_for_cmd(cmd_id)` blocks; use for synchronization
- Don't spam faster than robot consumes (queue will back up)
- Always track returned command IDs for async patterns

### Coordinate System
- **x, y, z** in **mm**
- **r** (end-effector rotation) in **degrees**
- **Joints** in **degrees**
- Small test deltas recommended (5–10 mm)

### Lock Pattern
- Internal `RLock` protects serial reads/writes
- Safe for multi-threaded use within same process

---

## Initialization Sequence (Auto)

When `Dobot()` is instantiated:

1. **Clear queue** – `_set_queued_cmd_clear()`
2. **Set PTP joint params** – velocities/accelerations for each axis
3. **Set PTP coordinate params** – Cartesian motion parameters
4. **Set jump params** – Z-axis jump height & limit
5. **Set common params** – Default velocity/acceleration
6. **Start queue execution** – `_set_queued_cmd_start_exec()`
7. **Query & clear alarms** – Get active alarms, auto-clear if any

---

## Exception Handling

```python
from pydobot import Dobot, DobotException

try:
    device = Dobot()
except DobotException as e:
    print(f"Failed to connect: {e}")
```

---

## Example Workflow

```python
from serial.tools import list_ports
from pydobot import Dobot

# Discover port
port = list_ports.comports()[0].device

# Connect
device = Dobot(port=port, verbose=True)

# Get current pose
pose = device.get_pose()
print(f"Current position: {pose.position}")

# Move to new location (queued, non-blocking)
cmd_id = device.move_to(x=220, y=50, z=80, r=0)

# Wait for move to complete (blocking)
device.wait_for_cmd(cmd_id)

# Grab with gripper
device.grip(enable=True)

# Return home
home_cmd = device.home()
device.wait_for_cmd(home_cmd)

# Cleanup
device.close()
```

---

## Differences from pydobotplus & dobot-python

| Aspect | pydobot | pydobotplus | dobot-python |
|--------|---------|-------------|--------------|
| **Status** | Stable, legacy | Fork of pydobot | Advanced queue patterns |
| **API** | `.move_to()` → cmd_id | `.move_to()` → blocks | `.lib.interface.Interface` |
| **Sync** | `.wait_for_cmd()` | Built-in blocking | Queue index polling |
| **Types** | NamedTuple (Pose) | Tuple unpacking | Dict-based responses |
| **Extras** | Engrave, IO | Motion profiles | Full protocol access |

---

## Troubleshooting

### "Device not found!"
- Check USB cable
- Run `list_ports.comports()` to find actual port
- Verify VID (4292 or 6790) in device descriptor

### Serial timeout / no response
- Only one process can own port → close DobotStudio
- Check baud rate (hardcoded 115200 in pydobot)
- Increase `serial` timeout if polling slow

### Motion doesn't execute
- Check `wait_for_cmd()` didn't timeout
- Verify speed/acceleration are set (not zero)
- Check robot not in alarm state → `get_alarms()`

### Queue fills up
- Don't queue more than ~30 commands before polling
- Use `wait_for_cmd()` periodically to drain queue

---

## References

- **Protocol**: Dobot Communication Protocol v1.1.4 (official)
- **GitHub**: https://github.com/ZdenekM/pydobot
- **PyPI**: https://pypi.org/project/pydobot/
- **Driver**: Silicon Labs USB-UART bridge drivers
