# Dobot Circle Drawing: Arc Decomposition Math Reference

## TL;DR: How Many Arcs for a Full Circle?

| Configuration | Arcs | Angle/Arc | Quality | Speed |
|---|---|---|---|---|
| **Minimum** | 4 | 90° | Visible angular steps | ⚡ Fastest |
| **Standard** | 8 | 45° | Smooth, good tradeoff | Fast |
| **High quality** | 12+ | 30° | Visually perfect | Slower |

**Recommendation for labs:** Use **8 arcs** for balance, or switch to sampled `move_to()` points (36–72 steps) for robustness.

---

## Core Mathematics

### Circle Parametrization

A circle with center `(cx, cy)`, radius `r`, at height `z`:

```
x(θ) = cx + r·cos(θ)
y(θ) = cy + r·sin(θ)
z(θ) = z           (constant)
r(θ) = rot         (constant)

where: θ ∈ [0, 2π]
```

### Decomposing Circle into N Arc Segments

Divide the circle into `N` equal arcs. For the **i-th arc** (i = 0, 1, ..., N-1):

```
Arc i spans from angle:  θ_start = 2π·i / N
                to angle: θ_end   = 2π·(i+1) / N

The via-point (intermediate waypoint) is at the midpoint:
  θ_via = (θ_start + θ_end) / 2 = 2π·(i + 0.5) / N
```

### Computing Waypoints for Arc i

```
START position (from previous arc, or manually moved):
  x_start = cx + r·cos(θ_start)
  y_start = cy + r·sin(θ_start)

VIA-POINT (intermediate waypoint on the arc):
  x_via = cx + r·cos(θ_via)
  y_via = cy + r·sin(θ_via)

END position (target for this arc):
  x_end = cx + r·cos(θ_end)
  y_end = cy + r·sin(θ_end)
```

### Calling go_arc()

```python
bot.go_arc(
    x=x_end, y=y_end, z=z, r=rot,
    cir_x=x_via, cir_y=y_via, cir_z=z, cir_r=rot
)
```

---

## Worked Example: 4-Arc Circle

**Circle:** center=(220, 0), radius=40, z=100, rot=0

### Arc 0: 0° → 90° (via 45°)

```
θ_start = 0°
θ_via   = 45°
θ_end   = 90°

START: (220 + 40·cos(0°),   0 + 40·sin(0°))   = (260, 0)
VIA:   (220 + 40·cos(45°),  0 + 40·sin(45°))  = (220 + 28.28, 28.28) ≈ (248.3, 28.3)
END:   (220 + 40·cos(90°),  0 + 40·sin(90°))  = (220, 40)

bot.go_arc(x=220, y=40, z=100, r=0,
           cir_x=248.3, cir_y=28.3, cir_z=100, cir_r=0)
```

### Arc 1: 90° → 180° (via 135°)

```
θ_start = 90°
θ_via   = 135°
θ_end   = 180°

START: (220, 40)                          [from previous arc]
VIA:   (220 + 40·cos(135°), 40·sin(135°)) ≈ (191.7, 28.3)
END:   (220 + 40·cos(180°), 40·sin(180°)) = (180, 0)

bot.go_arc(x=180, y=0, z=100, r=0,
           cir_x=191.7, cir_y=28.3, cir_z=100, cir_r=0)
```

### Arc 2: 180° → 270° (via 225°)

```
θ_start = 180°
θ_via   = 225°
θ_end   = 270°

START: (180, 0)                           [from previous arc]
VIA:   (220 + 40·cos(225°), 40·sin(225°)) ≈ (191.7, -28.3)
END:   (220, -40)

bot.go_arc(x=220, y=-40, z=100, r=0,
           cir_x=191.7, cir_y=-28.3, cir_z=100, cir_r=0)
```

### Arc 3: 270° → 360° (via 315°)

```
θ_start = 270°
θ_via   = 315°
θ_end   = 360° (= 0°)

START: (220, -40)                         [from previous arc]
VIA:   (220 + 40·cos(315°), 40·sin(315°)) ≈ (248.3, -28.3)
END:   (260, 0)                           [back to start]

bot.go_arc(x=260, y=0, z=100, r=0,
           cir_x=248.3, cir_y=-28.3, cir_z=100, cir_r=0)
```

---

## Trigonometric Values Reference

For quick calculations:

```
cos(0°)    = 1.0000    sin(0°)    = 0.0000
cos(22.5°) = 0.9239    sin(22.5°) = 0.3827
cos(30°)   = 0.8660    sin(30°)   = 0.5000
cos(45°)   = 0.7071    sin(45°)   = 0.7071
cos(60°)   = 0.5000    sin(60°)   = 0.8660
cos(67.5°) = 0.3827    sin(67.5°) = 0.9239
cos(90°)   = 0.0000    sin(90°)   = 1.0000
cos(135°)  = -0.7071   sin(135°)  = 0.7071
cos(180°)  = -1.0000   sin(180°)  = 0.0000
cos(225°)  = -0.7071   sin(225°)  = -0.7071
cos(270°)  = 0.0000    sin(270°)  = -1.0000
cos(315°)  = 0.7071    sin(315°)  = -0.7071
```

---

## Comparison: Arcs vs. Sampled Points

### Using `go_arc()` (N=4,8,12 arcs)

**Pros:**
- Firmware-native arc motion (potentially smoother at execution)
- Fewer commands
- Lower overhead

**Cons:**
- Arc accuracy firmware-dependent
- Via-point calculation must be exact
- Harder to debug if arc fails
- Limited to planar arcs (constant z) on most firmware

### Using `move_to()` Sampled Points (36–72 points)

**Pros:**
- Highly predictable (each point is a regular linear move)
- Easy to debug (just linear interpolation)
- Works on all firmware versions
- Adjustable smoothness (increase points for finer granularity)

**Cons:**
- More commands = slower execution
- Robot waits between commands

**Recommendation:** For **teaching and labs**, use sampled points. For **research** or **protocol studies**, use `go_arc()`.

---

## Python Implementation Pattern

```python
import math
from pydobotplus import Dobot

def draw_circle_arcs(bot, cx, cy, z, radius, num_arcs, rot=0):
    """Draw circle using N arcs."""
    # Move to start (0°)
    start_x = cx + radius * math.cos(0)
    start_y = cy + radius * math.sin(0)
    bot.move_to(start_x, start_y, z, rot, wait=True)
    
    # Execute each arc
    for i in range(num_arcs):
        via_angle = 2 * math.pi * (i + 0.5) / num_arcs
        end_angle = 2 * math.pi * (i + 1) / num_arcs
        
        via_x = cx + radius * math.cos(via_angle)
        via_y = cy + radius * math.sin(via_angle)
        end_x = cx + radius * math.cos(end_angle)
        end_y = cy + radius * math.sin(end_angle)
        
        bot.go_arc(
            x=end_x, y=end_y, z=z, r=rot,
            cir_x=via_x, cir_y=via_y, cir_z=z, cir_r=rot
        )

# Usage:
bot = Dobot(port="/dev/ttyUSB0")
draw_circle_arcs(bot, cx=220, cy=0, z=100, radius=40, num_arcs=8)
bot.close()
```

---

## Common Mistakes & Fixes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Using circle **center** instead of via-point | Arc goes to wrong place | Remember: via-point is ON the circle, not at center |
| Via-point out of safe bounds | Robot alarm or crash | Verify all points (start, via, end) in bounds before calling |
| Incorrect via-point angle | Jerky arc motion | Via-point angle must be (i + 0.5) × (360/N)°, not (i × 360/N)° |
| Too many arcs (>12) | Motion is very slow | Use sampled points instead if you need >12 segments |
| Floating-point rounding | Arc endpoint doesn't match expected | Use `clamp()` to safe bounds before executing |
| 3D arc (changing z) | Unexpected trajectory | Keep z constant; use separate z moves if needed |

---

## See Also

- **`scripts/11_circle_arcs.py`** — Working demo with 4, 8, 12 arc examples
- **`scripts/09_arc_motion.py`** — Sampled-point circles (recommended for labs)
- **`scripts/10_circle_queue.py`** — Track B high-res circles (Queue API)
- **`ARC_AND_CIRCLES.md`** — Full guide with spirals, figure-eights, troubleshooting
