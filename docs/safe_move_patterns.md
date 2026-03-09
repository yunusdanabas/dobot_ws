# safe_move() Pattern Comparison: Best Practices for Dobot Magician

## Executive Summary

The **current `safe_move()` pattern (clamp + move_to with wait=True)** is appropriate for most labs, but optimal safe_move design depends on your task:

| Aspect | Current Pattern | Better Pattern | When to Use |
|--------|-----------------|----------------|------------|
| **Axis clamping** | Independent clamp per axis | + 2D table collision check | Pick-place with lift |
| **Error handling** | Silent clamping | + Log warnings on clamp | Production/debugging |
| **Speed control** | Set before move | Set before move (same) | Both ✓ |
| **Gripper interlock** | Not implemented | Check vacuum/force feedback | Critical pick-place |

---

## (1) Combined Z + Lift Check (Avoid Table Collisions)

### Current Pattern
```python
# scripts/utils.py
def safe_move(bot, x: float, y: float, z: float, r: float, mode=None) -> None:
    x = clamp(x, *SAFE_BOUNDS["x"])  # Independent clamping
    y = clamp(y, *SAFE_BOUNDS["y"])
    z = clamp(z, *SAFE_BOUNDS["z"])  # Only checks Z alone
    r = clamp(r, *SAFE_BOUNDS["r"])
    if mode is not None:
        bot.move_to(x, y, z, r, wait=True, mode=mode)
    else:
        bot.move_to(x, y, z, r, wait=True)
```

**Problem:** If you call `safe_move(bot, 220, -60, 10, 0)` (Z=10 mm, already at ground level), then later try `safe_move(bot, 220, -60, 10, 0)` with a gripper open (simulating a 50 mm tall object), the robot hits the table.

### Better Pattern: Add Lift Validation
```python
SAFE_BOUNDS = {
    "x": (150, 280),
    "y": (-160, 160),
    "z": (10, 150),
    "r": (-90, 90),
}

MIN_TABLE_CLEARANCE = 5  # mm safety margin above table

def safe_move(bot, x: float, y: float, z: float, r: float, 
              lift: float = 0.0) -> None:
    """Move with optional lift parameter for pick-place approach.
    
    Args:
        lift: Height of attached object (mm). Used to validate
              z + lift does not hit table (z_ground = 10mm + clearance).
    """
    x = clamp(x, *SAFE_BOUNDS["x"])
    y = clamp(y, *SAFE_BOUNDS["y"])
    z = clamp(z, *SAFE_BOUNDS["z"])
    r = clamp(r, *SAFE_BOUNDS["r"])
    
    # Validate combined clearance: z + lift must be >= 10 + MIN_TABLE_CLEARANCE
    min_z = SAFE_BOUNDS["z"][0] + MIN_TABLE_CLEARANCE
    if z + lift < min_z:
        print(f"[Warning] Z={z} + lift={lift} would hit table "
              f"(min {min_z}); using z={min_z}")
        z = max(SAFE_BOUNDS["z"][0], min_z - lift)
    
    bot.move_to(x, y, z, r, wait=True)
```

### Usage in Pick-and-Place
```python
# scripts/08_pick_and_place.py
OBJECT_HEIGHT = 30  # mm (e.g., tall block)

def pick_up(bot):
    # Approach from above → always high enough
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R)  # No lift param needed; Z already high
    
    # Descend to pick (object on table, so effective Z is PICK_Z + OBJECT_HEIGHT)
    safe_move(bot, PICK_X, PICK_Y, PICK_Z, R, lift=OBJECT_HEIGHT)
```

**Benefit:** Prevents silent coordinate corruption in high-risk scenarios. Most labs won't need this, but it's essential for teams doing complex pick-place with variable object heights.

---

## (2) Error Handling: Silent Clamping vs. Exceptions

### Current Pattern (Clamp + Warn)

The current `utils.py` implementation already logs a warning when clamping occurs:

```python
def safe_move(bot, x: float, y: float, z: float, r: float, mode=None) -> None:
    cx = clamp(x, *SAFE_BOUNDS["x"])
    cy = clamp(y, *SAFE_BOUNDS["y"])
    cz = clamp(z, *SAFE_BOUNDS["z"])
    cr = clamp(r, *SAFE_BOUNDS["r"])
    if (cx, cy, cz, cr) != (x, y, z, r):
        print(f"[safe_move] Clamped: ({x:.1f},{y:.1f},{z:.1f},{r:.1f})"
              f" -> ({cx:.1f},{cy:.1f},{cz:.1f},{cr:.1f})")
    if mode is not None:
        bot.move_to(cx, cy, cz, cr, wait=True, mode=mode)
    else:
        bot.move_to(cx, cy, cz, cr, wait=True)
```

**Pros:**
- Never crashes on out-of-bounds coordinates.
- Student code runs to completion even if a coordinate is slightly wrong.

**Cons:**
- Hard to debug: student may not know their X=290 was silently clamped to X=280.
- Can hide coordinate/motion-planning errors for hours.

### Better Pattern: Log Warnings
```python
def safe_move(bot, x: float, y: float, z: float, r: float) -> None:
    orig = (x, y, z, r)
    x = clamp(x, *SAFE_BOUNDS["x"])
    y = clamp(y, *SAFE_BOUNDS["y"])
    z = clamp(z, *SAFE_BOUNDS["z"])
    r = clamp(r, *SAFE_BOUNDS["r"])
    
    if (x, y, z, r) != orig:
        clamped = (x, y, z, r)
        print(f"[Warning] Clamped move: {orig} → {clamped}")
    
    bot.move_to(x, y, z, r, wait=True)
```

### Optional: Strict Mode (Raise on Violation)
```python
def safe_move_strict(bot, x: float, y: float, z: float, r: float) -> None:
    """Raises ValueError if any axis is out of bounds."""
    bounds_ok = all([
        SAFE_BOUNDS["x"][0] <= x <= SAFE_BOUNDS["x"][1],
        SAFE_BOUNDS["y"][0] <= y <= SAFE_BOUNDS["y"][1],
        SAFE_BOUNDS["z"][0] <= z <= SAFE_BOUNDS["z"][1],
        SAFE_BOUNDS["r"][0] <= r <= SAFE_BOUNDS["r"][1],
    ])
    
    if not bounds_ok:
        raise ValueError(
            f"Coordinate out of bounds: x={x} {SAFE_BOUNDS['x']}, "
            f"y={y} {SAFE_BOUNDS['y']}, z={z} {SAFE_BOUNDS['z']}, "
            f"r={r} {SAFE_BOUNDS['r']}"
        )
    
    bot.move_to(x, y, z, r, wait=True)
```

### Recommendation
- **For labs 1–4 (FK/IK learning):** Use the warning version (easier to debug).
- **For production code / autonomous systems:** Use strict mode or warning + fallback.
- **Never silently clamp without logging** — defeats the purpose of bounds checking.

---

## (3) Velocity Ramp & Speed Parameters

### Current Pattern
```python
# scripts/04_speed_control.py
bot.speed(vel, acc)          # Set global speed/accel
safe_move(bot, x, y, z, r)  # Uses whatever speed was last set
```

**Current behavior:**
- `bot.speed(velocity, acceleration)` sets robot parameters globally.
- Remains active until overwritten.
- All subsequent moves use that speed until changed.

### Better Practice: Always Set Speed Before Critical Moves
```python
# Pattern A: Set once at startup
def main():
    bot = Dobot(port=PORT)
    bot.speed(SAFE_VELOCITY, SAFE_ACCELERATION)  # ← Set baseline
    
    safe_move(bot, *READY_POSE)  # Uses baseline
    pick_up(bot)                  # Uses baseline
    place_down(bot)               # Uses baseline

# Pattern B: Override for specific moves
def pick_up(bot):
    # Slow down for approach
    bot.speed(50, 40)
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R)
    
    # Normal speed for descent
    bot.speed(100, 80)
    safe_move(bot, PICK_X, PICK_Y, PICK_Z, R)
    
    # Fast lift (already high)
    bot.speed(150, 100)
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R)
```

### Enhanced safe_move with Speed Parameter (Optional)
```python
def safe_move(bot, x: float, y: float, z: float, r: float,
              velocity: float | None = None, 
              acceleration: float | None = None) -> None:
    """Move with optional per-call speed override.
    
    Args:
        velocity: mm/s. If None, uses robot's current speed setting.
        acceleration: mm/s². If None, uses robot's current accel setting.
    """
    x = clamp(x, *SAFE_BOUNDS["x"])
    y = clamp(y, *SAFE_BOUNDS["y"])
    z = clamp(z, *SAFE_BOUNDS["z"])
    r = clamp(r, *SAFE_BOUNDS["r"])
    
    if velocity is not None and acceleration is not None:
        bot.speed(velocity, acceleration)
    
    bot.move_to(x, y, z, r, wait=True)
```

**Usage:**
```python
safe_move(bot, x, y, z, r, velocity=50, acceleration=40)  # Slow approach
safe_move(bot, x, y, z, r, velocity=100, acceleration=80)  # Normal
```

### Recommendation
- **Set baseline speed once at startup** (like `04_speed_control.py` does).
- **Safe defaults are already in utils.py:**
  - `SAFE_VELOCITY = 100 mm/s` (~33% of max)
  - `SAFE_ACCELERATION = 80 mm/s²`
- **Only override per-move if you have a specific reason** (slow descent, fast lift).
- **Do NOT let speed drift** — always reset after tuning for debugging.

---

## (4) Gripper/Suction Interlock: Vacuum Sensor & Force Feedback

### Current Pattern (No Interlock)
```python
# scripts/08_pick_and_place.py
def pick_up(bot):
    safe_move(bot, PICK_X, PICK_Y, PICK_Z, R)
    bot.suck(True)             # ← No check that vacuum succeeded
    time.sleep(0.4)            # Hope vacuum builds in 0.4s
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R)  # Lift (object may fall!)
```

**Risk:** If suction fails (seal leak, wrong end-effector), the robot lifts an ungripped object and drops it.

### Better Pattern 1: Timeout + Vacuum Sensor Check (pydobotplus)
```python
def pick_up_safe(bot) -> bool:
    """Perform safe pick with interlock check.
    
    Returns:
        True if pick succeeded, False if vacuum failed.
    """
    safe_move(bot, PICK_X, PICK_Y, PICK_Z, R)
    
    print("  Suction ON ...")
    bot.suck(True)
    
    # Poll vacuum sensor (if available in your API)
    # Note: pydobotplus may not expose vacuum sensor directly.
    # This pattern assumes a sensor reading method exists.
    vacuum_built = False
    for attempt in range(5):  # 5 attempts × 0.1s = 0.5s timeout
        time.sleep(0.1)
        try:
            # Hypothetical sensor API:
            if hasattr(bot, 'get_vacuum_pressure'):
                pressure = bot.get_vacuum_pressure()
                if pressure > 50:  # Threshold in arbitrary units
                    vacuum_built = True
                    break
        except Exception:
            pass
    
    if not vacuum_built:
        print("  [ERROR] Vacuum failed. Aborting pick.")
        bot.suck(False)
        return False
    
    print("  Lift ...")
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R)
    return True
```

**Current limitation:** `pydobotplus` does not expose vacuum sensor reads. **Check your hardware manual** for sensor availability.

### Better Pattern 2: Force Feedback Check (Advanced)
If your Dobot has a force-torque sensor on the end-effector:

```python
def pick_up_with_force_check(bot) -> bool:
    """Perform pick with weight verification."""
    safe_move(bot, PICK_X, PICK_Y, PICK_Z, R)
    
    bot.suck(True)
    time.sleep(0.3)
    
    # Check if object has weight by reading Z-axis force
    # Hypothetical API: (requires force-torque sensor)
    if hasattr(bot, 'get_force_torque'):
        fx, fy, fz, tx, ty, tz = bot.get_force_torque()
        if abs(fz) < 0.5:  # No downward force = object not picked
            print("  [ERROR] No object detected. Aborting.")
            bot.suck(False)
            return False
    
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R)
    return True
```

### Better Pattern 3: Gripper Force Limit (Mechanical Gripper)
```python
def grip_safe(bot) -> bool:
    """Close gripper with torque limit."""
    bot.grip(True)
    
    # Hypothetical: set gripper force limit before gripping
    if hasattr(bot, 'set_gripper_force'):
        bot.set_gripper_force(80)  # % of max grip force
    
    time.sleep(0.5)  # Let gripper settle
    
    # Check if gripper detected an object by measuring grip position
    # (Some grippers return open/closed state, not force)
    if hasattr(bot, 'get_gripper_position'):
        pos = bot.get_gripper_position()
        if pos > 50:  # Still mostly open = nothing in grip
            print("  [ERROR] Gripper failed to close on object.")
            bot.grip(False)
            return False
    
    return True
```

### Practical Fallback: Conservative Timing (No Sensor)
If your hardware doesn't expose sensors, use **longer wait times + manual verification**:

```python
def pick_up_with_wait(bot):
    """Simple interlock: just wait longer and watch."""
    safe_move(bot, PICK_X, PICK_Y, PICK_Z, R)
    
    print("  Suction ON (watching for grip) ...")
    bot.suck(True)
    time.sleep(1.0)  # Wait 1s instead of 0.4s for vacuum to build
    
    # Operator should confirm suction worked before continuing
    print("  [Manual] Did the suction cup grip the object? (Y/N) ", end="")
    resp = input().strip().lower()
    if resp != "y":
        print("  Aborting pick.")
        bot.suck(False)
        return False
    
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R)
    return True
```

---

## Summary: Pattern Recommendations by Use Case

### Labs 1–3 (FK/IK, Basic Motion)
```python
# scripts/utils.py — Use current pattern with optional warning
def safe_move(bot, x, y, z, r):
    x, y, z, r = clamp(x, *SAFE_BOUNDS["x"]), clamp(y, *SAFE_BOUNDS["y"]), \
                 clamp(z, *SAFE_BOUNDS["z"]), clamp(r, *SAFE_BOUNDS["r"])
    bot.move_to(x, y, z, r, wait=True)
```

**Why:** Simple, reliable, sufficient for teaching FK/IK concepts.

### Lab 4 (Pick-and-Place, Simple)
```python
# Baseline + warnings for clamps
def safe_move(bot, x, y, z, r):
    orig, x, y, z, r = (x, y, z, r), clamp(x, ...), clamp(y, ...), \
                       clamp(z, ...), clamp(r, ...)
    if (x, y, z, r) != orig:
        print(f"[Warning] Clamped: {orig} → {(x, y, z, r)}")
    bot.move_to(x, y, z, r, wait=True)

# With conservative suction timing
def pick_up(bot):
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R)
    safe_move(bot, PICK_X, PICK_Y, PICK_Z, R)
    bot.suck(True)
    time.sleep(1.0)  # Increased from 0.4s
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R)
```

**Why:** Simple, still safe, catches common mistakes.

### Advanced Projects (Autonomous Pick-Place, Trajectory Labs)
```python
# Enhanced safe_move with lift check + speed parameter
def safe_move(bot, x, y, z, r, lift=0.0, velocity=None, acceleration=None):
    # Clamp axes
    x = clamp(x, *SAFE_BOUNDS["x"])
    y = clamp(y, *SAFE_BOUNDS["y"])
    z = clamp(z, *SAFE_BOUNDS["z"])
    r = clamp(r, *SAFE_BOUNDS["r"])
    
    # Validate lift
    min_z = SAFE_BOUNDS["z"][0] + 5
    if z + lift < min_z:
        z = max(SAFE_BOUNDS["z"][0], min_z - lift)
    
    # Set speed if provided
    if velocity and acceleration:
        bot.speed(velocity, acceleration)
    
    bot.move_to(x, y, z, r, wait=True)

# Pick with interlock (or fallback to manual check)
def pick_up(bot):
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R, velocity=80, acceleration=60)
    safe_move(bot, PICK_X, PICK_Y, PICK_Z, R, lift=OBJECT_HEIGHT)
    
    bot.suck(True)
    time.sleep(0.5)
    
    # Sensor check (if available)
    if hasattr(bot, 'get_vacuum_pressure'):
        if bot.get_vacuum_pressure() < 50:
            raise RuntimeError("Suction failed")
    
    safe_move(bot, PICK_X, PICK_Y, PICK_Z + LIFT, R, lift=OBJECT_HEIGHT, 
              velocity=120, acceleration=100)
```

**Why:** Catches design flaws early, prevents silent failures, speeds up development.

---

## Implementation Checklist

- [ ] **Review your `safe_move()` in `scripts/utils.py`**
  - [x] Clamp warning already implemented (`[safe_move] Clamped: ...`)
  - [x] Optional `mode` parameter already implemented (pass `MODE_PTP.*` enum)
  - [ ] Add optional `lift` parameter (for advanced pick-place height validation)
  - [ ] Add optional `velocity/acceleration` override (for advanced projects)

- [ ] **Check suction timing in `08_pick_and_place.py`**
  - [ ] Increase `time.sleep()` from 0.4s → 1.0s
  - [ ] OR add vacuum sensor check if available
  - [ ] OR add manual confirmation prompt

- [ ] **Document assumptions in your scripts**
  - [ ] What end-effector is attached (suction vs. gripper)?
  - [ ] What object heights are you assuming?
  - [ ] What speed is baseline?

- [ ] **Test edge cases**
  - [ ] What happens if `safe_move(bot, 280, 160, 10, 90)` is called (all axes maxed)?
  - [ ] What happens if suction fails mid-cycle?
  - [ ] What happens if robot loses connection?

---

## References

- **Current implementation:** `scripts/utils.py`, `scripts/04_speed_control.py`, `scripts/08_pick_and_place.py`
- **API reference:** `docs/pydobotplus_api_reference.md` (pydobotplus methods)
- **Hardware specs:** Dobot Magician datasheet (check workspace bounds, max velocities)
- **Troubleshooting:** `GUIDE.md` section "Common Issues"
