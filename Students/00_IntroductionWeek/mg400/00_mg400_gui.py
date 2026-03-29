"""
00_mg400_gui.py — PyQt5 GUI for DOBOT MG400 (ME403 Introduction Week).

Features:
  − Robot selector dropdown (Robot 1–4 with IPs)
  − Connect / Disconnect with EnableRobot() + go_home() on connect
  − Clear Errors button (GetErrorID → ClearError → Continue)
  − Home button (move to READY_POSE)
  − Emergency Stop (ESTOP) button
  − J1–J4 joint control: spinboxes + +/− step buttons
  − Joint limits reference panel
  − Live pose readout (X/Y/Z/R + J1–J4, 500 ms poll)
  − Step-size combo (0.5°/1°/5°/10°)
  − Details log panel

Usage:
    python 00_mg400_gui.py [--robot N]   (N = 1–4, default 1)

Prepared by Yunus Emre Danabas for ME403.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Optional

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)

# ---------------------------------------------------------------------------
# Ensure the local mg400/ directory is on sys.path so utils_mg400 can be found
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from utils_mg400 import (  # noqa: E402
    check_errors,
    clamp,
    close_all,
    connect_with_diagnostics,
    go_home,
    parse_angles,
    parse_pose,
    READY_POSE,
    ROBOT_IPS,
    SPEED_DEFAULT,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# MG400 joint limits per DT-MG400-4R075-01 hardware guide V1.1, Table 2.1.
# J3 is a firmware-absolute angle (= J2_body + J3_body), not a relative angle.
JOINT_BOUNDS = {
    "j1": (-160.0, 160.0),   # ±160° — base rotation
    "j2": ( -25.0,  85.0),   # −25° to +85° — shoulder elevation
    "j3": ( -25.0, 105.0),   # −25° to +105° — elbow (firmware absolute = J2+J3_body)
    "j4": (-180.0, 180.0),   # ±180° — wrist rotation
}

JOINT_DESCRIPTIONS = {
    "j1": "Base Rotation",
    "j2": "Shoulder Elevation",
    "j3": "Elbow (firmware abs)",
    "j4": "Wrist Rotation",
}

POLL_INTERVAL_MS = 500   # live pose update interval

# Status badge colors: (background, text)
_STATUS_STYLE: dict[str, tuple[str, str]] = {
    "—":             ("#bdc3c7", "#2c3e50"),
    "CONNECTING":    ("#2980b9", "white"),
    "CONNECTED":     ("#27ae60", "white"),
    "MOVING":        ("#8e44ad", "white"),
    "DISCONNECTING": ("#e67e22", "white"),
    "ERROR":         ("#c0392b", "white"),
    "ESTOP":         ("#c0392b", "white"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clamp_joints(j1: float, j2: float, j3: float, j4: float):
    """Clamp firmware angles to JOINT_BOUNDS. Returns (j1,j2,j3,j4, was_clamped)."""
    cj1 = clamp(j1, *JOINT_BOUNDS["j1"])
    cj2 = clamp(j2, *JOINT_BOUNDS["j2"])
    cj3 = clamp(j3, *JOINT_BOUNDS["j3"])
    cj4 = clamp(j4, *JOINT_BOUNDS["j4"])
    was_clamped = (cj1, cj2, cj3, cj4) != (j1, j2, j3, j4)
    return cj1, cj2, cj3, cj4, was_clamped


# ---------------------------------------------------------------------------
# AxisRow — one labeled axis row with spinbox and +/− step buttons
# ---------------------------------------------------------------------------

class AxisRow(QWidget):
    """Label | SpinBox | [−] [+] [Move] — clicking +/− adjusts the spinbox only.
    Move sends the current spinbox value immediately.
    """

    move_requested = pyqtSignal(float)   # emits spinbox value when Move is clicked

    def __init__(
        self,
        label: str,
        lo: float,
        hi: float,
        decimals: int = 2,
        suffix: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._lo = lo
        self._hi = hi

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 2, 0, 2)

        lbl = QLabel(label)
        lbl.setFixedWidth(40)
        lbl.setFont(QFont("monospace", 10, QFont.Bold))
        row.addWidget(lbl)

        self.spin = QDoubleSpinBox()
        self.spin.setRange(lo, hi)
        self.spin.setDecimals(decimals)
        self.spin.setSuffix(suffix)
        self.spin.setFixedWidth(104)
        self.spin.setFont(QFont("monospace", 10))
        row.addWidget(self.spin)

        self.minus_btn = QPushButton("−")
        self.minus_btn.setFixedWidth(32)
        self.minus_btn.clicked.connect(self._step_down)
        row.addWidget(self.minus_btn)

        self.plus_btn = QPushButton("+")
        self.plus_btn.setFixedWidth(32)
        self.plus_btn.clicked.connect(self._step_up)
        row.addWidget(self.plus_btn)

        self.move_btn = QPushButton("Move")
        self.move_btn.setFixedWidth(52)
        self.move_btn.clicked.connect(lambda: self.move_requested.emit(self.spin.value()))
        row.addWidget(self.move_btn)

        row.addStretch()

        # Callable returning the current step size; wired externally by the window.
        self.get_step: Callable[[], float] = lambda: 1.0

    def _step_down(self) -> None:
        self.spin.setValue(max(self._lo, self.spin.value() - self.get_step()))

    def _step_up(self) -> None:
        self.spin.setValue(min(self._hi, self.spin.value() + self.get_step()))

    def set_enabled(self, en: bool) -> None:
        for w in (self.spin, self.minus_btn, self.plus_btn, self.move_btn):
            w.setEnabled(en)


# ---------------------------------------------------------------------------
# Workers (QThread subclasses — keep UI responsive during blocking calls)
# ---------------------------------------------------------------------------

class ConnectWorker(QThread):
    """Background thread: open TCP sockets, enable robot, move to home."""

    done = pyqtSignal(bool, str)   # success, log message

    def __init__(self, ip: str) -> None:
        super().__init__()
        self.ip       = ip
        self.dashboard = None
        self.move_api  = None

    def run(self) -> None:
        try:
            dashboard, move_api = connect_with_diagnostics(self.ip)
            check_errors(dashboard)
            dashboard.EnableRobot()
            dashboard.SpeedFactor(SPEED_DEFAULT)   # set conservative speed
            go_home(move_api)                      # move to READY_POSE
            self.dashboard = dashboard
            self.move_api  = move_api
            self.done.emit(True, f"Connected to {self.ip} — at READY_POSE")
        except Exception as exc:
            self.done.emit(False, str(exc))


class MotionWorker(QThread):
    """Background thread: execute a motion callable, report result."""

    done = pyqtSignal(bool, str)   # success, log message

    def __init__(self, motion_fn: Callable) -> None:
        super().__init__()
        self._motion_fn = motion_fn

    def run(self) -> None:
        try:
            msg = self._motion_fn()
            self.done.emit(True, msg or "")
        except Exception as exc:
            self.done.emit(False, str(exc))


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MG400Window(QMainWindow):
    def __init__(self, preset_robot: int = 1) -> None:
        super().__init__()
        self.setWindowTitle("DOBOT MG400 — Introduction Week GUI  (ME 403)")
        self.setMinimumSize(720, 600)

        # API handles — None when disconnected
        self._dashboard = None
        self._move_api  = None

        # Worker handles — None when idle
        self._connect_worker: Optional[ConnectWorker] = None
        self._motion_worker:  Optional[MotionWorker]  = None

        # Poll timer: update Live Pose panel every 500 ms
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_pose)

        self._build_ui()

        # Pre-select robot from CLI argument (index 0 = Robot 1)
        idx = preset_robot - 1
        if 0 <= idx < self._robot_combo.count():
            self._robot_combo.setCurrentIndex(idx)

        self._set_connected(False)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        # ── Connection bar: robot selector, Connect/Disconnect, status badge ──
        conn_bar = QHBoxLayout()

        conn_bar.addWidget(QLabel("Robot:"))
        self._robot_combo = QComboBox()
        for rid, ip in ROBOT_IPS.items():
            self._robot_combo.addItem(f"Robot {rid}  ({ip})", userData=ip)
        self._robot_combo.setFixedWidth(200)
        conn_bar.addWidget(self._robot_combo)

        conn_bar.addStretch()

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setFixedWidth(88)
        self._connect_btn.clicked.connect(self._on_connect)
        conn_bar.addWidget(self._connect_btn)

        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.setFixedWidth(96)
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        conn_bar.addWidget(self._disconnect_btn)

        self._status_badge = QLabel("—")
        self._status_badge.setFixedWidth(120)
        self._status_badge.setAlignment(Qt.AlignCenter)
        self._status_badge.setFont(QFont("monospace", 9, QFont.Bold))
        self._apply_badge("—")
        conn_bar.addWidget(self._status_badge)

        root.addLayout(conn_bar)

        # ── Action bar: Clear Errors, Home, step size, ESTOP ──────────────
        action_bar = QHBoxLayout()

        self._clear_errors_btn = QPushButton("Clear Errors")
        self._clear_errors_btn.setFixedWidth(100)
        self._clear_errors_btn.setToolTip("GetErrorID → ClearError → Continue")
        self._clear_errors_btn.clicked.connect(self._on_clear_errors)
        action_bar.addWidget(self._clear_errors_btn)

        self._home_btn = QPushButton("Home")
        self._home_btn.setFixedWidth(72)
        self._home_btn.setToolTip(f"Move to READY_POSE {READY_POSE}")
        self._home_btn.clicked.connect(self._on_home)
        action_bar.addWidget(self._home_btn)

        action_bar.addStretch()

        action_bar.addWidget(QLabel("Step°:"))
        self._step_combo = QComboBox()
        for v in ("0.5°", "1°", "5°", "10°"):
            self._step_combo.addItem(v, userData=float(v.rstrip("°")))
        self._step_combo.setCurrentIndex(1)   # default 1°
        self._step_combo.setFixedWidth(64)
        action_bar.addWidget(self._step_combo)

        # ESTOP is always enabled (even when not connected — displays warning)
        self._estop_btn = QPushButton("ESTOP")
        self._estop_btn.setFixedWidth(80)
        self._estop_btn.setStyleSheet(
            "QPushButton {"
            "  background-color:#c0392b; color:white; font-weight:bold;"
            "}"
            "QPushButton:hover { background-color:#e74c3c; }"
        )
        self._estop_btn.clicked.connect(self._on_estop)
        action_bar.addWidget(self._estop_btn)

        root.addLayout(action_bar)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setFrameShadow(QFrame.Sunken)
        root.addWidget(sep1)

        # ── Middle: joint controls (left) + live readout + limits (right) ──
        mid = QHBoxLayout()

        # --- Left: Joint Control panel ---
        joint_box = QGroupBox("Joint Control  (firmware absolute angles)")
        joint_layout = QVBoxLayout(joint_box)
        joint_layout.setSpacing(4)

        axes = [
            ("J1", *JOINT_BOUNDS["j1"]),
            ("J2", *JOINT_BOUNDS["j2"]),
            ("J3", *JOINT_BOUNDS["j3"]),
            ("J4", *JOINT_BOUNDS["j4"]),
        ]
        self._joint_rows: list[AxisRow] = []
        for idx, (label, lo, hi) in enumerate(axes):
            row = AxisRow(label, lo, hi, decimals=2, suffix="°")
            row.move_requested.connect(
                lambda v, i=idx: self._on_move_single(i, v)
            )
            joint_layout.addWidget(row)
            self._joint_rows.append(row)

        joint_layout.addStretch()

        self._send_all_btn = QPushButton("Send All  (J1 – J4)")
        self._send_all_btn.setFixedHeight(32)
        self._send_all_btn.clicked.connect(self._on_send_all)
        joint_layout.addWidget(self._send_all_btn)

        mid.addWidget(joint_box, stretch=2)

        # --- Right: Live Pose readout + Joint Limits reference ---
        right_col = QVBoxLayout()

        # Live pose readout — updated by _poll_pose() every 500 ms
        pose_box = QGroupBox("Live Pose")
        pose_layout = QVBoxLayout(pose_box)
        pose_layout.setSpacing(4)

        mono = QFont("monospace", 10)
        self._pose_labels: dict[str, QLabel] = {}
        for key in ("X", "Y", "Z", "R", "J1", "J2", "J3", "J4"):
            lbl = QLabel(f"{key}: —")
            lbl.setFont(mono)
            pose_layout.addWidget(lbl)
            self._pose_labels[key] = lbl

        pose_layout.addStretch()
        right_col.addWidget(pose_box)

        # Joint limits — static reference so students can see safe ranges
        limits_box = QGroupBox("Joint Limits")
        limits_layout = QVBoxLayout(limits_box)
        limits_layout.setSpacing(2)

        small_mono = QFont("monospace", 9)
        for key in ("j1", "j2", "j3", "j4"):
            lo, hi = JOINT_BOUNDS[key]
            desc = JOINT_DESCRIPTIONS[key]
            lbl = QLabel(f"{key.upper()}: {lo:+.0f}° to {hi:+.0f}°  ({desc})")
            lbl.setFont(small_mono)
            lbl.setStyleSheet("color:#2c3e50;")
            limits_layout.addWidget(lbl)

        right_col.addWidget(limits_box)

        mid.addLayout(right_col, stretch=1)
        root.addLayout(mid)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setFrameShadow(QFrame.Sunken)
        root.addWidget(sep2)

        # ── Details log: scrollable text for connection events and moves ──
        detail_hdr = QHBoxLayout()
        detail_hdr.addWidget(QLabel("Details"))
        detail_hdr.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(58)
        clear_btn.clicked.connect(lambda: self._detail.clear())
        detail_hdr.addWidget(clear_btn)
        root.addLayout(detail_hdr)

        self._detail = QTextEdit()
        self._detail.setReadOnly(True)
        self._detail.setFont(QFont("monospace", 9))
        self._detail.setMaximumHeight(140)
        self._detail.setPlaceholderText(
            "Connection logs, error info, and move results will appear here.\n"
            "Select a robot and click Connect to begin."
        )
        root.addWidget(self._detail)

        # ── Footer ────────────────────────────────────────────────────────
        footer = QLabel("Prepared by Yunus Emre Danabas  —  ME 403 Introduction to Robotics")
        footer.setAlignment(Qt.AlignCenter)
        footer.setFont(QFont("sans-serif", 8))
        footer.setStyleSheet("color:#95a5a6; margin-top:4px;")
        root.addWidget(footer)

        # ── Wire step providers to AxisRow widgets ─────────────────────────
        def deg_step() -> float:
            return self._step_combo.currentData()

        for row in self._joint_rows:
            row.get_step = deg_step

    # ------------------------------------------------------------------
    # Badge helper
    # ------------------------------------------------------------------

    def _apply_badge(self, status: str) -> None:
        bg, fg = _STATUS_STYLE.get(status, ("#95a5a6", "white"))
        self._status_badge.setText(status)
        self._status_badge.setStyleSheet(
            f"background-color:{bg}; color:{fg}; "
            "border-radius:4px; padding:2px 6px;"
        )

    # ------------------------------------------------------------------
    # Log helper
    # ------------------------------------------------------------------

    def _log(self, text: str) -> None:
        self._detail.append(text)
        sb = self._detail.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ------------------------------------------------------------------
    # Connected / disconnected state — enable or disable controls
    # ------------------------------------------------------------------

    def _set_connected(self, connected: bool) -> None:
        self._connect_btn.setEnabled(not connected)
        self._robot_combo.setEnabled(not connected)
        self._disconnect_btn.setEnabled(connected)
        self._clear_errors_btn.setEnabled(connected)
        self._home_btn.setEnabled(connected)
        self._send_all_btn.setEnabled(connected)
        for row in self._joint_rows:
            row.set_enabled(connected)
        if not connected:
            self._apply_badge("—")
            for key, lbl in self._pose_labels.items():
                lbl.setText(f"{key}: —")

    def _set_motion_busy(self, busy: bool) -> None:
        """Disable controls while a move is in progress."""
        en = not busy
        for row in self._joint_rows:
            row.set_enabled(en)
        self._send_all_btn.setEnabled(en)
        self._home_btn.setEnabled(en)
        self._disconnect_btn.setEnabled(en)
        self._clear_errors_btn.setEnabled(en)
        self._apply_badge("MOVING" if busy else "CONNECTED")

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def _on_connect(self) -> None:
        if self._connect_worker is not None:
            return
        ip = self._robot_combo.currentData()
        if not ip:
            self._log("[Error] No robot selected.")
            return
        self._apply_badge("CONNECTING")
        self._connect_btn.setEnabled(False)
        self._log(f"Connecting to {ip} ...")

        worker = ConnectWorker(ip)
        worker.done.connect(self._on_connect_done)
        self._connect_worker = worker
        worker.start()

    def _on_connect_done(self, success: bool, msg: str) -> None:
        worker = self._connect_worker
        self._connect_worker = None

        if not success:
            self._apply_badge("ERROR")
            self._connect_btn.setEnabled(True)
            self._log(f"[Error] {msg}")
            return

        self._dashboard = worker.dashboard
        self._move_api  = worker.move_api
        self._log(msg)

        self._init_spinboxes()
        self._set_connected(True)
        self._apply_badge("CONNECTED")
        self._poll_timer.start()

    def _on_disconnect(self) -> None:
        self._poll_timer.stop()
        self._apply_badge("DISCONNECTING")
        self._disconnect_btn.setEnabled(False)

        if self._dashboard is not None:
            try:
                self._dashboard.DisableRobot()
            except Exception:
                pass
        if self._dashboard is not None and self._move_api is not None:
            close_all(self._dashboard, self._move_api)
        self._dashboard = None
        self._move_api  = None

        self._set_connected(False)
        self._log("Disconnected.")

    # ------------------------------------------------------------------
    # Init spinboxes from actual robot joint angles after connect
    # ------------------------------------------------------------------

    def _init_spinboxes(self) -> None:
        if self._dashboard is None:
            return
        try:
            j1, j2, j3, j4 = parse_angles(self._dashboard.GetAngle())
        except Exception:
            return
        for row, v in zip(self._joint_rows, (j1, j2, j3, j4)):
            row.spin.setValue(v)

    # ------------------------------------------------------------------
    # Poll pose (500 ms) — updates Live Pose panel
    # ------------------------------------------------------------------

    def _poll_pose(self) -> None:
        if self._motion_worker is not None or self._dashboard is None:
            return   # skip while moving to avoid concurrent socket calls
        try:
            x, y, z, r     = parse_pose(self._dashboard.GetPose())
            j1, j2, j3, j4 = parse_angles(self._dashboard.GetAngle())
        except Exception:
            return

        for key, val in zip(
            ("X", "Y", "Z", "R", "J1", "J2", "J3", "J4"),
            (x, y, z, r, j1, j2, j3, j4),
        ):
            self._pose_labels[key].setText(f"{key}: {val:.2f}")

    # ------------------------------------------------------------------
    # Motion: Send All — move all four joints simultaneously
    # ------------------------------------------------------------------

    def _on_send_all(self) -> None:
        if self._move_api is None or self._motion_worker is not None:
            return
        move_api = self._move_api
        j1, j2, j3, j4 = [r.spin.value() for r in self._joint_rows]
        j1c, j2c, j3c, j4c, clamped = clamp_joints(j1, j2, j3, j4)
        if clamped:
            self._log(
                f"[clamp] ({j1:.1f},{j2:.1f},{j3:.1f},{j4:.1f})"
                f" → ({j1c:.1f},{j2c:.1f},{j3c:.1f},{j4c:.1f})"
            )

        def _fn():
            move_api.JointMovJ(j1c, j2c, j3c, j4c)
            move_api.Sync()
            return f"JointMovJ {j1c:.1f} {j2c:.1f} {j3c:.1f} {j4c:.1f}"

        self._set_motion_busy(True)
        worker = MotionWorker(_fn)
        worker.done.connect(self._on_motion_done)
        self._motion_worker = worker
        worker.start()

    # ------------------------------------------------------------------
    # Motion: Single joint — move one joint while keeping the others
    # ------------------------------------------------------------------

    def _on_move_single(self, axis_idx: int, val: float) -> None:
        if self._move_api is None or self._dashboard is None:
            return
        if self._motion_worker is not None:
            return
        move_api  = self._move_api
        dashboard = self._dashboard
        axis_names = ["J1", "J2", "J3", "J4"]

        # Read current angles so unchanged joints stay where they are
        try:
            current = list(parse_angles(dashboard.GetAngle()))
        except Exception:
            current = [r.spin.value() for r in self._joint_rows]
        current[axis_idx] = val
        j1c, j2c, j3c, j4c, _ = clamp_joints(*current)

        def _fn():
            move_api.JointMovJ(j1c, j2c, j3c, j4c)
            move_api.Sync()
            return f"JointMovJ {axis_names[axis_idx]}={val:.1f}"

        self._set_motion_busy(True)
        worker = MotionWorker(_fn)
        worker.done.connect(self._on_motion_done)
        self._motion_worker = worker
        worker.start()

    # ------------------------------------------------------------------
    # Motion done callback
    # ------------------------------------------------------------------

    def _on_motion_done(self, success: bool, msg: str) -> None:
        self._motion_worker = None   # unblock poll first
        self._set_motion_busy(False)
        if not success:
            self._log(f"[Error] {msg}")
        else:
            self._log(f"[Move] {msg}")
        self._init_spinboxes()   # sync spinboxes to actual post-move state

    # ------------------------------------------------------------------
    # Clear Errors
    # ------------------------------------------------------------------

    def _on_clear_errors(self) -> None:
        if self._dashboard is None or self._motion_worker is not None:
            return
        dashboard = self._dashboard

        def _fn():
            check_errors(dashboard)
            return "Errors cleared."

        self._set_motion_busy(True)
        worker = MotionWorker(_fn)
        worker.done.connect(self._on_motion_done)
        self._motion_worker = worker
        worker.start()

    # ------------------------------------------------------------------
    # Home
    # ------------------------------------------------------------------

    def _on_home(self) -> None:
        if self._move_api is None or self._motion_worker is not None:
            return
        move_api = self._move_api

        def _fn():
            go_home(move_api)
            return f"Home → READY_POSE {READY_POSE}"

        self._set_motion_busy(True)
        worker = MotionWorker(_fn)
        worker.done.connect(self._on_motion_done)
        self._motion_worker = worker
        worker.start()

    # ------------------------------------------------------------------
    # Emergency Stop — called directly on the main thread for immediacy
    # ------------------------------------------------------------------

    def _on_estop(self) -> None:
        """Halt all motion: EmergencyStop + DisableRobot, then disconnect."""
        self._poll_timer.stop()
        self._apply_badge("ESTOP")
        self._log("[ESTOP] Emergency stop triggered.")

        if self._dashboard is not None:
            try:
                self._dashboard.EmergencyStop()
            except Exception:
                pass
            try:
                self._dashboard.DisableRobot()
            except Exception:
                pass

        # Kill any in-flight motion worker
        if self._motion_worker is not None:
            self._motion_worker.quit()
            self._motion_worker.wait(500)
            self._motion_worker = None

        if self._dashboard is not None and self._move_api is not None:
            close_all(self._dashboard, self._move_api)
        self._dashboard = None
        self._move_api  = None

        self._set_connected(False)

    # ------------------------------------------------------------------
    # Close event — clean up threads and connections on window close
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._poll_timer.stop()

        if self._motion_worker is not None:
            self._motion_worker.quit()
            self._motion_worker.wait(1000)
            self._motion_worker = None

        if self._connect_worker is not None:
            self._connect_worker.quit()
            self._connect_worker.wait(1000)

        if self._dashboard is not None:
            try:
                self._dashboard.DisableRobot()
            except Exception:
                pass
        if self._dashboard is not None and self._move_api is not None:
            close_all(self._dashboard, self._move_api)
        self._dashboard = None
        self._move_api  = None

        event.accept()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MG400 Introduction Week GUI (ME403)"
    )
    parser.add_argument(
        "--robot",
        type=int,
        default=1,
        choices=(1, 2, 3, 4),
        metavar="N",
        help="Pre-select robot 1–4 (default: 1)",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MG400Window(preset_robot=args.robot)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
