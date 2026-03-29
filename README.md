# Dobot Workspace (ME403)

Python control workspace for ME403 - Introduction to Robotics (Sabanci University, Spring 2025-26).

Supports two robots:
- **Dobot Magician** (USB-serial, pydobotplus)
- **DOBOT MG400** (Ethernet/TCP-IP, Dobot SDK)

## Start Here

- Full walkthrough for the root script sets: [`GUIDE.md`](./GUIDE.md)
- Student intro subset: [`Students/00_IntroductionWeek/README.md`](./Students/00_IntroductionWeek/README.md)
- Docs index: [`docs/README.md`](./docs/README.md)
- Dependencies: [`requirements.txt`](./requirements.txt)

## Platform Support

- Ubuntu 24 / Linux: native support for all scripts. Dobot Magician additionally needs the `dialout` permission step.
- Windows 10/11: native PowerShell workflow lives in [`windows/README.md`](./windows/README.md).
- Student Week 0 (Magician + MG400): [`Students/00_IntroductionWeek/README.md`](./Students/00_IntroductionWeek/README.md). Week 1 (MG400 advanced): [`Students/01_SecondWeek/README.md`](./Students/01_SecondWeek/README.md).
- Canonical keyboard teleop entrypoints are cross-platform: `magician/07_keyboard_teleop.py` and `mg400/07_keyboard_teleop.py`.

## Repo Layout

| Folder / File | Contents |
|---|---|
| `magician/` | Dobot Magician scripts 01-19 + shared helpers (`utils.py`, `viz.py`) |
| `mg400/` | MG400 scripts 01-17 + shared helpers (`utils_mg400.py`, `viz_mg400.py`) |
| `Students/` | Intro-week subsets: Week 0 (Magician + MG400) and Week 1 (MG400 advanced), plus report materials |
| `docs/` | Reference docs: motion modes, platform differences, robot comparisons, control map |
| `windows/` | Windows-only docs, PowerShell scripts, and lazy-imported helper modules |
| `vendor/` | External SDK trees (auto-discovered by scripts) |
| `GUIDE.md` | Script-by-script walkthrough + TA implementation details |

## Canonical References

- MG400 info: [`mg400/MG400_info.md`](./mg400/MG400_info.md)
- API comparison: [`docs/magician_vs_mg400.md`](./docs/magician_vs_mg400.md)
- Platform differences: [`docs/platform_differences.md`](./docs/platform_differences.md)
- Control stack map: [`docs/control_map.md`](./docs/control_map.md)
- Docs index: [`docs/README.md`](./docs/README.md)
- Student Week 0 (Magician + MG400): [`Students/00_IntroductionWeek/README.md`](./Students/00_IntroductionWeek/README.md)
- Student Week 1 (MG400): [`Students/01_SecondWeek/README.md`](./Students/01_SecondWeek/README.md)

## Notes

- Only one process can own the Dobot serial port at a time.
- Keep vendor folder names stable (`vendor/dobot-python`, `vendor/TCP-IP-4Axis-Python`) - scripts auto-discover these paths.
- MG400 network: set PC Ethernet to static IP `192.168.2.100 / 255.255.255.0`. Robot IPs: 192.168.2.7 (1), .10 (2), .9 (3), .6 (4).
- Optional overrides: `DOBOT_PORT` for an explicit Magician serial port, `DOBOT_MG400_IP` for a custom MG400 target IP.
- For native Windows setup and PowerShell commands, use [`windows/README.md`](./windows/README.md).
