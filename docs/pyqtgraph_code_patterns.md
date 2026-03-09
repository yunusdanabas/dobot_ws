# PyQtGraph Code Patterns: Side-by-Side Comparison

Quick reference for implementing visualization with different threading patterns.

---

## Pattern 1: QThread (Recommended)

### Architecture Diagram

```
┌─────────────────────────────────┐
│ Main Thread (Qt Event Loop)     │
│                                 │
│  ┌───────────────────────┐      │
│  │ MainWindow            │      │
│  │  PlotWidget           │◄─────┼── pose_updated.emit(pose)
│  │  on_pose_update()     │      │    (Qt Signal, thread-safe)
│  └───────────────────────┘      │
└─────────────────────────────────┘
          ▲
          │ pyqtSignal
          │ (queued connection)
          │
┌─────────────────────────────────┐
│ Worker Thread (QThread)         │
│                                 │
│  RobotWorker.run():             │
│    while self.running:          │
│      pose = robot.get_pose()    │◄─ Blocks 5-10 ms (serial I/O)
│      self.pose_updated.emit()   │   Then queues to main thread
│      time.sleep(0.05)           │   (~50 ms per cycle)
│                                 │
└─────────────────────────────────┘
```

### Complete Code Pattern

```python
import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QThread, pyqtSignal
import pyqtgraph as pg

class RobotWorker(QThread):
    """Background thread for robot control"""
    pose_updated = pyqtSignal(tuple)  # Signal: (x, y, z, r)
    
    def __init__(self, port):
        super().__init__()
        self.running = True
        self.port = port
        self.robot = None
    
    def run(self):
        """Runs in background thread"""
        try:
            from pydobotplus import Dobot
            self.robot = Dobot(port=self.port, verbose=False)
            self.robot.wait_for_home()
            
            while self.running:
                pose = self.robot.get_pose()  # Blocks ~5-10 ms
                self.pose_updated.emit(pose)   # Thread-safe signal
                time.sleep(0.05)               # 20 Hz sampling
        except Exception as e:
            print(f"Error: {e}")
    
    def stop(self):
        """Stop the worker thread"""
        self.running = False
        if self.robot:
            try:
                self.robot.close()
            except:
                pass

class VisualizationWindow(QMainWindow):
    """Main visualization window"""
    
    def __init__(self, port):
        super().__init__()
        self.setWindowTitle("Dobot Visualization")
        self.setGeometry(100, 100, 800, 600)
        
        # Setup plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Y (mm)')
        self.plot_widget.setLabel('bottom', 'X (mm)')
        self.curve = self.plot_widget.plot(pen='r')
        
        self.setCentralWidget(self.plot_widget)
        
        # Data storage
        self.trajectory = []
        
        # Start worker thread
        self.worker = RobotWorker(port)
        self.worker.pose_updated.connect(self.on_pose_update)  # Connect signal→slot
        self.worker.start()
    
    def on_pose_update(self, pose):
        """Slot called when robot sends new pose (in main thread)"""
        x, y, z, r = pose
        self.trajectory.append((x, y))
        
        if len(self.trajectory) > 1:
            xs, ys = zip(*self.trajectory)
            self.curve.setData(xs, ys)
    
    def closeEvent(self, event):
        """Cleanup when window closes"""
        self.worker.stop()
        self.worker.wait(timeout=2000)  # Wait up to 2 seconds
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    from utils import find_port
    port = find_port()
    
    window = VisualizationWindow(port)
    window.show()
    
    sys.exit(app.exec_())
```

### Key Points

✓ **Thread-safe:** `pyqtSignal` automatically queues to main thread  
✓ **Responsive:** UI never blocks on serial I/O  
✓ **Simple:** One QApplication, one window  
✓ **Cleanup:** Proper `stop()` and `wait()`  
✗ **GIL-limited:** CPU-heavy processing limited to ~1 core

---

## Pattern 2: Multiprocessing

### Architecture Diagram

```
┌─────────────────────────────────┐
│ Main Process (Qt Event Loop)    │
│                                 │
│  ┌───────────────────────┐      │
│  │ MainWindow            │      │
│  │  PlotWidget           │      │
│  │  on_pose_update()     │◄──┐  │
│  └───────────────────────┘   │  │
│                              │  │
│  QTimer (30 Hz):             │  │
│    try:                      │  │
│      pose = queue.get_no │  │
│        wait()            │  │
│      on_pose_update()────┘  │
│    except: pass             │
│                              │
└─────────────────────────────────┘
       ▲
       │ Multiprocessing.Queue
       │ (IPC via OS, ~1-3 ms per item)
       │
       ├─ Serialization (pickle)
       │ ~1-2 ms for pose tuple
       │
┌──────┴──────────────────────────┐
│ Child Process                    │
│                                 │
│  robot_control_process():       │
│    robot = connect()            │
│    while not stop_event:        │
│      pose = robot.get_pose()    │◄─ Blocks 5-10 ms (serial I/O)
│      try:                       │
│        queue.put(pose,          │   ~1-2 ms serialization
│          timeout=1)             │   ~1-3 ms IPC transfer
│      except:                    │
│        pass  (queue full)       │
│      time.sleep(0.05)           │   Rest: 33 ms
│                                 │
└─────────────────────────────────┘
```

### Complete Code Pattern

```python
import sys
import time
import multiprocessing as mp
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QTimer
import pyqtgraph as pg

def robot_control_process(pose_queue, stop_event):
    """Runs in separate OS process"""
    try:
        from pydobotplus import Dobot
        from utils import find_port
        
        port = find_port()
        robot = Dobot(port=port, verbose=False)
        robot.wait_for_home()
        
        while not stop_event.is_set():
            try:
                pose = robot.get_pose()  # Blocks ~5-10 ms
                # Non-blocking put with timeout (avoid deadlock)
                pose_queue.put(pose, timeout=0.5)
            except:
                pass  # Queue full or timeout
            
            time.sleep(0.05)  # 20 Hz sampling
        
        robot.close()
    except Exception as e:
        print(f"Process error: {e}")

class VisualizationWindow(QMainWindow):
    """Main visualization window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dobot Visualization (Multiprocess)")
        self.setGeometry(100, 100, 800, 600)
        
        # Setup plot
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Y (mm)')
        self.plot_widget.setLabel('bottom', 'X (mm)')
        self.curve = self.plot_widget.plot(pen='r')
        
        self.setCentralWidget(self.plot_widget)
        
        # Data storage
        self.trajectory = []
        
        # Multiprocessing setup
        self.pose_queue = mp.Queue(maxsize=2)  # Small queue to limit latency
        self.stop_event = mp.Event()
        
        self.process = mp.Process(
            target=robot_control_process,
            args=(self.pose_queue, self.stop_event),
            daemon=False  # Not daemon: we'll clean up explicitly
        )
        self.process.start()
        
        # Poll queue at 30 Hz (faster than robot sampling)
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_queue)
        self.timer.start(33)  # milliseconds
    
    def poll_queue(self):
        """Called by Qt timer every 33 ms"""
        try:
            # Non-blocking: consume all queued poses
            while True:
                pose = self.pose_queue.get_nowait()  # Raises queue.Empty if empty
                self.on_pose_update(pose)
        except:
            pass  # Queue empty
    
    def on_pose_update(self, pose):
        """Update visualization with new pose"""
        x, y, z, r = pose
        self.trajectory.append((x, y))
        
        if len(self.trajectory) > 1:
            xs, ys = zip(*self.trajectory)
            self.curve.setData(xs, ys)
    
    def closeEvent(self, event):
        """Cleanup when window closes"""
        self.timer.stop()
        
        # Signal process to stop
        self.stop_event.set()
        
        # Wait for process to exit
        self.process.join(timeout=2)
        
        # If still running, terminate
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=1)
        
        event.accept()

if __name__ == '__main__':
    # Required on some platforms
    mp.set_start_method('spawn', force=True)
    
    app = QApplication(sys.argv)
    window = VisualizationWindow()
    window.show()
    
    sys.exit(app.exec_())
```

### Key Points

✓ **True parallelism:** GIL not a factor  
✓ **Process isolation:** Crash in robot code won't crash UI  
✓ **CPU-bound capable:** Heavy math possible in process  
✗ **Higher latency:** ~100–300 ms typical  
✗ **More complex:** IPC, serialization, process management  
✗ **Memory overhead:** ~30–50 MB per process  

---

## Pattern 3: Hybrid (Best of Both Worlds)

Use QThread for robot I/O, but offload heavy computation to process pool:

```python
from concurrent.futures import ProcessPoolExecutor
from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np

class RobotWorker(QThread):
    pose_updated = pyqtSignal(tuple)
    
    def __init__(self, port):
        super().__init__()
        self.running = True
        self.port = port
        
        # Delegate heavy math to process pool
        self.executor = ProcessPoolExecutor(max_workers=2)
    
    def run(self):
        from pydobotplus import Dobot
        robot = Dobot(port=self.port, verbose=False)
        
        while self.running:
            pose = robot.get_pose()
            
            # Fast: just queue to thread pool
            # Doesn't block robot I/O thread
            self.executor.submit(self.compute_inverse_kinematics, pose)
            
            self.pose_updated.emit(pose)
            time.sleep(0.05)
    
    @staticmethod
    def compute_inverse_kinematics(pose):
        """CPU-intensive, runs in process pool, doesn't block main UI or robot thread"""
        # Heavy computation here
        pass
    
    def stop(self):
        self.running = False
        self.executor.shutdown(wait=False)
```

**Benefits:**
- UI responsive (main thread)
- Robot thread unblocked (QThread)
- Heavy math parallelized (ProcessPoolExecutor)
- Simple code (~20 lines hybrid code)

---

## Update Rate Comparison

### Code to Measure Update Rate

```python
import time

class PerformanceMonitor:
    def __init__(self, window_size=100):
        self.times = []
        self.window_size = window_size
    
    def tick(self):
        self.times.append(time.time())
        if len(self.times) > self.window_size:
            self.times.pop(0)
    
    @property
    def fps(self):
        if len(self.times) < 2:
            return 0
        dt = self.times[-1] - self.times[0]
        return len(self.times) / dt if dt > 0 else 0
    
    @property
    def frame_times_ms(self):
        times = np.diff(self.times) * 1000
        return {
            'min': times.min(),
            'max': times.max(),
            'mean': times.mean(),
            'stdev': times.std()
        }

# Usage in on_pose_update():
monitor = PerformanceMonitor()
def on_pose_update(self, pose):
    monitor.tick()
    if monitor.fps > 0:
        print(f"FPS: {monitor.fps:.1f}, Frame times: {monitor.frame_times_ms}")
```

### Expected Results

| Pattern | Sustainable Rate | Notes |
|---------|------------------|-------|
| QThread 2D | 20–30 Hz | Limited by Qt event loop + vsync |
| Multiprocess 2D | 20–30 Hz | Limited by queue polling + vsync |
| QThread 3D | 15–25 Hz | OpenGL rendering overhead |
| Multiprocess 3D | 15–25 Hz | Same rendering overhead |

---

## Memory Usage Comparison

### Measurement Code

```python
import psutil
import os

def get_memory_info():
    process = psutil.Process(os.getpid())
    info = process.memory_info()
    return {
        'rss': info.rss / 1024 / 1024,      # MB
        'vms': info.vms / 1024 / 1024,      # MB
        'percent': process.memory_percent()  # %
    }

# Baseline: nothing
print("Baseline:", get_memory_info())

# After creating QApplication + PlotWidget
print("After Qt setup:", get_memory_info())

# After starting QThread
print("After QThread:", get_memory_info())

# After starting multiprocess
print("After multiprocess:", get_memory_info())
```

### Expected Results

| Phase | Memory (MB) | Delta (MB) |
|-------|------------|-----------|
| Python baseline | 25–30 | — |
| + PyQt5 + pyqtgraph | 80–100 | +50–70 |
| + QThread (robot) | 100–120 | +0–20 |
| + Multiprocess (robot) | 130–160 | +30–60 |

---

## Choosing a Pattern

```python
# Decision tree:

if heavy_computation_on_pose_data:
    # Option A: Use Multiprocessing (true parallelism)
    if isolation_important:
        return 'multiprocessing'
    # Option B: Use QThread + ProcessPoolExecutor (hybrid)
    else:
        return 'hybrid'

elif simple_visualization:
    # Always QThread (simplest, fastest, most responsive)
    return 'qthread'

else:
    # Default to QThread
    return 'qthread'
```

---

## Common Mistakes & Fixes

### ❌ Mistake 1: Multiple QApplications

```python
# WRONG
for i in range(3):
    app = QApplication(sys.argv)  # Error on 2nd iteration
    window = MyWindow()
```

**Fix:**
```python
# CORRECT
app = QApplication(sys.argv)  # Once per process
windows = [MyWindow() for i in range(3)]
sys.exit(app.exec_())
```

---

### ❌ Mistake 2: Blocking Event Loop

```python
# WRONG - Freezes UI during robot I/O
class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        while True:
            pose = robot.get_pose()  # Blocks 5-10 ms, repeated → frozen UI
            self.update_plot(pose)
```

**Fix:**
```python
# CORRECT - Use QThread
class RobotWorker(QThread):
    pose_updated = pyqtSignal(tuple)
    def run(self):
        while True:
            pose = robot.get_pose()
            self.pose_updated.emit(pose)  # Doesn't block event loop

class MyWindow(QMainWindow):
    def __init__(self):
        self.worker = RobotWorker()
        self.worker.pose_updated.connect(self.update_plot)
        self.worker.start()
```

---

### ❌ Mistake 3: Not Cleaning Up Threads

```python
# WRONG - Thread keeps robot connection open
window = MyWindow()
# ... window closes, thread not stopped ...
# Robot still thinks it's connected, port still locked
```

**Fix:**
```python
# CORRECT
def closeEvent(self, event):
    self.worker.stop()
    self.worker.wait(timeout=2000)  # Wait for cleanup
    event.accept()
```

---

### ❌ Mistake 4: Queue Deadlock in Multiprocess

```python
# WRONG - Queue.put() blocks if queue full
def robot_process(queue):
    while True:
        pose = robot.get_pose()
        queue.put(pose)  # Blocks if queue full, can deadlock
```

**Fix:**
```python
# CORRECT - Use timeout
def robot_process(queue, stop_event):
    while not stop_event.is_set():
        pose = robot.get_pose()
        try:
            queue.put(pose, timeout=1)  # Don't block forever
        except:
            pass  # Queue full, skip this sample
```

---

## Summary Table

| Aspect | QThread | Multiprocess | Hybrid |
|--------|---------|-------------|--------|
| **Code lines** | ~100 | ~150 | ~130 |
| **Latency** | 50–100 ms | 100–300 ms | 50–100 ms |
| **CPU** | 5–8% (active) | 8–12% (active) | 5–10% (active) |
| **Memory** | +0–20 MB | +30–60 MB | +20–40 MB |
| **Responsiveness** | Excellent | Good | Excellent |
| **For heavy math** | ✗ GIL limits | ✓ True parallel | ✓ True parallel |
| **Complexity** | Low | Medium | Medium |
| **Recommended** | **90% of cases** | CPU-intensive | Rare |

---

## Further Reading

- `scripts/viz_2d_realtime.py` — QThread example
- `scripts/viz_3d_workspace.py` — QThread 3D
- `scripts/viz_3d_multiprocess.py` — Multiprocess example
- `scripts/viz_threading_comparison.py` — Live pattern comparison

Run with robot to see real performance characteristics!
