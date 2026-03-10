"""
viz_mg400.py — Real-time dual-view visualizer for MG400 motion scripts.

Two side-by-side 2D panels (no OpenGL required):
  Left  — Top View  (XY plane): horizontal reach and Y travel
  Right — Front View (XZ plane): reach vs. height (elevation)

Usage in any motion script (3 lines):
    from viz_mg400 import RobotViz
    viz = RobotViz()
    viz.attach(move_api)        # patches move_api.MovJ and .MovL
    # ... motion code unchanged ...
    viz.close()                 # in finally block, before closing connections

Manual pose push (e.g. in feedback loops):
    viz.send(x, y, z, r)

Disable via environment or CLI:
    DOBOT_VIZ=0 python 07_keyboard_teleop.py
    python 07_keyboard_teleop.py --no-viz

Trail length (default 500):
    DOBOT_TRAIL=1000 python 09_arc_motion.py

Architecture: identical to scripts/viz.py — the motion script owns all TCP
sockets; this module spawns a separate subprocess (spawn context) that owns
the Qt GUI.  The two processes communicate through a multiprocessing.Queue.
The subprocess never inherits the parent's socket file descriptors.

Dependencies (from requirements.txt):
    pip install pyqtgraph PyQt5
"""

from __future__ import annotations

import multiprocessing as mp
import os


def _viz_enabled() -> bool:
    return os.environ.get("DOBOT_VIZ", "1") not in ("0", "false", "no")


class RobotViz:
    """Public handle used by motion scripts to control the visualizer.

    All methods are no-ops when enabled=False, DOBOT_VIZ=0, or when the GUI
    subprocess fails to start (e.g. missing pyqtgraph/PyQt5, headless server).
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = False
        if not enabled or not _viz_enabled():
            return
        try:
            ctx = mp.get_context("spawn")
            self._queue: mp.Queue = ctx.Queue(maxsize=500)
            self._proc = ctx.Process(
                target=_viz_process, args=(self._queue,), daemon=True
            )
            self._proc.start()
            self._enabled = True
        except Exception as exc:
            print(f"[viz] Visualizer disabled: {exc}")

    def attach(self, move_api) -> None:
        """Monkey-patch move_api.MovJ and move_api.MovL to auto-forward poses.

        The original methods are called first so robot behavior is unchanged.
        After each move is sent, the commanded (x,y,z,r) are forwarded to the
        visualizer queue with put_nowait (drops silently on overflow).
        """
        if not self._enabled:
            return
        q = self._queue
        orig_movj = move_api.MovJ
        orig_movl = move_api.MovL

        def _patched_movj(x, y, z, r, *args, **kwargs):
            result = orig_movj(x, y, z, r, *args, **kwargs)
            try:
                q.put_nowait((float(x), float(y), float(z), float(r)))
            except Exception:
                pass
            return result

        def _patched_movl(x, y, z, r, *args, **kwargs):
            result = orig_movl(x, y, z, r, *args, **kwargs)
            try:
                q.put_nowait((float(x), float(y), float(z), float(r)))
            except Exception:
                pass
            return result

        move_api.MovJ = _patched_movj
        move_api.MovL = _patched_movl

    def send(self, x: float, y: float, z: float, r: float) -> None:
        """Manually push a pose update (e.g. inside feedback loops or arc loops)."""
        if not self._enabled:
            return
        try:
            self._queue.put_nowait((x, y, z, r))
        except Exception:
            pass

    def close(self) -> None:
        """Send sentinel, wait up to 2 s for subprocess to exit, then terminate."""
        if not self._enabled:
            return
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass
        self._proc.join(timeout=2)
        if self._proc.is_alive():
            self._proc.terminate()


def _viz_process(queue) -> None:
    """Subprocess entry point — owns the Qt event loop.

    All Qt/pyqtgraph imports happen here so the parent process pays no import
    cost and its TCP socket file descriptors are never shared with the child.
    Uses only PyQt5 + pyqtgraph 2D PlotWidgets (no OpenGL/GLViewWidget).
    """
    import os as _os
    import sys
    from collections import deque

    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtWidgets import QApplication, QMainWindow, QSplitter
    import pyqtgraph as pg

    # MG400 workspace constants (mirrors utils_mg400.py — kept local to avoid
    # importing utils_mg400 in the subprocess at spawn time)
    HL = {"x": (0,   440), "y": (-220, 220), "z": (0, 150)}   # hardware limits
    SB = {"x": (60,  400), "y": (-220, 220), "z": (5, 140)}   # safe bounds

    trail_maxlen = int(_os.environ.get("DOBOT_TRAIL", "500"))

    class _MG400VizWindow(QMainWindow):
        def __init__(self, q):
            super().__init__()
            self._q = q
            self._trail: deque = deque(maxlen=trail_maxlen)
            self._move_count = 0

            self.setWindowTitle("MG400 — Live Visualizer")
            self.resize(1200, 600)

            splitter = QSplitter(Qt.Horizontal)
            self.setCentralWidget(splitter)

            dashed = Qt.DashLine

            # ---- Left: Top View (XY) ----------------------------------------
            self._plot_xy = pg.PlotWidget(
                title="Top View (XY)  —  white=hard limits  yellow=safe bounds  [C]=clear trail"
            )
            self._plot_xy.setAspectLocked(True)
            self._plot_xy.setXRange(-50, 470)
            self._plot_xy.setYRange(-250, 250)
            self._plot_xy.setLabel("left", "Y (mm)")
            self._plot_xy.setLabel("bottom", "X (mm)")
            splitter.addWidget(self._plot_xy)

            # Hard limits XY (white solid)
            hx, hy = HL["x"], HL["y"]
            self._plot_xy.plot(
                [hx[0], hx[1], hx[1], hx[0], hx[0]],
                [hy[0], hy[0], hy[1], hy[1], hy[0]],
                pen=pg.mkPen("w", width=1),
            )
            # Safe bounds XY (yellow dashed)
            sx, sy = SB["x"], SB["y"]
            self._plot_xy.plot(
                [sx[0], sx[1], sx[1], sx[0], sx[0]],
                [sy[0], sy[0], sy[1], sy[1], sy[0]],
                pen=pg.mkPen("y", width=1, style=dashed),
            )

            # 3-segment fading trail XY: dim (old) → medium → bright (recent)
            self._xy_old = self._plot_xy.plot([], [], pen=pg.mkPen((0, 110, 140), width=1))
            self._xy_mid = self._plot_xy.plot([], [], pen=pg.mkPen((0, 185, 200), width=2))
            self._xy_new = self._plot_xy.plot([], [], pen=pg.mkPen((100, 255, 255), width=2))

            # Current position dot XY (red)
            self._dot_xy = self._plot_xy.plot(
                [], [], pen=None, symbol="o", symbolBrush="r", symbolSize=10,
            )

            # ---- Right: Front View (XZ) -------------------------------------
            self._plot_xz = pg.PlotWidget(
                title="Front View (XZ)  —  white=hard limits  yellow=safe bounds"
            )
            self._plot_xz.setAspectLocked(False)
            self._plot_xz.setXRange(-50, 470)
            self._plot_xz.setYRange(-20, 170)
            self._plot_xz.setLabel("left", "Z (mm)")
            self._plot_xz.setLabel("bottom", "X (mm)")
            splitter.addWidget(self._plot_xz)

            # Hard limits XZ (white solid)
            hz = HL["z"]
            self._plot_xz.plot(
                [hx[0], hx[1], hx[1], hx[0], hx[0]],
                [hz[0], hz[0], hz[1], hz[1], hz[0]],
                pen=pg.mkPen("w", width=1),
            )
            # Safe bounds XZ (yellow dashed)
            sz = SB["z"]
            self._plot_xz.plot(
                [sx[0], sx[1], sx[1], sx[0], sx[0]],
                [sz[0], sz[0], sz[1], sz[1], sz[0]],
                pen=pg.mkPen("y", width=1, style=dashed),
            )

            # 3-segment fading trail XZ
            self._xz_old = self._plot_xz.plot([], [], pen=pg.mkPen((0, 110, 140), width=1))
            self._xz_mid = self._plot_xz.plot([], [], pen=pg.mkPen((0, 185, 200), width=2))
            self._xz_new = self._plot_xz.plot([], [], pen=pg.mkPen((100, 255, 255), width=2))

            # Current position dot XZ (red)
            self._dot_xz = self._plot_xz.plot(
                [], [], pen=None, symbol="o", symbolBrush="r", symbolSize=10,
            )

            self.statusBar().showMessage(
                "Waiting for robot data ...  |  [C] = clear trail"
            )

            self._timer = QTimer()
            self._timer.timeout.connect(self._poll)
            self._timer.start(50)   # 50 ms = 20 Hz refresh

        def keyPressEvent(self, event) -> None:
            """Press C to clear the trail without restarting the visualizer."""
            if event.key() == Qt.Key_C:
                self._trail.clear()
                self._move_count = 0
                for item in (
                    self._xy_old, self._xy_mid, self._xy_new,
                    self._xz_old, self._xz_mid, self._xz_new,
                ):
                    item.setData([], [])
                self._dot_xy.setData([], [])
                self._dot_xz.setData([], [])
                self.statusBar().showMessage("Trail cleared.  |  [C] = clear trail")
            else:
                super().keyPressEvent(event)

        def _poll(self) -> None:
            while True:
                try:
                    item = self._q.get_nowait()
                except Exception:
                    break
                if item is None:
                    self.close()
                    return
                self._update(*item)

        def _update(self, x: float, y: float, z: float, r: float) -> None:
            self._trail.append((x, y, z))
            self._move_count += 1
            n = len(self._trail)

            xs = [p[0] for p in self._trail]
            ys = [p[1] for p in self._trail]
            zs = [p[2] for p in self._trail]

            # Split trail into 3 brightness segments (overlap by 1 for connectivity)
            # old: [0 .. 60%], mid: [60% .. 90%], new: [90% .. end]
            s1 = max(0, n * 6 // 10)
            s2 = max(s1, n * 9 // 10)

            self._xy_old.setData(xs[: s1 + 1], ys[: s1 + 1])
            self._xy_mid.setData(xs[s1: s2 + 1], ys[s1: s2 + 1])
            self._xy_new.setData(xs[s2:], ys[s2:])

            self._xz_old.setData(xs[: s1 + 1], zs[: s1 + 1])
            self._xz_mid.setData(xs[s1: s2 + 1], zs[s1: s2 + 1])
            self._xz_new.setData(xs[s2:], zs[s2:])

            self._dot_xy.setData([x], [y])
            self._dot_xz.setData([x], [z])

            self.statusBar().showMessage(
                f"X={x:.1f}  Y={y:.1f}  Z={z:.1f}  R={r:.1f}"
                f"  |  moves={self._move_count}  ·  [C] clear trail"
            )

    app = QApplication(sys.argv)
    window = _MG400VizWindow(queue)
    window.show()
    app.exec_()
