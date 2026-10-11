"""The slab drawn to proportion, with each edge's support beam and condition."""

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from pavement_ui.core.results.slab_result import EdgeSupport, SlabResult
from pavement_ui.presentation.results.slab.slab_texts import condition
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.theme import tokens

_MARGIN_PX = 44.0
_SIDE_ROOM_PX = 120.0  # room for the left/right edge labels
_FIXED_PX = 4.0
_PINNED_PX = 1.5
_HATCH_STEP_PX = 8.0
_HATCH_PX = 7.0


def _hatch(painter: QPainter, line: QLineF, outward: QPointF) -> None:
    """Short diagonal strokes along a fixed edge, on its outer side."""
    steps = int(line.length() // _HATCH_STEP_PX)
    for i in range(steps + 1):
        start = line.pointAt(i / max(steps, 1))
        painter.drawLine(
            start, start + outward * _HATCH_PX + QPointF(_HATCH_PX / 2, -_HATCH_PX / 2)
        )


_LABEL_W, _LABEL_H, _LABEL_GAP = 150.0, 18.0, 10.0


def _label_box(line: QLineF, outward: QPointF) -> QRectF:
    """Text box fully outside the slab, centered on the edge."""
    center = line.center()
    if outward.x() < 0:  # left edge: text ends before the line
        return QRectF(
            center.x() - _LABEL_GAP - _LABEL_W,
            center.y() - _LABEL_H / 2,
            _LABEL_W,
            _LABEL_H,
        )
    if outward.x() > 0:  # right edge: text starts after the line
        return QRectF(
            center.x() + _LABEL_GAP, center.y() - _LABEL_H / 2, _LABEL_W, _LABEL_H
        )
    y = (
        center.y() - _LABEL_GAP - _LABEL_H
        if outward.y() < 0
        else center.y() + _LABEL_GAP
    )
    return QRectF(center.x() - _LABEL_W / 2, y, _LABEL_W, _LABEL_H)


def _label_align(outward: QPointF) -> Qt.AlignmentFlag:
    if outward.x() < 0:
        return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    if outward.x() > 0:
        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    return Qt.AlignmentFlag.AlignCenter


class SlabEdgesWidget(QWidget):
    """Edges in the order of the result (top, bottom, left, right)"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(260, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._result: SlabResult | None = None

    def set_result(self, result: SlabResult) -> None:
        self._result = result
        self.update()

    def _box(self, result: SlabResult) -> QRectF:
        room_w = self.width() - 2 * (_MARGIN_PX + _SIDE_ROOM_PX)
        room_h = self.height() - 2 * _MARGIN_PX
        scale = min(room_w / result.lx_cm, room_h / result.ly_cm)
        box = QRectF(0, 0, result.lx_cm * scale, result.ly_cm * scale)
        box.moveCenter(QRectF(self.rect()).center())
        return box

    def paintEvent(self, event: QPaintEvent) -> None:
        result = self._result
        if result is None:
            return
        box = self._box(result)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(box, QColor(tokens.PLAN_SLAB))
        sides = {
            "top": (QLineF(box.topLeft(), box.topRight()), QPointF(0, -1)),
            "bottom": (QLineF(box.bottomLeft(), box.bottomRight()), QPointF(0, 1)),
            "left": (QLineF(box.topLeft(), box.bottomLeft()), QPointF(-1, 0)),
            "right": (QLineF(box.topRight(), box.bottomRight()), QPointF(1, 0)),
        }
        for edge in result.edges:
            line, outward = sides[edge.edge_key]
            self._draw_edge(painter, edge, line, outward)
        painter.end()

    def _draw_edge(
        self, painter: QPainter, edge: EdgeSupport, line: QLineF, outward: QPointF
    ) -> None:
        pen = QPen(
            QColor(tokens.PLAN_BEAM_OUTLINE), _FIXED_PX if edge.fixed else _PINNED_PX
        )
        painter.setPen(pen)
        painter.drawLine(line)
        if edge.fixed:
            painter.setPen(QPen(QColor(tokens.PLAN_BEAM_OUTLINE), 1.0))
            _hatch(painter, line, outward)
        painter.setPen(QColor(tokens.TEXT))
        text = s.EDGE_LABEL.format(beam=edge.beam_id, condition=condition(edge).lower())
        painter.drawText(_label_box(line, outward), _label_align(outward), text)
