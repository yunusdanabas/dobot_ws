# Product Specifications: MG400 Sliding Rail Kit

## Device Information

* **Brand:** DOBOT
* **Product Name:** MG400 滑轨套件 (MG400 Sliding Rail Kit)
* **Model:** DT-AC-HDSR-001
* **Serial Number:** `DTAC-HDSR-2223-0018`
* **Barcode:** 6 970632 060182
* **Origin:** Made in China

## Technical Specifications

| Parameter | Specification |
| --- | --- |
| **Payload** | 20 kg |
| **Effective Travel Distance** | 800 mm |
| **Repeat Positioning Accuracy** | $\pm 0.05$ mm |
| **Rated Power** | 200 W |
| **Weight** | 15 kg |
| **Maximum Speed** | 800 mm/s |
| **Dimension (L * W * H)** | 1150 * 230 * 90 mm |

---

## Manufacturer Details

* **Company:** Shenzhen Yuejiang Technology Co., Ltd. | China
* **Website:** [www.dobot.cc](http://www.dobot.cc)
* **Address:** Room 1003, Building 2, Chongwen Park, Nanshan iPark, No. 3370, Liuxian Blvd, Fuguang Community, Taoyuan Street, Nanshan District, Shenzhen

---

## Python API Quick Reference

### Import

```python
# Run from mg400/slider/
from utils_slider import (
    connect, close_all, check_errors,
    go_home, go_home_slider,
    safe_move, safe_move_ext,
    jog_slider, get_slider_pos, print_slider_status,
    SLIDER_IP, SLIDER_BOUNDS, SLIDER_HOME, SPEED_EXT,
    SLIDER_STEP_FAST, SLIDER_STEP_SLOW,
)
```

### Basic Pattern

```python
dashboard, move_api, feed = connect(SLIDER_IP)
try:
    dashboard.EnableRobot()
    go_home(move_api)           # arm to READY_POSE
    go_home_slider(move_api)    # slider to 0 mm — establishes position reference

    # Move slider alone — use Sync() (arm queue only is fine)
    safe_move_ext(move_api, 400.0, sync=True)

    # Coordinated arm + slider — queue both, then SyncAll()
    safe_move_ext(move_api, 600.0)        # queues slider (no Sync)
    safe_move(move_api, 250, 0, 60, 0)   # queues arm   (no Sync)
    move_api.SyncAll()                    # wait for BOTH queues

    print_slider_status()
finally:
    dashboard.DisableRobot()
    close_all(dashboard, move_api, feed)
```

### API Notes

| Command | Effect |
|---------|--------|
| `move_api.MovJExt(pos_mm, "SpeedE=50", "AccE=50")` | Move slider to absolute position |
| `move_api.Sync()` | Wait for **arm queue** only |
| `move_api.SyncAll()` | Wait for **arm queue AND slider queue** |
| `get_slider_pos()` | Returns last commanded mm, or `None` if not homed |

**Key constraints:**
- **No `GetPoseExt`** — slider position is tracked in software (last commanded value).
- **No `MoveJog` for E-axis** — use incremental `MovJExt` for jogging.
- `go_home_slider()` must be called after enabling before any `jog_slider()` call.

### DobotStudio Pro Setup (one-time, required)

1. Open DobotStudio Pro → **Configure** → **External Axis**
2. Set **Type** = **Linear**, **Unit** = **mm**
3. Enable the external axis and click **Save**
4. Reboot the robot controller
5. Verify: `ping 192.168.2.10` → run `mg400/slider/01_slider_connect_test.py`