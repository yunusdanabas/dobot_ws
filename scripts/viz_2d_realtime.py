#!/usr/bin/env python3
"""
2D real-time trajectory visualization using pyqtgraph.
Runs robot control in QThread, visualization in main thread.
Update rate: 10–30 Hz sustainable.

Requires: PyQt5, pyqtgraph, numpy
Install: pip install PyQt5 pyqtgraph numpy
"""

import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import pyqtgraph as pg

from pyqtgraph_helpers import PosePollingThread
from utils import HARD_LIMITS, SAFE_BOUNDS, find_port

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
        
        # Workspace bounds reference derived from utils.py
        self.plot_widget.setXRange(HARD_LIMITS['x'][0] - 25, HARD_LIMITS['x'][1] + 25)
        self.plot_widget.setYRange(HARD_LIMITS['y'][0] - 20, HARD_LIMITS['y'][1] + 20)

        hard_x, hard_y = HARD_LIMITS['x'], HARD_LIMITS['y']
        safe_x, safe_y = SAFE_BOUNDS['x'], SAFE_BOUNDS['y']
        self.plot_widget.plot(
            [hard_x[0], hard_x[1], hard_x[1], hard_x[0], hard_x[0]],
            [hard_y[0], hard_y[0], hard_y[1], hard_y[1], hard_y[0]],
            pen=pg.mkPen('w', width=1),
        )
        self.plot_widget.plot(
            [safe_x[0], safe_x[1], safe_x[1], safe_x[0], safe_x[0]],
            [safe_y[0], safe_y[0], safe_y[1], safe_y[1], safe_y[0]],
            pen=pg.mkPen('y', width=1, style=Qt.DashLine),
        )
        
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
        self.statusBar().showMessage("Connecting to robot...")
        
        # Start robot thread
        self.worker = PosePollingThread(port)
        self.worker.pose_updated.connect(self.on_pose_update)
        self.worker.error_occurred.connect(self.on_error)
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
