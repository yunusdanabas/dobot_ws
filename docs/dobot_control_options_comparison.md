# Dobot Control Options Comparison

This page is a compact map of the control surfaces available in this workspace.

## Robots

| Robot | Transport | Main workspace | Primary reference |
|---|---|---|---|
| Dobot Magician | USB serial | [`magician/`](./magician/) | [`magician/dobot_magician_info.md`](./magician/dobot_magician_info.md) |
| DOBOT MG400 | Ethernet / TCP-IP | [`mg400/`](./mg400/) | [`mg400/MG400_info.md`](./mg400/MG400_info.md) |

## Magician Software Tracks

| Track | Library | Best fit | Reference |
|---|---|---|---|
| A | `pydobotplus` | default teaching scripts | [`GUIDE.md`](./GUIDE.md) |
| B | `dobot-python` | queue-heavy advanced examples | [`magician/10_circle_queue.py`](./magician/10_circle_queue.py) |
| C | `pydobot` | legacy compatibility only | [`GUIDE.md`](./GUIDE.md) |

## MG400 Software Stack

| Component | Purpose | Reference |
|---|---|---|
| `vendor/TCP-IP-4Axis-Python/dobot_api.py` | official SDK transport layer | [`mg400/utils_mg400.py`](./mg400/utils_mg400.py) |
| `mg400/utils_mg400.py` | shared safety, parsing, connection helpers | [`mg400/utils_mg400.py`](./mg400/utils_mg400.py) |
| `mg400/slider/utils_slider.py` | slider-specific wrapper layer | [`mg400/slider/utils_slider.py`](./mg400/slider/utils_slider.py) |

## Use These Docs

- Workspace overview: [`README.md`](./README.md)
- Full walkthrough: [`GUIDE.md`](./GUIDE.md)
- Docs index: [`docs/README.md`](./docs/README.md)
- Magician vs MG400 code comparison: [`magician_vs_mg400.md`](./magician_vs_mg400.md)
- Windows setup: [`windows/README.md`](./windows/README.md)
- Student wrapper entrypoints: [`Students/00_IntroductionWeek/README.md`](./Students/00_IntroductionWeek/README.md)
