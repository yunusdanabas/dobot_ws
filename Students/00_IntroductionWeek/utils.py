"""
utils.py — Shared helpers for Dobot Magician lab scripts (ME403).

Import in any script:
    from utils import (
        clamp, safe_move, go_home, do_homing, unpack_pose,
        prepare_robot, check_alarms,
        HOME_JOINTS, SAFE_READY_POSE, SAFE_BOUNDS, DOBOT_KEYWORDS, find_port
    )

This module also applies _patch_pydobotplus() at import time, which fixes two
upstream bugs in pydobotplus.Dobot.move_to: an unconditional get_pose() serial
round-trip (~20-50 ms) and an unconditional print(current_pose) that would
otherwise appear on every move command.  The patch is transparent to callers.
"""

import time

from serial.tools import list_ports

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOME_JOINTS = (0, 0, 0, 0)  # J1, J2, J3, J4 (deg) — joint-space home
SAFE_READY_POSE = (200, 0, 100, 0)  # X, Y, Z (mm), R (deg) — Cartesian staging pose

# Operating safe bounds — minimal clearance from hard limits.
# All motion commands are clamped here; safe_move() will warn when clamping.
SAFE_BOUNDS = {
    "x": (120, 315),   # 5 mm from base singularity / max reach
    "y": (-158, 158),  # 2 mm margin
    "z": (5, 155),     # 5 mm above table, 5 mm below ceiling
    "r": (-90, 90),    # keep ±90° to avoid cable wrap
}

# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------

# Dobot Magician uses either CP210x (Silicon Labs) or CH340 (1A86) USB-serial chips
DOBOT_KEYWORDS = ("Silicon Labs", "1A86", "USB2.0-Serial")


def find_port(keywords: tuple[str, ...] = DOBOT_KEYWORDS) -> str | None:
    """Return the first serial port matching any *keywords* (description or hwid).

    Falls back to the first USB port (ttyUSB*, ttyACM*) if no keyword match.
    Avoids ttyS* on Linux (virtual/COM ports that often cause I/O errors).
    Returns None if no ports are found at all.
    """
    ports = list(list_ports.comports())
    desc_hwid = lambda p: f"{(p.description or '')} {p.hwid}".lower()
    for p in ports:
        combined = desc_hwid(p)
        if any(kw.lower() in combined for kw in keywords):
            return p.device
    # Fallback: prefer USB ports over ttyS* (ttyS often fails with I/O error)
    usb_ports = [p for p in ports if "/ttyUSB" in p.device or "/ttyACM" in p.device]
    if usb_ports:
        return usb_ports[0].device
    return ports[0].device if ports else None


# ---------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------

def clamp(v: float, lo: float, hi: float) -> float:
    """Clamp *v* to the closed interval [lo, hi]."""
    return max(lo, min(hi, v))


def unpack_pose(pose) -> tuple[float, float, float, float, float, float, float, float]:
    """Normalize pose feedback to a flat 8-tuple.

    Supports:
    - pydobotplus Pose(position=..., joints=...)
    - Flat 8-element tuple/list as returned by pydobot and dobot-python parsers
    """
    if hasattr(pose, "position") and hasattr(pose, "joints"):
        return (
            float(pose.position.x),
            float(pose.position.y),
            float(pose.position.z),
            float(pose.position.r),
            float(pose.joints.j1),
            float(pose.joints.j2),
            float(pose.joints.j3),
            float(pose.joints.j4),
        )

    if isinstance(pose, (tuple, list)) and len(pose) == 8:
        return tuple(float(v) for v in pose)

    raise ValueError(f"Unsupported pose format: {type(pose)!r}")


def safe_move(bot, x: float, y: float, z: float, r: float, mode=None,
              bounds: dict | None = None) -> None:
    """Move *bot* to (x, y, z, r) after clamping each axis to SAFE_BOUNDS.

    Prints a warning when any coordinate is clamped.
    Optional *mode* sets the PTP motion mode (e.g. MODE_PTP.MOVL_XYZ).
    """
    b = bounds or SAFE_BOUNDS
    cx = clamp(x, *b["x"])
    cy = clamp(y, *b["y"])
    cz = clamp(z, *b["z"])
    cr = clamp(r, *b["r"])
    if (cx, cy, cz, cr) != (x, y, z, r):
        print(f"[safe_move] Clamped: ({x:.1f},{y:.1f},{z:.1f},{r:.1f})"
              f" -> ({cx:.1f},{cy:.1f},{cz:.1f},{cr:.1f})")
    if mode is not None:
        bot.move_to(cx, cy, cz, cr, wait=True, mode=mode)
    else:
        bot.move_to(cx, cy, cz, cr, wait=True)


def go_home(bot) -> None:
    """Send *bot* to joint-space home (0, 0, 0, 0)."""
    from pydobotplus.dobotplus import MODE_PTP
    bot.move_to(*HOME_JOINTS, wait=True, mode=MODE_PTP.MOVJ_ANGLE)
    print("[utils] At home: joint zero (0, 0, 0, 0)")


def check_alarms(bot) -> None:
    """Warn if the robot has active alarms; clears them. Call after connecting.

    Prints each alarm's name so students can identify the fault quickly.
    If no alarms are active, returns silently.
    """
    alarms = bot.get_alarms()
    if alarms:
        print(f"[check_alarms] WARNING: {len(alarms)} alarm(s) detected:")
        for a in alarms:
            print(f"  {a.name}")
        bot.clear_alarms()
        print("[check_alarms] Alarms cleared.")


def do_homing(bot) -> None:
    """Run the robot homing sequence. Call after power-on or when LIMIT_* alarms occur.

    Power-on position is NOT home. The robot must be homed to establish its
    coordinate frame before motion. Homing moves the arm to physical limit
    switches and calibrates encoders. Takes ~15-30 seconds.
    """
    print("[do_homing] Running homing sequence (15-30 s) ...")
    bot.home()
    time.sleep(25)  # homing takes 15-30 s; home() may not block
    print("[do_homing] Homing complete.")


def prepare_robot(bot) -> None:
    """Clear alarms and run homing if LIMIT alarms were present.

    Call right after connecting:
        bot = Dobot(port=PORT)
        prepare_robot(bot)
    """
    alarms = bot.get_alarms()
    if alarms:
        print(f"[prepare_robot] Clearing {len(alarms)} alarm(s):")
        for a in alarms:
            print(f"  {getattr(a, 'name', a)}")
        bot.clear_alarms()
        if any(getattr(a, "name", "").find("LIMIT") >= 0 for a in alarms):
            do_homing(bot)


# ---------------------------------------------------------------------------
# pydobotplus compatibility patch (applied automatically on import)
# ---------------------------------------------------------------------------

def _patch_pydobotplus() -> None:
    """Patch pydobotplus.Dobot.move_to to remove two upstream bugs:

    1. Unconditional get_pose() call — the upstream implementation always
       queries the robot's current position (a serial round-trip of ~20-50 ms)
       even when all x/y/z/r coordinates are supplied by the caller.
    2. Unconditional print(current_pose) — prints "Position(x=..., y=...,
       z=..., r=...)" to stdout on every call, cluttering terminal output and
       overwriting status lines in teleop scripts.

    This patch skips both when x, y, z are all supplied.  Falls back to the
    original for partial-coordinate calls so move_to(z=50) still works.
    Applied once at module import; silently does nothing if pydobotplus
    internals change.
    """
    try:
        import pydobotplus.dobotplus as _dp
        from pydobotplus.dobotplus import MODE_PTP

        _orig = _dp.Dobot.move_to

        def _fast_move_to(self, x=None, y=None, z=None, r=0,
                          wait=True, mode=None, position=None):
            if position is not None:
                x, y, z, r = position.x, position.y, position.z, position.r
            if x is None or y is None or z is None:
                # Partial call: fall back to original (needs get_pose for Nones)
                return _orig(self, x=x, y=y, z=z, r=r, wait=wait, mode=mode)
            if mode is None:
                mode = MODE_PTP.MOVJ_XYZ
            return self._extract_cmd_index(
                self._set_ptp_cmd(x, y, z, r, mode, wait=wait)
            )

        _dp.Dobot.move_to = _fast_move_to
    except Exception:
        pass  # graceful degradation if pydobotplus internals change


_patch_pydobotplus()
