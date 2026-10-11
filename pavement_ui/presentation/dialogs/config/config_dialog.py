"""ConfigDialog: the general project settings (mockup A4, docs/UI_SPEC.md §9.1)."""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pavement_ui.core.model.settings import ConfigValues, LogValues
from pavement_ui.core.options import EngineOptions
from pavement_ui.presentation.dialogs.config.building_section import BuildingSection
from pavement_ui.presentation.dialogs.config.detailing_section import DetailingSection
from pavement_ui.presentation.dialogs.config.log_section import LogSection
from pavement_ui.presentation.dialogs.config.materials_section import MaterialsSection
from pavement_ui.presentation.text.strings import dialogs as s
from pavement_ui.presentation.widgets.variants import set_variant

_SIZE_PX = (640, 720)

_Button = QDialogButtonBox.StandardButton
_Role = QDialogButtonBox.ButtonRole


class ConfigDialog(QDialog):
    """Edit settings without applying them; the caller reads ``result_values`` on OK

    The field ranges keep every value valid; the engine checks the combination
    (e.g. concrete below the aggressiveness-class minimum) when validating.
    """

    def __init__(
        self,
        config: ConfigValues,
        log: LogValues,
        options: EngineOptions,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("configDialog")
        self.setWindowTitle(s.CONFIG_TITLE)
        self.setModal(True)
        self.resize(*_SIZE_PX)
        self._config = config
        self._materials = MaterialsSection(options)
        self._detailing = DetailingSection()
        self._building = BuildingSection(options)
        self._log = LogSection(options)
        layout = QVBoxLayout(self)
        for section in (self._materials, self._detailing, self._building, self._log):
            layout.addWidget(section)
        layout.addStretch(1)
        layout.addWidget(self._buttons())
        self._load(config, log)

    def _buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(_Button.Ok | _Button.Cancel)
        ok = buttons.button(_Button.Ok)
        ok.setText(s.CONFIG_OK)
        ok.setDefault(True)
        set_variant(ok, "primary")
        buttons.button(_Button.Cancel).setText(s.CANCEL)
        restore = QPushButton(s.CONFIG_RESTORE)
        restore.setObjectName("cfgRestoreDefaults")
        buttons.addButton(restore, _Role.ResetRole)
        restore.clicked.connect(lambda: self._load(ConfigValues(), LogValues()))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        return buttons

    def _load(self, config: ConfigValues, log: LogValues) -> None:
        self._materials.load(config)
        self._detailing.load(config)
        self._building.load(config)
        self._log.load(log)

    def result_values(self) -> tuple[ConfigValues, LogValues]:
        """The settings as edited in the form"""
        config = self._config
        for section in (self._materials, self._detailing, self._building):
            config = section.apply_to(config)
        return config, self._log.values()
