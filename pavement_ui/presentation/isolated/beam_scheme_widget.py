"""Scheme of the continuous beam: pillars, loads per span and span lengths."""

from collections.abc import Sequence
from itertools import accumulate

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPaintEvent, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.isolated.load_rows import LoadValues
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.theme import tokens

_MARGIN_PX = 40.0
_BEAM_PX = 14.0
_PILLAR_ABOVE_PX = 10.0
_PILLAR_BELOW_PX = 34.0
_MIN_PILLAR_PX = 6.0
_LOAD_MAX_PX = 40.0
_LOAD_MIN_PX = 10.0
_ARROW_GAP_PX = 24.0
_HEAD_PX = 5.0
_TEXT_PX = 20.0
_CM_PER_M = 100.0


class BeamSchemeWidget(QWidget):
    """The beam to scale over its pillars, each span's g and q and its length"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(250)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._lengths: tuple[float, ...] = ()
        self._pillar_widths_cm: tuple[float, ...] = ()
        self._loads: tuple[LoadValues, ...] = ()

    def set_values(
        self,
        span_lengths_m: Sequence[float],
        pillar_widths_cm: Sequence[float],
        span_loads: Sequence[LoadValues],
    ) -> None:
        """Show spans (m), pillar widths along the beam (cm) and the loads per span"""
        self._lengths = tuple(span_lengths_m)
        self._pillar_widths_cm = tuple(pillar_widths_cm)
        self._loads = tuple(span_loads)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        total = sum(self._lengths)
        if total <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = (self.width() - 2 * _MARGIN_PX) / total  # px per m
        axes = [_MARGIN_PX + x * scale for x in (0.0, *accumulate(self._lengths))]
        beam_top = self.height() / 2 - _BEAM_PX / 2 + 10
        halves = [
            max(w / _CM_PER_M * scale, _MIN_PILLAR_PX) / 2
            for w in self._pillar_widths_cm
        ]
        beam = QRectF(
            axes[0] - halves[0],
            beam_top,
            axes[-1] + halves[-1] - axes[0] + halves[0],
            _BEAM_PX,
        )
        self._draw_pillars(painter, axes, halves, beam)
        painter.setPen(QPen(QColor(tokens.PLAN_BEAM_OUTLINE), 1.2))
        painter.setBrush(QBrush(QColor(tokens.PLAN_BEAM_FILL)))
        painter.drawRect(beam)
        self._draw_loads(painter, axes, beam)
        self._draw_lengths(
            painter, axes, beam.bottom() + _PILLAR_BELOW_PX + _TEXT_PX + 12
        )
        painter.end()

    def _draw_pillars(
        self,
        painter: QPainter,
        axes: list[float],
        halves: list[float],
        beam: QRectF,
    ) -> None:
        painter.setPen(QPen(QColor(tokens.PLAN_PILLAR), 1.0))
        painter.setBrush(QBrush(QColor(tokens.PLAN_PILLAR)))
        top = beam.top() - _PILLAR_ABOVE_PX
        height = _PILLAR_ABOVE_PX + _BEAM_PX + _PILLAR_BELOW_PX
        for index, (x, half) in enumerate(zip(axes, halves, strict=False)):
            painter.drawRect(QRectF(x - half, top, 2 * half, height))
            painter.drawText(
                QRectF(x - 30, top + height + 2, 60, _TEXT_PX),
                Qt.AlignmentFlag.AlignHCenter,
                s.PILLAR_NAME.format(n=index + 1),
            )

    def _draw_loads(self, painter: QPainter, axes: list[float], beam: QRectF) -> None:
        peak = max((v.g_kn_m + v.q_kn_m for v in self._loads), default=0.0)
        color = QColor(tokens.DIAGRAM_SHEAR_LINE)
        metrics = painter.fontMetrics()
        for start, end, value in zip(axes, axes[1:], self._loads, strict=False):
            load = value.g_kn_m + value.q_kn_m
            if load <= 0 or peak <= 0:
                continue
            height = _LOAD_MIN_PX + (_LOAD_MAX_PX - _LOAD_MIN_PX) * load / peak
            top = beam.top() - _PILLAR_ABOVE_PX - height
            painter.setPen(QPen(color, 1.2))
            painter.setBrush(QBrush(color))
            painter.drawLine(QPointF(start, top), QPointF(end, top))
            arrows = max(2, int((end - start) / _ARROW_GAP_PX) + 1)
            for i in range(arrows):
                x = start + i * (end - start) / (arrows - 1)
                tip = QPointF(x, beam.top() - _PILLAR_ABOVE_PX - 1)
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
            text = s.SCHEME_LOAD.format(
                g=fmt_number(value.g_kn_m, 2), q=fmt_number(value.q_kn_m, 2)
            )
            width = end - start
            painter.drawText(
                QRectF(start, top - _TEXT_PX - 2, width, _TEXT_PX),
                Qt.AlignmentFlag.AlignHCenter,
                metrics.elidedText(text, Qt.TextElideMode.ElideRight, int(width)),
            )

    def _draw_lengths(self, painter: QPainter, axes: list[float], y: float) -> None:
        painter.setPen(QPen(QColor(tokens.TEXT_MUTED), 1.0))
        painter.drawLine(QPointF(axes[0], y), QPointF(axes[-1], y))
        for x in axes:
            painter.drawLine(QPointF(x, y - 5), QPointF(x, y + 5))
        for start, end, length in zip(axes, axes[1:], self._lengths, strict=False):
            painter.drawText(
                QRectF(start, y + 4, end - start, _TEXT_PX),
                Qt.AlignmentFlag.AlignHCenter,
                s.SCHEME_LENGTH.format(value=fmt_number(length, 2)),
            )
