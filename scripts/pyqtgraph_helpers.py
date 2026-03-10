"""
Shared helpers for the standalone pyqtgraph visualization examples.

These examples intentionally stay separate from viz.py, but they still share
the same Dobot connection pattern: open one robot connection, normalize the
pose to a flat tuple, emit updates at a fixed rate, and close cleanly.
"""

from __future__ import annotations

import time

from PyQt5.QtCore import QThread, pyqtSignal

try:
    from utils import unpack_pose
except ModuleNotFoundError:
    from scripts.utils import unpack_pose


class PosePollingThread(QThread):
    """Poll the robot pose in a background QThread and emit normalized tuples."""

    pose_updated = pyqtSignal(tuple)
    error_occurred = pyqtSignal(str)

    def __init__(self, port: str, interval_s: float = 0.05):
        super().__init__()
        self.port = port
        self.interval_s = interval_s
        self.running = True
        self.robot = None

    def run(self) -> None:
        try:
            from pydobotplus import Dobot

            self.robot = Dobot(port=self.port)
            while self.running:
                self.pose_updated.emit(unpack_pose(self.robot.get_pose()))
                time.sleep(self.interval_s)
        except Exception as exc:
            self.error_occurred.emit(str(exc))
        finally:
            if self.robot is not None:
                try:
                    self.robot.close()
                except Exception:
                    pass

    def stop(self) -> None:
        self.running = False
        if self.robot is not None:
            try:
                self.robot.close()
            except Exception:
                pass
