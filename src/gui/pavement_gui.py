"""
PySide6 window for defining a pavement structure (pillars, beams, slabs).

The window has a tabbed form panel on the left for adding/removing elements,
and a live top-view Matplotlib schematic on the right that updates on every
change. A Validate button at the bottom of the left panel runs all connectivity
rules from Pavement.validate() and shows the result inline.
"""

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as mpatches

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.pavement.pavement import Pavement
from src.pavement.pillar import Pillar
from src.pavement.continuous_beam import ContinuousBeam
from src.pavement.slab import Slab
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.config import app_config

_CM_PER_M = 100.0


def _spin(lo: float, hi: float, decimals: int, step: float,
          value: float, suffix: str = "") -> QDoubleSpinBox:
    w = QDoubleSpinBox()
    w.setRange(lo, hi)
    w.setDecimals(decimals)
    w.setSingleStep(step)
    w.setValue(value)
    if suffix:
        w.setSuffix(suffix)
    return w


class PavementWindow(QMainWindow):
    """Top-level window for pavement structure definition."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pavement Designer")
        self.resize(1150, 720)

        self._pavement = Pavement()
        self._build_ui()
        self._redraw_canvas()

    # ------------------------------------------------------------------ UI ---

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 750])

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(380)
        panel.setMaximumWidth(420)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)

        layout.addWidget(self._build_settings_group())

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_pillars_tab(), "Pillars")
        self._tabs.addTab(self._build_beams_tab(), "Beams")
        self._tabs.addTab(self._build_slabs_tab(), "Slabs")
        layout.addWidget(self._tabs, stretch=1)

        validate_group = QGroupBox("Validation")
        vl = QVBoxLayout(validate_group)

        self._validate_btn = QPushButton("Validate Structure")
        self._validate_btn.setMinimumHeight(34)
        self._validate_btn.clicked.connect(self._validate)
        vl.addWidget(self._validate_btn)

        self._validate_label = QLabel("Not validated yet.")
        self._validate_label.setWordWrap(True)
        self._validate_label.setStyleSheet("color: grey;")
        vl.addWidget(self._validate_label)

        layout.addWidget(validate_group)
        return panel

    def _build_settings_group(self) -> QGroupBox:
        group = QGroupBox("Project Settings")
        form = QFormLayout(group)

        self._cfg_concrete = QComboBox()
        for c in Concrete:
            self._cfg_concrete.addItem(c.name, c)
        self._cfg_concrete.setCurrentText(app_config.pavement_concrete)
        form.addRow("Concrete:", self._cfg_concrete)

        self._cfg_steel = QComboBox()
        for s in Steel:
            self._cfg_steel.addItem(s.name, s)
        self._cfg_steel.setCurrentText(app_config.pavement_steel)
        form.addRow("Steel:", self._cfg_steel)

        return group

    # ---- Pillars tab --------------------------------------------------------

    def _build_pillars_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form_group = QGroupBox("Add Pillar")
        form = QFormLayout(form_group)

        self._p_id = QLineEdit()
        self._p_id.setPlaceholderText("e.g. P1")
        form.addRow("ID:", self._p_id)

        self._p_x = _spin(0, 9999, 2, 0.5, 0.0, " m")
        form.addRow("X:", self._p_x)

        self._p_y = _spin(0, 9999, 2, 0.5, 0.0, " m")
        form.addRow("Y:", self._p_y)

        self._p_width = _spin(5, 200, 1, 5, 30.0, " cm")
        form.addRow("Width:", self._p_width)

        self._p_depth = _spin(5, 200, 1, 5, 30.0, " cm")
        form.addRow("Depth:", self._p_depth)

        add_btn = QPushButton("Add Pillar")
        add_btn.clicked.connect(self._add_pillar)
        form.addRow(add_btn)
        layout.addWidget(form_group)

        list_group = QGroupBox("Pillars")
        list_layout = QVBoxLayout(list_group)
        self._pillar_list = QListWidget()
        list_layout.addWidget(self._pillar_list)

        del_btn = QPushButton("Delete Selected")
        del_btn.clicked.connect(self._delete_pillar)
        list_layout.addWidget(del_btn)
        layout.addWidget(list_group, stretch=1)

        return tab

    # ---- Beams tab ----------------------------------------------------------

    def _build_beams_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form_group = QGroupBox("Add Beam")
        form = QFormLayout(form_group)

        self._b_id = QLineEdit()
        self._b_id.setPlaceholderText("e.g. B1")
        form.addRow("ID:", self._b_id)

        self._b_pillars = QLineEdit()
        self._b_pillars.setPlaceholderText("e.g. P1, P2, P3")
        form.addRow("Pillar IDs:", self._b_pillars)

        self._pillar_hint_label = QLabel()
        self._pillar_hint_label.setWordWrap(True)
        self._pillar_hint_label.setStyleSheet("color: #555; font-size: 10px;")
        form.addRow("Available:", self._pillar_hint_label)

        self._b_width = _spin(5, 200, 1, 5, 20.0, " cm")
        form.addRow("Width (bw):", self._b_width)

        add_btn = QPushButton("Add Beam")
        add_btn.clicked.connect(self._add_beam)
        form.addRow(add_btn)
        layout.addWidget(form_group)

        list_group = QGroupBox("Beams")
        list_layout = QVBoxLayout(list_group)
        self._beam_list = QListWidget()
        list_layout.addWidget(self._beam_list)

        del_btn = QPushButton("Delete Selected")
        del_btn.clicked.connect(self._delete_beam)
        list_layout.addWidget(del_btn)
        layout.addWidget(list_group, stretch=1)

        return tab

    # ---- Slabs tab ----------------------------------------------------------

    def _build_slabs_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form_group = QGroupBox("Add Slab")
        form = QFormLayout(form_group)

        self._s_id = QLineEdit()
        self._s_id.setPlaceholderText("e.g. S1")
        form.addRow("ID:", self._s_id)

        self._s_pillar_hint = QLabel()
        self._s_pillar_hint.setWordWrap(True)
        self._s_pillar_hint.setStyleSheet("color: #555; font-size: 10px;")
        form.addRow("Available pillars:", self._s_pillar_hint)

        self._s_corners = []
        for label in ["Corner 1:", "Corner 2:", "Corner 3:", "Corner 4:"]:
            le = QLineEdit()
            le.setPlaceholderText("Pillar ID")
            self._s_corners.append(le)
            form.addRow(label, le)

        add_btn = QPushButton("Add Slab")
        add_btn.clicked.connect(self._add_slab)
        form.addRow(add_btn)
        layout.addWidget(form_group)

        list_group = QGroupBox("Slabs")
        list_layout = QVBoxLayout(list_group)
        self._slab_list = QListWidget()
        list_layout.addWidget(self._slab_list)

        del_btn = QPushButton("Delete Selected")
        del_btn.clicked.connect(self._delete_slab)
        list_layout.addWidget(del_btn)
        layout.addWidget(list_group, stretch=1)

        return tab

    # ---- Canvas panel -------------------------------------------------------

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)

        group = QGroupBox("Floor Plan — Top View")
        gl = QVBoxLayout(group)
        self._figure = Figure(layout="constrained")
        self._canvas = FigureCanvas(self._figure)
        gl.addWidget(self._canvas)
        layout.addWidget(group)
        return panel

    # ---------------------------------------------------------------- slots --

    def _add_pillar(self) -> None:
        pid = self._p_id.text().strip()
        if not pid:
            self._show_warning("Pillar ID cannot be empty.")
            return
        if pid in self._pavement.pillars:
            self._show_warning(f"Pillar '{pid}' already exists.")
            return

        pillar = Pillar(
            id=pid,
            x=self._p_x.value() * _CM_PER_M,
            y=self._p_y.value() * _CM_PER_M,
            width=self._p_width.value(),
            depth=self._p_depth.value(),
        )
        self._pavement.add_pillar(pillar)
        self._pillar_list.addItem(
            f"{pid}  ({self._p_x.value():.2f} m, {self._p_y.value():.2f} m)"
            f"  {pillar.width:.0f}×{pillar.depth:.0f} cm"
        )
        self._p_id.clear()
        self._update_pillar_hints()
        self._reset_validation_state()
        self._redraw_canvas()

    def _delete_pillar(self) -> None:
        row = self._pillar_list.currentRow()
        if row < 0:
            return
        pid = list(self._pavement.pillars.keys())[row]
        del self._pavement.pillars[pid]
        self._pillar_list.takeItem(row)
        self._update_pillar_hints()
        self._reset_validation_state()
        self._redraw_canvas()

    def _add_beam(self) -> None:
        bid = self._b_id.text().strip()
        if not bid:
            self._show_warning("Beam ID cannot be empty.")
            return
        if bid in self._pavement.beams:
            self._show_warning(f"Beam '{bid}' already exists.")
            return

        raw = self._b_pillars.text()
        pillar_ids = [p.strip() for p in raw.split(",") if p.strip()]
        if len(pillar_ids) < 2:
            self._show_warning("A beam needs at least 2 pillar IDs (comma-separated).")
            return

        beam = ContinuousBeam(id=bid, pillar_ids=pillar_ids, width=self._b_width.value())
        self._pavement.add_beam(beam)
        self._beam_list.addItem(f"{bid}  [{', '.join(pillar_ids)}]  bw={beam.width:.0f} cm")
        self._b_id.clear()
        self._b_pillars.clear()
        self._reset_validation_state()
        self._redraw_canvas()

    def _delete_beam(self) -> None:
        row = self._beam_list.currentRow()
        if row < 0:
            return
        bid = list(self._pavement.beams.keys())[row]
        del self._pavement.beams[bid]
        self._beam_list.takeItem(row)
        self._reset_validation_state()
        self._redraw_canvas()

    def _add_slab(self) -> None:
        sid = self._s_id.text().strip()
        if not sid:
            self._show_warning("Slab ID cannot be empty.")
            return
        if sid in self._pavement.slabs:
            self._show_warning(f"Slab '{sid}' already exists.")
            return

        corners = tuple(le.text().strip() for le in self._s_corners)
        if any(c == "" for c in corners):
            self._show_warning("All 4 corner pillar IDs must be filled in.")
            return

        slab = Slab(id=sid, corner_pillar_ids=corners)
        self._pavement.add_slab(slab)
        self._slab_list.addItem(f"{sid}  corners: [{', '.join(corners)}]")
        self._s_id.clear()
        for le in self._s_corners:
            le.clear()
        self._reset_validation_state()
        self._redraw_canvas()

    def _delete_slab(self) -> None:
        row = self._slab_list.currentRow()
        if row < 0:
            return
        sid = list(self._pavement.slabs.keys())[row]
        del self._pavement.slabs[sid]
        self._slab_list.takeItem(row)
        self._reset_validation_state()
        self._redraw_canvas()

    def _validate(self) -> None:
        try:
            self._pavement.validate()
            self._validate_label.setText("Structure is valid.")
            self._validate_label.setStyleSheet("color: green; font-weight: bold;")
        except ValueError as exc:
            self._validate_label.setText(str(exc))
            self._validate_label.setStyleSheet("color: red;")

    def _reset_validation_state(self) -> None:
        self._validate_label.setText("Not validated yet.")
        self._validate_label.setStyleSheet("color: grey;")

    def _update_pillar_hints(self) -> None:
        ids = list(self._pavement.pillars.keys())
        text = ", ".join(ids) if ids else "—"
        self._pillar_hint_label.setText(text)
        self._s_pillar_hint.setText(text)

    def _show_warning(self, msg: str) -> None:
        QMessageBox.warning(self, "Input error", msg)

    # -------------------------------------------------------------- canvas ---

    def _redraw_canvas(self) -> None:
        fig = self._figure
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_aspect("equal")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
        ax.set_title("Floor Plan — Top View", fontsize=10)
        ax.grid(True, alpha=0.25, linestyle="--")

        pillars = self._pavement.pillars
        beams = self._pavement.beams
        slabs = self._pavement.slabs

        if not pillars:
            ax.text(0.5, 0.5, "Add pillars to see the floor plan",
                    ha="center", va="center", transform=ax.transAxes,
                    color="#aaa", fontsize=11)
            self._canvas.draw_idle()
            return

        # --- slabs (drawn first so beams/pillars appear on top) ---
        for slab in slabs.values():
            coords = [pillars.get(pid) for pid in slab.corner_pillar_ids
                      if pid in pillars]
            if len(coords) == 4:
                xs = sorted({p.x for p in coords})
                ys = sorted({p.y for p in coords})
                if len(xs) == 2 and len(ys) == 2:
                    x0, x1 = xs[0] / _CM_PER_M, xs[1] / _CM_PER_M
                    y0, y1 = ys[0] / _CM_PER_M, ys[1] / _CM_PER_M
                    ax.add_patch(mpatches.Rectangle(
                        (x0, y0), x1 - x0, y1 - y0,
                        facecolor="#d4e8c2", edgecolor="#6aaa3a",
                        linewidth=1.0, alpha=0.55, zorder=1,
                    ))
                    ax.text((x0 + x1) / 2, (y0 + y1) / 2, slab.id,
                            ha="center", va="center", fontsize=8,
                            color="#3a7a1a", zorder=2)

        # --- beams ---
        for beam in beams.values():
            pts = [pillars[pid] for pid in beam.pillar_ids if pid in pillars]
            if len(pts) < 2:
                continue
            xs_b = [p.x / _CM_PER_M for p in pts]
            ys_b = [p.y / _CM_PER_M for p in pts]
            x_spread = max(xs_b) - min(xs_b)
            y_spread = max(ys_b) - min(ys_b)
            color = "#2c6fbb" if x_spread >= y_spread else "#e67e22"
            ax.plot(xs_b, ys_b, color=color, linewidth=2.5, zorder=3,
                    solid_capstyle="round")

        # --- pillars ---
        all_x = [p.x / _CM_PER_M for p in pillars.values()]
        all_y = [p.y / _CM_PER_M for p in pillars.values()]
        x_range = max(all_x) - min(all_x) if len(all_x) > 1 else 1.0
        y_range = max(all_y) - min(all_y) if len(all_y) > 1 else 1.0
        vis_half = max(x_range, y_range) * 0.018

        for p in pillars.values():
            px, py = p.x / _CM_PER_M, p.y / _CM_PER_M
            ax.add_patch(mpatches.Rectangle(
                (px - vis_half, py - vis_half), 2 * vis_half, 2 * vis_half,
                facecolor="#2c3e50", edgecolor="#1a252f",
                linewidth=1.0, zorder=4,
            ))
            ax.text(px, py + vis_half * 1.6, p.id,
                    ha="center", va="bottom", fontsize=8,
                    color="#2c3e50", fontweight="bold", zorder=5)

        # --- axes limits with padding ---
        pad = max(x_range, y_range) * 0.12 + vis_half * 3
        ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
        ax.set_ylim(min(all_y) - pad, max(all_y) + pad)

        # --- legend ---
        legend_handles = [
            mpatches.Patch(facecolor="#2c3e50", label="Pillar"),
            mpatches.Patch(color="#2c6fbb", label="Beam (X-dir)"),
            mpatches.Patch(color="#e67e22", label="Beam (Y-dir)"),
            mpatches.Patch(facecolor="#d4e8c2", edgecolor="#6aaa3a", label="Slab"),
        ]
        ax.legend(handles=legend_handles, loc="upper right", fontsize=8,
                  framealpha=0.8)

        self._canvas.draw_idle()
