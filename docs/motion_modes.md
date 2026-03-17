# Motion Modes

This workspace uses two different motion APIs:

- Dobot Magician: point-to-point modes from `pydobotplus.MODE_PTP`
- DOBOT MG400: separate motion commands such as `MovJ`, `MovL`, `Arc`, `Circle`, and `MoveJog`

## Magician

These are the modes students most often need:

| Mode | Path | Primary demo |
|---|---|---|
| `MOVJ_XYZ` | Joint-interpolated curved path | [`../magician/03_safe_move_demo.py`](../magician/03_safe_move_demo.py) |
| `MOVL_XYZ` | Straight-line Cartesian path | [`../magician/12_motion_modes.py`](../magician/12_motion_modes.py) |
| `JUMP_XYZ` | Lift, travel, lower | [`../magician/08_pick_and_place.py`](../magician/08_pick_and_place.py) |

Related references:

- [`../magician/12_motion_modes.py`](../magician/12_motion_modes.py): direct side-by-side demo
- [`../magician/08_pick_and_place.py`](../magician/08_pick_and_place.py): practical `JUMP_XYZ` pattern
- [`../magician/utils.py`](../magician/utils.py): `safe_move()` wrapper and shared bounds

## MG400

The MG400 SDK exposes separate commands rather than a shared motion-mode enum.

| Command | Path | Primary demo |
|---|---|---|
| `MovJ` | Joint-interpolated curved path | [`../mg400/11_motion_modes.py`](../mg400/11_motion_modes.py) |
| `MovL` | Straight-line Cartesian path | [`../mg400/11_motion_modes.py`](../mg400/11_motion_modes.py) |
| `Arc` | Arc through a via-point | [`../mg400/09_arc_motion.py`](../mg400/09_arc_motion.py) |
| `Circle` | Firmware circle command | [`../mg400/09_arc_motion.py`](../mg400/09_arc_motion.py) |
| `MoveJog` | Continuous jog motion | [`../mg400/07_keyboard_teleop.py`](../mg400/07_keyboard_teleop.py) |

Related references:

- [`../mg400/11_motion_modes.py`](../mg400/11_motion_modes.py): `MovJ` vs `MovL` comparison
- [`../mg400/09_arc_motion.py`](../mg400/09_arc_motion.py): `Arc`, `Circle`, and sampled circles
- [`../mg400/utils_mg400.py`](../mg400/utils_mg400.py): shared motion helpers and bounds

## Pick-And-Place

Use these scripts as the practical motion-mode references for lab work:

- Magician: [`../magician/08_pick_and_place.py`](../magician/08_pick_and_place.py)
- MG400: [`../mg400/08_pick_and_place.py`](../mg400/08_pick_and_place.py)
- MG400 slider: [`../mg400/slider/03_slider_arm_demo.py`](../mg400/slider/03_slider_arm_demo.py)
