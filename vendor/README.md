# Vendor SDK Layout

This folder stores external SDK source trees used by scripts in this workspace.

## Expected directories

- `dobot-python/` - Track B dependency for `scripts/10_circle_queue.py`
- `TCP-IP-4Axis-Python/` - MG400 SDK used by `mg400/utils_mg400.py`

## Policy

- Keep these folder names stable (scripts use path-based auto-discovery).
- Keep SDK source files available in the repo workspace.
- Treat nested checkout metadata as local noise:
  - `vendor/**/.git/`
  - `vendor/**/__pycache__/`

## Notes

- If you update vendor SDK content from upstream, keep changes limited to vendor folders.
- Do not rename or relocate vendor roots unless all path references in scripts and docs are updated together.
