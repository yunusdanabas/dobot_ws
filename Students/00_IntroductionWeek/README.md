# Week 0 — Magician Intro

## Setup

Run all commands from inside this folder (`00_IntroductionWeek/`).

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r magician/requirements.txt
```

Magician serial permission (one-time, then re-login):

```bash
sudo usermod -a -G dialout $USER
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r magician\requirements.txt
```

## Magician Scripts

```bash
cd magician
python 01_init_check.py
python 02_joint_control.py
python 03_relative_joint_control.py
```

## Report Template

LaTeX template and quick-start notes: [`Report Latex/`](./Report%20Latex/)

---

For MG400 (Week 1), see [`../01_SecondWeek/README.md`](../01_SecondWeek/README.md).
