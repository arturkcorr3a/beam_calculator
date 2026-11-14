"""Memorial de cálculo: log level and output — never saved to the project file."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from pavement_ui.core.model.settings import LogValues
from pavement_ui.core.options import EngineOptions
from pavement_ui.presentation.dialogs.config.materials_section import LABEL_WIDTH_PX
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import dialogs as s
from pavement_ui.presentation.widgets.combo_helpers import (
    key_combo,
    select_key,
    selected_key,
)
from pavement_ui.presentation.widgets.form_section import FormSection


class LogSection(FormSection):
    def __init__(self, options: EngineOptions, parent: QWidget | None = None) -> None:
        super().__init__(s.CONFIG_LOG, LABEL_WIDTH_PX, parent)
        self._level = key_combo(
            "cfgLogLevel", options.log_levels, lambda k: label(OptionKind.LOG_LEVEL, k)
        )
        self._output = key_combo(
            "cfgLogOutput",
            options.log_outputs,
            lambda k: label(OptionKind.LOG_OUTPUT, k),
        )
        self.add_row(s.CONFIG_LOG_LEVEL, self._level)
        hint = self.add_row(
            s.CONFIG_LOG_OUTPUT,
            self._output,
            s.CONFIG_LOG_HINT.format(folder=options.log_dir),
        )
        if hint is not None:  # the folder can be copied to open it elsewhere
            hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    def load(self, log: LogValues) -> None:
        select_key(self._level, log.level_key)
        select_key(self._output, log.output_key)

    def values(self) -> LogValues:
        return LogValues(
            level_key=selected_key(self._level) or LogValues().level_key,
            output_key=selected_key(self._output) or LogValues().output_key,
        )
