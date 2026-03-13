# DOBOT MG400

## Network Configuration (Lab Setup)

| Robot | IP Address |
|-------|------------|
| 1     | 192.168.2.9  |
| 2     | 192.168.2.10 |
| 3     | 192.168.2.7  |
| 4     | 192.168.2.8  |

**PC static IP**: `192.168.2.100`, netmask `255.255.255.0`

Verify connectivity: `ping 192.168.2.9`



## Scripts (`mg400/01–15`)

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

All scripts accept `--robot N` (N=1–4) or `--ip <addr>`.

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