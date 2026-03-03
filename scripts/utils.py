"""
utils.py — Shared helpers for Dobot Magician lab scripts (ME403).

Import in any script:
    from utils import (
        clamp, safe_move, go_home, unpack_pose,
        READY_POSE, SAFE_BOUNDS, find_port
    )
"""

from serial.tools import list_ports

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

READY_POSE = (200, 0, 100, 0)  # X, Y, Z (mm), R (deg) — safe home position

SAFE_BOUNDS = {
    "x": (150, 280),
    "y": (-160, 160),
    "z": (10, 150),
    "r": (-90, 90),
}

# Safe speed defaults (velocity mm/s, acceleration mm/s²)
SAFE_VELOCITY     = 100   # mm/s  (~33 % of max)
SAFE_ACCELERATION = 80    # mm/s²

# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------

def find_port(keyword: str = "Silicon Labs") -> str | None:
    """Return the first serial port whose description matches *keyword*.

    Falls back to returning the first available port if no keyword match.
    Returns None if no ports are found at all.
    """
    ports = list(list_ports.comports())
    for p in ports:
        if keyword.lower() in (p.description or "").lower():
            return p.device
    # Fallback: return first port
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


def safe_move(bot, x: float, y: float, z: float, r: float) -> None:
    """Move *bot* to (x, y, z, r) after clamping each axis to SAFE_BOUNDS.

    Uses the pydobotplus API (move_to with wait=True).
    For dobot-python, use either:
      - lib.dobot.Dobot.move_to(..., wait=True), or
      - lib.interface.Interface.set_point_to_point_command(..., queue=True)
    For pydobot, bot.move_to(..., wait=True) is equivalent.
    """
    x = clamp(x, *SAFE_BOUNDS["x"])
    y = clamp(y, *SAFE_BOUNDS["y"])
    z = clamp(z, *SAFE_BOUNDS["z"])
    r = clamp(r, *SAFE_BOUNDS["r"])
    bot.move_to(x, y, z, r, wait=True)


def go_home(bot) -> None:
    """Send *bot* to the predefined READY_POSE."""
    safe_move(bot, *READY_POSE)
    print(f"[utils] At home: {READY_POSE}")
