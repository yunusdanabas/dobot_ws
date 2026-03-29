"""
utils.py — Student utility module for Dobot Magician FK lab (ME403, Week 2).
Prepared by Yunus Emre Danabas for ME403.

Public API
----------
    bot = setup(port=None)      connect, clear alarms, go home
    moveMagician(bot, q)        move to body-frame angles [q1,q2,q3,q4]
    get_joints(bot)             returns body-frame (q1,q2,q3,q4) in degrees
    get_pose(bot)               returns Cartesian (x,y,z,r) in mm / degrees
    move_and_get_feedback(bot, q)  move to body-frame angles, return actual (x,y,z,r)
    teardown(bot)               go home, close connection

Constants
---------
    L1      = 135.0 mm   upper-arm length (J2 shoulder to elbow)
    L2      = 147.0 mm   forearm length (elbow to end-effector)
    Z_base  = 103.0 mm   shoulder (J2) height above mounting surface
                         (nominal value — measure at lab start; see lab01_fk.py)

Body-frame angles vs firmware angles
-------------------------------------
    The Magician parallel linkage has a firmware quirk:
      J3_firmware = q3 (body-frame offset, NOT accumulated from J2)
      J4_firmware = q2 + q3 + q4 (absolute wrist angle)
    moveMagician() converts body-frame → firmware internally.
    Students only work with body-frame angles.

Setup (one-time, Linux only):
    sudo usermod -a -G dialout $USER   # then log out and back in
"""

from __future__ import annotations

import os
import sys
import time

from serial.tools import list_ports

# ---------------------------------------------------------------------------
# Robot geometry constants
# ---------------------------------------------------------------------------

L1     = 135.0   # mm — upper arm (J2 pivot to elbow)
L2     = 147.0   # mm — forearm (elbow to end-effector)
Z_base = 103.0   # mm — shoulder (J2) height above mounting surface
                 # Verify at lab start: go to q=[0,0,0,0], read get_pose()[2]

# Firmware joint bounds (applied after body-frame → firmware conversion)
JOINT_BOUNDS_FW = {
    "j1": (-90.0,  90.0),
    "j2": (  0.0,  85.0),
    "j3": (-10.0,  85.0),   # firmware J3 = body-frame J3 (no accumulation)
    "j4": (-90.0,  90.0),   # firmware J4 = absolute wrist
}

# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------

_DOBOT_KEYWORDS = ("Silicon Labs", "1A86", "USB2.0-Serial")
_DOBOT_PORT_ENV = "DOBOT_PORT"


def find_port(keywords: tuple[str, ...] = _DOBOT_KEYWORDS) -> str | None:
    """Return the first serial port matching any Dobot USB-serial keyword.

    Honors the DOBOT_PORT environment override when set.
    Falls back to the most likely USB/UART device when no keyword match.
    Returns None if no ports are found.
    """
    preferred = os.environ.get(_DOBOT_PORT_ENV)
    if preferred:
        return preferred

    ports = list(list_ports.comports())

    def combined(p) -> str:
        return f"{(p.description or '')} {p.hwid}".lower()

    for p in ports:
        if any(kw.lower() in combined(p) for kw in keywords):
            return p.device

    # Fallback: pick by platform heuristics
    if not ports:
        return None

    def score(p):
        d = combined(p)
        v = 0
        if any(t in d for t in ("usb", "uart", "cp210", "ch340", "silicon labs")):
            v += 15
        if "bluetooth" in d or "virtual" in d:
            v -= 20
        if "/ttyusb" in p.device.lower() or "/ttyacm" in p.device.lower():
            v += 25
        return v

    best = max(ports, key=score)
    return best.device

# ---------------------------------------------------------------------------
# Internal: body-frame ↔ firmware conversion
# ---------------------------------------------------------------------------


def _rel_to_fw(q: list) -> tuple[float, float, float, float]:
    """Convert body-frame [q1,q2,q3,q4] to firmware (j1,j2,j3,j4).

    Magician parallel linkage:
      j1_fw = q1   (base rotation, identical)
      j2_fw = q2   (shoulder elevation, identical)
      j3_fw = q3   (firmware J3 IS body-frame offset; no accumulation)
      j4_fw = q4   (wrist yaw only; end-effector stays parallel to floor)
    """
    return float(q[0]), float(q[1]), float(q[2]), float(q[3])


def _fw_to_rel(j1: float, j2: float, j3: float, j4: float) -> tuple[float, float, float, float]:
    """Convert firmware joint angles to body-frame.

    Inverse of _rel_to_fw:
      q1 = j1
      q2 = j2
      q3 = j3   (firmware J3 = body-frame, no change)
      q4 = j4   (wrist yaw; end-effector stays parallel to floor)
    """
    return j1, j2, j3, j4


def _clamp_fw(j1: float, j2: float, j3: float, j4: float) -> tuple:
    """Clamp firmware angles to JOINT_BOUNDS_FW. Warn if any value changed."""
    def clamp(v, lo, hi):
        return max(lo, min(hi, v))

    cj1 = clamp(j1, *JOINT_BOUNDS_FW["j1"])
    cj2 = clamp(j2, *JOINT_BOUNDS_FW["j2"])
    cj3 = clamp(j3, *JOINT_BOUNDS_FW["j3"])
    cj4 = clamp(j4, *JOINT_BOUNDS_FW["j4"])
    if (cj1, cj2, cj3, cj4) != (j1, j2, j3, j4):
        print(f"  [moveMagician] Clamped firmware:  "
              f"({j1:.1f},{j2:.1f},{j3:.1f},{j4:.1f}) "
              f"→ ({cj1:.1f},{cj2:.1f},{cj3:.1f},{cj4:.1f})")
    return cj1, cj2, cj3, cj4

# ---------------------------------------------------------------------------
# Pose unpacking
# ---------------------------------------------------------------------------


def _unpack_pose(pose) -> tuple[float, float, float, float, float, float, float, float]:
    """Normalize pydobotplus Pose to flat 8-tuple (x,y,z,r,j1,j2,j3,j4)."""
    if hasattr(pose, "position") and hasattr(pose, "joints"):
        return (
            float(pose.position.x), float(pose.position.y),
            float(pose.position.z), float(pose.position.r),
            float(pose.joints.j1),  float(pose.joints.j2),
            float(pose.joints.j3),  float(pose.joints.j4),
        )
    if isinstance(pose, (tuple, list)) and len(pose) == 8:
        return tuple(float(v) for v in pose)
    raise ValueError(f"Unsupported pose format: {type(pose)!r}")

# ---------------------------------------------------------------------------
# pydobotplus performance patch
# ---------------------------------------------------------------------------


def _patch_pydobotplus() -> None:
    """Remove the unnecessary get_pose() round-trip and print() from move_to().

    Applied once at module import. Silently skips if pydobotplus internals change.
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
                return _orig(self, x=x, y=y, z=z, r=r, wait=wait, mode=mode)
            if mode is None:
                mode = MODE_PTP.MOVJ_XYZ
            return self._extract_cmd_index(
                self._set_ptp_cmd(x, y, z, r, mode, wait=wait)
            )

        _dp.Dobot.move_to = _fast_move_to
    except Exception:
        pass


_patch_pydobotplus()

# ---------------------------------------------------------------------------
# Robot lifecycle
# ---------------------------------------------------------------------------


def setup(port: str | None = None):
    """Connect to Dobot Magician, clear alarms, and move to home.

    Automatically discovers the serial port when port=None.

    Returns:
        bot — Dobot object. Pass this to moveMagician(), get_joints(),
              get_pose(), and teardown().

    Example::

        bot = U.setup()
    """
    from pydobotplus import Dobot

    target = port or find_port()
    if target is None:
        raise OSError(
            "No Dobot serial port found.\n"
            "  • Check USB cable and 12 V power adapter.\n"
            "  • Linux: sudo usermod -a -G dialout $USER  (then re-login)\n"
            "  • Set DOBOT_PORT=/dev/ttyUSB0 to override auto-discovery."
        )

    print(f"[setup] Connecting on {target} ...")
    bot = Dobot(port=target)

    alarms = bot.get_alarms()
    if alarms:
        print(f"[setup] {len(alarms)} alarm(s) detected — clearing.")
        bot.clear_alarms()

    _go_home_internal(bot)
    print(f"[setup] Ready. L1={L1:.0f} mm  L2={L2:.0f} mm  Z_base≈{Z_base:.0f} mm")
    return bot


def teardown(bot) -> None:
    """Move robot to home, then close the serial connection.

    Always call this (or put it in a finally block) to release the port.

    Example::

        try:
            ...
        finally:
            U.teardown(bot)
    """
    try:
        _go_home_internal(bot)
    except Exception:
        pass
    try:
        bot.close()
    except Exception:
        pass
    print("[teardown] Connection closed.")

# ---------------------------------------------------------------------------
# Motion
# ---------------------------------------------------------------------------


def moveMagician(bot, q: list) -> None:
    """Move to body-frame joint configuration q = [q1, q2, q3, q4].

    Each qi is the angle between consecutive links (degrees):
      q1 — base rotation (same as firmware J1)
      q2 — shoulder elevation from horizontal
      q3 — elbow offset FROM the upper-arm direction  (body-frame)
      q4 — wrist offset FROM the forearm direction    (body-frame)

    Conversion chain (Magician parallel linkage):
      J3_firmware = q3              (body-frame; no accumulation quirk)
      J4_firmware = q2 + q3 + q4   (absolute wrist angle)

    Firmware angles are clamped to JOINT_BOUNDS_FW with a warning if changed.

    Args:
        bot: Dobot object returned by setup()
        q:   list [q1, q2, q3, q4] in degrees
    """
    from pydobotplus.dobotplus import MODE_PTP

    if len(q) != 4:
        raise ValueError(f"q must have 4 elements, got {len(q)}")

    # Convert body-frame → firmware
    j1, j2, j3, j4 = _rel_to_fw(q)

    # Print conversion (body-frame → firmware)
    print(f"  [move] body: J1={q[0]:.1f}  J2={q[1]:.1f}  J3={q[2]:.1f}  J4={q[3]:.1f}")
    print(f"         fw:   J1={j1:.1f}  J2={j2:.1f}  J3={j3:.1f}  J4={j4:.1f}")

    # Clamp firmware angles (warn if adjusted)
    j1, j2, j3, j4 = _clamp_fw(j1, j2, j3, j4)

    # Execute MOVJ_ANGLE (interprets values as J1..J4 firmware joint angles)
    bot.move_to(j1, j2, j3, j4, wait=True, mode=MODE_PTP.MOVJ_ANGLE)

# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


def get_joints(bot) -> tuple[float, float, float, float]:
    """Read current body-frame joint angles from the robot.

    Returns:
        (q1, q2, q3, q4) in degrees (body-frame angles between links):
          q1 = J1_firmware   (base, no conversion needed)
          q2 = J2_firmware   (shoulder, no conversion needed)
          q3 = J3_firmware   (Magician: firmware J3 IS body-frame)
          q4 = J4_firmware - J2_firmware - J3_firmware  (wrist body-frame)

    Example::

        q = U.get_joints(bot)
        print(f"Shoulder: {q[1]:.1f}°  Elbow: {q[2]:.1f}°")
    """
    _, _, _, _, j1, j2, j3, j4 = _unpack_pose(bot.get_pose())
    q1, q2, q3, q4 = _fw_to_rel(j1, j2, j3, j4)
    return q1, q2, q3, q4


def get_pose(bot) -> tuple[float, float, float, float]:
    """Read current Cartesian pose from the robot.

    Returns:
        (x, y, z, r) — position in mm, end-effector rotation in degrees.

    Example::

        x, y, z, r = U.get_pose(bot)
        print(f"X={x:.1f}  Y={y:.1f}  Z={z:.1f}")
    """
    x, y, z, r, *_ = _unpack_pose(bot.get_pose())
    return x, y, z, r


def move_and_get_feedback(bot, q: list) -> tuple[float, float, float, float]:
    """Move to body-frame angles, then return the actual Cartesian pose.

    Calls moveMagician(bot, q), reads the actual end-effector position,
    and returns it. Students can add FK prediction / error computation
    in the marked section below.

    Args:
        bot: Dobot object returned by setup()
        q:   [q1, q2, q3, q4] body-frame angles in degrees

    Returns:
        (x, y, z, r) — actual Cartesian pose after the move (mm / degrees)
    """
    # I/O: move robot to requested joint angles
    moveMagician(bot, q)

    # I/O: read actual Cartesian pose after move
    x, y, z, r = get_pose(bot)

    # ------------------------------------------------------------------
    # TODO: add FK prediction and error computation here
    #   predicted = fk_predict(q, L1, L2, Z_base)
    #   error = ...
    # ------------------------------------------------------------------

    return x, y, z, r

# ---------------------------------------------------------------------------
# Internal helpers (not part of student API)
# ---------------------------------------------------------------------------


def _go_home_internal(bot) -> None:
    """Send arm to joint-space home (firmware 0,0,0,0) via MOVJ_ANGLE."""
    from pydobotplus.dobotplus import MODE_PTP
    bot.move_to(0, 0, 0, 0, wait=True, mode=MODE_PTP.MOVJ_ANGLE)
    print("[utils] At home: (J1=0, J2=0, J3=0, J4=0)")
