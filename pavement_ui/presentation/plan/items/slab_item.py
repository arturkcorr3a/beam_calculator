"""A slab: the region between its corner pillars, with its ID and usage."""

from collections.abc import Sequence

from PySide6.QtGui import QBrush, QColor, QPolygonF
from PySide6.QtWidgets import QGraphicsPolygonItem

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.results.plan_geometry import Point, SlabShape
from pavement_ui.presentation.plan.items.element_item import ElementItem, cosmetic_pen
from pavement_ui.presentation.plan.items.label_item import LabelItem
from pavement_ui.presentation.plan.scene_units import point
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.theme import tokens

_Z = 10
_ID_PT = 13.5  # 18 px
_USAGE_PT = 8.25  # 11 px
_LINE_GAP_PX = 10.0


class SlabItem(ElementItem, QGraphicsPolygonItem):
    """Filled polygon; ID (bold) above the usage, both centered on the centroid"""

    def __init__(self, shape: SlabShape, polygon_m: Sequence[Point]) -> None:
        QGraphicsPolygonItem.__init__(
            self, QPolygonF([point(x, y) for x, y in polygon_m])
        )
        self.kind, self.element_id = ElementKind.SLAB, shape.id
        self.setZValue(_Z)
        self.setPen(cosmetic_pen(tokens.BORDER))
        center = self.polygon().boundingRect().center()
        title = LabelItem(
            shape.id, _ID_PT, True, offset_px=(0.0, -_LINE_GAP_PX), parent=self
        )
        usage = LabelItem(
            label(OptionKind.USAGE, shape.usage_key),
            _USAGE_PT,
            offset_px=(0.0, _LINE_GAP_PX),
            parent=self,
        )
        for item in (title, usage):
            item.setPos(center)
        self.labels = (title, usage)
        self._apply_highlight(False)

    def _apply_highlight(self, highlighted: bool) -> None:
        fill = tokens.PLAN_SLAB_SELECTED if highlighted else tokens.PLAN_SLAB
        self.setBrush(QBrush(QColor(fill)))
