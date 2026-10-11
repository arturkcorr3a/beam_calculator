"""A read-only table model whose columns are declared as ``ColumnSpec``s."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)
from PySide6.QtGui import QColor

from pavement_ui.presentation.theme.fonts import mono_font

type _Index = QModelIndex | QPersistentModelIndex
_ROOT = QModelIndex()  # the invalid parent index of a flat table


@dataclass(frozen=True, slots=True)
class ColumnSpec[T]:
    """One table column

    Attributes:
        header: Column title.
        text: Cell text of a row (already formatted).
        numeric: Right-aligned, monospaced cell.
        tooltip: Optional tooltip of a row's cell.
        color: Optional text color of a row's cell (hex), e.g. a verdict.
    """

    header: str
    text: Callable[[T], str]
    numeric: bool = False
    tooltip: Callable[[T], str] | None = None
    color: Callable[[T], str | None] | None = None


class ColumnTableModel[T](QAbstractTableModel):
    """Show a sequence of rows through column specs; rows keep their given order"""

    def __init__(
        self, columns: Sequence[ColumnSpec[T]], parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._columns = tuple(columns)
        self._rows: tuple[T, ...] = ()
        self._mono = mono_font()

    def set_rows(self, rows: Sequence[T]) -> None:
        """Replace every row"""
        self.beginResetModel()
        self._rows = tuple(rows)
        self.endResetModel()

    def row_at(self, row: int) -> T:
        return self._rows[row]

    def rows(self) -> tuple[T, ...]:
        return self._rows

    def rowCount(self, parent: _Index = _ROOT) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: _Index = _ROOT) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        column = self._columns[index.column()]
        row = self._rows[index.row()]
        match role:
            case Qt.ItemDataRole.DisplayRole:
                return column.text(row)
            case Qt.ItemDataRole.ToolTipRole if column.tooltip is not None:
                return column.tooltip(row)
            case Qt.ItemDataRole.TextAlignmentRole if column.numeric:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            case Qt.ItemDataRole.ForegroundRole if column.color is not None:
                color = column.color(row)
                return QColor(color) if color else None
            case Qt.ItemDataRole.FontRole if column.numeric:
                return self._mono
            case _:
                return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if (
            orientation is Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self._columns[section].header
        return None
