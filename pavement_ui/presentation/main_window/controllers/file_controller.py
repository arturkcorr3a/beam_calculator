"""Flows of the Arquivo menu: new, open, save, save as and quit (F10)."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import QWidget

from pavement_ui.core.errors import PersistenceError
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.dialogs import file_dialogs, messages


class FileController:
    """Runs actNew, actOpen, actSave, actSaveAs and actQuit

    Args:
        on_opened: Called after a project is opened or started (e.g. to fit the plan).
    """

    def __init__(
        self,
        session: ProjectSession,
        window: QWidget,
        on_opened: Callable[[], None],
    ) -> None:
        self._session = session
        self._window = window
        self._on_opened = on_opened

    def new_project(self) -> None:
        """Discard the pavement and settings after confirmation"""
        if messages.confirm_new(self._window):
            self._session.new_project()
            self._on_opened()

    def open(self) -> None:
        """Replace the project with a file [Manual §8]; no unsaved-changes check (M21)"""
        path = file_dialogs.ask_open_path(self._window)
        if path is None:
            return
        try:
            self._session.open(path)
        except PersistenceError as error:
            messages.show_file_error(self._window, error, opening=True)
            return
        self._on_opened()

    def save(self) -> None:
        """Save to the current file, or ask for one"""
        if self._session.current_path is None:
            self.save_as()
        else:
            self._save_to(self._session.current_path)

    def save_as(self) -> None:
        path = file_dialogs.ask_save_path(self._window, self._session.current_path)
        if path is not None:
            self._save_to(path)

    def _save_to(self, path: Path) -> None:
        """Save, asking first when the engine considers the structure invalid"""
        error = self._session.check_before_save()
        if error is not None and not messages.confirm_save_invalid(self._window, error):
            return
        try:
            self._session.save(path)
        except PersistenceError as failure:
            messages.show_file_error(self._window, failure, opening=False)

    def quit(self) -> None:
        self._window.close()
