"""Open, save and save as of the isolated beam calculator, with their buttons and shortcuts."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QPushButton, QWidget

from pavement_ui.core.errors import PersistenceError, PersistenceErrorKind
from pavement_ui.core.model.isolated_beam_input import IsolatedBeamInput
from pavement_ui.core.ports import IsolatedBeamStore
from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.dialogs import file_dialogs, messages
from pavement_ui.presentation.isolated.spans_pillars_group import MAX_SPANS
from pavement_ui.presentation.text.strings import isolated as s


class IsolatedFileController(QObject):
    """Mirrors the pavement's Arquivo flows for the isolated beam

    Opening a file also replaces the project settings with the file's ones,
    as opening a pavement does.

    Args:
        read_input: Returns the beam shown in the window.
        apply_input: Shows a beam read from a file.
        on_path_changed: Called with the file now open (e.g. for the title).
    """

    def __init__(
        self,
        window: QWidget,
        session: ProjectSession,
        store: IsolatedBeamStore,
        read_input: Callable[[], IsolatedBeamInput],
        apply_input: Callable[[IsolatedBeamInput], None],
        on_path_changed: Callable[[Path | None], None],
    ) -> None:
        super().__init__(window)
        self._window, self._session, self._store = window, session, store
        self._read_input, self._apply_input = read_input, apply_input
        self._on_path_changed = on_path_changed
        self._path: Path | None = None
        flows = (
            (s.OPEN, "isoOpenButton", QKeySequence.StandardKey.Open, self.open),
            (s.SAVE, "isoSaveButton", QKeySequence.StandardKey.Save, self.save),
            (
                s.SAVE_AS,
                "isoSaveAsButton",
                QKeySequence.StandardKey.SaveAs,
                self.save_as,
            ),
        )
        self.buttons: tuple[QPushButton, ...] = ()
        self._shortcuts: list[QShortcut] = []
        for text, name, key, flow in flows:
            button = QPushButton(text)
            button.setObjectName(name)
            button.clicked.connect(flow)
            self.buttons += (button,)
            self._shortcuts.append(QShortcut(QKeySequence(key), window, flow))

    def set_enabled(self, enabled: bool) -> None:
        """Waits while a job runs, like the pavement's Abrir and Salvar"""
        for button in self.buttons:
            button.setEnabled(enabled)
        for shortcut in self._shortcuts:
            shortcut.setEnabled(enabled)

    def open(self) -> None:
        path = file_dialogs.ask_beam_open_path(self._window)
        if path is None:
            return
        try:
            loaded = self._store.open(path)
            count = len(loaded.data.span_lengths_m)
            if count > MAX_SPANS:
                raise PersistenceError(
                    PersistenceErrorKind.INVALID_CONTENT,
                    s.TOO_MANY_SPANS.format(count=count, maximum=MAX_SPANS),
                )
        except PersistenceError as error:
            messages.show_file_error(self._window, error, opening=True)
            return
        self._session.update_config(loaded.config, self._session.log)
        self._apply_input(loaded.data)
        self._set_path(path)

    def save(self) -> None:
        """Save to the open file, or ask for one"""
        if self._path is None:
            self.save_as()
        else:
            self._save_to(self._path)

    def save_as(self) -> None:
        path = file_dialogs.ask_beam_save_path(self._window, self._path)
        if path is not None:
            self._save_to(path)

    def _save_to(self, path: Path) -> None:
        try:
            self._store.save(path, self._read_input(), self._session.config)
        except PersistenceError as error:
            messages.show_file_error(self._window, error, opening=False)
            return
        self._set_path(path)

    def _set_path(self, path: Path) -> None:
        self._path = path
        self._on_path_changed(path)
