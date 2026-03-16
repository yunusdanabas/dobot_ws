"""
17_joint_control_gui.py — PyQt5 GUI for MG400 joint / Cartesian control (ME403).

Three control modes in tabs:
  • Absolute Joint  — J1–J4 firmware angles (direct)
  • Relative Joint  — body-frame relative angles (converted to firmware)
  • XYZ Cartesian   — X/Y/Z/R with MovJ or MovL

Features:
  − +/− step buttons (no immediate motion; use Move / Send All to execute)
  − Live pose readout panel (200 ms poll)
  − Speed slider (1–100 %) with 300 ms debounce
  − Step-size combos: degrees (0.5/1/5/10) and mm (1/5/10)
  − Home button, Emergency Stop button
  − RobotViz subprocess visualizer (--no-viz to disable)

Usage:
    python 17_joint_control_gui.py [--robot N] [--no-viz]

N = 1–4 pre-selects the robot combo (default: 1).
--no-viz disables the visualizer subprocess.
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
    QHBoxLayout, QLabel, QMainWindow, QPushButton, QSlider,
    QTabWidget, QVBoxLayout, QWidget,
)

# ---------------------------------------------------------------------------
# SDK path — utils_mg400 adds vendor/ to sys.path on import
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from utils_mg400 import (  # noqa: E402
    check_errors,
    clamp,
    close_all,
    connect,
    go_home,
    MG400_IP,
    parse_angles,
    parse_pose,
    READY_POSE,
    ROBOT_IPS,
    safe_move,
    SAFE_BOUNDS,
    SPEED_DEFAULT,
)
from viz_mg400 import RobotViz  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JOINT_BOUNDS = {
    "j1": (-160.0, 160.0),   # ±160° per hardware guide
    "j2": ( -25.0,  85.0),   # -25° ~ +85° per hardware guide
    "j3": ( -25.0, 105.0),   # -25° ~ +105° per hardware guide (firmware absolute = j2+j3_rel)
    "j4": (-180.0, 180.0),   # ±180° per hardware guide
}

POLL_INTERVAL_MS  = 200
SPEED_MIN, SPEED_MAX = 1, 100
TOOL_DO_INDEX = 1   # ToolDO index for end-effector (suction pump or gripper)
# Per-robot end-effector type — Robot 1 has a mechanical gripper; 2/3/4 have suction cups
ROBOT_END_EFFECTOR = {1: "gripper", 2: "suction", 3: "suction", 4: "suction"}

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
# Helpers copied from scripts 14 + 16
# ---------------------------------------------------------------------------


def clamp_joints(j1: float, j2: float, j3: float, j4: float):
    """Clamp firmware angles to JOINT_BOUNDS. Returns (j1,j2,j3,j4, was_clamped)."""
    cj1 = clamp(j1, *JOINT_BOUNDS["j1"])
    cj2 = clamp(j2, *JOINT_BOUNDS["j2"])
    cj3 = clamp(j3, *JOINT_BOUNDS["j3"])
    cj4 = clamp(j4, *JOINT_BOUNDS["j4"])
    was_clamped = (cj1, cj2, cj3, cj4) != (j1, j2, j3, j4)
    return cj1, cj2, cj3, cj4, was_clamped


def query_fk(dashboard, j1: float, j2: float, j3: float, j4: float):
    """Return (x,y,z,r) from PositiveSolution FK, or None on failure."""
    try:
        resp = dashboard.PositiveSolution(j1, j2, j3, j4, user=0, tool=0)
        return parse_pose(resp)
    except Exception:
        return None


def rel_to_abs_mg400(j1_r: float, j2_r: float, j3_r: float, j4_r: float):
    """Convert body-frame relative angles → firmware (absolute) tuple.

    j1_fw = j1_rel
    j2_fw = j2_rel
    j3_fw = j2_rel + j3_rel   (elbow accumulated from shoulder)
    j4_fw = j3_fw  + j4_rel   (wrist accumulated from elbow)
    """
    j3_abs = j2_r + j3_r
    j4_abs = j3_abs + j4_r
    return j1_r, j2_r, j3_abs, j4_abs


def fw_to_rel_mg400(j1_fw: float, j2_fw: float, j3_fw: float, j4_fw: float):
    """Convert firmware (absolute) angles → body-frame relative."""
    j3_rel = j3_fw - j2_fw
    j4_rel = j4_fw - j3_fw
    return j1_fw, j2_fw, j3_rel, j4_rel


# ---------------------------------------------------------------------------
# AxisRow — one labeled axis row with spinbox and +/− step buttons
# ---------------------------------------------------------------------------


class AxisRow(QWidget):
    """Label | SpinBox | [−] [+] [Move] — clicking +/− adjusts spinbox only."""

    move_requested = pyqtSignal(float)   # emits spinbox value when Move clicked

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
        lbl.setFixedWidth(56)
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
        self.move_btn.setFixedWidth(56)
        self.move_btn.clicked.connect(lambda: self.move_requested.emit(self.spin.value()))
        row.addWidget(self.move_btn)

        row.addStretch()

        # Callable that returns current step size; wired externally.
        self.get_step: Callable[[], float] = lambda: 1.0

    def _step_down(self) -> None:
        self.spin.setValue(max(self._lo, self.spin.value() - self.get_step()))

    def _step_up(self) -> None:
        self.spin.setValue(min(self._hi, self.spin.value() + self.get_step()))

    def set_enabled(self, en: bool) -> None:
        for w in (self.spin, self.minus_btn, self.plus_btn, self.move_btn):
            w.setEnabled(en)


# ---------------------------------------------------------------------------
# AbsJointTab — direct firmware joint angles
# ---------------------------------------------------------------------------


class AbsJointTab(QWidget):
    """Tab: J1–J4 firmware (absolute) angles."""

    send_all_requested    = pyqtSignal(list)        # [j1, j2, j3, j4]
    move_single_requested = pyqtSignal(int, float)  # axis_idx, value

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        axes = [
            ("J1 (fw)", *JOINT_BOUNDS["j1"]),
            ("J2 (fw)", *JOINT_BOUNDS["j2"]),
            ("J3 (fw)", *JOINT_BOUNDS["j3"]),
            ("J4 (fw)", *JOINT_BOUNDS["j4"]),
        ]
        self.rows: list[AxisRow] = []
        for idx, (label, lo, hi) in enumerate(axes):
            row = AxisRow(label, lo, hi, decimals=2, suffix="°")
            row.move_requested.connect(
                lambda v, i=idx: self.move_single_requested.emit(i, v)
            )
            layout.addWidget(row)
            self.rows.append(row)

        layout.addStretch()

        send_all = QPushButton("Send All  (J1 – J4)")
        send_all.setFixedHeight(32)
        send_all.clicked.connect(
            lambda: self.send_all_requested.emit([r.spin.value() for r in self.rows])
        )
        layout.addWidget(send_all)

    def set_values(self, j1: float, j2: float, j3: float, j4: float) -> None:
        for row, v in zip(self.rows, (j1, j2, j3, j4)):
            row.spin.setValue(v)

    def set_enabled(self, en: bool) -> None:
        for r in self.rows:
            r.set_enabled(en)


# ---------------------------------------------------------------------------
# RelJointTab — body-frame relative angles
# ---------------------------------------------------------------------------


class RelJointTab(QWidget):
    """Tab: J1_rel–J4_rel body-frame angles (converted to firmware before move)."""

    send_all_requested    = pyqtSignal(list)
    move_single_requested = pyqtSignal(int, float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # J3_rel / J4_rel effective ranges are J2-coupled; use worst-case bounds and
        # let rel_to_abs + clamp_joints enforce the firmware limits at move time.
        axes = [
            ("J1 rel", -160.0,  160.0),
            ("J2 rel",  -25.0,   85.0),
            ("J3 rel", -110.0,  130.0),   # worst-case: j3_fw(-25~105) − j2_fw(-25~85)
            ("J4 rel", -285.0,  205.0),   # worst-case: j4_fw(-180~180) − j3_fw(-25~105)
        ]
        self.rows: list[AxisRow] = []
        for idx, (label, lo, hi) in enumerate(axes):
            row = AxisRow(label, lo, hi, decimals=2, suffix="°")
            row.move_requested.connect(
                lambda v, i=idx: self.move_single_requested.emit(i, v)
            )
            layout.addWidget(row)
            self.rows.append(row)

        layout.addStretch()

        note = QLabel(
            "FK chain:  J3_fw = J2_rel + J3_rel   |   J4_fw = J3_fw + J4_rel"
        )
        note.setFont(QFont("monospace", 8))
        note.setStyleSheet("color:#7f8c8d;")
        layout.addWidget(note)

        send_all = QPushButton("Send All  (J1_rel – J4_rel)")
        send_all.setFixedHeight(32)
        send_all.clicked.connect(
            lambda: self.send_all_requested.emit([r.spin.value() for r in self.rows])
        )
        layout.addWidget(send_all)

    def set_values(
        self, j1_r: float, j2_r: float, j3_r: float, j4_r: float
    ) -> None:
        for row, v in zip(self.rows, (j1_r, j2_r, j3_r, j4_r)):
            row.spin.setValue(v)

    def set_enabled(self, en: bool) -> None:
        for r in self.rows:
            r.set_enabled(en)


# ---------------------------------------------------------------------------
# CartesianTab — X/Y/Z/R with MovJ / MovL
# ---------------------------------------------------------------------------


class CartesianTab(QWidget):
    """Tab: Cartesian X/Y/Z/R control."""

    send_all_requested    = pyqtSignal(list, str)        # [x,y,z,r], mode
    move_single_requested = pyqtSignal(int, float, str)  # axis_idx, value, mode

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        axes = [
            ("X",  SAFE_BOUNDS["x"][0], SAFE_BOUNDS["x"][1], " mm"),
            ("Y",  SAFE_BOUNDS["y"][0], SAFE_BOUNDS["y"][1], " mm"),
            ("Z",  SAFE_BOUNDS["z"][0], SAFE_BOUNDS["z"][1], " mm"),
            ("R",  SAFE_BOUNDS["r"][0], SAFE_BOUNDS["r"][1], "°"),
        ]
        self.rows: list[AxisRow] = []
        for idx, (label, lo, hi, sfx) in enumerate(axes):
            row = AxisRow(label, lo, hi, decimals=1, suffix=sfx)
            row.move_requested.connect(
                lambda v, i=idx: self.move_single_requested.emit(i, v, self._mode())
            )
            layout.addWidget(row)
            self.rows.append(row)

        layout.addStretch()

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["MovJ", "MovL"])
        self.mode_combo.setFixedWidth(80)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        send_all = QPushButton("Send All  (X Y Z R)")
        send_all.setFixedHeight(32)
        send_all.clicked.connect(
            lambda: self.send_all_requested.emit(
                [r.spin.value() for r in self.rows], self._mode()
            )
        )
        layout.addWidget(send_all)

    def _mode(self) -> str:
        return "J" if self.mode_combo.currentText() == "MovJ" else "L"

    def set_values(self, x: float, y: float, z: float, r: float) -> None:
        for row, v in zip(self.rows, (x, y, z, r)):
            row.spin.setValue(v)

    def set_enabled(self, en: bool) -> None:
        for r in self.rows:
            r.set_enabled(en)


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------


class ConnectWorker(QThread):
    done = pyqtSignal(bool, str)   # success, message

    def __init__(self, ip: str, speed: int) -> None:
        super().__init__()
        self.ip    = ip
        self.speed = speed
        self.dashboard = None
        self.move_api  = None
        self.feed      = None

    def run(self) -> None:
        try:
            dashboard, move_api, feed = connect(self.ip)
            check_errors(dashboard)
            dashboard.EnableRobot()
            dashboard.SpeedFactor(self.speed)
            self.dashboard = dashboard
            self.move_api  = move_api
            self.feed      = feed
            self.done.emit(True, f"Connected to {self.ip}")
        except Exception as exc:
            self.done.emit(False, str(exc))


class DisconnectWorker(QThread):
    done = pyqtSignal()

    def __init__(self, dashboard, move_api, feed) -> None:
        super().__init__()
        self._dashboard = dashboard
        self._move_api  = move_api
        self._feed      = feed

    def run(self) -> None:
        try:
            self._dashboard.DisableRobot()
        except Exception:
            pass
        close_all(self._dashboard, self._move_api, self._feed)
        self.done.emit()


class MotionWorker(QThread):
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


class JointControlWindow(QMainWindow):
    def __init__(
        self,
        preset_robot: int = 1,
        viz_enabled: bool = True,
    ) -> None:
        super().__init__()
        self.setWindowTitle("MG400 Joint Control GUI")
        self.setMinimumSize(860, 580)

        # API handles — None when disconnected
        self._dashboard = None
        self._move_api  = None
        self._feed      = None
        self._viz: Optional[RobotViz] = None
        self._viz_enabled = viz_enabled

        # Worker handles
        self._connect_worker:    Optional[ConnectWorker]    = None
        self._disconnect_worker: Optional[DisconnectWorker] = None
        self._motion_worker:     Optional[MotionWorker]     = None

        # Gripper state (tracked in software; reset to OPEN on connect/disconnect)
        self._gripper_closed = False

        # Poll timer (200 ms)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_pose)

        # Speed debounce timer (300 ms)
        self._speed_timer = QTimer(self)
        self._speed_timer.setSingleShot(True)
        self._speed_timer.setInterval(300)
        self._speed_timer.timeout.connect(self._apply_speed)

        self._build_ui()

        # Pre-select robot from CLI argument
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

        # ── Connection bar ────────────────────────────────────────────
        conn_bar = QHBoxLayout()

        conn_bar.addWidget(QLabel("Robot:"))
        self._robot_combo = QComboBox()
        for rid, ip in ROBOT_IPS.items():
            self._robot_combo.addItem(f"Robot {rid}  ({ip})", userData=ip)
        self._robot_combo.setFixedWidth(188)
        self._robot_combo.currentIndexChanged.connect(self._update_effector_labels)
        conn_bar.addWidget(self._robot_combo)

        self._ip_label = QLabel("")
        self._ip_label.setFont(QFont("monospace", 9))
        self._ip_label.setStyleSheet("color:#7f8c8d;")
        conn_bar.addWidget(self._ip_label)

        conn_bar.addStretch()

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setFixedWidth(88)
        self._connect_btn.clicked.connect(self._on_connect)
        conn_bar.addWidget(self._connect_btn)

        self._disconnect_btn = QPushButton("Disconnect")
        self._disconnect_btn.setFixedWidth(96)
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        conn_bar.addWidget(self._disconnect_btn)

        self._clear_errors_btn = QPushButton("Clear Errors")
        self._clear_errors_btn.setFixedWidth(96)
        self._clear_errors_btn.setToolTip("GetErrorID → ClearError → Continue")
        self._clear_errors_btn.clicked.connect(self._on_clear_errors)
        conn_bar.addWidget(self._clear_errors_btn)

        self._status_badge = QLabel("—")
        self._status_badge.setFixedWidth(120)
        self._status_badge.setAlignment(Qt.AlignCenter)
        self._status_badge.setFont(QFont("monospace", 9, QFont.Bold))
        self._apply_badge("—")
        conn_bar.addWidget(self._status_badge)

        root.addLayout(conn_bar)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setFrameShadow(QFrame.Sunken)
        root.addWidget(sep1)

        # ── Middle: tabs + live readout ───────────────────────────────
        mid = QHBoxLayout()

        # Control tabs
        self._tabs = QTabWidget()
        self._abs_tab  = AbsJointTab()
        self._rel_tab  = RelJointTab()
        self._cart_tab = CartesianTab()
        self._tabs.addTab(self._abs_tab,  "Absolute Joint")
        self._tabs.addTab(self._rel_tab,  "Relative Joint")
        self._tabs.addTab(self._cart_tab, "XYZ Cartesian")
        mid.addWidget(self._tabs, stretch=2)

        # Live pose readout
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

        self._fk_label = QLabel("FK: —")
        self._fk_label.setFont(QFont("monospace", 9))
        self._fk_label.setStyleSheet("color:#7f8c8d;")
        self._fk_label.setWordWrap(True)
        pose_layout.addWidget(self._fk_label)

        mid.addWidget(pose_box, stretch=1)
        root.addLayout(mid)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setFrameShadow(QFrame.Sunken)
        root.addWidget(sep2)

        # ── Bottom bar ────────────────────────────────────────────────
        bot = QHBoxLayout()

        bot.addWidget(QLabel("Speed:"))
        self._speed_slider = QSlider(Qt.Horizontal)
        self._speed_slider.setRange(SPEED_MIN, SPEED_MAX)
        self._speed_slider.setValue(SPEED_DEFAULT)
        self._speed_slider.setFixedWidth(130)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)
        bot.addWidget(self._speed_slider)

        self._speed_label = QLabel(f"{SPEED_DEFAULT}%")
        self._speed_label.setFixedWidth(36)
        self._speed_label.setFont(QFont("monospace", 9))
        bot.addWidget(self._speed_label)

        bot.addWidget(QLabel("Step°:"))
        self._step_combo_deg = QComboBox()
        for v in ("0.5°", "1°", "5°", "10°"):
            self._step_combo_deg.addItem(v, userData=float(v.rstrip("°")))
        self._step_combo_deg.setCurrentIndex(1)   # default 1°
        self._step_combo_deg.setFixedWidth(64)
        bot.addWidget(self._step_combo_deg)

        bot.addWidget(QLabel("StepMM:"))
        self._step_combo_mm = QComboBox()
        for v in ("1mm", "5mm", "10mm"):
            self._step_combo_mm.addItem(v, userData=float(v.rstrip("mm")))
        self._step_combo_mm.setCurrentIndex(1)    # default 5 mm
        self._step_combo_mm.setFixedWidth(64)
        bot.addWidget(self._step_combo_mm)

        bot.addStretch()

        self._home_btn = QPushButton("Home")
        self._home_btn.setFixedWidth(72)
        self._home_btn.setToolTip(f"Move to READY_POSE {READY_POSE}")
        self._home_btn.clicked.connect(self._on_home)
        bot.addWidget(self._home_btn)

        self._estop_btn = QPushButton("ESTOP")
        self._estop_btn.setFixedWidth(80)
        self._estop_btn.setStyleSheet(
            "QPushButton {"
            "  background-color:#c0392b; color:white; font-weight:bold;"
            "}"
            "QPushButton:hover { background-color:#e74c3c; }"
            "QPushButton:disabled { background-color:#7f8c8d; }"
        )
        self._estop_btn.clicked.connect(self._on_estop)
        bot.addWidget(self._estop_btn)

        root.addLayout(bot)

        # ── End-effector control bar (gripper or suction, per robot) ──
        gripper_bar = QHBoxLayout()

        self._effector_lbl = QLabel("Gripper:")
        self._effector_lbl.setFixedWidth(60)
        gripper_bar.addWidget(self._effector_lbl)

        self._gripper_open_btn = QPushButton("Open")
        self._gripper_open_btn.setFixedWidth(56)
        self._gripper_open_btn.clicked.connect(lambda: self._set_gripper(False))
        gripper_bar.addWidget(self._gripper_open_btn)

        self._gripper_slider = QSlider(Qt.Horizontal)
        self._gripper_slider.setRange(0, 100)
        self._gripper_slider.setValue(0)
        self._gripper_slider.setFixedWidth(160)
        self._gripper_slider.sliderReleased.connect(self._on_gripper_slider_released)
        gripper_bar.addWidget(self._gripper_slider)

        self._gripper_close_btn = QPushButton("Close")
        self._gripper_close_btn.setFixedWidth(56)
        self._gripper_close_btn.clicked.connect(lambda: self._set_gripper(True))
        gripper_bar.addWidget(self._gripper_close_btn)

        self._gripper_status_lbl = QLabel("OPEN")
        self._gripper_status_lbl.setFixedWidth(60)
        self._gripper_status_lbl.setFont(QFont("monospace", 10, QFont.Bold))
        self._gripper_status_lbl.setStyleSheet("color:#27ae60;")
        gripper_bar.addWidget(self._gripper_status_lbl)

        gripper_bar.addStretch()
        root.addLayout(gripper_bar)
        # Apply correct labels for the initially selected robot
        self._update_effector_labels()

        # ── Wire step providers to AxisRow widgets ────────────────────
        self._wire_step_providers()

        # ── Wire tab signals ──────────────────────────────────────────
        self._abs_tab.send_all_requested.connect(
            lambda vals: self._on_move_requested("abs_all", vals)
        )
        self._abs_tab.move_single_requested.connect(
            lambda idx, v: self._on_move_requested("abs_single", [idx, v])
        )
        self._rel_tab.send_all_requested.connect(
            lambda vals: self._on_move_requested("rel_all", vals)
        )
        self._rel_tab.move_single_requested.connect(
            lambda idx, v: self._on_move_requested("rel_single", [idx, v])
        )
        self._cart_tab.send_all_requested.connect(
            lambda vals, mode: self._on_move_requested("xyz_all", vals, mode)
        )
        self._cart_tab.move_single_requested.connect(
            lambda idx, v, mode: self._on_move_requested("xyz_single", [idx, v], mode)
        )

    def _wire_step_providers(self) -> None:
        """Attach step-provider callables to all AxisRow widgets."""

        def deg_step() -> float:
            return self._step_combo_deg.currentData()

        def mm_step() -> float:
            return self._step_combo_mm.currentData()

        for tab in (self._abs_tab, self._rel_tab):
            for row in tab.rows:
                row.get_step = deg_step

        # Cartesian: X/Y/Z rows use mm; R row uses degrees
        for i, row in enumerate(self._cart_tab.rows):
            row.get_step = mm_step if i < 3 else deg_step

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
    # Connected / disconnected state
    # ------------------------------------------------------------------

    def _set_connected(self, connected: bool) -> None:
        self._connect_btn.setEnabled(not connected)
        self._disconnect_btn.setEnabled(connected)
        self._clear_errors_btn.setEnabled(connected)
        self._home_btn.setEnabled(connected)
        self._estop_btn.setEnabled(connected)
        self._gripper_open_btn.setEnabled(connected)
        self._gripper_slider.setEnabled(connected)
        self._gripper_close_btn.setEnabled(connected)
        self._speed_slider.setEnabled(connected)
        self._step_combo_deg.setEnabled(connected)
        self._step_combo_mm.setEnabled(connected)
        self._tabs.setEnabled(connected)
        for tab in (self._abs_tab, self._rel_tab, self._cart_tab):
            tab.set_enabled(connected)
        if not connected:
            self._gripper_closed = False
            self._update_gripper_ui()
            self._apply_badge("—")
            for key, lbl in self._pose_labels.items():
                lbl.setText(f"{key}: —")
            self._fk_label.setText("FK: —")

    def _set_motion_busy(self, busy: bool) -> None:
        """Disable/re-enable interactive controls while a move is in flight."""
        en = not busy
        for tab in (self._abs_tab, self._rel_tab, self._cart_tab):
            tab.set_enabled(en)
        self._home_btn.setEnabled(en)
        self._disconnect_btn.setEnabled(en)
        self._clear_errors_btn.setEnabled(en)
        self._apply_badge("MOVING" if busy else "CONNECTED")

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def _selected_ip(self) -> str:
        return self._robot_combo.currentData()

    def _on_connect(self) -> None:
        if self._connect_worker is not None:
            return
        ip = self._selected_ip()
        self._ip_label.setText(ip)
        self._apply_badge("CONNECTING")
        self._connect_btn.setEnabled(False)

        worker = ConnectWorker(ip, self._speed_slider.value())
        worker.done.connect(self._on_connect_done)
        self._connect_worker = worker
        worker.start()

    def _on_connect_done(self, success: bool, msg: str) -> None:
        worker = self._connect_worker
        self._connect_worker = None

        if not success:
            self._apply_badge("ERROR")
            self._connect_btn.setEnabled(True)
            self._fk_label.setText(f"Connect error: {msg}")
            return

        self._dashboard = worker.dashboard
        self._move_api  = worker.move_api
        self._feed      = worker.feed

        self._viz = RobotViz(enabled=self._viz_enabled)
        self._viz.attach(self._move_api)

        self._init_spinboxes()
        self._set_connected(True)
        self._apply_badge("CONNECTED")
        self._poll_timer.start()

    def _on_disconnect(self) -> None:
        if self._disconnect_worker is not None:
            return
        self._poll_timer.stop()
        self._set_motion_busy(False)

        try:
            self._viz.close()
        except Exception:
            pass
        self._viz = None

        self._apply_badge("DISCONNECTING")
        self._disconnect_btn.setEnabled(False)

        worker = DisconnectWorker(self._dashboard, self._move_api, self._feed)
        worker.done.connect(self._on_disconnect_done)
        self._disconnect_worker = worker
        worker.start()

    def _on_disconnect_done(self) -> None:
        self._disconnect_worker = None
        self._dashboard = self._move_api = self._feed = None
        self._set_connected(False)

    def _init_spinboxes(self) -> None:
        """Read current robot state and populate all three tab spinboxes."""
        try:
            j1_fw, j2_fw, j3_fw, j4_fw = parse_angles(self._dashboard.GetAngle())
            j1_r, j2_r, j3_r, j4_r = fw_to_rel_mg400(j1_fw, j2_fw, j3_fw, j4_fw)
            x, y, z, r = parse_pose(self._dashboard.GetPose())
        except Exception:
            return
        self._abs_tab.set_values(j1_fw, j2_fw, j3_fw, j4_fw)
        self._rel_tab.set_values(j1_r, j2_r, j3_r, j4_r)
        self._cart_tab.set_values(x, y, z, r)

    # ------------------------------------------------------------------
    # Poll pose (200 ms)
    # ------------------------------------------------------------------

    def _poll_pose(self) -> None:
        if self._motion_worker is not None:
            return   # do not issue concurrent socket calls during motion
        if self._dashboard is None:
            return
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

        if self._viz:
            self._viz.send(x, y, z, r)

    # ------------------------------------------------------------------
    # Speed control
    # ------------------------------------------------------------------

    def _on_speed_changed(self, value: int) -> None:
        self._speed_label.setText(f"{value}%")
        self._speed_timer.start()   # restart 300 ms debounce

    def _apply_speed(self) -> None:
        if self._dashboard is None:
            return
        try:
            self._dashboard.SpeedFactor(self._speed_slider.value())
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Motion dispatch
    # ------------------------------------------------------------------

    def _on_move_requested(
        self, mode: str, vals: list, extra: str = "J"
    ) -> None:
        if self._move_api is None or self._dashboard is None:
            return
        if self._motion_worker is not None:
            return   # already moving

        move_api  = self._move_api
        dashboard = self._dashboard

        # Build frozen motion closure for the requested mode.
        if mode == "abs_all":
            j1, j2, j3, j4 = vals
            j1c, j2c, j3c, j4c, clamped = clamp_joints(j1, j2, j3, j4)
            if clamped:
                print(
                    f"[clamp] ({j1:.1f},{j2:.1f},{j3:.1f},{j4:.1f})"
                    f" → ({j1c:.1f},{j2c:.1f},{j3c:.1f},{j4c:.1f})"
                )
            fk = query_fk(dashboard, j1c, j2c, j3c, j4c)
            if fk:
                self._fk_label.setText(
                    f"FK: X={fk[0]:.1f} Y={fk[1]:.1f} Z={fk[2]:.1f} R={fk[3]:.1f}"
                )

            def _fn():
                move_api.JointMovJ(j1c, j2c, j3c, j4c)
                move_api.Sync()
                return (
                    f"JointMovJ {j1c:.1f} {j2c:.1f} {j3c:.1f} {j4c:.1f}"
                )

        elif mode == "abs_single":
            axis_idx = int(vals[0])
            val      = float(vals[1])
            combined = [
                self._abs_tab.rows[i].spin.value() if i != axis_idx else val
                for i in range(4)
            ]
            j1c, j2c, j3c, j4c, _ = clamp_joints(*combined)

            def _fn():
                move_api.JointMovJ(j1c, j2c, j3c, j4c)
                move_api.Sync()
                return f"JointMovJ single ax{axis_idx}={val:.1f}"

        elif mode == "rel_all":
            j1_r, j2_r, j3_r, j4_r = vals
            j1_fw, j2_fw, j3_fw, j4_fw = rel_to_abs_mg400(j1_r, j2_r, j3_r, j4_r)
            j1c, j2c, j3c, j4c, clamped = clamp_joints(j1_fw, j2_fw, j3_fw, j4_fw)
            if clamped:
                print(
                    f"[clamp-fw] ({j1_fw:.1f},{j2_fw:.1f},{j3_fw:.1f},{j4_fw:.1f})"
                    f" → ({j1c:.1f},{j2c:.1f},{j3c:.1f},{j4c:.1f})"
                )
            fk = query_fk(dashboard, j1c, j2c, j3c, j4c)
            if fk:
                self._fk_label.setText(
                    f"FK: X={fk[0]:.1f} Y={fk[1]:.1f} Z={fk[2]:.1f} R={fk[3]:.1f}"
                )

            def _fn():
                move_api.JointMovJ(j1c, j2c, j3c, j4c)
                move_api.Sync()
                return (
                    f"Rel→Fw JointMovJ "
                    f"rel=({j1_r:.1f},{j2_r:.1f},{j3_r:.1f},{j4_r:.1f}) "
                    f"fw=({j1c:.1f},{j2c:.1f},{j3c:.1f},{j4c:.1f})"
                )

        elif mode == "rel_single":
            axis_idx = int(vals[0])
            val      = float(vals[1])
            rel_vals = [
                self._rel_tab.rows[i].spin.value() if i != axis_idx else val
                for i in range(4)
            ]
            j1_fw, j2_fw, j3_fw, j4_fw = rel_to_abs_mg400(*rel_vals)
            j1c, j2c, j3c, j4c, _ = clamp_joints(j1_fw, j2_fw, j3_fw, j4_fw)

            def _fn():
                move_api.JointMovJ(j1c, j2c, j3c, j4c)
                move_api.Sync()
                return (
                    f"Rel single ax{axis_idx}={val:.1f} "
                    f"fw=({j1c:.1f},{j2c:.1f},{j3c:.1f},{j4c:.1f})"
                )

        elif mode == "xyz_all":
            x, y, z, r = vals
            mv_mode = extra

            def _fn():
                safe_move(move_api, x, y, z, r, mode=mv_mode)
                move_api.Sync()
                return f"Cart {mv_mode} X={x:.1f} Y={y:.1f} Z={z:.1f} R={r:.1f}"

        elif mode == "xyz_single":
            axis_idx = int(vals[0])
            val      = float(vals[1])
            mv_mode  = extra
            cart = [
                self._cart_tab.rows[i].spin.value() if i != axis_idx else val
                for i in range(4)
            ]
            x, y, z, r = cart

            def _fn():
                safe_move(move_api, x, y, z, r, mode=mv_mode)
                move_api.Sync()
                return f"Cart single ax{axis_idx}={val:.1f}"

        else:
            return

        self._set_motion_busy(True)
        worker = MotionWorker(_fn)
        worker.done.connect(self._on_motion_done)
        self._motion_worker = worker
        worker.start()

    def _on_motion_done(self, success: bool, msg: str) -> None:
        self._motion_worker = None   # unblock poll first
        self._set_motion_busy(False)
        if not success:
            self._fk_label.setText(f"Error: {msg}")
        else:
            print(f"[move] {msg}")
        # Re-sync spinboxes to actual post-move robot state
        self._init_spinboxes()

    # ------------------------------------------------------------------
    # Home
    # ------------------------------------------------------------------

    def _on_clear_errors(self) -> None:
        if self._dashboard is None or self._motion_worker is not None:
            return
        dashboard = self._dashboard

        def _fn():
            check_errors(dashboard)
            return "Errors cleared"

        self._set_motion_busy(True)
        worker = MotionWorker(_fn)
        worker.done.connect(self._on_motion_done)
        self._motion_worker = worker
        worker.start()

    # ------------------------------------------------------------------
    # Gripper
    # ------------------------------------------------------------------

    def _is_gripper_robot(self) -> bool:
        robot_id = self._robot_combo.currentIndex() + 1
        return ROBOT_END_EFFECTOR.get(robot_id, "suction") == "gripper"

    def _update_effector_labels(self, _index: int = 0) -> None:
        """Refresh bar label and button text to match the selected robot's end-effector."""
        is_gripper = self._is_gripper_robot()
        if is_gripper:
            self._effector_lbl.setText("Gripper:")
            self._gripper_open_btn.setText("Open")
            self._gripper_open_btn.setToolTip("Open gripper  (ToolDO 1, 0)")
            self._gripper_close_btn.setText("Close")
            self._gripper_close_btn.setToolTip("Close gripper  (ToolDO 1, 1)")
            self._gripper_slider.setToolTip("0 = Open  ·  100 = Closed  (release to send)")
        else:
            self._effector_lbl.setText("Suction:")
            self._gripper_open_btn.setText("OFF")
            self._gripper_open_btn.setToolTip("Suction OFF  (ToolDO 1, 0)")
            self._gripper_close_btn.setText("ON")
            self._gripper_close_btn.setToolTip("Suction ON  (ToolDO 1, 1)")
            self._gripper_slider.setToolTip("0 = OFF  ·  100 = ON  (release to send)")
        self._gripper_closed = False
        self._update_gripper_ui()

    def _update_gripper_ui(self) -> None:
        """Sync slider and status label to the current _gripper_closed state."""
        is_gripper = self._is_gripper_robot()
        if self._gripper_closed:
            label = "CLOSED" if is_gripper else "ON"
            color = "#e67e22"
            self._gripper_slider.setValue(100)
        else:
            label = "OPEN" if is_gripper else "OFF"
            color = "#27ae60"
            self._gripper_slider.setValue(0)
        self._gripper_status_lbl.setText(label)
        self._gripper_status_lbl.setStyleSheet(f"color:{color}; font-weight:bold;")

    def _set_gripper(self, close: bool) -> None:
        """Send ToolDO immediately via dashboard and update UI."""
        if self._dashboard is None:
            return
        try:
            self._dashboard.ToolDO(TOOL_DO_INDEX, 1 if close else 0)
            self._gripper_closed = close
        except Exception as exc:
            print(f"[effector] ToolDO error: {exc}")
        self._update_gripper_ui()

    def _on_gripper_slider_released(self) -> None:
        """Fired when user releases the slider; snaps to 0/100 and sends command."""
        self._set_gripper(self._gripper_slider.value() >= 50)

    def _on_home(self) -> None:
        if self._move_api is None or self._motion_worker is not None:
            return
        move_api = self._move_api

        def _fn():
            go_home(move_api)
            return "Home (READY_POSE)"

        self._set_motion_busy(True)
        worker = MotionWorker(_fn)
        worker.done.connect(self._on_motion_done)
        self._motion_worker = worker
        worker.start()

    # ------------------------------------------------------------------
    # Emergency stop (direct main-thread call)
    # ------------------------------------------------------------------

    def _on_estop(self) -> None:
        """Halt motion immediately: EmergencyStop + DisableRobot, then reset."""
        if self._dashboard is None:
            return

        self._poll_timer.stop()

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

        try:
            self._viz.close()
        except Exception:
            pass
        self._viz = None

        try:
            close_all(self._dashboard, self._move_api, self._feed)
        except Exception:
            pass
        self._dashboard = self._move_api = self._feed = None
        self._disconnect_worker = None

        self._set_connected(False)
        self._apply_badge("ESTOP")

    # ------------------------------------------------------------------
    # Close event
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        self._poll_timer.stop()
        self._speed_timer.stop()

        # Stop any in-flight motion worker
        if self._motion_worker is not None:
            self._motion_worker.quit()
            self._motion_worker.wait(1000)
            self._motion_worker = None

        # Close visualizer
        try:
            if self._viz:
                self._viz.close()
        except Exception:
            pass

        # Disable and close connections
        if self._dashboard is not None:
            try:
                self._dashboard.DisableRobot()
            except Exception:
                pass
            close_all(self._dashboard, self._move_api, self._feed)
            self._dashboard = self._move_api = self._feed = None

        # Wait for any background workers still running
        for w in (self._connect_worker, self._disconnect_worker):
            if w is not None:
                w.quit()
                w.wait(1000)

        event.accept()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MG400 joint / Cartesian control GUI (ME403)"
    )
    parser.add_argument(
        "--robot", type=int, choices=[1, 2, 3, 4], metavar="N",
        default=1,
        help="Pre-select robot 1–4 (default: 1)",
    )
    parser.add_argument(
        "--no-viz", action="store_true",
        help="Disable the RobotViz subprocess visualizer",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = JointControlWindow(
        preset_robot=args.robot,
        viz_enabled=not args.no_viz,
    )
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
