# Dobot Workspace (ME403)

Simple Python control workspace for:
- Dobot Magician (USB serial)
- DOBOT MG400 (TCP/IP)

## Start Here

- Student walkthrough: `GUIDE.md`
- Dependencies: `requirements.txt`
- Script index: `scripts/README.md`

## Repo Layout

- `scripts/` - Dobot Magician runnable scripts (`01` to `18`) and shared helpers
- `mg400/` - MG400 runnable scripts and MG400 utilities
- `basics/` - introductory exercises and reference material
- `Students/` - student-facing starter scripts and resources
- `vendor/` - external SDK trees used by scripts

## Canonical References

- Magician info: `scripts/dobot_magician_info.md`
- Kinematics guide: `scripts/kinematics_guide.md`
- MG400 info: `mg400/MG400_info.md`
- Vendor SDK notes: `vendor/README.md`

## Notes

- Only one process can own the Dobot serial port at a time.
- Keep vendor folder names stable (`vendor/dobot-python`, `vendor/TCP-IP-4Axis-Python`), because scripts auto-discover these paths.
