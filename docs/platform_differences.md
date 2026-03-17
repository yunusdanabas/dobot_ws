# Platform Differences

This guide covers the meaningful differences students and TAs encounter across Linux, Windows, and macOS.

## 1. Serial Port Names (Dobot Magician)

| Platform | Typical port name |
|----------|-------------------|
| Windows  | `COM3`, `COM4`, … |
| Linux    | `/dev/ttyUSB0`, `/dev/ttyACM0` |
| macOS    | `/dev/cu.usbserial-*`, `/dev/cu.SLAB_USBtoUART` |

The `DOBOT_PORT` environment variable bypasses auto-detection:
```bash
export DOBOT_PORT=/dev/ttyUSB1   # Linux/macOS
$env:DOBOT_PORT = "COM5"         # Windows PowerShell
```

## 2. Linux Serial Permission (one-time)

Linux requires the user to be in the `dialout` group to access serial devices:
```bash
sudo usermod -a -G dialout $USER
# Log out and back in for the change to take effect.
```
No equivalent step is needed on Windows or macOS.

## 3. Windows PowerShell Activation

Activating a venv on Windows requires an execution policy change if scripts are blocked:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```
On Linux/macOS `source .venv/bin/activate` works without any policy change.

## 4. Terminal Keyboard Input

`terminal_keys.py` (repo root) provides a cross-platform `TerminalKeyReader` that abstracts:
- **Windows**: `msvcrt.getwch()` — two-byte scan codes for arrow/function keys
- **Linux/macOS**: `select` + `termios` raw mode — ANSI escape sequences (`\x1b[A`)

Scripts must **not** import `msvcrt` or `termios` directly; use `TerminalKeyReader` instead.

## 5. TTY Detection

`TerminalKeyReader.require_tty()` returns `False` in:
- VS Code integrated terminal (Windows and Linux)
- Some other IDE terminals

Use **Windows Terminal** or a standard shell tab for keyboard teleop scripts. Pass `--no-viz` if
the pyqtgraph window steals keyboard focus.

## 6. MG400 Ethernet Setup

Both platforms need a static IP `192.168.2.100/24` on the Ethernet adapter connected to the robot.

| Platform | Method |
|----------|--------|
| Windows  | `.\windows\Set-MG400StaticIp.ps1 -Apply` (requires Administrator) |
| Linux    | `nmcli con mod <adapter> ipv4.addresses 192.168.2.100/24 ipv4.method manual && nmcli con up <adapter>` |
| macOS    | System Preferences → Network → Ethernet → Manual → 192.168.2.100 / 255.255.255.0 |

## 7. Extended Key Sequences

Arrow keys and function keys send multi-byte sequences that differ by platform:

| Platform | Sequence for ↑ |
|----------|---------------|
| Windows  | `\xe0\x48` (two `msvcrt` reads) |
| Linux/macOS | `\x1b[A` (ANSI escape) |

`TerminalKeyReader` normalises both to a consistent string (e.g., `"UP"`) so script logic is
platform-neutral.
