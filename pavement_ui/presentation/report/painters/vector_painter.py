"""Paint an engine VectorDrawing into a rectangle, fitted and centered."""

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPen,
    QPolygonF,
)

from pavement_ui.core.results.vector_drawing import (
    HAlign,
    LayerLook,
    TextShape,
    VAlign,
    VectorDrawing,
)
from pavement_ui.presentation.theme import tokens

_MARGIN_PX = 6.0
_PEN_BASE_PX = 0.5
_PEN_PX_PER_MM = 2.5  # plotted weight (mm) to screen pen width
_FONT_PX = 100.0  # texts are laid out at this size, then scaled
_CAP_RATIO = 0.7  # cap height over font pixel size
_FALLBACK = LayerLook("", tokens.TEXT, 0.18, False)


@dataclass(frozen=True, slots=True)
class _Frame:
    """Model (cm, y up) to painter (px, y down) mapping"""

    scale: float
    origin_x: float
    origin_y: float

    def point(self, p: tuple[float, float]) -> QPointF:
        return QPointF(
            self.origin_x + p[0] * self.scale, self.origin_y - p[1] * self.scale
        )


def _frame(drawing: VectorDrawing, rect: QRectF, margin: float) -> _Frame:
    x0, y0, x1, y1 = drawing.bounds
    width, height = max(x1 - x0, 1e-9), max(y1 - y0, 1e-9)
    scale = min(
        (rect.width() - 2 * margin) / width,
        (rect.height() - 2 * margin) / height,
    )
    return _Frame(
        scale,
        rect.left() + (rect.width() - width * scale) / 2 - x0 * scale,
        rect.top() + (rect.height() + height * scale) / 2 + y0 * scale,
    )


@dataclass(frozen=True, slots=True)
class _PenStyle:
    """How layer weights become pens

    Attributes:
        cosmetic: Whether pens keep their width when the painter zooms.
        px_per_mm: Painter units per plotted mm, for the real line weights;
            None for the screen widths of the report figures.
    """

    cosmetic: bool
    px_per_mm: float | None


def _pen(look: LayerLook, style: _PenStyle) -> QPen:
    width = (
        _PEN_BASE_PX + look.width_mm * _PEN_PX_PER_MM
        if style.px_per_mm is None
        else look.width_mm * style.px_per_mm
    )
    pen = QPen(QColor(look.color), width)
    pen.setCosmetic(style.cosmetic)
    if look.dashed:
        pen.setStyle(Qt.PenStyle.DashLine)
    return pen


def _paint_text(painter: QPainter, text: TextShape, frame: _Frame, color: str) -> None:
    """Paint a text with its cap height, rotation and anchor"""
    font = QFont(tokens.UI_FONT_FAMILY)
    font.setPixelSize(int(_FONT_PX))
    metrics = QFontMetricsF(font)
    cap = _FONT_PX * _CAP_RATIO
    width = metrics.horizontalAdvance(text.text)
    dx = {HAlign.LEFT: 0.0, HAlign.CENTER: -width / 2, HAlign.RIGHT: -width}[
        text.h_align
    ]
    dy = {VAlign.BASELINE: 0.0, VAlign.MIDDLE: cap / 2, VAlign.TOP: cap}[text.v_align]
    factor = text.height * frame.scale / cap
    painter.save()
    painter.translate(frame.point(text.position))
    painter.rotate(-text.rotation)
    painter.scale(factor, factor)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(QPointF(dx, dy), text.text)
    painter.restore()


def paint_vector(
    painter: QPainter,
    drawing: VectorDrawing,
    rect: QRectF,
    *,
    margin: float = _MARGIN_PX,
    cosmetic: bool = False,
    px_per_mm: float | None = None,
) -> None:
    """Paint the drawing as large as fits in rect, keeping its proportions

    Args:
        margin: Room left on every side of rect (painter units).
        cosmetic: Whether lines keep their width when the view zooms.
        px_per_mm: Painter units per plotted mm, to draw the layers' real line
            weights; None keeps the fixed screen widths of the report figures.
    """
    frame = _frame(drawing, rect, margin)
    style = _PenStyle(cosmetic, px_per_mm)
    looks = {look.name: look for look in drawing.layers}
    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for line in drawing.lines:
        painter.setPen(_pen(looks.get(line.layer, _FALLBACK), style))
        painter.drawLine(frame.point(line.start), frame.point(line.end))
    for polyline in drawing.polylines:
        painter.setPen(_pen(looks.get(polyline.layer, _FALLBACK), style))
        polygon = QPolygonF([frame.point(p) for p in polyline.points])
        if polyline.closed:
            painter.drawPolygon(polygon)
        else:
            painter.drawPolyline(polygon)
    for circle in drawing.circles:
        look = looks.get(circle.layer, _FALLBACK)
        painter.setPen(_pen(look, style))
        painter.setBrush(
            QBrush(QColor(look.color)) if circle.filled else Qt.BrushStyle.NoBrush
        )
        radius = circle.radius * frame.scale
        painter.drawEllipse(frame.point(circle.center), radius, radius)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for text in drawing.texts:
        _paint_text(painter, text, frame, looks.get(text.layer, _FALLBACK).color)
    painter.restore()


def vector_figure(drawing: VectorDrawing) -> Callable[[QPainter, QRectF], None]:
    """Return a paint function that draws the drawing into the given rectangle"""

    def paint(painter: QPainter, rect: QRectF) -> None:
        paint_vector(painter, drawing, rect)

    return paint
