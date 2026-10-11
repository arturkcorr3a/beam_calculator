"""Detalhamento das armaduras: maximum bar diameters and maximum layers."""

from dataclasses import replace

from PySide6.QtWidgets import QWidget

from pavement_ui.core.model.settings import ConfigValues
from pavement_ui.presentation.dialogs.config.materials_section import LABEL_WIDTH_PX
from pavement_ui.presentation.text.strings import dialogs as s
from pavement_ui.presentation.widgets.form_section import FormSection
from pavement_ui.presentation.widgets.unit_spin_box import IntUnitSpinBox

_LIMITS = (1, 10)


class DetailingSection(FormSection):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(s.CONFIG_DETAILING, LABEL_WIDTH_PX, parent)
        self._bar_types = IntUnitSpinBox(*_LIMITS, s.CONFIG_PER_REINFORCEMENT)
        self._bar_types.setObjectName("cfgMaxBarTypes")
        self._layers = IntUnitSpinBox(*_LIMITS, s.CONFIG_LAYERS)
        self._layers.setObjectName("cfgMaxLayers")
        self.add_row(s.CONFIG_MAX_BAR_TYPES, self._bar_types)
        self.add_row(s.CONFIG_MAX_LAYERS, self._layers)

    def load(self, config: ConfigValues) -> None:
        self._bar_types.setValue(config.max_bar_types)
        self._layers.setValue(config.max_layers)

    def apply_to(self, config: ConfigValues) -> ConfigValues:
        return replace(
            config,
            max_bar_types=self._bar_types.value(),
            max_layers=self._layers.value(),
        )
