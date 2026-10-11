"""Scheme of the simply supported beam: supports, distributed load, span."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPaintEvent, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.theme import tokens

_MARGIN_PX = 60.0
_BEAM_PX = 14.0
_SUPPORT_PX = 16.0
_ROLLER_PX = 4.0
_LOAD_PX = 36.0
_ARROWS = 11
_HEAD_PX = 5.0


def _triangle(apex: QPointF) -> QPolygonF:
    return QPolygonF(
        [
            apex,
            QPointF(apex.x() - _SUPPORT_PX / 1.4, apex.y() + _SUPPORT_PX),
            QPointF(apex.x() + _SUPPORT_PX / 1.4, apex.y() + _SUPPORT_PX),
        ]
    )


class BeamSchemeWidget(QWidget):
    """Fixed support at the left, roller at the right, uniform load g over L"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(170)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._length_m = 0.0
        self._load_kn_m = 0.0

    def set_values(self, length_m: float, load_kn_m: float) -> None:
        self._length_m, self._load_kn_m = length_m, load_kn_m
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        left, right = _MARGIN_PX, self.width() - _MARGIN_PX
        beam_top = self.height() / 2 - _BEAM_PX / 2
        beam = QRectF(left, beam_top, right - left, _BEAM_PX)
        painter.setPen(QPen(QColor(tokens.PLAN_BEAM_OUTLINE), 1.2))
        painter.setBrush(QBrush(QColor(tokens.PLAN_BEAM_FILL)))
        painter.drawRect(beam)
        self._draw_supports(painter, beam)
        self._draw_load(painter, beam)
        self._draw_length(painter, beam)
        painter.end()

    def _draw_supports(self, painter: QPainter, beam: QRectF) -> None:
        painter.setPen(QPen(QColor(tokens.TEXT), 1.2))
        painter.setBrush(QBrush(QColor(tokens.SURFACE)))
        left_apex, right_apex = (
            QPointF(beam.left(), beam.bottom()),
            QPointF(beam.right(), beam.bottom()),
        )
        painter.drawPolygon(_triangle(left_apex))
        ground = left_apex.y() + _SUPPORT_PX
        painter.drawLine(
            QPointF(beam.left() - 14, ground), QPointF(beam.left() + 14, ground)
        )
        painter.drawPolygon(_triangle(right_apex))
        for dx in (-6.0, 0.0, 6.0):  # rollers of the moving support
            painter.drawEllipse(
                QPointF(beam.right() + dx, ground + _ROLLER_PX), _ROLLER_PX, _ROLLER_PX
            )

    def _draw_load(self, painter: QPainter, beam: QRectF) -> None:
        color = QColor(tokens.DIAGRAM_SHEAR_LINE)
        painter.setPen(QPen(color, 1.2))
        painter.setBrush(QBrush(color))
        top = beam.top() - _LOAD_PX
        painter.drawLine(QPointF(beam.left(), top), QPointF(beam.right(), top))
        for i in range(_ARROWS):
            x = beam.left() + i * beam.width() / (_ARROWS - 1)
            tip = QPointF(x, beam.top() - 1)
            painter.drawLine(QPointF(x, top), tip)
            painter.drawPolygon(
                QPolygonF(
                    [
                        tip,
                        QPointF(x - _HEAD_PX / 2, tip.y() - _HEAD_PX),
                        QPointF(x + _HEAD_PX / 2, tip.y() - _HEAD_PX),
                    ]
                )
            )
        text = s.SCHEME_LOAD.format(value=fmt_number(self._load_kn_m, 2))
        painter.drawText(
            QRectF(beam.left(), top - 22, beam.width(), 18),
            Qt.AlignmentFlag.AlignHCenter,
            text,
        )

    def _draw_length(self, painter: QPainter, beam: QRectF) -> None:
        painter.setPen(QPen(QColor(tokens.TEXT_MUTED), 1.0))
        y = beam.bottom() + _SUPPORT_PX + 30
        painter.drawLine(QPointF(beam.left(), y), QPointF(beam.right(), y))
        for x in (beam.left(), beam.right()):
            painter.drawLine(QPointF(x, y - 5), QPointF(x, y + 5))
        text = s.SCHEME_LENGTH.format(value=fmt_number(self._length_m, 2))
        painter.drawText(
            QRectF(beam.left(), y + 4, beam.width(), 18),
            Qt.AlignmentFlag.AlignHCenter,
            text,
        )
