"""Common interface of the plan items that represent a registered element."""

from PySide6.QtGui import QPen
from PySide6.QtWidgets import QGraphicsItem

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.presentation.plan.items.label_item import LabelItem
from pavement_ui.presentation.theme import tokens


class ElementItem:
    """Mixin of pillar, beam and slab items: identity and highlight

    Subclasses set ``kind``, ``element_id`` and ``labels``, and implement
    ``_apply_highlight``. Clicks are resolved by walking up to this item.
    """

    kind: ElementKind
    element_id: str
    labels: tuple[LabelItem, ...] = ()

    def set_highlighted(self, highlighted: bool) -> None:
        """Paint the element (and its labels) in the selection color, or not"""
        self._apply_highlight(highlighted)
        for label in self.labels:
            label.set_color(tokens.ACCENT if highlighted else tokens.TEXT)

    def _apply_highlight(self, highlighted: bool) -> None:
        raise NotImplementedError


def cosmetic_pen(color: str, width_px: float = 1.0) -> QPen:
    """A pen whose width is in screen pixels, independent of the zoom"""
    pen = QPen(color)
    pen.setWidthF(width_px)
    pen.setCosmetic(True)
    return pen


def element_of(item: QGraphicsItem | None) -> ElementItem | None:
    """The element an item belongs to (the item itself or one of its parents)"""
    while item is not None:
        if isinstance(item, ElementItem):
            return item
        item = item.parentItem()
    return None
