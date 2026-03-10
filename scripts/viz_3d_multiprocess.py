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
from queue import Empty, Full
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer
from pyqtgraph.opengl import (
    GLViewWidget, GLBoxItem, GLGridItem, GLLinePlotItem,
    GLScatterPlotItem, GLAxisItem
)
import numpy as np

from utils import HARD_LIMITS, SAFE_BOUNDS, find_port, unpack_pose

def robot_control_process(port, pose_queue, stop_event):
    """
    Runs robot control in separate process.
    Continuously reads pose and puts it in queue.
    Stops when stop_event is set.
    """
    robot = None
    try:
        from pydobotplus import Dobot

        robot = Dobot(port=port)
        print(f"[Process] Robot connected on {port}")
        while not stop_event.is_set():
            try:
                pose_queue.put(unpack_pose(robot.get_pose()), timeout=0.2)
            except Full:
                pass
            except Exception as exc:
                print(f"[Process] Pose read failed: {exc}")
                time.sleep(0.1)
            time.sleep(0.05)  # 20 Hz sampling
    except Exception as exc:
        print(f"Robot process error: {exc}")
    finally:
        if robot is not None:
            print("[Process] Closing robot...")
            try:
                robot.close()
            except Exception:
                pass

class RealTimeViz3DMultiprocess(QMainWindow):
    """3D workspace visualization with multiprocessing"""
    
    def __init__(self, port):
        super().__init__()
        self.port = port
        self.setWindowTitle("Dobot 3D (Multiprocessing)")
        self.setGeometry(100, 100, 1000, 800)
        
        # Setup 3D view
        self.view = GLViewWidget()
        self.view.opts['distance'] = 400
        self.view.setCameraPosition(distance=400, elevation=30, azimuth=-45)
        
        # Extract workspace bounds
        x_min, x_max = HARD_LIMITS['x']
        y_min, y_max = HARD_LIMITS['y']
        z_min, z_max = HARD_LIMITS['z']
        
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
        self.statusBar().showMessage("Starting robot process...")
        
        # Multiprocessing setup
        self.pose_queue = mp.Queue(maxsize=2)
        self.stop_event = mp.Event()
        self.process = mp.Process(
            target=robot_control_process,
            args=(self.port, self.pose_queue, self.stop_event),
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
                    f"History: {len(self.trajectory)} points | "
                    f"Process alive: {self.process.is_alive()}"
                )
        except Empty:
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
    port = find_port()
    if not port:
        print("Robot not found. Run 01_find_port.py first.")
        sys.exit(1)

    print(f"Connecting to robot on {port}...")
    window = RealTimeViz3DMultiprocess(port)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
