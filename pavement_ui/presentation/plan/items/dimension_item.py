"""A dimension line with end ticks and its length, e.g. "6,00 m"."""

from PySide6.QtCore import QLineF, QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from pavement_ui.presentation.formatting.numbers import fmt_with_unit
from pavement_ui.presentation.plan.dimension_lines import DimensionSegment
from pavement_ui.presentation.plan.items.element_item import cosmetic_pen
from pavement_ui.presentation.plan.items.label_item import LabelItem
from pavement_ui.presentation.plan.scene_units import point
from pavement_ui.presentation.text.strings import panels as units
from pavement_ui.presentation.theme import tokens

_Z = 40
_TICK = 10.0  # half tick length (cm)
_LABEL_PT = 8
_LABEL_GAP_PX = 4.0
_Align = Qt.AlignmentFlag


class DimensionItem(QGraphicsItem):
    """Horizontal dimensions are labeled below the line, vertical ones to its left"""

    def __init__(self, segment: DimensionSegment) -> None:
        super().__init__()
        self.setZValue(_Z)
        if segment.horizontal:
            a = point(segment.start_m, segment.position_m)
            b = point(segment.end_m, segment.position_m)
            ticks = [QLineF(p.x(), p.y() - _TICK, p.x(), p.y() + _TICK) for p in (a, b)]
            anchor, offset = _Align.AlignHCenter | _Align.AlignTop, (0.0, _LABEL_GAP_PX)
        else:
            a = point(segment.position_m, segment.start_m)
            b = point(segment.position_m, segment.end_m)
            ticks = [QLineF(p.x() - _TICK, p.y(), p.x() + _TICK, p.y()) for p in (a, b)]
            anchor, offset = (
                _Align.AlignRight | _Align.AlignVCenter,
                (-_LABEL_GAP_PX, 0.0),
            )
        self._lines = [QLineF(a, b), *ticks]
        self._rect = QRectF(a, b).normalized().adjusted(-_TICK, -_TICK, _TICK, _TICK)
        text = fmt_with_unit(segment.length_m, 2, units.UNIT_M)
        label = LabelItem(text, _LABEL_PT, anchor=anchor, offset_px=offset, parent=self)
        label.set_color(tokens.TEXT_MUTED)
        label.setPos(QLineF(a, b).center())

    def boundingRect(self) -> QRectF:
        return self._rect

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setPen(cosmetic_pen(tokens.TEXT_MUTED))
        painter.drawLines(self._lines)
