"""A slab: the region between its corner pillars, with its ID, usage and lowering."""

from collections.abc import Sequence

from PySide6.QtGui import QBrush, QColor, QPolygonF
from PySide6.QtWidgets import QGraphicsPolygonItem

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.results.plan_geometry import Point, SlabShape
from pavement_ui.presentation.plan.items.element_item import ElementItem, cosmetic_pen
from pavement_ui.presentation.plan.items.label_item import LabelItem
from pavement_ui.presentation.plan.scene_units import point
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import main_window as s
from pavement_ui.presentation.theme import tokens

_Z = 10
_ID_PT = 13.5  # 18 px
_USAGE_PT = 8.25  # 11 px
_LINE_GAP_PX = 10.0
_LOWERED_OFFSET_PX = 24.0  # below the usage line


class SlabItem(ElementItem, QGraphicsPolygonItem):
    """Filled polygon; ID (bold) above the usage, both centered on the centroid

    A lowered slab gets its own fill and a third line with the lowering.
    """

    def __init__(self, shape: SlabShape, polygon_m: Sequence[Point]) -> None:
        QGraphicsPolygonItem.__init__(
            self, QPolygonF([point(x, y) for x, y in polygon_m])
        )
        self.kind, self.element_id = ElementKind.SLAB, shape.id
        self._lowered = shape.lowered_cm > 0
        self.setZValue(_Z)
        self.setPen(cosmetic_pen(tokens.BORDER))
        center = self.polygon().boundingRect().center()
        labels = [
            LabelItem(
                shape.id, _ID_PT, True, offset_px=(0.0, -_LINE_GAP_PX), parent=self
            ),
            LabelItem(
                label(OptionKind.USAGE, shape.usage_key),
                _USAGE_PT,
                offset_px=(0.0, _LINE_GAP_PX),
                parent=self,
            ),
        ]
        if self._lowered:
            labels.append(
                LabelItem(
                    s.PLAN_SLAB_LOWERED.format(cm=shape.lowered_cm),
                    _USAGE_PT,
                    offset_px=(0.0, _LOWERED_OFFSET_PX),
                    parent=self,
                )
            )
        for item in labels:
            item.setPos(center)
        self.labels = tuple(labels)
        self._apply_highlight(False)

    def _apply_highlight(self, highlighted: bool) -> None:
        if self._lowered:
            fill = (
                tokens.PLAN_SLAB_LOWERED_SELECTED
                if highlighted
                else tokens.PLAN_SLAB_LOWERED
            )
        else:
            fill = tokens.PLAN_SLAB_SELECTED if highlighted else tokens.PLAN_SLAB
        self.setBrush(QBrush(QColor(fill)))
