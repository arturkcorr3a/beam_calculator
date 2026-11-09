"""Convert an engine drawing (src.drawing) into the core's VectorDrawing."""

from dataclasses import replace

from pavement_ui.core.results.vector_drawing import (
    CircleShape,
    HAlign,
    LayerLook,
    LineShape,
    PolylineShape,
    TextShape,
    VAlign,
    VectorDrawing,
)
from src.drawing.config import DEFAULT_CONFIG, DrawingConfig
from src.drawing.layers import CONTINUOUS, layer_style
from src.drawing.primitives import Circle, Drawing, Line, Polyline, Text

_SCALES = (50, 75, 100, 125, 150, 200, 250, 300, 400, 500)
_ROOM = 1.3  # extra room for the dimensions and names around the geometry


def report_config(
    width_cm: float, height_cm: float, width_mm: float, height_mm: float
) -> DrawingConfig:
    """Return the drawing settings of a report figure, at the scale it is printed

    Texts and annotation offsets are set in paper mm at the sheet scale, so
    drawing at the scale the figure is printed at keeps them at their paper size.

    Args:
        width_cm: Width of the drawn geometry (cm).
        height_cm: Height of the drawn geometry (cm).
        width_mm: Width of the figure in the report (mm).
        height_mm: Height of the figure in the report (mm).
    """
    needed = _ROOM * max(width_cm * 10 / width_mm, height_cm * 10 / height_mm)
    scale = next((s for s in _SCALES if s >= needed), _SCALES[-1])
    return replace(DEFAULT_CONFIG, sheet_scale=scale)


def _look(name: str) -> LayerLook:
    style = layer_style(name)
    return LayerLook(
        name, style.screen_color, style.lineweight_mm, style.linetype != CONTINUOUS
    )


def _text(item: Text) -> TextShape:
    return TextShape(
        item.position,
        item.text,
        item.height,
        item.layer,
        HAlign(item.halign.value),
        VAlign(item.valign.value),
        item.rotation,
    )


def read_drawing(
    drawing: Drawing, scale: float = DEFAULT_CONFIG.sheet_scale
) -> VectorDrawing:
    """Return the drawing's items by kind, arcs flattened, with their layers' looks

    Args:
        scale: Sheet scale the drawing was built with (its config's sheet_scale).

    Raises:
        ValueError: If the drawing is empty (it has no bounds).
    """
    lines: list[LineShape] = []
    polylines: list[PolylineShape] = []
    circles: list[CircleShape] = []
    texts: list[TextShape] = []
    for item in drawing.items:
        match item:
            case Line():
                lines.append(LineShape(item.start, item.end, item.layer))
            case Polyline():
                points = item.flattened(DEFAULT_CONFIG.arc_segments)
                polylines.append(
                    PolylineShape(
                        tuple(points),
                        item.closed,
                        item.layer,
                        item.points,
                        item.bulges,
                    )
                )
            case Circle():
                circles.append(
                    CircleShape(item.center, item.radius, item.filled, item.layer)
                )
            case Text():
                texts.append(_text(item))
    return VectorDrawing(
        lines=tuple(lines),
        polylines=tuple(polylines),
        circles=tuple(circles),
        texts=tuple(texts),
        layers=tuple(_look(name) for name in drawing.layers()),
        bounds=drawing.bounds(),
        scale=scale,
    )
