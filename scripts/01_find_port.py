"""
01_find_port.py — Discover all serial ports and highlight the Dobot.

Run this first, before any connection script, to find the correct port.

Usage:
    python 01_find_port.py
"""

from serial.tools import list_ports
from utils import find_port

DOBOT_KEYWORD = "Silicon Labs"  # CP210x USB-to-UART bridge description

def main():
    ports = list(list_ports.comports())

    if not ports:
        print("No serial ports found. Is the robot plugged in?")
        return

    print(f"{'Device':<20} {'Description':<40} {'HWID'}")
    print("-" * 90)

    for p in ports:
        marker = "  <-- DOBOT" if DOBOT_KEYWORD.lower() in (p.description or "").lower() else ""
        print(f"{p.device:<20} {(p.description or 'n/a'):<40} {p.hwid}{marker}")

    print()
    likely = find_port(DOBOT_KEYWORD)
    if likely and any(p.device == likely for p in ports):
        print(f"[OK] Likely Dobot port: {likely}")
        print(f"     Use PORT = '{likely}' in your connection scripts.")
    else:
        print("[!] No 'Silicon Labs' device found.")
        print("    Check USB cable, power adapter, and driver installation.")
        print("    On Linux: sudo usermod -a -G dialout $USER  (then re-login)")


if __name__ == "__main__":
    main()
