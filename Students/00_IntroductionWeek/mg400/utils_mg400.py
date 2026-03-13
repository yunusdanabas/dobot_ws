"""
utils_mg400.py — Shared helpers for MG400 student intro scripts (ME403).
Prepared by Yunus Emre Danabas for ME403.

Import in any script:
    from utils_mg400 import (
        connect, close_all,
        clamp, safe_move, go_home,
        parse_pose, parse_angles,
        check_errors,
        ROBOT_IPS, MG400_IP, READY_POSE, SAFE_BOUNDS,
    )

SDK auto-discovery: finds dobot_api.py from either:
  1. Students/00_IntroductionWeek/mg400/dobot_api.py  (user-placed copy)
  2. vendor/TCP-IP-4Axis-Python/dobot_api.py          (SDK git clone at dobot_ws root)

One-time SDK setup:
    cd dobot_ws
    git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git vendor/TCP-IP-4Axis-Python

Network setup (one-time): set PC Ethernet adapter to static IP 192.168.2.100/24.
Verify connectivity:  ping 192.168.2.9

Robot IP map (192.168.2.x subnet):
  Robot 1 → 192.168.2.9
  Robot 2 → 192.168.2.10
  Robot 3 → 192.168.2.7
  Robot 4 → 192.168.2.8

MG400 coordinate notes:
  - X: 60–400 mm  (safe inner limit ≈60 mm due to base singularity; max reach 440 mm)
  - Y: ±220 mm    (symmetric around centre)
  - Z: 5–140 mm   (Z CANNOT go negative — 0 mm = mounting surface)
  - R: ±170°      (end-effector rotation)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# SDK auto-discovery
# ---------------------------------------------------------------------------

_HERE        = Path(__file__).parent
_VENDOR_PATH = _HERE.parent.parent.parent / "vendor" / "TCP-IP-4Axis-Python"


def _find_dobot_api() -> str:
    """Return the directory containing dobot_api.py, or raise ImportError."""
    if (_HERE / "dobot_api.py").exists():
        return str(_HERE)
    if (_VENDOR_PATH / "dobot_api.py").exists():
        return str(_VENDOR_PATH)
    raise ImportError(
        "dobot_api.py not found.\n"
        "Clone the official SDK with:\n"
        "  cd dobot_ws\n"
        "  git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git "
        "vendor/TCP-IP-4Axis-Python\n"
        "Or place dobot_api.py directly in Students/00_IntroductionWeek/mg400/."
    )


_api_dir = _find_dobot_api()
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from dobot_api import DobotApiDashboard, DobotApiMove  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROBOT_IPS = {
    1: "192.168.2.9",
    2: "192.168.2.10",
    3: "192.168.2.7",
    4: "192.168.2.8",
}
MG400_IP       = ROBOT_IPS[1]   # default: Robot 1
DASHBOARD_PORT = 29999
MOVE_PORT      = 30003

# Operating safe bounds (inside the 440 mm hardware envelope).
# Z is non-negative: 0 mm = mounting surface.
SAFE_BOUNDS = {
    "x": (60,   400),   # inner: base singularity ≥60 mm; outer: ≤440 mm reach
    "y": (-220, 220),   # full lateral sweep
    "z": (5,    140),   # 5 mm above surface
    "r": (-170, 170),   # full wrist rotation
}

READY_POSE    = (300, 0, 50, 0)   # (x mm, y mm, z mm, r deg) — safe home position
SPEED_DEFAULT = 30                 # % (1–100) — conservative for teaching

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def connect(ip: str = MG400_IP):
    """Connect to MG400. Returns (dashboard, move_api).

    Call dashboard.EnableRobot() before any motion commands.
    Call dashboard.DisableRobot() + close_all() in the finally block.
    """
    dashboard = DobotApiDashboard(ip, DASHBOARD_PORT)
    move_api  = DobotApiMove(ip, MOVE_PORT)
    return dashboard, move_api


def close_all(dashboard, move_api) -> None:
    """Close both API connections safely."""
    for obj in (dashboard, move_api):
        try:
            obj.close()
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def parse_pose(response: str) -> tuple[float, float, float, float]:
    """Parse GetPose() response string → (x, y, z, r).

    Expected format: "0,{x},{y},{z},{rx},{ry},{rz},{r}" or "0,{x},{y},{z},{r}"
    The leading '0' is the error code; rx/ry are always 0 for the 4-axis MG400.
    """
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", response)
    floats = [float(n) for n in nums]
    if len(floats) >= 5:
        return floats[1], floats[2], floats[3], floats[4]
    if len(floats) == 4:
        return floats[0], floats[1], floats[2], floats[3]
    raise ValueError(f"Cannot parse pose from: {response!r}")


def parse_angles(response: str) -> tuple[float, float, float, float]:
    """Parse GetAngle() response string → (j1, j2, j3, j4).

    Expected format: "0,{j1},{j2},{j3},{j4}" (degrees).
    """
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", response)
    floats = [float(n) for n in nums]
    if len(floats) >= 5:
        return floats[1], floats[2], floats[3], floats[4]
    if len(floats) == 4:
        return floats[0], floats[1], floats[2], floats[3]
    raise ValueError(f"Cannot parse angles from: {response!r}")

# ---------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------


def clamp(v: float, lo: float, hi: float) -> float:
    """Clamp v to [lo, hi]."""
    return max(lo, min(hi, v))


def safe_move(
    move_api,
    x: float, y: float, z: float, r: float,
    mode: str = "J",
    bounds: dict | None = None,
) -> None:
    """Clamp (x,y,z,r) to SAFE_BOUNDS and send MovJ or MovL.

    Does NOT call Sync() — the caller decides when to synchronise.
    Prints a warning whenever any axis is clamped.

    Args:
        move_api: DobotApiMove instance
        x,y,z,r:  target pose (mm and degrees)
        mode:      "J" → MovJ (joint interpolation, default)
                   "L" → MovL (straight-line Cartesian path)
    """
    b  = bounds or SAFE_BOUNDS
    cx = clamp(x, *b["x"])
    cy = clamp(y, *b["y"])
    cz = clamp(z, *b["z"])
    cr = clamp(r, *b["r"])
    if (cx, cy, cz, cr) != (x, y, z, r):
        print(
            f"[safe_move] Clamped: ({x:.1f},{y:.1f},{z:.1f},{r:.1f})"
            f" -> ({cx:.1f},{cy:.1f},{cz:.1f},{cr:.1f})"
        )
    if mode.upper() == "L":
        move_api.MovL(cx, cy, cz, cr)
    else:
        move_api.MovJ(cx, cy, cz, cr)


def go_home(move_api) -> None:
    """Move to READY_POSE (joint interpolation) and Sync."""
    move_api.MovJ(*READY_POSE)
    move_api.Sync()
    print(f"[utils] At home: {READY_POSE}")

# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def check_errors(dashboard) -> None:
    """Query GetErrorID(), print any active errors, then ClearError + Continue.

    Safe to call at startup; silently returns if no errors exist.
    Raises RuntimeError if errors cannot be cleared (robot needs physical
    intervention — check E-stop, collision guards, then power-cycle).
    """
    try:
        resp = dashboard.GetErrorID()
        nums = re.findall(r"\d+", resp)
        error_ids = [int(n) for n in nums if int(n) != 0]
        if error_ids:
            print(f"[check_errors] Active error IDs: {error_ids}")
            dashboard.ClearError()
            cont_resp = dashboard.Continue()
            if not cont_resp or cont_resp.strip().startswith("-1"):
                raise RuntimeError(
                    f"[check_errors] Cannot clear robot errors {error_ids}.\n"
                    "  Robot is still in ERROR mode — do not proceed.\n"
                    "  Required action: check E-stop and joint limits,\n"
                    "  then power-cycle the robot (hold power button ~3 s)."
                )
            print("[check_errors] Errors cleared, robot resumed.")
        else:
            print("[check_errors] No errors.")
    except RuntimeError:
        raise
    except Exception as exc:
        print(f"[check_errors] Could not read errors: {exc}")
