# 05: Practical Lab Examples (Python)

These examples are aligned with the scripts in this workspace and keep the same safety/cleanup patterns.

---

## 1. Minimal Connection + Pose (Track A: pydobotplus)

```python
import sys
from pydobotplus import Dobot
from utils import find_port, unpack_pose

port = find_port()
if port is None:
    sys.exit("No serial port found")

bot = Dobot(port=port)
try:
    x, y, z, r, j1, j2, j3, j4 = unpack_pose(bot.get_pose())
    print(f"X={x:.1f} Y={y:.1f} Z={z:.1f} R={r:.1f}")
finally:
    bot.close()
```

---

## 2. Safe Pick-and-Place Skeleton (Track A)

```python
import sys
import time
from pydobotplus import Dobot
from utils import find_port, safe_move, go_home

PICK = (220, -60, 30, 0)
PLACE = (220, 60, 30, 0)
LIFT = 60

port = find_port()
if port is None:
    sys.exit("No serial port found")

bot = Dobot(port=port)
try:
    go_home(bot)
    time.sleep(0.3)

    safe_move(bot, PICK[0], PICK[1], PICK[2] + LIFT, PICK[3])
    safe_move(bot, *PICK)
    bot.suck(True)
    time.sleep(0.4)
    safe_move(bot, PICK[0], PICK[1], PICK[2] + LIFT, PICK[3])

    safe_move(bot, PLACE[0], PLACE[1], PLACE[2] + LIFT, PLACE[3])
    safe_move(bot, *PLACE)
    bot.suck(False)
    time.sleep(0.3)
    safe_move(bot, PLACE[0], PLACE[1], PLACE[2] + LIFT, PLACE[3])
finally:
    try:
        bot.suck(False)
    except Exception:
        pass
    bot.close()
```

---

## 3. Queue-Based Circle (Track B: dobot-python `Interface`)

```python
import math
import sys
import time

sys.path.insert(0, "/absolute/path/to/dobot-python")  # or vendor/dobot-python if cloned there
from lib.interface import Interface
from utils import find_port

port = find_port()
if port is None:
    raise SystemExit("No serial port found")

bot = Interface(port)
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
