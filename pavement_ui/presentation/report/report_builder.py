"""ReportBuilder: collect a report's HTML and figures into one QTextDocument."""

from collections.abc import Callable, Sequence

from PySide6.QtCore import QRectF, QUrl
from PySide6.QtGui import QColor, QImage, QPainter, QTextDocument

from pavement_ui.presentation.report import html
from pavement_ui.presentation.theme import tokens

type Paint = Callable[[QPainter, QRectF], None]

PX_PER_MM = 96 / 25.4  # layout pixels of the document
PRINT_DPI = 300  # figures of an exported PDF
SCREEN_DPI = 192  # figures on screen: twice the layout pixels, for high-DPI screens
TEXT_WIDTH_MM = 170.0  # A4 minus the margins
_STYLE = (
    f"body {{ font-family: '{tokens.UI_FONT_FAMILY}'; color: {tokens.TEXT}; }}"
    f"h1 {{ font-size: 16pt; color: {tokens.ACCENT}; }}"
    "h2 { font-size: 13pt; margin-top: 14px; }"
    "h3 { font-size: 11pt; margin-top: 10px; }"
    "td, th { font-size: 9pt; }"
)


def render_figure(paint: Paint, width_mm: float, height_mm: float, dpi: int) -> QImage:
    """Paint a figure on a white image at dpi

    The paint function works in layout pixels (96 per inch), so its sizes match
    the screen; the image just has more pixels per layout pixel.
    """
    width, height = width_mm * PX_PER_MM, height_mm * PX_PER_MM
    factor = dpi / 96
    image = QImage(
        round(width * factor), round(height * factor), QImage.Format.Format_RGB32
    )
    image.fill(QColor(tokens.SURFACE))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.scale(
        factor, factor
    )  # the image keeps 96 dpi, so fonts in points match the screen
    paint(painter, QRectF(0, 0, width, height))
    painter.end()
    return image


class ReportBuilder:
    """Append headings, texts, tables and figures, then build the document

    Args:
        dpi: Resolution of the figures: SCREEN_DPI to show, PRINT_DPI to export.
    """

    def __init__(self, dpi: int = SCREEN_DPI) -> None:
        self._dpi = dpi
        self._parts: list[str] = []
        self._images: dict[str, QImage] = {}

    def heading(self, text: str, level: int, page_break: bool = False) -> None:
        self._parts.append(html.heading(text, level, page_break))

    def paragraph(self, text: str, muted: bool = False) -> None:
        self._parts.append(html.paragraph(text, muted))

    def table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        left_columns: int = 1,
        bold_rows: Sequence[int] = (),
    ) -> None:
        self._parts.append(html.table(headers, rows, left_columns, bold_rows))

    def key_values(self, rows: Sequence[tuple[str, str]]) -> None:
        self._parts.append(html.key_values(rows))

    def figure(
        self,
        paint: Paint,
        height_mm: float,
        caption: str,
        width_mm: float = TEXT_WIDTH_MM,
    ) -> None:
        """Render a figure and place it, centered, with its caption"""
        name = f"figure:{len(self._images)}"
        self._images[name] = render_figure(paint, width_mm, height_mm, self._dpi)
        self._parts.append(
            html.figure(name, width_mm * PX_PER_MM, height_mm * PX_PER_MM, caption)
        )

    def figure_row(
        self, figures: Sequence[tuple[Paint, float]], height_mm: float, caption: str
    ) -> None:
        """Render figures of one height and place them side by side, with one caption

        Args:
            figures: Paint function and width (mm) of each figure, left to right.
        """
        images: list[tuple[str, float, float]] = []
        for paint, width_mm in figures:
            name = f"figure:{len(self._images)}"
            self._images[name] = render_figure(paint, width_mm, height_mm, self._dpi)
            images.append((name, width_mm * PX_PER_MM, height_mm * PX_PER_MM))
        self._parts.append(html.figure_row(images, caption))

    def document(self) -> QTextDocument:
        """Return the document, with every figure registered as an image resource"""
        document = QTextDocument()
        document.setDefaultStyleSheet(_STYLE)
        for name, image in self._images.items():
            document.addResource(
                QTextDocument.ResourceType.ImageResource.value, QUrl(name), image
            )
        document.setHtml("<body>" + "".join(self._parts) + "</body>")
        return document
