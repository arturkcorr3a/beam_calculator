"""Flow of Ferramentas → Configurações… (F1)."""

from PySide6.QtWidgets import QDialog, QWidget

from pavement_ui.core.session import ProjectSession
from pavement_ui.presentation.dialogs.config.config_dialog import ConfigDialog


class ConfigController:
    """Runs actConfig: edit the settings in a modal dialog, apply them on OK"""

    def __init__(self, session: ProjectSession, window: QWidget) -> None:
        self._session = session
        self._window = window

    def edit(self) -> None:
        session = self._session
        dialog = ConfigDialog(
            session.config, session.log, session.options, self._window
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            session.update_config(*dialog.result_values())
