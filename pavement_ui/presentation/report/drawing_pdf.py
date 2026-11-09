"""Print a drawing to a PDF at its true scale, on a page the size of the drawing."""

from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, QSizeF
from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter

from pavement_ui.core.results.vector_drawing import VectorDrawing
from pavement_ui.presentation.report.painters.vector_painter import paint_vector
from pavement_ui.presentation.report.report_builder import PX_PER_MM

_DPI = 300
_MARGIN_MM = 10.0
_MM_PER_CM = 10.0


def drawing_page_mm(drawing: VectorDrawing) -> tuple[float, float]:
    """Return the page size (mm): the drawing at 1:scale plus the margins"""
    x0, y0, x1, y1 = drawing.bounds
    paper_per_model = _MM_PER_CM / drawing.scale  # paper mm per model cm
    return (
        (x1 - x0) * paper_per_model + 2 * _MARGIN_MM,
        (y1 - y0) * paper_per_model + 2 * _MARGIN_MM,
    )


def export_drawing_pdf(drawing: VectorDrawing, path: Path, title: str) -> None:
    """Write the drawing to a one-page PDF at 1:scale, with the plotted line weights

    Raises:
        OSError: If the file cannot be written.
    """
    width_mm, height_mm = drawing_page_mm(drawing)
    writer = QPdfWriter(str(path))
    writer.setResolution(_DPI)
    writer.setTitle(title)
    writer.setPageLayout(
        QPageLayout(
            QPageSize(QSizeF(width_mm, height_mm), QPageSize.Unit.Millimeter),
            QPageLayout.Orientation.Portrait,
            QMarginsF(0, 0, 0, 0),
            QPageLayout.Unit.Millimeter,
        )
    )
    painter = QPainter()
    if not painter.begin(writer):
        raise OSError(str(path))
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(_DPI / 96, _DPI / 96)  # layout pixels, as the reports
        paint_vector(
            painter,
            drawing,
            QRectF(0, 0, width_mm * PX_PER_MM, height_mm * PX_PER_MM),
            margin=_MARGIN_MM * PX_PER_MM,
            px_per_mm=PX_PER_MM,
        )
    finally:
        painter.end()
