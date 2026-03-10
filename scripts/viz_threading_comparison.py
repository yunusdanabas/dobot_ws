#!/usr/bin/env python3
"""
PyQtGraph Threading Patterns Comparison
========================================

Demonstrates three threading patterns for real-time robot visualization:
1. Naive (blocking) - DO NOT USE - included for educational purposes
2. QThread (recommended) - Responsive UI, shared memory
3. Multiprocessing - True parallelism, IPC overhead

Select pattern by setting PATTERN = 'qthread' or 'multiprocess'

This script shows architecture differences and performance tradeoffs.
"""

import sys
import time
import multiprocessing as mp
from queue import Empty, Full
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QLabel
)
from PyQt5.QtCore import QTimer, Qt
import pyqtgraph as pg

from pyqtgraph_helpers import PosePollingThread
from utils import HARD_LIMITS, SAFE_BOUNDS, find_port, unpack_pose

# ============================================================================
# Pattern 1: Naive (BLOCKING) - For comparison only
# ============================================================================

class NaiveVisualization:
    """
    ANTI-PATTERN: Blocks on serial I/O in main thread
    This freezes the UI and is included only for educational contrast.
    """
    def update_and_block(self, robot):
        # This blocks the Qt event loop!
        while True:
            pose = robot.get_pose()  # BLOCKS here!
            self.plot.setData([pose[0]], [pose[1]])
            # UI is frozen while waiting for pose


# ============================================================================
# Pattern 2: QThread (Recommended)
# ============================================================================

# ============================================================================
# Pattern 3: Multiprocessing
# ============================================================================

def robot_control_process_mp(port, pose_queue, stop_event):
    """Separate OS process for robot control"""
    robot = None
    try:
        from pydobotplus import Dobot

        robot = Dobot(port=port)
        iteration = 0
        while not stop_event.is_set():
            try:
                pose_queue.put(unpack_pose(robot.get_pose()), timeout=0.2)
                iteration += 1
            except Full:
                pass
            except Exception as exc:
                print(f"[Process] Pose read failed: {exc}")
                time.sleep(0.1)
            time.sleep(0.05)
        print(f"[Process] Completed {iteration} iterations")
    except Exception as exc:
        print(f"[Process] Error: {exc}")
    finally:
        if robot is not None:
            try:
                robot.close()
            except Exception:
                pass


# ============================================================================
# Main Visualization Window
# ============================================================================

class ThreadingComparisonWindow(QMainWindow):
    """Main window demonstrating threading patterns"""
    
    def __init__(self, pattern='qthread'):
        super().__init__()
        self.setWindowTitle(f"PyQtGraph Threading Comparison - {pattern.upper()}")
        self.setGeometry(100, 100, 1000, 700)
        self.pattern = pattern
        
        # Setup main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Control panel
        control_layout = QHBoxLayout()
        
        self.pattern_label = QLabel(f"Pattern: {pattern}")
        control_layout.addWidget(self.pattern_label)
        
        self.status_label = QLabel("Status: Initializing...")
        control_layout.addWidget(self.status_label)
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_collection)
        control_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_collection)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button)
        
        main_layout.addLayout(control_layout)
        
        # Plot
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Y (mm)', color='white')
        self.plot_widget.setLabel('bottom', 'X (mm)', color='white')
        self.plot_widget.setTitle(f'End-Effector Trajectory ({pattern})')
        self.plot_widget.setAspectLocked(True)
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
        
        self.trajectory_curve = self.plot_widget.plot(
            pen=pg.mkPen('r', width=2),
            name='Trajectory'
        )
        self.current_point = self.plot_widget.plot(
            pen=None,
            symbol='o',
            symbolSize=10,
            symbolBrush=pg.mkBrush('g')
        )
        
        main_layout.addWidget(self.plot_widget)
        
        # Stats
        self.stats_label = QLabel(
            "Updates: 0 | Last pose: - | Update rate: - Hz"
        )
        main_layout.addWidget(self.stats_label)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Data storage
        self.trajectory = []
        self.max_history = 1000
        self.update_count = 0
        self.last_update_time = time.time()
        
        # Pattern-specific setup
        self.worker = None
        self.process = None
        self.pose_queue = None
        self.stop_event = None
        
        # Performance monitor
        self.frame_times = []
    
    def start_collection(self):
        """Start robot data collection using selected pattern"""
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.trajectory = []
        self.update_count = 0
        self.frame_times = []
        
        port = find_port()
        if not port:
            self.status_label.setText("Status: Robot not found!")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            return
        
        self.status_label.setText("Status: Connecting...")
        
        if self.pattern == 'qthread':
            self._start_qthread(port)
        elif self.pattern == 'multiprocess':
            self._start_multiprocess(port)
        
        self.status_label.setText("Status: Running...")
    
    def _start_qthread(self, port):
        """Start QThread pattern"""
        self.worker = PosePollingThread(port)
        self.worker.pose_updated.connect(self.on_pose_update_qthread)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
    
    def _start_multiprocess(self, port):
        """Start multiprocessing pattern"""
        self.pose_queue = mp.Queue(maxsize=2)
        self.stop_event = mp.Event()
        self.process = mp.Process(
            target=robot_control_process_mp,
            args=(port, self.pose_queue, self.stop_event),
            daemon=False
        )
        self.process.start()
        
        # Poll queue at 30 Hz
        self.timer = QTimer()
        self.timer.timeout.connect(self.on_pose_update_multiprocess)
        self.timer.start(33)
    
    def on_pose_update_qthread(self, pose):
        """Handle pose update from QThread"""
        self._update_visualization(pose)
    
    def on_pose_update_multiprocess(self):
        """Poll queue for multiprocess pattern"""
        try:
            while True:
                pose = self.pose_queue.get_nowait()
                self._update_visualization(pose)
        except Empty:
            pass
    
    def _update_visualization(self, pose):
        """Update plot with new pose"""
        x, y, z, r, *_ = pose
        self.trajectory.append((x, y))
        
        if len(self.trajectory) > self.max_history:
            self.trajectory.pop(0)
        
        if len(self.trajectory) > 1:
            xs, ys = zip(*self.trajectory)
            self.trajectory_curve.setData(xs, ys)
        
        self.current_point.setData([x], [y])
        self.update_count += 1
        
        # Calculate update rate
        now = time.time()
        self.frame_times.append(now)
        if len(self.frame_times) > 100:
            self.frame_times.pop(0)
        
        dt = now - self.last_update_time
        if dt > 0.5 and len(self.frame_times) > 1:
            window_s = self.frame_times[-1] - self.frame_times[0]
            fps = len(self.frame_times) / window_s if window_s > 0 else 0.0
            self.stats_label.setText(
                f"Updates: {self.update_count} | "
                f"Last pose: ({x:.1f}, {y:.1f}, {z:.1f}) | "
                f"Update rate: {fps:.1f} Hz"
            )
            self.last_update_time = now
    
    def on_error(self, error_msg):
        """Handle errors"""
        self.status_label.setText(f"Status: Error - {error_msg}")
        self.stop_collection()
    
    def stop_collection(self):
        """Stop robot data collection"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        if self.pattern == 'qthread':
            if self.worker:
                self.worker.stop()
                self.worker.wait(timeout=2000)
        elif self.pattern == 'multiprocess':
            if hasattr(self, 'timer'):
                self.timer.stop()
            if self.stop_event:
                self.stop_event.set()
            if self.process:
                self.process.join(timeout=2)
                if self.process.is_alive():
                    self.process.terminate()
        
        self.status_label.setText("Status: Stopped")
    
    def closeEvent(self, event):
        """Cleanup on close"""
        self.stop_collection()
        event.accept()


def main():
    # Check dependencies
    try:
        import pyqtgraph
        import PyQt5
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Install: pip install PyQt5 pyqtgraph numpy")
        sys.exit(1)
    
    # Choose pattern
    if len(sys.argv) > 1:
        pattern = sys.argv[1].lower()
        if pattern not in ['qthread', 'multiprocess']:
            print("Usage: python viz_threading_comparison.py [qthread|multiprocess]")
            print("  qthread (default) - Qt signals, shared memory, recommended")
            print("  multiprocess - Separate process, IPC, true parallelism")
            sys.exit(1)
    else:
        pattern = 'qthread'
    
    if pattern == 'multiprocess':
        mp.set_start_method('spawn', force=True)
    
    app = QApplication(sys.argv)
    window = ThreadingComparisonWindow(pattern=pattern)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
