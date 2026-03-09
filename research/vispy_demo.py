#!/usr/bin/env python3
"""
Vispy real-time trajectory visualization example.
Demonstrates:
  - Native window (no Jupyter)
  - 30 Hz update rate
  - Background thread for data source
  - Thread-safe Qt integration
  - Minimal boilerplate
"""

import numpy as np
import threading
import time
from queue import Queue
from vispy.scene import SceneCanvas
from vispy import app, visuals
from vispy.color import Color


def demo_synthetic_robot_path():
    """Simulate a robot tracing a 3D spiral path."""
    
    # Canvas setup (native window)
    canvas = SceneCanvas(
        title='Robot Arm Trajectory (Vispy Demo)',
        size=(1200, 800),
        bgcolor='white'
    )
    view = canvas.central_widget.add_view()
    view.camera = 'turntable'  # Allows mouse rotation
    
    # Visualization elements
    trajectory_points = np.array([[0, 0, 0]], dtype=np.float32)
    trajectory_line = visuals.Line(
        pos=trajectory_points,
        color=Color(name='blue', alpha=0.7),
        width=2
    )
    view.add(trajectory_line)
    
    # Current position marker
    position_marker = visuals.Markers(
        pos=trajectory_points[-1:],
        size=15,
        face_color=Color(name='red'),
        edge_color=Color(name='darkred'),
        edge_width=2
    )
    view.add(position_marker)
    
    # Origin marker (for reference)
    origin = visuals.Markers(
        pos=np.array([[0, 0, 0]], dtype=np.float32),
        size=10,
        face_color=Color(name='green'),
        edge_width=0
    )
    view.add(origin)
    
    # Axes for reference
    axes = visuals.XYZAxis(parent=view.scene)
    
    # Data queue for thread-safe updates
    data_queue = Queue(maxsize=1)
    
    def synthetic_robot_reader():
        """
        Background thread: simulates robot position updates.
        In real use, this would read from serial port.
        """
        t = 0
        while True:
            # Simulate spiral motion
            t += 0.05
            x = 100 * np.cos(t)
            y = 100 * np.sin(t)
            z = 50 * np.sin(t / 10)  # Slow vertical oscillation
            
            try:
                data_queue.put_nowait({
                    'x': x,
                    'y': y,
                    'z': z,
                    'timestamp': time.time()
                })
            except:
                pass  # Queue full, drop update
            
            time.sleep(0.033)  # ~30 Hz
    
    def update_visualization(event):
        """
        Main thread: update visualization.
        Called by Qt timer every ~33 ms (30 Hz).
        """
        nonlocal trajectory_points
        
        try:
            pose = data_queue.get_nowait()
            new_point = np.array(
                [[pose['x'], pose['y'], pose['z']]],
                dtype=np.float32
            )
            trajectory_points = np.vstack([trajectory_points, new_point])
            
            # Update visuals
            trajectory_line.set_data(pos=trajectory_points)
            position_marker.set_data(pos=trajectory_points[-1:])
            
            # Limit history to last 500 points (for performance)
            if len(trajectory_points) > 500:
                trajectory_points = trajectory_points[-500:]
                trajectory_line.set_data(pos=trajectory_points)
        
        except:
            pass  # Queue empty
    
    # Setup timer (Qt event loop)
    timer = app.Timer(interval=0.033)  # ~30 Hz
    timer.connect(update_visualization)
    timer.start()
    
    # Start background thread
    thread = threading.Thread(target=synthetic_robot_reader, daemon=True)
    thread.start()
    
    # Show and run
    canvas.show()
    app.run()
    
    print("Demo completed")


def demo_static_arm_visualization():
    """
    Simpler demo: visualize static robot arm configuration.
    Shows how to draw cylinders and spheres using Vispy meshes.
    """
    
    canvas = SceneCanvas(
        title='Robot Arm Configuration (Vispy)',
        size=(1200, 800),
        bgcolor='white'
    )
    view = canvas.central_widget.add_view()
    view.camera = 'turntable'
    
    # For this demo, use simpler visualization approach
    # (Vispy meshes are more complex than VPython primitives)
    
    # Joint positions (example: 4-DOF arm)
    joints = np.array([
        [0, 0, 0],       # Base
        [50, 0, 50],     # Joint 1
        [80, 20, 80],    # Joint 2
        [100, 40, 100],  # Joint 3 (end effector)
    ], dtype=np.float32)
    
    # Draw arm skeleton
    skeleton = visuals.Line(
        pos=joints,
        color=Color(name='steelblue'),
        width=3
    )
    view.add(skeleton)
    
    # Draw joints
    joint_markers = visuals.Markers(
        pos=joints,
        size=15,
        face_color=Color(name='red'),
        edge_width=1,
        edge_color=Color(name='darkred')
    )
    view.add(joint_markers)
    
    # Draw end effector differently
    effector = visuals.Markers(
        pos=joints[-1:],
        size=25,
        face_color=Color(name='gold'),
        symbol='diamond'
    )
    view.add(effector)
    
    # Axes
    axes = visuals.XYZAxis(parent=view.scene)
    
    # Add some text
    text = visuals.Text('Robot Arm - Static Configuration', pos=(0, 100, 0))
    view.add(text)
    
    canvas.show()
    app.run()


def demo_real_robot_template():
    """
    Template for real robot integration.
    Shows where serial I/O would go.
    """
    
    template_code = '''
from vispy.scene import SceneCanvas
from vispy import app, visuals
import numpy as np
import threading
from utils import find_port, safe_move
from pydobotplus import dobot

# Initialize robot
port = find_port()
robot = dobot(port=port)

# Canvas
canvas = SceneCanvas(title='Dobot Live Trajectory', size=(1200, 800))
view = canvas.central_widget.add_view()

# State
trajectory = np.array([[0, 0, 0]], dtype=np.float32)
line = visuals.Line(pos=trajectory, color='blue', width=2)
view.add(line)

def update_frame(event):
    """Called every 33 ms by Qt timer."""
    line.set_data(pos=trajectory)

def read_robot():
    """Background thread: poll robot position."""
    global trajectory
    while True:
        x, y, z, r = robot.get_pose()
        trajectory = np.vstack([trajectory, [[x, y, z]]])
        time.sleep(0.033)  # Don't spam

# Start
timer = app.Timer(interval=0.033)
timer.connect(update_frame)
timer.start()

thread = threading.Thread(target=read_robot, daemon=True)
thread.start()

canvas.show()
app.run()
    '''
    
    print("Real robot template:")
    print(template_code)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        demo = sys.argv[1]
    else:
        demo = 'synthetic'
    
    if demo == 'synthetic':
        print("Running synthetic robot path demo (30 Hz, 3D spiral)...")
        print("Press 'Ctrl+C' to exit")
        demo_synthetic_robot_path()
    
    elif demo == 'static':
        print("Running static arm visualization demo...")
        demo_static_arm_visualization()
    
    elif demo == 'template':
        demo_real_robot_template()
    
    else:
        print(f"Unknown demo: {demo}")
        print("Options: synthetic, static, template")
