# Vispy Implementation Guide for Dobot Trajectory Visualization

## Quick Start (5 minutes)

### 1. Install Dependencies
```bash
pip install vispy PyQt5 numpy
```

### 2. Test Installation
```bash
python3 << 'EOF'
from vispy.scene import SceneCanvas
from vispy import app, visuals
import numpy as np

canvas = SceneCanvas(title='Test', size=(800, 600))
view = canvas.central_widget.add_view()

# Add a simple line
line = visuals.Line(pos=np.array([[0, 0, 0], [100, 100, 100]]))
view.add(line)

canvas.show()
app.run()
EOF
```

You should see a native window with a blue line. Close it to proceed.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Dobot Trajectory Visualization         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐          ┌──────────────────┐     │
│  │  Serial Thread   │          │   Qt Event Loop  │     │
│  │                  │  numpy   │  (Main Thread)   │     │
│  │  - Read pose     │ array───→│                  │     │
│  │  - Poll @ 30 Hz  │ updates  │  - Timer callback│     │
│  │  - No blocking   │◄─────────┤  - Render canvas │     │
│  │                  │          │  - Mouse/keyboard│     │
│  └──────────────────┘          └──────────────────┘     │
│                                         ↓                 │
│                              ┌──────────────────┐        │
│                              │  Vispy Canvas    │        │
│                              │  (Native Window) │        │
│                              │  - 1200x800 px   │        │
│                              │  - GL-rendered   │        │
│                              │  - 30+ Hz        │        │
│                              └──────────────────┘        │
│                                                          │
└─────────────────────────────────────────────────────────┘

Threading Model:
  - Serial thread: Reads from robot, updates numpy array
  - Main thread: Qt event loop + Vispy timer
  - Synchronization: Qt handles automatically (no locks needed!)
```

---

## Minimal Working Example (Robot Simulator)

This simulates a robot without hardware (useful for testing):

```python
#!/usr/bin/env python3
"""
Minimal Vispy visualization example with simulated robot.
Run this to verify everything works before connecting hardware.
"""

import numpy as np
import threading
import time
from vispy.scene import SceneCanvas
from vispy import app, visuals
from vispy.color import Color


def main():
    # === SETUP ===
    canvas = SceneCanvas(
        title='Dobot Trajectory (Simulated)',
        size=(1200, 800),
        bgcolor='white'
    )
    view = canvas.central_widget.add_view()
    view.camera = 'turntable'
    
    # State: shared between threads (numpy array is thread-safe for assignment)
    trajectory = np.array([[0, 0, 0]], dtype=np.float32)
    
    # Visualization elements
    trajectory_line = visuals.Line(
        pos=trajectory,
        color=Color(name='blue', alpha=0.8),
        width=2
    )
    view.add(trajectory_line)
    
    current_pos = visuals.Markers(
        pos=trajectory[-1:],
        size=15,
        face_color=Color(name='red')
    )
    view.add(current_pos)
    
    # === BACKGROUND THREAD: Simulate robot ===
    def robot_simulator():
        """Background thread: generates synthetic pose updates."""
        nonlocal trajectory
        
        t = 0
        while True:
            # Spiral motion (simulating moving robot)
            t += 0.02
            x = 100 * np.cos(t)
            y = 100 * np.sin(t)
            z = 50 + 20 * np.sin(t / 5)
            
            new_point = np.array([[x, y, z]], dtype=np.float32)
            trajectory = np.vstack([trajectory, new_point])
            
            # Limit history to 1000 points
            if len(trajectory) > 1000:
                trajectory = trajectory[-1000:]
            
            time.sleep(0.033)  # ~30 Hz
    
    # === MAIN THREAD: Qt event loop callback ===
    def update_visualization(event):
        """Called every 33 ms by Qt timer."""
        trajectory_line.set_data(pos=trajectory)
        current_pos.set_data(pos=trajectory[-1:])
    
    # Start timer
    timer = app.Timer(interval=0.033)  # 30 Hz = 33 ms
    timer.connect(update_visualization)
    timer.start()
    
    # Start background thread
    thread = threading.Thread(target=robot_simulator, daemon=True)
    thread.start()
    
    # === RUN ===
    canvas.show()
    print("Visualization running. Press Ctrl+C to exit.")
    app.run()


if __name__ == '__main__':
    main()
```

**Run it:**
```bash
cd /path/to/scripts
python3 vispy_example.py
```

You should see:
- Native window (1200x800)
- Blue spiral trajectory
- Red dot at current position
- Mouse rotation (click + drag)
- Runs smoothly at 30 Hz

---

## Real Hardware Integration (Dobot)

### Pattern 1: Simple Position Polling

```python
#!/usr/bin/env python3
"""
Real Dobot visualization: simple polling pattern.
Connects to Dobot, polls get_pose(), visualizes trajectory.
"""

import numpy as np
import threading
import time
from vispy.scene import SceneCanvas
from vispy import app, visuals
from vispy.color import Color

# Import robot control
import sys
sys.path.insert(0, '/path/to/scripts')
from utils import find_port, READY_POSE, SAFE_BOUNDS

try:
    from pydobotplus import dobot
except ImportError:
    print("ERROR: Install pydobotplus: pip install pydobotplus")
    sys.exit(1)


def main():
    # Connect to robot
    port = find_port()
    if not port:
        print("ERROR: Could not find Dobot on serial port")
        sys.exit(1)
    
    print(f"Connecting to Dobot on {port}...")
    robot = dobot(port=port)
    print("✓ Connected")
    
    # Canvas
    canvas = SceneCanvas(
        title=f'Dobot Trajectory - {port}',
        size=(1200, 800),
        bgcolor='white'
    )
    view = canvas.central_widget.add_view()
    view.camera = 'turntable'
    
    # State
    trajectory = np.array([[0, 0, 0]], dtype=np.float32)
    
    # Visuals
    trajectory_line = visuals.Line(
        pos=trajectory,
        color=Color(name='blue', alpha=0.8),
        width=2
    )
    view.add(trajectory_line)
    
    position_marker = visuals.Markers(
        pos=trajectory[-1:],
        size=15,
        face_color=Color(name='red')
    )
    view.add(position_marker)
    
    # Safety bounds visualization (optional)
    bounds = SAFE_BOUNDS
    bounds_marker = visuals.Markers(
        pos=np.array([
            [bounds['x'][0], bounds['y'][0], bounds['z'][0]],
            [bounds['x'][1], bounds['y'][1], bounds['z'][1]],
        ], dtype=np.float32),
        size=8,
        face_color=Color(name='green', alpha=0.5)
    )
    view.add(bounds_marker)
    
    # === BACKGROUND THREAD: Read from robot ===
    def robot_reader():
        """Background thread: continuously poll robot position."""
        nonlocal trajectory
        
        while True:
            try:
                # Get current pose (x, y, z, r)
                x, y, z, r = robot.get_pose()
                
                new_point = np.array([[x, y, z]], dtype=np.float32)
                trajectory = np.vstack([trajectory, new_point])
                
                # Keep last 2000 points
                if len(trajectory) > 2000:
                    trajectory = trajectory[-2000:]
            
            except Exception as e:
                print(f"Robot read error: {e}")
            
            time.sleep(0.033)  # Don't spam; ~30 Hz
    
    # === MAIN THREAD: Update visualization ===
    def update_visualization(event):
        """Called every 33 ms by Qt timer."""
        trajectory_line.set_data(pos=trajectory)
        position_marker.set_data(pos=trajectory[-1:])
    
    # Start
    timer = app.Timer(interval=0.033)
    timer.connect(update_visualization)
    timer.start()
    
    thread = threading.Thread(target=robot_reader, daemon=True)
    thread.start()
    
    print(f"Visualization live at 30 Hz")
    print(f"Press Ctrl+C to exit")
    
    canvas.show()
    app.run()
    
    # Cleanup
    robot.close()
    print("✓ Closed robot connection")


if __name__ == '__main__':
    main()
```

### Pattern 2: Command Execution + Live Visualization

```python
#!/usr/bin/env python3
"""
Dobot visualization while robot executes motion commands.
Demonstrates concurrent visualization + control.
"""

import numpy as np
import threading
import time
from vispy.scene import SceneCanvas
from vispy import app, visuals
from vispy.color import Color
from pydobotplus import dobot
from utils import find_port, safe_move, READY_POSE


def main():
    # Setup
    port = find_port()
    robot = dobot(port=port)
    robot.move_to(*READY_POSE, wait=True)
    
    canvas = SceneCanvas(title='Dobot Motion + Visualization', size=(1200, 800))
    view = canvas.central_widget.add_view()
    
    trajectory = np.array([[0, 0, 0]], dtype=np.float32)
    line = visuals.Line(pos=trajectory, color='blue', width=2)
    view.add(line)
    
    # Background thread: Reader
    def read_position():
        nonlocal trajectory
        while True:
            x, y, z, r = robot.get_pose()
            trajectory = np.vstack([trajectory, [[x, y, z]]])
            if len(trajectory) > 2000:
                trajectory = trajectory[-2000:]
            time.sleep(0.033)
    
    # Update callback
    def update_viz(event):
        line.set_data(pos=trajectory)
    
    timer = app.Timer(interval=0.033)
    timer.connect(update_viz)
    timer.start()
    
    reader_thread = threading.Thread(target=read_position, daemon=True)
    reader_thread.start()
    
    # === EXECUTE MOTION WHILE VISUALIZING ===
    def execute_motion():
        """Main thread: send motion commands."""
        waypoints = [
            (200, 0, 100, 0),
            (250, -100, 80, 0),
            (200, 100, 120, 0),
            (150, 0, 100, 0),
            (200, 0, 100, 0),  # Back to start
        ]
        
        for i, waypoint in enumerate(waypoints):
            print(f"Moving to waypoint {i+1}/{len(waypoints)}: {waypoint}")
            safe_move(robot, *waypoint, mode=0)  # MODE_PTP
            time.sleep(0.5)  # Brief pause between moves
        
        print("Motion sequence complete")
    
    # Start motion in background
    motion_thread = threading.Thread(target=execute_motion, daemon=True)
    motion_thread.start()
    
    canvas.show()
    app.run()
    
    robot.close()


if __name__ == '__main__':
    main()
```

---

## Advanced Features

### Add Joint Markers

```python
def add_joint_markers(view, trajectory):
    """Add markers at every 10th position to show joint locations."""
    sparse_points = trajectory[::10]  # Every 10th point
    
    markers = visuals.Markers(
        pos=sparse_points,
        size=8,
        face_color='red',
        edge_color='darkred',
        edge_width=1
    )
    view.add(markers)
    
    return markers
```

### Add Bounding Box

```python
def add_bounding_box(view, bounds):
    """Draw workspace bounding box."""
    corners = np.array([
        [bounds['x'][0], bounds['y'][0], bounds['z'][0]],
        [bounds['x'][1], bounds['y'][0], bounds['z'][0]],
        [bounds['x'][1], bounds['y'][1], bounds['z'][0]],
        [bounds['x'][0], bounds['y'][1], bounds['z'][0]],
        [bounds['x'][0], bounds['y'][0], bounds['z'][1]],
        [bounds['x'][1], bounds['y'][0], bounds['z'][1]],
        [bounds['x'][1], bounds['y'][1], bounds['z'][1]],
        [bounds['x'][0], bounds['y'][1], bounds['z'][1]],
    ], dtype=np.float32)
    
    edges = np.array([
        [0, 1], [1, 2], [2, 3], [3, 0],  # Bottom
        [4, 5], [5, 6], [6, 7], [7, 4],  # Top
        [0, 4], [1, 5], [2, 6], [3, 7],  # Vertical
    ])
    
    for edge in edges:
        line = visuals.Line(pos=corners[edge], color='gray', width=1)
        view.add(line)
```

### Add 3D Text Labels

```python
from vispy.scene import visuals

def add_text_label(view, pos, text):
    """Add 3D text at position."""
    text_obj = visuals.Text(
        text,
        pos=pos,
        font_size=12,
        color='black'
    )
    view.add(text_obj)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No module named vispy" | `pip install vispy` |
| "No module named PyQt5" | `pip install PyQt5` |
| Window doesn't appear | Check if running in headless environment |
| Visualization very slow | Reduce trajectory history length |
| Robot thread not updating | Ensure `robot.get_pose()` is being called |
| Frozen window | Press Ctrl+C in terminal |

---

## Performance Tips

1. **Trajectory history:** Keep ~1000-2000 points max (older points get deleted)
2. **Update interval:** 33 ms (30 Hz) is good balance
3. **Line width:** Use reasonable width (2-3 pixels)
4. **Marker size:** 10-20 pixels works well
5. **Camera:** Turntable is responsive; avoid complex shaders

---

## Next Steps

1. ✓ Install Vispy + PyQt5
2. ✓ Test with simulator example
3. Create `scripts/16_visualize_trajectory.py` (real robot version)
4. Test with actual Dobot
5. Document in `GUIDE.md`
6. Optional: Add features (waypoint markers, bounding box, etc.)

---

## Reference Code Snippets

### Get Current Pose (Thread-Safe)
```python
x, y, z, r = robot.get_pose()
# Returns (x, y, z, r) in mm/degrees
```

### Numpy Array Tricks
```python
# Add point to trajectory
trajectory = np.vstack([trajectory, [[x, y, z]]])

# Limit to last N points
if len(trajectory) > 2000:
    trajectory = trajectory[-2000:]

# Slice every Nth point
sparse = trajectory[::10]

# Clear trajectory
trajectory = np.array([[0, 0, 0]], dtype=np.float32)
```

### Vispy Colors
```python
from vispy.color import Color

Color(name='blue')
Color(name='red', alpha=0.5)  # 50% transparent
Color([1.0, 0.0, 0.0])  # RGB tuple
Color([1.0, 0.0, 0.0, 0.5])  # RGBA
```

---

## Resources

- Vispy docs: http://vispy.org/
- Vispy gallery: http://vispy.org/gallery.html
- PyQt5 docs: https://www.riverbankcomputing.com/software/pyqt/
- Dobot/pydobotplus: See main CLAUDE.md

---

**Document Version:** 1.0  
**Date:** 2025-03-09  
**Status:** Ready for production  
**Maintained By:** ME403 TA Team
