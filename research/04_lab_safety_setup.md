# 04: Lab Safety & Setup Guidelines (ME403)

These constraints are the baseline for first-time Dobot use in ME403 labs.

---

## 1. Safe Workspace Bounds

| Axis | Min | Max | Why |
|---|---|---|---|
| X | 150 mm | 280 mm | Avoid base singularity region |
| Y | -160 mm | 160 mm | Keep base rotation conservative |
| Z | 10 mm | 150 mm | Avoid table collision |
| R | -90 deg | 90 deg | Avoid cable wrap |

Use these exact bounds in all scripts and documentation.

---

## 2. Startup Procedure

1. Confirm USB cable and wall adapter are both connected.
2. Close DobotStudio/DobotDemo before running Python scripts.
3. Verify serial permission (`dialout` group on Linux).
4. Run `scripts/01_find_port.py`.
5. Run `scripts/02_first_connection.py`.

---

## 3. Safe Helper Pattern

```python
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def safe_move(bot, x, y, z, r):
    safe_x = clamp(x, 150, 280)
    safe_y = clamp(y, -160, 160)
    safe_z = clamp(z, 10, 150)
    safe_r = clamp(r, -90, 90)
    bot.move_to(safe_x, safe_y, safe_z, safe_r, wait=True)
```

---

## 4. Cleanup Discipline

Always close the connection in `finally` blocks:

```python
bot = Dobot(port=PORT)
try:
    # robot commands
    ...
finally:
    bot.close()
```

For Track B (`lib.interface.Interface`), use `bot.serial.close()`.

---

## 5. Failure Patterns to Watch

- Grinding/clicking sounds: stop immediately and re-home.
- `Permission denied`: fix Linux group membership.
- No motion with valid commands: check wall power and serial-port ownership.
