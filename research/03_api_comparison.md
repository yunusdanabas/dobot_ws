# 03: API Differences & Key Syntax (ME403)

The three tracks share the same Dobot serial protocol but expose different Python surfaces.

## 1. Connection / Imports

| Track | Import | Construct |
|---|---|---|
| A (`pydobotplus`) | `from pydobotplus import Dobot` | `bot = Dobot(port=PORT)` |
| B (`dobot-python`) | `from lib.interface import Interface` | `bot = Interface(PORT)` |
| C (`pydobot`) | `from pydobot import Dobot` | `bot = Dobot(port=PORT, verbose=False)` |

> Track B requires adding the cloned repo root to `sys.path`.

## 2. Pose Feedback

| Track | Call | Return type |
|---|---|---|
| A | `bot.get_pose()` | `Pose(position, joints)` |
| B | `bot.get_pose()` | Flat 8-tuple `(x, y, z, r, j1, j2, j3, j4)` |
| C | `bot.pose()` | Flat 8-tuple `(x, y, z, r, j1, j2, j3, j4)` |

In course scripts, `unpack_pose()` is used to normalize Track A output.

## 3. Movement

| Track | Core movement call | Blocking/queue behavior |
|---|---|---|
| A | `bot.move_to(x, y, z, r, wait=True)` | `wait=True` blocks until completion |
| B | `bot.set_point_to_point_command(mode, x, y, z, r, queue=True)` | Queued; monitor with `get_current_queue_index()` |
| C | `bot.move_to(x, y, z, r, wait=True)` | `wait=True` blocks |

## 4. Speed Configuration

| Track | API |
|---|---|
| A | `bot.speed(velocity, acceleration)` |
| B | `bot.set_point_to_point_coordinate_params(...)` + `bot.set_point_to_point_common_params(...)` |
| C | `bot.speed(velocity, acceleration)` |

## 5. End-Effector Control

| Function | Track A / C | Track B (`Interface`) |
|---|---|---|
| Suction | `bot.suck(True/False)` | `set_end_effector_suction_cup(enable_control, enable_suction, queue=True)` |
| Gripper | `bot.grip(True/False)` | `set_end_effector_gripper(enable_control, enable_grip, queue=True)` |

## 6. Cleanup

| Track | Cleanup |
|---|---|
| A | `bot.close()` |
| B | `bot.serial.close()` |
| C | `bot.close()` |

## 7. Recommendation

- Use Track A as the default teaching track.
- Introduce Track B when queue semantics are a learning objective.
- Keep Track C for compatibility checks with older code.
