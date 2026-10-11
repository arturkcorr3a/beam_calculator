"""A beam: its real band when the engine resolved it, otherwise a dashed line."""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QPainterPath
from PySide6.QtWidgets import QGraphicsPathItem

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.results.plan_geometry import BeamShape
from pavement_ui.presentation.plan.items.element_item import ElementItem, cosmetic_pen
from pavement_ui.presentation.plan.items.label_item import LabelItem
from pavement_ui.presentation.plan.scene_units import point, rect_from_corners_m
from pavement_ui.presentation.theme import tokens

_Z = 20
_LABEL_PT = 9
_LABEL_OFFSET_PX = 8.0
_FALLBACK_WIDTH_PX = 1.5
_Align = Qt.AlignmentFlag


def _path(shape: BeamShape) -> QPainterPath:
    path = QPainterPath()
    if shape.rect_m is not None:
        path.addRect(rect_from_corners_m(*shape.rect_m))
    elif shape.fallback_line_m:
        first, *rest = (point(x, y) for x, y in shape.fallback_line_m)
        path.moveTo(first)
        for p in rest:
            path.lineTo(p)
    return path


class BeamItem(ElementItem, QGraphicsPathItem):
    """Band of width bw positioned by the engine's alignment; the ID beside its middle"""

    def __init__(self, shape: BeamShape) -> None:
        QGraphicsPathItem.__init__(self, _path(shape))
        self.kind, self.element_id = ElementKind.BEAM, shape.id
        self._resolved = shape.rect_m is not None
        self.setZValue(_Z)
        if (
            shape.label_m is not None
        ):  # None: fewer than 2 existing pillars, nothing drawn
            self.labels = (self._label(shape, point(*shape.label_m)),)
        self._apply_highlight(False)

    def _label(self, shape: BeamShape, middle: QPointF) -> LabelItem:
        """The ID beside the middle of the longest span."""
        bounds = self.path().boundingRect()
        if shape.axis_key == "Y":  # to the right of a vertical beam
            anchor = _Align.AlignLeft | _Align.AlignVCenter
            offset = (_LABEL_OFFSET_PX, 0.0)
            at = QPointF(bounds.right(), middle.y())
        else:  # above a horizontal (or unresolved) beam; Y is up in the scene
            anchor = _Align.AlignHCenter | _Align.AlignBottom
            offset = (0.0, -_LABEL_OFFSET_PX)
            at = QPointF(middle.x(), bounds.bottom() if shape.rect_m else middle.y())
        label = LabelItem(shape.id, _LABEL_PT, True, anchor, offset, self)
        label.setPos(at)
        return label

    def _apply_highlight(self, highlighted: bool) -> None:
        if self._resolved:
            outline = tokens.ACCENT if highlighted else tokens.PLAN_BEAM_OUTLINE
            fill = tokens.ACCENT if highlighted else tokens.PLAN_BEAM_FILL
            self.setPen(cosmetic_pen(outline))
            self.setBrush(QBrush(QColor(fill)))
            return
        pen = cosmetic_pen(
            tokens.ACCENT if highlighted else tokens.PLAN_BEAM_OUTLINE,
            _FALLBACK_WIDTH_PX,
        )
        pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setBrush(Qt.BrushStyle.NoBrush)
