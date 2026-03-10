# PyQtGraph Real-Time Robot Visualization Guide

## 1. Installation & Dependencies

### Recommended Setup (PyQt5 + pyqtgraph)

```bash
# Option A: mamba/conda
mamba create -n dobot-viz python=3.10 -y
mamba activate dobot-viz
pip install -U pip
pip install PyQt5 pyqtgraph numpy

# Option B: pip + venv
python3 -m venv .venv-viz
source .venv-viz/bin/activate
pip install -U pip
pip install PyQt5 pyqtgraph numpy
```

### Dependencies Summary

| Package      | Version | Purpose                                    | Notes                          |
|--------------|---------|--------------------------------------------|-----------------------         |
| PyQt5        | 5.15+   | Qt5 Python bindings                        | Official Qt bindings           |
| pyqtgraph    | 0.13+   | Real-time 2D/3D plotting & visualization   | Built on Qt                    |
| numpy        | 1.20+   | Numerical arrays & fast updates             | Required by pyqtgraph          |
| pydobotplus  | *       | Robot control (Track A)                     | From requirements.txt          |
| pyserial     | *       | Serial communication                        | From requirements.txt          |

**Optional (Qt6 support):**
- PySide6 (official Qt6 bindings) - pyqtgraph also works with PySide6
- PyQt6 (alternative Qt6 bindings) - limited pyqtgraph support, use PyQt5 preferred

### Installation Footprints

```
PyQt5: ~250 MB (core: 120 MB + plugins 100 MB + dependencies 30 MB)
pyqtgraph: ~4 MB (lightweight Python-only library)
numpy: ~40 MB
Total new: ~300 MB (modest for visualization needs)
```

---

## 2. 2D Plot Update Speed Analysis

### Update Rate Characteristics

**pyqtgraph 2D PlotWidget:**
- **Achievable update rate:** 30–60 Hz (typical)
- **Bottleneck:** Qt event loop refresh rate (vsync-limited on many systems)
- **Safe sustained rate:** 10–30 Hz for smooth real-time display
- **Peak bursts:** Up to 60 Hz possible with optimized data handling

**Update Pattern (Simple):**
```python
import pyqtgraph as pg
import numpy as np
from PyQt5.QtCore import QTimer

curve = plot.plot(pen='r')
timer = QTimer()
timer.timeout.connect(update_data)
timer.start(33)  # ~30 Hz (33 ms per frame)

def update_data():
    new_x, new_y = robot.get_pose_xy()
    # Either append or set entire data
    curve.setData(x, y, pen='r')  # ~30 Hz sustainable
```

**Optimization Tips:**
1. **Use `setData()` not `addPoints()`** — setData is ~3× faster for bulk updates
2. **Pre-allocate arrays** — avoid repeated memory allocation
3. **Downsample if > 30 Hz** — collect 3–5 points, update on batch
4. **Disable antialiasing** for rate-critical plots: `plot.opts['antialiasing'] = False`
5. **Run plot in separate thread** — don't block Qt event loop with I/O

---

## 3. 3D Support via pyqtgraph.opengl

### Available 3D Primitives

| Class                  | Use case                                        | Performance |
|------------------------|------------------------------------------------|-------------|
| `GLViewWidget`         | Main 3D canvas (equivalent to `PlotWidget`)    | Excellent   |
| `GLLinePlotItem`       | Trajectory lines, arm links, grid              | Very good   |
| `GLScatterPlotItem`    | End-effector position, joints, points          | Very good   |
| `GLMeshItem`           | Robot body CAD mesh (STL/OBJ via Mesh object) | Good (VBO)  |
| `GLBoxItem`            | Workspace bounding box                         | Excellent   |
| `GLGridItem`           | Reference axes/grid                            | Excellent   |

### 3D Update Pattern (Minimal)

```python
from pyqtgraph.opengl import GLViewWidget, GLLinePlotItem, GLScatterPlotItem, GLBoxItem
import numpy as np

view = GLViewWidget()

# Static workspace box
box = GLBoxItem(size=(130, 320, 140), color=(1, 1, 1, 0.3))
box.translate(215, 0, 80)  # Center at workspace center
view.addItem(box)

# Dynamic trajectory line
trajectory = GLLinePlotItem(
    pos=np.array([[0, 0, 0]]),
    color=(1, 0, 0, 1),
    width=2,
    antialias=False
)
view.addItem(trajectory)

# End-effector position
scatter = GLScatterPlotItem(pos=np.array([[0, 0, 0]]), color=(0, 1, 0, 1), size=5)
view.addItem(scatter)

# Update loop (from robot data)
def update_3d():
    pose = unpack_pose(robot.get_pose())
    trajectory.setData(pos=trajectory_points)
    scatter.setData(pos=np.array([pose[:3]]))
```

---

## 4. Threading Patterns: Separate Thread vs. Process

### Pattern A: QThread (Recommended for most cases)

**Pros:**
- Shared memory → easy data exchange (queues, locks)
- Lower overhead than multiprocessing
- Works well with Qt signals/slots
- Simpler debugging

**Cons:**
- GIL-limited if CPU-heavy robot math
- Qt must run in main thread

```python
# Pattern: QThread for robot control, Qt event loop in main thread
import sys
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import pyqtgraph as pg
from queue import Queue

class RobotWorker(QThread):
    pose_updated = pyqtSignal(tuple)  # (x, y, z, r)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.robot = None
    
    def run(self):
        # Control loop runs in worker thread
        self.robot = DobotMagician(port="/dev/ttyUSB0")
        while self.running:
            pose = self.robot.get_pose()
            self.pose_updated.emit(pose)
            time.sleep(0.05)  # 20 Hz sampling
    
    def stop(self):
        self.running = False
        if self.robot:
            self.robot.close()

class VisualizationWindow(pg.PlotWidget):
    def __init__(self):
        super().__init__()
        self.setLabel('left', 'Y (mm)')
        self.setLabel('bottom', 'X (mm)')
        self.curve = self.plot(pen='r')
        
        # Start worker thread
        self.worker = RobotWorker()
        self.worker.pose_updated.connect(self.on_pose_update)
        self.worker.start()
        
        self.trajectory = []
    
    def on_pose_update(self, pose):
        x, y, z, r = pose
        self.trajectory.append((x, y))
        if len(self.trajectory) > 1000:
            self.trajectory.pop(0)
        
        xs, ys = zip(*self.trajectory)
        self.curve.setData(xs, ys)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VisualizationWindow()
    window.show()
    
    # Cleanup on exit
    def closeEvent(ev):
        window.worker.stop()
        window.worker.wait()
    window.closeEvent = closeEvent
    
    sys.exit(app.exec_())
```

### Pattern B: Multiprocessing (For CPU-intensive tasks)

**Pros:**
- True parallelism (bypasses GIL)
- Isolated processes (one crash won't kill visualization)

**Cons:**
- Inter-process communication overhead
- Pickling/serialization of data
- More complex debugging
- Serial port can't be shared → requires queue-based protocol

```python
# Pattern: Multiprocessing with Queue for data exchange
import multiprocessing as mp
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
import sys
from PyQt5.QtWidgets import QApplication

def robot_control_process(pose_queue, command_queue):
    """Runs in separate process"""
    from scripts.utils import find_port, unpack_pose
    from pydobotplus import Dobot
    
    robot = Dobot(port=find_port())
    
    while True:
        pose = unpack_pose(robot.get_pose())
        pose_queue.put(pose)
        
        # Check for commands
        try:
            cmd = command_queue.get_nowait()
            if cmd[0] == 'move':
                robot.move_to(*cmd[1], wait=True)
            elif cmd[0] == 'stop':
                break
        except:
            pass
        
        time.sleep(0.05)
    
    robot.close()

class VisualizationApp(pg.PlotWidget):
    def __init__(self, pose_queue, command_queue):
        super().__init__()
        self.pose_queue = pose_queue
        self.command_queue = command_queue
        
        self.curve = self.plot(pen='r')
        self.trajectory = []
        
        # Poll queue at 30 Hz
        timer = QTimer()
        timer.timeout.connect(self.poll_data)
        timer.start(33)
    
    def poll_data(self):
        try:
            while True:
                pose = self.pose_queue.get_nowait()
                x, y, z, r = pose
                self.trajectory.append((x, y))
                if len(self.trajectory) > 1000:
                    self.trajectory.pop(0)
        except:
            pass
        
        if len(self.trajectory) > 1:
            xs, ys = zip(*self.trajectory)
            self.curve.setData(xs, ys)

if __name__ == '__main__':
    pose_q = mp.Queue()
    cmd_q = mp.Queue()
    
    process = mp.Process(target=robot_control_process, args=(pose_q, cmd_q))
    process.start()
    
    app = QApplication(sys.argv)
    window = VisualizationApp(pose_q, cmd_q)
    window.show()
    
    sys.exit(app.exec_())
```

### Pattern Comparison

| Aspect              | QThread               | Multiprocessing       |
|---------------------|-----------------------|-----------------------|
| **Setup complexity** | Simple                | Moderate              |
| **Memory overhead**  | Low (shared memory)   | High (separate VM)    |
| **Communication**    | Queues, signals, vars | Queues only           |
| **GIL avoidance**    | No                    | Yes (true parallel)   |
| **Robot I/O**        | Direct serial access  | Serialized commands   |
| **Recommended for**  | Most 2D/3D viz        | Heavy computation     |

---

## 5. Workspace Bounding Box in 3D

### Dobot Magician Workspace Bounds

```python
# From ME403 documentation
SAFE_BOUNDS = {
    "x": (120, 315),    # mm, workspace depth
    "y": (-158, 158),   # mm, left-right
    "z": (5, 155),      # mm, height above base
    "r": (-90, 90)      # degrees, rotation
}

# Derived center and size for GLBoxItem
workspace_center = ((120+315)/2, 0, (5+155)/2)   # (217.5, 0, 80)
workspace_size = (315-120, 316, 155-5)           # (195, 316, 150)
```

### 3D Visualization Code

```python
from pyqtgraph.opengl import GLViewWidget, GLBoxItem, GLGridItem
import numpy as np

def setup_workspace_visualization():
    view = GLViewWidget()
    
    # Set camera view for Dobot workspace
    view.opts['distance'] = 400
    view.setCameraPosition(distance=400, elevation=30, azimuth=-45)
    
    # Workspace bounding box
    box = GLBoxItem(size=(130, 320, 140), color=(1, 0, 0, 0.2))
    box.translate(215, 0, 80)
    view.addItem(box)
    
    # Reference grid (XY plane at Z=10)
    grid = GLGridItem()
    grid.scale(2, 2, 1)
    grid.translate(215, 0, 10)
    view.addItem(grid)
    
    # Axes
    from pyqtgraph.opengl import GLAxisItem
    axis = GLAxisItem()
    axis.setSize(100, 100, 100)
    view.addItem(axis)
    
    return view
```

---

## 6. Minimal Working Examples

### Example 1: 2D Real-Time Plot (QThread)

**File:** `scripts/viz_2d_realtime.py`

```python
#!/usr/bin/env python3
"""
2D real-time trajectory visualization using pyqtgraph.
Runs robot control in QThread, visualization in main thread.
Update rate: 10–30 Hz sustainable.
"""

import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
import pyqtgraph as pg
import numpy as np

from utils import find_port

class RobotWorker(QThread):
    """Background thread for robot control"""
    pose_updated = pyqtSignal(tuple)
    
    def __init__(self, port):
        super().__init__()
        self.running = True
        self.port = port
        self.robot = None
    
    def run(self):
        try:
            from pydobotplus import Dobot
            from utils import unpack_pose

            self.robot = Dobot(port=self.port)
            
            while self.running:
                pose = unpack_pose(self.robot.get_pose())
                self.pose_updated.emit(pose)
                time.sleep(0.05)  # 20 Hz
        except Exception as e:
            print(f"Robot error: {e}")
    
    def stop(self):
        self.running = False
        if self.robot:
            try:
                self.robot.close()
            except:
                pass

class RealTimeViz2D(QMainWindow):
    """2D trajectory visualization window"""
    
    def __init__(self, port):
        super().__init__()
        self.setWindowTitle("Dobot 2D Real-Time Visualization")
        self.setGeometry(100, 100, 800, 600)
        
        # Setup plot
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Y (mm)', color='white')
        self.plot_widget.setLabel('bottom', 'X (mm)', color='white')
        self.plot_widget.setTitle('End-Effector XY Trajectory')
        self.plot_widget.setAspectLocked(True)
        
        # Workspace bounds reference
        self.plot_widget.setXRange(90, 345)
        self.plot_widget.setYRange(-180, 180)
        
        # Add workspace box region
        workspace_region = pg.LinearRegionItem(
            values=[120, 315],
            orientation='vertical',
            brush=pg.mkBrush(255, 0, 0, 30),
            movable=False
        )
        self.plot_widget.addItem(workspace_region)
        
        self.trajectory_curve = self.plot_widget.plot(pen=pg.mkPen('r', width=2))
        self.current_point = self.plot_widget.plot(pen=None, symbol='o', symbolSize=10, symbolBrush='g')
        
        # Layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.plot_widget)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # Trajectory storage
        self.trajectory = []
        self.max_history = 1000
        
        # Start robot thread
        self.worker = RobotWorker(port)
        self.worker.pose_updated.connect(self.on_pose_update)
        self.worker.start()
    
    def on_pose_update(self, pose):
        """Called when robot sends new pose"""
        x, y, z, r, *_ = pose
        self.trajectory.append((x, y))
        
        if len(self.trajectory) > self.max_history:
            self.trajectory.pop(0)
        
        if len(self.trajectory) > 1:
            xs, ys = zip(*self.trajectory)
            self.trajectory_curve.setData(xs, ys)
        
        self.current_point.setData([x], [y])
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        self.worker.stop()
        self.worker.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    port = find_port()
    if not port:
        print("Robot not found. Run 01_find_port.py first.")
        sys.exit(1)
    
    window = RealTimeViz2D(port)
    window.show()
    sys.exit(app.exec_())
```

### Example 2: 3D Workspace + Trajectory (QThread)

**File:** `scripts/viz_3d_workspace.py`

```python
#!/usr/bin/env python3
"""
3D workspace visualization with end-effector trajectory.
Shows bounding box, reference grid, and live trajectory.
"""

import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QThread, pyqtSignal
from pyqtgraph.opengl import (
    GLViewWidget, GLBoxItem, GLGridItem, GLLinePlotItem,
    GLScatterPlotItem, GLAxisItem
)
import numpy as np

from utils import find_port, SAFE_BOUNDS

class RobotWorker(QThread):
    """Background thread for robot control"""
    pose_updated = pyqtSignal(tuple)
    
    def __init__(self, port):
        super().__init__()
        self.running = True
        self.port = port
        self.robot = None
    
    def run(self):
        try:
            from pydobotplus import Dobot
            from utils import unpack_pose

            self.robot = Dobot(port=self.port)
            
            while self.running:
                pose = unpack_pose(self.robot.get_pose())
                self.pose_updated.emit(pose)
                time.sleep(0.05)  # 20 Hz
        except Exception as e:
            print(f"Robot error: {e}")
    
    def stop(self):
        self.running = False
        if self.robot:
            try:
                self.robot.close()
            except:
                pass

class RealTimeViz3D(QMainWindow):
    """3D workspace visualization window"""
    
    def __init__(self, port):
        super().__init__()
        self.setWindowTitle("Dobot 3D Workspace Visualization")
        self.setGeometry(100, 100, 1000, 800)
        
        # Setup 3D view
        self.view = GLViewWidget()
        self.view.opts['distance'] = 400
        self.view.setCameraPosition(distance=400, elevation=30, azimuth=-45)
        
        # Workspace bounds
        bounds = SAFE_BOUNDS
        x_min, x_max = bounds['x']
        y_min, y_max = bounds['y']
        z_min, z_max = bounds['z']
        
        center_x = (x_min + x_max) / 2
        center_y = (y_min + y_max) / 2
        center_z = (z_min + z_max) / 2
        
        size_x = x_max - x_min
        size_y = y_max - y_min
        size_z = z_max - z_min
        
        # Workspace bounding box
        workspace_box = GLBoxItem(
            size=(size_x, size_y, size_z),
            color=(1, 0, 0, 0.15)
        )
        workspace_box.translate(center_x, center_y, center_z)
        self.view.addItem(workspace_box)
        
        # Reference grid
        grid = GLGridItem(size=(size_x * 2, size_y * 2, 1))
        grid.translate(center_x, center_y, z_min)
        self.view.addItem(grid)
        
        # Axes
        axis = GLAxisItem()
        axis.setSize(100, 100, 100)
        self.view.addItem(axis)
        
        # Trajectory line
        self.trajectory_line = GLLinePlotItem(
            pos=np.array([[0, 0, 0]]),
            color=(1, 0, 0, 1),
            width=2,
            antialias=False
        )
        self.view.addItem(self.trajectory_line)
        
        # End-effector scatter
        self.ee_scatter = GLScatterPlotItem(
            pos=np.array([[0, 0, 0]]),
            color=(0, 1, 0, 1),
            size=8
        )
        self.view.addItem(self.ee_scatter)
        
        # Layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # Trajectory storage
        self.trajectory = np.array([[0, 0, 0]])
        self.max_history = 500
        
        # Start robot thread
        self.worker = RobotWorker(port)
        self.worker.pose_updated.connect(self.on_pose_update)
        self.worker.start()
    
    def on_pose_update(self, pose):
        """Called when robot sends new pose"""
        x, y, z, r = pose
        point = np.array([[x, y, z]])
        
        if len(self.trajectory) >= self.max_history:
            self.trajectory = self.trajectory[1:]
        
        self.trajectory = np.vstack([self.trajectory, point])
        
        # Update visualization
        self.trajectory_line.setData(pos=self.trajectory)
        self.ee_scatter.setData(pos=point)
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        self.worker.stop()
        self.worker.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    port = find_port()
    if not port:
        print("Robot not found. Run 01_find_port.py first.")
        sys.exit(1)
    
    window = RealTimeViz3D(port)
    window.show()
    sys.exit(app.exec_())
```

### Example 3: 3D with Multiprocessing

**File:** `scripts/viz_3d_multiprocess.py`

```python
#!/usr/bin/env python3
"""
3D visualization using multiprocessing for robot control.
Useful for CPU-intensive post-processing or heavy visualization.
"""

import sys
import time
import multiprocessing as mp
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer
from pyqtgraph.opengl import (
    GLViewWidget, GLBoxItem, GLGridItem, GLLinePlotItem,
    GLScatterPlotItem, GLAxisItem
)
import numpy as np

from utils import find_port, SAFE_BOUNDS

def robot_control_process(pose_queue, stop_event):
    """Runs robot control in separate process"""
    try:
        from pydobotplus import Dobot
        from utils import find_port, unpack_pose
        
        robot = Dobot(port=find_port())
        
        while not stop_event.is_set():
            pose = unpack_pose(robot.get_pose())
            try:
                pose_queue.put(pose, timeout=1)
            except:
                pass
            time.sleep(0.05)
        
        robot.close()
    except Exception as e:
        print(f"Robot process error: {e}")

class RealTimeViz3DMultiprocess(QMainWindow):
    """3D visualization with multiprocessing"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dobot 3D (Multiprocessing)")
        self.setGeometry(100, 100, 1000, 800)
        
        # Setup 3D view
        self.view = GLViewWidget()
        self.view.opts['distance'] = 400
        self.view.setCameraPosition(distance=400, elevation=30, azimuth=-45)
        
        # Workspace setup
        bounds = SAFE_BOUNDS
        x_min, x_max = bounds['x']
        y_min, y_max = bounds['y']
        z_min, z_max = bounds['z']
        
        center_x = (x_min + x_max) / 2
        center_y = (y_min + y_max) / 2
        center_z = (z_min + z_max) / 2
        
        size_x = x_max - x_min
        size_y = y_max - y_min
        size_z = z_max - z_min
        
        # Workspace box
        workspace_box = GLBoxItem(
            size=(size_x, size_y, size_z),
            color=(1, 0, 0, 0.15)
        )
        workspace_box.translate(center_x, center_y, center_z)
        self.view.addItem(workspace_box)
        
        # Grid + axes
        grid = GLGridItem(size=(size_x * 2, size_y * 2, 1))
        grid.translate(center_x, center_y, z_min)
        self.view.addItem(grid)
        
        axis = GLAxisItem()
        axis.setSize(100, 100, 100)
        self.view.addItem(axis)
        
        # Trajectory line
        self.trajectory_line = GLLinePlotItem(
            pos=np.array([[0, 0, 0]]),
            color=(1, 0, 0, 1),
            width=2,
            antialias=False
        )
        self.view.addItem(self.trajectory_line)
        
        # End-effector scatter
        self.ee_scatter = GLScatterPlotItem(
            pos=np.array([[0, 0, 0]]),
            color=(0, 1, 0, 1),
            size=8
        )
        self.view.addItem(self.ee_scatter)
        
        # Layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # Multiprocessing setup
        self.pose_queue = mp.Queue(maxsize=2)
        self.stop_event = mp.Event()
        self.process = mp.Process(
            target=robot_control_process,
            args=(self.pose_queue, self.stop_event)
        )
        self.process.start()
        
        # Trajectory storage
        self.trajectory = np.array([[0, 0, 0]])
        self.max_history = 500
        
        # Poll queue at 30 Hz
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_queue)
        self.timer.start(33)
    
    def poll_queue(self):
        """Poll pose queue and update visualization"""
        try:
            while True:
                pose = self.pose_queue.get_nowait()
                x, y, z, r = pose
                point = np.array([[x, y, z]])
                
                if len(self.trajectory) >= self.max_history:
                    self.trajectory = self.trajectory[1:]
                
                self.trajectory = np.vstack([self.trajectory, point])
                
                self.trajectory_line.setData(pos=self.trajectory)
                self.ee_scatter.setData(pos=point)
        except:
            pass
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        self.timer.stop()
        self.stop_event.set()
        self.process.join(timeout=2)
        if self.process.is_alive():
            self.process.terminate()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RealTimeViz3DMultiprocess()
    window.show()
    sys.exit(app.exec_())
```

---

## 7. Common Patterns & Tips

### Update Rate Tuning

```python
# QThread pattern: Adjust update frequency
class RobotWorker(QThread):
    pose_updated = pyqtSignal(tuple)
    
    def run(self):
        while self.running:
            pose = unpack_pose(self.robot.get_pose())
            self.pose_updated.emit(pose)
            time.sleep(0.05)  # 20 Hz: adjust 0.033 (30 Hz) to 0.1 (10 Hz)
```

### Performance Monitoring

```python
import time

class PerformanceMonitor:
    def __init__(self):
        self.times = []
    
    def tick(self):
        self.times.append(time.time())
        if len(self.times) > 100:
            self.times.pop(0)
    
    @property
    def fps(self):
        if len(self.times) < 2:
            return 0
        dt = self.times[-1] - self.times[0]
        return len(self.times) / dt if dt > 0 else 0

# In update function
monitor = PerformanceMonitor()
monitor.tick()
print(f"Update rate: {monitor.fps:.1f} Hz")
```

### Handling Long Trajectories

```python
# Use a rolling buffer to avoid memory bloat
def update_trajectory(trajectory_line, new_point, max_points=1000):
    current_pos = trajectory_line.pos
    
    if len(current_pos) >= max_points:
        # Drop oldest point
        new_pos = np.vstack([current_pos[1:], new_point])
    else:
        new_pos = np.vstack([current_pos, new_point])
    
    trajectory_line.setData(pos=new_pos)
```

### Graceful Shutdown

```python
def closeEvent(self, event):
    """Always cleanup threads/processes"""
    if hasattr(self, 'worker'):
        self.worker.stop()
        self.worker.wait(timeout=2000)  # 2 second timeout
    
    if hasattr(self, 'process'):
        self.stop_event.set()
        self.process.join(timeout=2)
        if self.process.is_alive():
            self.process.terminate()
    
    event.accept()
```

---

## 8. Troubleshooting

| Problem                          | Cause                              | Solution                               |
|----------------------------------|----------------------------------|-----------------------------------------|
| Qt platform plugin not found     | Qt libraries not installed        | `pip install PyQt5`                     |
| QApplication already exists      | Multiple QApplication instances  | Create only one per process             |
| Serial port blocked              | Other process owns port           | Kill DobotStudio or previous Python app |
| Plot not updating                | Event loop blocked               | Use QThread for robot I/O               |
| 3D view very slow                | Too many trajectory points       | Limit history to 500–1000 points        |
| Memory leak in long runs         | Unbounded trajectory array       | Use rolling buffer with max_history     |
| Multiprocessing hangs            | Deadlock in Queue.put()          | Use timeout: `queue.put(x, timeout=1)`  |

---

## References

- **pyqtgraph docs:** https://www.pyqtgraph.org/
- **PyQt5 docs:** https://www.riverbankcomputing.com/static/Docs/PyQt5/
- **OpenGL visualization:** pyqtgraph.opengl module reference
- **Real-time plotting:** "Best Practices for Real-Time Qt Visualization"
