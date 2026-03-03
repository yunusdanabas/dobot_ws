# Circle Drawing with Dobot Magician — Complete Index

## Quick Links

| Resource | Purpose | Audience |
|----------|---------|----------|
| **This file** | Index & navigation | Everyone |
| [`circle_drawing_math.md`](circle_drawing_math.md) | Complete mathematical guide | Students & researchers |
| [`circle_arc_math_reference.md`](circle_arc_math_reference.md) | Quick reference with formulas | Students & programmers |
| [`scripts/11_circle_arcs.py`](../scripts/11_circle_arcs.py) | Working demo (4, 8, 12 arcs) | Hands-on learners |
| [`scripts/09_arc_motion.py`](../scripts/09_arc_motion.py) | **RECOMMENDED**: Sampled circles | ME403 labs |
| [`scripts/10_circle_queue.py`](../scripts/10_circle_queue.py) | High-throughput circles (Track B) | Advanced users |

---

## One-Minute Answer

**How many arc segments do you need for a full circle?**

- **Minimum:** 4 (90° each) → angular steps visible
- **Recommended:** 8 (45° each) → smooth motion, good speed
- **High quality:** 12+ (30° each) → visually perfect

**Via-point formula for arc i (out of N total):**

```python
via_angle = 2π·(i + 0.5) / N    # Midpoint angle
end_angle = 2π·(i + 1) / N      # Endpoint angle

via_x = cx + r·cos(via_angle)
via_y = cy + r·sin(via_angle)
end_x = cx + r·cos(end_angle)
end_y = cy + r·sin(end_angle)

bot.go_arc(x=end_x, y=end_y, z=z, r=rot,
           cir_x=via_x, cir_y=via_y, cir_z=z, cir_r=rot)
```

**Key insight:** Via-point is **ON the circle** (at the midpoint angle), **NOT** at the center!

---

## Two Approaches: Side-by-Side

### Approach 1: Sampled Points (RECOMMENDED)

**Pros:**
- ✓ Works on all firmware versions
- ✓ Easy to debug
- ✓ Smooth circles with 36–72 points

**Cons:**
- ✗ More commands
- ✗ Slower execution

**Example:**
```python
for i in range(36):
    angle = 2π·i / 36
    x = cx + r·cos(angle)
    y = cy + r·sin(angle)
    bot.move_to(x, y, z, rot, wait=True)
```

**Script:** [`scripts/09_arc_motion.py`](../scripts/09_arc_motion.py)

---

### Approach 2: go_arc() Decomposition (Research)

**Pros:**
- ✓ Firmware-native arc motion
- ✓ Fewer commands
- ✓ Potentially smoother execution

**Cons:**
- ✗ Firmware-dependent arc accuracy
- ✗ Via-point calculation must be exact
- ✗ Harder to debug if it fails

**Example:**
```python
for i in range(8):
    via_angle = 2π·(i + 0.5) / 8
    end_angle = 2π·(i + 1) / 8
    via_x = cx + r·cos(via_angle)
    via_y = cy + r·sin(via_angle)
    end_x = cx + r·cos(end_angle)
    end_y = cy + r·sin(end_angle)
    bot.go_arc(x=end_x, y=end_y, z=z, r=rot,
               cir_x=via_x, cir_y=via_y, cir_z=z, cir_r=rot)
```

**Script:** [`scripts/11_circle_arcs.py`](../scripts/11_circle_arcs.py)

---

## Math Deep Dive

### Circle Equation

For a circle centered at `(cx, cy)` with radius `r`:

```
x(θ) = cx + r·cos(θ)
y(θ) = cy + r·sin(θ)

where θ ∈ [0, 2π]
```

### Decomposing into N Arc Segments

Divide the circle into N equal parts. For the **i-th segment** (i = 0, 1, ..., N-1):

```
via_angle = 2π·(i + 0.5) / N     (midpoint)
end_angle = 2π·(i + 1) / N       (endpoint)
```

The via-point is placed at the **midpoint angle** on the circle to ensure the firmware arc passes through it smoothly.

### Worked Example: 4-Arc Circle

**Circle:** center=(220, 0), radius=40, z=100

```
Arc 0 (0°→90°):
  via at 45°:  (220 + 40·cos(45°), 0 + 40·sin(45°)) ≈ (248.3, 28.3)
  end at 90°:  (220, 40)

Arc 1 (90°→180°):
  via at 135°: (220 + 40·cos(135°), 40·sin(135°)) ≈ (191.7, 28.3)
  end at 180°: (180, 0)

Arc 2 (180°→270°):
  via at 225°: (220 + 40·cos(225°), 40·sin(225°)) ≈ (191.7, -28.3)
  end at 270°: (220, -40)

Arc 3 (270°→360°):
  via at 315°: (220 + 40·cos(315°), 40·sin(315°)) ≈ (248.3, -28.3)
  end at 360°: (260, 0)
```

See [`circle_arc_math_reference.md`](circle_arc_math_reference.md) for full details.

---

## Running the Demos

### Test 1: Sampled-Point Circle (Recommended)

```bash
cd /home/yunusdanabas/dobot_ws
source .venv/bin/activate
python scripts/09_arc_motion.py
```

Demonstrates:
- Simple arc with `go_arc()`
- Full circle with 36 sampled points
- Smaller circle with 24 points

---

### Test 2: go_arc() Decomposition (Research)

```bash
python scripts/11_circle_arcs.py
```

Demonstrates:
- 4-arc circle (90° per segment)
- 8-arc circle (45° per segment, smoother)
- 12-arc circle (30° per segment, highest quality)
- Smaller circle with 8 arcs

---

### Test 3: Track B High-Throughput (Advanced)

```bash
export DOBOT_PYTHON_PATH=/path/to/dobot-python
python scripts/10_circle_queue.py
```

Demonstrates:
- Queue-based command execution
- Medium-resolution (36 points)
- High-resolution (72 points)
- Small fast circles (24 points)

---

## Safety Checklist

- [ ] All waypoints (start, via, end) are within safe bounds:
  - 150 ≤ x ≤ 280 mm
  - −160 ≤ y ≤ 160 mm
  - 10 ≤ z ≤ 150 mm
  - −90 ≤ r ≤ 90°

- [ ] Use planar circles (constant z) — most reliable

- [ ] Speed ≤ 50 mm/s for arc motion

- [ ] Close DobotStudio/DobotDemo before running Python

- [ ] Test with small radius (≤ 50 mm) first

- [ ] Start from a known safe position

---

## Common Mistakes & Fixes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Using circle **center** as via-point | Arc goes nowhere | Remember: via-point is **ON the circle** |
| Via-point out of bounds | Robot alarm | Check all points satisfy safe bounds |
| Wrong via-point angle | Jerky motion | Use `(i + 0.5)` not `i` in angle calculation |
| Too many arcs (>12) | Very slow | Switch to sampled points instead |
| Floating-point rounding | Endpoint mismatch | Use `clamp()` to snap to safe bounds |

---

## For ME403 Students

**For labs:** Use `scripts/09_arc_motion.py` (sampled circles)
- More robust
- Easier to understand
- Meets all learning objectives
- Less likely to fail

**For projects:** Consider both approaches
- Sampled points: reliability and simplicity
- go_arc() decomposition: efficiency and study of firmware motion control

---

## References & Further Reading

- **[`arc_and_circles.md`](arc_and_circles.md)** — Original comprehensive guide with spirals, figure-eights
- **[`dobot_control_options_comparison.md`](../dobot_control_options_comparison.md)** — Hardware specs, all library syntaxes, queue patterns
- **[`CLAUDE.md`](../CLAUDE.md)** — Project context and library track overview
- **[`GUIDE.md`](../GUIDE.md)** — Student lab guide with script walkthrough

---

**Last Updated:** 2026-03-04  
**Files:** circle_drawing_index.md, circle_drawing_math.md, circle_arc_math_reference.md, scripts/11_circle_arcs.py
