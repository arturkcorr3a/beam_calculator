"""Print a report document to an A4 PDF, page by page, with page numbers."""

from pathlib import Path

from PySide6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QTextDocument,
)

from pavement_ui.presentation.report.report_builder import PX_PER_MM
from pavement_ui.presentation.theme import tokens

_DPI = 300
_MARGIN_MM = 15.0
_FOOTER_MM = 8.0  # room under the text for the page number
_A4_MM = (210.0, 297.0)
_FOOTER_FONT_PX = 11


def export_pdf(document: QTextDocument, path: Path, title: str) -> None:
    """Write the document to an A4 PDF at path

    The document is laid out in layout pixels (96 per inch), as on screen, on a
    copy whose page size is the A4 text area; each page is then painted scaled
    to the writer's resolution, with its number centered in the footer.

    Raises:
        OSError: If the file cannot be written.
    """
    writer = QPdfWriter(str(path))
    writer.setResolution(_DPI)
    writer.setTitle(title)
    writer.setPageLayout(
        QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(0, 0, 0, 0),
            QPageLayout.Unit.Millimeter,
        )
    )
    copy = document.clone()
    width_px = (_A4_MM[0] - 2 * _MARGIN_MM) * PX_PER_MM
    height_px = (_A4_MM[1] - 2 * _MARGIN_MM - _FOOTER_MM) * PX_PER_MM
    copy.setPageSize(QSizeF(width_px, height_px))
    pages = copy.pageCount()
    scale = _DPI / 96
    footer_font = QFont(tokens.UI_FONT_FAMILY)
    footer_font.setPixelSize(_FOOTER_FONT_PX)  # layout pixels, under the scale
    painter = QPainter()
    if not painter.begin(writer):
        raise OSError(str(path))
    try:
        for index in range(pages):
            if index:
                writer.newPage()
            painter.save()
            painter.scale(scale, scale)
            painter.translate(_MARGIN_MM * PX_PER_MM, _MARGIN_MM * PX_PER_MM)
            painter.save()
            painter.translate(0, -index * height_px)
            copy.drawContents(
                painter, QRectF(0, index * height_px, width_px, height_px)
            )
            painter.restore()
            painter.setPen(QColor(tokens.TEXT_MUTED))
            painter.setFont(footer_font)
            footer = QRectF(
                QPointF(0, height_px), QSizeF(width_px, _FOOTER_MM * PX_PER_MM)
            )
            painter.drawText(
                footer, Qt.AlignmentFlag.AlignCenter, f"{index + 1} / {pages}"
            )
            painter.restore()
    finally:
        painter.end()
