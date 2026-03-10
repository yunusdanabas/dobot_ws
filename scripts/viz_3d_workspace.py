#!/usr/bin/env python3
"""
3D workspace visualization with end-effector trajectory.
Shows bounding box, reference grid, axes, and live trajectory.
Uses QThread for robot control.

Requires: PyQt5, pyqtgraph, numpy
Install: pip install PyQt5 pyqtgraph numpy
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from pyqtgraph.opengl import (
    GLViewWidget, GLBoxItem, GLGridItem, GLLinePlotItem,
    GLScatterPlotItem, GLAxisItem
)
import numpy as np

from pyqtgraph_helpers import PosePollingThread
from utils import HARD_LIMITS, SAFE_BOUNDS, find_port

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
        
        # Extract workspace bounds from utils.py
        x_min, x_max = HARD_LIMITS['x']
        y_min, y_max = HARD_LIMITS['y']
        z_min, z_max = HARD_LIMITS['z']
        
        center_x = (x_min + x_max) / 2
        center_y = (y_min + y_max) / 2
        center_z = (z_min + z_max) / 2
        
        size_x = x_max - x_min
        size_y = y_max - y_min
        size_z = z_max - z_min
        
        # Workspace bounding box (red, semi-transparent)
        workspace_box = GLBoxItem(
            size=(size_x, size_y, size_z),
            color=(1, 0, 0, 0.15)
        )
        workspace_box.translate(center_x, center_y, center_z)
        self.view.addItem(workspace_box)

        safe_box = GLBoxItem(
            size=(
                SAFE_BOUNDS['x'][1] - SAFE_BOUNDS['x'][0],
                SAFE_BOUNDS['y'][1] - SAFE_BOUNDS['y'][0],
                SAFE_BOUNDS['z'][1] - SAFE_BOUNDS['z'][0],
            ),
            color=(1, 1, 0, 0.08)
        )
        safe_box.translate(
            (SAFE_BOUNDS['x'][0] + SAFE_BOUNDS['x'][1]) / 2,
            (SAFE_BOUNDS['y'][0] + SAFE_BOUNDS['y'][1]) / 2,
            (SAFE_BOUNDS['z'][0] + SAFE_BOUNDS['z'][1]) / 2,
        )
        self.view.addItem(safe_box)
        
        # Reference grid (XY plane at Z_min)
        grid = GLGridItem(
            size=(size_x * 2, size_y * 2, 1),
            color=(0.5, 0.5, 0.5, 0.5)
        )
        grid.translate(center_x, center_y, z_min)
        self.view.addItem(grid)
        
        # Reference axes
        axis = GLAxisItem()
        axis.setSize(100, 100, 100)
        self.view.addItem(axis)
        
        # Trajectory line (red)
        self.trajectory_line = GLLinePlotItem(
            pos=np.array([[0, 0, 0]]),
            color=(1, 0, 0, 1),
            width=2,
            antialias=False
        )
        self.view.addItem(self.trajectory_line)
        
        # End-effector position (green scatter)
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
        
        # Status label
        self.statusBar().showMessage("Connecting to robot...")
        
        # Start robot thread
        self.worker = PosePollingThread(port)
        self.worker.pose_updated.connect(self.on_pose_update)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
    
    def on_pose_update(self, pose):
        """Called when robot sends new pose"""
        x, y, z, r, *_ = pose
        point = np.array([[x, y, z]])
        
        # Add to trajectory with rolling buffer
        if len(self.trajectory) >= self.max_history:
            self.trajectory = self.trajectory[1:]
        
        self.trajectory = np.vstack([self.trajectory, point])
        
        # Update visualization
        self.trajectory_line.setData(pos=self.trajectory)
        self.ee_scatter.setData(pos=point)
        
        # Update status
        self.statusBar().showMessage(
            f"Pose: X={x:.1f}, Y={y:.1f}, Z={z:.1f}, R={r:.1f} | "
            f"History: {len(self.trajectory)} points"
        )
    
    def on_error(self, error_msg):
        """Handle errors from robot thread"""
        self.statusBar().showMessage(f"Error: {error_msg}")
        print(f"Robot error: {error_msg}")
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        self.worker.stop()
        self.worker.wait(timeout=2000)
        event.accept()

def main():
    # Check for dependencies
    try:
        import pyqtgraph
        import PyQt5
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Install with: pip install PyQt5 pyqtgraph numpy")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    
    port = find_port()
    if not port:
        print("Robot not found. Run 01_find_port.py first.")
        sys.exit(1)
    
    print(f"Connecting to robot on {port}...")
    window = RealTimeViz3D(port)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
