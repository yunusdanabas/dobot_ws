"""
00_connectivity_check.py — 3-phase connectivity diagnostics for all MG400 robots.

Phase 1 — Network layer:
  * Ping each robot IP
  * TCP port probe all three ports (29999/30003/30004)
  * Detect lingering connections from this PC via ss

Phase 2 — Application layer (dashboard-only, for robots with port 29999 open):
  * Connect via DobotApiDashboard (try/finally guaranteed cleanup)
  * Query: GetVersion(), RobotMode(), GetErrorID(), GetPose(), GetAngle()
  * Parse and report firmware, mode, errors, pose, joint angles

Phase 3 — Auto-remediation:
  * Identify failure patterns → targeted recommendations
  * If robot is in ERROR mode, attempt ClearError() + Continue() and recheck

Usage:
    python 00_connectivity_check.py              # check all 4 robots
    python 00_connectivity_check.py --robot 4    # check single robot
"""

from __future__ import annotations

import argparse
import re
import socket
import subprocess
import sys
import time
from typing import Optional, Tuple

from utils_mg400 import (
    DASHBOARD_PORT, FEED_PORT, MOVE_PORT, ROBOT_IPS, ROBOT_MODE,
    parse_angles, parse_error_ids, parse_pose, parse_robot_mode,
)

# ---------------------------------------------------------------------------
# Phase 1 — Network layer
# ---------------------------------------------------------------------------


def ping_host(ip: str, count: int = 3, timeout: int = 1) -> bool:
    """Return True if host responds to ICMP ping."""
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout), ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_tcp_port(ip: str, port: int, timeout: float = 2.0) -> Tuple[bool, str]:
    """Try to open a TCP connection. Return (ok, detail_msg)."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True, "open"
    except ConnectionRefusedError:
        return False, "ConnectionRefused"
    except socket.timeout:
        return False, "Timeout"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def check_local_connections(ip: str) -> list[str]:
    """Return list of established connections from this PC to the robot IP.

    Uses 'ss -tnp dst <ip>' so PID and process name are included in output.
    Returns one string per connection (header line excluded).
    """
    connections: list[str] = []
    try:
        result = subprocess.run(
            ["ss", "-tnp", "dst", ip],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = result.stdout.strip().splitlines()
        for line in lines[1:]:   # skip column-header row
            if line.strip():
                connections.append(line.strip())
    except Exception:
        pass
    return connections


def phase1_network(ip: str) -> dict:
    """Ping + TCP port probes + lingering-connection scan. Return results dict."""
    reachable = ping_host(ip)
    ports: dict = {}
    for name, port in [
        ("dashboard", DASHBOARD_PORT),
        ("move",      MOVE_PORT),
        ("feed",      FEED_PORT),
    ]:
        ok, msg = check_tcp_port(ip, port)
        ports[name] = {"ok": ok, "detail": msg, "port": port}
    local_conns = check_local_connections(ip)
    return {"reachable": reachable, "ports": ports, "local_connections": local_conns}


# ---------------------------------------------------------------------------
# Response normalisation / diagnostics
# ---------------------------------------------------------------------------


def _normalize_response(response: object) -> str:
    """Return a text response regardless of SDK return type."""
    if response is None:
        return ""
    if isinstance(response, bytes):
        return response.decode("utf-8", errors="replace")
    return str(response)


def _sanitize_payload(payload: str, limit: int = 140) -> str:
    """Compact payload text for one-line diagnostics."""
    compact = (
        (payload or "")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .strip()
    )
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def _format_query_error(name: str, exc: Exception, payload: str | None = None) -> str:
    """Build a compact query error with optional raw payload snippet."""
    if payload is None:
        return f"{name}: {exc}"
    return f"{name}: {exc}; raw={_sanitize_payload(payload)!r}"


def _query_get_version(dashboard) -> str:
    """Query firmware version across SDK variants."""
    if hasattr(dashboard, "GetVersion"):
        return _normalize_response(dashboard.GetVersion())
    if hasattr(dashboard, "sendRecvMsg"):
        return _normalize_response(dashboard.sendRecvMsg("GetVersion()"))
    raise AttributeError("dashboard object has neither GetVersion nor sendRecvMsg")


# ---------------------------------------------------------------------------
# Phase 2 — Application layer
# ---------------------------------------------------------------------------


def phase2_application(ip: str, dash_open: bool) -> Optional[dict]:
    """Query the dashboard API. Returns a result dict, or None if dash closed.

    Only connects to port 29999 (dashboard) so feed-port failures don't block
    this phase. Connection is always closed in the finally block.
    """
    if not dash_open:
        return None

    # dobot_api was added to sys.path as a side-effect of importing utils_mg400
    from dobot_api import DobotApiDashboard  # noqa: PLC0415

    result: dict = {
        "version":       None,
        "mode_raw":      None,
        "mode_name":     "unavailable",
        "error_ids":     None,
        "pose":          None,
        "angles":        None,
        "connect_error": None,
        "query_errors":  [],
        "raw":           {},
    }
    dashboard = None
    try:
        dashboard = DobotApiDashboard(ip, DASHBOARD_PORT)

        try:
            ver_resp = _query_get_version(dashboard)
            result["raw"]["GetVersion"] = ver_resp
            result["version"] = ver_resp.strip() or None
        except Exception as exc:
            result["query_errors"].append(_format_query_error("GetVersion", exc))

        try:
            mode_resp = _normalize_response(dashboard.RobotMode())
            result["raw"]["RobotMode"] = mode_resp
            mode_raw  = parse_robot_mode(mode_resp)
            result["mode_raw"]  = mode_raw
            result["mode_name"] = ROBOT_MODE.get(mode_raw, f"UNKNOWN({mode_raw})")
        except Exception as exc:
            result["mode_name"] = f"ERR: {exc}"
            result["query_errors"].append(
                _format_query_error("RobotMode", exc, result["raw"].get("RobotMode"))
            )

        try:
            err_resp = _normalize_response(dashboard.GetErrorID())
            result["raw"]["GetErrorID"] = err_resp
            result["error_ids"] = parse_error_ids(err_resp)
        except Exception as exc:
            result["query_errors"].append(
                _format_query_error("GetErrorID", exc, result["raw"].get("GetErrorID"))
            )

        try:
            pose_resp = _normalize_response(dashboard.GetPose())
            result["raw"]["GetPose"] = pose_resp
            result["pose"] = parse_pose(pose_resp)
        except Exception as exc:
            result["query_errors"].append(
                _format_query_error("GetPose", exc, result["raw"].get("GetPose"))
            )

        try:
            angle_resp = _normalize_response(dashboard.GetAngle())
            result["raw"]["GetAngle"] = angle_resp
            result["angles"] = parse_angles(angle_resp)
        except Exception as exc:
            result["query_errors"].append(
                _format_query_error("GetAngle", exc, result["raw"].get("GetAngle"))
            )

    except Exception as exc:
        result["connect_error"] = str(exc)
    finally:
        if dashboard is not None:
            try:
                dashboard.close()
            except Exception:
                pass

    return result


# ---------------------------------------------------------------------------
# Phase 3 — Auto-remediation helpers
# ---------------------------------------------------------------------------


def _attempt_clear_error(ip: str) -> str:
    """Open a fresh dashboard connection, call ClearError+Continue, recheck mode.

    Returns a one-line status string. Connection is always closed in finally.
    """
    from dobot_api import DobotApiDashboard  # noqa: PLC0415

    dashboard = None
    try:
        dashboard = DobotApiDashboard(ip, DASHBOARD_PORT)
        dashboard.ClearError()
        dashboard.Continue()
        time.sleep(1.0)  # allow firmware state transition
        mode_resp = _normalize_response(dashboard.RobotMode())
        new_mode  = parse_robot_mode(mode_resp)
        new_name  = ROBOT_MODE.get(new_mode, f"UNKNOWN({new_mode})")
        return f"After ClearError+Continue: mode is now {new_mode}={new_name}"
    except Exception as exc:
        return f"ClearError attempt failed: {exc}"
    finally:
        if dashboard is not None:
            try:
                dashboard.close()
            except Exception:
                pass


def phase3_remediation(ip: str, p1: dict, p2: Optional[dict]) -> list[str]:
    """Analyse Phase 1+2 results and return a list of action strings."""
    actions: list[str] = []
    reachable  = p1["reachable"]
    ports      = p1["ports"]
    local_conns = p1["local_connections"]
    dash_ok  = ports["dashboard"]["ok"]
    move_ok  = ports["move"]["ok"]
    feed_ok  = ports["feed"]["ok"]

    # ── Not reachable ──────────────────────────────────────────────────────
    if not reachable:
        actions.append(
            "Check Ethernet cable, robot power, and that the PC Ethernet adapter "
            "is set to static IP 192.168.2.100 / 255.255.255.0."
        )
        return actions

    # ── Lingering local connections ────────────────────────────────────────
    if local_conns:
        actions.append(
            f"This PC has {len(local_conns)} lingering connection(s) to {ip}. "
            "Kill the stuck process(es) shown in Phase 1 to release ports."
        )

    # ── Port-level failures ────────────────────────────────────────────────
    if not dash_ok and not move_ok and not feed_ok:
        actions.append(
            f"All 3 ports refused (ping OK). Controller may still be starting up — "
            "wait 30 s and retry. If it persists, power-cycle the robot."
        )
    else:
        if not dash_ok:
            actions.append(
                f"Dashboard port {DASHBOARD_PORT} refused. "
                "Another client may hold it. Wait ~10 s or power-cycle the robot."
            )
        if not move_ok:
            actions.append(
                f"Move port {MOVE_PORT} refused. "
                "Close DobotStudio or other MG400 scripts and retry."
            )
        if not feed_ok and dash_ok and move_ok:
            # Canonical "feed only refused" pattern
            actions.append(
                f"Feed port {FEED_PORT} refused (dashboard+move are OK). "
                "Another client is likely occupying port 30004 — it accepts only "
                "one simultaneous connection. "
                "→ Close DobotStudio or other MG400 scripts on any PC connected to "
                f"this robot. If the issue persists, power-cycle robot ({ip})."
            )
        elif not feed_ok:
            actions.append(
                f"Feed port {FEED_PORT} refused. "
                "Check for external clients or power-cycle the robot."
            )

    # ── API-level failures ─────────────────────────────────────────────────
    if p2 is not None and p2.get("connect_error"):
        actions.append(f"Dashboard API connect error: {p2['connect_error']}")
    if p2 is not None and p2.get("query_errors"):
        issues = "; ".join(p2["query_errors"])
        actions.append(
            "Dashboard API payload parse issue(s): "
            f"{issues}. This is independent from feed-port connectivity."
        )

    # ── Mode-based remediation ─────────────────────────────────────────────
    if p2 is not None and p2.get("mode_raw") is not None:
        mode = p2["mode_raw"]
        if mode == 9:   # ERROR
            actions.append(
                "Robot is in ERROR mode — attempting ClearError() + Continue()..."
            )
            result = _attempt_clear_error(ip)
            actions.append(f"  → {result}")
        elif mode == 4:  # DISABLED
            actions.append(
                "Robot is DISABLED. "
                "Call dashboard.EnableRobot() before sending any motion commands."
            )
    elif p2 is not None and p2.get("query_errors"):
        actions.append(
            "RobotMode() payload is malformed/unreadable. Compare this robot against "
            "a known-good MG400 on the same SDK; if mismatch persists, power-cycle "
            "and verify controller firmware/config."
        )

    if not actions:
        actions.append("All checks passed — robot is healthy.")

    return actions


# ---------------------------------------------------------------------------
# Per-robot report
# ---------------------------------------------------------------------------


def check_robot(robot_id: int, ip: str) -> dict:
    """Run all 3 phases for one robot, print a formatted report, return results."""
    width = 62
    print(f"\n{'=' * width}")
    print(f"  Robot {robot_id}  ({ip})")
    print(f"{'=' * width}")

    # ── Phase 1 ──────────────────────────────────────────────────────────
    print("\n  [Phase 1] Network Layer")
    p1        = phase1_network(ip)
    reachable = p1["reachable"]
    ports     = p1["ports"]

    print(f"    Ping:      {'OK' if reachable else 'FAILED'}")
    for name, info in ports.items():
        tag = "OPEN    " if info["ok"] else "REFUSED "
        print(f"    Port {info['port']:5d} ({name:9s}): {tag}  {info['detail']}")

    local_conns = p1["local_connections"]
    if local_conns:
        print(f"\n    *** Lingering connections from this PC to {ip} ***")
        for conn in local_conns:
            print(f"        {conn}")
    else:
        print(f"    No lingering connections from this PC.")

    # ── Phase 2 ──────────────────────────────────────────────────────────
    print("\n  [Phase 2] Application Layer")
    p2: Optional[dict] = None
    if not reachable:
        print("    Skipped — host unreachable.")
    elif not ports["dashboard"]["ok"]:
        print("    Skipped — dashboard port not accessible.")
    else:
        p2 = phase2_application(ip, ports["dashboard"]["ok"])
        if p2 is None or p2.get("connect_error"):
            err = (p2 or {}).get("connect_error", "unknown error")
            print(f"    Dashboard API connection failed: {err}")
        else:
            version = p2.get("version")
            print(f"    Version:   {version if version else 'unavailable'}")
            mode_raw  = p2.get("mode_raw")
            mode_name = p2.get("mode_name", "N/A")
            label = f"{mode_raw}={mode_name}" if mode_raw is not None else mode_name
            print(f"    Mode:      {label}")
            err_ids = p2.get("error_ids")
            if err_ids is None:
                print("    Error IDs: unavailable (payload parse failed)")
            else:
                print(f"    Error IDs: {err_ids if err_ids else 'none'}")
            pose = p2.get("pose")
            if pose:
                x, y, z, r = pose
                print(f"    Pose:      X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}  mm/°")
            angles = p2.get("angles")
            if angles:
                j1, j2, j3, j4 = angles
                print(f"    Joints:    J1={j1:.1f}  J2={j2:.1f}  J3={j3:.1f}  J4={j4:.1f}  °")
            query_errors = p2.get("query_errors", [])
            if query_errors:
                print("    API payload issues:")
                for issue in query_errors:
                    print(f"      - {issue}")
                raw_payloads = p2.get("raw", {})
                if raw_payloads:
                    print("    Raw payload snippets:")
                    for cmd, payload in raw_payloads.items():
                        print(f"      - {cmd}: {_sanitize_payload(payload)!r}")

    # ── Phase 3 ──────────────────────────────────────────────────────────
    print("\n  [Phase 3] Remediation")
    actions = phase3_remediation(ip, p1, p2)
    for action in actions:
        print(f"    {action}")

    return {"p1": p1, "p2": p2, "actions": actions}


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------


def print_summary(results: dict) -> None:
    width = 62
    print(f"\n{'=' * width}")
    print("  Summary")
    print(f"{'=' * width}")
    for rid in sorted(results):
        ip   = ROBOT_IPS[rid]
        p1   = results[rid]["p1"]
        reachable  = p1["reachable"]
        bad_ports  = [n for n, info in p1["ports"].items() if not info["ok"]]
        actions    = results[rid].get("actions", [])

        parts: list[str] = ["PING_OK" if reachable else "PING_FAIL"]
        if reachable and not bad_ports:
            parts.append("ALL_PORTS_OK")
        elif bad_ports:
            parts.append("PORT_ISSUES:" + ",".join(bad_ports))

        print(f"  Robot {rid} ({ip}): {' | '.join(parts)}")
        for action in actions:
            print(f"    → {action}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MG400 3-phase connectivity diagnostics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ports probed:\n"
            f"  {DASHBOARD_PORT} dashboard\n"
            f"  {MOVE_PORT} move\n"
            f"  {FEED_PORT} feed (telemetry — single-client only)\n"
        ),
    )
    parser.add_argument(
        "--robot",
        type=int,
        choices=list(ROBOT_IPS.keys()),
        metavar="N",
        help="Check only robot N (1–4). Omit to check all.",
    )
    args = parser.parse_args()

    print("MG400 Connectivity Diagnostics — 3 Phases")
    print(
        f"Ports: dashboard={DASHBOARD_PORT}, move={MOVE_PORT}, "
        f"feed={FEED_PORT}"
    )
    print(
        "Robots: "
        + ", ".join(f"{rid}={ip}" for rid, ip in ROBOT_IPS.items())
    )

    robots_to_check = (
        {args.robot: ROBOT_IPS[args.robot]}
        if args.robot
        else dict(ROBOT_IPS)
    )
    print(f"\nChecking {len(robots_to_check)} robot(s)...")

    results: dict = {}
    for rid, ip in robots_to_check.items():
        results[rid] = check_robot(rid, ip)

    print_summary(results)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
