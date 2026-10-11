"""A 1 m grid behind the plan."""

import math

from PySide6.QtCore import QLineF, QRectF
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from pavement_ui.presentation.plan.items.element_item import cosmetic_pen
from pavement_ui.presentation.plan.scene_units import SCENE_UNITS_PER_M
from pavement_ui.presentation.theme import tokens

_Z = 0
_MARGIN = SCENE_UNITS_PER_M  # 1 m around the bounds


class GridItem(QGraphicsItem):
    """Lines every meter over the given bounds plus a 1 m margin"""

    def __init__(self, bounds: QRectF) -> None:
        super().__init__()
        self.setZValue(_Z)
        step = SCENE_UNITS_PER_M
        left = math.floor((bounds.left() - _MARGIN) / step) * step
        right = math.ceil((bounds.right() + _MARGIN) / step) * step
        top = math.floor((bounds.top() - _MARGIN) / step) * step
        bottom = math.ceil((bounds.bottom() + _MARGIN) / step) * step
        self._rect = QRectF(left, top, right - left, bottom - top)
        columns = round((right - left) / step)
        rows = round((bottom - top) / step)
        self._lines = [
            QLineF(left + i * step, top, left + i * step, bottom)
            for i in range(columns + 1)
        ]
        self._lines += [
            QLineF(left, top + j * step, right, top + j * step) for j in range(rows + 1)
        ]

    def boundingRect(self) -> QRectF:
        return self._rect

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        painter.setPen(cosmetic_pen(tokens.PLAN_GRID))
        painter.drawLines(self._lines)
