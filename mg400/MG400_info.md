# DOBOT MG400

## Network Configuration (Lab Setup)

| Robot | IP Address |
|-------|------------|
| 1     | 192.168.2.7  |
| 2     | 192.168.2.10 |
| 3     | 192.168.2.9  |
| 4     | 192.168.2.6  |

**PC static IP**: `192.168.2.100`, netmask `255.255.255.0`

Verify connectivity: `ping 192.168.2.7`

The MG400 script entrypoints are the same on Ubuntu and native Windows. For the
native Windows setup, direct-Ethernet steps, and PowerShell commands, use
[`../windows/README.md`](../windows/README.md).
For the broader documentation map, use [`../docs/README.md`](../docs/README.md).

### Windows Direct Cable Setup

From the repo root:

```powershell
.\windows\Set-MG400StaticIp.ps1
.\windows\Set-MG400StaticIp.ps1 -InterfaceAlias "Ethernet" -Apply
python mg400\01_connect_test.py
```

If your robot is not using the lab-default IP, either pass `--ip <addr>` or set:

```powershell
$env:DOBOT_MG400_IP = "192.168.2.7"
```



## Scripts (`mg400/01–17`)

| Script | Description |
|--------|-------------|
| `01_connect_test.py` | TCP ping + firmware version + pose (no enable) |
| `02_first_connection.py` | Enable, query pose/angles, move home, disable |
| `03_safe_move_demo.py` | safe_move() with clamping warning demo |
| `04_speed_control.py` | SpeedFactor/SpeedJ/SpeedL/AccJ/AccL at three levels |
| `05_end_effectors.py` | ToolDO suction/gripper + base DO/DI |
| `06_joint_angles.py` | GetAngle, JointMovJ, FK/IK queries |
| `07_keyboard_teleop.py` | MoveJog-based terminal jog (hold-to-move) |
| `08_pick_and_place.py` | Arch/lift pick-and-place with suction |
| `09_arc_motion.py` | Arc(), Circle(), sampled circle with viz |
| `10_relative_moves.py` | RelMovJ, RelMovL, relative pick-and-place |
| `11_motion_modes.py` | MovJ vs MovL vs Arc path comparison + viz |
| `12_feedback_monitor.py` | Live pose from port 30004 + viz (no motion) |
| `13_multi_robot_demo.py` | Parallel XY-square demo on up to 4 robots simultaneously |
| `14_joint_control.py` | Interactive J1–J4 REPL with FK display, clamping, optional CSV log |
| `15_multi_joint_control.py` | Broadcast joint commands to multiple robots simultaneously |
| `16_relative_joint_control.py` | Body-frame FK exercise: enter relative joint angles, observe conversion chain and FK prediction |
| `17_joint_control_gui.py` | PyQt5 GUI: Absolute Joint / Relative Joint / XYZ Cartesian tabs, +/− step buttons, live pose readout, speed slider, Home + ESTOP, RobotViz integration |

All scripts accept `--robot N` (N=1–4) or `--ip <addr>`.
`07_keyboard_teleop.py` is the cross-platform terminal teleop entrypoint; no
separate Windows teleop script is required.

### Connectivity Diagnostics

- `00_connectivity_check.py` prints a detailed per-robot network and dashboard report
- `00_connectivity_gui.py` provides the same checks in a GUI for lab troubleshooting
- `00_raw_dashboard_probe.py` is the low-level raw socket probe for vendor-response debugging

## Sliding Rail — Robot 2 (DT-AC-HDSR-001)

Robot 2 (IP `192.168.2.10`) has a **DOBOT MG400 Sliding Rail Kit** attached.
Hardware specs: 800 mm travel, ±0.05 mm repeat accuracy, 800 mm/s max speed.
Full hardware spec: see `dobot_slider_info.md` (repo root).

### One-time DobotStudio Pro Setup (required before any slider script)

1. Open DobotStudio Pro → **Configure** → **External Axis**
2. Set **Type** to **Linear** and **Unit** to **mm**
3. Enable the external axis and click **Save**
4. Reboot the robot controller
5. Verify: `ping 192.168.2.10` and run `slider/01_slider_connect_test.py`

### Slider Scripts (`mg400/slider/01–04`)

| Script | Description |
|--------|-------------|
| `slider/01_slider_connect_test.py` | TCP test; no enable, no motion; shows position = UNKNOWN |
| `slider/02_slider_basic.py` | Home arm + slider, traverse [0,200,400,600,800] mm |
| `slider/03_slider_arm_demo.py` | Coordinated arm + rail via `SyncAll()` (5 waypoints) |
| `slider/04_slider_teleop.py` | Hybrid keyboard teleop: `MoveJog` (arm) + incremental `MovJExt` (slider) |

All slider scripts default to `--robot 2`. Pass `--robot N` or `--ip <addr>` to override.
`slider/04_slider_teleop.py` uses the same keybindings on Ubuntu and Windows.

### Key Slider API

```python
from mg400.slider.utils_slider import (
    go_home_slider,    # MovJExt(0) + Sync() — establishes position reference
    safe_move_ext,     # clamp + MovJExt; optional sync=True
    jog_slider,        # relative step from current position
    get_slider_pos,    # returns last commanded mm, or None if not homed
    print_slider_status,
)

# Pattern: home → move → SyncAll for coordinated arm+rail
go_home_slider(move_api)                       # reference at 0 mm
safe_move_ext(move_api, 400.0)                 # queue slider (no Sync yet)
safe_move(move_api, 300, 0, 50, 0)             # queue arm   (no Sync yet)
move_api.SyncAll()                             # wait for BOTH queues
```

**Notes:**
- `move_api.SyncAll()` waits for the arm queue **and** the slider queue.
- `move_api.Sync()` waits for the arm queue only.
- There is **no** `GetPoseExt` — slider position is tracked in software.
- `MovJExt` is in `vendor/TCP-IP-4Axis-Python/dobot_api.py` (line 770).

## Joint Ranges (per DT-MG400-4R075-01 hardware guide V1.1, Table 2.1)

| Joint | Range | Notes |
|-------|-------|-------|
| J1 | ±160° | base rotation |
| J2 | -25° ~ +85° | shoulder elevation from horizontal |
| J3 | -25° ~ +105° | firmware absolute = j2 + j3_rel; factory home = 60° |
| J4 | ±180° | wrist rotation |

Factory/home joint angles: J1=0°, J2=0°, J3=60°, J4=0° (§2.8 of hardware guide)

## Product Information

- **Model:** DT-MG400-4R075-01
- **Equipment Type:** Industrial Robot
- **Rated Power:** 150W
- **Rated Current:** 3.2A
- **Rated Voltage:** DC 48V
- **Rated Load:** 500g (Max. 750g)
- **Weight:** 8kg
- **Max. Reach:** 440mm
- **Short-Circuit Current:** 50A

## Manufacturing Information

- **Made in:** China
- **Production Date:** 2022.06
- **Barcode:** 6970632060045
- **Code:** DT1802-4240-2162

## Manufacturer

- **Company:** Shenzhen Yuejiang Technology Co., Ltd. | China
- **Website:** www.dobot.cc

## Address

**English:**  
Room1003, Building 2, Chongwen Park, Nanshan Park, No.3370, Liuxian Blvd,  
Fuguang Community, Taoyuan Street, Nanshan District, Shenzhen

**Chinese:**  
深圳市南山区桃源街道福光社区留仙大道3370号南山智园崇文园区2号楼1003
