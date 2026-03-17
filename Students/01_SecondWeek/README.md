# Week 1 — MG400 Intro

This folder contains the student intro scripts for the **DOBOT MG400** (Ethernet/TCP-IP).
It follows the Week 0 Magician session. See `../00_IntroductionWeek/README.md` for the Magician scripts.

Run all commands from inside this folder (`01_SecondWeek/`).

## Prerequisites

1. **SDK clone** (one-time, run from inside `01_SecondWeek/`):
   ```bash
   git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git vendor/TCP-IP-4Axis-Python
   ```

2. **Static IP setup** — set your PC's Ethernet adapter to `192.168.2.100 / 255.255.255.0`:
   - **Windows**: open *Network Connections → Ethernet adapter → IPv4 Properties*, set static IP `192.168.2.100`, subnet `255.255.255.0`
   - **Linux**: `nmcli con mod <adapter> ipv4.addresses 192.168.2.100/24 ipv4.method manual && nmcli con up <adapter>`

3. **Ping check**:
   ```bash
   ping 192.168.2.7   # Robot 1 (default)
   ```

## Setup

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r mg400/requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r mg400\requirements.txt
```

## Run Instructions

```bash
cd mg400

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

## Robot Network Map

| Robot | IP | Notes |
|-------|----|-------|
| 1 | 192.168.2.7 | default |
| 2 | 192.168.2.10 | has sliding rail |
| 3 | 192.168.2.9 | |
| 4 | 192.168.2.6 | |

## MG400 Safe Operating Bounds

| Axis | Range | Notes |
|------|-------|-------|
| X | 60–400 mm | inner limit ≈60 mm (base singularity) |
| Y | ±220 mm | symmetric |
| Z | 5–140 mm | cannot go negative (0 = mounting surface) |
| R | ±170° | end-effector rotation |

READY_POSE = `(300, 0, 50, 0)` — safe home position.
