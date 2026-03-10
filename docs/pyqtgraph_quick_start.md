# PyQtGraph Quick Start for Dobot Visualization

## Installation (2 minutes)

```bash
# Add to your environment (mamba/venv already created)
pip install PyQt5 pyqtgraph numpy

# Or update requirements.txt and install all at once
pip install -r requirements.txt
```

## Three Minimal Examples

### 1. 2D Real-Time Trajectory (QThread)

**File:** `scripts/viz_2d_realtime.py`

```bash
python scripts/viz_2d_realtime.py
```

- Plots end-effector X-Y position in real-time
- Updates at ~20 Hz
- Red line = trajectory history
- Green circle = current position
- Uses QThread to keep Qt event loop responsive
- Memory-bounded (max 1000 points)

**What you see:**
- Live trajectory traced on 2D plot
- Workspace bounds shown as semi-transparent region
- FPS and position in status bar

---

### 2. 3D Workspace with Trajectory (QThread)

**File:** `scripts/viz_3d_workspace.py`

```bash
python scripts/viz_3d_workspace.py
```

- Full 3D workspace visualization
- Workspace bounding box (red, 130×320×140 mm)
- Reference grid at workspace floor
- X-Y-Z axes for orientation
- Red trajectory line
- Green dot for end-effector
- Uses QThread

**Camera controls:**
- Drag with mouse to rotate
- Scroll wheel to zoom
- Right-click drag to pan

---

### 3. 3D with Multiprocessing

**File:** `scripts/viz_3d_multiprocess.py`

```bash
python scripts/viz_3d_multiprocess.py
```

- Same 3D visualization as example 2
- **Robot control runs in separate process**
- Qt visualization in main thread polls queue
- No blocking serial I/O in event loop
- Cleaner separation of concerns
- Slightly higher latency but more robust

**When to use:**
- Heavy post-processing of robot data
- CPU-intensive trajectory analysis
- Isolating robot faults from UI

---

## Update Rates

| Pattern        | Sustainable Rate | Notes                              |
|----------------|------------------|---------------------------------------|
| 2D PlotWidget  | 10–30 Hz         | Typical Qt vsync limit (~60 Hz max) |
| 3D GLViewWidget| 20–30 Hz         | OpenGL overhead slightly higher    |
| Queue polling  | 30+ Hz           | Independent of robot sample rate   |

**Tuning example:**

```python
# In RobotWorker.run():
time.sleep(0.05)   # 20 Hz (50 ms)
time.sleep(0.033)  # 30 Hz (33 ms) — faster, higher CPU
time.sleep(0.1)    # 10 Hz (100 ms) — slower, lower CPU
```

---

## Architecture Patterns

### Pattern A: QThread (Recommended)

```python
# Robot runs in background QThread
# Qt event loop in main thread
# Data flows via pyqtSignal

class RobotWorker(QThread):
    pose_updated = pyqtSignal(tuple)  # Emits (x, y, z, r)
    
    def run(self):
        while self.running:
            pose = robot.get_pose()
            self.pose_updated.emit(pose)  # Thread-safe signal

# Main window connects signal to slot
window.worker.pose_updated.connect(window.on_pose_update)
```

**Pros:** Shared memory, simple, fast, Qt-native  
**Cons:** GIL limits CPU-heavy work

---

### Pattern B: Multiprocessing

```python
# Robot runs in separate OS process
# Qt runs in main process
# Data flows via Queue

def robot_process(pose_queue, stop_event):
    while not stop_event.is_set():
        pose = robot.get_pose()
        pose_queue.put(pose, timeout=1)

# Main thread polls queue
timer = QTimer()
timer.timeout.connect(lambda: poll_queue(pose_queue))
timer.start(33)  # 30 Hz polling
```

**Pros:** True parallelism, process isolation, no GIL  
**Cons:** Higher overhead, serialization cost, IPC latency

---

## Workspace Bounds Reference

```python
# From utils.py
SAFE_BOUNDS = {
    "x": (120, 315),    # mm, workspace X depth
    "y": (-158, 158),   # mm, workspace Y (left-right)
    "z": (5, 155),      # mm, workspace Z (height)
    "r": (-90, 90)      # degrees, wrist rotation
}

# Derived for 3D box
workspace_center = (217.5, 0, 80)    # mm
workspace_size = (195, 316, 150)     # (X, Y, Z) extent
```

Use these to set PlotWidget ranges or GLBoxItem positioning.

---

## Common Issues & Fixes

### Plot not updating

**Cause:** Event loop blocked by robot I/O

**Fix:** Use QThread
```python
worker = RobotWorker(port)
worker.pose_updated.connect(self.on_pose_update)
worker.start()
```

---

### "QApplication already exists"

**Cause:** Multiple QApplication instances in same process

**Fix:** Create only ONE QApplication before creating windows
```python
app = QApplication(sys.argv)  # Once per process
window = MyWindow()
window.show()
sys.exit(app.exec_())
```

---

### Serial port blocked

**Cause:** Another process owns the port (DobotStudio, previous script)

**Fix:** Kill process or disconnect
```bash
# Find process holding port
lsof /dev/ttyUSB0

# Or restart robot
sudo systemctl restart udev  # Linux
```

---

### High CPU usage / memory leak

**Cause:** Unbounded trajectory history

**Fix:** Use rolling buffer
```python
if len(self.trajectory) >= self.max_history:
    self.trajectory = self.trajectory[1:]  # Drop oldest
self.trajectory = np.vstack([self.trajectory, new_point])
```

---

### 3D view very slow

**Cause:** Too many trajectory points

**Fix:** Reduce history or downsample
```python
self.max_history = 500  # Not 5000
# Or store every Nth point
if len(self.trajectory) % 5 == 0:
    self.trajectory.append(pose)
```

---

## Performance Tips

1. **Disable antialiasing for 2D plots:**
   ```python
   curve = plot.plot(pen='r', antialias=False)
   ```

2. **Use `setData()` not `addPoints()`:**
   ```python
   # Fast: replaces entire dataset
   curve.setData(xs, ys)
   
   # Slow: appends to dataset
   curve.addPoints(x, y)
   ```

3. **Pre-allocate NumPy arrays:**
   ```python
   trajectory = np.zeros((0, 3))  # Shape (N, 3)
   trajectory = np.vstack([trajectory, point])
   ```

4. **Limit Qt update rate:**
   ```python
   # Update visualization every 33 ms (~30 Hz)
   # Don't update faster than you can see
   timer.start(33)  # milliseconds
   ```

5. **Use daemon threads carefully:**
   ```python
   # Good: worker thread cleaned up on exit
   worker = RobotWorker(port)
   worker.start()
   
   # Bad: daemon process might terminate abruptly
   proc = mp.Process(target=..., daemon=True)
   ```

---

## Testing Your Setup

```bash
# 1. Check dependencies
python -c "import PyQt5; import pyqtgraph; print('OK')"

# 2. Find robot
python scripts/01_find_port.py

# 3. Test 2D visualization
python scripts/viz_2d_realtime.py

# 4. Run with robot connected
# Ensure DobotStudio is closed
python scripts/viz_2d_realtime.py
```

---

## References

- **pyqtgraph:** https://www.pyqtgraph.org/
- **PyQt5 signals/slots:** https://www.riverbankcomputing.com/static/Docs/PyQt5/signals_slots.html
- **Threading in Qt:** https://doc.qt.io/qt-5/qthread.html
- **Multiprocessing:** https://docs.python.org/3/library/multiprocessing.html

---

## Next Steps

1. **Run example 1** (`viz_2d_realtime.py`) to verify setup
2. **Explore example 2** (`viz_3d_workspace.py`) for better visualization
3. **For heavy computation**, try example 3 with multiprocessing
4. **Extend** with your own data (forces, velocities, sensor streams)

These examples are standalone visualizers. For motion + visualization in one
process, use the built-in `scripts/viz.py` integration used by scripts 07–09 and 12–13.

---

## FAQ

**Q: Can I run visualization on a different machine?**  
A: Yes, if you pipe pose data over network (TCP/UDP). Use Queue-like pattern with socket communication.

**Q: How do I record trajectories?**  
A: Store `self.trajectory` array and save with NumPy:
```python
np.save('trajectory.npy', self.trajectory)
```

**Q: Can I add force/torque data?**  
A: Yes, extend pose tuple in signals:
```python
self.pose_updated.emit((x, y, z, r, fx, fy, fz))
```

**Q: Is pyqtgraph production-ready?**  
A: Yes, used in scientific/industrial software. Active development, good documentation.

**Q: PySide vs PyQt5?**  
A: Both work with pyqtgraph. PyQt5 is official. PySide6 is Qt6-native. Stick with PyQt5 for stability.
