#!/usr/bin/env python3
"""
3D workspace visualization using multiprocessing for robot control.
Useful for isolating robot I/O from visualization thread.

Runs robot in separate process, communicates via Queue.
Visualization in main Qt thread polls queue at 30 Hz.

Requires: PyQt5, pyqtgraph, numpy
Install: pip install PyQt5 pyqtgraph numpy
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
    """
    Runs robot control in separate process.
    Continuously reads pose and puts it in queue.
    Stops when stop_event is set.
    """
    try:
        from pydobotplus import Dobot
        
        port = find_port()
        if not port:
            print("Robot not found")
            return
        
        robot = Dobot(port=port, verbose=False)
        robot.wait_for_home()
        
        print(f"[Process] Robot connected on {port}")
        
        while not stop_event.is_set():
            try:
                pose = robot.get_pose()
                # Non-blocking put with timeout to avoid deadlock
                pose_queue.put(pose, timeout=0.5)
            except:
                pass
            
            time.sleep(0.05)  # 20 Hz sampling
        
        print("[Process] Closing robot...")
        robot.close()
    except Exception as e:
        print(f"Robot process error: {e}")

class RealTimeViz3DMultiprocess(QMainWindow):
    """3D workspace visualization with multiprocessing"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dobot 3D (Multiprocessing)")
        self.setGeometry(100, 100, 1000, 800)
        
        # Setup 3D view
        self.view = GLViewWidget()
        self.view.opts['distance'] = 400
        self.view.setCameraPosition(distance=400, elevation=30, azimuth=-45)
        
        # Extract workspace bounds
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
        grid = GLGridItem(
            size=(size_x * 2, size_y * 2, 1),
            color=(0.5, 0.5, 0.5, 0.5)
        )
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
        
        # Status label
        self.setStatusBar(self)
        self.statusBar().showMessage("Starting robot process...")
        
        # Multiprocessing setup
        self.pose_queue = mp.Queue(maxsize=2)
        self.stop_event = mp.Event()
        self.process = mp.Process(
            target=robot_control_process,
            args=(self.pose_queue, self.stop_event),
            daemon=False
        )
        self.process.start()
        
        # Poll queue at 30 Hz
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_queue)
        self.timer.start(33)
        
        print("[Main] Visualization started, polling robot queue...")
    
    def poll_queue(self):
        """Poll pose queue and update visualization"""
        try:
            # Non-blocking get to process all queued poses
            while True:
                pose = self.pose_queue.get_nowait()
                x, y, z, r = pose
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
                    f"History: {len(self.trajectory)} points | "
                    f"Process alive: {self.process.is_alive()}"
                )
        except:
            # Queue empty, just update display
            pass
    
    def closeEvent(self, event):
        """Cleanup on window close"""
        print("[Main] Closing visualization...")
        
        self.timer.stop()
        self.stop_event.set()
        
        # Wait for process to exit gracefully
        self.process.join(timeout=2)
        
        if self.process.is_alive():
            print("[Main] Process didn't exit, terminating...")
            self.process.terminate()
            self.process.join(timeout=1)
        
        print("[Main] Cleanup complete")
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
    
    # Required for multiprocessing on some platforms
    mp.set_start_method('spawn', force=True)
    
    app = QApplication(sys.argv)
    window = RealTimeViz3DMultiprocess()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
