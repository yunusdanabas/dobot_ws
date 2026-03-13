# Dobot Workspace (ME403)

Python control workspace for ME403 — Introduction to Robotics (Sabancı University, Spring 2025-26).

Supports two robots:
- **Dobot Magician** (USB-serial, pydobotplus)
- **DOBOT MG400** (Ethernet/TCP-IP, Dobot SDK)

## Start Here

- Student walkthrough: `GUIDE.md`
- Student intro materials: `Students/00_IntroductionWeek/`
- Dependencies: `requirements.txt`

## Repo Layout

| Folder / File | Contents |
|---|---|
| `magician/` | Dobot Magician scripts 01–19 + shared helpers (`utils.py`, `viz.py`) |
| `mg400/` | MG400 scripts 01–16 + shared helpers (`utils_mg400.py`, `viz_mg400.py`) |
| `Students/` | Student-facing starter scripts and lab handout |
| `vendor/` | External SDK trees (auto-discovered by scripts) |
| `GUIDE.md` | Script-by-script walkthrough + TA implementation details |
| `magician_vs_mg400.md` | Side-by-side code comparison: Magician vs MG400 |

## Canonical References

- Magician info: `magician/dobot_magician_info.md`
- Kinematics guide: `magician/kinematics_guide.md`
- MG400 info: `mg400/MG400_info.md`
- Comparison table: `dobot_control_options_comparison.md`
- Vendor SDK notes: `vendor/README.md`

## Notes

- Only one process can own the Dobot serial port at a time.
- Keep vendor folder names stable (`vendor/dobot-python`, `vendor/TCP-IP-4Axis-Python`) — scripts auto-discover these paths.
- MG400 network: set PC Ethernet to static IP `192.168.2.100 / 255.255.255.0`. Robot IPs: 192.168.2.9 (1), .10 (2), .7 (3), .8 (4).
