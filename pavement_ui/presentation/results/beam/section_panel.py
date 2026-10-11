"""The section panel: a design-point combo in its header driving the section drawing."""

from PySide6.QtWidgets import QComboBox, QWidget

from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.presentation.formatting.elements import fmt_point_label
from pavement_ui.presentation.results.beam.section_layout import section_layout
from pavement_ui.presentation.results.beam.section_widget import SectionWidget
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.widgets.titled_panel import TitledPanel


class SectionPanel(TitledPanel):
    """ "Seção transversal dimensionada", for the point selected in the combo"""

    def __init__(self, parent: QWidget | None = None) -> None:
        self._drawing = SectionWidget()
        super().__init__(s.SECTION_PANEL, self._drawing, parent=parent)
        self._points = QComboBox()
        self._points.setObjectName("sectionPoint")
        self._points.currentIndexChanged.connect(self._show_point)
        self.add_tool(self._points)
        self._result: BeamResult | None = None

    def set_result(self, result: BeamResult) -> None:
        self._result = result
        self._points.blockSignals(True)
        self._points.clear()
        self._points.addItems([fmt_point_label(p) for p in result.points])
        self._points.blockSignals(False)
        self._points.setCurrentIndex(0 if result.points else -1)
        self._show_point(self._points.currentIndex())

    def _show_point(self, index: int) -> None:
        result = self._result
        if result is None or not 0 <= index < len(result.points):
            self._drawing.clear()
            return
        point = result.points[index]
        stirrup = result.spans[point.span_index - 1].stirrup
        layout = section_layout(
            point,
            result.width_cm,
            result.height_cm,
            result.cover_cm,
            stirrup.diameter_mm,
        )
        self._drawing.set_section(layout, stirrup, result.cover_cm)
