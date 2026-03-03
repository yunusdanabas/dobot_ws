# 01: Python Libraries for Dobot Magician (ME403)

This workspace intentionally uses a three-track strategy so students can start simple and still access low-level queue control when needed.

## Track A — `pydobotplus` (default)

- **Install:** `pip install pydobotplus`
- **Why default:** straightforward API for Labs 1-4 (`move_to`, `suck`, `grip`), plus explicit `close()`.
- **Pose shape:** `get_pose()` returns a structured `Pose(position, joints)` object.

## Track B — `dobot-python` (advanced, source checkout)

- **Source:** <https://github.com/AlexGustafsson/dobot-python>
- **Setup:** clone repo and import from `lib.interface` or `lib.dobot` via `sys.path`.
- **Why advanced:** direct access to protocol-level queue controls (`set_point_to_point_command`, `get_current_queue_index`).
- **Important:** this project is not distributed on PyPI as `dobot-python`.

## Track C — `pydobot` (legacy reference)

- **Install:** `pip install pydobot`
- **Why keep it:** historical API reference and compatibility fallback.
- **Cleanup:** use `bot.close()`.

## ME403 Recommendation

1. Start with **Track A** for first contact, safe motion, and end-effector labs.
2. Use **Track B** only when trajectory buffering/queue introspection is the learning target.
3. Keep **Track C** for comparison and troubleshooting with older examples.
