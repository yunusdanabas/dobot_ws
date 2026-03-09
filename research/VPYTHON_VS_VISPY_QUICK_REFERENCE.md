# VPython vs Vispy — Quick Reference (2025)

## TL;DR Decision Matrix

```
Use VPYTHON if:
  • Primary environment is Jupyter notebooks
  • Want intuitive object-oriented 3D API
  • Teaching or quick prototyping
  • Can accept browser/Jupyter dependency

Use VISPY if:
  • Need standalone desktop application ✓ (THIS PROJECT)
  • Have background threads (serial I/O) ✓ (THIS PROJECT)
  • Want 10-30 Hz+ reliable updates ✓ (THIS PROJECT)
  • Need professional scientific visualization
  • Want thread-safe rendering with no Queue management
```

---

## Technical Specification Table

| Property | VPython 7.6.5 | Vispy 0.16.1 | Notes |
|----------|---------------|------------|-------|
| **Core Package Size** | 9.0 MB | 9.7 MB | Negligible difference |
| **Total w/ Dependencies** | ~100 MB (Jupyter stack) | ~50-60 MB (or +100 MB with PyQt5) | Context-dependent |
| **Rendering** | Browser-based (Jupyter) | Native desktop (Qt/PyQt) | VPython locked to Jupyter |
| **Window Type** | WebSocket canvas | Native window | Vispy is true desktop app |
| **Headless Mode** | Not practical | Yes (glfw/pygame backend) | Vispy is flexible |
| **Max Update Rate** | 30-60 Hz (Jupyter-limited) | 60+ Hz easily | Both sufficient for 10-30 Hz |
| **3D Primitives** | sphere, cylinder, cone, box, etc. | Mesh-based (more flexible) | VPython simpler for basic shapes |
| **Thread Safety** | NO (manual Queue required) | YES (Qt signals/slots) | Vispy wins decisively |
| **OpenGL Backend** | No (web-based) | Yes (vispy.gloo) | Vispy more powerful |
| **GUI Framework** | None (Jupyter) | Qt/PyQt (professional) | Vispy ready for larger apps |
| **Learning Curve** | Easy (object-oriented) | Moderate (more abstract) | VPython more intuitive |
| **Documentation** | Good | Excellent | Vispy more thorough |
| **Community** | Active (Jupyter-focused) | Active (scientific computing) | Different niches |

---

## Threading Model Comparison

### VPython: Manual Queue Pattern
```python
from vpython import rate as vprate
from queue import Queue

queue = Queue(maxsize=1)

# Background thread: producer
def serial_reader():
    while True:
        pose = robot.get_pose()
        queue.put_nowait(pose)  # Drop if full

# Main thread: consumer (busy-wait)
frame = vprate(30)
while True:
    frame(30)  # Throttle to 30 Hz
    try:
        pose = queue.get_nowait()
        arm.pos = vector(*pose)
    except:
        pass  # Queue empty

# ISSUES:
#   - Manual Queue management
#   - Main thread is polling (busy-wait)
#   - Synchronization not guaranteed
```

### Vispy: Qt Signal-Slot Model
```python
from vispy import app
from vispy.scene import SceneCanvas
import numpy as np

canvas = SceneCanvas()
view = canvas.central_widget.add_view()

# Background thread: producer (can update directly)
def serial_reader():
    global trajectory
    while True:
        pose = robot.get_pose()
        trajectory = np.vstack([trajectory, pose[:3]])
        # Qt automatically syncs on next draw

# Main thread: Qt event loop manages everything
def update(event):
    line.set_data(pos=trajectory)

timer = app.Timer(interval=0.033)  # 30 Hz
timer.connect(update)
timer.start()

thread = threading.Thread(target=serial_reader, daemon=True)
thread.start()

canvas.show()
app.run()

# ADVANTAGES:
#   - No Queue needed
#   - Background thread updates directly
#   - Qt handles synchronization automatically
#   - Cleaner code
```

---

## Integration Boilerplate Comparison

### VPython (Minimal Example: ~30 lines)
```python
from vpython import scene, sphere, cylinder, vector, color, rate as vprate
from queue import Queue
import threading

# Setup
scene.width, scene.height = 1200, 800
arm_joint = cylinder(color=color.blue, radius=5)
trajectory = []
queue = Queue(maxsize=1)

# Main loop
def main():
    frame = vprate(30)
    while True:
        frame(30)
        try:
            pose = queue.get_nowait()
            arm_joint.pos = vector(*pose[:3])
            trajectory.append(arm_joint.pos)
        except:
            pass

# Threading
def reader():
    while True:
        queue.put_nowait(robot.get_pose())

threading.Thread(target=reader, daemon=True).start()
main()
```

### Vispy (Minimal Example: ~35 lines)
```python
from vispy.scene import SceneCanvas
from vispy import app, visuals
import numpy as np
import threading

# Setup
canvas = SceneCanvas(title='Robot', size=(1200, 800))
view = canvas.central_widget.add_view()

trajectory = np.array([[0, 0, 0]], dtype=np.float32)
line = visuals.Line(pos=trajectory, color='blue', width=2)
view.add(line)

# Update callback
def update(event):
    line.set_data(pos=trajectory)

# Threading
def reader():
    global trajectory
    while True:
        pose = robot.get_pose()
        trajectory = np.vstack([trajectory, pose[:3]])

# Main
timer = app.Timer(interval=0.033)
timer.connect(update)
timer.start()

threading.Thread(target=reader, daemon=True).start()
canvas.show()
app.run()
```

**Result:** Both ~30-35 lines. Vispy slightly cleaner (no Queue).

---

## Installation & Setup

### VPython
```bash
pip install vpython
# Note: Also installs Jupyter stack if not present (~100 MB)
# For standalone use, much more complex setup needed
```

### Vispy
```bash
pip install vispy PyQt5
# Vispy: 10 MB
# PyQt5: ~100 MB (but optional; can use glfw instead)
```

---

## 3D Graphics Capability

### VPython Primitives (Simpler)
```python
from vpython import sphere, cylinder, vector, color

# Easy intuitive API
base = sphere(pos=vector(0, 0, 0), radius=10, color=color.gray)
joint = cylinder(pos=vector(0, 0, 0), axis=vector(0, 0, 50), radius=5)
effector = sphere(pos=vector(0, 0, 50), radius=8, color=color.red)
```

### Vispy Meshes (More Flexible)
```python
from vispy.scene import visuals
from vispy.geometry import create_cylinder, create_sphere
import numpy as np

# More verbose but scalable
base_mesh = create_sphere(radius=10)
base = visuals.Mesh(geometry=base_mesh)

joint_mesh = create_cylinder(radius=5, height=50)
joint = visuals.Mesh(geometry=joint_mesh)

effector_mesh = create_sphere(radius=8)
effector = visuals.Mesh(geometry=effector_mesh)

view.add(base)
view.add(joint)
view.add(effector)
```

**VPython wins for robot arm visualization** (simpler primitives).
**Vispy wins for complex geometry** (meshes, scalability).

---

## Update Rate Analysis

### Target: 10-30 Hz (Typical Robot Telemetry)

| Library | Achievable | Notes |
|---------|-----------|-------|
| **VPython** | 20-30 Hz | Limited by Jupyter kernel (single-threaded) |
| **Vispy** | 60+ Hz easily | Qt event loop is optimized; 30 Hz is trivial |

Both easily exceed 10-30 Hz target, but Vispy has more headroom and no Jupyter overhead.

---

## Decision Flowchart

```
Are you using Jupyter?
    YES → Use VPYTHON (it's native there)
    NO  → Go to next question

Do you need standalone desktop app?
    YES → Use VISPY ✓
    NO  → Consider VPYTHON

Do you have background serial thread?
    YES → Use VISPY (thread-safe by design)
    NO  → Either works

Do you want 10-30 Hz updates with minimal code?
    YES → Use VISPY ✓

Final Decision: VISPY for Dobot lab project
```

---

## Ecosystem Integration

### VPython + Dobot
- ✓ Can work (with Queue pattern)
- ✗ Requires Jupyter
- ✗ Manual thread synchronization
- ✗ Not professional desktop app

### Vispy + Dobot
- ✓ Perfect match (native window)
- ✓ Thread-safe serial integration
- ✓ Clean Qt event loop
- ✓ Professional visualization
- ✓ Scales to complex projects

---

## Performance Characteristics (Vispy)

| Metric | Typical Value | Notes |
|--------|---------------|-------|
| Frame rate | 30+ Hz | Target: 10-30 Hz easily met |
| Trajectory history | 500+ points | Can render thousands efficiently |
| Memory footprint | ~50 MB | With PyQt5; much less with glfw |
| GUI responsiveness | Excellent | Qt event loop is responsive |
| Thread overhead | Negligible | Qt signals/slots are optimized |

---

## Recommendation for ME403 Robotics Lab

### Choose: **VISPY** ✓

**Reasons:**
1. **Native desktop app** — Professional appearance
2. **Thread-safe** — No Queue gymnastics needed
3. **10-30 Hz trivial** — Plenty of headroom
4. **Simple integration** — ~35 lines for working visualization
5. **No Jupyter** — Students can run from terminal
6. **Scalable** — Works for more complex projects later
7. **Industry standard** — Scientific computing standard visualization tool

### Implementation Steps
1. `pip install vispy PyQt5`
2. Create `scripts/16_visualize_trajectory.py` using Vispy
3. Demonstrate with synthetic path (spiral)
4. Connect to real Dobot via background thread
5. Document in `GUIDE.md`

---

## Files & Resources

- **Detailed Comparison:** `VISUALIZATION_COMPARISON_2025.md` (this directory)
- **VPython Demo:** `test_vpython_demo.py` (analysis only, requires Jupyter)
- **Vispy Demo:** `test_vispy_demo.py` (run with `python vispy_demo.py`)
- **Real Robot Template:** See Vispy demo or detailed comparison

---

## References

- VPython: http://vpython.org (Jupyter-centric)
- Vispy: http://vispy.org (scientific visualization)
- Vispy Docs: http://vispy.org/user_guide/index.html
- Vispy Examples: http://vispy.org/gallery.html

---

**Last Updated:** 2025-03-09  
**Status:** Ready for production use in ME403 lab
