# Windows Quick Start

Use PowerShell from the repo root.

## 1. Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks `Activate.ps1`:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

MG400 scripts also need the official SDK:

```powershell
git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git vendor\TCP-IP-4Axis-Python
```

Optional Magician vendor checkout:

```powershell
git clone https://github.com/AlexGustafsson/dobot-python.git vendor\dobot-python
```

## 2. Magician

Find the USB serial port:

```powershell
python magician\01_find_port.py
```

Connect:

```powershell
python magician\02_first_connection.py
```

Force a specific port if needed:

```powershell
$env:DOBOT_PORT = "COM3"
python magician\02_first_connection.py
```

Common scripts:

```powershell
python magician\03_safe_move_demo.py
python magician\07_keyboard_teleop.py
python magician\17_visualizer.py
```

Notes:
- Only one program can use the serial port at a time.
- Close DobotStudio before running Python scripts.
- `magician\07_keyboard_teleop.py` is the main teleop script on Windows.

## 3. MG400

Lab robot IPs:

| Robot | IP |
|---|---|
| 1 | `192.168.2.7` |
| 2 | `192.168.2.10` |
| 3 | `192.168.2.9` |
| 4 | `192.168.2.6` |

PC Ethernet should be `192.168.2.100/24`.

Show adapters:

```powershell
.\windows\Set-MG400StaticIp.ps1
```

Apply the standard MG400 adapter address from an elevated PowerShell window:

```powershell
.\windows\Set-MG400StaticIp.ps1 -InterfaceAlias "Ethernet" -Apply
```

Check the link:

```powershell
ping 192.168.2.7
```

Connect and test:

```powershell
python mg400\01_connect_test.py
python mg400\02_first_connection.py
python mg400\07_keyboard_teleop.py
```

Choose another robot:

```powershell
python mg400\01_connect_test.py --robot 2
python mg400\02_first_connection.py --robot 4
```

Use a custom IP:

```powershell
python mg400\01_connect_test.py --ip 192.168.2.77
```

Or set the default for the current shell:

```powershell
$env:DOBOT_MG400_IP = "192.168.2.77"
python mg400\01_connect_test.py
```

Useful scripts:

```powershell
python mg400\03_safe_move_demo.py
python mg400\12_feedback_monitor.py --viz
python mg400\17_joint_control_gui.py
python mg400\00_connectivity_check.py
```

## 4. Sliding Rail

Robot 2 is the default slider robot.

One-time DobotStudio Pro setup:
1. Open `Configure`.
2. Open `External Axis`.
3. Set type to `Linear`.
4. Set unit to `mm`.
5. Enable the external axis.
6. Save and reboot the controller.

Run:

```powershell
python mg400\slider\01_slider_connect_test.py
python mg400\slider\02_slider_basic.py
python mg400\slider\03_slider_arm_demo.py --viz
python mg400\slider\04_slider_teleop.py
```

## 5. Student Intro Scripts

Run from the script directory:

```powershell
# Week 0 — Magician
Push-Location Students\00_IntroductionWeek\magician
python 01_init_check.py
python 02_joint_control.py
python 03_relative_joint_control.py
Pop-Location

# Week 1 — MG400
Push-Location Students\01_SecondWeek\mg400
python 01_init_check.py
python 02_joint_control.py
python 03_relative_joint_control.py
python 04_slider_intro.py
Pop-Location
```

## 6. Common Fixes

- `Activate.ps1` blocked: run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- `dobot_api.py not found`: clone `vendor\TCP-IP-4Axis-Python`
- Magician port not found: run `python magician\01_find_port.py` and, if needed, set `$env:DOBOT_PORT`
- MG400 connection fails: confirm robot power, cable, `192.168.2.100/24`, and `ping <robot-ip>`
- Teleop exits immediately: run it from a normal interactive PowerShell or Windows Terminal tab
- **DobotStudio background service holds the port** — DobotStudio v2+ can leave `DobotstudioService.exe`
  running after closing the UI. Open Task Manager (Ctrl+Shift+Esc) → Details tab, find and end
  `DobotstudioService.exe`, or disable it via Services (`services.msc`).
- **`python` opens Microsoft Store** — Windows 11 App Execution Aliases redirect the bare `python`
  command to the Store. Disable via Settings → Apps → Advanced app settings → App execution aliases,
  then toggle off the Python stubs. Use the venv's `python` or the `py` launcher instead.
- **COM port number changes after replug** — Windows assigns a new COM number when a USB device
  plugs into a different physical port. Always use the same USB port, or re-run
  `python magician\01_find_port.py` and update `$env:DOBOT_PORT`.
- **Windows Firewall blocks MG400 TCP ports** — Even when `ping` succeeds, Defender Firewall may
  block outbound TCP to ports 29999/30003/30004. Add an outbound allow rule for `192.168.2.0/24`
  in Defender Firewall Advanced Security, or temporarily disable the private network firewall.
- **`Set-MG400StaticIp.ps1 -Apply` requires Administrator** — Right-click Windows Terminal →
  "Run as Administrator". Run `Get-NetAdapter` first to confirm the exact interface alias name.
- **Visualizer window steals keyboard focus** — The pyqtgraph window may come to the foreground
  and stop keyboard input reaching the teleop loop. Alt-Tab back to the terminal to restore input,
  or run with `--no-viz`.
- **`pip install` fails with "Microsoft Visual C++ required"** — Some PyQt5/pyqtgraph wheels need
  the MSVC build tools. Fix: `pip install --only-binary :all: PyQt5 pyqtgraph`, or install
  Visual C++ Build Tools via `winget install Microsoft.VisualCppBuildTools`.

Useful references:
- [`README.md`](../README.md)
- [`GUIDE.md`](../GUIDE.md)
- [`docs/README.md`](../docs/README.md)
- [`mg400/MG400_info.md`](../mg400/MG400_info.md)
