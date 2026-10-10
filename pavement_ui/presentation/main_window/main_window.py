"""Main window of the application (mockups A1–A3)."""

from PySide6.QtWidgets import QMainWindow, QWidget

from pavement_ui.presentation.text.strings.main_window import window_title

_INITIAL_SIZE_PX = (1280, 800)
_MINIMUM_SIZE_PX = (1024, 640)


class MainWindow(QMainWindow):
    """Top-level window: assembles the side panels, the plan and the status bar

    It only builds and connects components; flows live in the controllers and
    enabling rules in ``action_rules`` (docs/UI_SPEC.md §8).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("mainWindow")
        self.setWindowTitle(window_title(None))
        self.resize(*_INITIAL_SIZE_PX)
        self.setMinimumSize(*_MINIMUM_SIZE_PX)
