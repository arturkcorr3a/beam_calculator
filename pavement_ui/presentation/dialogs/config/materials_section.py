"""Materiais: concrete, steel, aggregate type and maximum aggregate size."""

from dataclasses import replace

from PySide6.QtWidgets import QWidget

from pavement_ui.core.model.settings import ConfigValues
from pavement_ui.core.options import EngineOptions
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

LABEL_WIDTH_PX = 200


class MaterialsSection(FormSection):
    def __init__(self, options: EngineOptions, parent: QWidget | None = None) -> None:
        super().__init__(s.CONFIG_MATERIALS, LABEL_WIDTH_PX, parent)
        self._concrete = key_combo(
            "cfgConcrete",
            options.concrete_classes,
            lambda k: label(OptionKind.CONCRETE, k),
        )
        self._steel = key_combo(
            "cfgSteel", options.steels, lambda k: label(OptionKind.STEEL, k)
        )
        self._aggregate = key_combo(
            "cfgAggregate", options.aggregates, lambda k: label(OptionKind.AGGREGATE, k)
        )
        self._aggregate_size = UnitSpinBox(1, 0.1, 10.0, units.UNIT_CM, 0.1)
        self._aggregate_size.setObjectName("cfgAggSize")
        self.add_row(s.CONFIG_CONCRETE, self._concrete)
        self.add_row(s.CONFIG_STEEL, self._steel)
        self.add_row(s.CONFIG_AGGREGATE, self._aggregate)
        self.add_row(s.CONFIG_AGG_SIZE, self._aggregate_size)

    def load(self, config: ConfigValues) -> None:
        select_key(self._concrete, config.concrete_key)
        select_key(self._steel, config.steel_key)
        select_key(self._aggregate, config.aggregate_key)
        self._aggregate_size.setValue(config.max_aggregate_size_cm)

    def apply_to(self, config: ConfigValues) -> ConfigValues:
        return replace(
            config,
            concrete_key=selected_key(self._concrete) or config.concrete_key,
            steel_key=selected_key(self._steel) or config.steel_key,
            aggregate_key=selected_key(self._aggregate) or config.aggregate_key,
            max_aggregate_size_cm=self._aggregate_size.value(),
        )
