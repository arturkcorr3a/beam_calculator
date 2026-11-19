"""A table of named rows whose cells are numeric inputs with units."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from pavement_ui.presentation.widgets.unit_spin_box import UnitSpinBox

_ROW_HEIGHT_PX = 30


@dataclass(frozen=True, slots=True)
class SpinColumn:
    """One numeric column

    Attributes:
        default: Value of a new row, in the unit.
    """

    header: str
    decimals: int
    minimum: float
    maximum: float
    unit: str
    default: float


class SpinTable(QTableWidget):
    """Rows named by ``name_of(index)``; each column is a ``UnitSpinBox``

    Signals:
        changed: Any value was edited, or rows were added or removed.
    """

    changed = Signal()

    def __init__(
        self,
        name_header: str,
        columns: Sequence[SpinColumn],
        name_of: Callable[[int], str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(0, 1 + len(columns), parent)
        self._columns = tuple(columns)
        self._name_of = name_of
        self.setHorizontalHeaderLabels([name_header, *(c.header for c in columns)])
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(_ROW_HEIGHT_PX)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_row_count(self, count: int) -> None:
        """Add rows with the defaults or drop the last ones; kept rows keep their values"""
        while self.rowCount() < count:
            self._append_row()
        while self.rowCount() > count:
            self.removeRow(self.rowCount() - 1)
        self._fit_height()
        self.changed.emit()

    def set_values(self, rows: Sequence[Sequence[float]]) -> None:
        """One row per item, each with a value per column; emits changed once"""
        self.blockSignals(True)
        self.set_row_count(len(rows))
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                box = self._box(row, col)
                box.blockSignals(True)
                box.setValue(value)
                box.blockSignals(False)
        self.blockSignals(False)
        self.changed.emit()

    def values(self) -> list[tuple[float, ...]]:
        """The values of each row, left to right, in the columns' units"""
        return [
            tuple(self._box(row, col).value() for col in range(len(self._columns)))
            for row in range(self.rowCount())
        ]

    def _box(self, row: int, col: int) -> UnitSpinBox:
        widget = self.cellWidget(row, col + 1)
        assert isinstance(widget, UnitSpinBox)
        return widget

    def _append_row(self) -> None:
        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, QTableWidgetItem(self._name_of(row)))
        for col, column in enumerate(self._columns, start=1):
            box = UnitSpinBox(
                column.decimals, column.minimum, column.maximum, column.unit
            )
            box.setValue(column.default)
            box.setFrame(False)
            box.valueChanged.connect(self.changed)
            self.setCellWidget(row, col, box)

    def _fit_height(self) -> None:
        """Show every row and no empty space below them"""
        rows = self.verticalHeader().length()
        self.setFixedHeight(
            rows + self.horizontalHeader().height() + 2 * self.frameWidth()
        )
