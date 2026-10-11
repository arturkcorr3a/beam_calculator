"""Edificação: aggressiveness class, building category and ceiling height."""

from dataclasses import replace

from PySide6.QtWidgets import QWidget

from pavement_ui.core.model.settings import ConfigValues
from pavement_ui.core.options import EngineOptions
from pavement_ui.presentation.dialogs.config.materials_section import LABEL_WIDTH_PX
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import dialogs as s
from pavement_ui.presentation.text.strings import panels as units
from pavement_ui.presentation.widgets.combo_helpers import (
    key_combo,
    select_key,
    selected_key,
)
from pavement_ui.presentation.widgets.form_section import FormSection
from pavement_ui.presentation.widgets.unit_spin_box import UnitSpinBox


class BuildingSection(FormSection):
    def __init__(self, options: EngineOptions, parent: QWidget | None = None) -> None:
        super().__init__(s.CONFIG_BUILDING, LABEL_WIDTH_PX, parent)
        self._exposure = key_combo(
            "cfgExposure",
            options.exposure_classes,
            lambda k: label(OptionKind.EXPOSURE, k),
        )
        self._category = key_combo(
            "cfgCategory",
            options.building_categories,
            lambda k: label(OptionKind.CATEGORY, k),
        )
        self._ceiling = UnitSpinBox(2, 0.01, 20.0, units.UNIT_M, 0.05)
        self._ceiling.setObjectName("cfgCeilingHeight")
        self.add_row(s.CONFIG_EXPOSURE, self._exposure)
        self.add_row(s.CONFIG_CATEGORY, self._category, s.CONFIG_CATEGORY_HINT)
        self.add_row(s.CONFIG_CEILING, self._ceiling)

    def load(self, config: ConfigValues) -> None:
        select_key(self._exposure, config.exposure_key)
        select_key(self._category, config.building_category_key)
        self._ceiling.setValue(config.ceiling_height_m)

    def apply_to(self, config: ConfigValues) -> ConfigValues:
        return replace(
            config,
            exposure_key=selected_key(self._exposure) or config.exposure_key,
            building_category_key=selected_key(self._category)
            or config.building_category_key,
            ceiling_height_m=self._ceiling.value(),
        )
