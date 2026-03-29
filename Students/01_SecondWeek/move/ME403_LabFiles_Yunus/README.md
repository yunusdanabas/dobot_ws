# Move Homework (Simple Version)

This folder is prepared for a homework where the student gives a single move command.

## What this package provides

- One terminal command format: `move q1 q2 q3 q4`
- One library function that sends robot IO commands
- The same function returns Cartesian feedback `(x, y, z, r)` after motion
- A placeholder function for computation/FK, ready for instructor/student implementation

## File structure

- `magician/interactive_move.py`: user input loop for Magician
- `magician/utils.py`: Magician IO + move-and-feedback function
- `mg400/interactive_move.py`: user input loop for MG400
- `mg400/utils_mg400.py`: MG400 IO + move-and-feedback function

## Command format (both robots)

```text
move 0 30 20 0
q
```

- `move q1 q2 q3 q4`: moves the robot
- returns and prints actual Cartesian pose `(x, y, z, r)`
- `q`: quit the program

## Computation placeholder

The computation/FK part is intentionally left as a placeholder:

- `magician/utils.py` -> `compute_placeholder(q)`
- `mg400/utils_mg400.py` -> `compute_placeholder(q)`

Only IO flow is implemented by default.

## Run: Magician

```bash
cd magician
pip install -r requirements.txt
python interactive_move.py
```

Linux one-time permission:

```bash
sudo usermod -a -G dialout $USER
```

Then log out and log in again.

## Run: MG400

SDK one-time setup from `dobot_ws` root:

```bash
git clone https://github.com/Dobot-Arm/TCP-IP-4Axis-Python.git vendor/TCP-IP-4Axis-Python
```

Run:

```bash
cd mg400
pip install -r requirements.txt
python interactive_move.py
```

Set PC Ethernet to static IP: `192.168.2.100 / 255.255.255.0`.

To choose robot, edit `setup(robot=N)` in `mg400/interactive_move.py`.

| Robot | IP |
|-------|----|
| 1 | 192.168.2.7 |
| 2 | 192.168.2.10 |
| 3 | 192.168.2.9 |
| 4 | 192.168.2.6 |
