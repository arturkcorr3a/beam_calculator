"""QuantitiesWindow: bar schedule and net quantities of the beams."""

from collections.abc import Sequence
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pavement_ui.core.errors import EngineRuleError
from pavement_ui.core.ports import BudgetCalculator
from pavement_ui.core.results.materials import MaterialsInfo
from pavement_ui.core.results.quantities import (
    BeamQuantity,
    QuantitiesResult,
    ScheduleEntry,
    SteelByDiameter,
)
from pavement_ui.presentation.dialogs.messages import show_budget_error
from pavement_ui.presentation.dialogs.price_dialog import ask_concrete_price
from pavement_ui.presentation.formatting.numbers import fmt_number
from pavement_ui.presentation.results.budget.budget_window import BudgetWindow
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
    """Steel by diameter and quantities per beam, beside the bar schedule; Orçamento… and Fechar

    Orçamento… asks the concrete price and opens the budget, priced at that
    moment. New results close the budget, which no longer matches them.
    """

    def __init__(
        self, budget_calculator: BudgetCalculator, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setObjectName("quantitiesWindow")
        self.resize(*_SIZE_PX)
        self._budget_calculator = budget_calculator
        self._budget: BudgetWindow | None = None
        self._quantities: QuantitiesResult | None = None
        self._materials: MaterialsInfo | None = None
        self._file_name = ""
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
        budget = QPushButton(s.QUANTITIES_BUDGET)
        budget.setObjectName("quantitiesBudgetButton")
        budget.clicked.connect(self._open_budget)
        close = QPushButton(s.CLOSE)
        close.clicked.connect(self.close)
        footer = QHBoxLayout()
        footer.addWidget(hint, 1)
        footer.addWidget(budget)
        footer.addWidget(close)
        layout = QVBoxLayout(self)
        margin = tokens.MARGIN_PX * 2
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.addLayout(tables, 1)
        layout.addLayout(footer)

    def set_results(
        self, quantities: QuantitiesResult, materials: MaterialsInfo, file_name: str
    ) -> None:
        self._close_budget()
        self._quantities, self._materials = quantities, materials
        self._file_name = file_name
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

    def _open_budget(self) -> None:
        """Ask the concrete price, price the quantities now and show the budget"""
        if self._quantities is None or self._materials is None:
            return
        price = ask_concrete_price(self)
        if price is None:
            return
        try:
            budget = self._budget_calculator.budget(
                self._quantities, self._materials, price, datetime.now()
            )
        except EngineRuleError as error:
            show_budget_error(self, error.message)
            return
        if self._budget is None:
            self._budget = BudgetWindow(budget, self._file_name, self)
        else:
            self._budget.set_budget(budget, self._file_name)
        self._budget.show()
        self._budget.raise_()
        self._budget.activateWindow()

    def _close_budget(self) -> None:
        if self._budget is not None:
            self._budget.close()
            self._budget.deleteLater()
            self._budget = None

    def closeEvent(self, event: QCloseEvent) -> None:
        self._close_budget()
        super().closeEvent(event)
