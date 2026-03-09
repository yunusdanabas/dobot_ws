# VPython vs Vispy for Real-Time Robot Arm Visualization (2025)

## Executive Summary

| Criterion | VPython | Vispy | Winner |
|-----------|---------|-------|--------|
| **Install Size** | 9 MB | 10 MB | Tie (negligible difference) |
| **Native Window** | NO (Jupyter/browser default) | YES (true desktop app) | **Vispy** |
| **Update Rate (10-30 Hz)** | Capable but Jupyter-limited | Excellent (60+ Hz possible) | **Vispy** |
| **3D Support** | Excellent (primitives) | Good (meshes + advanced) | VPython (for arm) |
| **Threading Model** | NOT thread-safe | Thread-safe (Qt signals) | **Vispy** |
| **Integration Boilerplate** | ~30 lines | ~35 lines | Tie (similar) |
| **Learning Curve** | Easy (intuitive objects) | Moderate (more abstract) | VPython |
| **Production Ready** | Good (Jupyter-focused) | **Excellent** (desktop-focused) | **Vispy** |

---

## Detailed Evaluation

### 1. Install Size & Dependencies

#### VPython
```
Direct install:     9.0 MB
Dependencies:       autobahn, ipykernel, jupyter, jupyter-server-proxy, jupyterlab-vpython, numpy
Total footprint:    ~100 MB (with Jupyter stack)
Installation time:  ~30 seconds
```

**Key insight:** VPython is designed for Jupyter environments. If Jupyter is not already installed, you're adding the entire Jupyter stack (100+ MB).

#### Vispy
```
Direct install:     9.7 MB
Core dependencies:  numpy, freetype-py, kiwisolver, hsluv (all small)
Optional backends:  PyQt5 (~100 MB), PyOpenGL, glfw, pygame
Installation time:  ~20 seconds
```

**Key insight:** Vispy itself is small. Additional size depends on which backend you choose. PyQt5 is heavyweight but provides professional GUI features.

**Winner:** **TIE** — Both are similar in raw package size. Context matters: VPython + Jupyter is ~100 MB; Vispy + PyQt5 is also ~100 MB.

---

### 2. Native Window vs Browser

#### VPython (2025)
- **Default behavior:** Renders in Jupyter notebook/lab (requires browser or Jupyter client)
- **Native window:** NOT available by default
  - Requires GlowScript Web VPython (separate library, limited)
  - OR custom Jupyter server setup with websocket tunneling
  - OR third-party wrapper (not official)
- **Issue:** Designed around Jupyter kernel assumption. Running standalone requires non-standard setup.

```python
# VPython (Jupyter-centric)
from vpython import scene, sphere
s = sphere()  # Renders in Jupyter browser
```

#### Vispy (2025)
- **Default behavior:** Native window (true desktop application)
- **Backend:** Qt/PyQt (professional, stable, feature-rich)
- **Window:** Standalone, no Jupyter required
- **Headless support:** Can use glfw or pygame backend if needed

```python
# Vispy (native desktop)
from vispy.scene import SceneCanvas
from vispy import app
canvas = SceneCanvas(title='Robot Arm', size=(1200, 800))
# Native window opens immediately
app.run()
```

**Winner:** **Vispy** — True native window support out-of-the-box. VPython requires Jupyter infrastructure.

---

### 3. Update Rate (Target: 10-30 Hz)

#### VPython
- **Mechanism:** `rate()` function for frame limiting
- **Typical achievable:** 20-30 Hz in Jupyter (Jupyter kernel overhead limits higher rates)
- **Limitation:** Notebook kernel is single-threaded; if kernel is busy, frame rate drops
- **Best practice:** Use Queue with background thread, poll in `rate()` loop

```python
from vpython import rate as vprate
frame = vprate(30)  # Target 30 Hz
while True:
    frame(30)  # ~33 ms per frame
    # Update visuals
```

#### Vispy
- **Mechanism:** `app.Timer(interval, callback)` — event-driven
- **Typical achievable:** 60+ Hz easily; 10-30 Hz is trivial
- **Advantage:** Qt event loop is highly optimized, decoupled from drawing
- **Clean pattern:** Timer callback is always called at requested interval

```python
from vispy import app
timer = app.Timer(interval=0.033)  # ~30 Hz
def update(event):
    # Update visuals (always called every ~33 ms)
    pass
timer.connect(update)
timer.start()
app.run()
```

**Winner:** **Vispy** — More reliable, higher max rate, cleaner event model. VPython is Jupyter-limited.

---

### 4. 3D Graphics Support

#### VPython
- **Primitives:** sphere, cylinder, box, cone, pyramid, ring, arrow
- **Rendering:** Immediate-mode (conceptually simpler)
- **Best use:** Quick visualization, educational demos
- **Drawback:** Fewer advanced features (no mesh manipulation, limited texturing)

```python
from vpython import sphere, cylinder, vector, color
arm_joint = cylinder(
    pos=vector(0, 0, 0),
    axis=vector(0, 0, 10),
    radius=0.5,
    color=color.blue
)
end_effector = sphere(pos=vector(0, 0, 10), radius=1, color=color.red)
```

**Pros:** Very intuitive for robot arm visualization
**Cons:** Primitives only; no advanced geometry

#### Vispy
- **Primitives:** Line, Scatter, Mesh, Volume, Isosurface
- **Geometry:** Can load/create arbitrary meshes (triangles)
- **Rendering:** GPU-accelerated (vispy.gloo abstraction)
- **Best use:** Professional, scalable visualization

```python
from vispy.scene import SceneCanvas, visuals
import numpy as np

canvas = SceneCanvas(title='Robot Arm')
view = canvas.central_widget.add_view()

# Cylinders: Use mesh geometry
from vispy.geometry import create_cylinder
cylinder_mesh = create_cylinder(radius=0.5, height=10)
arm_visual = visuals.Mesh(geometry=cylinder_mesh)
view.add(arm_visual)

# Sphere: Use mesh geometry
from vispy.geometry import create_sphere
sphere_mesh = create_sphere(radius=1)
effector_visual = visuals.Mesh(geometry=sphere_mesh)
view.add(effector_visual)

# Trajectory: Line
trajectory_line = visuals.Line(pos=np.array([[0, 0, 0]]))
view.add(trajectory_line)
```

**Pros:** Professional mesh support, GPU acceleration, scalable
**Cons:** More verbose for simple geometries

**Winner:** **VPython** (for this specific use case) — Simpler to draw a robot arm with primitives. Vispy wins for complex geometries.

---

### 5. Threading Model & Serial Integration

This is **critical** for robot arm control (serial I/O happens in background thread).

#### VPython
- **Thread-safety:** NOT thread-safe by design (Jupyter kernel is single-threaded)
- **Pattern:** Background thread → Queue → Main thread polling
- **Complexity:** Moderate (must manage Queue, use `vprate()` loop)

```python
from vpython import scene, sphere, vector, rate as vprate
from queue import Queue
import threading

update_queue = Queue(maxsize=1)
positions = []
arm = sphere(color=color.red)

def serial_reader():
    """Background thread: read from robot."""
    while True:
        pose = robot.get_pose()
        try:
            update_queue.put_nowait(pose)
        except:
            pass  # Queue full, skip

def render_loop():
    """Main thread: render with vprate."""
    frame = vprate(30)
    while True:
        frame(30)
        try:
            pose = update_queue.get_nowait()
            arm.pos = vector(*pose[:3])
            positions.append(arm.pos)
        except:
            pass  # Queue empty

# Start background thread
thread = threading.Thread(target=serial_reader, daemon=True)
thread.start()

# Main loop
render_loop()
```

**Issues:**
- Queue management required
- Main thread must poll Queue (busy-wait pattern)
- No guarantee of synchronized updates

#### Vispy
- **Thread-safety:** YES (via Qt signals/slots)
- **Pattern:** Background thread can directly call canvas methods; Qt handles synchronization
- **Complexity:** Low (Qt event loop manages everything)

```python
from vispy.scene import SceneCanvas
from vispy import app, visuals
import numpy as np
import threading

canvas = SceneCanvas(title='Robot Arm')
view = canvas.central_widget.add_view()

positions = np.array([[0, 0, 0]])
trajectory_line = visuals.Line(pos=positions)
view.add(trajectory_line)

def update_visualization():
    """Callback triggered by timer every ~33 ms."""
    global positions
    # Canvas is automatically updated if positions changed
    trajectory_line.set_data(pos=positions)

def serial_reader():
    """Background thread: read from robot, update canvas directly."""
    global positions
    while True:
        pose = robot.get_pose()
        positions = np.vstack([positions, pose[:3]])
        # Qt automatically syncs to canvas on next draw

timer = app.Timer(interval=0.033)  # ~30 Hz
timer.connect(update_visualization)
timer.start()

thread = threading.Thread(target=serial_reader, daemon=True)
thread.start()

canvas.show()
app.run()
```

**Advantages:**
- No Queue needed (Qt handles it)
- Background thread can update directly
- Automatic synchronization
- No busy-waiting

**Winner:** **VISPY** — Clean, safe threading model. VPython requires manual Queue management.

---

### 6. Integration Boilerplate

#### VPython Setup
```python
# ~30 lines total
from vpython import scene, sphere, cylinder, vector, color, rate as vprate
from queue import Queue
import threading
import serial

# Configuration
scene.width, scene.height = 1200, 800
scene.background = color.white

# Robot visualization
base = sphere(pos=vector(0, 0, 0), radius=10, color=color.gray)
joint1 = cylinder(color=color.blue, radius=5)
joint2 = cylinder(color=color.red, radius=5)
effector = sphere(color=color.green, radius=8)

# State
update_queue = Queue(maxsize=1)
trajectory = []

# Main loop
def main_loop():
    frame_rate = vprate(30)
    while True:
        frame_rate(30)
        try:
            pose = update_queue.get_nowait()
            joint1.pos = vector(*pose[0])
            joint2.pos = vector(*pose[1])
            trajectory.append(pose[0])
        except:
            pass

# Threading
def serial_worker():
    bot = serial.Serial('/dev/ttyUSB0', 115200)
    while True:
        try:
            update_queue.put_nowait(robot.get_pose())
        except:
            pass

thread = threading.Thread(target=serial_worker, daemon=True)
thread.start()
main_loop()
```

#### Vispy Setup
```python
# ~35 lines total
from vispy.scene import SceneCanvas
from vispy import app, visuals
import numpy as np
import threading
import serial

# Canvas setup
canvas = SceneCanvas(title='Robot Arm Visualization', size=(1200, 800))
view = canvas.central_widget.add_view()

# Robot visualization (using meshes or primitives)
positions = np.array([[0, 0, 0], [50, 50, 50], [100, 100, 100]])
trajectory_line = visuals.Line(pos=positions, color='blue', width=2)
view.add(trajectory_line)

joints_scatter = visuals.Markers(size=10, color='red')
view.add(joints_scatter)

# State
robot_pose = np.array([[0, 0, 0]])

def update_visualization(event):
    """Called every ~33 ms by timer."""
    trajectory_line.set_data(pos=robot_pose)
    joints_scatter.set_data(pos=robot_pose)

def serial_reader():
    """Background thread: read from robot."""
    global robot_pose
    bot = serial.Serial('/dev/ttyUSB0', 115200)
    while True:
        pose = robot.get_pose()
        robot_pose = np.vstack([robot_pose, pose[:3]])

# Timer + threading
timer = app.Timer(interval=0.033)
timer.connect(update_visualization)
timer.start()

thread = threading.Thread(target=serial_reader, daemon=True)
thread.start()

canvas.show()
app.run()
```

**Winner:** **TIE** — Similar complexity (~30-35 lines). Vispy slightly cleaner due to no Queue management.

---

### 7. Specific Criteria Summary

| Criterion | VPython | Vispy |
|-----------|---------|-------|
| **Install size** | 9 MB | 10 MB |
| **Requires browser?** | YES (by default) | NO |
| **Native window?** | NO (needs workaround) | YES |
| **Update rate at 10-30 Hz** | ✓ (limited by Jupyter) | ✓✓ (excellent) |
| **3D object support** | ✓✓ (primitives) | ✓ (meshes, scalable) |
| **Threading model** | ✓ (Queue pattern) | ✓✓ (thread-safe Qt) |
| **OpenGL backend** | No (Web-based) | YES (vispy.gloo) |
| **Headless support** | Limited | YES (glfw, pygame backends) |
| **Documentation** | Good | Excellent |
| **Community** | Active (Jupyter-focused) | Active (scientific viz) |

---

## Use Case Analysis

### VPython is BETTER if:
- ✓ You want to demonstrate in Jupyter notebooks
- ✓ You prefer intuitive object-oriented API
- ✓ You're teaching physics/visualization concepts
- ✓ Jupyter environment is already established

### Vispy is BETTER if:
- ✓ **You need a standalone desktop application** ← **THIS PROJECT**
- ✓ **You have background serial I/O thread** ← **THIS PROJECT**
- ✓ **You need reliable 10-30 Hz updates** ← **THIS PROJECT**
- ✓ You want professional-grade visualization
- ✓ You need thread-safe rendering
- ✓ You want GPU acceleration
- ✓ You prefer Qt-based GUI infrastructure

---

## Recommendation for Dobot Robot Arm Lab

### **Winner: VISPY** ✓

**Reasoning:**
1. **Native desktop application** — Students get a real program, not a Jupyter notebook
2. **Thread-safe serial integration** — Robot control runs in background; visualization runs in Qt event loop (automatic synchronization)
3. **10-30 Hz updates trivial** — Vispy's timer model is perfect for robot telemetry
4. **No Jupyter dependency** — Cleaner deployment (can run from terminal)
5. **Professional visualization** — Scales to more complex scenarios later
6. **Clean code** — Minimal boilerplate, no Queue management gymnastics

### Implementation Pattern (Vispy)

```python
#!/usr/bin/env python3
"""Real-time robot arm trajectory visualization with Vispy."""

from vispy.scene import SceneCanvas
from vispy import app, visuals
import numpy as np
import threading
from utils import find_port
from pydobotplus import dobot

# Initialize robot
port = find_port()
robot = dobot(port=port)

# Canvas
canvas = SceneCanvas(title='Dobot Trajectory', size=(1200, 800))
view = canvas.central_widget.add_view()

# Visualization
trajectory = np.array([[0, 0, 0]], dtype=np.float32)
line = visuals.Line(pos=trajectory, color='blue', width=2)
joints = visuals.Markers(pos=trajectory[-1:], size=10, color='red')
view.add(line)
view.add(joints)

# Update callback (called by Qt timer every 33 ms)
def update_frame(event):
    line.set_data(pos=trajectory)
    joints.set_data(pos=trajectory[-1:])

# Background thread: poll robot
def robot_reader():
    global trajectory
    while True:
        pose = robot.get_pose()
        trajectory = np.vstack([trajectory, pose[:3]])

# Start
timer = app.Timer(interval=0.033)  # 30 Hz
timer.connect(update_frame)
timer.start()

thread = threading.Thread(target=robot_reader, daemon=True)
thread.start()

canvas.show()
app.run()
```

---

## Next Steps

1. **Install Vispy:**
   ```bash
   pip install vispy PyQt5
   ```

2. **Create demo script:** `scripts/16_visualize_trajectory.py`
   - Connect to Dobot
   - Stream trajectory to Vispy canvas
   - Demonstrate 10-30 Hz update capability

3. **Documentation:** Update `GUIDE.md` with visualization section

4. **Optional:** Create example with multiple trajectories, joint highlighting, etc.

---

## Research Notes

- **VPython (7.6.5):** Excellent for Jupyter + educational use. Not designed for standalone apps.
- **Vispy (0.16.1):** Professional visualization, Qt integration, thread-safe, modern OpenGL abstractions.
- **Ecosystem:** Both active communities. Vispy more aligned with scientific computing; VPython more aligned with physics education.

**2025 Verdict:** Vispy is the superior choice for this robotics lab project.
