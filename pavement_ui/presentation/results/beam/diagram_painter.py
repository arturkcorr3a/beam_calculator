"""Paint a bending moment or shear force diagram, on a widget or an image."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF

from pavement_ui.presentation.formatting.numbers import fmt_signed
from pavement_ui.presentation.results.beam.diagram_layout import (
    DiagramGeometry,
    DiagramKind,
)
from pavement_ui.presentation.theme import tokens

_TRIANGLE_PX = 7.0
_LABEL_GAP_PX = 4.0
_COLORS = {
    DiagramKind.MOMENT: (tokens.DIAGRAM_MOMENT_LINE, tokens.DIAGRAM_MOMENT_FILL),
    DiagramKind.SHEAR: (tokens.DIAGRAM_SHEAR_LINE, tokens.DIAGRAM_SHEAR_FILL),
}


def paint_diagram(
    painter: QPainter, geometry: DiagramGeometry, kind: DiagramKind
) -> None:
    """Paint the filled diagram over the axis, with the supports and extreme values

    The painter must have antialiasing set by the caller if wanted.
    """
    if not geometry.polyline:
        return
    line, fill = _COLORS[kind]
    curve = [QPointF(x, y) for x, y in geometry.polyline]
    ends = (
        QPointF(curve[0].x(), geometry.axis_y),
        QPointF(curve[-1].x(), geometry.axis_y),
    )
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(fill)))
    painter.drawPolygon(QPolygonF([ends[0], *curve, ends[1]]))
    painter.setPen(QPen(QColor(line), 1.6))
    painter.drawPolyline(QPolygonF(curve))
    painter.setPen(QPen(QColor(tokens.TEXT), 1.0))
    painter.drawLine(
        QPointF(geometry.left, geometry.axis_y),
        QPointF(geometry.right, geometry.axis_y),
    )
    paint_supports(painter, geometry.supports, geometry.axis_y)
    _paint_labels(painter, geometry, line)


def paint_supports(
    painter: QPainter, supports: tuple[tuple[float, str], ...], axis_y: float
) -> None:
    """Paint a triangle under the axis at each support, with its label below"""
    painter.setPen(QPen(QColor(tokens.TEXT), 1.0))
    painter.setBrush(QBrush(QColor(tokens.TEXT_MUTED)))
    for x, text in supports:
        painter.drawPolygon(
            QPolygonF(
                [
                    QPointF(x, axis_y),
                    QPointF(x - _TRIANGLE_PX, axis_y + _TRIANGLE_PX * 1.4),
                    QPointF(x + _TRIANGLE_PX, axis_y + _TRIANGLE_PX * 1.4),
                ]
            )
        )
        painter.drawText(
            QRectF(x - 30, axis_y + _TRIANGLE_PX * 1.4 + 2, 60, 16),
            Qt.AlignmentFlag.AlignHCenter,
            text,
        )


def _paint_labels(painter: QPainter, geometry: DiagramGeometry, color: str) -> None:
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
