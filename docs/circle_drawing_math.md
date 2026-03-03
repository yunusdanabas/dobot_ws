# Drawing Circles with Dobot Magician: Mathematics & Implementation

## Quick Answer: Arc Decomposition

**For a full circle using `go_arc()`: You need exactly 4 arc segments** to complete one full 360° circle, assuming each arc is a quarter circle (90°).

---

## Understanding `go_arc()` Parameters

```python
bot.go_arc(x, y, z, r, cir_x, cir_y, cir_z, cir_r)
```

| Parameter | Meaning |
|-----------|---------|
| `(x, y, z, r)` | **Target endpoint** of the arc |
| `(cir_x, cir_y, cir_z, cir_r)` | **Via-point** (intermediate point the arc passes through) |
| **Current position** | (implicitly) The arc starts from where the arm currently is |

**Key insight:** The firmware traces an arc:
```
Current Position → Via-Point → Target Endpoint
```

The via-point is **NOT** the circle center—it's an intermediate waypoint on the arc itself.

---

## Mathematical Decomposition: 2D Planar Circle into 4 Arcs

### Setup

- **Circle center:** `(cx, cy)` at height `z`
- **Circle radius:** `r`
- **Number of arc segments:** 4 (90° each)
- **Fixed rotation:** `rot = 0`

### Quarter-Circle Arc Calculation

For a circle divided into 4 equal quarter-circles, the via-point is positioned at **45°** (midpoint) of each quarter-arc.

#### **Arc 1: 0° → 90°**

```
Start:     (cx + r,  cy,      z, rot)  = Current position
Via-point: (cx + r/√2, cy + r/√2, z, rot)  (45° angle)
End:       (cx,      cy + r,  z, rot)  (90° angle)
```

**Calculation:**
```
cos(45°) = 1/√2 ≈ 0.7071
sin(45°) = 1/√2 ≈ 0.7071

via_x = cx + r * cos(45°) = cx + r/√2
via_y = cy + r * sin(45°) = cy + r/√2
```

#### **Arc 2: 90° → 180°**

```
Start:     (cx,      cy + r,  z, rot)
Via-point: (cx - r/√2, cy + r/√2, z, rot)  (135° angle)
End:       (cx - r,  cy,      z, rot)
```

#### **Arc 3: 180° → 270°**

```
Start:     (cx - r,  cy,      z, rot)
Via-point: (cx - r/√2, cy - r/√2, z, rot)  (225° angle)
End:       (cx,      cy - r,  z, rot)
```

#### **Arc 4: 270° → 360°**

```
Start:     (cx,      cy - r,  z, rot)
Via-point: (cx + r/√2, cy - r/√2, z, rot)  (315° angle)
End:       (cx + r,  cy,      z, rot)  (back to start)
```

### Generalized Formula for N Arc Segments

For **any number of arc segments** `N`:

```
For segment i (i = 0, 1, 2, ..., N-1):
  start_angle   = 2π * i / N
  via_angle     = 2π * (i + 0.5) / N     (midpoint)
  end_angle     = 2π * (i + 1) / N

  start_x = cx + r * cos(start_angle)
  start_y = cy + r * sin(start_angle)

  via_x = cx + r * cos(via_angle)
  via_y = cy + r * sin(via_angle)

  end_x = cx + r * cos(end_angle)
  end_y = cy + r * sin(end_angle)

  bot.go_arc(
      x=end_x, y=end_y, z=z, r=rot,
      cir_x=via_x, cir_y=via_y, cir_z=z, cir_r=rot
  )
```

---

## Why 4 Arcs? (Or more?)

### Considerations:

| Factor | Impact | Recommendation |
|--------|--------|-----------------|
| Firmware arc accuracy | Firmware may not handle large arcs (>90°) well | Use 4–8 arcs |
| Smoothness | More arcs = smoother circle | For teaching, 4–8; for visual quality, 12+ |
| Execution time | More arcs = longer runtime | Trade-off with accuracy |
| Via-point feasibility | Via-point must be in bounds | Easier to guarantee with smaller arcs |

**Practical choice:** **Use 8 arcs (45° each)** for a good balance of smoothness and safety.

---

## Working Code Example: Circle via 4 `go_arc()` Calls

```python
#!/usr/bin/env python3
"""
Draw a circle using 4 go_arc() calls (quarter-circle arcs).
"""

import math
import sys
import time
from pydobotplus import Dobot
from utils import find_port, safe_move, go_home

def draw_circle_arcs(bot, center_x, center_y, z, radius, num_arcs=4, rot=0):
    """
    Draw a circle using go_arc() segments.
    
    Args:
        bot: Dobot instance
        center_x, center_y: Circle center
        z: Fixed height (mm)
        radius: Circle radius (mm)
        num_arcs: Number of arc segments (default 4 = quarter-circles)
        rot: End-effector rotation (degrees)
    """
    print(f"\n📍 Drawing circle with {num_arcs} arc(s)")
    print(f"   Center: ({center_x}, {center_y}), Z={z}, Radius={radius} mm")
    
    # Move to start of first arc (angle = 0°)
    start_angle = 0
    start_x = center_x + radius * math.cos(start_angle)
    start_y = center_y + radius * math.sin(start_angle)
    
    print(f"   Moving to start: ({start_x:.1f}, {start_y:.1f})")
    safe_move(bot, start_x, start_y, z, rot)
    time.sleep(0.3)
    
    # Execute each arc segment
    for i in range(num_arcs):
        via_angle = 2 * math.pi * (i + 0.5) / num_arcs
        end_angle = 2 * math.pi * (i + 1) / num_arcs
        
        via_x = center_x + radius * math.cos(via_angle)
        via_y = center_y + radius * math.sin(via_angle)
        
        end_x = center_x + radius * math.cos(end_angle)
        end_y = center_y + radius * math.sin(end_angle)
        
        print(f"   Arc {i+1}/{num_arcs}: "
              f"via=({via_x:.1f}, {via_y:.1f}) → "
              f"end=({end_x:.1f}, {end_y:.1f})")
        
        bot.go_arc(
            x=end_x, y=end_y, z=z, r=rot,
            cir_x=via_x, cir_y=via_y, cir_z=z, cir_r=rot
        )
        time.sleep(0.2)
    
    print(f"   ✓ Circle complete")


def draw_circle_8arcs(bot, center_x, center_y, z, radius):
    """Convenience: draw circle with 8 arcs (45° each, smoother)."""
    draw_circle_arcs(bot, center_x, center_y, z, radius, num_arcs=8)


def demo():
    """Demonstrate circle drawing with multiple arc counts."""
    port = find_port()
    if port is None:
        sys.exit("❌ No serial port found. Run: python scripts/01_find_port.py")
    
    bot = Dobot(port=port)
    try:
        print("✓ Connected to Dobot")
        
        bot.speed(50, 40)  # 50 mm/s, 40 mm/s² acceleration
        print("✓ Speed set to 50 mm/s")
        
        go_home(bot)
        time.sleep(0.5)
        
        # === Test 1: 4-arc circle (quarter-circles) ===
        print("\n" + "="*60)
        print("TEST 1: 4-arc circle (90° arcs)")
        print("="*60)
        draw_circle_arcs(bot, 220, 0, 100, 40, num_arcs=4)
        time.sleep(1)
        go_home(bot)
        time.sleep(0.5)
        
        # === Test 2: 8-arc circle (45° arcs, smoother) ===
        print("\n" + "="*60)
        print("TEST 2: 8-arc circle (45° arcs, smoother)")
        print("="*60)
        draw_circle_8arcs(bot, 220, 0, 100, 40)
        time.sleep(1)
        go_home(bot)
        time.sleep(0.5)
        
        # === Test 3: Smaller circle with 8 arcs ===
        print("\n" + "="*60)
        print("TEST 3: Smaller circle (radius=25mm, 8 arcs)")
        print("="*60)
        draw_circle_arcs(bot, 200, -60, 100, 25, num_arcs=8)
        time.sleep(1)
        go_home(bot)
        time.sleep(0.5)
        
        print("\n" + "="*60)
        print("✓ All tests completed successfully!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            go_home(bot)
        except Exception:
            pass
        bot.close()
        print("✓ Connection closed")


if __name__ == "__main__":
    demo()
```

---

## Comparison: `go_arc()` vs. Sampled Points

| Method | Pros | Cons | Use Case |
|--------|------|------|----------|
| **4× `go_arc()` (quarter-circles)** | Firmware-native, smooth, efficient | Limited precision, firmware-dependent | Research, protocol studies |
| **36 sampled `move_to()` points** | Highly reliable, debuggable, adjustable | Slower, more commands | Teaching, labs, safety-critical |
| **72+ sampled points (Track B queue)** | Smooth, high-throughput, monitorable | More complex setup | Visual quality, demos |

**Recommendation for ME403 labs:** Use **sampled points** (36–72 steps) for reliability; use `go_arc()` only for protocol exploration.

---

## Safety Checklist for Arc Motion

- [ ] **Via-point in bounds:** All points (start, via, end) must satisfy:
  - 150 ≤ x ≤ 280 mm
  - −160 ≤ y ≤ 160 mm
  - 10 ≤ z ≤ 150 mm
  - −90 ≤ r ≤ 90°

- [ ] **Planar circles (constant z):** Most reliable; avoid 3D arcs unless tested

- [ ] **Slow speed:** Use ≤50 mm/s for arc motion

- [ ] **No DobotStudio:** Close DobotStudio/DobotDemo before running Python

- [ ] **Start from known position:** Always `safe_move()` to a valid starting point before arcs

---

## Running the Code

### Using the 4-arc demo:

```bash
cd /home/yunusdanabas/dobot_ws
source .venv/bin/activate

# Run the demo with 4, 8, and 8 arc tests
python scripts/circle_arc_demo.py
```

### Using the existing sampled-circle scripts:

```bash
# Track A (pydobotplus) — recommended
python scripts/09_arc_motion.py

# Track B (dobot-python queue) — high-res
python scripts/10_circle_queue.py
```

---

## Mathematical References

### Parametric Circle Equation
```
x(θ) = cx + r·cos(θ)
y(θ) = cy + r·sin(θ)

where:
  θ ∈ [0, 2π]
  (cx, cy) = circle center
  r = radius
```

### Arc Via-Point Placement
For a circular arc from angle θ₁ to θ₂, the via-point at the midpoint θ_mid = (θ₁ + θ₂) / 2:
```
via_x = cx + r·cos(θ_mid)
via_y = cy + r·sin(θ_mid)
```

This ensures the arc passes through the exact midpoint of the intended circular arc.

---

## See Also

- **`ARC_AND_CIRCLES.md`** — Full guide with spirals, figure-eights, troubleshooting
- **`scripts/09_arc_motion.py`** — Working demo (sampled circles)
- **`scripts/10_circle_queue.py`** — Track B high-res circles
- **`dobot_control_options_comparison.md`** — Hardware specs and safety bounds
