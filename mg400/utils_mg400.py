"""
utils_mg400.py — Shared helpers for MG400 lab scripts (ME403).

Import in any script:
    from utils_mg400 import (
        connect, clamp, safe_move, safe_rel_move, go_home,
        parse_pose, parse_angles, check_errors, start_feedback_thread,
        MG400_IP, READY_POSE, SAFE_BOUNDS, JUMP_HEIGHT, SPEED_DEFAULT,
        ROBOT_MODE, current_pose,
    )

SDK auto-discovery: utils_mg400 finds dobot_api.py from either:
  1. mg400/dobot_api.py    (user-placed copy — takes precedence)
  2. vendor/TCP-IP-4Axis-Python/dobot_api.py  (SDK git clone)

One-time SDK setup:
    git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git \\
        /path/to/dobot_ws/vendor/TCP-IP-4Axis-Python

Network setup (one-time): set PC Ethernet to static 192.168.2.100/24.
Verify:  ping 192.168.2.7

Robot IP map (192.168.2.x subnet):
  Robot 1 → 192.168.2.7
  Robot 2 → 192.168.2.10
  Robot 3 → 192.168.2.9
  Robot 4 → 192.168.2.6

MG400 coordinate notes (verified from Dobot hardware spec v1.1):
  - X: 0–440 mm  (safe inner limit ≈60 mm due to base singularity)
  - Y: ±220 mm   (symmetric around centre)
  - Z: 0–150 mm  (Z CANNOT go negative — 0 mm = mounting surface)
  - R: ±170°     (end-effector rotation; 10° safety margin inside J4 hardware limit of ±180°)

Joint ranges (per DT-MG400-4R075-01 hardware guide V1.1, Table 2.1):
  - J1: ±160°    (base rotation)
  - J2: -25° ~ +85°   (shoulder elevation from horizontal)
  - J3: -25° ~ +105°  (firmware absolute = j2 + j3_rel; factory home = 60°)
  - J4: ±180°    (wrist rotation)
"""

from __future__ import annotations

import re
import sys
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# SDK auto-discovery
# ---------------------------------------------------------------------------

_HERE        = Path(__file__).parent
_VENDOR_PATH = _HERE.parent / "vendor" / "TCP-IP-4Axis-Python"


def _find_dobot_api() -> str:
    """Return the directory containing dobot_api.py, or raise ImportError."""
    if (_HERE / "dobot_api.py").exists():
        return str(_HERE)
    if (_VENDOR_PATH / "dobot_api.py").exists():
        return str(_VENDOR_PATH)
    raise ImportError(
        "dobot_api.py not found.\n"
        "Clone the official SDK with:\n"
        "  git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git "
        f"{_VENDOR_PATH}\n"
        "Or place dobot_api.py directly in mg400/."
    )


_api_dir = _find_dobot_api()
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from dobot_api import DobotApiDashboard, DobotApiMove, DobotApi, MyType  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROBOT_IPS = {
    1: "192.168.2.7",
    2: "192.168.2.10",
    3: "192.168.2.9",
    4: "192.168.2.6",
}
MG400_IP       = ROBOT_IPS[1]   # default: Robot 1
DASHBOARD_PORT = 29999
MOVE_PORT      = 30003
FEED_PORT      = 30004

# Operating safe bounds (inside the 440 mm hardware envelope).
# Z is non-negative: 0 mm = mounting surface, max 150 mm above.
SAFE_BOUNDS = {
    "x": (60,   400),   # inner: base singularity ≥60 mm; outer: ≤440 mm reach
    "y": (-220, 220),   # full lateral sweep
    "z": (5,    140),   # 5 mm above surface; 10 mm below firmware ceiling
    "r": (-170, 170),   # 10° safety margin inside J4 hardware limit of ±180°
}

# Narrower bounds for in-class demos — stays comfortably inside workspace
CONSERVATIVE_BOUNDS = {
    "x": (150,  350),
    "y": (-150, 150),
    "z": (20,   100),
    "r": (-90,   90),
}

READY_POSE    = (300, 0, 50, 0)   # (x mm, y mm, z mm, r deg) — safe home
JUMP_HEIGHT   = 50                 # mm Z lift above pick/place Z for arch moves
SPEED_DEFAULT = 30                 # % (1–100) — conservative for teaching

# Robot mode values returned by dashboard.RobotMode()
ROBOT_MODE = {
    1:  "INIT",
    2:  "BRAKE_OPEN",
    3:  "POWER_STATUS",
    4:  "DISABLED",
    5:  "ENABLE",        # idle, ready for commands
    6:  "BACKDRIVE",     # drag-teach mode
    7:  "RUNNING",       # executing motion
    8:  "RECORDING",
    9:  "ERROR",         # any uncleared alarm → returns 9 regardless of other state
    10: "PAUSE",
    11: "JOG",
}

# ---------------------------------------------------------------------------
# Shared feedback state (updated by start_feedback_thread)
# ---------------------------------------------------------------------------

current_pose: dict = {"x": 0.0, "y": 0.0, "z": 0.0, "r": 0.0, "valid": False}
_feedback_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


def connect(ip: str = MG400_IP):
    """Connect to MG400. Returns (dashboard, move_api, feed).

    Call EnableRobot() on dashboard before any motion commands.
    Call DisableRobot() + close all three objects in the finally block.

    The feed object is a raw DobotApi socket to port 30004.
    Read 1440-byte packets and parse with numpy MyType dtype (see
    start_feedback_thread and 12_feedback_monitor.py for usage).
    """
    dashboard = DobotApiDashboard(ip, DASHBOARD_PORT)
    move_api  = DobotApiMove(ip, MOVE_PORT)
    feed      = DobotApi(ip, FEED_PORT)
    return dashboard, move_api, feed


def close_all(dashboard, move_api, feed) -> None:
    """Close all three API connections safely."""
    for obj in (dashboard, move_api, feed):
        try:
            obj.close()
        except Exception:
            pass


def connect_multi(robot_ids=None):
    """Connect to multiple MG400 robots simultaneously.

    Args:
        robot_ids: list of ints 1-4. None = all 4 robots.

    Returns:
        dict mapping robot_id → (dashboard, move_api, feed)
    """
    if robot_ids is None:
        robot_ids = list(ROBOT_IPS.keys())
    return {rid: connect(ROBOT_IPS[rid]) for rid in robot_ids}


def close_all_robots(robots: dict) -> None:
    """Close all connections returned by connect_multi()."""
    for _rid, (dashboard, move_api, feed) in robots.items():
        close_all(dashboard, move_api, feed)

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
        # SDK responses include return code first: 0 means success.
        status = int(floats[0])
        if status != 0:
            raise ValueError(f"GetPose returned status {status}: {response!r}")
        # Skip return code; take x,y,z,r (indices 1,2,3,4)
        return floats[1], floats[2], floats[3], floats[4]
    if len(floats) == 4:
        # Legacy/fallback format without a leading status code.
        return floats[0], floats[1], floats[2], floats[3]
    raise ValueError(f"Cannot parse pose from: {response!r}")


def parse_angles(response: str) -> tuple[float, float, float, float]:
    """Parse GetAngle() response string → (j1, j2, j3, j4).

    Expected format: "0,{j1},{j2},{j3},{j4}" (degrees).
    """
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", response)
    floats = [float(n) for n in nums]
    if len(floats) >= 5:
        status = int(floats[0])
        if status != 0:
            raise ValueError(f"GetAngle returned status {status}: {response!r}")
        return floats[1], floats[2], floats[3], floats[4]
    if len(floats) == 4:
        # Legacy/fallback format without a leading status code.
        return floats[0], floats[1], floats[2], floats[3]
    raise ValueError(f"Cannot parse angles from: {response!r}")


def parse_robot_mode(response: str) -> int:
    """Parse RobotMode() response → integer mode code."""
    nums = [int(n) for n in re.findall(r"[-+]?\d+", response)]
    if not nums:
        raise ValueError(f"Cannot parse robot mode from: {response!r}")

    if len(nums) >= 2 and nums[0] in (0, -1):
        status = nums[0]
        if status != 0:
            raise ValueError(f"RobotMode returned status {status}: {response!r}")
        mode = nums[1]
    elif len(nums) == 1:
        # Fallback for response styles that return mode directly.
        mode = nums[0]
    else:
        mode = nums[-1]

    if mode not in ROBOT_MODE:
        raise ValueError(f"RobotMode payload missing/invalid in: {response!r}")
    return mode


def parse_error_ids(response: str) -> list[int]:
    """Parse GetErrorID() response → list[int] of non-zero error IDs.

    Valid empty-alarm payloads still include a bracketed matrix, e.g.
    "0,{[[],[],...]} ,GetErrorID();". Echo-only payloads like "GetErrorID()"
    or "0,{},GetErrorID();" are treated as malformed.
    """
    text = (response or "").strip()
    if not text:
        raise ValueError("Empty GetErrorID response")
    if "[" not in text or "]" not in text:
        raise ValueError(f"Malformed GetErrorID payload (missing matrix): {response!r}")

    nums = [int(n) for n in re.findall(r"[-+]?\d+", text)]
    if not nums:
        raise ValueError(f"Cannot parse GetErrorID response: {response!r}")

    status = nums[0]
    if status != 0:
        raise ValueError(f"GetErrorID returned status {status}: {response!r}")

    return [n for n in nums[1:] if n != 0]

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
    """Clamp (x,y,z,r) to bounds and send MovJ or MovL.

    Does NOT call Sync() — the caller decides when to synchronise.
    Prints a warning whenever any axis is clamped.

    Args:
        move_api: DobotApiMove instance
        x,y,z,r:  target pose (mm and degrees)
        mode:      "J" → MovJ (joint interpolation, default)
                   "L" → MovL (straight-line Cartesian path)
        bounds:    dict with keys "x","y","z","r" each a (lo,hi) tuple.
                   Defaults to SAFE_BOUNDS.
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


def safe_rel_move(
    move_api,
    dashboard,
    dx: float = 0, dy: float = 0, dz: float = 0, dr: float = 0,
    mode: str = "J",
) -> None:
    """Move relative to current pose, clamped to SAFE_BOUNDS.

    Reads the current pose via dashboard.GetPose(), adds the deltas,
    then delegates to safe_move(). All clamping warnings apply.
    """
    resp = dashboard.GetPose()
    x, y, z, r = parse_pose(resp)
    safe_move(move_api, x + dx, y + dy, z + dz, r + dr, mode=mode)


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
    intervention — check E-stop, collision guards, joint limits, then power-cycle).
    """
    try:
        resp = dashboard.GetErrorID()
        error_ids = parse_error_ids(resp)
        if error_ids:
            print(f"[check_errors] Active error IDs: {error_ids}")
            dashboard.ClearError()
            cont_resp = dashboard.Continue()
            # A -1 return code means the command was rejected (robot still in ERROR)
            if not cont_resp or cont_resp.strip().startswith("-1"):
                raise RuntimeError(
                    f"[check_errors] Cannot clear robot errors {error_ids}.\n"
                    "  Robot is still in ERROR mode — do not proceed.\n"
                    "  Required action: check E-stop, collision guards, and joint limits,\n"
                    "  then power-cycle the robot (hold power button ~3 s)."
                )
            print("[check_errors] Errors cleared, robot resumed.")
        else:
            print("[check_errors] No errors.")
    except RuntimeError:
        raise
    except Exception as exc:
        print(f"[check_errors] Could not read errors: {exc}")

# ---------------------------------------------------------------------------
# Feedback thread
# ---------------------------------------------------------------------------


def start_feedback_thread(feed) -> threading.Thread:
    """Spawn a daemon thread that reads port 30004 binary packets at 8 ms.

    Parses each 1440-byte packet using the SDK's MyType numpy dtype and
    updates the shared current_pose dict with tool_vector_actual (x,y,z,r).

    Updates the shared current_pose dict continuously.
    Thread is a daemon so it exits when the main program exits.

    Args:
        feed: DobotApi instance connected to port 30004 (from connect()).

    Returns:
        The running Thread object (daemon; no need to join).
    """
    import numpy as np

    PACKET_SIZE = 1440
    TEST_VALUE  = 0x123456789ABCDEF

    def _read() -> None:
        while True:
            try:
                data    = bytes()
                has_read = 0
                while has_read < PACKET_SIZE:
                    chunk = feed.socket_dobot.recv(PACKET_SIZE - has_read)
                    if chunk:
                        has_read += len(chunk)
                        data     += chunk
                info = np.frombuffer(data, dtype=MyType)
                if int(info["test_value"][0]) == TEST_VALUE:
                    tv = info["tool_vector_actual"][0]   # [x, y, z, r, ...]
                    with _feedback_lock:
                        current_pose["x"]     = float(tv[0])
                        current_pose["y"]     = float(tv[1])
                        current_pose["z"]     = float(tv[2])
                        current_pose["r"]     = float(tv[3])
                        current_pose["valid"] = True
            except Exception:
                pass
            time.sleep(0.001)

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    return t


def wait_arrive(
    target: tuple[float, float, float],
    tol_mm: float = 2.0,
    timeout: float = 20.0,
) -> bool:
    """Block until current_pose is within tol_mm of target (x,y,z).

    Requires start_feedback_thread() to be running.

    Returns:
        True if arrived within timeout, False on timeout.
    """
    tx, ty, tz = target[0], target[1], target[2]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with _feedback_lock:
            valid = current_pose["valid"]
            px, py, pz = current_pose["x"], current_pose["y"], current_pose["z"]
        if valid:
            dist = ((px - tx) ** 2 + (py - ty) ** 2 + (pz - tz) ** 2) ** 0.5
            if dist < tol_mm:
                return True
        time.sleep(0.05)
    print(f"[wait_arrive] Timeout: could not reach {target} within {timeout:.0f}s")
    return False
