"""
utils.py — Shared helpers for Dobot Magician lab scripts (ME403).

Import in any script:
    from utils import (
        clamp, safe_move, safe_rel_move, go_home, do_homing, unpack_pose,
        prepare_robot, check_alarms,
        HOME_JOINTS, SAFE_READY_POSE, HARD_LIMITS, SAFE_BOUNDS, CONSERVATIVE_BOUNDS,
        JUMP_HEIGHT, SPEED_SMOOTH, SPEED_DEFAULT, find_port
    )

This module also applies _patch_pydobotplus() at import time. The patch removes
an unnecessary get_pose() round-trip and a noisy print() in the upstream
move_to() implementation.
"""

import time

from serial.tools import list_ports

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOME_JOINTS = (0, 0, 0, 0)  # J1, J2, J3, J4 (deg) — joint-space home
SAFE_READY_POSE = (200, 0, 100, 0)  # X, Y, Z (mm), R (deg) — Cartesian staging pose
READY_POSE = SAFE_READY_POSE  # backward compat

# Physical/firmware hard limits — used only for visualization reference.
# Do NOT use these as motion targets; they are the boundaries the firmware
# enforces (or where joint singularities/cable-wrap risks begin).
HARD_LIMITS = {
    "x": (115, 320),   # full Cartesian reach envelope
    "y": (-160, 160),  # arm geometry limit
    "z": (0, 160),     # 0 mm = table surface; 160 mm = firmware ceiling
    "r": (-135, 135),  # servo range (cable-wrap risk past ±90°)
}

# Operating safe bounds — minimal clearance from hard limits.
# All motion commands are clamped here; safe_move() will warn when clamping.
SAFE_BOUNDS = {
    "x": (120, 315),   # was (150,280) — 5 mm from base singularity / max reach
    "y": (-158, 158),  # was (-160,160) — 2 mm margin
    "z": (5, 155),     # was (10,150) — 5 mm above table, 5 mm below ceiling
    "r": (-90, 90),    # keep ±90° to avoid cable wrap despite servo ±135° range
}

# Tighter bounds for demos — stays well inside reachable workspace to avoid
# POSE_LIMIT_OVER and joint limits. Use when SAFE_BOUNDS targets hit limits.
CONSERVATIVE_BOUNDS = {
    "x": (170, 250),
    "y": (-120, 120),
    "z": (30, 120),
    "r": (-60, 60),
}

# Speed profiles (velocity mm/s, acceleration mm/s²)
SAFE_VELOCITY     = 100   # mm/s  (~33 % of max)
SAFE_ACCELERATION = 80    # mm/s²
SPEED_DEFAULT    = (SAFE_VELOCITY, SAFE_ACCELERATION)
SPEED_SMOOTH     = (50, 40)   # gentler for demos

JUMP_HEIGHT = 30  # mm — default Z clearance for JUMP_XYZ mode

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
    def desc_hwid(port) -> str:
        return f"{(port.description or '')} {port.hwid}".lower()

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
              bounds: dict | None = None, verify: bool = False,
              verify_tol_mm: float = 5, verify_tol_deg: float = 5) -> None:
    """Move *bot* to (x, y, z, r) after clamping each axis to bounds.

    Uses SAFE_BOUNDS by default. Pass bounds=CONSERVATIVE_BOUNDS to stay
    well inside the reachable workspace and avoid POSE_LIMIT_OVER.

    Prints a warning when any coordinate is clamped. Optional *verify* checks
    the achieved pose after the move and warns if it differs from target.

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
    if verify:
        ax, ay, az, ar, *_ = unpack_pose(bot.get_pose())
        dx = abs(ax - cx)
        dy = abs(ay - cy)
        dz = abs(az - cz)
        dr = abs(ar - cr)
        if dx > verify_tol_mm or dy > verify_tol_mm or dz > verify_tol_mm or dr > verify_tol_deg:
            print(f"[safe_move] LIMIT: target ({cx:.1f},{cy:.1f},{cz:.1f},{cr:.1f}) "
                  f"-> achieved ({ax:.1f},{ay:.1f},{az:.1f},{ar:.1f}) "
                  f"(drift: dx={dx:.1f} dy={dy:.1f} dz={dz:.1f} dr={dr:.1f})")


def go_home(bot) -> None:
    """Send *bot* to joint-space home (0, 0, 0, 0)."""
    from pydobotplus.dobotplus import MODE_PTP
    bot.move_to(*HOME_JOINTS, wait=True, mode=MODE_PTP.MOVJ_ANGLE)
    print("[utils] At home: joint zero (0, 0, 0, 0)")


def safe_rel_move(bot, dx: float = 0, dy: float = 0, dz: float = 0, dr: float = 0) -> None:
    """Move relative to the current pose, clamped to SAFE_BOUNDS.

    Reads the current pose, adds the deltas, then delegates to safe_move().
    All clamping and warning logic from safe_move() applies.
    """
    x, y, z, r, *_ = unpack_pose(bot.get_pose())
    safe_move(bot, x + dx, y + dy, z + dz, r + dr)


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
        alarm_names = [str(getattr(a, "name", a)) for a in alarms]
        print(f"[prepare_robot] Clearing {len(alarms)} alarm(s):")
        for name in alarm_names:
            print(f"  {name}")
        bot.clear_alarms()
        if any("LIMIT" in name.upper() for name in alarm_names):
            do_homing(bot)


def startup_check(bot) -> None:
    """Alias for prepare_robot. Clear alarms and run homing if LIMIT alarms present."""
    prepare_robot(bot)


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
