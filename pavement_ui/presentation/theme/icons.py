"""Stroke icons (24 × 24 SVG) rendered to ``QIcon`` in the theme colors."""

from functools import cache
from typing import Literal

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from pavement_ui.presentation.theme import tokens

type IconName = Literal[
    "new",
    "open",
    "save",
    "settings",
    "validate",
    "design",
    "results",
    "trash",
    "isolated_beam",
    "zoom_in",
    "zoom_out",
    "fit",
    "ok",
    "error",
    "warning",
    "question",
    "close",
]

# Inner SVG markup of each icon; strokes use the color passed to icon().
_SHAPES: dict[IconName, str] = {
    "new": '<path d="M14 3H6v18h12V7z"/><path d="M14 3v4h4"/><path d="M12 11v6M9 14h6"/>',
    "open": '<path d="M3 7V5h7l2 2h9v12H3z"/><path d="M3 10h18"/>',
    "save": '<path d="M5 3h11l3 3v15H5z"/><path d="M8 3v5h8V3"/><path d="M8 21v-7h8v7"/>',
    "settings": '<circle cx="12" cy="12" r="3"/>'
    '<path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1'
    'M4.9 19.1L7 17M17 7l2.1-2.1"/>',
    "validate": '<path d="M9 3h6v3H9z"/><path d="M7 4H5v17h14V4h-2"/><path d="M8 13l3 3 5-6"/>',
    "design": '<path d="M3 18h18"/><path d="M5 18V9h14v9"/><path d="M8 9V6h8v3"/>'
    '<path d="M9 13h6"/>',
    "results": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "trash": '<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 14h10l1-14"/>'
    '<path d="M10 11v6M14 11v6"/>',
    "isolated_beam": '<path d="M3 9h18v4H3z"/><path d="M5 13l-2 4h4z"/>'
    '<path d="M19 13l-2 4h4z"/><path d="M8 5v3M12 5v3M16 5v3"/>',
    "zoom_in": '<circle cx="10" cy="10" r="6"/><path d="M14.5 14.5L20 20"/>'
    '<path d="M10 7v6M7 10h6"/>',
    "zoom_out": '<circle cx="10" cy="10" r="6"/><path d="M14.5 14.5L20 20"/>'
    '<path d="M7 10h6"/>',
    "fit": '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
    "ok": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    "error": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "warning": '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/>',
    "question": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3'
    'c-.6.3-1 .8-1 1.5V14M12 17v.5"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
}

_PIXMAP_SIZES_PX = (16, 24, 32, 48)


def _svg(name: IconName, color: str) -> bytes:
    """Wrap an icon's shapes in a complete SVG document stroked with color."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round">{_SHAPES[name]}</svg>'
    ).encode()


@cache
def icon(name: IconName, color: str = tokens.TEXT) -> QIcon:
    """Render a theme icon at the usual toolbar and menu sizes

    Args:
        name: Icon identifier.
        color: Stroke color (hex), usually a token.

    Returns:
        The icon, cached per name and color.
    """
    renderer = QSvgRenderer(QByteArray(_svg(name, color)))
    result = QIcon()
    for size in _PIXMAP_SIZES_PX:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        result.addPixmap(pixmap)
    return result
