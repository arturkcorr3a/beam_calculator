"""Composition root: creates the Qt application, the engine adapters, the session
and the main window, and wires them together."""

import sys

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication

from pavement_ui.core.engine.drawing_exporter import DxfDrawingExporter
from pavement_ui.core.engine.isolated_beam_engine import IsolatedBeamCalculator
from pavement_ui.core.engine.pavement_gateway import PavementGateway
from pavement_ui.core.engine.project_store import YamlProjectStore
from pavement_ui.core.events import EventBus
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.execution.engine_executor import EngineExecutor
from pavement_ui.presentation.main_window.main_window import MainWindow
from pavement_ui.presentation.session_bridge import QtSessionBridge
from pavement_ui.presentation.text.strings.common import APP_NAME
from pavement_ui.presentation.theme.fonts import register_fonts, ui_font
from pavement_ui.presentation.theme.logo import app_icon
from pavement_ui.presentation.theme.stylesheet import build_stylesheet

_STYLE = "Fusion"
# Name of packaging/linux/beam_calculator.desktop: on Wayland the shell finds
# the app's icon and name through it, never through the window icon
_DESKTOP_FILE = "beam_calculator"


def _configure_application(app: QApplication) -> None:
    """Apply the pt-BR locale, fonts, base style and stylesheet to the application."""
    QLocale.setDefault(QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil))
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(_DESKTOP_FILE)
    app.setStyle(_STYLE)
    app.setWindowIcon(app_icon())
    register_fonts()
    app.setFont(ui_font())
    app.setStyleSheet(build_stylesheet())


def build_main_window() -> MainWindow:
    """Create the adapters, the session and the main window (needs a QApplication)"""
    bus = EventBus()
    session = ProjectSession(PavementGateway(), YamlProjectStore(), bus)
    bridge = QtSessionBridge(bus)
    executor = EngineExecutor()
    window = MainWindow(
        session, bridge, executor, IsolatedBeamCalculator(), DxfDrawingExporter()
    )
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
    window.warm_up_engine()
    return app.exec()
