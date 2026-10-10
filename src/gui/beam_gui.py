# type: ignore

# cSpell:disable

# REVIEW AI-Generated -> re-do after the calculations are finalized

"""
PySide6 desktop GUI for the reinforced-concrete beam calculator.

The window lets the user type the beam geometry (length in metres, width and
height in centimetres) and pick the concrete/steel classes. The self-weight is
computed automatically (25 kN/m3 * cross-section area) and used as the only
load, distributed over the full span, with two pinned supports at the edges.

A schematic of the beam is drawn live as the inputs change. Pressing
"Run Analysis" runs the existing dimensioning engine (unchanged) and enables
three result buttons that open popup dialogs for results, section, and diagrams.
"""

from collections import Counter

import matplotlib

matplotlib.use("QtAgg")  # ensure the Qt backend before importing the canvas
import matplotlib.patches as mpatches
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.analysis.beam_analysis import BeamAnalysis
from src.analysis.model import BeamSupport, DistributedLoad
from src.analysis.solver import analyse_beam
from src.calculators.rebar_calculator import RebarCalculator
from src.calculators.stirrup_calculator import StirrupCalculator
from src.calculators.stirrup_rebar_coordinator import coordinate_span
from src.config import APP_CONFIG
from src.gui.theme import (
    DARK_ACCENT,
    DARK_BG_INPUT,
    DARK_BG_MAIN,
    DARK_BG_PANEL,
    DARK_BORDER,
    DARK_DANGER,
    DARK_TEXT_PRIMARY,
    DARK_WARNING,
    apply_dark_theme,
    style_figure,
)
from src.loading.forces import design_effort_elu
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.reinforcement.stirrups import Stirrups
from src.structural_elements.rectangular_beam import RectangularBeam

# Self-weight of reinforced concrete (ABNT NBR 6118). kN/m3.
CONCRETE_UNIT_WEIGHT = 25.0
# Number of positions sampled along the beam for the effort diagrams.
DIAGRAM_SAMPLES = 200


def _format_diameter(diameter: float) -> str:
    """Render a bar diameter without a trailing '.0' for whole numbers."""
    return str(int(diameter) if float(diameter).is_integer() else diameter)


def format_reinforcement(reinforcement, title: str) -> str:
    lines = [
        title.upper() + " REINFORCEMENT",
        "-" * 44,
        f"Required area: {reinforcement.required_area:.3f} cm2",
    ]

    for index, layer in enumerate(reinforcement.chosen_bars):
        if layer.bars:
            layer_count = Counter([d.diameter_mm for d in layer.bars])
            formatted = " + ".join(
                f"{count} Φ {_format_diameter(diameter)}"
                for diameter, count in sorted(
                    layer_count.items(), key=lambda item: item[0], reverse=True
                )
            )
            lines.append(f"Layer {index + 1}: {formatted}")
        else:
            lines.append(f"Layer {index + 1}: No bars")

    actual_area = sum(layer.area for layer in reinforcement.chosen_bars)
    lines.append(f"Actual reinforcement area: {actual_area:.3f} cm2")
    return "\n".join(lines)


def format_stirrups(stirrups: Stirrups) -> str:
    actual_ratio = Stirrups.calculate_ratio(stirrups.diameter, stirrups.spacing)
    return "\n".join(
        [
            "STIRRUPS",
            "-" * 44,
            f"Required ratio: {stirrups.required_ratio:.4f} cm2/cm",
            f"Chosen: Φ {_format_diameter(stirrups.diameter * 10)} ",
            f"c/ {stirrups.spacing} cm",
            f"Actual ratio: {actual_ratio:.4f} cm2/cm",
        ]
    )


# ----------------------------------------------------------------- dialogs ---


class ConfigDialog(QDialog):
    """Modal dialog for settings that rarely need to change."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configuration")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        form_group = QGroupBox("Materials & reinforcement")
        form = QFormLayout(form_group)

        self.steel_input = QComboBox()
        for steel in Steel:
            self.steel_input.addItem(steel.name, steel)
        self.steel_input.setCurrentText(APP_CONFIG.pavement_steel.name)
        form.addRow("Steel:", self.steel_input)

        self.max_aggregate_size_input = QDoubleSpinBox()
        self.max_aggregate_size_input.setRange(0.5, 10.0)
        self.max_aggregate_size_input.setDecimals(1)
        self.max_aggregate_size_input.setSingleStep(0.5)
        self.max_aggregate_size_input.setValue(APP_CONFIG.max_aggregate_size)
        self.max_aggregate_size_input.setSuffix(" cm")
        form.addRow("Max aggregate size:", self.max_aggregate_size_input)

        self.max_bar_types_input = QSpinBox()
        self.max_bar_types_input.setRange(1, 5)
        self.max_bar_types_input.setValue(APP_CONFIG.max_bar_types)
        form.addRow("Max bar types:", self.max_bar_types_input)

        self.max_layers_input = QSpinBox()
        self.max_layers_input.setRange(1, 5)
        self.max_layers_input.setValue(APP_CONFIG.max_layers)
        form.addRow("Max layers:", self.max_layers_input)

        layout.addWidget(form_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply(self) -> None:
        APP_CONFIG.pavement_steel = Steel[self.steel_input.currentText()]
        APP_CONFIG.max_aggregate_size = self.max_aggregate_size_input.value()
        APP_CONFIG.max_bar_types = self.max_bar_types_input.value()
        APP_CONFIG.max_layers = self.max_layers_input.value()
        self.accept()


class ResultsDialog(QDialog):
    """Shows loads, efforts and designed reinforcement layers."""

    def __init__(self, text: str, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Loads, efforts & designed layers")
        self.resize(460, 500)

        layout = QVBoxLayout(self)
        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Menlo", 11))
        text_edit.setPlainText(text)
        layout.addWidget(text_edit)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class SectionDialog(QDialog):
    """Shows the designed cross-section with reinforcements."""

    def __init__(
        self,
        beam: RectangularBeam,
        calculator,
        stirrups: Stirrups,
        parent: QWidget = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Designed cross-section")
        self.resize(520, 600)

        layout = QVBoxLayout(self)
        fig = Figure(figsize=(4.8, 5.5), layout="constrained")
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self._draw(fig, beam, calculator, stirrups)
        canvas.draw()

    def _draw(
        self, fig: Figure, beam: RectangularBeam, calculator, stirrups: Stirrups
    ) -> None:  # NOSONAR
        style_figure(fig, DARK_BG_MAIN)
        w = beam.width
        h = beam.height
        cov = RectangularBeam.nominal_covering

        ax = fig.add_subplot(111)
        ax.set_facecolor(DARK_BG_MAIN)
        ax.set_aspect("equal")
        ax.axis("off")

        # Beam concrete section
        ax.add_patch(
            mpatches.Rectangle(
                (0, 0),
                w,
                h,
                facecolor=DARK_BG_PANEL,
                edgecolor=DARK_ACCENT,
                linewidth=2.0,
            )
        )

        stirrup_d_cm = stirrups.diameter
        sx0, sy0 = cov, cov
        sw, sh = w - 2 * cov, h - 2 * cov
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (sx0, sy0),
                sw,
                sh,
                boxstyle="round,pad=0",
                facecolor="none",
                edgecolor="#bb9af7",
                linewidth=1.4,
                linestyle="--",
            )
        )

        stirrup_spacing = stirrups.spacing
        stirrup_diam_mm = int(stirrup_d_cm * 10)
        ax.text(
            w / 2,
            h + 0.8,
            f"Estribo: Φ{stirrup_diam_mm} c/{stirrup_spacing:.0f} cm",
            ha="center",
            va="bottom",
            fontsize=8,
            color=DARK_TEXT_PRIMARY,
        )

        def draw_bar_row(y_center: float, bars: list, label_side: str) -> None:
            if not bars:
                return
            n = len(bars)
            inner_w = sw - 2 * stirrup_d_cm
            spacing = inner_w / (n + 1)
            x_start = sx0 + stirrup_d_cm
            counts = Counter([d.diameter_mm for d in bars])
            label = " + ".join(
                f"{cnt}Φ{int(d) if float(d).is_integer() else d}"
                for d, cnt in sorted(counts.items(), key=lambda x: x[0], reverse=True)
            )
            for i, bar in enumerate(bars):
                r = bar.diameter_mm / 10 / 2
                cx = x_start + (i + 1) * spacing
                ax.add_patch(
                    mpatches.Circle(
                        (cx, y_center),
                        r,
                        facecolor=DARK_ACCENT,
                        edgecolor="#ffffff",
                        linewidth=0.8,
                    )
                )
            lx = -1.0 if label_side == "left" else w + 1.0
            ha = "right" if label_side == "left" else "left"
            ax.annotate(
                label,
                xy=(lx, y_center),
                fontsize=8,
                ha=ha,
                va="center",
                color=DARK_TEXT_PRIMARY,
            )

        chosen = [
            layer.bars for layer in calculator.tensioned_reinforcement.chosen_bars
        ]
        for layer_idx, layer in enumerate(chosen):
            if not layer:
                continue
            max_bar_r = max(d.diameter_mm / 10 / 2 for d in layer)
            if layer_idx == 0:
                y = cov + stirrup_d_cm + max_bar_r
            else:
                prev = chosen[layer_idx - 1]
                prev_r = max(d.diameter_mm / 10 / 2 for d in prev) if prev else 0
                spacing_v = cov / 2
                y_prev = cov + stirrup_d_cm + prev_r
                for li in range(1, layer_idx):
                    li_bars = chosen[li - 1]
                    li_r = (
                        max(d.diameter_mm / 10 / 2 for d in li_bars) if li_bars else 0
                    )
                    y_prev += 2 * li_r + spacing_v
                y = y_prev + 2 * prev_r + spacing_v + max_bar_r
            draw_bar_row(y, layer, "left")

        comp = calculator.compressed_reinforcement
        if comp.is_chosen:
            for layer_idx, layer in enumerate(layer.bars for layer in comp.chosen_bars):
                if not layer:
                    continue
                max_bar_r = max(d.diameter_mm / 10 / 2 for d in layer)
                y = (
                    h
                    - cov
                    - stirrup_d_cm
                    - max_bar_r
                    - layer_idx * (2 * max_bar_r + 0.5)
                )
                draw_bar_row(y, layer, "right")

        arrow_kw = {"arrowstyle": "<->", "color": DARK_ACCENT, "lw": 1.0}
        y_dim = -2.5
        ax.annotate("", xy=(0, y_dim), xytext=(w, y_dim), arrowprops=arrow_kw)
        ax.text(
            w / 2,
            y_dim - 0.6,
            f"b = {w:.0f} cm",
            ha="center",
            va="top",
            fontsize=8,
            color=DARK_TEXT_PRIMARY,
        )

        x_dim = w + 2.5
        ax.annotate("", xy=(x_dim, 0), xytext=(x_dim, h), arrowprops=arrow_kw)
        ax.text(
            x_dim + 0.4,
            h / 2,
            f"h = {h:.0f} cm",
            ha="left",
            va="center",
            fontsize=8,
            color=DARK_TEXT_PRIMARY,
            rotation=90,
        )

        ax.set_xlim(-6, w + 6)
        ax.set_ylim(y_dim - 2, h + 3)


class DiagramsDialog(QDialog):
    """Shows bending-moment and shear-force diagrams."""

    def __init__(self, analysis: BeamAnalysis, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Effort diagrams")
        self.resize(720, 500)

        layout = QVBoxLayout(self)
        fig = Figure(figsize=(7, 4.5), layout="constrained")
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self._draw(fig, analysis)
        canvas.draw()

    def _draw(self, fig: Figure, analysis: BeamAnalysis) -> None:
        style_figure(fig, DARK_BG_MAIN)
        positions = [
            analysis.length * i / DIAGRAM_SAMPLES for i in range(DIAGRAM_SAMPLES + 1)
        ]  # cm
        moments = [analysis.bending_moment(x) for x in positions]
        shears = [analysis.shear_force(x) for x in positions]
        xs = [x / 100.0 for x in positions]  # m

        ax_m = fig.add_subplot(211)
        ax_v = fig.add_subplot(212)

        moments_inv = [-m for m in moments]
        ax_m.set_facecolor(DARK_BG_INPUT)
        ax_m.plot(xs, moments_inv, color=DARK_ACCENT, linewidth=1.8)
        ax_m.fill_between(xs, moments_inv, color=DARK_ACCENT, alpha=0.25)
        ax_m.axhline(0, color=DARK_BORDER, linewidth=0.8)
        ax_m.set_ylabel("M [kN.m]", color=DARK_TEXT_PRIMARY)
        ax_m.set_title("Bending moment diagram", fontsize=10, color=DARK_TEXT_PRIMARY)
        ax_m.grid(True, alpha=0.35, color=DARK_BORDER)

        ax_v.set_facecolor(DARK_BG_INPUT)
        ax_v.plot(xs, shears, color=DARK_DANGER, linewidth=1.8)
        ax_v.fill_between(xs, shears, color=DARK_DANGER, alpha=0.25)
        ax_v.axhline(0, color=DARK_BORDER, linewidth=0.8)
        ax_v.set_ylabel("V [kN]", color=DARK_TEXT_PRIMARY)
        ax_v.set_xlabel("position along beam [m]", color=DARK_TEXT_PRIMARY)
        ax_v.set_title("Shear force diagram", fontsize=10, color=DARK_TEXT_PRIMARY)
        ax_v.grid(True, alpha=0.35, color=DARK_BORDER)


# ------------------------------------------------------------ main window ---


class BeamCalculatorWindow(QMainWindow):
    """Main application window for the beam calculator GUI."""

    def __init__(self) -> None:
        super().__init__()
        apply_dark_theme()
        self.setWindowTitle("Reinforced Concrete Beam Calculator")
        self.resize(900, 620)

        self._last_results_text: str = ""
        self._last_beam: RectangularBeam | None = None
        self._last_analysis: BeamAnalysis | None = None
        self._last_calculator = None
        self._last_stirrups: Stirrups | None = None
        self._pavement_window = None

        self._build_ui()
        self._build_menu()
        self._connect_signals()

        self._update_self_weight_label()
        self._draw_beam_schematic()

    # ------------------------------------------------------------------ UI --
    def _build_menu(self) -> None:

        menu_bar = self.menuBar()
        tools_menu = menu_bar.addMenu("Tools")
        pavement_action = tools_menu.addAction("Pavement Designer...")
        pavement_action.triggered.connect(self._open_pavement_designer)

    def _open_pavement_designer(self) -> None:
        from src.gui.pavement_gui import PavementWindow

        if self._pavement_window is None or not self._pavement_window.isVisible():
            self._pavement_window = PavementWindow(self)
        self._pavement_window.show()
        self._pavement_window.raise_()
        self._pavement_window.activateWindow()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(splitter)

        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([380, 520])

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # --- Inputs group ---
        inputs_group = QGroupBox("Beam inputs")
        form = QFormLayout(inputs_group)

        self.length_input = QDoubleSpinBox()
        self.length_input.setRange(0.1, 100.0)
        self.length_input.setDecimals(2)
        self.length_input.setSingleStep(0.1)
        self.length_input.setValue(5.0)
        self.length_input.setSuffix(" m")
        form.addRow("Length:", self.length_input)

        self.width_input = QDoubleSpinBox()
        self.width_input.setRange(12.0, 200.0)
        self.width_input.setDecimals(1)
        self.width_input.setSingleStep(1.0)
        self.width_input.setValue(20.0)
        self.width_input.setSuffix(" cm")
        form.addRow("Width:", self.width_input)

        self.height_input = QDoubleSpinBox()
        self.height_input.setRange(5.0, 300.0)
        self.height_input.setDecimals(1)
        self.height_input.setSingleStep(1.0)
        self.height_input.setValue(50.0)
        self.height_input.setSuffix(" cm")
        form.addRow("Height:", self.height_input)

        self.concrete_input = QComboBox()
        for concrete in Concrete:
            self.concrete_input.addItem(concrete.name, concrete)
        self.concrete_input.setCurrentText(APP_CONFIG.pavement_concrete.name)
        form.addRow("Concrete:", self.concrete_input)

        self.self_weight_label = QLabel()
        self.self_weight_label.setStyleSheet("font-weight: bold; color: #7aa2f7;")
        form.addRow("Self-weight load:", self.self_weight_label)

        layout.addWidget(inputs_group)

        # --- Run + config row ---
        run_row = QHBoxLayout()
        self.run_button = QPushButton("Run Analysis")
        self.run_button.setMinimumHeight(38)
        self.config_button = QPushButton("⚙")
        self.config_button.setMinimumHeight(38)
        self.config_button.setFixedWidth(38)
        self.config_button.setToolTip("Configuration")
        run_row.addWidget(self.run_button)
        run_row.addWidget(self.config_button)
        layout.addLayout(run_row)

        # --- Result buttons (enabled after analysis) ---
        result_group = QGroupBox("Results")
        result_layout = QVBoxLayout(result_group)

        self.results_button = QPushButton("Loads, efforts & layers")
        self.results_button.setEnabled(False)
        result_layout.addWidget(self.results_button)

        self.section_button = QPushButton("Designed cross-section")
        self.section_button.setEnabled(False)
        result_layout.addWidget(self.section_button)

        self.diagrams_button = QPushButton("Effort diagrams")
        self.diagrams_button.setEnabled(False)
        result_layout.addWidget(self.diagrams_button)

        layout.addWidget(result_group)
        layout.addStretch(1)

        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        schematic_group = QGroupBox("Beam schematic")
        schematic_layout = QVBoxLayout(schematic_group)
        self.schematic_figure = Figure(figsize=(6, 2.6), layout="constrained")
        self.schematic_canvas = FigureCanvas(self.schematic_figure)
        schematic_layout.addWidget(self.schematic_canvas)
        layout.addWidget(schematic_group, stretch=1)

        return panel

    def _connect_signals(self) -> None:
        for spin in (self.length_input, self.width_input, self.height_input):
            spin.valueChanged.connect(self._on_inputs_changed)
        self.concrete_input.currentIndexChanged.connect(self._on_inputs_changed)
        self.run_button.clicked.connect(self.run_analysis)
        self.config_button.clicked.connect(self._open_config)
        self.results_button.clicked.connect(self._open_results)
        self.section_button.clicked.connect(self._open_section)
        self.diagrams_button.clicked.connect(self._open_diagrams)

    # -------------------------------------------------------------- helpers --
    def _current_geometry(self):
        length_cm = self.length_input.value() * 100.0
        return length_cm, self.width_input.value(), self.height_input.value()

    def _self_weight(self) -> float:
        width = self.width_input.value()
        height = self.height_input.value()
        area = (width / 100.0) * (height / 100.0)
        return CONCRETE_UNIT_WEIGHT * area

    # --------------------------------------------------------------- slots ---
    def _on_inputs_changed(self, *_args) -> None:
        self._update_self_weight_label()
        self._draw_beam_schematic()

    def _update_self_weight_label(self) -> None:
        self.self_weight_label.setText(f"{self._self_weight():.2f} kN/m")

    def _open_config(self) -> None:
        ConfigDialog(self).exec()

    def _open_results(self) -> None:
        ResultsDialog(self._last_results_text, self).exec()

    def _open_section(self) -> None:
        SectionDialog(
            self._last_beam, self._last_calculator, self._last_stirrups, self
        ).exec()

    def _open_diagrams(self) -> None:
        DiagramsDialog(self._last_analysis, self).exec()

    def _draw_beam_schematic(self) -> None:
        length_m = self.length_input.value()
        width = self.width_input.value()
        height = self.height_input.value()

        fig = self.schematic_figure
        style_figure(fig, DARK_BG_PANEL)
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_facecolor(DARK_BG_PANEL)

        length_cm = max(length_m * 100.0, 1e-6)
        bar_h = max(min(height / length_cm, 0.18), 0.05)
        y0 = 0.0

        # Beam element
        ax.add_patch(
            mpatches.Rectangle(
                (0.0, y0),
                1.0,
                bar_h,
                facecolor="#2d3f66",
                edgecolor=DARK_ACCENT,
                linewidth=1.8,
            )
        )

        # Pinned supports
        tri_h = bar_h * 1.2
        tri_w = 0.05
        for x in (0.0, 1.0):
            ax.add_patch(
                mpatches.Polygon(
                    [(x - tri_w, y0 - tri_h), (x + tri_w, y0 - tri_h), (x, y0)],
                    closed=True,
                    facecolor=DARK_WARNING,
                    edgecolor="#ff9e3b",
                )
            )
            ax.plot(
                [x - tri_w * 1.6, x + tri_w * 1.6],
                [y0 - tri_h, y0 - tri_h],
                color="#ff9e3b",
                linewidth=1.4,
            )

        # Distributed load arrows
        arrow_top = bar_h + tri_h
        n_arrows = 9
        for i in range(n_arrows):
            x = i / (n_arrows - 1)
            ax.annotate(
                "",
                xy=(x, bar_h),
                xytext=(x, arrow_top),
                arrowprops={"arrowstyle": "->", "color": DARK_DANGER, "lw": 1.2},
            )
        ax.plot([0.0, 1.0], [arrow_top, arrow_top], color=DARK_DANGER, lw=1.4)
        ax.text(
            0.5,
            arrow_top + tri_h * 0.4,
            f"self-weight q = {self._self_weight():.2f} kN/m",
            ha="center",
            va="bottom",
            color=DARK_DANGER,
            fontsize=9,
        )

        # Dimension annotation
        dim_y = y0 - tri_h * 2.0
        ax.annotate(
            "",
            xy=(0.0, dim_y),
            xytext=(1.0, dim_y),
            arrowprops={"arrowstyle": "<->", "color": DARK_ACCENT, "lw": 1.0},
        )
        ax.text(
            0.5,
            dim_y - tri_h * 0.5,
            f"L = {length_m:.2f} m",
            ha="center",
            va="top",
            color=DARK_TEXT_PRIMARY,
            fontsize=9,
        )

        ax.set_title(
            f"Bi-supported beam  |  section {width:.0f} x {height:.0f} cm (W x H)",
            fontsize=10,
            color=DARK_TEXT_PRIMARY,
        )
        ax.set_xlim(-0.12, 1.12)
        ax.set_ylim(dim_y - tri_h * 1.6, arrow_top + tri_h * 1.6)
        ax.set_aspect("auto")
        ax.axis("off")
        self.schematic_canvas.draw_idle()

    # ------------------------------------------------------------- analysis --
    def run_analysis(self) -> None:
        length_cm, width, height = self._current_geometry()
        concrete: Concrete = self.concrete_input.currentData()
        steel: Steel = APP_CONFIG.pavement_steel

        try:
            beam = RectangularBeam(length_cm, width, height, concrete, steel)
            analysis = analyse_beam(
                beam,
                [BeamSupport(0.0), BeamSupport(length_cm)],
                [DistributedLoad(0.0, length_cm, self._self_weight())],
            )

            position, max_bending_moment = analysis.moment_extreme_in_range(
                0.0, length_cm
            )
            design_shear_force = design_effort_elu(analysis.max_abs_shear())

            stirrup_calculator = StirrupCalculator(beam, design_shear_force)
            stirrups = Stirrups(beam, stirrup_calculator)
            calculator = RebarCalculator(
                beam=beam,
                bending_moment=max_bending_moment,
                bending_moment_position=position,
            )
            coordinate_span([calculator], stirrups)
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Design not verified",
                f"The section could not be designed:\n\n{exc}\n\n"
                "Try a larger cross-section or a stronger concrete class.",
            )
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "Analysis error",
                f"An unexpected error occurred during analysis:\n\n{exc}",
            )
            return

        self._last_beam = beam
        self._last_analysis = analysis
        self._last_calculator = calculator
        self._last_stirrups = stirrups
        self._last_results_text = self._build_results_text(
            analysis, max_bending_moment, design_shear_force, calculator, stirrups
        )

        for btn in (self.results_button, self.section_button, self.diagrams_button):
            btn.setEnabled(True)

    def _build_results_text(
        self, analysis, max_bending_moment, design_shear_force, calculator, stirrups
    ) -> str:
        length_cm = analysis.length
        reaction_a = analysis.reaction(0.0)
        reaction_b = analysis.reaction(length_cm)
        max_shear = analysis.max_abs_shear()

        blocks: list[str] = []
        blocks.append(
            "\n".join(
                [
                    "LOADS & EFFORTS",
                    "-" * 44,
                    f"Self-weight load q : {self._self_weight():.3f} kN/m",
                    f"Reaction @ left    : {reaction_a:.3f} kN",
                    f"Reaction @ right   : {reaction_b:.3f} kN",
                    f"Max bending moment : {max_bending_moment:.3f} kN.m",
                    f"Max shear force    : {max_shear:.3f} kN",
                    f"Design shear (x1.4): {design_shear_force:.3f} kN",
                    f"Effective depth d  : {calculator.d:.2f} cm",
                ]
            )
        )
        blocks.append(
            format_reinforcement(calculator.tensioned_reinforcement, "Tensioned")
        )
        blocks.append(format_stirrups(stirrups))
        if calculator.compressed_reinforcement.is_chosen:
            blocks.append(
                format_reinforcement(calculator.compressed_reinforcement, "Compressed")
            )

        return "\n\n".join(blocks)
