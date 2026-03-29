"""
Minimal MG400 helpers for move-homework.

Public API:
    dashboard, move_api = setup(robot=1)
    x, y, z, r = move_and_get_feedback(move_api, dashboard, q)
    teardown(dashboard, move_api)
"""

import os
import re
import socket
import sys
import time
from contextlib import closing
from pathlib import Path

_HERE = Path(__file__).parent
for _candidate in (
    _HERE,
    _HERE.parent / "vendor" / "TCP-IP-4Axis-Python",
    _HERE.parent.parent.parent.parent / "vendor" / "TCP-IP-4Axis-Python",
):
    if (_candidate / "dobot_api.py").exists():
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
        break
else:
    raise ImportError("dobot_api.py not found. Clone SDK or place it in this folder.")

from dobot_api import DobotApiDashboard, DobotApiMove  # noqa: E402

ROBOT_IPS = {1: "192.168.2.7", 2: "192.168.2.10", 3: "192.168.2.9", 4: "192.168.2.6"}
DASHBOARD_PORT = 29999
MOVE_PORT = 30003
READY_POSE = (300, 0, 50, 0)
SPEED_DEFAULT = 30

JOINT_BOUNDS_FW = {
    "j1": (-160.0, 160.0),
    "j2": (-25.0, 85.0),
    "j3": (-25.0, 105.0),
    "j4": (-180.0, 180.0),
}


def _connect(ip):
    return DobotApiDashboard(ip, DASHBOARD_PORT), DobotApiMove(ip, MOVE_PORT)


def _close_all(dashboard, move_api):
    for obj in (dashboard, move_api):
        try:
            obj.close()
        except Exception:
            pass


def _parse_pose(response):
    nums = [float(n) for n in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", response)]
    if len(nums) >= 5:
        return nums[1], nums[2], nums[3], nums[4]
    return nums[0], nums[1], nums[2], nums[3]


def _check_errors(dashboard):
    try:
        resp = dashboard.GetErrorID()
        ids = [int(n) for n in re.findall(r"\d+", resp) if int(n) != 0]
        if ids:
            dashboard.ClearError()
            dashboard.Continue()
    except Exception:
        pass


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _to_firmware_angles(q):
    """Body-frame -> firmware angles."""
    j3 = q[1] + q[2]
    return float(q[0]), float(q[1]), float(j3), float(q[3])


def _clamp_firmware_angles(j1, j2, j3, j4):
    clamped = (
        _clamp(j1, *JOINT_BOUNDS_FW["j1"]),
        _clamp(j2, *JOINT_BOUNDS_FW["j2"]),
        _clamp(j3, *JOINT_BOUNDS_FW["j3"]),
        _clamp(j4, *JOINT_BOUNDS_FW["j4"]),
    )
    if clamped != (j1, j2, j3, j4):
        print("  [clamp] Joint values were clamped to safe limits.")
    return clamped


def _go_home(move_api):
    move_api.MovJ(*READY_POSE)
    move_api.Sync()


def _move_joint_angles(move_api, q):
    j1, j2, j3, j4 = _to_firmware_angles(q)
    j1, j2, j3, j4 = _clamp_firmware_angles(j1, j2, j3, j4)
    move_api.JointMovJ(j1, j2, j3, j4)
    move_api.Sync()


def _read_pose(dashboard):
    return _parse_pose(dashboard.GetPose())


def compute_placeholder(q):
    """Placeholder for FK/analysis logic.

    Instructor/students can implement this function later.
    """
    _ = q
    return None


def setup(ip=None, robot=None):
    """Connect, enable robot, clear errors, and go home."""
    if robot is not None:
        target = ROBOT_IPS[robot]
    else:
        target = ip or os.environ.get("DOBOT_MG400_IP", ROBOT_IPS[1])

    print(f"[setup] Connecting to MG400 at {target} ...")
    for port in (DASHBOARD_PORT, MOVE_PORT):
        with closing(socket.create_connection((target, port), timeout=1.5)):
            pass

    dashboard, move_api = _connect(target)
    dashboard.EnableRobot()
    time.sleep(1.5)
    _check_errors(dashboard)
    dashboard.SpeedFactor(SPEED_DEFAULT)
    _go_home(move_api)
    print("[setup] Ready.")
    return dashboard, move_api


def teardown(dashboard, move_api):
    """Go home, disable robot, and close connections."""
    try:
        _go_home(move_api)
    except Exception:
        pass
    try:
        dashboard.DisableRobot()
    except Exception:
        pass
    _close_all(dashboard, move_api)
    print("[teardown] Done.")


def move_and_get_feedback(move_api, dashboard, q):
    """Move robot from q=[q1,q2,q3,q4], return actual (x, y, z, r)."""
    _move_joint_angles(move_api, q)
    compute_placeholder(q)
    return _read_pose(dashboard)
