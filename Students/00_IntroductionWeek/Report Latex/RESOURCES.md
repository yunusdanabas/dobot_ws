# Dobot Magician — Resources and Reference

---

## What is the Dobot Magician?

The **Dobot Magician** is a 4-degree-of-freedom desktop robotic arm designed for education, prototyping, and light automation. It is widely used in robotics courses because it is affordable, safe, and comes with a Python API.

| Spec | Value |
|------|-------|
| Degrees of freedom | 4 (J1–J4) |
| Maximum reach | 320 mm |
| Payload | 500 g |
| Repeatability | ±0.2 mm |
| End-effectors | Suction cup, gripper, pen/laser holder |
| Interface | USB-serial via CP210x chip (115200 baud) |
| Power | 12 V DC wall adapter (USB alone is insufficient) |
| Communication protocol | Proprietary binary serial protocol |

The arm connects to any PC over USB. Python control is done through the **pydobotplus** library, which translates Python function calls into the robot's binary protocol.

---

## Coordinate System

The Dobot Magician uses a **right-handed Cartesian coordinate system** with the origin at the center of the robot's base:

```
          Z (up)
          |
          |
          +---------- X (forward, away from you)
         /
        /
       Y (left)
```

- **X axis** — forward, pointing away from the front of the base
- **Y axis** — to the left
- **Z axis** — upward; Z = 0 is approximately the table surface

All positions are in **millimetres** (mm). Rotation (R) is in **degrees**.

### Joint Angles

The robot has four joints:

| Joint | Role | Range (safe) | Notes |
|-------|------|-------------|-------|
| **J1** | Base rotation | ±90° | Rotates the entire arm left/right around the Z axis |
| **J2** | Rear arm elevation | 0–85° | Lifts the rear arm segment up from horizontal |
| **J3** | Forearm elevation | -10–85° | Controls forearm angle via a **parallel linkage** |
| **J4** | End-effector rotation | ±90° | Rotates only the tool, not the arm |

#### The Parallel Linkage (J2 + J3)
The Dobot uses a **4-bar parallel linkage** mechanism. This means the forearm's actual angle from horizontal is always `J2 + J3`, not J3 alone. This is why the Forward Kinematics function uses `math.radians(j2 + j3)` for the forearm.

The benefit: the end-effector stays level even as the arm raises and lowers.

### Safe Operating Bounds

| Axis | Safe range | Hard limit |
|------|-----------|-----------|
| X | 120–315 mm | 115–320 mm |
| Y | ±158 mm | ±160 mm |
| Z | 5–155 mm | 0–160 mm |
| R | ±90° | ±135° |

Stay within the **safe range** when writing scripts. The `safe_move()` function in `utils.py` enforces these bounds automatically.

---

## Forward Kinematics (FK)

Given joint angles, FK predicts the Cartesian position:

```
reach  = L1·cos(J2) + L2·cos(J2+J3)   [horizontal distance from base axis]
height = L1·sin(J2) + L2·sin(J2+J3)   [arm height above shoulder pivot]

x = reach · cos(J1)
y = reach · sin(J1)
```

Where:
- `L1 = 135 mm` (rear arm, shoulder to elbow)
- `L2 = 147 mm` (forearm, elbow to wrist)

**Important:** the computed height is the arm-plane height above the shoulder pivot, **not** the firmware Z coordinate. The firmware Z adds a fixed ~138 mm base offset (the height of the shoulder above the table surface). This is why `02_joint_control.py` shows a predicted Z that is roughly 130–145 mm lower than the actual firmware Z readout.

---

## Official Links

| Resource | Link |
|---------|------|
| Product page | https://www.dobot-robots.com/products/education/magician.html |
| DobotStudio download | https://www.dobot-robots.com/service/download-center.html |
| pydobotplus (PyPI) | https://pypi.org/project/pydobotplus/ |

---

## Learning Resources

The links below point to the full workspace documentation. Those docs describe
the full root tracks in `magician/` and `mg400/`; the intro-week copies in
`Students/00_IntroductionWeek/` keep the same core concepts but omit some
advanced helper options and extra tooling.

| Topic | Resource |
|-------|---------|
| Full 18-script lab walkthrough | `GUIDE.md` in the full course workspace |
| Repo documentation index | `docs/README.md` in the full course workspace |
| Motion modes (MOVJ, MOVL, JUMP) | `docs/motion_modes.md` in the full course workspace |
| Arc and circle references | `docs/circle_drawing_index.md` in the full course workspace |
| Magician hardware and kinematics | `magician/dobot_magician_info.md` and `magician/kinematics_guide.md` |
| Magician vs MG400 overview | `docs/dobot_control_options_comparison.md` and `magician_vs_mg400.md` |
| Denavit-Hartenberg parameters | [Wikipedia: Denavit–Hartenberg parameters](https://en.wikipedia.org/wiki/Denavit%E2%80%93Hartenberg_parameters) |
| Robotics coordinate frames | Any introductory robotics textbook (e.g. Craig, *Introduction to Robotics*) |
