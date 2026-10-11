"""Composition root: creates the Qt application, the engine adapters, the session
and the main window, and wires them together."""

import sys

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication

from pavement_ui.core.engine.pavement_gateway import PavementGateway
from pavement_ui.core.engine.project_store import YamlProjectStore
from pavement_ui.core.events import EventBus
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.execution.engine_executor import EngineExecutor
from pavement_ui.presentation.main_window.main_window import MainWindow
from pavement_ui.presentation.session_bridge import QtSessionBridge
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


def build_main_window() -> MainWindow:
    """Create the adapters, the session and the main window (needs a QApplication)"""
    bus = EventBus()
    session = ProjectSession(PavementGateway(), YamlProjectStore(), bus)
    bridge = QtSessionBridge(bus)
    executor = EngineExecutor()
    window = MainWindow(session, bridge, executor)
    bridge.setParent(window)
    executor.setParent(window)
    return window


def main() -> int:
    """Start the application and run its event loop

    Returns:
        The exit code of the Qt event loop.
    """
    app = QApplication(sys.argv)
    _configure_application(app)
    window = build_main_window()
    window.show()
    return app.exec()
