# Dobot Magician Arc Motion & Circle Drawing Guide

## Quick Reference

| Method | Library | Use Case | Speed |
|--------|---------|----------|-------|
| `go_arc()` | pydobotplus / pydobot | Simple planar arcs | Fast ⚡ |
| Sampled circles | pydobotplus | Smooth 2D circles | Medium ⏱ |
| Queue circles | dobot-python `Interface` | High-resolution, dense | Fast ⚡ |
| Spirals/3D paths | pydobotplus | Complex trajectories | Slow 🐢 |

---

## Arc Motion with `go_arc()`

### Function Signature

```python
bot.go_arc(x, y, z, r, cir_x, cir_y, cir_z, cir_r)
```

### Parameters

| Parameter | Type | Unit | Meaning |
|-----------|------|------|---------|
| `x` | float | mm | Target endpoint X coordinate |
| `y` | float | mm | Target endpoint Y coordinate |
| `z` | float | mm | Target endpoint Z coordinate |
| `r` | float | deg | Target endpoint rotation |
| `cir_x` | float | mm | Via-point X (intermediate point on arc) |
| `cir_y` | float | mm | Via-point Y (intermediate point on arc) |
| `cir_z` | float | mm | Via-point Z (intermediate point on arc) |
| `cir_r` | float | deg | Via-point rotation (intermediate point on arc) |

### Key Concept: Via-Point vs. Center

❌ **NOT** a circle center definition  
✅ **IS** an intermediate point the arc passes through

The firmware calculates the arc:
```
Current Position → Via-Point → Target Endpoint
```

### Example: Simple Arc

```python
from pydobotplus import Dobot
from utils import find_port, safe_move

bot = Dobot(port=find_port())
try:
    # Start position
    safe_move(bot, 200, 0, 100, 0)
    
    # Arc from (200, 0) to (250, 50)
    # The arc passes through via-point (220, 30)
    bot.go_arc(
        x=250, y=50, z=100, r=0,        # Endpoint
        cir_x=220, cir_y=30, cir_z=100, cir_r=0  # Via-point
    )
finally:
    bot.close()
```

### Limitations & Cautions

| Issue | Impact | Mitigation |
|-------|--------|------------|
| Via-point must be within safe bounds | Will fail or crash if out of bounds | Check via-point before executing |
| Firmware arc support is limited | 3D arcs may not work; planar arcs (constant z) most reliable | Test with small arcs first |
| Not heavily tested in the wild | Unexpected behavior possible | Use backup sampled-point approach |

---

## Circle Drawing via Sampled Points (Recommended for Teaching)

### Why This Approach?

✅ **Reliable:** Works on all firmware versions  
✅ **Smooth:** High point density produces smooth circles  
✅ **Debuggable:** Each waypoint is a regular `move_to()` command  
✅ **Safe:** Easy to inspect and adjust

### Basic Implementation

```python
import math
from pydobotplus import Dobot
from utils import find_port, safe_move, go_home

def draw_circle(bot, center_x, center_y, z, radius, steps=36):
    """Draw circle by moving to sampled points."""
    for i in range(steps + 1):
        angle = 2 * math.pi * i / steps
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        bot.move_to(x, y, z, 0, wait=True)

bot = Dobot(port=find_port())
try:
    bot.speed(50, 40)  # Slow for smooth motion
    go_home(bot)
    
    # Draw 40mm circle centered at (220, 0) at height z=100
    draw_circle(bot, 220, 0, 100, 40, steps=36)
    
    go_home(bot)
finally:
    bot.close()
```

### Angular Resolution

| Steps | Delta angle | Use case |
|-------|-------------|----------|
| 12 | 30° | Very coarse (testing) |
| 24 | 15° | Coarse (small circles) |
| 36 | 10° | Default (smooth visual) |
| 72 | 5° | Fine (high-quality) |

**Recommendation:** Start with 36 steps; increase if jagged, decrease if slow.

---

## High-Throughput Circles with Track B (dobot-python Interface)

### Why Track B for Circles?

✅ **Efficient:** Queues all points at once, no per-command wait  
✅ **Monitored:** Explicit queue index backpressure  
✅ **Fast:** Minimal overhead between commands

### Implementation

```python
import math
import sys
import time

sys.path.insert(0, "/path/to/dobot-python")
from lib.interface import Interface
from utils import find_port

def draw_circle_fast(bot, center_x, center_y, z, radius, steps=72):
    """Draw circle using Track B queue."""
    vel, acc = 50, 40
    
    # Set speed for all commands
    bot.set_point_to_point_coordinate_params(vel, vel, acc, acc, queue=True)
    bot.set_point_to_point_common_params(vel, acc, queue=True)
    
    # Queue all points
    last_idx = None
    for i in range(steps + 1):
        angle = 2 * math.pi * i / steps
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        
        # mode=3 is linear Cartesian interpolation
        last_idx = bot.set_point_to_point_command(3, x, y, z, 0, queue=True)
    
    # Monitor queue until complete
    while bot.get_current_queue_index() < last_idx:
        time.sleep(0.05)

bot = Interface(find_port())
try:
    draw_circle_fast(bot, 220, 0, 100, 40, steps=72)
finally:
    bot.serial.close()
```

### Queue Mode Codes

| Code | Motion Type | Description |
|------|-------------|-------------|
| 0 | JUMP | Rapid jog (air move) |
| 1 | MOVJ_XYZ | Joint interpolation to Cartesian target |
| 2 | MOVL_XYZ | Linear Cartesian interpolation (smooth line) |
| 3 | **Cartesian Linear** | What you want for circles—smooth continuous path |

---

## Advanced: Spirals (Vertical Arcs)

### Implementation

```python
import math
from pydobotplus import Dobot
from utils import find_port, safe_move, go_home

def draw_spiral(bot, center_x, center_y, z_start, z_end, radius, steps=36):
    """Draw a spiral with height change."""
    for i in range(steps + 1):
        angle = 2 * math.pi * i / steps
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        z = z_start + (z_end - z_start) * i / steps  # Ramp height
        bot.move_to(x, y, z, 0, wait=True)

bot = Dobot(port=find_port())
try:
    bot.speed(50, 40)
    go_home(bot)
    
    # Spiral up from z=80 to z=120 with 40mm radius
    draw_spiral(bot, 220, 0, 80, 120, 40, steps=36)
    
    go_home(bot)
finally:
    bot.close()
```

### Output
```
Height increases as the arm rotates around the circle:
    * Start (z=80): 3 o'clock
    * Middle (z=100): 12 o'clock  
    * End (z=120): 9 o'clock (completing circle)
```

---

## Practical Example: Figure-Eight

```python
import math
from pydobotplus import Dobot
from utils import find_port, safe_move, go_home

def draw_figure_eight(bot, center_x, center_y, z, radius, steps=36):
    """Draw a figure-eight pattern."""
    for i in range(2 * steps + 1):
        t = 2 * math.pi * i / steps
        # Lemniscate equations (infinity symbol)
        denom = 1 + math.sin(t) ** 2
        x = center_x + (radius * math.cos(t)) / denom
        y = center_y + (radius * math.sin(t) * math.cos(t)) / denom
        bot.move_to(x, y, z, 0, wait=True)

bot = Dobot(port=find_port())
try:
    bot.speed(50, 40)
    go_home(bot)
    draw_figure_eight(bot, 220, 0, 100, 40, steps=36)
    go_home(bot)
finally:
    bot.close()
```

---

## Safety Checklist

- [ ] **Via-point in bounds:** All intermediate points must satisfy:
  - 150 mm ≤ x ≤ 280 mm
  - −160 mm ≤ y ≤ 160 mm
  - 10 mm ≤ z ≤ 150 mm
  - −90° ≤ r ≤ 90°

- [ ] **Speed profile:** Use 50 mm/s or slower for arcs

- [ ] **Small test radius:** Start with radius ≤ 50 mm

- [ ] **Validate visually:** Run demo first at slow speed before full execution

- [ ] **No table collision:** Z must always be ≥ 10 mm

- [ ] **Single process:** Close DobotStudio/DobotDemo before running Python

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Arc reaches wrong endpoint | Via-point miscalculated or out of bounds | Recalculate via-point; ensure it's within safe bounds |
| Circle is jagged (angular) | Too few steps | Increase steps (try 48 or 72) |
| Circle motion stops mid-way | Queue overflow or motion error | Reduce steps or increase monitoring interval |
| `go_arc()` fails/alarm | Firmware doesn't support 3D arcs | Use constant-z circles instead |
| Robot grinds during arc | Speed too high or illegal trajectory | Reduce velocity; check via-point validity |
| Suction cup falls off during circle | G-force too high | Reduce radius or speed |

---

## Running the Examples

### Track A (pydobotplus) — Recommended for Teaching

```bash
cd /home/yunusdanabas/dobot_ws
source .venv/bin/activate
python scripts/09_arc_motion.py
```

Demos:
1. Simple arc via `go_arc()`
2. Circle with 36 points
3. Smaller circle with 24 points

### Track B (dobot-python) — For Queue Studies

```bash
export DOBOT_PYTHON_PATH=/path/to/dobot-python
python scripts/10_circle_queue.py
```

Demos:
1. Medium-resolution circle (36 points)
2. High-resolution circle (72 points)
3. Small fast circle (24 points)

---

## References

- **Main API:** [`pydobotplus_api_detailed.md`](pydobotplus_api_detailed.md) — Full `go_arc()` docs
- **Library comparison:** [`research/03_api_comparison.md`](../research/03_api_comparison.md)
- **Code examples:** [`research/05_code_examples.md`](../research/05_code_examples.md)
- **Hardware specs:** [`dobot_control_options_comparison.md`](../dobot_control_options_comparison.md)
