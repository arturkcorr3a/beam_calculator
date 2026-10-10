"""Composition root: creates the Qt application, applies locale and theme, and opens the main window."""

import sys

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication

from pavement_ui.presentation.main_window.main_window import MainWindow
from pavement_ui.presentation.text.strings.common import APP_NAME
from pavement_ui.presentation.theme.fonts import register_fonts, ui_font
from pavement_ui.presentation.theme.stylesheet import build_stylesheet

_STYLE = "Fusion"


def _configure_application(app: QApplication) -> None:
    """Apply the pt-BR locale, fonts, base style and stylesheet to the application."""
    QLocale.setDefault(QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil))
    app.setApplicationName(APP_NAME)
    app.setStyle(_STYLE)
    register_fonts()
    app.setFont(ui_font())
    app.setStyleSheet(build_stylesheet())


def main() -> int:
    """Start the application and run its event loop

    Returns:
        The exit code of the Qt event loop.
    """
    app = QApplication(sys.argv)
    _configure_application(app)
    window = MainWindow()
    window.show()
    return app.exec()
