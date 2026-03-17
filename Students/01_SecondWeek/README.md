# Week 1 — MG400 Intro

This folder contains the student intro scripts for the **DOBOT MG400** (Ethernet/TCP-IP).
It follows the Week 0 Magician session. See `../00_IntroductionWeek/README.md` for the Magician scripts.

## Prerequisites

1. **SDK clone** (one-time, from repo root):
   ```bash
   git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git vendor/TCP-IP-4Axis-Python
   ```

2. **Static IP setup** — set your PC's Ethernet adapter to `192.168.2.100 / 255.255.255.0`:
   - **Windows**: run `.\windows\Set-MG400StaticIp.ps1 -Apply` from an elevated PowerShell, or see [`../../windows/README.md`](../../windows/README.md)
   - **Linux**: use Network Manager or `nmcli con mod <adapter> ipv4.addresses 192.168.2.100/24 ipv4.method manual`

3. **Ping check**:
   ```bash
   ping 192.168.2.7   # Robot 1 (default)
   ```

## Setup

### Linux / macOS

```bash
source .venv/bin/activate
pip install -r Students/01_SecondWeek/mg400/requirements.txt
```

### Windows (PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r Students\01_SecondWeek\mg400\requirements.txt
```

## Run Instructions

```bash
cd Students/01_SecondWeek/mg400

python 01_init_check.py              # Robot 1 (192.168.2.7)
python 01_init_check.py --robot 2   # Robot 2 (192.168.2.10)
python 02_joint_control.py
python 03_relative_joint_control.py
python 04_slider_intro.py           # Robot 2 only (has the sliding rail)
```

## Scripts

| Script | Description |
|--------|-------------|
| `01_init_check.py` | TCP connectivity check, enable robot, move to READY_POSE, print pose and joint angles |
| `02_joint_control.py` | Interactive REPL: enter J1–J4 absolute angles with FK preview and clamping |
| `03_relative_joint_control.py` | Body-frame FK exercise: enter relative joint angles, see the conversion chain |
| `04_slider_intro.py` | Sliding rail basics for Robot 2 (IP 192.168.2.10, 800 mm travel) |

## References

- MG400 hardware and network notes: [`../../mg400/MG400_info.md`](../../mg400/MG400_info.md)
- Windows setup guide: [`../../windows/README.md`](../../windows/README.md)
- Full lab walkthrough: [`../../GUIDE.md`](../../GUIDE.md)
