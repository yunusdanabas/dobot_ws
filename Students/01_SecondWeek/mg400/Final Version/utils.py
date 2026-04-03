"""
Minimal MG400 helpers for Lab 1 (ME403).

Public API:
    dashboard, move_api = setup()
    x, y, z, r = move_and_get_feedback(dashboard, move_api, q)
    teardown(dashboard, move_api)

Network setup (one-time): set PC Ethernet adapter to static IP 192.168.2.100/24.
Verify: ping 192.168.2.7

SDK setup (one-time):
    git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git vendor/TCP-IP-4Axis-Python
Or place dobot_api.py directly next to this file.
"""

import os
import re
import sys
import time
from pathlib import Path

JOINT_BOUNDS_FW = {
    "j1": (-160.0, 160.0),
    "j2": ( -25.0,  85.0),
    "j3": ( -25.0, 105.0),   # firmware j3 = q2 + q3 (accumulated from horizontal)
    "j4": (-180.0, 180.0),
}

READY_POSE = (300, 0, 50, 0)   # (x mm, y mm, z mm, r deg) — safe home above surface

_HERE = Path(__file__).parent


def _find_dobot_api():
    """Return the directory containing dobot_api.py, or raise ImportError."""
    # 1. Local copy next to this file
    if (_HERE / "dobot_api.py").exists():
        return str(_HERE)
    # 2. vendor/ next to the mg400/ parent folder (standalone distribution)
    vendor_local = _HERE.parent / "vendor" / "TCP-IP-4Axis-Python"
    if (vendor_local / "dobot_api.py").exists():
        return str(vendor_local)
    # 3. vendor/ at the dobot_ws root (full repo checkout)
    vendor_repo = _HERE.parent.parent.parent / "vendor" / "TCP-IP-4Axis-Python"
    if (vendor_repo / "dobot_api.py").exists():
        return str(vendor_repo)
    raise ImportError(
        "dobot_api.py not found.\n"
        "Clone the SDK:\n"
        "  git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git vendor/TCP-IP-4Axis-Python\n"
        "Or place dobot_api.py directly next to utils.py."
    )


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _to_firmware_angles(q):
    """Body-frame [q1, q2, q3, q4] -> MG400 firmware angles.

    MG400 firmware uses accumulated angles from the base:
        j1_fw = q1          (base rotation, same as body-frame)
        j2_fw = q2          (shoulder elevation from horizontal)
        j3_fw = q2 + q3     (forearm absolute angle from horizontal)
        j4_fw = q4          (wrist yaw)
    """
    return float(q[0]), float(q[1]), float(q[1]) + float(q[2]), float(q[3])


def _clamp_firmware_angles(j1, j2, j3, j4):
    return (
        _clamp(j1, *JOINT_BOUNDS_FW["j1"]),
        _clamp(j2, *JOINT_BOUNDS_FW["j2"]),
        _clamp(j3, *JOINT_BOUNDS_FW["j3"]),
        _clamp(j4, *JOINT_BOUNDS_FW["j4"]),
    )


def _parse_pose(response):
    """Parse GetPose() response string -> (x, y, z, r)."""
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", response)
    floats = [float(n) for n in nums]
    if len(floats) >= 5:
        return floats[1], floats[2], floats[3], floats[4]
    if len(floats) == 4:
        return floats[0], floats[1], floats[2], floats[3]
    raise ValueError(f"Cannot parse pose from: {response!r}")


def _go_home(move_api):
    move_api.MovJ(*READY_POSE)
    move_api.Sync()


def setup(ip=None):
    """Connect to MG400, enable robot, and move to home."""
    sdk_dir = _find_dobot_api()
    if sdk_dir not in sys.path:
        sys.path.insert(0, sdk_dir)
    from dobot_api import DobotApiDashboard, DobotApiMove

    target = ip or os.environ.get("MG400_IP", "192.168.2.7")
    print(f"[setup] Connecting to MG400 at {target} ...")
    dashboard = DobotApiDashboard(target, 29999)
    move_api  = DobotApiMove(target, 30003)

    dashboard.EnableRobot()
    time.sleep(1.5)

    # Clear any active errors before moving
    err = dashboard.GetErrorID()
    if "{}" not in err and "0,{}" not in err:
        dashboard.ClearError()
        time.sleep(0.5)
        dashboard.Continue()
        time.sleep(0.5)

    _go_home(move_api)
    print("[setup] Ready.")
    return dashboard, move_api


def teardown(dashboard, move_api):
    """Move home, disable robot, and close connections."""
    try:
        _go_home(move_api)
    except Exception:
        pass
    try:
        dashboard.DisableRobot()
    except Exception:
        pass
    for obj in (dashboard, move_api):
        try:
            obj.close()
        except Exception:
            pass
    print("[teardown] Done.")


def move_and_get_feedback(dashboard, move_api, q):
    """Move robot to q=[q1, q2, q3, q4] (body-frame), return the resulting (x, y, z, r)."""
    j1, j2, j3, j4 = _to_firmware_angles(q)
    cj1, cj2, cj3, cj4 = _clamp_firmware_angles(j1, j2, j3, j4)
    if (cj1, cj2, cj3, cj4) != (j1, j2, j3, j4):
        print("Joint values exceed safe limits. Motion denied!")
        return _parse_pose(dashboard.GetPose())
    move_api.JointMovJ(j1, j2, j3, j4)
    move_api.Sync()
    return _parse_pose(dashboard.GetPose())
