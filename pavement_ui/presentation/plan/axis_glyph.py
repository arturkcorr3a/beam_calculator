"""The X→ / Y↑ indicator drawn in the top-left corner of the plan viewport."""

from PySide6.QtCore import QPointF, QRect
from PySide6.QtGui import QFont, QPainter, QPolygonF

from pavement_ui.presentation.plan.items.element_item import cosmetic_pen
from pavement_ui.presentation.text.strings import main_window as s
from pavement_ui.presentation.theme import tokens

_MARGIN_PX = 16.0
_LENGTH_PX = 34.0
_HEAD_PX = 5.0
_FONT_PT = 8


def _arrow_head(tip: QPointF, dx: float, dy: float) -> QPolygonF:
    """Triangle at tip pointing along (dx, dy), a unit axis direction."""
    back = QPointF(tip.x() - dx * _HEAD_PX * 1.6, tip.y() - dy * _HEAD_PX * 1.6)
    side = QPointF(dy * _HEAD_PX, dx * _HEAD_PX)
    return QPolygonF([tip, back + side, back - side])


def draw_axis_glyph(painter: QPainter, viewport: QRect) -> None:
    """Draw the axes in screen pixels (call with the painter already reset to them)"""
    origin = QPointF(
        viewport.left() + _MARGIN_PX, viewport.top() + _MARGIN_PX + _LENGTH_PX
    )
    x_tip = QPointF(origin.x() + _LENGTH_PX, origin.y())
    y_tip = QPointF(origin.x(), origin.y() - _LENGTH_PX)
    painter.save()
    painter.setPen(cosmetic_pen(tokens.TEXT_MUTED, 1.4))
    painter.setBrush(painter.pen().color())
    painter.drawLine(origin, x_tip)
    painter.drawLine(origin, y_tip)
    painter.drawPolygon(_arrow_head(x_tip, 1.0, 0.0))
    painter.drawPolygon(_arrow_head(y_tip, 0.0, -1.0))
    font = QFont()
    font.setPointSize(_FONT_PT)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QPointF(x_tip.x() + 4, x_tip.y() + 4), s.AXIS_X)
    painter.drawText(QPointF(y_tip.x() - 3, y_tip.y() - 6), s.AXIS_Y)
    painter.restore()
