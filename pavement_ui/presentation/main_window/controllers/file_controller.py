"""Flows of the Arquivo menu (open and save are added with the file dialogs, stage 8)."""

from PySide6.QtWidgets import QWidget

from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.dialogs import messages


class FileController:
    """Runs actNew and actQuit"""

    def __init__(self, session: ProjectSession, window: QWidget) -> None:
        self._session = session
        self._window = window

    def new_project(self) -> None:
        """Discard the pavement and settings after confirmation"""
        if messages.confirm_new(self._window):
            self._session.new_project()

    def quit(self) -> None:
        self._window.close()
