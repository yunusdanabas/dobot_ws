"""
utils.py — Unified robot helpers for Lab 1 (ME403).

Supports both Dobot Magician (USB-serial) and MG400 (TCP/IP).
Change ROBOT_TYPE below to select the robot.

Public API:
    robot = setup()
    x, y, z, r = move_and_get_feedback(robot, q)
    teardown(robot)

Magician setup:
    pip install pydobotplus pyserial
    Connect USB, power on, close DobotStudio.

MG400 setup:
    git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git vendor/TCP-IP-4Axis-Python
    Set PC Ethernet to 192.168.2.100/24. Verify: ping 192.168.2.7

Prepared by Yunus Emre Danabas for ME403.
"""

import os
import re
import sys
import time
from pathlib import Path

# ── CHANGE THIS ──────────────────────────────────────────────────────────────
ROBOT_TYPE = "magician"       # "magician" or "mg400"
MG400_IP   = "192.168.2.7"   # only used when ROBOT_TYPE = "mg400"
# ─────────────────────────────────────────────────────────────────────────────

_CONFIGS = {
    "magician": {
        "joint_bounds": {
            "j1": (-90.0,  90.0),
            "j2": (  0.0,  85.0),
            "j3": (-10.0,  85.0),
            "j4": (-90.0,  90.0),
        },
    },
    "mg400": {
        "joint_bounds": {
            "j1": (-160.0, 160.0),
            "j2": ( -25.0,  85.0),
            "j3": ( -25.0, 105.0),
            "j4": (-180.0, 180.0),
        },
    },
}

_HERE = Path(__file__).parent


# ── Robot wrapper ─────────────────────────────────────────────────────────────

class Robot:
    """Thin wrapper that holds either a Magician bot or MG400 handles."""
    def __init__(self, robot_type, **handles):
        self.type = robot_type
        self._h = handles


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _to_firmware_angles(q):
    """Body-frame [q1, q2, q3, q4] -> firmware angles.

    Both robots: j3_fw = q2 + q3 (accumulated from horizontal).
    """
    return float(q[0]), float(q[1]), float(q[1]) + float(q[2]), float(q[3])


def _clamp_firmware_angles(j1, j2, j3, j4, bounds):
    return (
        _clamp(j1, *bounds["j1"]),
        _clamp(j2, *bounds["j2"]),
        _clamp(j3, *bounds["j3"]),
        _clamp(j4, *bounds["j4"]),
    )


# ── Magician internals ───────────────────────────────────────────────────────

def _find_serial_port():
    """Auto-detect the Dobot Magician serial port."""
    from serial.tools import list_ports
    env = os.environ.get("DOBOT_PORT")
    if env:
        return env
    for port in list_ports.comports():
        desc = f"{port.description or ''} {port.hwid}".lower()
        if any(kw in desc for kw in ("silicon labs", "1a86", "usb2.0-serial")):
            return port.device
    ports = list(list_ports.comports())
    return ports[0].device if ports else None


def _setup_magician():
    from pydobotplus import Dobot
    from pydobotplus.dobotplus import MODE_PTP
    port = _find_serial_port()
    if not port:
        raise OSError("No Dobot serial port found. Check USB + power.")
    print(f"[setup] Connecting to Magician on {port} ...")
    bot = Dobot(port=port)
    if bot.get_alarms():
        bot.clear_alarms()
    bot.move_to(0, 0, 0, 0, wait=True, mode=MODE_PTP.MOVJ_ANGLE)
    print("[setup] Ready.")
    return Robot("magician", bot=bot)


def _move_magician(robot, j1, j2, j3, j4):
    from pydobotplus.dobotplus import MODE_PTP
    robot._h["bot"].move_to(j1, j2, j3, j4, wait=True, mode=MODE_PTP.MOVJ_ANGLE)


def _read_pose_magician(robot):
    pose = robot._h["bot"].get_pose()
    if hasattr(pose, "position"):
        p = pose.position
        return float(p.x), float(p.y), float(p.z), float(p.r)
    return tuple(float(v) for v in pose[:4])


def _go_home_magician(robot):
    from pydobotplus.dobotplus import MODE_PTP
    robot._h["bot"].move_to(0, 0, 0, 0, wait=True, mode=MODE_PTP.MOVJ_ANGLE)


def _teardown_magician(robot):
    try:
        _go_home_magician(robot)
    except Exception:
        pass
    try:
        robot._h["bot"].close()
    except Exception:
        pass
    print("[teardown] Done.")


# ── MG400 internals ──────────────────────────────────────────────────────────

def _find_dobot_api():
    """Return the directory containing dobot_api.py, or raise ImportError."""
    if (_HERE / "dobot_api.py").exists():
        return str(_HERE)
    for candidate in [
        _HERE.parent / "vendor" / "TCP-IP-4Axis-Python",
        _HERE.parent.parent.parent / "vendor" / "TCP-IP-4Axis-Python",
    ]:
        if (candidate / "dobot_api.py").exists():
            return str(candidate)
    raise ImportError(
        "dobot_api.py not found.\n"
        "Clone the SDK:\n"
        "  git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git "
        "vendor/TCP-IP-4Axis-Python\n"
        "Or place dobot_api.py next to utils.py."
    )


def _parse_pose_mg400(response):
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", response)
    floats = [float(n) for n in nums]
    if len(floats) >= 5:
        return floats[1], floats[2], floats[3], floats[4]
    if len(floats) == 4:
        return floats[0], floats[1], floats[2], floats[3]
    raise ValueError(f"Cannot parse pose from: {response!r}")


_MG400_READY = (300, 0, 50, 0)


def _setup_mg400():
    sdk_dir = _find_dobot_api()
    if sdk_dir not in sys.path:
        sys.path.insert(0, sdk_dir)
    from dobot_api import DobotApiDashboard, DobotApiMove

    ip = os.environ.get("MG400_IP", MG400_IP)
    print(f"[setup] Connecting to MG400 at {ip} ...")
    dashboard = DobotApiDashboard(ip, 29999)
    move_api  = DobotApiMove(ip, 30003)

    dashboard.EnableRobot()
    time.sleep(1.5)
    err = dashboard.GetErrorID()
    if "{}" not in err and "0,{}" not in err:
        dashboard.ClearError()
        time.sleep(0.5)
        dashboard.Continue()
        time.sleep(0.5)

    move_api.MovJ(*_MG400_READY)
    move_api.Sync()
    print("[setup] Ready.")
    return Robot("mg400", dashboard=dashboard, move_api=move_api)


def _move_mg400(robot, j1, j2, j3, j4):
    robot._h["move_api"].JointMovJ(j1, j2, j3, j4)
    robot._h["move_api"].Sync()


def _read_pose_mg400(robot):
    return _parse_pose_mg400(robot._h["dashboard"].GetPose())


def _go_home_mg400(robot):
    robot._h["move_api"].MovJ(*_MG400_READY)
    robot._h["move_api"].Sync()


def _teardown_mg400(robot):
    try:
        _go_home_mg400(robot)
    except Exception:
        pass
    try:
        robot._h["dashboard"].DisableRobot()
    except Exception:
        pass
    for obj in (robot._h["dashboard"], robot._h["move_api"]):
        try:
            obj.close()
        except Exception:
            pass
    print("[teardown] Done.")


# ── Dispatch tables ───────────────────────────────────────────────────────────

_SETUP     = {"magician": _setup_magician,     "mg400": _setup_mg400}
_MOVE      = {"magician": _move_magician,      "mg400": _move_mg400}
_READ_POSE = {"magician": _read_pose_magician, "mg400": _read_pose_mg400}
_TEARDOWN  = {"magician": _teardown_magician,  "mg400": _teardown_mg400}


# ── Public API ────────────────────────────────────────────────────────────────

def setup():
    """Connect to the robot selected by ROBOT_TYPE and move home."""
    return _SETUP[ROBOT_TYPE]()


def move_and_get_feedback(robot, q):
    """Move robot to q=[q1, q2, q3, q4] (body-frame), return (x, y, z, r)."""
    bounds = _CONFIGS[robot.type]["joint_bounds"]
    j1, j2, j3, j4 = _to_firmware_angles(q)
    cj1, cj2, cj3, cj4 = _clamp_firmware_angles(j1, j2, j3, j4, bounds)
    if (cj1, cj2, cj3, cj4) != (j1, j2, j3, j4):
        print("Joint values exceed safe limits. Motion denied!")
        return _READ_POSE[robot.type](robot)
    _MOVE[robot.type](robot, j1, j2, j3, j4)
    return _READ_POSE[robot.type](robot)


def teardown(robot):
    """Move home and close the connection."""
    _TEARDOWN[robot.type](robot)
