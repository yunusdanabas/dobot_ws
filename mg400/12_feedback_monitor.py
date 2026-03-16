"""
12_feedback_monitor.py — Live pose monitor using port 30004 feedback + viz.

Port 30004 streams 1440-byte binary packets at 8 ms intervals.
Each packet is parsed with the SDK's MyType numpy dtype (defined in dobot_api.py).

Key fields extracted from each packet:
  tool_vector_actual[0..3] → x, y, z, r  (Cartesian TCP pose, mm and deg)
  robot_mode               → current state (5=ENABLE, 7=RUNNING, 9=ERROR ...)
  test_value               → magic number 0x123456789ABCDEF; skip invalid packets
  EnableStatus             → 1 if robot is enabled
  ErrorStatus              → 1 if robot has an uncleared error

Displays live X/Y/Z/R and robot_mode at the configured Hz, plus sends to viz.
No motion commands — robot can be disabled (just reading state).

Usage:
    python 12_feedback_monitor.py [--ip 192.168.2.7] [--viz] [--hz 10]
    python 12_feedback_monitor.py --robot 2 [--viz]
"""

import argparse
import threading
import time

import numpy as np

from utils_mg400 import (
    connect,
    close_all,
    MG400_IP,
    ROBOT_IPS,
)
from viz_mg400 import RobotViz

# Import MyType from the SDK (resolved via utils_mg400's sys.path insertion)
from dobot_api import MyType  # noqa: E402 (path set by utils_mg400 import)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PACKET_SIZE = 1440
TEST_VALUE  = 0x123456789ABCDEF   # magic number in valid packets

# ---------------------------------------------------------------------------
# Shared state updated by reader thread
# ---------------------------------------------------------------------------

_lock      = threading.Lock()
_feed_data = {
    "x":            0.0,
    "y":            0.0,
    "z":            0.0,
    "r":            0.0,
    "robot_mode":   None,
    "enabled":      False,
    "error":        False,
    "valid":        False,
    "packets":      0,
}


def _feed_thread(feed) -> None:
    """Daemon thread: read 1440-byte packets from port 30004 and parse."""
    while True:
        try:
            data     = bytes()
            has_read = 0
            while has_read < PACKET_SIZE:
                chunk = feed.socket_dobot.recv(PACKET_SIZE - has_read)
                if chunk:
                    has_read += len(chunk)
                    data     += chunk

            info = np.frombuffer(data, dtype=MyType)

            # Validate magic number
            if int(info["test_value"][0]) != TEST_VALUE:
                continue

            tv   = info["tool_vector_actual"][0]   # [x, y, z, r, ...]
            mode = int(info["robot_mode"][0])
            ena  = bool(int(info["EnableStatus"][0][0]))
            err  = bool(int(info["ErrorStatus"][0][0]))

            with _lock:
                _feed_data["x"]          = float(tv[0])
                _feed_data["y"]          = float(tv[1])
                _feed_data["z"]          = float(tv[2])
                _feed_data["r"]          = float(tv[3])
                _feed_data["robot_mode"] = mode
                _feed_data["enabled"]    = ena
                _feed_data["error"]      = err
                _feed_data["valid"]      = True
                _feed_data["packets"]   += 1

        except Exception:
            pass
        time.sleep(0.001)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MG400 live feedback monitor")
    parser.add_argument("--ip",    default=MG400_IP, help="MG400 IP address")
    parser.add_argument("--robot", type=int, choices=[1, 2, 3, 4], metavar="N",
                        help="Robot number 1-4 (overrides --ip)")
    parser.add_argument("--viz", action="store_true", help="Enable visualizer")
    parser.add_argument("--hz",    type=float, default=10.0,
                        help="Display/viz update rate in Hz (default 10)")
    args = parser.parse_args()
    ip = ROBOT_IPS[args.robot] if args.robot else args.ip

    interval = 1.0 / max(1.0, args.hz)

    print(f"Connecting to MG400 at {ip} ...")
    dashboard, move_api, feed = connect(ip)
    print("  Connected: dashboard(29999), move(30003), feed(30004)")
    print("  Robot does NOT need to be enabled for pose monitoring.\n")

    viz = RobotViz(enabled=args.viz)

    # Start binary feedback reader thread
    ft = threading.Thread(target=_feed_thread, args=(feed,), daemon=True)
    ft.start()
    print("  Port 30004 reader started (8 ms binary packets, MyType numpy parse)")

    # Wait for first valid packet
    print("  Waiting for first valid packet ...")
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        with _lock:
            if _feed_data["valid"]:
                break
        time.sleep(0.05)
    else:
        print("  [Warning] No valid packet received in 5 s. Check robot is powered.")

    print(f"\nDisplaying pose at {args.hz:.0f} Hz. Press Ctrl+C to stop.\n")
    header = f"  {'X(mm)':>8}  {'Y(mm)':>8}  {'Z(mm)':>8}  {'R(deg)':>8}  {'Mode':>5}  {'State':<16}  {'Pkts'}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    count = 0
    try:
        while True:
            t0 = time.perf_counter()

            with _lock:
                x    = _feed_data["x"]
                y    = _feed_data["y"]
                z    = _feed_data["z"]
                r    = _feed_data["r"]
                mode = _feed_data["robot_mode"]
                ena  = _feed_data["enabled"]
                err  = _feed_data["error"]
                pkts = _feed_data["packets"]
                valid = _feed_data["valid"]

            if valid:
                state = ("ERROR " if err else "") + ("ENABLED" if ena else "disabled")
                viz.send(x, y, z, r)
                print(
                    f"  {x:8.2f}  {y:8.2f}  {z:8.2f}  {r:8.2f}"
                    f"  {str(mode) if mode is not None else '---':>5}  {state:<16}  {pkts}"
                )
                count += 1

            elapsed = time.perf_counter() - t0
            if elapsed < interval:
                time.sleep(interval - elapsed)

    except KeyboardInterrupt:
        pass

    print(f"\nMonitor stopped after {count} display cycles ({_feed_data['packets']} total packets).")

    try:
        viz.close()
    except Exception:
        pass
    close_all(dashboard, move_api, feed)
    print("Connections closed.")


if __name__ == "__main__":
    main()
