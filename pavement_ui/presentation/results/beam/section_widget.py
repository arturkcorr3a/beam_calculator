"""Draw the dimensioned cross-section of a design point."""

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from pavement_ui.core.results.reinforcement import StirrupSpec
from pavement_ui.presentation.formatting.numbers import fmt_length_cm, fmt_number
from pavement_ui.presentation.formatting.reinforcement import fmt_bar_layer, fmt_stirrup
from pavement_ui.presentation.results.beam.section_layout import Rect, SectionLayout
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.theme import tokens

_MARGIN_LEFT, _MARGIN_RIGHT, _MARGIN_BOTTOM, _MARGIN_TOP = 60.0, 170.0, 40.0, 16.0
_MIN_STIRRUP_PX = 2.0
_CALLOUT_GAP_PX = 18.0
_CALLOUT_SPACING_PX = 18.0


@dataclass(frozen=True, slots=True)
class _Mapper:
    """Section cm (y up) → widget pixels (y down)."""

    origin: QPointF  # screen point of the section's bottom-left corner
    scale: float  # pixels per cm

    def point(self, x: float, y: float) -> QPointF:
        return QPointF(
            self.origin.x() + x * self.scale, self.origin.y() - y * self.scale
        )

    def rect(self, r: Rect) -> QRectF:
        return QRectF(self.point(r.x0, r.y1), self.point(r.x1, r.y0))


def _spread(wanted: list[float], spacing: float) -> list[float]:
    """Move callout heights apart (keeping their order) so labels never overlap."""
    order = sorted(range(len(wanted)), key=wanted.__getitem__)
    placed = list(wanted)
    for previous, current in zip(order, order[1:], strict=False):
        placed[current] = max(placed[current], placed[previous] + spacing)
    return placed


class SectionWidget(QWidget):
    """Concrete, stirrup and bars in scale; dimensions and callouts around them"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._layout: SectionLayout | None = None
        self._stirrup: StirrupSpec | None = None
        self._cover_cm = 0.0

    def set_section(
        self, layout: SectionLayout, stirrup: StirrupSpec, cover_cm: float
    ) -> None:
        self._layout, self._stirrup, self._cover_cm = layout, stirrup, cover_cm
        self.update()

    def clear(self) -> None:
        self._layout = None
        self.update()

    def _mapper(self, concrete: Rect) -> _Mapper:
        room_w = self.width() - _MARGIN_LEFT - _MARGIN_RIGHT
        room_h = self.height() - _MARGIN_TOP - _MARGIN_BOTTOM
        scale = min(room_w / concrete.x1, room_h / concrete.y1)
        return _Mapper(QPointF(_MARGIN_LEFT, _MARGIN_TOP + concrete.y1 * scale), scale)

    def paintEvent(self, event: QPaintEvent) -> None:
        if self._layout is None or self._stirrup is None:
            return
        layout, stirrup = self._layout, self._stirrup
        mapper = self._mapper(layout.concrete)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(tokens.PLAN_BEAM_OUTLINE), 1.2))
        painter.setBrush(QBrush(QColor(tokens.CONCRETE)))
        painter.drawRect(mapper.rect(layout.concrete))
        stirrup_px = max(layout.stirrup_diameter * mapper.scale, _MIN_STIRRUP_PX)
        painter.setPen(QPen(QColor(tokens.STIRRUP), stirrup_px))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        corner = 2.0 * layout.stirrup_diameter * mapper.scale
        painter.drawRoundedRect(mapper.rect(layout.stirrup), corner, corner)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(tokens.BAR)))
        for _, bars in layout.layers:
            for bar in bars:
                radius = bar.diameter * mapper.scale / 2
                painter.drawEllipse(mapper.point(bar.x, bar.y), radius, radius)
        self._draw_dimensions(painter, layout, mapper)
        self._draw_callouts(painter, layout, stirrup, mapper)
        painter.end()

    def _draw_dimensions(
        self, painter: QPainter, layout: SectionLayout, mapper: _Mapper
    ) -> None:
        box = mapper.rect(layout.concrete)
        painter.setPen(QColor(tokens.TEXT))
        width_text = s.SECTION_B.format(value=fmt_length_cm(layout.concrete.x1))
        painter.drawText(
            QRectF(box.left(), box.bottom() + 6, box.width(), 20),
            Qt.AlignmentFlag.AlignHCenter,
            width_text,
        )
        painter.save()
        painter.translate(box.left() - 14, box.center().y())
        painter.rotate(-90)
        height_text = s.SECTION_H.format(value=fmt_length_cm(layout.concrete.y1))
        painter.drawText(
            QRectF(-80, -14, 160, 20), Qt.AlignmentFlag.AlignHCenter, height_text
        )
        painter.restore()

    def _draw_callouts(
        self,
        painter: QPainter,
        layout: SectionLayout,
        stirrup: StirrupSpec,
        mapper: _Mapper,
    ) -> None:
        box = mapper.rect(layout.concrete)
        anchors = [
            mapper.point(0, layer.y_cm).y() for layer, bars in layout.layers if bars
        ]
        texts = [fmt_bar_layer(layer) for layer, bars in layout.layers if bars]
        anchors += [box.center().y(), box.top() + 10]
        texts += [
            fmt_stirrup(stirrup, prefixed=True),
            s.SECTION_COVER.format(value=fmt_number(self._cover_cm, 1)),
        ]
        x_text = box.right() + _CALLOUT_GAP_PX
        painter.setPen(QColor(tokens.TEXT_MUTED))
        for anchor, y, text in zip(
            anchors, _spread(anchors, _CALLOUT_SPACING_PX), texts, strict=True
        ):
            painter.drawLine(QPointF(box.right(), anchor), QPointF(x_text - 4, y))
            painter.drawText(QPointF(x_text, y + 4), text)
