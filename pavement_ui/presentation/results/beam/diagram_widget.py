"""Draw a bending moment or shear force diagram along the beam."""

from PySide6.QtGui import QPainter, QPaintEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.presentation.results.beam.diagram_layout import (
    DiagramGeometry,
    DiagramKind,
    diagram_geometry,
)
from pavement_ui.presentation.results.beam.diagram_painter import paint_diagram


class DiagramWidget(QWidget):
    """Filled diagram over the beam axis, with supports and extreme values"""

    def __init__(self, kind: DiagramKind, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kind = kind
        self._result: BeamResult | None = None
        self.setMinimumSize(320, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_result(self, result: BeamResult | None) -> None:
        self._result = result
        self.update()

    def geometry_for_size(self) -> DiagramGeometry | None:
        """The diagram scaled to the current size (None without a result)"""
        result = self._result
        if result is None:
            return None
        series = result.moment if self._kind is DiagramKind.MOMENT else result.shear
        return diagram_geometry(
            series,
            result.supports,
            result.spans,
            self._kind,
            self.width(),
            self.height(),
        )

    def paintEvent(self, event: QPaintEvent) -> None:
        geometry = self.geometry_for_size()
        if geometry is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint_diagram(painter, geometry, self._kind)
        painter.end()
