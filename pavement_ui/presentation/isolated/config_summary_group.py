"""Das configurações gerais: the project settings the isolated beam also uses (read-only)."""

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QWidget

from pavement_ui.core.model.settings import ConfigValues
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.widgets.key_value_table import KeyValueTable


class ConfigSummaryGroup(QGroupBox):
    """Steel, aggregate size, bar types and layers of the current project"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(s.FROM_CONFIG, parent)
        self._table = KeyValueTable()
        self._table.setObjectName("isoConfigSummary")
        QVBoxLayout(self).addWidget(self._table)

    def set_config(self, config: ConfigValues) -> None:
        self._table.set_items(
            [
                (s.STEEL, label(OptionKind.STEEL, config.steel_key)),
                (
                    s.AGG_SIZE,
                    s.CM_VALUE.format(
                        value=fmt_number(config.max_aggregate_size_cm, 1)
                    ),
                ),
                (s.MAX_BAR_TYPES, str(config.max_bar_types)),
                (s.MAX_LAYERS, str(config.max_layers)),
            ]
        )
        self._fit_height()

    def _fit_height(self) -> None:
        """Show every row and no empty space below them"""
        table = self._table
        rows = table.verticalHeader().length()
        header = (
            table.horizontalHeader().height()
            if table.horizontalHeader().isVisible()
            else 0
        )
        table.setFixedHeight(rows + header + 2 * table.frameWidth())
