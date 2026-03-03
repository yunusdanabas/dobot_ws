# 02: Official Dobot SDK Options (ME403 Notes)

Dobot's official tools are useful for calibration and diagnostics, but classroom scripting in ME403 is centered on pure-Python community libraries.

## 1. Official DLL Wrapper SDK

- Uses vendor binaries via `ctypes` (`DobotDll.dll` / `.so`).
- Works, but setup is fragile across operating systems and Python environments.
- Best reserved for vendor-specific features not exposed elsewhere.

## 2. DobotStudio / DobotStudio Pro

- Convenient GUI for calibration, homing, and quick checks.
- Not ideal for teaching reproducible Python workflows.
- Must be closed before running course scripts (serial-port ownership conflict).

## 3. ME403 Practical Stack (recommended)

| Track | Library | Setup | Typical use |
|---|---|---|---|
| A | `pydobotplus` | `pip install pydobotplus` | Intro labs and safe motion |
| B | `dobot-python` | Source checkout (`git clone ...`) | Queue/protocol trajectory labs |
| C | `pydobot` | `pip install pydobot` | Legacy API reference |

## Conclusion

For first-time students:

1. Use Track A scripts in `scripts/`.
2. Keep bounds enforced through `safe_move()`.
3. Move to Track B only when queue index monitoring is required.
