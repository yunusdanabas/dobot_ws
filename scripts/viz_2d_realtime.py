#!/usr/bin/env python3
"""
2D real-time trajectory visualization using pyqtgraph.
Runs robot control in QThread, visualization in main thread.
Update rate: 10–30 Hz sustainable.

Requires: PyQt5, pyqtgraph, numpy
Install: pip install PyQt5 pyqtgraph numpy
"""

import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QThread, pyqtSignal
import pyqtgraph as pg
import numpy as np

from utils import find_port

class RobotWorker(QThread):
    """Background thread for robot control"""
    pose_updated = pyqtSignal(tuple)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, port):
        super().__init__()
        self.running = True
        self.port = port
        self.robot = None
    
    def run(self):
        try:
            from pydobotplus import Dobot
            self.robot = Dobot(port=self.port, verbose=False)
            self.robot.wait_for_home()
            
            while self.running:
                pose = self.robot.get_pose()
                self.pose_updated.emit(pose)
                time.sleep(0.05)  # 20 Hz
        except Exception as e:
            self.error_occurred.emit(str(e))
    
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
        
        # Workspace bounds reference (mm)
        self.plot_widget.setXRange(140, 290)
        self.plot_widget.setYRange(-170, 170)
        
        # Add workspace region visualization
        workspace_region_h = pg.LinearRegionItem(
            values=[150, 280],
            orientation='vertical',
            brush=pg.mkBrush(255, 0, 0, 20),
            movable=False
        )
        self.plot_widget.addItem(workspace_region_h)
        
        # Trajectory curve (red line)
        self.trajectory_curve = self.plot_widget.plot(
            pen=pg.mkPen('r', width=2),
            name='Trajectory'
        )
        
        # Current position (green circle)
        self.current_point = self.plot_widget.plot(
            pen=None,
            symbol='o',
            symbolSize=10,
            symbolBrush=pg.mkBrush('g'),
            name='Current Position'
        )
        
        # Layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.plot_widget)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # Trajectory storage
        self.trajectory = []
        self.max_history = 1000
        
        # Status label
        self.setStatusBar(self)
        self.statusBar().showMessage("Connecting to robot...")
        
        # Start robot thread
        self.worker = RobotWorker(port)
        self.worker.pose_updated.connect(self.on_pose_update)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
    
    def on_pose_update(self, pose):
        """Called when robot sends new pose"""
        x, y, z, r = pose
        self.trajectory.append((x, y))
        
        if len(self.trajectory) > self.max_history:
            self.trajectory.pop(0)
        
        if len(self.trajectory) > 1:
            xs, ys = zip(*self.trajectory)
            self.trajectory_curve.setData(xs, ys)
        
        self.current_point.setData([x], [y])
        
        # Update status
        self.statusBar().showMessage(
            f"Pose: X={x:.1f}, Y={y:.1f}, Z={z:.1f}, R={r:.1f} | "
            f"History: {len(self.trajectory)} points | "
            f"Update rate: ~20 Hz"
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
    # Check for pyqtgraph and PyQt5
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
    window = RealTimeViz2D(port)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
