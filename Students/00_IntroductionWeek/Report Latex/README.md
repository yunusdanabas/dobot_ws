# Dobot Magician — Student Quick-Start

This quick-start accompanies the simplified Magician intro scripts in
`../magician/`. These files are a teaching subset of the full workspace.

---

## Quick Start

```bash
# 1. Activate your Python environment (see "Python Environment" below)
mamba activate dobot         # or: source .venv/bin/activate  (Linux/macOS)
                             #     .venv\Scripts\activate      (Windows)

# 2. Install dependencies for the Magician intro track
cd Students/00_IntroductionWeek/magician
pip install -r requirements.txt

# 3. Run the initialization check
python 01_init_check.py
```

If the script exits cleanly and prints `[OK] Initialization complete.`, your setup is working.

---

## Scripts in This Folder

| Script | What it does | What you learn |
|--------|-------------|----------------|
| `01_init_check.py` | Discovers the serial port, connects, moves to home, prints X/Y/Z and joint angles | Verify hardware + software setup |
| `02_joint_control.py` | Interactive REPL: type four joint angles to move the arm | Forward kinematics, joint space vs Cartesian space |
| `03_relative_joint_control.py` | Interactive REPL: type body-frame relative joint angles | Relative vs absolute joint angles, FK conversion chain |

See [RESOURCES.md](RESOURCES.md) for Dobot specs, coordinate system explanation, and official links.
For the MG400 intro subset, see `../mg400/`.

---

## Hardware Setup

### Before powering on
1. Place the robot on a stable flat surface with enough clear space around it (≥ 40 cm radius).
2. Set the arm to **neutral posture** — rear arm and forearm each roughly 45° from horizontal. This prevents jerky movements at first power-on.
3. Plug in the **wall power adapter** first — USB alone cannot power the robot.
4. Connect the USB cable between the robot and your PC.

### LED and beep signals
| Signal | Meaning |
|--------|---------|
| Steady light + one beep | Ready — safe to run scripts |
| Three rapid beeps | Fault — check arm posture or run the script to see alarm details |
| Flashing light | Homing or executing a command |

### Connectors on the arm (end-effector port)
| Label | Function |
|-------|---------|
| SW1 | Tool power (suction pump) |
| GP1 / GP3 | Analog/digital sensor inputs |
| SW4 | Gripper control |

---

## Platform Setup

### Linux
Grant yourself serial port access (one-time setup, then re-login):
```bash
sudo usermod -a -G dialout $USER
# Log out and log back in for the change to take effect
```
The robot will appear as `/dev/ttyUSB0` or `/dev/ttyACM0`.

### Windows
Plug in the USB cable. On Windows 10/11 the driver is included automatically.
The robot appears as a COM port (`COM3`, `COM4`, etc.).
To find it: open **Device Manager** → expand **Ports (COM & LPT)** → look for "Silicon Labs" or "USB Serial".

### macOS
The robot appears as `/dev/cu.SLAB_USBtoUART` or `/dev/cu.usbserial-*`.
The driver is pre-installed on macOS 12 and later. On older macOS you may need to install it from the Silicon Labs website.

---

## Python Environment

**Option A — mamba (recommended):**
```bash
mamba create -n dobot python=3.10 -y
mamba activate dobot
pip install -r requirements.txt
```

**Option B — venv:**
```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## Important: Close DobotStudio First

Only **one program** can talk to the robot's serial port at a time.
If DobotStudio (or any other program) is open and connected, your Python script will fail to connect.
Close DobotStudio before running any script.

---

## Troubleshooting

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `No serial port found` | USB not connected or power adapter not plugged in | Check both cables; try a different USB port |
| `Permission denied /dev/ttyUSB0` | Missing dialout group (Linux) | `sudo usermod -a -G dialout $USER` then re-login |
| `serial.SerialException: could not open port` | DobotStudio or another script is connected | Close all other programs using the robot |
| Three rapid beeps at power-on | Arm not in neutral posture, or old alarm | Set arm to ~45/45° posture; run `01_init_check.py` — it will clear alarms automatically |
| Script connects but arm doesn't move | Previous alarm state | Run `01_init_check.py` — `prepare_robot()` clears alarms before moving |

---

## Next Steps

Once `01_init_check.py` works, continue to `02_joint_control.py`, then
`03_relative_joint_control.py`.

For the full 18-script lab walkthrough, hardware details, and TA implementation notes see:
`GUIDE.md` in the full course workspace
