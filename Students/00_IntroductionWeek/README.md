# Week 0 — Introduction Week

Both the **Dobot Magician** (USB-serial) and the **DOBOT MG400** (Ethernet/TCP-IP) are
covered in this lab. Each platform has its own subfolder.

---

## Magician Setup

Run all commands from inside `00_IntroductionWeek/`.

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r magician/requirements.txt
```

Serial port permission (one-time, then re-login):

```bash
sudo usermod -a -G dialout $USER
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r magician\requirements.txt
```

### Running the Magician GUI

```bash
cd magician
python 00_magician_gui.py
```

The GUI handles port discovery, connection, alarm clearing, homing, and joint control.

---

## MG400 Setup

### Network (one-time)

Set your PC's Ethernet adapter to static IP `192.168.2.100`, subnet `255.255.255.0`.
Use the sticker on your assigned robot to match Robot Number and IP.

Robot IP table:

| Robot | IP            | Notes            |
|-------|---------------|------------------|
| 1     | 192.168.2.7   | match robot sticker |
| 2     | 192.168.2.10  | match robot sticker |
| 3     | 192.168.2.9   | match robot sticker |
| 4     | 192.168.2.6   | match robot sticker |

Verify connectivity: `ping <assigned-robot-ip>` (example: `ping 192.168.2.7`)

### SDK clone (one-time, run from `dobot_ws/` root)

```bash
git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git vendor/TCP-IP-4Axis-Python
```

### Install dependencies (from `00_IntroductionWeek/`)

```bash
# Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r mg400/requirements.txt
```

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r mg400\requirements.txt
```

### Running the MG400 GUI

```bash
cd mg400
python 00_mg400_gui.py          # select your robot in the GUI dropdown
python 00_mg400_gui.py --robot 2  # optional CLI preselection
```

The GUI handles TCP connection, robot enabling, homing, error clearing, and joint control.

---

## Report Template

LaTeX template and quick-start notes: [`Report Latex/`](./Report%20Latex/)
