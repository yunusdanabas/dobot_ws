# Week 0 — Magician Intro

## Setup

Run all commands from inside this folder (`00_IntroductionWeek/`).

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

## Running the GUI

```bash
cd magician
python 00_magician_gui.py
```

The GUI handles port discovery, connection, alarm clearing, homing, and joint control.

## Report Template

LaTeX template and quick-start notes: [`Report Latex/`](./Report%20Latex/)

---

For MG400 (Week 1), see [`../01_SecondWeek/README.md`](../01_SecondWeek/README.md).
