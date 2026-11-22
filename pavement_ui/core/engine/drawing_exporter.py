"""DxfDrawingExporter: write a core VectorDrawing with the engine's DXF writer."""

from dataclasses import replace
from pathlib import Path

from pavement_ui.core.results.vector_drawing import (
    PolylineShape,
    TextShape,
    VectorDrawing,
)
from src.drawing.config import DEFAULT_CONFIG
from src.drawing.primitives import (
    Circle,
    Drawing,
    DrawingItem,
    HAlign,
    Image,
    Line,
    Polyline,
    Text,
    VAlign,
)
from src.drawing.render_dxf import write_dxf
from src.errors import DxfAuditError


def _polyline(shape: PolylineShape) -> Polyline:
    """Rebuild a polyline with its arcs; flattened points if the originals are missing."""
    if shape.vertices:
        return Polyline(shape.vertices, shape.bulges, shape.layer, shape.closed)
    return Polyline(shape.points, (0.0,) * len(shape.points), shape.layer, shape.closed)


def _text(shape: TextShape) -> Text:
    return Text(
        shape.position,
        shape.text,
        shape.height,
        shape.layer,
        HAlign(shape.h_align.value),
        VAlign(shape.v_align.value),
        shape.rotation,
    )


def to_engine_drawing(drawing: VectorDrawing) -> Drawing:
    """Rebuild the engine's drawing: lines, polylines, circles, texts, then images"""
    items: list[DrawingItem] = [
        *(Line(line.start, line.end, line.layer) for line in drawing.lines),
        *(_polyline(shape) for shape in drawing.polylines),
        *(
            Circle(circle.center, circle.radius, circle.layer, circle.filled)
            for circle in drawing.circles
        ),
        *(_text(shape) for shape in drawing.texts),
    ]
    items.extend(
        Image(i.position, i.width, i.height, i.path, i.layer) for i in drawing.images
    )
    return Drawing(items, drawing.paper_mm)


class DxfDrawingExporter:
    """The DrawingExporter port, through src.drawing.render_dxf"""

    def write_dxf(self, drawing: VectorDrawing, path: Path) -> None:
        """Write the drawing to a DXF file at its own scale

        Raises:
            OSError: If the file cannot be written or the document fails the audit.
        """
        config = replace(DEFAULT_CONFIG, sheet_scale=drawing.scale)
        try:
            write_dxf(to_engine_drawing(drawing), path, config)
        except DxfAuditError as error:
            raise OSError(str(error)) from error
