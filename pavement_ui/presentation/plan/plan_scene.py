"""PlanScene: the plan's graphics items, rebuilt from a PlanGeometry."""

from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QGraphicsScene

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.results.plan_geometry import PlanGeometry
from pavement_ui.presentation.plan.dimension_lines import dimension_segments
from pavement_ui.presentation.plan.items.beam_item import BeamItem
from pavement_ui.presentation.plan.items.dimension_item import DimensionItem
from pavement_ui.presentation.plan.items.element_item import ElementItem
from pavement_ui.presentation.plan.items.grid_item import GridItem
from pavement_ui.presentation.plan.items.pillar_item import PillarItem
from pavement_ui.presentation.plan.items.slab_item import SlabItem
from pavement_ui.presentation.plan.scene_units import geometry_bounds

_LOWEST_ROW_TOLERANCE_M = 0.01
_PAN_ROOM = 3.0  # scene margin, in plan sizes


class PlanScene(QGraphicsScene):
    """Turns the engine-resolved geometry (m) into items (cm); computes no geometry"""

    def __init__(self) -> None:
        super().__init__()
        self._elements: dict[tuple[ElementKind, str], ElementItem] = {}
        self._highlighted: tuple[ElementKind, str] | None = None
        self._bounds: QRectF | None = None

    @property
    def bounds(self) -> QRectF | None:
        """Rectangle enclosing every pillar and beam, or None for an empty plan"""
        return self._bounds

    def rebuild(self, geometry: PlanGeometry) -> None:
        """Replace every item, then re-apply the current highlight"""
        self.clear()
        self._elements.clear()
        self._bounds = geometry_bounds(geometry)
        if self._bounds is None:
            return
        self.addItem(GridItem(self._bounds))
        for slab in geometry.slabs:
            if slab.polygon_m is not None:  # a slab missing a pillar is not drawn
                self._add(SlabItem(slab, slab.polygon_m))
        for beam in geometry.beams:
            self._add(BeamItem(beam))
        lowest_y = min((p.y_m for p in geometry.pillars), default=0.0)
        for pillar in geometry.pillars:
            lowest = pillar.y_m - lowest_y <= _LOWEST_ROW_TOLERANCE_M
            self._add(PillarItem(pillar, lowest))
        for segment in dimension_segments(geometry.pillars):
            dimension = DimensionItem(segment)
            self.addItem(dimension)
            # fit the dimension lines too (their labels are added as a margin by the view)
            self._bounds = self._bounds.united(dimension.sceneBoundingRect())
        # a generous scene rect, so panning and fitting are never clamped
        rect = self.itemsBoundingRect()
        pad = max(rect.width(), rect.height()) * _PAN_ROOM
        self.setSceneRect(rect.adjusted(-pad, -pad, pad, pad))
        self._apply_highlight()

    def _add(self, item: SlabItem | BeamItem | PillarItem) -> None:
        self.addItem(item)
        self._elements[(item.kind, item.element_id)] = item

    def highlight(self, kind: ElementKind, element_id: str | None) -> None:
        """Highlight one element (None clears the highlight of that kind)"""
        if element_id is None:
            if self._highlighted is not None and self._highlighted[0] is kind:
                self._set(self._highlighted, False)
                self._highlighted = None
            return
        if self._highlighted is not None:
            self._set(self._highlighted, False)
        self._highlighted = (kind, element_id)
        self._apply_highlight()

    def _apply_highlight(self) -> None:
        if self._highlighted is not None:
            self._set(self._highlighted, True)

    def _set(self, key: tuple[ElementKind, str], on: bool) -> None:
        item = self._elements.get(key)
        if item is not None:
            item.set_highlighted(on)

    def element(self, kind: ElementKind, element_id: str) -> ElementItem | None:
        return self._elements.get((kind, element_id))
