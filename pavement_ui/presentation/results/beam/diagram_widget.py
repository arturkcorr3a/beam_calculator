"""Draw a bending moment or shear force diagram along the beam."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPaintEvent, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.presentation.formatting.numbers import fmt_signed
from pavement_ui.presentation.results.beam.diagram_layout import (
    DiagramGeometry,
    DiagramKind,
    diagram_geometry,
)
from pavement_ui.presentation.theme import tokens

_TRIANGLE_PX = 7.0
_LABEL_GAP_PX = 4.0
_COLORS = {
    DiagramKind.MOMENT: (tokens.DIAGRAM_MOMENT_LINE, tokens.DIAGRAM_MOMENT_FILL),
    DiagramKind.SHEAR: (tokens.DIAGRAM_SHEAR_LINE, tokens.DIAGRAM_SHEAR_FILL),
}


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
        if geometry is None or not geometry.polyline:
            return
        line, fill = _COLORS[self._kind]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        curve = [QPointF(x, y) for x, y in geometry.polyline]
        ends = (
            QPointF(curve[0].x(), geometry.axis_y),
            QPointF(curve[-1].x(), geometry.axis_y),
        )
        area = QPolygonF([ends[0], *curve, ends[1]])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(fill)))
        painter.drawPolygon(area)
        painter.setPen(QPen(QColor(line), 1.6))
        painter.drawPolyline(QPolygonF(curve))
        painter.setPen(QPen(QColor(tokens.TEXT), 1.0))
        painter.drawLine(
            QPointF(geometry.left, geometry.axis_y),
            QPointF(geometry.right, geometry.axis_y),
        )
        self._draw_supports(painter, geometry)
        self._draw_labels(painter, geometry, line)
        painter.end()

    def _draw_supports(self, painter: QPainter, geometry: DiagramGeometry) -> None:
        painter.setBrush(QBrush(QColor(tokens.TEXT_MUTED)))
        for x, text in geometry.supports:
            y = geometry.axis_y
            triangle = QPolygonF(
                [
                    QPointF(x, y),
                    QPointF(x - _TRIANGLE_PX, y + _TRIANGLE_PX * 1.4),
                    QPointF(x + _TRIANGLE_PX, y + _TRIANGLE_PX * 1.4),
                ]
            )
            painter.drawPolygon(triangle)
            painter.drawText(
                QRectF(x - 30, y + _TRIANGLE_PX * 1.4 + 2, 60, 16),
                Qt.AlignmentFlag.AlignHCenter,
                text,
            )

    def _draw_labels(
        self, painter: QPainter, geometry: DiagramGeometry, color: str
    ) -> None:
        painter.setPen(QColor(color))
        for label in geometry.labels:
            text = fmt_signed(label.value, 1)
            if label.below_axis:
                box = QRectF(label.x - 40, label.y + _LABEL_GAP_PX, 80, 16)
                align = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
            else:
                box = QRectF(label.x - 40, label.y - _LABEL_GAP_PX - 16, 80, 16)
                align = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
            painter.drawText(box, align, text)
