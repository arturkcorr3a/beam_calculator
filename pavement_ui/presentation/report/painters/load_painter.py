"""Paint a beam's load scheme: the axis, the supports and g and q on each span."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen

from pavement_ui.core.results.beam_result import BeamResult
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.results.beam.diagram_painter import paint_supports
from pavement_ui.presentation.text.strings import report as s
from pavement_ui.presentation.theme import tokens

_SIDE_MARGIN_PX = 40.0
_BOTTOM_ROOM_PX = 34.0  # supports and their names under the axis
_TOP_ROOM_PX = 40.0  # load labels over the tallest block
_LABEL_HEIGHT_PX = 34.0  # two lines: g and q


def paint_loads(painter: QPainter, result: BeamResult, rect: QRectF) -> None:
    """Paint each span's g (bottom) and q (top) as blocks over the axis, to scale"""
    length = max((support.position_m for support in result.supports), default=0.0)
    peak = max((span.g_kn_m + span.q_kn_m for span in result.spans), default=0.0)
    if length <= 0 or peak <= 0:
        return
    left, right = rect.left() + _SIDE_MARGIN_PX, rect.right() - _SIDE_MARGIN_PX
    axis_y = rect.bottom() - _BOTTOM_ROOM_PX
    room = axis_y - rect.top() - _TOP_ROOM_PX

    def px(x_m: float) -> float:
        return left + x_m / length * (right - left)

    painter.save()
    for span in result.spans:
        x0, x1 = px(span.start_m), px(span.end_m)
        g_height = span.g_kn_m / peak * room
        q_height = span.q_kn_m / peak * room
        painter.setPen(QPen(QColor(tokens.DIAGRAM_MOMENT_LINE), 1.0))
        painter.setBrush(QBrush(QColor(tokens.DIAGRAM_MOMENT_FILL)))
        painter.drawRect(QRectF(x0, axis_y - g_height, x1 - x0, g_height))
        painter.setPen(QPen(QColor(tokens.DIAGRAM_SHEAR_LINE), 1.0))
        painter.setBrush(QBrush(QColor(tokens.DIAGRAM_SHEAR_FILL)))
        painter.drawRect(QRectF(x0, axis_y - g_height - q_height, x1 - x0, q_height))
        painter.setPen(QColor(tokens.TEXT))
        painter.drawText(
            QRectF(
                x0,
                axis_y - g_height - q_height - _LABEL_HEIGHT_PX - 2,
                x1 - x0,
                _LABEL_HEIGHT_PX,
            ),
            Qt.AlignmentFlag.AlignCenter,
            s.LOAD_LABEL.format(
                g=fmt_number(span.g_kn_m, 2), q=fmt_number(span.q_kn_m, 2)
            ),
        )
    painter.setPen(QPen(QColor(tokens.TEXT), 1.0))
    painter.drawLine(QPointF(left, axis_y), QPointF(right, axis_y))
    supports = tuple((px(s_.position_m), s_.label) for s_ in result.supports)
    paint_supports(painter, supports, axis_y)
    painter.restore()
