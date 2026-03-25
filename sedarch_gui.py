#!/usr/bin/env python3
"""
SedArch GUI — PySide6 desktop application
Covers: Input editor, simulation runner, output visualization, multi-run comparison.

Requirements:
    pip install PySide6 matplotlib numpy

Usage:
    python sedarch_gui.py
    python sedarch_gui.py path/to/input.vvm
"""

import sys
import os
import re

# Windows: conflicting Qt6 DLLs from other apps (e.g. Intel, 4KDownload) can
# shadow PySide6's own Qt DLLs. Explicitly preload from the correct location
# before any Qt module is imported.
if sys.platform == "win32":
    try:
        import ctypes, PySide6 as _p6
        _pyside_dir = os.path.dirname(_p6.__file__)
        for _dll in ("Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll"):
            _dll_path = os.path.join(_pyside_dir, _dll)
            if os.path.exists(_dll_path):
                ctypes.WinDLL(_dll_path)
        del _p6, _pyside_dir, _dll, _dll_path, ctypes
    except Exception:
        pass
import copy
import time
import tempfile
import threading
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavToolbar
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
from matplotlib.ticker import MaxNLocator

from PySide6.QtCore import (Qt, QThread, Signal, QTimer, QSize, QSettings,
                             QMutex, QMutexLocker)
from PySide6.QtGui import (QColor, QPalette, QFont, QIcon, QPixmap,
                            QAction, QKeySequence, QPainter, QBrush)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFormLayout, QSplitter, QLabel, QPushButton, QLineEdit,
    QDoubleSpinBox, QSpinBox, QTextEdit, QProgressBar, QFileDialog,
    QComboBox, QSlider, QGroupBox, QCheckBox, QScrollArea, QFrame,
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QMessageBox, QDialog, QDialogButtonBox,
    QStatusBar, QToolBar, QDockWidget, QListWidget, QListWidgetItem,
    QAbstractItemView, QMenu, QRadioButton, QButtonGroup, QStackedWidget
)

# ─────────────────────────────────────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────────────────────────────────────

DARK_BG      = "#0f1117"
PANEL_BG     = "#161b27"
CARD_BG      = "#1e2535"
BORDER       = "#2a3550"
ACCENT       = "#4a9eff"
ACCENT2      = "#ff6b35"
TEXT_PRI     = "#e8eaf0"
TEXT_SEC     = "#8a93b0"
SUCCESS      = "#4caf50"
WARNING      = "#ff9800"
DANGER       = "#f44336"
MUTED        = "#3a4460"

MPL_STYLE = {
    "axes.facecolor":    PANEL_BG,
    "figure.facecolor":  DARK_BG,
    "axes.edgecolor":    BORDER,
    "axes.labelcolor":   TEXT_PRI,
    "xtick.color":       TEXT_SEC,
    "ytick.color":       TEXT_SEC,
    "text.color":        TEXT_PRI,
    "grid.color":        BORDER,
    "grid.linewidth":    0.5,
}

STYLESHEET = f"""
QMainWindow, QDialog {{
    background-color: {DARK_BG};
    color: {TEXT_PRI};
    font-family: 'Segoe UI', 'SF Pro Text', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {PANEL_BG};
    border-radius: 6px;
}}
QTabBar::tab {{
    background: {CARD_BG};
    color: {TEXT_SEC};
    padding: 10px 22px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-radius: 5px 5px 0 0;
    margin-right: 2px;
    font-weight: 600;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    background: {PANEL_BG};
    color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover:!selected {{
    background: {MUTED};
    color: {TEXT_PRI};
}}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 12px;
    padding: 10px;
    color: {TEXT_SEC};
    font-weight: 600;
    font-size: 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {ACCENT};
}}
QPushButton {{
    background: {CARD_BG};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 7px 18px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {MUTED}; border-color: {ACCENT}; }}
QPushButton:pressed {{ background: {ACCENT}; color: #fff; }}
QPushButton#primary {{
    background: {ACCENT};
    color: #fff;
    border: none;
}}
QPushButton#primary:hover {{ background: #6ab4ff; }}
QPushButton#danger {{
    background: {DANGER};
    color: #fff;
    border: none;
}}
QPushButton#danger:hover {{ background: #e53935; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {CARD_BG};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 10px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {ACCENT};
}}
QTextEdit {{
    background: {CARD_BG};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 4px;
    font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace;
    font-size: 12px;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {MUTED};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QProgressBar {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 4px;
    height: 18px;
    text-align: center;
    color: {TEXT_PRI};
    font-weight: 600;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT}, stop:1 #6ab4ff);
    border-radius: 4px;
}}
QTreeWidget, QListWidget, QTableWidget {{
    background: {CARD_BG};
    color: {TEXT_PRI};
    border: 1px solid {BORDER};
    border-radius: 4px;
    alternate-background-color: {PANEL_BG};
    gridline-color: {BORDER};
}}
QTreeWidget::item:selected, QListWidget::item:selected,
QTableWidget::item:selected {{
    background: {ACCENT};
    color: #fff;
}}
QTreeWidget::item:hover, QListWidget::item:hover {{
    background: {MUTED};
}}
QHeaderView::section {{
    background: {PANEL_BG};
    color: {TEXT_SEC};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 6px 10px;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
QScrollBar:vertical {{
    background: {DARK_BG};
    width: 8px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {MUTED};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar:horizontal {{
    background: {DARK_BG};
    height: 8px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: {MUTED};
    border-radius: 4px;
    min-width: 30px;
}}
QSplitter::handle {{
    background: {BORDER};
}}
QToolTip {{
    background: {CARD_BG};
    color: {TEXT_PRI};
    border: 1px solid {ACCENT};
    border-radius: 4px;
    padding: 4px 8px;
}}
QStatusBar {{
    background: {DARK_BG};
    color: {TEXT_SEC};
    border-top: 1px solid {BORDER};
}}
QLabel#heading {{
    font-size: 18px;
    font-weight: 700;
    color: {TEXT_PRI};
}}
QLabel#subheading {{
    font-size: 12px;
    color: {TEXT_SEC};
}}
QLabel#badge {{
    background: {ACCENT};
    color: #fff;
    border-radius: 10px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 700;
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT PARSER  — reads multi-block VVM output files
# ─────────────────────────────────────────────────────────────────────────────

class SimResult:
    """Holds parsed simulation results for one output file."""

    def __init__(self):
        self.path: str = ""
        self.label: str = ""
        self.times: np.ndarray = np.array([])
        self.sealevels: np.ndarray = np.array([])
        self.tops: List[np.ndarray] = []      # list of (ncols, nrows)
        self.seds: List[List[np.ndarray]] = []  # [nsed][timestep]
        self.ncols: int = 0
        self.nrows: int = 0
        self.cellside: float = 100.0
        self.nsed: int = 0

    @property
    def ntimes(self) -> int:
        return len(self.times)

    def top_at(self, ti: int) -> np.ndarray:
        return self.tops[ti]

    def sed_at(self, is_: int, ti: int) -> np.ndarray:
        if is_ < len(self.seds) and ti < len(self.seds[is_]):
            return self.seds[is_][ti]
        return np.zeros((self.ncols, self.nrows))

    def mean_grain_size(self, ti: int, diameters=None) -> np.ndarray:
        if diameters is None or self.nsed == 0:
            return np.zeros((self.ncols, self.nrows))
        diams = np.array(diameters[:self.nsed], dtype=float)
        mg = np.zeros((self.ncols, self.nrows))
        total = np.zeros((self.ncols, self.nrows))
        for i, d in enumerate(diams):
            if i < len(self.seds) and ti < len(self.seds[i]):
                f = self.seds[i][ti]
                mg += f * d
                total += f
        return np.where(total > 0, mg / total, 0.0)

    def shoreline_x(self, ti: int) -> Optional[float]:
        top = self.tops[ti]
        sl  = self.sealevels[ti]
        mid = self.nrows // 2
        col = top[:, mid]
        for i in range(len(col) - 1):
            if (col[i] - sl) * (col[i+1] - sl) <= 0:
                return i + (sl - col[i]) / (col[i+1] - col[i])
        return None


def parse_output(path: str) -> SimResult:
    """Parse a SedArch multi-block VVM output file."""
    result = SimResult()
    result.path = path
    result.label = Path(path).stem

    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read()

    # Split into per-timestep blocks
    parts = re.split(r'(?=\nTIME\s*=)', raw)

    def _parse_matrix(text: str, key: str) -> Optional[np.ndarray]:
        m = re.search(rf'{key}\s*=\s*\n([\s\S]*?)(?=\n[A-Z_]|\Z)', text)
        if not m:
            return None
        nums = list(map(float, m.group(1).split()))
        if not nums:
            return None
        return np.array(nums, dtype=np.float32)

    # Determine grid shape from first block with TOP
    ref_shape = None
    for part in parts:
        if "TOP" not in part:
            continue
        tm = re.search(r'TIME\s*=\s*([\d.eE+\-]+)', part)
        slm = re.search(r'SEALEVEL\s*=\s*([\d.eE+\-]+)', part)
        top_raw = _parse_matrix(part, "TOP")
        if top_raw is None:
            continue
        t_val = float(tm.group(1)) if tm else 0.0
        sl_val = float(slm.group(1)) if slm else 0.0

        # We don't know nrows/ncols yet — infer from number of rows in text
        top_block_m = re.search(r'TOP\s*=\s*\n([\s\S]*?)(?=\n[A-Z_]|\Z)', part)
        if top_block_m:
            rows_text = [l.strip() for l in top_block_m.group(1).strip().splitlines() if l.strip()]
            nrows = len(rows_text)
            if nrows > 0:
                ncols = len(rows_text[0].split())
                ref_shape = (ncols, nrows)
                result.ncols = ncols
                result.nrows = nrows
        break

    if ref_shape is None:
        return result

    ncols, nrows = ref_shape

    # Figure out nsed
    nsed = 0
    for part in parts:
        for k in range(1, 10):
            if f"SED{k}" in part:
                nsed = max(nsed, k)

    result.nsed = nsed
    sed_lists: List[List] = [[] for _ in range(nsed)]

    # Parse all blocks
    for part in parts:
        if "TOP" not in part:
            continue
        tm  = re.search(r'TIME\s*=\s*([\d.eE+\-]+)', part)
        slm = re.search(r'SEALEVEL\s*=\s*([\d.eE+\-]+)', part)
        top_raw = _parse_matrix(part, "TOP")
        if top_raw is None:
            continue
        t_val  = float(tm.group(1))  if tm  else 0.0
        sl_val = float(slm.group(1)) if slm else 0.0

        try:
            top = top_raw.reshape(ncols, nrows)
        except ValueError:
            continue

        result.times     = np.append(result.times, t_val)
        result.sealevels = np.append(result.sealevels, sl_val)
        result.tops.append(top)

        for is_ in range(nsed):
            sed_raw = _parse_matrix(part, f"SED{is_+1}")
            if sed_raw is not None and sed_raw.size == ncols * nrows:
                sed_lists[is_].append(sed_raw.reshape(ncols, nrows))
            else:
                if sed_lists[is_]:
                    sed_lists[is_].append(sed_lists[is_][-1].copy())
                else:
                    sed_lists[is_].append(np.full((ncols, nrows),
                                                   1.0 / nsed, dtype=np.float32))

    result.seds = sed_lists
    return result


# ─────────────────────────────────────────────────────────────────────────────
# MATPLOTLIB CANVAS HELPER
# ─────────────────────────────────────────────────────────────────────────────

class MplCanvas(FigureCanvas):
    """Matplotlib figure embedded in Qt with dark theme."""

    def __init__(self, nrows=1, ncols=1, figsize=(6, 4), tight=True):
        with plt.style.context(MPL_STYLE):
            self.fig = Figure(figsize=figsize, facecolor=DARK_BG)
        super().__init__(self.fig)
        self.setStyleSheet(f"background: {DARK_BG};")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._nrows = nrows
        self._ncols = ncols
        self._tight = tight
        self.axes = []
        self._make_axes()

    def _make_axes(self):
        self.fig.clear()
        self.axes = []
        for i in range(self._nrows * self._ncols):
            ax = self.fig.add_subplot(self._nrows, self._ncols, i + 1)
            _style_ax(ax)
            self.axes.append(ax)
        if self._tight:
            self.fig.tight_layout(pad=1.5)

    def ax(self, i=0) -> plt.Axes:
        return self.axes[i]

    def clear_and_draw(self):
        self._make_axes()
        self.draw()

    def redraw(self):
        if self._tight:
            try:
                self.fig.tight_layout(pad=1.5)
            except Exception:
                pass
        self.draw()


def _style_ax(ax):
    ax.set_facecolor(PANEL_BG)
    ax.tick_params(colors=TEXT_SEC, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)
    ax.xaxis.label.set_color(TEXT_SEC)
    ax.yaxis.label.set_color(TEXT_SEC)
    ax.title.set_color(TEXT_PRI)
    ax.grid(True, color=BORDER, linewidth=0.5, alpha=0.7)


# ─────────────────────────────────────────────────────────────────────────────
# SIMULATION WORKER  (QThread)
# ─────────────────────────────────────────────────────────────────────────────

class SimulationWorker(QThread):
    """Runs the SedArch simulation in a background thread."""

    progress    = Signal(int, int, float)          # step, total, time_ka
    live_update = Signal(int, int, np.ndarray, float)  # step, total, top, sealevel
    log_line    = Signal(str)
    finished    = Signal(bool, str)                # success, message

    def __init__(self, input_file: str, sedarch_path: str):
        super().__init__()
        self.input_file   = input_file
        self.sedarch_path = sedarch_path
        self._cancel      = False
        self._mutex       = QMutex()

    def cancel(self):
        with QMutexLocker(self._mutex):
            self._cancel = True

    def run(self):
        sys.path.insert(0, self.sedarch_path)
        old_cwd = os.getcwd()
        try:
            import importlib
            import sedarch.__main__ as sm
            importlib.reload(sm)

            def callback(step, total, time_ka, top, sealevel, seq):
                self.progress.emit(step, total, time_ka)
                self.live_update.emit(step, total, top, sealevel)
                with QMutexLocker(self._mutex):
                    return self._cancel

            # Redirect stderr
            import io
            old_stderr = sys.stderr
            log_buf = io.StringIO()
            log_signal = self.log_line

            class Tee:
                def write(self, s):
                    log_buf.write(s)
                    if s.strip():
                        log_signal.emit(s.rstrip())
                def flush(self): pass

            sys.stderr = Tee()

            # Run from the project root (sedarch_path) so OUTFILE resolves
            # to Output/ and INCLUDE paths resolve relative to the VVM file
            os.chdir(self.sedarch_path)
            try:
                sm.run(self.input_file, step_callback=callback)
                sys.stderr = old_stderr
                self.finished.emit(True, "Run completed successfully.")
            except Exception as e:
                sys.stderr = old_stderr
                self.finished.emit(False, f"ERROR: {e}")

        except ImportError as e:
            self.finished.emit(False, f"Cannot import sedarch: {e}\n"
                                       "Check SedArch path in Settings.")
        finally:
            os.chdir(old_cwd)
            # Remove the path we inserted to avoid accumulation across reruns
            try:
                sys.path.remove(self.sedarch_path)
            except ValueError:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# CURVE EDITOR DIALOG
# ─────────────────────────────────────────────────────────────────────────────

class CurveEditorDialog(QDialog):
    """Modal dialog for editing a 2-column X/Y curve with live preview."""

    def __init__(self, title: str, data: np.ndarray,
                 x_label="X", y_label="Y", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Curve — {title}")
        self.setMinimumSize(700, 500)
        self._data = data.copy() if data is not None else np.zeros((0, 2))

        layout = QHBoxLayout(self)
        layout.setSpacing(10)

        # Left: table
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)

        lv.addWidget(QLabel(f"<b>{title}</b>"))

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([x_label, y_label])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self._populate_table()
        lv.addWidget(self.table)

        btns = QHBoxLayout()
        add_btn = QPushButton("+ Add Row")
        del_btn = QPushButton("− Delete Row")
        load_btn = QPushButton("📂 Load .vvm…")
        add_btn.clicked.connect(self._add_row)
        del_btn.clicked.connect(self._del_row)
        load_btn.clicked.connect(self._load_from_vvm)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addWidget(load_btn)
        btns.addStretch()
        lv.addLayout(btns)

        # Right: preview
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(QLabel("Preview"))
        self.canvas = MplCanvas(figsize=(4, 4))
        rv.addWidget(self.canvas)

        layout.addWidget(left, 1)
        layout.addWidget(right, 1)

        # Dialog buttons
        dbb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dbb.accepted.connect(self.accept)
        dbb.rejected.connect(self.reject)

        wrapper = QVBoxLayout()
        wrapper.addLayout(layout)
        wrapper.addWidget(dbb)
        self.setLayout(wrapper)

        self.table.itemChanged.connect(self._refresh_preview)
        self._refresh_preview()

    def _populate_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._data))
        for i, (x, y) in enumerate(self._data):
            self.table.setItem(i, 0, QTableWidgetItem(f"{x:.4g}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{y:.4g}"))
        self.table.blockSignals(False)

    def _add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem("0"))
        self.table.setItem(r, 1, QTableWidgetItem("0"))

    def _del_row(self):
        rows = sorted({i.row() for i in self.table.selectedItems()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)
        self._refresh_preview()

    def _load_from_vvm(self):
        default_dir = str(Path(__file__).parent / "Input" / "curves")
        path, _ = QFileDialog.getOpenFileName(
            self, "Load curve from VVM file", default_dir,
            "VVM files (*.vvm);;All files (*)")
        if not path:
            return
        rows = []
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for raw in fh:
                    line = raw.split("!")[0].strip()   # strip inline comments
                    if not line or "=" in line:        # skip blank / keyword lines
                        continue
                    parts = line.split()
                    if len(parts) == 2:
                        try:
                            rows.append((float(parts[0]), float(parts[1])))
                        except ValueError:
                            pass
        except OSError as e:
            QMessageBox.warning(self, "Load failed", str(e))
            return
        if not rows:
            QMessageBox.warning(self, "Load failed",
                                "No two-column numeric data found in the file.")
            return
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        for i, (x, y) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(f"{x:.6g}"))
            self.table.setItem(i, 1, QTableWidgetItem(f"{y:.6g}"))
        self.table.blockSignals(False)
        self._refresh_preview()

    def _refresh_preview(self):
        data = self._read_table()
        ax = self.canvas.ax()
        ax.clear()
        _style_ax(ax)
        if len(data) >= 2:
            ax.plot(data[:, 0], data[:, 1], color=ACCENT, lw=2, marker="o",
                    markersize=4, markerfacecolor=ACCENT2)
            ax.fill_between(data[:, 0], data[:, 1], alpha=0.15, color=ACCENT)
        ax.set_xlabel(self.table.horizontalHeaderItem(0).text())
        ax.set_ylabel(self.table.horizontalHeaderItem(1).text())
        self.canvas.redraw()

    def _read_table(self) -> np.ndarray:
        rows = []
        for i in range(self.table.rowCount()):
            try:
                x = float(self.table.item(i, 0).text())
                y = float(self.table.item(i, 1).text())
                rows.append([x, y])
            except (ValueError, AttributeError):
                pass
        return np.array(rows) if rows else np.zeros((0, 2))

    def get_data(self) -> np.ndarray:
        return self._read_table()


# ─────────────────────────────────────────────────────────────────────────────
# VVM PARAMETER EDITOR
# ─────────────────────────────────────────────────────────────────────────────

class InputEditorWidget(QWidget):
    """Tab 1 — edit VVM input parameters."""

    file_saved = Signal(str)  # emitted when user saves

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vvm_path: Optional[str] = None
        self._params: Dict[str, Any] = {}
        self._curves: Dict[str, Optional[np.ndarray]] = {}
        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # Toolbar
        tb = QHBoxLayout()
        title = QLabel("Input Editor")
        title.setObjectName("heading")
        tb.addWidget(title)
        tb.addStretch()

        self.new_btn  = QPushButton("⊕  New")
        self.open_btn = QPushButton("📂  Open VVM…")
        self.save_btn = QPushButton("💾  Save")
        self.saveas_btn = QPushButton("Save As…")
        self.save_btn.setObjectName("primary")

        self.new_btn.clicked.connect(self._on_new)
        self.open_btn.clicked.connect(self._on_open)
        self.save_btn.clicked.connect(self._on_save)
        self.saveas_btn.clicked.connect(self._on_save_as)

        for w in [self.new_btn, self.open_btn, self.save_btn, self.saveas_btn]:
            tb.addWidget(w)
        root.addLayout(tb)

        self.file_label = QLabel("No file loaded")
        self.file_label.setObjectName("subheading")
        self.file_label.setFixedHeight(20)
        self.file_label.setWordWrap(False)
        root.addWidget(self.file_label)

        # Splitter: left tree | right form
        splitter = QSplitter(Qt.Horizontal)

        # Left: section tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Sections")
        self.tree.setMaximumWidth(220)
        self.tree.itemClicked.connect(self._on_tree_select)
        splitter.addWidget(self.tree)

        # Right: stacked forms via scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.form_widget = QWidget()
        self.form_layout = QVBoxLayout(self.form_widget)
        self.form_layout.setSpacing(12)
        scroll.setWidget(self.form_widget)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter)
        self._build_tree()
        self._build_forms()
        self._load_defaults()

    def _build_tree(self):
        self.tree.clear()
        sections = [
            ("🗃  General",      "general"),
            ("🌐  Grid",          "grid"),
            ("🪨  Sediments",     "sediments"),
            ("🌊  Sea Level",     "sealevel"),
            ("🌀  Dispersion",    "dispersion"),
            ("🌱  Growth",        "growth"),
            ("📂  File Paths",    "files"),
        ]
        self._tree_items = {}
        for label, key in sections:
            item = QTreeWidgetItem([label])
            self.tree.addTopLevelItem(item)
            self._tree_items[key] = item
        self.tree.expandAll()

    def _build_forms(self):
        fl = self.form_layout
        # Clear previous
        while fl.count():
            child = fl.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._widgets = {}

        # ── General ──────────────────────────────────────────────────────────
        gb_gen = self._group("General", fl)
        self._add_field(gb_gen, "TITLE",         "Title",               QLineEdit)
        self._add_field(gb_gen, "STEP_COUNT",     "Step Count",          QSpinBox,
                        extra={"minimum": 1, "maximum": 10000})
        self._add_field(gb_gen, "STEP_DURATION",  "Step Duration (ka)",  QDoubleSpinBox,
                        extra={"minimum": 0.001, "maximum": 10000, "decimals": 3})
        self._add_field(gb_gen, "INITIAL_TIME",   "Initial Time (ka)",   QDoubleSpinBox,
                        extra={"minimum": -1e9, "maximum": 1e9, "decimals": 3})

        # ── Grid ─────────────────────────────────────────────────────────────
        gb_grid = self._group("Grid", fl)
        self._add_field(gb_grid, "CELLSIDE", "Cell Side (m)", QDoubleSpinBox,
                        extra={"minimum": 1, "maximum": 1e7, "decimals": 1})

        # Topography source: radio group
        self._topo_btn_file  = QRadioButton("Include file")
        self._topo_btn_const = QRadioButton("Constant elevation")
        self._topo_btn_file.setChecked(True)
        topo_bg = QButtonGroup(self)
        topo_bg.addButton(self._topo_btn_file)
        topo_bg.addButton(self._topo_btn_const)
        radio_row = QHBoxLayout()
        radio_row.addWidget(self._topo_btn_file)
        radio_row.addWidget(self._topo_btn_const)
        radio_row.addStretch()
        gb_grid.layout().addRow("Topography Source", radio_row)

        # --- File picker row ---
        self._topo_file_widget = QWidget()
        file_row = QHBoxLayout(self._topo_file_widget)
        file_row.setContentsMargins(0, 0, 0, 0)
        self._topo_file_edit = QLineEdit()
        self._topo_file_edit.setPlaceholderText("maps/top_slope_4p_60x40.vvm")
        topo_browse_btn = QPushButton("📂 …")
        topo_browse_btn.setFixedWidth(36)
        topo_browse_btn.clicked.connect(self._browse_topo_file)
        file_row.addWidget(self._topo_file_edit)
        file_row.addWidget(topo_browse_btn)
        gb_grid.layout().addRow("Topography File", self._topo_file_widget)

        # --- Constant elevation row ---
        self._topo_const_widget = QWidget()
        const_row = QHBoxLayout(self._topo_const_widget)
        const_row.setContentsMargins(0, 0, 0, 0)
        self._topo_nx = QSpinBox(); self._topo_nx.setRange(2, 9999); self._topo_nx.setValue(61)
        self._topo_ny = QSpinBox(); self._topo_ny.setRange(2, 9999); self._topo_ny.setValue(41)
        self._topo_elev = QDoubleSpinBox()
        self._topo_elev.setRange(-1e6, 1e6); self._topo_elev.setValue(0.0); self._topo_elev.setDecimals(2)
        const_row.addWidget(QLabel("NX:")); const_row.addWidget(self._topo_nx)
        const_row.addWidget(QLabel("NY:")); const_row.addWidget(self._topo_ny)
        const_row.addWidget(QLabel("Elev (m):")); const_row.addWidget(self._topo_elev)
        const_row.addStretch()
        gb_grid.layout().addRow("Grid Size / Elev", self._topo_const_widget)

        # Show/hide based on radio selection
        self._topo_const_widget.setVisible(False)
        self._topo_btn_file.toggled.connect(
            lambda checked: (self._topo_file_widget.setVisible(checked),
                             self._topo_const_widget.setVisible(not checked))
        )

        # ── Sediments ────────────────────────────────────────────────────────
        gb_sed = self._group("Sediments", fl)
        for i in range(1, 5):
            self._add_field(gb_sed, f"SED_DIAM_{i}", f"Diameter {i} (mm)",
                            QDoubleSpinBox,
                            extra={"minimum": 0.001, "maximum": 100000, "decimals": 3})
            self._add_field(gb_sed, f"SED_FRAC_{i}", f"Base Fraction {i}",
                            QDoubleSpinBox,
                            extra={"minimum": 0, "maximum": 1, "decimals": 3,
                                   "singleStep": 0.05})
        self._add_field(gb_sed, "NSED", "# of Sediment Types", QSpinBox,
                        extra={"minimum": 1, "maximum": 8})

        # ── Sea Level ─────────────────────────────────────────────────────────
        gb_sl = self._group("Sea Level", fl)
        self._add_field(gb_sl, "SEALEVEL", "Constant Sea Level (m)", QDoubleSpinBox,
                        extra={"minimum": -10000, "maximum": 10000, "decimals": 2})
        btn_sl = QPushButton("Edit TIME_SEALEVEL_CURVE…")
        btn_sl.clicked.connect(lambda: self._edit_curve("TIME_SEALEVEL_CURVE",
                                                         "Time (ka)", "Sea Level (m)"))
        gb_sl.layout().addRow("Sea Level Curve", btn_sl)

        # ── Dispersion ────────────────────────────────────────────────────────
        gb_disp = self._group("Dispersion", fl)
        self._add_field(gb_disp, "DISP_FACTOR", "Dispersion Factor (m²/ka)",
                        QDoubleSpinBox,
                        extra={"minimum": 0, "maximum": 1e9, "decimals": 4,
                               "singleStep": 0.01})
        btn_ldc = QPushButton("Edit LEVEL_DISP_CURVE…")
        btn_ldc.clicked.connect(lambda: self._edit_curve("LEVEL_DISP_CURVE",
                                                          "Elevation rel. SL (m)",
                                                          "Multiplier"))
        gb_disp.layout().addRow("Level Dispersion Curve", btn_ldc)

        # ── Growth ────────────────────────────────────────────────────────────
        gb_gr = self._group("Growth (Carbonates)", fl)
        self._add_field(gb_gr, "GROWTH_FACTOR", "Growth Factor",
                        QDoubleSpinBox,
                        extra={"minimum": 0, "maximum": 1e6, "decimals": 4})

        # ── File Paths ─────────────────────────────────────────────────────────
        gb_fp = self._group("File Paths", fl)
        self._add_file_row(gb_fp, "OUTFILE", "Output File")

        # ── Apply button ────────────────────────────────────────────────────────
        apply_btn = QPushButton("Apply Changes to VVM")
        apply_btn.setToolTip("Build VVM text from the fields above and update the editor")
        apply_btn.clicked.connect(self._apply_fields_to_raw)
        fl.addWidget(apply_btn)

        # ── Raw VVM editor ─────────────────────────────────────────────────────
        gb_raw = self._group("Raw VVM (Advanced)", fl)
        self.raw_edit = QTextEdit()
        self.raw_edit.setMinimumHeight(200)
        self.raw_edit.setPlaceholderText(
            "The full VVM file content will appear here after loading.\n"
            "You can edit it directly for advanced parameters.")
        gb_raw.layout().addRow(self.raw_edit)

        fl.addStretch()

    def _group(self, title: str, parent_layout: QVBoxLayout) -> QGroupBox:
        gb = QGroupBox(title)
        fl = QFormLayout()
        fl.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fl.setSpacing(8)
        gb.setLayout(fl)
        parent_layout.addWidget(gb)
        return gb

    def _add_field(self, gb: QGroupBox, key: str, label: str,
                   widget_cls, extra: dict = None):
        w = widget_cls()
        for k, v in (extra or {}).items():
            getattr(w, f"set{k[0].upper()}{k[1:]}")(v)
        if isinstance(w, QLineEdit):
            w.setPlaceholderText(key)
        self._widgets[key] = w
        gb.layout().addRow(label, w)

    def _add_file_row(self, gb: QGroupBox, key: str, label: str):
        row = QHBoxLayout()
        le = QLineEdit()
        le.setPlaceholderText("path/to/output.vvm")
        btn = QPushButton("…")
        btn.setFixedWidth(30)
        btn.clicked.connect(lambda: self._browse_file(le))
        row.addWidget(le)
        row.addWidget(btn)
        self._widgets[key] = le
        container = QWidget()
        container.setLayout(row)
        gb.layout().addRow(label, container)

    def _browse_topo_file(self):
        default_dir = str(Path(__file__).parent / "Input" / "maps")
        p, _ = QFileDialog.getOpenFileName(self, "Topography VVM file", default_dir,
                                           "VVM files (*.vvm);;All files (*)")
        if p:
            # Store as relative path from Input/ if possible
            try:
                rel = Path(p).relative_to(Path(__file__).parent / "Input")
                self._topo_file_edit.setText(str(rel).replace("\\", "/"))
            except ValueError:
                self._topo_file_edit.setText(p.replace("\\", "/"))

    def _browse_file(self, le: QLineEdit):
        default_dir = str(Path(__file__).parent / "Output")
        p, _ = QFileDialog.getSaveFileName(self, "Output file", default_dir, "VVM files (*.vvm)")
        if p:
            le.setText(p)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_new(self):
        self._vvm_path = None
        self.file_label.setText("New file (unsaved)")
        self.file_label.setToolTip("")
        self._load_defaults()
        self.raw_edit.setPlainText(self._default_vvm_text())

    def _on_open(self):
        default_dir = str(Path(__file__).parent / "Input")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open VVM input file", default_dir,
            "VVM files (*.vvm);;All files (*)")
        if path:
            self.load_file(path)

    def _on_save(self):
        if not self._vvm_path:
            self._on_save_as()
        else:
            self._write_file(self._vvm_path)

    def _on_save_as(self):
        default_dir = str(Path(__file__).parent / "Input")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save VVM file", default_dir,
            "VVM files (*.vvm);;All files (*)")
        if path:
            self._vvm_path = path
            self._write_file(path)

    def _on_tree_select(self, item: QTreeWidgetItem, col: int):
        label = item.text(0).split()[-1].lower()
        # Scroll form to matching group
        for i in range(self.form_layout.count()):
            w = self.form_layout.itemAt(i).widget()
            if isinstance(w, QGroupBox):
                if label in w.title().lower():
                    self.form_widget.parent().parent().ensureWidgetVisible(w)
                    break

    def _edit_curve(self, key: str, x_label: str, y_label: str):
        data = self._curves.get(key, np.zeros((0, 2)))
        dlg = CurveEditorDialog(key, data, x_label, y_label, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._curves[key] = dlg.get_data()

    def _apply_fields_to_raw(self):
        """Rebuild VVM text from all form fields and push it into the raw editor."""
        self.raw_edit.setPlainText(self._build_vvm_text())

    # ── Data helpers ──────────────────────────────────────────────────────────

    def _load_defaults(self):
        defaults = {
            "TITLE": "SedArch Model",
            "STEP_COUNT": 10,
            "STEP_DURATION": 20.0,
            "INITIAL_TIME": 0.0,
            "CELLSIDE": 100.0,
            "NSED": 4,
            "SED_DIAM_1": 20.0, "SED_FRAC_1": 0.25,
            "SED_DIAM_2": 10.0, "SED_FRAC_2": 0.25,
            "SED_DIAM_3": 5.0,  "SED_FRAC_3": 0.25,
            "SED_DIAM_4": 1.0,  "SED_FRAC_4": 0.25,
            "SEALEVEL": 0.0,
            "DISP_FACTOR": 0.1,
            "GROWTH_FACTOR": 0.0,
            "OUTFILE": str(Path(__file__).parent / "Output" / "out.vvm").replace("\\", "/"),
        }
        for key, val in defaults.items():
            w = self._widgets.get(key)
            if w is None:
                continue
            if isinstance(w, QLineEdit):
                w.setText(str(val))
            elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                w.setValue(float(val))

    def load_file(self, path: str):
        self._vvm_path = path
        self.file_label.setText(f"📄  {os.path.basename(path)}")
        self.file_label.setToolTip(path)
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
            self.raw_edit.setPlainText(text)
            self._parse_into_fields(text)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot open file:\n{e}")

    def _parse_into_fields(self, text: str):
        def _get(key):
            m = re.search(rf'^\s*{key}\s*=\s*"?([^"\n]+)"?', text, re.MULTILINE)
            return m.group(1).strip() if m else None

        mappings = {
            "TITLE": ("TITLE", str),
            "STEP_COUNT": ("STEP_COUNT", int),
            "STEP_DURATION": ("STEP_DURATION", float),
            "INITIAL_TIME": ("INITIAL_TIME", float),
            "CELLSIDE": ("CELLSIDE", float),
            "SEALEVEL": ("SEALEVEL", float),
            "DISP_FACTOR": ("DISP_FACTOR", float),
            "GROWTH_FACTOR": ("GROWTH_FACTOR", float),
        }
        for key, (vvm_key, typ) in mappings.items():
            raw = _get(vvm_key)
            if raw is None:
                continue
            try:
                val = typ(raw.split("!")[0].strip())
                w = self._widgets.get(key)
                if isinstance(w, QLineEdit):
                    w.setText(str(val))
                elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                    w.setValue(float(val))
            except Exception:
                pass

        # Sediment diameters
        m_sed = re.search(r'SED_DIAMETERS\s*=\s*([^\n!]+)', text)
        if m_sed:
            diams = list(map(float, m_sed.group(1).strip().split()))
            for i, d in enumerate(diams[:4]):
                w = self._widgets.get(f"SED_DIAM_{i+1}")
                if w:
                    w.setValue(d)
            w_n = self._widgets.get("NSED")
            if w_n:
                w_n.setValue(len(diams))

        # Output file – always store as absolute path
        m_out = re.search(r'OUTFILE\s*=\s*"([^"]+)"', text)
        if m_out:
            w = self._widgets.get("OUTFILE")
            if w:
                out_raw = m_out.group(1)
                if not os.path.isabs(out_raw):
                    # Resolve relative to project root (folder containing this script)
                    out_raw = str(
                        (Path(__file__).parent / out_raw).resolve()
                    ).replace("\\", "/")
                w.setText(out_raw)

        # Topography source: INCLUDE file or inline TOP =
        m_inc_topo = re.search(
            r'^[ \t]*INCLUDE\s*=\s*"([^"]*(?:maps|top)[^"]*\.vvm)"',
            text, re.MULTILINE | re.IGNORECASE)
        if m_inc_topo:
            self._topo_btn_file.setChecked(True)
            self._topo_file_edit.setText(m_inc_topo.group(1))
        else:
            m_top = re.search(r'^\s*TOP\s*=', text, re.MULTILINE)
            if m_top:
                # Try to infer NX/NY from the first numeric block
                block = text[m_top.end():]
                rows = []
                for ln in block.splitlines():
                    ln = ln.split("!")[0].strip()
                    if not ln:
                        continue
                    if re.match(r'[A-Z_]', ln):
                        break
                    try:
                        rows.append(list(map(float, ln.split())))
                    except ValueError:
                        break
                if rows:
                    nx = len(rows[0])
                    ny = len(rows)
                    elev = rows[0][0] if rows[0] else 0.0
                    self._topo_btn_const.setChecked(True)
                    self._topo_nx.setValue(nx)
                    self._topo_ny.setValue(ny)
                    self._topo_elev.setValue(elev)

    def _write_file(self, path: str):
        # Use raw editor content if edited; otherwise rebuild from fields
        raw = self.raw_edit.toPlainText().strip()
        if raw:
            content = raw
        else:
            content = self._build_vvm_text()
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.file_saved.emit(path)
            QMessageBox.information(self, "Saved", f"Saved to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot save:\n{e}")

    def _build_vvm_text(self) -> str:
        def _v(key):
            w = self._widgets.get(key)
            if w is None:
                return ""
            if isinstance(w, QLineEdit):
                return w.text()
            return str(w.value())

        diams = " ".join(_v(f"SED_DIAM_{i}") for i in range(1, 5)
                         if self._widgets.get(f"SED_DIAM_{i}") is not None)
        fracs = " ".join(_v(f"SED_FRAC_{i}") for i in range(1, 5)
                         if self._widgets.get(f"SED_FRAC_{i}") is not None)

        # Topography block
        topo_lines = []
        if self._topo_btn_file.isChecked():
            topo_path = self._topo_file_edit.text().strip()
            if topo_path:
                topo_lines = [f'INCLUDE = "{topo_path}"']
        else:
            nx = self._topo_nx.value()
            ny = self._topo_ny.value()
            elev = self._topo_elev.value()
            row_str = "  " + "  ".join(f"{elev:.2f}" for _ in range(nx))
            topo_lines = ["TOP ="] + [row_str] * ny

        lines = [
            f'TITLE = "{_v("TITLE")}"',
            f'OUTFILE = "{_v("OUTFILE")}"',
            f'SED_DIAMETERS = {diams}',
            f'CELLSIDE = {_v("CELLSIDE")}',
        ]
        if topo_lines:
            lines += [''] + topo_lines
        lines += [
            f'',
            f'! Sediment base fractions',
        ]
        for i, f in enumerate(fracs.split(), 1):
            lines.append(f'SED{i} = {f}')

        lines += [
            f'',
            f'STEP_DURATION = {_v("STEP_DURATION")}',
            f'STEP_COUNT = {_v("STEP_COUNT")}',
            f'INITIAL_TIME = {_v("INITIAL_TIME")}',
            f'SEALEVEL = {_v("SEALEVEL")}',
            f'',
            f'DISP_FACTOR = {_v("DISP_FACTOR")}',
            f'GROWTH_FACTOR = {_v("GROWTH_FACTOR")}',
        ]

        sl_curve = self._curves.get("TIME_SEALEVEL_CURVE")
        if sl_curve is not None and len(sl_curve) > 0:
            lines += ["", "TIME_SEALEVEL_CURVE ="]
            for x, y in sl_curve:
                lines.append(f"  {x:.4g}  {y:.4g}")

        ldc = self._curves.get("LEVEL_DISP_CURVE")
        if ldc is not None and len(ldc) > 0:
            lines += ["", "LEVEL_DISP_CURVE ="]
            for x, y in ldc:
                lines.append(f"  {x:.4g}  {y:.4g}")

        return "\n".join(lines) + "\n"

    def _default_vvm_text(self) -> str:
        _out = str(Path(__file__).parent / "Output" / "out.vvm").replace("\\", "/")
        return (
            'TITLE = "New SedArch Model"\n'
            f'OUTFILE = "{_out}"\n'
            'SED_DIAMETERS = 20 10 5 1\n'
            'CELLSIDE = 100\n'
            'SED1 = 0.25\nSED2 = 0.25\nSED3 = 0.25\nSED4 = 0.25\n'
            'STEP_DURATION = 20\n'
            'STEP_COUNT = 10\n'
            'SEALEVEL = 0\n'
            'DISP_FACTOR = 0.1\n'
        )

    def get_input_path(self) -> Optional[str]:
        return self._vvm_path


# ─────────────────────────────────────────────────────────────────────────────
# RUN WIDGET
# ─────────────────────────────────────────────────────────────────────────────

class RunWidget(QWidget):
    """Tab 2 — run simulation with progress and live preview."""

    run_complete = Signal(str)   # emits output VVM path

    def __init__(self, sedarch_path: str, parent=None):
        super().__init__(parent)
        self.sedarch_path = sedarch_path
        self._worker: Optional[SimulationWorker] = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # Main splitter: controls | live preview
        splitter = QSplitter(Qt.Horizontal)

        # ── Left panel: controls ──────────────────────────────────────────────
        left = QWidget()
        left.setMaximumWidth(400)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(8)

        # File selection
        gb_files = QGroupBox("Files")
        ff = QFormLayout()
        ff.setSpacing(8)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("path/to/input.vvm")
        input_browse = QPushButton("…")
        input_browse.setFixedWidth(30)
        input_browse.clicked.connect(self._browse_input)
        in_row = QHBoxLayout()
        in_row.addWidget(self.input_edit)
        in_row.addWidget(input_browse)
        in_cont = QWidget(); in_cont.setLayout(in_row)
        ff.addRow("Input VVM", in_cont)

        self.sedarch_edit = QLineEdit(self.sedarch_path)
        self.sedarch_edit.setPlaceholderText("path/to/sedarch_python/")
        sa_browse = QPushButton("…")
        sa_browse.setFixedWidth(30)
        sa_browse.clicked.connect(lambda: self._browse_dir(self.sedarch_edit))
        sa_row = QHBoxLayout()
        sa_row.addWidget(self.sedarch_edit)
        sa_row.addWidget(sa_browse)
        sa_cont = QWidget(); sa_cont.setLayout(sa_row)
        ff.addRow("SedArch Path", sa_cont)

        gb_files.setLayout(ff)
        lv.addWidget(gb_files)

        # Run controls
        gb_run = QGroupBox("Controls")
        gb_run.setMaximumHeight(140)
        rv = QVBoxLayout()
        rv.setSpacing(4)
        rv.setContentsMargins(6, 6, 6, 6)

        ctrl_row = QHBoxLayout()
        self.run_btn  = QPushButton("▶  Run")
        self.stop_btn = QPushButton("⬛  Stop")
        self.run_btn.setObjectName("primary")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._start_run)
        self.stop_btn.clicked.connect(self._stop_run)
        ctrl_row.addWidget(self.run_btn)
        ctrl_row.addWidget(self.stop_btn)
        rv.addLayout(ctrl_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(14)
        rv.addWidget(self.progress)

        # Status and elapsed on one line
        info_row = QHBoxLayout()
        self.status_lbl = QLabel("Ready")
        self.status_lbl.setObjectName("subheading")
        self.elapsed_lbl = QLabel("")
        self.elapsed_lbl.setObjectName("subheading")
        self.elapsed_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        info_row.addWidget(self.status_lbl)
        info_row.addWidget(self.elapsed_lbl)
        rv.addLayout(info_row)

        gb_run.setLayout(rv)
        lv.addWidget(gb_run)

        # Log
        gb_log = QGroupBox("Log")
        log_v = QVBoxLayout()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(150)
        log_v.addWidget(self.log)
        clear_log = QPushButton("Clear Log")
        clear_log.clicked.connect(self.log.clear)
        log_v.addWidget(clear_log)
        gb_log.setLayout(log_v)
        lv.addWidget(gb_log)

        splitter.addWidget(left)

        # ── Right panel: live preview ──────────────────────────────────────────
        right = QWidget()
        rv2 = QVBoxLayout(right)
        rv2.setContentsMargins(0, 0, 0, 0)

        gb_preview = QGroupBox("Live Preview — Topography")
        pv = QVBoxLayout()
        self.live_canvas = MplCanvas(figsize=(5, 4))
        pv.addWidget(self.live_canvas)
        self.step_lbl = QLabel("No data yet")
        self.step_lbl.setObjectName("subheading")
        self.step_lbl.setAlignment(Qt.AlignCenter)
        pv.addWidget(self.step_lbl)
        gb_preview.setLayout(pv)
        rv2.addWidget(gb_preview)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 9999])   # left panel fixed ~400 px; preview takes the rest

        root.addWidget(splitter)

        # Elapsed timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_elapsed)
        self._t_start = 0.0

    # ── Actions ───────────────────────────────────────────────────────────────

    def set_input(self, path: str):
        self.input_edit.setText(path)

    def _browse_input(self):
        default_dir = str(Path(__file__).parent / "Input")
        p, _ = QFileDialog.getOpenFileName(self, "Input VVM", default_dir,
                                            "VVM files (*.vvm);;All files (*)")
        if p:
            self.input_edit.setText(p)

    def _browse_dir(self, le: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, "Select directory",
                                              le.text() or ".")
        if d:
            le.setText(d)

    def _start_run(self):
        inp = self.input_edit.text().strip()
        if not inp or not os.path.exists(inp):
            QMessageBox.warning(self, "Error", "Please select a valid input VVM file.")
            return

        sa_path = self.sedarch_edit.text().strip()
        self.sedarch_path = sa_path

        self.log.clear()
        self.progress.setValue(0)
        self.status_lbl.setText("Running…")
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._t_start = time.time()
        self._timer.start(500)

        self._worker = SimulationWorker(inp, sa_path)
        self._worker.progress.connect(self._on_progress)
        self._worker.live_update.connect(self._on_live_update)
        self._worker.log_line.connect(self._on_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _stop_run(self):
        if self._worker:
            self._worker.cancel()
        self.status_lbl.setText("Cancelling…")

    def _on_progress(self, step: int, total: int, time_ka: float):
        pct = int(step / total * 100) if total else 0
        self.progress.setValue(pct)
        self.status_lbl.setText(
            f"Step {step}/{total}  ·  t = {time_ka:.1f} ka")

    def _on_live_update(self, step: int, total: int,
                         top: np.ndarray, sealevel: float):
        ax = self.live_canvas.ax()
        ax.clear()
        _style_ax(ax)
        ncols, nrows = top.shape
        im = ax.imshow(top.T, origin="lower", cmap="RdYlBu_r",
                       vmin=top.min(), vmax=top.max(), aspect="auto")
        ax.contour(top.T, levels=[sealevel], colors="cyan",
                   linewidths=1.2, linestyles="--")
        ax.set_title(f"t = step {step}/{total}", fontsize=9, color=TEXT_PRI)
        ax.axis("off")
        if not hasattr(self, "_live_cbar") or self._live_cbar is None:
            self._live_cbar = self.live_canvas.fig.colorbar(
                im, ax=ax, fraction=0.046, pad=0.04)
            self._live_cbar.ax.tick_params(colors=TEXT_SEC, labelsize=7)
        else:
            self._live_cbar.update_normal(im)
        try:
            self.live_canvas.fig.tight_layout(pad=1.0)
        except Exception:
            pass
        self.live_canvas.draw_idle()
        self.step_lbl.setText(f"Step {step}/{total}  ·  SL = {sealevel:.1f} m")

    def _on_log(self, line: str):
        self.log.append(line)

    def _on_finished(self, success: bool, msg: str):
        self._timer.stop()
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        color = SUCCESS if success else DANGER
        self.status_lbl.setText(f'<span style="color:{color}">{msg}</span>')
        self.log.append(f"\n{'✓' if success else '✗'} {msg}")
        self.progress.setValue(100 if success else self.progress.value())

        if success:
            inp = self.input_edit.text().strip()
            # Try to find output file from log first, then fall back to input VVM
            log_text = self.log.toPlainText()
            m = re.search(r'OUTFILE\s*=\s*"([^"]+)"', log_text)
            if not m:
                try:
                    with open(inp) as f:
                        content = f.read()
                    m = re.search(r'OUTFILE\s*=\s*"([^"]+)"', content)
                except Exception:
                    m = None
            if m:
                out = m.group(1)
                if not os.path.isabs(out):
                    # Resolve relative to project root so Output/ paths work correctly
                    out = str((Path(__file__).parent / out).resolve())
                self.run_complete.emit(out)

    def _update_elapsed(self):
        elapsed = time.time() - self._t_start
        mins, secs = divmod(int(elapsed), 60)
        self.elapsed_lbl.setText(f"⏱ {mins:02d}:{secs:02d}")


# ─────────────────────────────────────────────────────────────────────────────
# VISUALIZATION WIDGET
# ─────────────────────────────────────────────────────────────────────────────

_SED_CMAPS  = ["Reds", "Oranges", "Blues", "Greens",
               "Purples", "YlOrRd", "BuGn", "PiYG"]
_SED_COLORS = ["#ef5350", "#ffa726", "#42a5f5", "#66bb6a",
               "#ab47bc", "#ffca28", "#26a69a", "#d4e157"]


class VizWidget(QWidget):
    """Tab 3 — output visualization with timestep slider."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: Optional[SimResult] = None
        self._diameters: List[float] = [20, 10, 5, 1]
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left: controls ────────────────────────────────────────────────────
        ctrl = QWidget()
        ctrl.setFixedWidth(220)
        ctrl.setStyleSheet(f"background:{CARD_BG}; border-right:1px solid {BORDER};")
        cv = QVBoxLayout(ctrl)
        cv.setContentsMargins(12, 12, 12, 12)
        cv.setSpacing(10)

        cv.addWidget(QLabel("Visualization"))

        load_btn = QPushButton("📂  Load Output VVM…")
        load_btn.clicked.connect(self._on_load)
        cv.addWidget(load_btn)

        self.file_lbl = QLabel("No file loaded")
        self.file_lbl.setObjectName("subheading")
        self.file_lbl.setWordWrap(True)
        cv.addWidget(self.file_lbl)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color:{BORDER};")
        cv.addWidget(sep)

        # Plot type
        cv.addWidget(QLabel("Plot Type"))
        self.plot_type = QComboBox()
        self.plot_type.addItems([
            "Topography Map",
            "Sediment Maps",
            "E–W Cross-Section",
            "N–S Cross-Section",
            "Sea Level & Shoreline",
            "Grain-Size Timeseries",
            "Strat Column",
            "Net Change Map",
            "Overview (4-panel)",
        ])
        self.plot_type.currentIndexChanged.connect(self._update_plot)
        cv.addWidget(self.plot_type)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"color:{BORDER};")
        cv.addWidget(sep2)

        # Timestep slider
        cv.addWidget(QLabel("Timestep"))
        self.ts_slider = QSlider(Qt.Horizontal)
        self.ts_slider.setRange(0, 0)
        self.ts_slider.valueChanged.connect(self._on_ts_change)
        cv.addWidget(self.ts_slider)

        self.ts_lbl = QLabel("—")
        self.ts_lbl.setAlignment(Qt.AlignCenter)
        self.ts_lbl.setObjectName("subheading")
        cv.addWidget(self.ts_lbl)

        sep3 = QFrame(); sep3.setFrameShape(QFrame.HLine)
        sep3.setStyleSheet(f"color:{BORDER};")
        cv.addWidget(sep3)

        # Options
        cv.addWidget(QLabel("Options"))
        self.show_sl_cb = QCheckBox("Show shoreline")
        self.show_sl_cb.setChecked(True)
        self.show_sl_cb.toggled.connect(self._update_plot)
        cv.addWidget(self.show_sl_cb)

        self.show_grid_cb = QCheckBox("Show grid")
        self.show_grid_cb.setChecked(True)
        self.show_grid_cb.toggled.connect(self._update_plot)
        cv.addWidget(self.show_grid_cb)

        self.cmap_box = QComboBox()
        self.cmap_box.addItems(["RdYlBu_r", "terrain", "viridis",
                                 "plasma", "coolwarm", "seismic"])
        self.cmap_box.currentIndexChanged.connect(self._update_plot)
        cv.addWidget(QLabel("Colormap"))
        cv.addWidget(self.cmap_box)

        cv.addStretch()

        export_btn = QPushButton("📤  Export PNG…")
        export_btn.clicked.connect(self._export_png)
        cv.addWidget(export_btn)

        # ── Right: canvas ─────────────────────────────────────────────────────
        canvas_wrap = QWidget()
        cw_v = QVBoxLayout(canvas_wrap)
        cw_v.setContentsMargins(6, 6, 6, 6)

        self.canvas = MplCanvas(figsize=(9, 6))
        self.toolbar = NavToolbar(self.canvas, canvas_wrap)
        self.toolbar.setStyleSheet(f"background:{DARK_BG}; color:{TEXT_PRI};")
        cw_v.addWidget(self.toolbar)
        cw_v.addWidget(self.canvas)

        root.addWidget(ctrl)
        root.addWidget(canvas_wrap, 1)

    # ── Load / data ────────────────────────────────────────────────────────────

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load output VVM", "",
            "VVM files (*.vvm);;All files (*)")
        if path:
            self.load_result(path)

    def load_result(self, path: str):
        try:
            result = parse_output(path)
            if result.ntimes == 0:
                QMessageBox.warning(self, "Error",
                                    "No timestep data found in this file.")
                return
            self._result = result
            self.file_lbl.setText(f"📄 {Path(path).name}\n"
                                   f"{result.ntimes} steps · "
                                   f"{result.ncols}×{result.nrows}")
            self.ts_slider.setRange(0, result.ntimes - 1)
            self.ts_slider.setValue(result.ntimes - 1)
            self._update_plot()
        except Exception as e:
            QMessageBox.critical(self, "Parse Error", str(e))

    def _on_ts_change(self, val: int):
        if self._result and val < self._result.ntimes:
            t = self._result.times[val]
            sl = self._result.sealevels[val]
            self.ts_lbl.setText(f"t = {t:.1f} ka  ·  SL = {sl:.1f} m")
        self._update_plot()

    # ── Plot dispatcher ────────────────────────────────────────────────────────

    def _update_plot(self):
        if self._result is None:
            return
        pt = self.plot_type.currentText()
        self.canvas.fig.clear()
        ax = self.canvas.fig.add_subplot(111)
        _style_ax(ax)

        ti = self.ts_slider.value()
        cmap = self.cmap_box.currentText()

        try:
            if pt == "Topography Map":
                self._plot_topo(ax, ti, cmap)
            elif pt == "Sediment Maps":
                self._plot_sed_maps(ti)
                return
            elif pt == "E–W Cross-Section":
                self._plot_xsec(ax, "EW")
            elif pt == "N–S Cross-Section":
                self._plot_xsec(ax, "NS")
            elif pt == "Sea Level & Shoreline":
                self._plot_sl_shore(ax)
            elif pt == "Grain-Size Timeseries":
                self._plot_gs_ts(ax, ti)
            elif pt == "Strat Column":
                self._plot_strat(ax, ti)
            elif pt == "Net Change Map":
                self._plot_net_change(ax, cmap)
            elif pt == "Overview (4-panel)":
                self._plot_overview(ti, cmap)
                return
        except Exception as e:
            ax.text(0.5, 0.5, f"Plot error:\n{e}",
                    ha="center", va="center", transform=ax.transAxes,
                    color=DANGER, fontsize=10)

        self.canvas.redraw()

    def _x_km(self) -> np.ndarray:
        r = self._result
        return np.arange(r.ncols) * r.cellside / 1000

    def _y_km(self) -> np.ndarray:
        r = self._result
        return np.arange(r.nrows) * r.cellside / 1000

    def _plot_topo(self, ax, ti, cmap):
        r = self._result
        top = r.top_at(ti)
        sl  = r.sealevels[ti]
        im  = ax.pcolormesh(self._x_km(), self._y_km(), top.T,
                             cmap=cmap, shading="auto")
        if self.show_sl_cb.isChecked():
            ax.contour(self._x_km(), self._y_km(), top.T,
                       levels=[sl], colors="cyan", linewidths=1.5)
        cb = self.canvas.fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
        cb.set_label("Elevation (m)", color=TEXT_SEC, fontsize=8)
        cb.ax.tick_params(colors=TEXT_SEC, labelsize=7)
        ax.set_xlabel("Distance E–W (km)")
        ax.set_ylabel("Distance N–S (km)")
        ax.set_title(f"Topography  ·  t = {r.times[ti]:.0f} ka  ·  SL = {sl:.1f} m",
                     color=TEXT_PRI, fontsize=10)
        if self.show_grid_cb.isChecked():
            ax.grid(True, color=BORDER, alpha=0.3, lw=0.5)

    def _plot_sed_maps(self, ti):
        r = self._result
        n = min(r.nsed, 4)
        self.canvas.fig.clear()
        for i in range(n):
            ax = self.canvas.fig.add_subplot(2, 2, i + 1)
            _style_ax(ax)
            frac = r.sed_at(i, ti)
            im = ax.pcolormesh(self._x_km(), self._y_km(), frac.T,
                                cmap=_SED_CMAPS[i], vmin=0, vmax=1,
                                shading="auto")
            if self.show_sl_cb.isChecked():
                ax.contour(self._x_km(), self._y_km(), r.top_at(ti).T,
                           levels=[r.sealevels[ti]], colors="cyan",
                           linewidths=1.0, linestyles="--")
            cb = self.canvas.fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cb.ax.tick_params(colors=TEXT_SEC, labelsize=7)
            diam = self._diameters[i] if i < len(self._diameters) else "?"
            ax.set_title(f"SED {i+1}  ({diam} mm)", color=TEXT_PRI, fontsize=9)
            ax.set_xlabel("E–W (km)", fontsize=8)
            ax.set_ylabel("N–S (km)", fontsize=8)
        self.canvas.redraw()

    def _plot_xsec(self, ax, orientation):
        r = self._result
        mid = r.nrows // 2 if orientation == "EW" else r.ncols // 2
        x   = self._x_km() if orientation == "EW" else self._y_km()
        palette = plt.cm.plasma(np.linspace(0.1, 0.95, r.ntimes))

        step = max(1, r.ntimes // 8)
        shown = list(range(0, r.ntimes, step))
        if r.ntimes - 1 not in shown:
            shown.append(r.ntimes - 1)

        for i, ti in enumerate(shown):
            top = r.top_at(ti)
            col = top[:, mid] if orientation == "EW" else top[mid, :]
            sl  = r.sealevels[ti]
            ax.plot(x, col, color=palette[ti], lw=1.4,
                    label=f"{r.times[ti]:.0f} ka", zorder=5)
            if self.show_sl_cb.isChecked():
                ax.axhline(sl, color=palette[ti], lw=0.5, ls="--", alpha=0.6)

        ax.set_xlabel(f"{'E–W' if orientation=='EW' else 'N–S'} distance (km)")
        ax.set_ylabel("Elevation (m)")
        ax.set_title(f"{'E–W' if orientation=='EW' else 'N–S'} cross-section "
                     f"(centreline)")
        ax.legend(fontsize=7, loc="best",
                  facecolor=CARD_BG, edgecolor=BORDER, labelcolor=TEXT_PRI,
                  framealpha=0.85)
        ax.axhline(0, color=TEXT_SEC, lw=0.5, ls=":")

    def _plot_sl_shore(self, ax):
        r = self._result
        ax2 = ax.twinx()

        ax.plot(r.times, r.sealevels, color=ACCENT, lw=2, label="Sea level")
        ax.fill_between(r.times, r.sealevels, r.sealevels.min(),
                         color=ACCENT, alpha=0.1)
        ax.set_xlabel("Time (ka)")
        ax.set_ylabel("Sea Level (m)", color=ACCENT)
        ax.tick_params(axis="y", colors=ACCENT)

        shores = [r.shoreline_x(i) for i in range(r.ntimes)]
        valid  = [(t, s * r.cellside / 1000)
                  for t, s in zip(r.times, shores) if s is not None]
        if valid:
            vt, vs = zip(*valid)
            ax2.plot(vt, vs, color=ACCENT2, lw=2, label="Shoreline")
            ax2.set_ylabel("Shoreline position (km)", color=ACCENT2)
            ax2.tick_params(axis="y", colors=ACCENT2)
            ax2.spines["right"].set_edgecolor(ACCENT2)
            ax2.yaxis.label.set_color(ACCENT2)

        ax.set_title("Sea Level & Shoreline Migration")
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2,
                  facecolor=CARD_BG, edgecolor=BORDER,
                  labelcolor=TEXT_PRI, fontsize=8)

    def _plot_gs_ts(self, ax, ti):
        r = self._result
        mid_x = r.ncols // 2
        mid_y = r.nrows // 2
        for i in range(r.nsed):
            fracs = [float(r.sed_at(i, t)[mid_x, mid_y]) for t in range(r.ntimes)]
            diam  = self._diameters[i] if i < len(self._diameters) else f"SED{i+1}"
            ax.plot(r.times, fracs, color=_SED_COLORS[i % len(_SED_COLORS)],
                    lw=1.8, label=f"{diam} mm")
        ax.axvline(r.times[ti], color=TEXT_SEC, lw=1, ls="--", alpha=0.7)
        ax.set_xlabel("Time (ka)")
        ax.set_ylabel("Surface fraction at centre")
        ax.set_ylim(0, 1)
        ax.set_title("Grain-size History (grid centre)")
        ax.legend(fontsize=8, facecolor=CARD_BG, edgecolor=BORDER,
                  labelcolor=TEXT_PRI, framealpha=0.85)

    def _plot_strat(self, ax, ti):
        r = self._result
        mid_x = r.ncols // 2
        mid_y = r.nrows // 2
        topo  = [float(r.top_at(t)[mid_x, mid_y]) for t in range(r.ntimes)]
        sls   = list(r.sealevels)
        ax.plot(r.times, topo, color="#81c784", lw=2, label="Surface")
        ax.plot(r.times, sls,  color=ACCENT,    lw=1.5, ls="--", label="Sea level")
        ax.fill_between(r.times, topo, sls,
                         where=[t < s for t, s in zip(topo, sls)],
                         color="#1a5276", alpha=0.4, label="Marine")
        ax.fill_between(r.times, topo, sls,
                         where=[t >= s for t, s in zip(topo, sls)],
                         color="#6d4c41", alpha=0.3, label="Terrestrial")
        ax.axvline(r.times[ti], color=TEXT_SEC, lw=1, ls="--", alpha=0.7)
        ax.set_xlabel("Time (ka)")
        ax.set_ylabel("Elevation (m)")
        ax.set_title("Stratigraphic Column (grid centre)")
        ax.legend(fontsize=8, facecolor=CARD_BG, edgecolor=BORDER,
                  labelcolor=TEXT_PRI, framealpha=0.85)

    def _plot_net_change(self, ax, cmap):
        r = self._result
        if r.ntimes < 2:
            ax.text(0.5, 0.5, "Need ≥2 timesteps",
                    ha="center", va="center", transform=ax.transAxes)
            return
        delta = r.top_at(-1) - r.top_at(0)
        vmax  = np.abs(delta).max()
        im = ax.pcolormesh(self._x_km(), self._y_km(), delta.T,
                            cmap=cmap, vmin=-vmax, vmax=vmax,
                            shading="auto")
        if self.show_sl_cb.isChecked():
            ax.contour(self._x_km(), self._y_km(), r.top_at(-1).T,
                       levels=[r.sealevels[-1]], colors="white", linewidths=1.2)
        cb = self.canvas.fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
        cb.set_label("Δ Elevation (m)", color=TEXT_SEC, fontsize=8)
        cb.ax.tick_params(colors=TEXT_SEC, labelsize=7)
        ax.set_xlabel("E–W (km)")
        ax.set_ylabel("N–S (km)")
        ax.set_title(f"Net Change  ({r.times[0]:.0f} → {r.times[-1]:.0f} ka)")

    def _plot_overview(self, ti, cmap):
        r = self._result
        self.canvas.fig.clear()
        gs = gridspec.GridSpec(2, 3, figure=self.canvas.fig,
                               hspace=0.45, wspace=0.38)
        axes = []
        for i in range(6):
            ax = self.canvas.fig.add_subplot(gs[i // 3, i % 3])
            _style_ax(ax)
            axes.append(ax)

        # [0] Topo
        top = r.top_at(ti); sl = r.sealevels[ti]
        im0 = axes[0].pcolormesh(self._x_km(), self._y_km(), top.T,
                                  cmap=cmap, shading="auto")
        axes[0].contour(self._x_km(), self._y_km(), top.T,
                         levels=[sl], colors="cyan", linewidths=1.0)
        axes[0].set_title(f"Topography  t={r.times[ti]:.0f} ka",
                          color=TEXT_PRI, fontsize=9)
        self.canvas.fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)\
            .ax.tick_params(colors=TEXT_SEC, labelsize=7)

        # [1] Net change
        if r.ntimes >= 2:
            delta = r.top_at(-1) - r.top_at(0)
            vmax  = max(np.abs(delta).max(), 0.01)
            im1 = axes[1].pcolormesh(self._x_km(), self._y_km(), delta.T,
                                      cmap=cmap, vmin=-vmax, vmax=vmax,
                                      shading="auto")
            axes[1].set_title("Net Elevation Change", color=TEXT_PRI, fontsize=9)
            self.canvas.fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)\
                .ax.tick_params(colors=TEXT_SEC, labelsize=7)

        # [2] Mean grain size
        mg = r.mean_grain_size(ti, self._diameters)
        if mg.max() > 0:
            im2 = axes[2].pcolormesh(self._x_km(), self._y_km(), mg.T,
                                      cmap="YlOrRd_r", vmin=0,
                                      vmax=max(self._diameters),
                                      shading="auto")
            axes[2].set_title("Mean Grain Size (mm)", color=TEXT_PRI, fontsize=9)
            self.canvas.fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04)\
                .ax.tick_params(colors=TEXT_SEC, labelsize=7)

        # [3] Cross-section
        mid = r.nrows // 2
        pal = plt.cm.plasma(np.linspace(0.1, 0.9, 5))
        step = max(1, (r.ntimes - 1) // 4)
        snap = list(range(0, r.ntimes, step))[:5]
        for idx, t_ in enumerate(snap):
            axes[3].plot(self._x_km(), r.top_at(t_)[:, mid],
                         color=pal[idx], lw=1.3,
                         label=f"{r.times[t_]:.0f} ka")
        axes[3].set_xlabel("E–W (km)", fontsize=8)
        axes[3].set_ylabel("Elevation (m)", fontsize=8)
        axes[3].set_title("Cross-section", color=TEXT_PRI, fontsize=9)
        axes[3].legend(fontsize=6, facecolor=CARD_BG,
                       edgecolor=BORDER, labelcolor=TEXT_PRI)

        # [4] Sea level
        axes[4].plot(r.times, r.sealevels, color=ACCENT, lw=1.8)
        axes[4].fill_between(r.times, r.sealevels, min(r.sealevels),
                              color=ACCENT, alpha=0.1)
        axes[4].axvline(r.times[ti], color=TEXT_SEC, lw=1, ls="--", alpha=0.6)
        axes[4].set_xlabel("Time (ka)", fontsize=8)
        axes[4].set_ylabel("Sea Level (m)", fontsize=8)
        axes[4].set_title("Sea Level", color=TEXT_PRI, fontsize=9)

        # [5] Grain-size at centre
        mid_x, mid_y = r.ncols // 2, r.nrows // 2
        for i in range(min(r.nsed, 4)):
            fracs = [float(r.sed_at(i, t)[mid_x, mid_y]) for t in range(r.ntimes)]
            d = self._diameters[i] if i < len(self._diameters) else f"SED{i+1}"
            axes[5].plot(r.times, fracs,
                         color=_SED_COLORS[i % len(_SED_COLORS)],
                         lw=1.4, label=f"{d} mm")
        axes[5].axvline(r.times[ti], color=TEXT_SEC, lw=1, ls="--", alpha=0.6)
        axes[5].set_xlabel("Time (ka)", fontsize=8)
        axes[5].set_ylabel("Surface fraction", fontsize=8)
        axes[5].set_title("Grain-size (centre)", color=TEXT_PRI, fontsize=9)
        axes[5].legend(fontsize=6, facecolor=CARD_BG,
                       edgecolor=BORDER, labelcolor=TEXT_PRI)
        axes[5].set_ylim(0, 1)

        self.canvas.redraw()

    def _export_png(self):
        p, _ = QFileDialog.getSaveFileName(self, "Export PNG", "",
                                            "PNG (*.png);;PDF (*.pdf)")
        if p:
            self.canvas.fig.savefig(p, dpi=200, bbox_inches="tight",
                                     facecolor=DARK_BG)
            QMessageBox.information(self, "Exported", f"Saved to:\n{p}")

    def set_diameters(self, diameters: List[float]):
        self._diameters = diameters


# ─────────────────────────────────────────────────────────────────────────────
# COMPARE WIDGET
# ─────────────────────────────────────────────────────────────────────────────

class CompareWidget(QWidget):
    """Tab 4 — side-by-side run comparison."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._runs: List[Optional[SimResult]] = [None, None]
        self._diameters: List[float] = [20, 10, 5, 1]
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        title = QLabel("Compare Runs")
        title.setObjectName("heading")
        root.addWidget(title)

        # Load panels
        load_row = QHBoxLayout()
        for i in range(2):
            gb = QGroupBox(f"Run {'A' if i==0 else 'B'}")
            gv = QHBoxLayout()
            lbl = QLabel("No file")
            lbl.setObjectName("subheading")
            lbl.setWordWrap(True)
            btn = QPushButton(f"📂  Load Run {'A' if i==0 else 'B'}…")
            idx = i
            btn.clicked.connect(lambda _, x=idx: self._load_run(x))
            gv.addWidget(btn)
            gv.addWidget(lbl, 1)
            gb.setLayout(gv)
            setattr(self, f"_lbl_{i}", lbl)
            load_row.addWidget(gb)
        root.addLayout(load_row)

        # Controls row
        ctrl_row = QHBoxLayout()

        ctrl_row.addWidget(QLabel("Plot:"))
        self.plot_type = QComboBox()
        self.plot_type.addItems([
            "Topography Maps",
            "Cross-sections",
            "Sea Level & Shoreline",
            "Grain-size",
            "Difference Map",
        ])
        self.plot_type.currentIndexChanged.connect(self._update)
        ctrl_row.addWidget(self.plot_type)

        ctrl_row.addStretch()
        ctrl_row.addWidget(QLabel("Timestep:"))
        self.ts_slider = QSlider(Qt.Horizontal)
        self.ts_slider.setRange(0, 0)
        self.ts_slider.valueChanged.connect(self._update)
        self.ts_slider.setFixedWidth(200)
        ctrl_row.addWidget(self.ts_slider)

        self.ts_lbl = QLabel("—")
        self.ts_lbl.setObjectName("subheading")
        ctrl_row.addWidget(self.ts_lbl)

        ctrl_row.addStretch()
        self.cmap_box = QComboBox()
        self.cmap_box.addItems(["RdYlBu_r", "terrain", "viridis", "plasma"])
        self.cmap_box.currentIndexChanged.connect(self._update)
        ctrl_row.addWidget(QLabel("Cmap:"))
        ctrl_row.addWidget(self.cmap_box)

        export_btn = QPushButton("📤  Export…")
        export_btn.clicked.connect(self._export)
        ctrl_row.addWidget(export_btn)
        root.addLayout(ctrl_row)

        # Canvas
        self.canvas = MplCanvas(figsize=(12, 5))
        self.toolbar = NavToolbar(self.canvas, self)
        self.toolbar.setStyleSheet(f"background:{DARK_BG};")
        root.addWidget(self.toolbar)
        root.addWidget(self.canvas, 1)

    def _load_run(self, idx: int):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Load Run {'AB'[idx]} output", "",
            "VVM files (*.vvm);;All files (*)")
        if not path:
            return
        try:
            result = parse_output(path)
            if result.ntimes == 0:
                QMessageBox.warning(self, "Error", "No data found.")
                return
            self._runs[idx] = result
            getattr(self, f"_lbl_{idx}").setText(
                f"📄 {Path(path).name}  "
                f"({result.ntimes} steps)")
            # Update slider range to min of both runs
            valid = [r for r in self._runs if r is not None]
            if valid:
                mn = min(r.ntimes for r in valid)
                self.ts_slider.setRange(0, mn - 1)
                self.ts_slider.setValue(mn - 1)
            self._update()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _update(self):
        ti   = self.ts_slider.value()
        runs = self._runs
        cmap = self.cmap_box.currentText()
        pt   = self.plot_type.currentText()

        # Update label
        labels = []
        for r in runs:
            if r is not None and ti < r.ntimes:
                labels.append(f"t = {r.times[ti]:.0f} ka")
        self.ts_lbl.setText("  |  ".join(labels) if labels else "—")

        self.canvas.fig.clear()

        if pt == "Topography Maps":
            self._plot_topo_pair(ti, cmap)
        elif pt == "Cross-sections":
            self._plot_xsec_pair(ti)
        elif pt == "Sea Level & Shoreline":
            self._plot_sl_pair()
        elif pt == "Grain-size":
            self._plot_gs_pair(ti)
        elif pt == "Difference Map":
            self._plot_diff(ti, cmap)

        self.canvas.redraw()

    def _x_km(self, r: SimResult) -> np.ndarray:
        return np.arange(r.ncols) * r.cellside / 1000

    def _y_km(self, r: SimResult) -> np.ndarray:
        return np.arange(r.nrows) * r.cellside / 1000

    def _plot_topo_pair(self, ti, cmap):
        runs = self._runs
        n = sum(1 for r in runs if r is not None)
        for i, r in enumerate(runs):
            if r is None:
                continue
            col = [j for j, rr in enumerate(runs) if rr is not None].index(i) + 1
            ax = self.canvas.fig.add_subplot(1, n, col)
            _style_ax(ax)
            if ti >= r.ntimes: continue
            top = r.top_at(ti)
            sl  = r.sealevels[ti]
            im = ax.pcolormesh(self._x_km(r), self._y_km(r), top.T,
                                cmap=cmap, shading="auto")
            ax.contour(self._x_km(r), self._y_km(r), top.T,
                       levels=[sl], colors="cyan", linewidths=1.0)
            ax.set_title(f"Run {'AB'[i]}  ·  t = {r.times[ti]:.0f} ka",
                         color=TEXT_PRI, fontsize=9)
            ax.set_xlabel("E–W (km)", fontsize=8)
            ax.set_ylabel("N–S (km)", fontsize=8)
            self.canvas.fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)\
                .ax.tick_params(colors=TEXT_SEC, labelsize=7)

    def _plot_xsec_pair(self, ti):
        ax = self.canvas.fig.add_subplot(111)
        _style_ax(ax)
        colors = [ACCENT, ACCENT2]
        styles = ["-", "--"]
        for i, r in enumerate(self._runs):
            if r is None or ti >= r.ntimes:
                continue
            mid = r.nrows // 2
            x   = self._x_km(r)
            top = r.top_at(ti)[:, mid]
            ax.plot(x, top, color=colors[i], lw=2, ls=styles[i],
                    label=f"Run {'AB'[i]}  t={r.times[ti]:.0f} ka")
            ax.axhline(r.sealevels[ti], color=colors[i],
                       lw=0.8, ls=":", alpha=0.7)
        ax.set_xlabel("E–W (km)")
        ax.set_ylabel("Elevation (m)")
        ax.set_title("E–W Cross-section comparison")
        ax.legend(facecolor=CARD_BG, edgecolor=BORDER,
                  labelcolor=TEXT_PRI, fontsize=9)

    def _plot_sl_pair(self):
        ax = self.canvas.fig.add_subplot(111)
        _style_ax(ax)
        colors = [ACCENT, ACCENT2]
        for i, r in enumerate(self._runs):
            if r is None:
                continue
            ax.plot(r.times, r.sealevels, color=colors[i], lw=2,
                    label=f"Run {'AB'[i]} — Sea Level")
            shores = [r.shoreline_x(t) for t in range(r.ntimes)]
            valid  = [(t, s * r.cellside / 1000)
                      for t, s in zip(r.times, shores) if s is not None]
            if valid:
                vt, vs = zip(*valid)
                ax.plot(vt, vs, color=colors[i], lw=2, ls="--",
                        label=f"Run {'AB'[i]} — Shoreline")
        ax.set_xlabel("Time (ka)")
        ax.set_ylabel("Level (m) or position (km)")
        ax.set_title("Sea Level & Shoreline")
        ax.legend(facecolor=CARD_BG, edgecolor=BORDER,
                  labelcolor=TEXT_PRI, fontsize=9)

    def _plot_gs_pair(self, ti):
        gs_obj = gridspec.GridSpec(1, 2, self.canvas.fig, wspace=0.35)
        for i, r in enumerate(self._runs):
            if r is None:
                continue
            ax = self.canvas.fig.add_subplot(gs_obj[0, i])
            _style_ax(ax)
            mid_x, mid_y = r.ncols // 2, r.nrows // 2
            for j in range(min(r.nsed, 4)):
                fracs = [float(r.sed_at(j, t)[mid_x, mid_y])
                         for t in range(r.ntimes)]
                d = self._diameters[j] if j < len(self._diameters) else f"SED{j+1}"
                ax.plot(r.times, fracs,
                        color=_SED_COLORS[j], lw=1.5, label=f"{d} mm")
            ax.axvline(r.times[ti], color=TEXT_SEC, lw=1, ls="--", alpha=0.6)
            ax.set_ylim(0, 1)
            ax.set_xlabel("Time (ka)", fontsize=8)
            ax.set_ylabel("Surface fraction", fontsize=8)
            ax.set_title(f"Run {'AB'[i]} — Grain-size",
                         color=TEXT_PRI, fontsize=9)
            ax.legend(fontsize=7, facecolor=CARD_BG,
                      edgecolor=BORDER, labelcolor=TEXT_PRI)

    def _plot_diff(self, ti, cmap):
        runs = [r for r in self._runs if r is not None]
        if len(runs) < 2:
            ax = self.canvas.fig.add_subplot(111)
            _style_ax(ax)
            ax.text(0.5, 0.5, "Load both Run A and Run B",
                    ha="center", va="center", transform=ax.transAxes,
                    color=TEXT_SEC, fontsize=12)
            return
        rA, rB = runs
        tiA = min(ti, rA.ntimes - 1)
        tiB = min(ti, rB.ntimes - 1)

        # Interpolate to common grid if needed (simple crop)
        nco = min(rA.ncols, rB.ncols)
        nro = min(rA.nrows, rB.nrows)
        diff = rA.top_at(tiA)[:nco, :nro] - rB.top_at(tiB)[:nco, :nro]
        vmax = max(np.abs(diff).max(), 0.01)

        ax_diff = self.canvas.fig.add_subplot(121)
        ax_stat = self.canvas.fig.add_subplot(122)
        _style_ax(ax_diff); _style_ax(ax_stat)

        x = np.arange(nco) * rA.cellside / 1000
        y = np.arange(nro) * rA.cellside / 1000
        im = ax_diff.pcolormesh(x, y, diff.T, cmap=cmap,
                                  vmin=-vmax, vmax=vmax, shading="auto")
        self.canvas.fig.colorbar(im, ax=ax_diff, fraction=0.046, pad=0.04)\
            .ax.tick_params(colors=TEXT_SEC, labelsize=7)
        ax_diff.set_title(f"Δ Top (A − B)  t≈{rA.times[tiA]:.0f} ka",
                          color=TEXT_PRI, fontsize=9)
        ax_diff.set_xlabel("E–W (km)", fontsize=8)
        ax_diff.set_ylabel("N–S (km)", fontsize=8)

        # Stats panel
        flat = diff.ravel()
        ax_stat.hist(flat, bins=40, color=ACCENT, alpha=0.8, edgecolor=BORDER)
        ax_stat.axvline(0, color="white", lw=1, ls="--")
        ax_stat.set_xlabel("Elevation difference (m)", fontsize=8)
        ax_stat.set_ylabel("Count", fontsize=8)
        ax_stat.set_title(f"Distribution  μ={flat.mean():.2f} m  "
                          f"σ={flat.std():.2f} m",
                          color=TEXT_PRI, fontsize=9)

    def _export(self):
        p, _ = QFileDialog.getSaveFileName(self, "Export comparison", "",
                                            "PNG (*.png);;PDF (*.pdf)")
        if p:
            self.canvas.fig.savefig(p, dpi=200, bbox_inches="tight",
                                     facecolor=DARK_BG)
            QMessageBox.information(self, "Exported", f"Saved:\n{p}")

    def set_diameters(self, diameters: List[float]):
        self._diameters = diameters

    def load_result_as(self, idx: int, result: SimResult):
        self._runs[idx] = result
        getattr(self, f"_lbl_{idx}").setText(
            f"📄 {Path(result.path).name}  ({result.ntimes} steps)")
        valid = [r for r in self._runs if r is not None]
        if valid:
            mn = min(r.ntimes for r in valid)
            self.ts_slider.setRange(0, mn - 1)
            self.ts_slider.setValue(mn - 1)
        self._update()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, input_file: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("SedArch GUI")
        self.setMinimumSize(1200, 750)
        self._settings = QSettings("SedArch", "GUI")
        self._sedarch_path = self._settings.value(
            "sedarch_path",
            str(Path(__file__).parent))

        self._build_ui()
        self._restore_geometry()

        if input_file:
            self.editor.load_file(input_file)
            self.runner.set_input(input_file)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready  ·  SedArch GUI")

        # Central tabs (widgets must exist before menu wires to them)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.editor  = InputEditorWidget()
        self.runner  = RunWidget(self._sedarch_path)
        self.viz     = VizWidget()
        self.compare = CompareWidget()

        # Menu (built after widgets so signal connections work)
        self._build_menu()

        self.tabs.addTab(self.editor,  "✏  Input Editor")
        self.tabs.addTab(self.runner,  "▶  Run")
        self.tabs.addTab(self.viz,     "📊  Visualize")
        self.tabs.addTab(self.compare, "⚖  Compare")

        # Wire signals
        self.editor.file_saved.connect(self._on_file_saved)
        self.runner.run_complete.connect(self._on_run_complete)

        # Quick-send input path from editor → runner
        self.editor.save_btn.clicked.connect(
            lambda: self.runner.set_input(self.editor.get_input_path() or ""))

    def _build_menu(self):
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar {{ background: {DARK_BG}; color: {TEXT_PRI}; }}"
            f"QMenuBar::item:selected {{ background: {MUTED}; }}"
            f"QMenu {{ background: {CARD_BG}; color: {TEXT_PRI}; "
            f"border: 1px solid {BORDER}; }}"
            f"QMenu::item:selected {{ background: {ACCENT}; color: #fff; }}")

        # File
        file_menu = mb.addMenu("File")
        act_new  = QAction("New Input…",  self)
        act_open = QAction("Open Input…", self)
        act_save = QAction("Save",        self)
        act_load_out = QAction("Load Output VVM…", self)
        act_quit = QAction("Quit",        self)
        act_new.setShortcut(QKeySequence.New)
        act_open.setShortcut(QKeySequence.Open)
        act_save.setShortcut(QKeySequence.Save)
        act_quit.setShortcut(QKeySequence.Quit)
        act_new.triggered.connect(self.editor._on_new)
        act_open.triggered.connect(self.editor._on_open)
        act_save.triggered.connect(self.editor._on_save)
        act_load_out.triggered.connect(lambda: (
            self.tabs.setCurrentIndex(2),
            self.viz._on_load()))
        act_quit.triggered.connect(self.close)
        for a in [act_new, act_open, act_save, act_load_out,
                  None, act_quit]:
            if a is None:
                file_menu.addSeparator()
            else:
                file_menu.addAction(a)

        # Run
        run_menu = mb.addMenu("Run")
        act_run  = QAction("Start Simulation", self)
        act_stop = QAction("Stop",             self)
        act_run.setShortcut("F5")
        act_run.triggered.connect(lambda: (
            self.tabs.setCurrentIndex(1),
            self.runner._start_run()))
        act_stop.triggered.connect(self.runner._stop_run)
        run_menu.addAction(act_run)
        run_menu.addAction(act_stop)

        # Settings
        set_menu = mb.addMenu("Settings")
        act_path = QAction("Set SedArch Path…", self)
        act_path.triggered.connect(self._set_sedarch_path)
        set_menu.addAction(act_path)

        # Help
        help_menu = mb.addMenu("Help")
        act_about = QAction("About", self)
        act_about.triggered.connect(self._about)
        help_menu.addAction(act_about)

    # ── Signal handlers ────────────────────────────────────────────────────────

    def _on_file_saved(self, path: str):
        self.runner.set_input(path)
        self.status.showMessage(f"Saved: {path}")

    def _on_run_complete(self, output_path: str):
        self.status.showMessage(f"✓ Run complete  ·  Output: {output_path}")
        if output_path and os.path.exists(output_path):
            reply = QMessageBox.question(
                self, "Run Complete",
                f"Simulation finished!\n\nOutput: {output_path}\n\n"
                "Load result in Visualizer?",
                QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.viz.load_result(output_path)
                self.tabs.setCurrentIndex(2)

    def _set_sedarch_path(self):
        d = QFileDialog.getExistingDirectory(
            self, "Select SedArch Python directory",
            self._sedarch_path)
        if d:
            self._sedarch_path = d
            self.runner.sedarch_path = d
            self.runner.sedarch_edit.setText(d)
            self._settings.setValue("sedarch_path", d)

    def _about(self):
        QMessageBox.about(self, "SedArch GUI",
                          "<b>SedArch GUI</b><br>"
                          "Graphical interface for the SedArch "
                          "sedimentary simulation engine.<br><br>"
                          "PySide6  ·  Matplotlib  ·  NumPy")

    # ── Geometry persistence ──────────────────────────────────────────────────

    def _restore_geometry(self):
        geom = self._settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        else:
            self.resize(1280, 800)

    def closeEvent(self, event):
        self._settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    # Global matplotlib style
    for k, v in MPL_STYLE.items():
        plt.rcParams[k] = v

    # Dark palette for native widgets
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(DARK_BG))
    palette.setColor(QPalette.WindowText,      QColor(TEXT_PRI))
    palette.setColor(QPalette.Base,            QColor(CARD_BG))
    palette.setColor(QPalette.AlternateBase,   QColor(PANEL_BG))
    palette.setColor(QPalette.Text,            QColor(TEXT_PRI))
    palette.setColor(QPalette.Button,          QColor(CARD_BG))
    palette.setColor(QPalette.ButtonText,      QColor(TEXT_PRI))
    palette.setColor(QPalette.Highlight,       QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.Link,            QColor(ACCENT))
    app.setPalette(palette)

    inp = sys.argv[1] if len(sys.argv) > 1 else None
    win = MainWindow(input_file=inp)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
