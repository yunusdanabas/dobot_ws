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
  1. Students/01_SecondWeek/mg400/dobot_api.py  (user-placed copy)
  2. vendor/TCP-IP-4Axis-Python/dobot_api.py    (SDK git clone at dobot_ws root)

One-time SDK setup:
    cd dobot_ws
    git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git vendor/TCP-IP-4Axis-Python

Network setup (one-time): set PC Ethernet adapter to static IP 192.168.2.100/24.
Verify connectivity:  ping 192.168.2.7

Robot IP map (192.168.2.x subnet):
  Robot 1 → 192.168.2.7
  Robot 2 → 192.168.2.10
  Robot 3 → 192.168.2.9
  Robot 4 → 192.168.2.6

MG400 coordinate notes:
  - X: 60–400 mm  (safe inner limit ≈60 mm due to base singularity; max reach 440 mm)
  - Y: ±220 mm    (symmetric around centre)
  - Z: 5–140 mm   (Z CANNOT go negative — 0 mm = mounting surface)
  - R: ±170°      (end-effector rotation)
"""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
import os
import re
import socket
import sys
from contextlib import closing
from pathlib import Path

# ---------------------------------------------------------------------------
# SDK auto-discovery
# ---------------------------------------------------------------------------

_HERE          = Path(__file__).parent
# standalone share: vendor/ sits next to mg400/ inside 01_SecondWeek/
_VENDOR_LOCAL  = _HERE.parent / "vendor" / "TCP-IP-4Axis-Python"
# full repo: vendor/ sits at dobot_ws root
_VENDOR_REPO   = _HERE.parent.parent.parent / "vendor" / "TCP-IP-4Axis-Python"


def _find_dobot_api() -> str:
    """Return the directory containing dobot_api.py, or raise ImportError."""
    if (_HERE / "dobot_api.py").exists():
        return str(_HERE)
    if (_VENDOR_LOCAL / "dobot_api.py").exists():
        return str(_VENDOR_LOCAL)
    if (_VENDOR_REPO / "dobot_api.py").exists():
        return str(_VENDOR_REPO)
    raise ImportError(
        "dobot_api.py not found.\n"
        "Clone the official SDK next to this folder:\n"
        "  cd 01_SecondWeek\n"
        "  git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git "
        "vendor/TCP-IP-4Axis-Python\n"
        "Or place dobot_api.py directly in mg400/."
    )


_api_dir = _find_dobot_api()
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from dobot_api import DobotApiDashboard, DobotApiMove  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROBOT_IPS = {
    1: "192.168.2.7",
    2: "192.168.2.10",
    3: "192.168.2.9",
    4: "192.168.2.6",
}
ROBOT_IDS      = tuple(ROBOT_IPS)
MG400_IP_ENV   = "DOBOT_MG400_IP"
MG400_IP       = os.environ.get(MG400_IP_ENV, ROBOT_IPS[1])   # default: Robot 1, env-overridable
PC_STATIC_IP   = "192.168.2.100"
PC_PREFIX_LEN  = 24
DASHBOARD_PORT = 29999
MOVE_PORT      = 30003
REQUIRED_PORTS = (DASHBOARD_PORT, MOVE_PORT)

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


def resolve_target_ip(ip: str | None = None, robot: int | None = None) -> str:
    """Return the selected MG400 target IP from robot, explicit IP, or env."""
    if robot is not None:
        return ROBOT_IPS[robot]
    return ip or os.environ.get(MG400_IP_ENV, ROBOT_IPS[1])


def add_target_arguments(
    parser: ArgumentParser,
    *,
    default_ip: str = MG400_IP,
    default_robot: int | None = None,
    ip_help: str = "MG400 IP address",
    robot_help: str = "Robot number 1-4 (overrides --ip)",
) -> None:
    """Attach the standard MG400 `--ip/--robot` arguments to a parser."""
    parser.add_argument("--ip", default=default_ip, help=ip_help)
    parser.add_argument(
        "--robot",
        type=int,
        default=default_robot,
        choices=ROBOT_IDS,
        metavar="N",
        help=robot_help,
    )


def format_direct_connect_help(ip: str, platform_name: str | None = None) -> str:
    """Return a concise setup hint for direct MG400 Ethernet connections."""
    platform_name = platform_name or sys.platform
    lines = [
        "Direct connection checklist:",
        "  1. Power the robot and connect Ethernet directly to the PC",
        f"  2. Set the PC adapter IPv4 to {PC_STATIC_IP}/{PC_PREFIX_LEN} (255.255.255.0)",
        f"  3. Verify with: ping {ip}",
        f"  4. Use --ip {ip} or set {MG400_IP_ENV}",
    ]
    return "\n".join(lines + _platform_direct_connect_lines(platform_name))


def _platform_direct_connect_lines(platform_name: str) -> list[str]:
    """Return OS-specific direct-connect guidance with lazy Windows imports."""
    if platform_name == "win32":
        return _load_windows_direct_connect_lines()
    return [
        "Linux/macOS:",
        "  Use Network Manager or nmcli to set the adapter to 192.168.2.100/24.",
    ]


def _load_windows_direct_connect_lines() -> list[str]:
    """Load Windows-only MG400 guidance lazily."""
    try:
        from windows.mg400_support import get_direct_connect_help_lines
    except Exception:
        return [
            "Windows PowerShell (from repo root):",
            "  .\\windows\\Set-MG400StaticIp.ps1   # dry run only",
            "  Get-NetAdapter",
            "  Run PowerShell as Administrator for the -Apply step",
            "  .\\windows\\Set-MG400StaticIp.ps1 -InterfaceAlias '<EthernetName>' -Apply",
            "  The PowerShell helper does not change the adapter unless you add -Apply.",
        ]
    return get_direct_connect_help_lines()


def _probe_required_ports(ip: str, ports: tuple[int, ...] = REQUIRED_PORTS, timeout: float = 1.5) -> None:
    """Fail fast with a normal socket error before the vendor SDK prints noise."""
    for port in ports:
        try:
            with closing(socket.create_connection((ip, port), timeout=timeout)):
                pass
        except OSError as exc:
            raise OSError(f"TCP port {port} is unreachable: {exc}") from exc


def _connection_error(ip: str, message: str) -> ConnectionError:
    """Build a consistent connection error with setup guidance."""
    return ConnectionError(f"{message}\n{format_direct_connect_help(ip)}")


def connect_with_diagnostics(ip: str = MG400_IP):
    """Connect to MG400 or raise ConnectionError with setup guidance."""
    try:
        _probe_required_ports(ip)
    except OSError as exc:
        raise _connection_error(ip, f"Cannot reach MG400 at {ip}: {exc}") from exc

    try:
        return connect(ip)
    except ConnectionRefusedError as exc:
        raise _connection_error(ip, f"Connection refused for MG400 at {ip}.") from exc
    except OSError as exc:
        raise _connection_error(ip, f"Cannot connect to MG400 at {ip}: {exc}") from exc
    except Exception as exc:
        raise _connection_error(ip, f"MG400 connection setup failed at {ip}: {exc}") from exc


def resolve_target_from_args(args: Namespace) -> str:
    """Resolve the MG400 target IP from parsed CLI arguments."""
    return resolve_target_ip(ip=getattr(args, "ip", None), robot=getattr(args, "robot", None))


def connect_from_args_or_exit(args: Namespace):
    """Resolve CLI target args, connect, or exit with a clean script error."""
    ip = resolve_target_from_args(args)
    try:
        dashboard, move_api = connect_with_diagnostics(ip)
    except ConnectionError as exc:
        raise SystemExit(f"[Error] {exc}") from exc
    return ip, dashboard, move_api


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


def query_dashboard_version(dashboard) -> str:
    """Query firmware version across SDK variants."""
    if hasattr(dashboard, "GetVersion"):
        response = dashboard.GetVersion()
    elif hasattr(dashboard, "sendRecvMsg"):
        response = dashboard.sendRecvMsg("GetVersion()")
    else:
        raise AttributeError("dashboard object has neither GetVersion nor sendRecvMsg")

    match = re.match(r"\s*([-+]?\d+),", str(response))
    if match and int(match.group(1)) != 0:
        raise ValueError(f"GetVersion returned status {match.group(1)}")
    return response


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
