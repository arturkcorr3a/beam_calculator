"""A pillar: its real section, centered on its coordinates, with its ID."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QGraphicsRectItem

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.results.plan_geometry import PillarShape
from pavement_ui.presentation.plan.items.element_item import ElementItem, cosmetic_pen
from pavement_ui.presentation.plan.items.label_item import LabelItem
from pavement_ui.presentation.plan.scene_units import rect_from_corners_m
from pavement_ui.presentation.theme import tokens

_Z = 30
_LABEL_PT = 9
_LABEL_OFFSET_PX = 10.0
_Align = Qt.AlignmentFlag


class PillarItem(ElementItem, QGraphicsRectItem):
    """Filled section rectangle; the ID sits above-right, or below-right for the lowest row"""

    def __init__(self, shape: PillarShape, lowest: bool) -> None:
        QGraphicsRectItem.__init__(
            self,
            rect_from_corners_m(
                shape.x_m - shape.width_m / 2,
                shape.y_m - shape.depth_m / 2,
                shape.x_m + shape.width_m / 2,
                shape.y_m + shape.depth_m / 2,
            ),
        )
        self.kind, self.element_id = ElementKind.PILLAR, shape.id
        self.setZValue(_Z)
        self.setPen(cosmetic_pen(tokens.PLAN_PILLAR))
        rect = self.rect()
        if lowest:  # Y is up in the scene: bottom() is the larger y
            label = LabelItem(
                shape.id,
                _LABEL_PT,
                True,
                _Align.AlignLeft | _Align.AlignTop,
                (_LABEL_OFFSET_PX, _LABEL_OFFSET_PX),
                self,
            )
            label.setPos(rect.right(), rect.top())
        else:
            label = LabelItem(
                shape.id,
                _LABEL_PT,
                True,
                _Align.AlignLeft | _Align.AlignBottom,
                (_LABEL_OFFSET_PX, -_LABEL_OFFSET_PX),
                self,
            )
            label.setPos(rect.right(), rect.bottom())
        self.labels = (label,)
        self._apply_highlight(False)

    def _apply_highlight(self, highlighted: bool) -> None:
        color = tokens.ACCENT if highlighted else tokens.PLAN_PILLAR
        self.setBrush(QBrush(QColor(color)))
        self.setPen(cosmetic_pen(color))
