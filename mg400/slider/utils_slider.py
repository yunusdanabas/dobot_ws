"""
utils_slider.py — Slider helpers for MG400 + DT-AC-HDSR-001 sliding rail (ME403).

The MG400 Sliding Rail Kit (model DT-AC-HDSR-001) extends Robot 3
(IP 192.168.2.10) with 800 mm of linear travel.

Key API facts:
  - move_api.MovJExt(pos_mm, "SpeedE=50", "AccE=50")  — the ONLY slider command
  - No GetPoseExt — slider position is tracked in software (last commanded value)
  - move_api.SyncAll() — waits for BOTH arm queue AND slider queue to finish
  - move_api.Sync()    — arm queue only (use when moving arm OR slider alone)
  - No MoveJog for E-axis — use incremental MovJExt for jogging

One-time setup in DobotStudio Pro (required before any slider script):
  Configure → External Axis → Type: Linear → Unit: mm → Enable → Reboot

Import in any script:
    from utils_slider import (
        connect, close_all, check_errors, go_home, parse_pose,
        safe_move, safe_rel_move,
        SLIDER_IP, SLIDER_BOUNDS, SLIDER_HOME, SPEED_EXT,
        SLIDER_STEP_FAST, SLIDER_STEP_SLOW,
        safe_move_ext, go_home_slider, jog_slider,
        get_slider_pos, print_slider_status,
    )
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — insert mg400/ so utils_mg400 is importable from mg400/slider/
# ---------------------------------------------------------------------------

_HERE        = Path(__file__).parent          # mg400/slider/
_MG400_DIR   = _HERE.parent                   # mg400/
_VENDOR_PATH = _HERE.parent.parent / "vendor" / "TCP-IP-4Axis-Python"

if str(_MG400_DIR) not in sys.path:
    sys.path.insert(0, str(_MG400_DIR))

# Re-export everything from the parent utils so slider scripts only need one import.
from utils_mg400 import (           # noqa: E402
    connect, close_all, connect_multi, close_all_robots,
    clamp, safe_move, safe_rel_move, go_home,
    parse_pose, parse_angles, parse_robot_mode,
    check_errors, start_feedback_thread, wait_arrive,
    ROBOT_IPS, READY_POSE, SAFE_BOUNDS, SPEED_DEFAULT, ROBOT_MODE,
    current_pose,
)

# ---------------------------------------------------------------------------
# Slider constants
# ---------------------------------------------------------------------------

SLIDER_ROBOT_ID  = 2
SLIDER_IP        = ROBOT_IPS[2]   # "192.168.2.10"

SLIDER_BOUNDS    = (0.0, 800.0)   # mm — hardware limit of DT-AC-HDSR-001
SLIDER_HOME      = 0.0            # fully retracted

SPEED_EXT        = 50             # % default for SpeedE / AccE
SLIDER_STEP_FAST = 20.0           # mm per keypress (coarse jog)
SLIDER_STEP_SLOW = 5.0            # mm per keypress (fine jog, Shift)

# ---------------------------------------------------------------------------
# Software position tracker (no API read-back available)
# ---------------------------------------------------------------------------

_slider_pos: float | None = None  # None until first command after homing


def get_slider_pos() -> float | None:
    """Return the last commanded slider position, or None if not yet homed."""
    return _slider_pos

# ---------------------------------------------------------------------------
# Slider helpers
# ---------------------------------------------------------------------------


def safe_move_ext(
    move_api,
    pos_mm: float,
    speed: int = SPEED_EXT,
    acc: int = SPEED_EXT,
    sync: bool = False,
) -> float:
    """Clamp pos_mm to SLIDER_BOUNDS and send MovJExt.

    Updates the internal position tracker.
    Calls move_api.Sync() only if sync=True; otherwise the caller decides.
    Prints a clamping warning (matching safe_move() style) when clipped.

    Args:
        move_api: DobotApiMove instance
        pos_mm:   target rail position in mm
        speed:    SpeedE percentage (1–100)
        acc:      AccE percentage (1–100)
        sync:     if True, block until the slider finishes (Sync, arm only)

    Returns:
        The clamped position that was commanded (mm).
    """
    global _slider_pos
    lo, hi = SLIDER_BOUNDS
    cpos = clamp(pos_mm, lo, hi)
    if cpos != pos_mm:
        print(
            f"[safe_move_ext] Clamped: {pos_mm:.1f} mm"
            f" -> {cpos:.1f} mm (bounds {lo:.0f}–{hi:.0f} mm)"
        )
    move_api.MovJExt(cpos, f"SpeedE={speed}", f"AccE={acc}")
    _slider_pos = cpos
    if sync:
        move_api.Sync()
    return cpos


def go_home_slider(move_api) -> None:
    """Move slider to SLIDER_HOME (0 mm) and Sync.

    Must be called before jog_slider() so the position tracker is valid.
    """
    global _slider_pos
    move_api.MovJExt(SLIDER_HOME, f"SpeedE={SPEED_EXT}", f"AccE={SPEED_EXT}")
    move_api.Sync()
    _slider_pos = SLIDER_HOME
    print(f"[slider] Homed to {SLIDER_HOME:.0f} mm")


def jog_slider(move_api, delta_mm: float) -> float:
    """Move slider by delta_mm relative to the current tracked position.

    Raises RuntimeError if go_home_slider() has not been called first
    (position would be undefined).

    Args:
        move_api:  DobotApiMove instance
        delta_mm:  signed step size in mm (positive = extend, negative = retract)

    Returns:
        The resulting clamped position (mm).
    """
    if _slider_pos is None:
        raise RuntimeError(
            "[jog_slider] Slider position unknown — call go_home_slider() first."
        )
    target = _slider_pos + delta_mm
    return safe_move_ext(move_api, target, sync=True)


def print_slider_status(prefix: str = "") -> None:
    """Print the current tracked slider position (or UNKNOWN if not homed)."""
    if _slider_pos is None:
        label = "UNKNOWN (not homed)"
    else:
        label = f"{_slider_pos:.1f} mm"
    tag = f"[{prefix}] " if prefix else ""
    print(f"{tag}Slider: {label}")
