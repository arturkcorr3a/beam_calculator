"""QuantitiesWindow: bar schedule and net quantities of the beams."""

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pavement_ui.core.results.quantities import (
    BeamQuantity,
    QuantitiesResult,
    ScheduleEntry,
    SteelByDiameter,
)
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.results.quantities.quantities_columns import (
    BEAM_COLUMNS,
    SCHEDULE_COLUMNS,
    STEEL_COLUMNS,
)
from pavement_ui.presentation.text.strings import results as s
from pavement_ui.presentation.theme import tokens
from pavement_ui.presentation.widgets.column_table_model import (
    ColumnSpec,
    ColumnTableModel,
)
from pavement_ui.presentation.widgets.read_only_table import ReadOnlyTable

_SIZE_PX = (1100, 760)


def _table[T](
    columns: Sequence[ColumnSpec[T]], name: str
) -> tuple[QGroupBox, ColumnTableModel[T]]:
    """A titled group holding a read-only table."""
    table = ReadOnlyTable()
    table.setObjectName(name)
    model = ColumnTableModel[T](columns, table)
    table.setModel(model)
    group = QGroupBox()
    QVBoxLayout(group).addWidget(table)
    return group, model


class QuantitiesWindow(QWidget):
    """Steel by diameter and quantities per beam, beside the bar schedule; Fechar"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("quantitiesWindow")
        self.resize(*_SIZE_PX)
        self._steel_group, self._steel = _table(STEEL_COLUMNS, "quantitiesSteelTable")
        self._beams_group, self._beams = _table(BEAM_COLUMNS, "quantitiesBeamTable")
        self._schedule_group, self._schedule = _table(
            SCHEDULE_COLUMNS, "quantitiesScheduleTable"
        )
        left = QVBoxLayout()
        left.addWidget(self._steel_group, 2)
        left.addWidget(self._beams_group, 3)
        tables = QHBoxLayout()
        tables.addLayout(left, 1)
        tables.addWidget(self._schedule_group, 1)
        hint = QLabel(s.QUANTITIES_HINT)
        hint.setObjectName("hint")
        close = QPushButton(s.CLOSE)
        close.clicked.connect(self.close)
        footer = QHBoxLayout()
        footer.addWidget(hint, 1)
        footer.addWidget(close)
        layout = QVBoxLayout(self)
        margin = tokens.MARGIN_PX * 2
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addLayout(tables, 1)
        layout.addLayout(footer)

    def set_results(self, quantities: QuantitiesResult, file_name: str) -> None:
        self.setWindowTitle(s.QUANTITIES_TITLE.format(file=file_name))
        self._steel_group.setTitle(
            s.QUANTITIES_STEEL.format(
                length=fmt_number(quantities.steel_length_m, 2),
                mass=fmt_number(quantities.steel_kg, 1),
            )
        )
        self._beams_group.setTitle(
            s.QUANTITIES_BEAMS.format(
                mass=fmt_number(quantities.steel_kg, 1),
                concrete=fmt_number(quantities.concrete_m3, 2),
                formwork=fmt_number(quantities.formwork_m2, 2),
            )
        )
        self._schedule_group.setTitle(
            s.QUANTITIES_SCHEDULE.format(n=len(quantities.schedule))
        )
        steel: Sequence[SteelByDiameter] = quantities.steel
        beams: Sequence[BeamQuantity] = quantities.beams
        schedule: Sequence[ScheduleEntry] = quantities.schedule
        self._steel.set_rows(steel)
        self._beams.set_rows(beams)
        self._schedule.set_rows(schedule)
