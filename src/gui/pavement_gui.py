# type: ignore

# cSpell:disable

# REVIEW AI-Generated -> re-do after the calculations are finalized
"""
PySide6 window for defining a pavement structure (pillars, beams, slabs).

The window has a tabbed form panel on the left for adding/removing elements,
and a live top-view Matplotlib schematic on the right that updates on every
change. A Validate button at the bottom of the left panel runs all connectivity
rules from Pavement.validate() and shows the result inline.
"""

import matplotlib

matplotlib.use("QtAgg")
import matplotlib.patches as mpatches
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.config import APP_CONFIG
from src.data.nbr6120_2019.table_10.data import TABLE_10
from src.gui.theme import (
    DARK_ACCENT,
    DARK_BG_INPUT,
    DARK_BG_MAIN,
    DARK_BG_PANEL,
    DARK_BORDER,
    DARK_DANGER,
    DARK_SUCCESS,
    DARK_TEXT_MUTED,
    DARK_TEXT_PRIMARY,
    DARK_WARNING,
    apply_dark_theme,
    style_figure,
)
from src.pavement.continuous_beam import ContinuousBeam, WallDefinition
from src.pavement.geometry_utils import Alignment
from src.pavement.pavement import Pavement
from src.pavement.pillar import Pillar
from src.pavement.slab import Slab
from src.persistency import load_pavement, save_pavement
from src.properties.concrete import Concrete
from src.properties.steel import Steel

_CM_PER_M = 100.0

_STRUCTURAL_MASONRY_TYPES = [
    "Hollow concrete block (Classes A and B - ABNT NBR 6136)",
    "Hollow ceramic block with solid walls (Vertical holes - ABNT NBR 15270-1)",
    "Hollow ceramic block with hollow walls (Vertical holes - ABNT NBR 15270-1)",
    "Solid ceramic brick (ABNT NBR 15270-1)",
    "Hollow calcium silicate block (Class E - ABNT NBR 14974-1)",
    "Perforated calcium silicate block (Classes E, F and G - ABNT NBR 14974-1)",
]
_NON_BEARING_MASONRY_TYPES = [
    "Hollow concrete block (Class C - ABNT NBR 6136)",
    "Hollow ceramic block (Horizontal holes - ABNT NBR 15270-1)",
    "Autoclaved aerated concrete block (Class C25 - ABNT NBR 13438)",
    "Glass block (decorative, non-fire-rated)",
]


def _usage_locals_for_category(category_description: str) -> list[str]:
    try:
        cat = TABLE_10.find_category(category_description)
        return [loc.description for loc in cat.locations]
    except KeyError:
        return []


_USAGE_LOCALS: list[str] = _usage_locals_for_category(APP_CONFIG.building_category)


def _spin(
    lo: float, hi: float, decimals: int, step: float, value: float, suffix: str = ""
) -> QDoubleSpinBox:
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
        apply_dark_theme()
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

        self._build_menu_bar()

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 750])

    def _build_menu_bar(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        open_action = QAction("Open…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._load_from_file)
        file_menu.addAction(open_action)

        save_action = QAction("Save…", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_to_file)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        config_action = QAction("Configuration…", self)
        config_action.setShortcut("Ctrl+,")
        config_action.triggered.connect(self._open_config)
        file_menu.addAction(config_action)

        tools_menu = menubar.addMenu("Tools")
        beam_action = QAction("Beam Calculator", self)
        beam_action.triggered.connect(self._open_beam_calculator)
        tools_menu.addAction(beam_action)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(380)
        panel.setMaximumWidth(420)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(f"color: {DARK_DANGER};")
        clear_btn.clicked.connect(self._clear)
        layout.addWidget(clear_btn)

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

        self._calculate_btn = QPushButton("Calculate")
        self._calculate_btn.setMinimumHeight(38)
        self._calculate_btn.setStyleSheet(
            f"background-color: {DARK_ACCENT}; color: #000; font-weight: bold;"
        )
        self._calculate_btn.clicked.connect(self._calculate)
        vl.addWidget(self._calculate_btn)

        layout.addWidget(validate_group)
        return panel

    # ---- Pillars tab --------------------------------------------------------

    def _build_pillars_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form_group = QGroupBox("Add Pillar")
        form = QFormLayout(form_group)

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

        self._b_pillars = QLineEdit()
        self._b_pillars.setPlaceholderText("e.g. P1, P2, P3")
        form.addRow("Pillar IDs:", self._b_pillars)

        self._pillar_hint_label = QLabel()
        self._pillar_hint_label.setWordWrap(True)
        self._pillar_hint_label.setStyleSheet("color: #555; font-size: 10px;")
        form.addRow("Available:", self._pillar_hint_label)

        self._b_ref_pillar = QLineEdit()
        self._b_ref_pillar.setPlaceholderText("e.g. P1")
        form.addRow("Reference pillar:", self._b_ref_pillar)

        ref_hint = QLabel("Pillar used to anchor the beam's centerline (alignment).")
        ref_hint.setStyleSheet("color: #555; font-size: 10px;")
        ref_hint.setWordWrap(True)
        form.addRow("", ref_hint)

        self._b_width = _spin(5, 200, 1, 5, 20.0, " cm")
        form.addRow("Width (bw):", self._b_width)

        self._b_alignment = QComboBox()
        for al in Alignment:
            self._b_alignment.addItem(al.value, al)
        self._b_alignment.setCurrentText(Alignment.CENTER.value)
        form.addRow("Alignment:", self._b_alignment)

        align_hint = QLabel(
            "top/center/bottom → horizontal beam\nleft/center/right → vertical beam"
        )
        align_hint.setStyleSheet("color: #555; font-size: 10px;")
        align_hint.setWordWrap(True)
        form.addRow("", align_hint)

        # Wall definition fields
        self._b_wall_structural = QCheckBox("Structural masonry")
        self._b_wall_structural.setChecked(False)
        self._b_wall_structural.toggled.connect(self._on_wall_structural_toggled)
        form.addRow("Wall type:", self._b_wall_structural)

        self._b_wall_masonry = QComboBox()
        for t in _NON_BEARING_MASONRY_TYPES:
            self._b_wall_masonry.addItem(t)
        form.addRow("Masonry:", self._b_wall_masonry)

        self._b_wall_thickness = _spin(6.5, 30.0, 1, 0.5, 14.0, " cm")
        form.addRow("Nominal thickness:", self._b_wall_thickness)

        self._b_wall_coating = QSpinBox()
        self._b_wall_coating.setRange(0, 2)
        self._b_wall_coating.setValue(1)
        self._b_wall_coating.setSuffix(" cm")
        form.addRow("Coating thickness:", self._b_wall_coating)

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

        self._s_usage = QComboBox()
        for loc in _USAGE_LOCALS:
            self._s_usage.addItem(loc)
        form.addRow("Usage:", self._s_usage)

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
        pillar = Pillar(
            x=self._p_x.value() * _CM_PER_M,
            y=self._p_y.value() * _CM_PER_M,
            width=self._p_width.value(),
            depth=self._p_depth.value(),
        )
        self._pavement.add_pillar(pillar)
        self._pillar_list.addItem(
            f"{pillar.id}  ({self._p_x.value():.2f} m, {self._p_y.value():.2f} m)"
            f"  {pillar.width:.0f}×{pillar.depth:.0f} cm"
        )
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
        raw = self._b_pillars.text()
        pillar_ids = [p.strip() for p in raw.split(",") if p.strip()]
        if len(pillar_ids) < 2:
            self._show_warning("A beam needs at least 2 pillar IDs (comma-separated).")
            return

        ref_pillar = self._b_ref_pillar.text().strip()
        if not ref_pillar:
            self._show_warning("Reference pillar ID cannot be empty.")
            return
        if ref_pillar not in pillar_ids:
            self._show_warning(
                f"Reference pillar '{ref_pillar}' must be one of the beam's pillar IDs."
            )
            return

        structural = self._b_wall_structural.isChecked()
        wall = WallDefinition(
            structural=structural,
            masonry_type=self._b_wall_masonry.currentText(),
            nominal_thickness=self._b_wall_thickness.value(),
            coating_thickness=self._b_wall_coating.value(),
        )

        beam = ContinuousBeam(
            pillar_ids=pillar_ids,
            reference_pillar_id=ref_pillar,
            width=self._b_width.value(),
            alignment=self._b_alignment.currentData(),
            wall=wall,
        )
        self._pavement.add_beam(beam)
        self._beam_list.addItem(
            f"{beam.id}  [{', '.join(pillar_ids)}]  ref={ref_pillar}  bw={beam.width:.0f} cm  align={beam.alignment.value}"
        )
        self._b_pillars.clear()
        self._b_ref_pillar.clear()
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
        corners = tuple(le.text().strip() for le in self._s_corners)
        if any(c == "" for c in corners):
            self._show_warning("All 4 corner pillar IDs must be filled in.")
            return

        local = self._s_usage.currentText()
        slab = Slab(corner_pillar_ids=corners, local=local)
        self._pavement.add_slab(slab)
        self._slab_list.addItem(
            f"{slab.id}  corners: [{', '.join(corners)}]  usage: {local}"
        )
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

    def _clear(self) -> None:
        if (
            QMessageBox.question(
                self,
                "Clear pavement",
                "Remove all pillars, beams, and slabs?",
                QMessageBox.Yes | QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        self._pavement = Pavement()
        self._pillar_list.clear()
        self._beam_list.clear()
        self._slab_list.clear()
        self._update_pillar_hints()
        self._reset_validation_state()
        self._redraw_canvas()

    def _validate(self) -> None:
        try:
            self._pavement.validate()
            self._validate_label.setText("Structure is valid.")
            self._validate_label.setStyleSheet(
                f"color: {DARK_SUCCESS}; font-weight: bold;"
            )
        except ValueError as exc:
            self._validate_label.setText(str(exc))
            self._validate_label.setStyleSheet(f"color: {DARK_DANGER};")
        except Exception as exc:  # noqa: BLE001
            self._validate_label.setText(f"Error: {exc}")
            self._validate_label.setStyleSheet(f"color: {DARK_DANGER};")

    def _calculate(self) -> None:
        self._calculate_btn.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            self._pavement.validate()
            self._pavement.pre_size_beams()
            self._pavement.load_beam_spans()
            self._pavement.pre_size_slabs()
            self._pavement.unload_slabs_on_beams()
            self._pavement.dimension_beams()
        except ValueError as exc:
            self._validate_label.setText(str(exc))
            self._validate_label.setStyleSheet(f"color: {DARK_DANGER};")
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Calculation error", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
            self._calculate_btn.setEnabled(True)
        self._validate_label.setText("Calculation complete.")
        self._validate_label.setStyleSheet(f"color: {DARK_SUCCESS}; font-weight: bold;")
        dlg = ResultsWindow(self._pavement, parent=self)
        dlg.exec()

    def _load_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Pavement", "", "Pavement files (*.yaml *.yml)"
        )
        if not path:
            return
        try:
            self._pavement = load_pavement(path)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Load failed", str(exc))
            return
        self._refresh_from_pavement()

    def _save_to_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Pavement", "pavement.yaml", "Pavement files (*.yaml *.yml)"
        )
        if not path:
            return
        try:
            save_pavement(self._pavement, path)
        except OSError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))

    def _on_category_changed(self, category: str) -> None:
        APP_CONFIG.building_category = category
        locs = _usage_locals_for_category(category)
        current = self._s_usage.currentText()
        self._s_usage.clear()
        for loc in locs:
            self._s_usage.addItem(loc)
        if current in locs:
            self._s_usage.setCurrentText(current)

    def _open_config(self) -> None:
        dlg = ConfigDialog(self)
        dlg.exec()

    def _open_beam_calculator(self) -> None:
        from src.gui.beam_gui import BeamCalculatorWindow

        win = BeamCalculatorWindow(parent=self)
        win.show()

    def _refresh_from_pavement(self) -> None:
        self._pillar_list.clear()
        self._beam_list.clear()
        self._slab_list.clear()
        for pillar in self._pavement.pillars.values():
            self._pillar_list.addItem(
                f"{pillar.id}  ({pillar.x / _CM_PER_M:.2f} m, {pillar.y / _CM_PER_M:.2f} m)"
                f"  {pillar.width:.0f}×{pillar.depth:.0f} cm"
            )
        for beam in self._pavement.beams.values():
            self._beam_list.addItem(
                f"{beam.id}  [{', '.join(beam.pillar_ids)}]  ref={beam.reference_pillar_id}"
                f"  bw={beam.width:.0f} cm  align={beam.alignment.value}"
            )
        for slab in self._pavement.slabs.values():
            self._slab_list.addItem(
                f"{slab.id}  corners: [{', '.join(slab.corner_pillar_ids)}]"
                f"  usage: {slab.local}"
            )
        self._update_pillar_hints()
        self._reset_validation_state()
        self._redraw_canvas()

    def _on_wall_structural_toggled(self, checked: bool) -> None:
        self._b_wall_masonry.clear()
        types = _STRUCTURAL_MASONRY_TYPES if checked else _NON_BEARING_MASONRY_TYPES
        for t in types:
            self._b_wall_masonry.addItem(t)

    def _reset_validation_state(self) -> None:
        self._validate_label.setText("Not validated yet.")
        self._validate_label.setStyleSheet(f"color: {DARK_TEXT_MUTED};")

    def _update_pillar_hints(self) -> None:
        ids = list(self._pavement.pillars.keys())
        text = ", ".join(ids) if ids else "—"
        self._pillar_hint_label.setText(text)
        self._s_pillar_hint.setText(text)

    def _show_warning(self, msg: str) -> None:
        QMessageBox.warning(self, "Input error", msg)

    # -------------------------------------------------------------- canvas ---

    def _redraw_canvas(self) -> None:  # NOSONAR
        fig = self._figure
        style_figure(fig, DARK_BG_MAIN)
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_facecolor(DARK_BG_INPUT)
        ax.set_aspect("equal")
        ax.set_xlabel("X (m)", color=DARK_TEXT_PRIMARY)
        ax.set_ylabel("Y (m)", color=DARK_TEXT_PRIMARY)
        ax.set_title("Floor Plan — Top View", fontsize=10, color=DARK_TEXT_PRIMARY)
        ax.grid(True, alpha=0.3, linestyle="--", color=DARK_BORDER)

        pillars = self._pavement.pillars
        beams = self._pavement.beams
        slabs = self._pavement.slabs

        if not pillars:
            ax.text(
                0.5,
                0.5,
                "Add pillars to see the floor plan",
                ha="center",
                va="center",
                transform=ax.transAxes,
                color=DARK_TEXT_MUTED,
                fontsize=11,
            )
            self._canvas.draw_idle()
            return

        # Bounds from actual pillar extents (edges, not centres)
        all_x = (
            [(p.x - p.width / 2) / _CM_PER_M for p in pillars.values()]
            + [(p.x + p.width / 2) / _CM_PER_M for p in pillars.values()]
        )
        all_y = (
            [(p.y - p.depth / 2) / _CM_PER_M for p in pillars.values()]
            + [(p.y + p.depth / 2) / _CM_PER_M for p in pillars.values()]
        )
        x_range = max(all_x) - min(all_x) if len(all_x) > 1 else 1.0
        y_range = max(all_y) - min(all_y) if len(all_y) > 1 else 1.0

        # --- slabs (drawn first so beams/pillars appear on top) ---
        for slab in slabs.values():
            coords = [
                pillars.get(pid) for pid in slab.corner_pillar_ids if pid in pillars
            ]
            if len(coords) == 4:
                sorted_by_y = sorted(coords, key=lambda p: p.y, reverse=True)
                top = sorted(sorted_by_y[:2], key=lambda p: p.x)
                bottom = sorted(sorted_by_y[2:], key=lambda p: p.x)
                top_left, top_right = top
                bottom_left, bottom_right = bottom
                poly_xy = [
                    (bottom_left.x / _CM_PER_M, bottom_left.y / _CM_PER_M),
                    (bottom_right.x / _CM_PER_M, bottom_right.y / _CM_PER_M),
                    (top_right.x / _CM_PER_M, top_right.y / _CM_PER_M),
                    (top_left.x / _CM_PER_M, top_left.y / _CM_PER_M),
                ]
                cx = sum(x for x, _ in poly_xy) / 4
                cy = sum(y for _, y in poly_xy) / 4
                ax.add_patch(
                    mpatches.Polygon(
                        poly_xy,
                        closed=True,
                        facecolor="#164e63",
                        edgecolor="#22d3ee",
                        linewidth=1.0,
                        alpha=0.45,
                        zorder=1,
                    )
                )
                ax.text(
                    cx,
                    cy,
                    slab.id,
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="#67e8f9",
                    zorder=2,
                )

        # --- beams (drawn as width-correct rectangles) ---
        for beam in beams.values():
            pts = [pillars[pid] for pid in beam.pillar_ids if pid in pillars]
            if len(pts) < 2:
                continue
            ref = pillars.get(beam.reference_pillar_id)
            if ref is None:
                continue

            xs_b = [p.x for p in pts]
            ys_b = [p.y for p in pts]
            x_spread = max(xs_b) - min(xs_b)
            y_spread = max(ys_b) - min(ys_b)
            is_horizontal = x_spread >= y_spread
            bw_m = beam.width / _CM_PER_M

            if is_horizontal:
                # Spans in X; width in Y centred on the alignment-resolved Y
                if beam.alignment == Alignment.TOP:
                    cl_y = ref.y + ref.depth / 2 - beam.width / 2
                elif beam.alignment == Alignment.BOTTOM:
                    cl_y = ref.y - ref.depth / 2 + beam.width / 2
                else:
                    cl_y = ref.y
                cl_y /= _CM_PER_M
                rect = mpatches.Rectangle(
                    (min(xs_b) / _CM_PER_M, cl_y - bw_m / 2),
                    (max(xs_b) - min(xs_b)) / _CM_PER_M,
                    bw_m,
                    facecolor=DARK_ACCENT,
                    edgecolor=DARK_ACCENT,
                    linewidth=0,
                    alpha=0.9,
                    zorder=3,
                )
                label_x = (min(xs_b) + max(xs_b)) / 2 / _CM_PER_M
                label_y = cl_y
            else:
                # Spans in Y; width in X centred on the alignment-resolved X
                if beam.alignment == Alignment.LEFT:
                    cl_x = ref.x - ref.width / 2 + beam.width / 2
                elif beam.alignment == Alignment.RIGHT:
                    cl_x = ref.x + ref.width / 2 - beam.width / 2
                else:
                    cl_x = ref.x
                cl_x /= _CM_PER_M
                rect = mpatches.Rectangle(
                    (cl_x - bw_m / 2, min(ys_b) / _CM_PER_M),
                    bw_m,
                    (max(ys_b) - min(ys_b)) / _CM_PER_M,
                    facecolor="#ff9e64",
                    edgecolor="#ff9e64",
                    linewidth=0,
                    alpha=0.9,
                    zorder=3,
                )
                label_x = cl_x
                label_y = (min(ys_b) + max(ys_b)) / 2 / _CM_PER_M

            ax.add_patch(rect)
            ax.text(
                label_x,
                label_y,
                beam.id,
                ha="center",
                va="center",
                fontsize=7,
                color="#000",
                fontweight="bold",
                zorder=4,
            )

        # --- pillars (drawn with actual cross-section dimensions) ---
        for p in pillars.values():
            px_m = p.x / _CM_PER_M
            py_m = p.y / _CM_PER_M
            hw = p.width / (2 * _CM_PER_M)
            hd = p.depth / (2 * _CM_PER_M)
            ax.add_patch(
                mpatches.Rectangle(
                    (px_m - hw, py_m - hd),
                    p.width / _CM_PER_M,
                    p.depth / _CM_PER_M,
                    facecolor=DARK_WARNING,
                    edgecolor="#ff9e3b",
                    linewidth=1.0,
                    zorder=5,
                )
            )
            label_offset = max(x_range, y_range, 1.0) * 0.015
            ax.text(
                px_m,
                py_m + hd + label_offset,
                p.id,
                ha="center",
                va="bottom",
                fontsize=8,
                color=DARK_TEXT_PRIMARY,
                fontweight="bold",
                zorder=6,
            )

        # --- axes limits with padding ---
        pad = max(x_range, y_range) * 0.12
        ax.set_xlim(min(all_x) - pad, max(all_x) + pad)
        ax.set_ylim(min(all_y) - pad, max(all_y) + pad)

        # --- legend ---
        legend_handles = [
            mpatches.Patch(facecolor=DARK_WARNING, edgecolor="#ff9e3b", label="Pillar"),
            mpatches.Patch(color=DARK_ACCENT, label="Beam (X-dir)"),
            mpatches.Patch(color="#ff9e64", label="Beam (Y-dir)"),
            mpatches.Patch(facecolor="#164e63", edgecolor="#22d3ee", label="Slab"),
        ]
        ax.legend(
            handles=legend_handles,
            loc="upper right",
            fontsize=8,
            facecolor=DARK_BG_PANEL,
            edgecolor=DARK_BORDER,
            labelcolor=DARK_TEXT_PRIMARY,
            framealpha=0.9,
        )

        self._canvas.draw_idle()


class ResultsWindow(QDialog):
    """Dialog listing all calculated beams with a button to open each beam's report."""

    def __init__(self, pavement, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Calculation Results")
        self.resize(700, 520)
        self._pavement = pavement
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QLabel(f"<b>{len(self._pavement.beams)} beam(s) calculated</b>")
        header.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; font-size: 13px;")
        layout.addWidget(header)

        for beam in self._pavement.beams.values():
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 2, 0, 2)

            pillars_str = ", ".join(beam.pillar_ids)
            label = QLabel(
                f"<b>{beam.id}</b>  bw={beam.width:.0f} cm  h={beam.height:.0f} cm  "
                f"[{pillars_str}]  {len(beam.spans)} span(s)"
            )
            label.setStyleSheet(f"color: {DARK_TEXT_PRIMARY};")
            row.addWidget(label, stretch=1)

            btn = QPushButton("View Report")
            btn.setFixedWidth(100)
            btn.clicked.connect(lambda checked, b=beam: self._open_beam_report(b))
            row.addWidget(btn)
            layout.addWidget(row_widget)

        if self._pavement.slabs:
            slab_header = QLabel(f"<b>{len(self._pavement.slabs)} slab(s) sized</b>")
            slab_header.setStyleSheet(
                f"color: {DARK_TEXT_PRIMARY}; font-size: 13px; margin-top: 8px;"
            )
            layout.addWidget(slab_header)

            for slab in self._pavement.slabs.values():
                lx, ly = slab.dimensions
                slab_type = "one-way" if slab.is_one_way else "two-way"
                row_widget = QWidget()
                row = QHBoxLayout(row_widget)
                row.setContentsMargins(0, 2, 0, 2)

                label = QLabel(
                    f"<b>{slab.id}</b>  h={slab.thickness} cm  "
                    f"{lx:.0f}×{ly:.0f} cm  [{slab_type}]  {slab.local}"
                )
                label.setStyleSheet(f"color: {DARK_TEXT_PRIMARY};")
                row.addWidget(label, stretch=1)

                btn = QPushButton("View Report")
                btn.setFixedWidth(100)
                btn.clicked.connect(lambda checked, s=slab: self._open_slab_report(s))
                row.addWidget(btn)
                layout.addWidget(row_widget)

        layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _open_beam_report(self, beam) -> None:
        try:
            dlg = BeamReportWindow(beam, self._pavement.pillars, parent=self)
            dlg.exec()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Report error", str(exc))

    def _open_slab_report(self, slab) -> None:
        try:
            dlg = SlabReportWindow(slab, parent=self)
            dlg.exec()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Report error", str(exc))


class BeamReportWindow(QDialog):
    """Dialog showing the result buttons for a single pavement beam.

    Re-runs the beam's structural build steps to obtain a RectangularBeam and
    RebarCalculator, then exposes the same three result dialogs as the standalone
    beam window: loads/efforts/layers, cross-section, and effort diagrams.
    """

    def __init__(self, beam, pillar_registry: dict, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Report — {beam.id}")
        self.resize(480, 280)
        self._beam = beam
        self._pillar_registry = pillar_registry
        self._rect_beam = None
        self._calculator = None
        self._results_text = ""
        self._build_ui()
        self._run()

    # ------------------------------------------------------------------ UI ---

    def _build_ui(self) -> None:
        from src.gui.beam_gui import DiagramsDialog, ResultsDialog, SectionDialog

        self._ResultsDialog = ResultsDialog
        self._SectionDialog = SectionDialog
        self._DiagramsDialog = DiagramsDialog

        layout = QVBoxLayout(self)

        pillars_str = ", ".join(self._beam.pillar_ids)
        summary = QLabel(
            f"<b>{self._beam.id}</b> &nbsp;|&nbsp; "
            f"bw = {self._beam.width:.0f} cm &nbsp; h = {self._beam.height:.0f} cm "
            f"&nbsp;|&nbsp; Pillars: {pillars_str}"
        )
        summary.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; font-size: 12px;")
        layout.addWidget(summary)

        self._status_label = QLabel("Running…")
        self._status_label.setStyleSheet(f"color: {DARK_TEXT_MUTED};")
        layout.addWidget(self._status_label)

        result_group = QGroupBox("Results")
        result_layout = QVBoxLayout(result_group)

        self._results_btn = QPushButton("Loads, efforts & layers")
        self._results_btn.setEnabled(False)
        self._results_btn.clicked.connect(self._open_results)
        result_layout.addWidget(self._results_btn)

        self._section_btn = QPushButton("Designed cross-section")
        self._section_btn.setEnabled(False)
        self._section_btn.clicked.connect(self._open_section)
        result_layout.addWidget(self._section_btn)

        self._diagrams_btn = QPushButton("Effort diagrams")
        self._diagrams_btn.setEnabled(False)
        self._diagrams_btn.clicked.connect(self._open_diagrams)
        result_layout.addWidget(self._diagrams_btn)

        layout.addWidget(result_group)
        layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    # ---------------------------------------------------------------- slots ---

    def _open_results(self) -> None:
        self._ResultsDialog(self._results_text, self).exec()

    def _open_section(self) -> None:
        self._SectionDialog(self._rect_beam, self._calculator, self).exec()

    def _open_diagrams(self) -> None:
        self._DiagramsDialog(self._rect_beam, self).exec()

    # ------------------------------------------------------------ analysis ---

    def _run(self) -> None:
        from src.elements.beam_calculator import BeamCalculator
        from src.loading.forces import (
            design_effort_elu,
        )
        from src.reinforcement.rebar_calculator import RebarCalculator
        from src.reinforcement.stirrup_calculator import StirrupCalculator
        from src.reinforcement.stirrups import Stirrups

        beam = self._beam
        try:
            calc = BeamCalculator(beam, self._pillar_registry)
            supports = calc._build_supports()
            loads = calc._build_loads()
            rect_beam = calc._build_structural_beam(supports, loads)

            max_bm, max_sf = calc._get_max_forces(rect_beam)
            design_sf = design_effort_elu(max_sf)

            stirrup_calc = StirrupCalculator(rect_beam, design_sf)
            stirrups = Stirrups(rect_beam, stirrup_calc)
            calculator = RebarCalculator(rect_beam, max_bm, stirrups)
            calculator.calculate()
        except Exception as exc:  # noqa: BLE001
            self._status_label.setText(f"Error: {exc}")
            self._status_label.setStyleSheet(f"color: {DARK_DANGER};")
            return

        self._rect_beam = rect_beam
        self._calculator = calculator
        self._results_text = self._build_results_text(
            rect_beam, max_bm, max_sf, design_sf, calculator
        )
        self._status_label.setText("Analysis complete.")
        self._status_label.setStyleSheet(f"color: {DARK_SUCCESS}; font-weight: bold;")
        for btn in (self._results_btn, self._section_btn, self._diagrams_btn):
            btn.setEnabled(True)

    def _build_results_text(
        self, rect_beam, max_bm, max_sf, design_sf, calculator
    ) -> str:
        from src.gui.beam_gui import format_reinforcement, format_stirrups

        lines = [
            "BEAM INFO",
            "-" * 44,
            f"Beam ID : {self._beam.id}",
            f"Pillars : {', '.join(self._beam.pillar_ids)}",
            f"Section : bw={self._beam.width:.0f} cm  h={self._beam.height:.0f} cm",
            "",
            "SPANS",
            "-" * 44,
        ]
        for i, span in enumerate(self._beam.spans, 1):
            length = span.get_length(self._pillar_registry)
            lines.append(
                f"  Span {i} ({span.start_pillar_id}→{span.end_pillar_id}): "
                f"L={length:.1f} cm  "
                f"g={span.permanent_load:.3f} kN/m  q={span.variable_load:.3f} kN/m"
            )
        lines += [
            "",
            "EFFORTS",
            "-" * 44,
            f"Max bending moment Mk : {max_bm:.3f} kN.m",
            f"Max shear force Vk    : {max_sf:.3f} kN",
            f"Design shear Vsd      : {design_sf:.3f} kN",
            f"Effective depth d     : {calculator.d:.2f} cm",
        ]
        blocks = ["\n".join(lines)]
        blocks.append(
            format_reinforcement(calculator.tensioned_reinforcement, "Tensioned")
        )
        blocks.append(format_stirrups(calculator.stirrups))
        if calculator.compressed_reinforcement.is_chosen:
            blocks.append(
                format_reinforcement(calculator.compressed_reinforcement, "Compressed")
            )
        return "\n\n".join(blocks)


class SlabReportWindow(QDialog):
    """Dialog showing the deformation check report for a single slab."""

    def __init__(self, slab: Slab, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Report — {slab.id}")
        self.resize(480, 300)
        self._slab = slab
        self._results_text = ""
        self._build_ui()
        self._run()

    # ------------------------------------------------------------------ UI ---

    def _build_ui(self) -> None:
        from src.gui.beam_gui import ResultsDialog

        self._ResultsDialog = ResultsDialog

        layout = QVBoxLayout(self)

        lx, ly = self._slab.dimensions
        slab_type = "One-way" if self._slab.is_one_way else "Two-way"
        summary = QLabel(
            f"<b>{self._slab.id}</b> &nbsp;|&nbsp; "
            f"h = {self._slab.thickness} cm &nbsp;|&nbsp; "
            f"{lx:.0f} × {ly:.0f} cm &nbsp;|&nbsp; "
            f"{slab_type} &nbsp;|&nbsp; {self._slab.local}"
        )
        summary.setStyleSheet(f"color: {DARK_TEXT_PRIMARY}; font-size: 12px;")
        layout.addWidget(summary)

        self._status_label = QLabel("Running…")
        self._status_label.setStyleSheet(f"color: {DARK_TEXT_MUTED};")
        layout.addWidget(self._status_label)

        result_group = QGroupBox("Results")
        result_layout = QVBoxLayout(result_group)

        self._report_btn = QPushButton("Slab deformation report")
        self._report_btn.setEnabled(False)
        self._report_btn.clicked.connect(self._open_report)
        result_layout.addWidget(self._report_btn)

        layout.addWidget(result_group)
        layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    # ---------------------------------------------------------------- slots ---

    def _open_report(self) -> None:
        self._ResultsDialog(self._results_text, self).exec()

    # ------------------------------------------------------------ analysis ---

    def _run(self) -> None:
        from src.loading.slab_deformation_checker import SlabDeformationChecker
        from src.pavement.slab_edge import Edges

        slab = self._slab
        concrete = Concrete[APP_CONFIG.pavement_concrete]

        try:
            support_conditions = {
                edge: slab.edges[edge].support_condition for edge in Edges
            }
            lx, ly = slab.dimensions

            checker = SlabDeformationChecker(
                permanent_load=slab.permanent_load,
                variable_load=slab.variable_load,
                usage=slab.local,
                concrete=concrete,
                lx=lx,
                ly=ly,
                support_conditions=support_conditions,
            )
            passed = checker.verify(slab.thickness)
        except Exception as exc:  # noqa: BLE001
            self._status_label.setText(f"Error: {exc}")
            self._status_label.setStyleSheet(f"color: {DARK_DANGER};")
            return

        self._results_text = self._build_results_text(slab, checker, passed)
        verdict_style = (
            f"color: {DARK_SUCCESS}; font-weight: bold;"
            if passed
            else f"color: {DARK_DANGER}; font-weight: bold;"
        )
        self._status_label.setText(
            "PASS — deformation within limits."
            if passed
            else "FAIL — deformation exceeds limit."
        )
        self._status_label.setStyleSheet(verdict_style)
        self._report_btn.setEnabled(True)

    def _build_results_text(self, slab: Slab, checker, passed: bool) -> str:
        from src.pavement.slab_edge import Edges

        lx, ly = slab.dimensions
        sep = "-" * 50
        slab_type = "One-way" if slab.is_one_way else "Two-way"
        cond_lines = [
            f"    {edge.value.capitalize():8}: {slab.edges[edge].support_condition}"
            for edge in Edges
        ]
        lines = [
            "SLAB INFO",
            sep,
            f"  Slab ID          : {slab.id}",
            f"  Usage            : {slab.local}",
            f"  Type             : {slab_type} (lx/ly = {max(lx, ly) / min(lx, ly):.2f})",
            f"  Dimensions       : lx = {lx:.0f} cm  ly = {ly:.0f} cm",
            f"  Governing span   : {checker.span:.0f} cm  (= min(lx, ly))",
            "  Support conditions:",
            *cond_lines,
            f"  Supporting beams : {', '.join(slab.supporting_beam_ids)}",
            "",
            "LOADS",
            sep,
            f"  Permanent (g)    : {slab.permanent_load:.3f} kN/m²",
            f"  Variable  (q)    : {slab.variable_load:.3f} kN/m²",
            f"  Design load (ELS): {checker.design_load * 10_000:.4f} kN/m²  ({checker.design_load:.6f} kN/cm²)",
            "",
            "DEFORMATION CHECK  (ELS-DEF — ABNT NBR 6118 §17.3.2)",
            sep,
            f"  Final thickness h: {slab.thickness} cm",
            f"  Effective depth d: {checker.effective_depth:.2f} cm",
            f"  Supporting case  : {checker.supporting_case}  (Carvalho Quadro 7.2)",
            f"  Service moment Ms: {checker.service_moment:.4f} kN.cm",
            f"  Cracking moment Mr: {checker.cracking_moment:.4f} kN.cm",
            f"  Section state    : {'CRACKED' if checker.is_cracked else 'UNCRACKED'}",
            f"  Equiv. inertia Ie: {checker.equivalent_moment_of_inertia:.2f} cm⁴",
            f"  Long-term defl.  : {checker.long_term_deflection:.4f} cm",
            f"  Acceptable (L/250): {checker.acceptable_deflection:.4f} cm",
            "",
            f"  Verdict          : {'PASS ✓' if passed else 'FAIL ✗'}",
        ]
        return "\n".join(lines)


class ConfigDialog(QDialog):
    """Dialog for editing all AppConfig values."""

    def __init__(self, parent: "PavementWindow") -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuration")
        self.setMinimumWidth(460)
        self._parent_window = parent
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        layout.addLayout(form)

        def _section(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color: {DARK_TEXT_MUTED}; font-size: 10px; font-weight: bold; margin-top: 6px;"
            )
            return lbl

        # ---- Pavement materials ----
        form.addRow(_section("PAVEMENT MATERIALS"))

        cfg_pav_concrete = QComboBox()
        for c in Concrete:
            cfg_pav_concrete.addItem(c.name, c)
        cfg_pav_concrete.setCurrentText(APP_CONFIG.pavement_concrete)
        cfg_pav_concrete.currentTextChanged.connect(
            lambda v: setattr(APP_CONFIG, "pavement_concrete", v)
        )
        form.addRow("Concrete:", cfg_pav_concrete)

        cfg_pav_steel = QComboBox()
        for s in Steel:
            cfg_pav_steel.addItem(s.name, s)
        cfg_pav_steel.setCurrentText(APP_CONFIG.pavement_steel)
        cfg_pav_steel.currentTextChanged.connect(
            lambda v: setattr(APP_CONFIG, "pavement_steel", v)
        )
        form.addRow("Steel:", cfg_pav_steel)

        # ---- Beam defaults ----
        form.addRow(_section("BEAM DEFAULTS"))

        cfg_beam_concrete = QComboBox()
        for c in Concrete:
            cfg_beam_concrete.addItem(c.name, c)
        cfg_beam_concrete.setCurrentText(APP_CONFIG.default_concrete)
        cfg_beam_concrete.currentTextChanged.connect(
            lambda v: setattr(APP_CONFIG, "default_concrete", v)
        )
        form.addRow("Concrete:", cfg_beam_concrete)

        cfg_beam_steel = QComboBox()
        for s in Steel:
            cfg_beam_steel.addItem(s.name, s)
        cfg_beam_steel.setCurrentText(APP_CONFIG.steel)
        cfg_beam_steel.currentTextChanged.connect(
            lambda v: setattr(APP_CONFIG, "steel", v)
        )
        form.addRow("Steel:", cfg_beam_steel)

        # ---- Reinforcement ----
        form.addRow(_section("REINFORCEMENT"))

        cfg_agg = _spin(0.5, 10.0, 1, 0.5, APP_CONFIG.max_aggregate_size, " cm")
        cfg_agg.valueChanged.connect(
            lambda v: setattr(APP_CONFIG, "max_aggregate_size", v)
        )
        form.addRow("Max. aggregate size:", cfg_agg)

        cfg_bar_types = QSpinBox()
        cfg_bar_types.setRange(1, 5)
        cfg_bar_types.setValue(APP_CONFIG.max_bar_types)
        cfg_bar_types.valueChanged.connect(
            lambda v: setattr(APP_CONFIG, "max_bar_types", v)
        )
        form.addRow("Max. bar types:", cfg_bar_types)

        cfg_layers = QSpinBox()
        cfg_layers.setRange(1, 5)
        cfg_layers.setValue(APP_CONFIG.max_layers)
        cfg_layers.valueChanged.connect(
            lambda v: setattr(APP_CONFIG, "max_layers", v)
        )
        form.addRow("Max. layers:", cfg_layers)

        # ---- Project ----
        form.addRow(_section("PROJECT"))

        cfg_category = QComboBox()
        for cat in TABLE_10.categories:
            cfg_category.addItem(cat.description)
        cfg_category.setCurrentText(APP_CONFIG.building_category)
        cfg_category.currentTextChanged.connect(self._parent_window._on_category_changed)
        form.addRow("Building category:", cfg_category)

        cfg_ceiling = _spin(1.5, 10.0, 2, 0.1, APP_CONFIG.ceiling_height, " m")
        cfg_ceiling.valueChanged.connect(
            lambda v: setattr(APP_CONFIG, "ceiling_height", v)
        )
        form.addRow("Ceiling height:", cfg_ceiling)

        layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
