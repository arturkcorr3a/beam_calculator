"""Application fonts: IBM Plex when bundled, the system font otherwise."""

from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

from pavement_ui.presentation.theme import tokens

_FONTS_DIR = Path(__file__).parent / "resources" / "fonts"


def register_fonts() -> None:
    """Register every font file bundled in ``theme/resources/fonts``

    The IBM Plex files (OFL license) are optional; when absent, ``ui_font`` and
    ``mono_font`` fall back to the system fonts.
    """
    if not _FONTS_DIR.is_dir():
        return
    for path in sorted(_FONTS_DIR.glob("*.[ot]tf")):
        QFontDatabase.addApplicationFont(str(path))


def ui_font() -> QFont:
    """Return the interface font (IBM Plex Sans 10 pt, or the system font)"""
    if tokens.UI_FONT_FAMILY in QFontDatabase.families():
        return QFont(tokens.UI_FONT_FAMILY, tokens.UI_FONT_POINT_SIZE)
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    font.setPointSize(tokens.UI_FONT_POINT_SIZE)
    return font


def mono_font() -> QFont:
    """Return the font for numeric values (IBM Plex Mono, or the system fixed font)"""
    if tokens.MONO_FONT_FAMILY in QFontDatabase.families():
        return QFont(tokens.MONO_FONT_FAMILY, tokens.UI_FONT_POINT_SIZE)
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    font.setPointSize(tokens.UI_FONT_POINT_SIZE)
    return font
