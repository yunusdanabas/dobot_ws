# Dobot MG400 Device Information Report

## 1. Hardware Specifications (Nameplate)

| Attribute | Details |
| --- | --- |
| **Model** | DT-MG400-4R075-01 |
| **Equipment Type** | Industrial Robot |
| **Rated Power** | 150W |
| **Rated Current** | 3.2A |
| **Rated Voltage** | DC 48V |
| **Rated Load** | 500g (Max. 750g) |
| **Weight** | 8kg |
| **Max. Reach** | 440mm |
| **Short-Circuit Current** | 50A |
| **Production Date** | 2022.06 |
| **Manufacturer** | Shenzhen Yuejiang Technology Co., Ltd. |

---

## 2. Software & Firmware Status

* **Device Name:** 4
* **Device Serial Number (SN):** DT1802-4240-1828
* **Software Version:** DobotStudio Pro 2.7.1-x86_64-stable.202305291805
* **Controller Firmware:** 1.5.4.0-stable-438e776c-2109181846
* **Servo Version:** 3.0.6.0
* **Configuration File:** 3.4.18
* **Hardware Versions:**
* **Controller:** 3101010275
* **Servo:** 3101010209
* **Power Board:** 3101010250



---

## 3. Communication Settings

### IP Configuration (Manual)

* **IP Address:** `192.168.2.6`
* **Netmask:** `255.255.255.0`
* **Gateway:** `192.168.2.6`

> **Note:** Only the IP address of LAN2 can be modified to connect external devices.

### WiFi Settings

* **SSID:** MG400444
* **Password:** 1234567890

---

## 4. Initial Position & Motion

* **Initial Pose (X, Y, Z, R):** `350.000, 0.000, 0.000, 0.000`
* **User/Tool Index:** User 0 / Tool 0
* **TrueMotion:** Disabled (Off)

---

## 5. Known Issues & Recovery

### Z=0 Initial Pose → ERROR Mode

**Problem:** The initial pose Z=0.000mm means the robot was left at (or driven to) the
mounting surface. `SAFE_BOUNDS` requires Z ≥ 5mm. A Z=0 position triggers a joint-limit
or collision alarm, placing the robot in **ERROR mode (mode=9)**. In ERROR mode the robot
refuses all motion commands, which appears as a "connection problem."

**Network status:** TCP connection to 192.168.2.6 is fine. The issue is at the firmware
level, not the network level.

> **IP update note:** Robot 4 was previously at 192.168.2.8 and appeared to be in firmware
> echo mode (API process not running). The issue was resolved by connecting via DobotStudio Pro
> and performing a firmware re-initialization. LAN2 was reconfigured to the new static IP
> 192.168.2.6 (netmask 255.255.255.0) at the same time.

### Recovery Procedure

1. **Run the connectivity checker** (auto-attempts ClearError):
   ```bash
   cd /home/yunusdanabas/dobot_ws/mg400
   python 00_connectivity_check.py --robot 4
   ```

2. **Or use the GUI** — open `00_connectivity_gui.py` and click **Fix** on the Robot 4 row.

3. **After errors clear**, the robot enters DISABLED (mode=4). Enable it:
   ```python
   dashboard.EnableRobot()
   ```

4. **First move must go to READY_POSE** (Z=50mm, safe above the surface):
   ```python
   move_api.MovJ(300, 0, 50, 0)
   move_api.Sync()
   ```
   Never send Z=0 as a first move after recovery.

### Mode Reference

| Mode | Meaning | Action needed |
|------|---------|---------------|
| 9 | ERROR | Run `check_errors(dashboard)` or click Fix |
| 4 | DISABLED | Call `EnableRobot()` |
| 5 | ENABLED (idle) | Ready for motion commands |
| 7 | RUNNING | Motion in progress |

### Persistent ERROR

If `ClearError()` does not resolve mode=9 after 2–3 attempts, **power-cycle the robot**
(hold power button 3 s, wait 30 s for reboot, then reconnect).