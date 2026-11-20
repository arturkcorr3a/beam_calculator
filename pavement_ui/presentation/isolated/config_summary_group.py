"""Das configurações gerais: the project settings the isolated beam also uses."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from pavement_ui.core.model.settings import ConfigValues
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.text.option_labels import OptionKind, label
from pavement_ui.presentation.text.strings import isolated as s
from pavement_ui.presentation.theme.icons import icon
from pavement_ui.presentation.widgets.key_value_table import KeyValueTable


class ConfigSummaryGroup(QGroupBox):
    """Concrete, steel, aggregate size, bar types, layers and ceiling height of the project

    The ceiling height sets the pillars' rotational stiffness and a new wall's height.
    The table is read-only; the button asks to open the settings dialog.
    """

    edit_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(s.FROM_CONFIG, parent)
        self._table = KeyValueTable()
        self._table.setObjectName("isoConfigSummary")
        self._edit = QPushButton(icon("settings"), s.EDIT_CONFIG)
        self._edit.setObjectName("isoConfigButton")
        self._edit.clicked.connect(self.edit_requested)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self._edit)
        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addLayout(buttons)

    def set_edit_enabled(self, enabled: bool) -> None:
        self._edit.setEnabled(enabled)

    def set_config(self, config: ConfigValues) -> None:
        self._table.set_items(
            [
                (s.CONCRETE, label(OptionKind.CONCRETE, config.concrete_key)),
                (s.STEEL, label(OptionKind.STEEL, config.steel_key)),
                (
                    s.AGG_SIZE,
                    s.CM_VALUE.format(
                        value=fmt_number(config.max_aggregate_size_cm, 1)
                    ),
                ),
                (s.MAX_BAR_TYPES, str(config.max_bar_types)),
                (s.MAX_LAYERS, str(config.max_layers)),
                (
                    s.CEILING_HEIGHT,
                    s.M_VALUE.format(value=fmt_number(config.ceiling_height_m, 2)),
                ),
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
